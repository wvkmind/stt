#!/usr/bin/env python3
"""
流式实时语音转文字 WebSocket 服务
基于 SenseVoice-Small (阿里最新，速度快)
"""
import asyncio
import websockets
import json
import tempfile
import os
import logging
from funasr import AutoModel

try:
    from opencc import OpenCC
    HAS_OPENCC = True
except ImportError:
    HAS_OPENCC = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局模型
MODEL = None
CC = None

def init_model():
    """初始化 SenseVoice 模型（从 HuggingFace 下载）"""
    global MODEL, CC
    logger.info("正在从 HuggingFace 加载 SenseVoice-Small 模型...")
    logger.info("这可能需要 1-2 分钟，请耐心等待...")
    
    # 设置详细日志
    import logging
    logging.getLogger("funasr").setLevel(logging.INFO)
    
    MODEL = AutoModel(
        model="FunAudioLLM/SenseVoiceSmall",
        hub="hf",
        device="cpu",
        disable_pbar=False,
        disable_log=False,  # 显示日志
        disable_update=True
    )
    
    logger.info("✅ 模型加载完成")
    
    # 初始化繁简转换
    if HAS_OPENCC:
        CC = OpenCC('t2s')
        logger.info("繁简转换已启用")

class AudioBuffer:
    """音频缓冲区，分段转录"""
    def __init__(self):
        self.buffer = bytearray()
        self.all_text = []
        self.last_data_time = None
        self.min_data_size = 30 * 1024  # 30KB
        self.silence_threshold = 1.0  # 1秒停顿
        
    def add_data(self, data: bytes):
        """添加音频数据"""
        import time
        self.buffer.extend(data)
        self.last_data_time = time.time()
        
    def should_transcribe(self):
        """是否应该转录"""
        import time
        
        if len(self.buffer) < self.min_data_size:
            return False
        
        if self.last_data_time:
            silence_duration = time.time() - self.last_data_time
            if silence_duration >= self.silence_threshold:
                logger.info(f"🔇 停顿 {silence_duration:.1f}秒")
                return True
        
        return False
    
    def get_segment_for_transcribe(self):
        """获取当前段数据并清空"""
        if len(self.buffer) == 0:
            return None
        chunk = bytes(self.buffer)
        self.buffer.clear()
        return chunk
    
    def get_remaining_data(self):
        """获取剩余数据"""
        if len(self.buffer) == 0:
            return None
        chunk = bytes(self.buffer)
        self.buffer.clear()
        return chunk
    
    def add_text(self, text: str):
        """添加转录结果"""
        if text:
            self.all_text.append(text)
    
    def get_full_text(self):
        """获取完整转录结果"""
        return "".join(self.all_text)

def to_simplified_chinese(text: str) -> str:
    """转换为简体中文"""
    if not text:
        return text
    
    if HAS_OPENCC and CC:
        try:
            return CC.convert(text)
        except Exception as e:
            logger.error(f"繁简转换错误: {e}")
            return text
    return text

async def transcribe_chunk(audio_data: bytes):
    """转录音频块"""
    try:
        # 保存临时文件
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name
        
        logger.info(f"开始转录 {len(audio_data)} 字节")
        
        # 转录
        result = MODEL.generate(
            input=tmp_path,
            language="zh",
            use_itn=True  # 逆文本归一化
        )
        
        # 删除临时文件
        os.unlink(tmp_path)
        
        # 提取文本
        if result and len(result) > 0:
            text = result[0].get("text", "")
            text = text.strip()
            text = to_simplified_chinese(text)
            logger.info(f"转录完成: {text}")
            return text
        
        return None
    
    except Exception as e:
        logger.error(f"转录错误: {e}", exc_info=True)
        return None

async def periodic_transcribe(buffer, websocket, interval=0.5):
    """定时检查任务"""
    transcribing = False
    
    while True:
        await asyncio.sleep(interval)
        
        if transcribing:
            continue
        
        if buffer.should_transcribe():
            transcribing = True
            segment = buffer.get_segment_for_transcribe()
            logger.info(f"🎙️ 转录段 {len(segment)} 字节")
            
            try:
                text = await transcribe_chunk(segment)
                if text:
                    buffer.add_text(text)
                    full_text = buffer.get_full_text()
                    await websocket.send(json.dumps({
                        "type": "partial",
                        "text": full_text,
                        "is_final": False
                    }))
                    logger.info(f"✅ 段: {text}")
                    logger.info(f"📝 累积: {full_text}")
            finally:
                transcribing = False

async def handle_streaming_client(websocket, path):
    """处理流式客户端连接"""
    client_id = id(websocket)
    logger.info(f"客户端 {client_id} 已连接")
    
    buffer = AudioBuffer()
    session_active = False
    transcribe_task = None
    
    try:
        await websocket.send(json.dumps({
            "type": "connected",
            "message": "已连接到 SenseVoice STT 服务",
            "mode": "streaming"
        }))
        
        async for message in websocket:
            if isinstance(message, bytes):
                if not session_active:
                    session_active = True
                    logger.info(f"✅ 开始接收音频流")
                
                buffer.add_data(message)
            
            elif isinstance(message, str):
                try:
                    data = json.loads(message)
                    cmd = data.get("command")
                    
                    if cmd == "start":
                        buffer = AudioBuffer()
                        session_active = True
                        
                        transcribe_task = asyncio.create_task(
                            periodic_transcribe(buffer, websocket, interval=0.5)
                        )
                        
                        await websocket.send(json.dumps({
                            "type": "session_started"
                        }))
                        logger.info(f"✅ 开始新会话")
                    
                    elif cmd == "stop":
                        if transcribe_task:
                            transcribe_task.cancel()
                            try:
                                await transcribe_task
                            except asyncio.CancelledError:
                                pass
                        
                        # 处理剩余数据
                        remaining = buffer.get_remaining_data()
                        if remaining and len(remaining) > 10240:
                            logger.info(f"🔄 最后一段 {len(remaining)} 字节")
                            text = await transcribe_chunk(remaining)
                            if text:
                                buffer.add_text(text)
                                logger.info(f"✅ 段: {text}")
                        
                        # 返回完整结果
                        full_text = buffer.get_full_text()
                        logger.info(f"📝 完整: {full_text}")
                        
                        await websocket.send(json.dumps({
                            "type": "final",
                            "text": full_text,
                            "is_final": True
                        }))
                        
                        session_active = False
                        await websocket.send(json.dumps({
                            "type": "session_ended"
                        }))
                        logger.info(f"✅ 结束")
                    
                    elif cmd == "ping":
                        await websocket.send(json.dumps({
                            "type": "pong"
                        }))
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️ 无效 JSON: {e}")
    
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"客户端 {client_id} 断开连接")
        if transcribe_task:
            transcribe_task.cancel()
    except Exception as e:
        logger.error(f"处理客户端 {client_id} 时出错: {e}", exc_info=True)
        if transcribe_task:
            transcribe_task.cancel()

async def main():
    """启动服务"""
    init_model()
    
    host = "0.0.0.0"
    port = 8765
    
    logger.info(f"启动 SenseVoice WebSocket 服务器: ws://{host}:{port}")
    logger.info("支持实时流式转录")
    
    async with websockets.serve(handle_streaming_client, host, port):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
