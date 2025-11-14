#!/usr/bin/env python3
"""
流式实时语音转文字 WebSocket 服务
基于 Whisper.cpp (C++ 实现，速度快 5-10 倍)
"""
import asyncio
import websockets
import json
import tempfile
import os
import logging
from pywhispercpp.model import Model

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
    """初始化 Whisper.cpp 模型"""
    global MODEL, CC
    logger.info("正在加载 Whisper.cpp 模型 (C++ 实现)...")
    logger.info("首次运行会下载模型，请稍候...")
    
    # 使用 medium 模型，中文准确率更高（比 base 慢 2 倍，但准确率提升 20%）
    MODEL = Model(
        'medium',  # medium 模型，中文识别更准确
        n_threads=8  # 使用 8 线程
    )
    
    logger.info("✅ 模型加载完成")
    
    # 初始化繁简转换
    if HAS_OPENCC:
        CC = OpenCC('t2s')
        logger.info("繁简转换已启用")

class AudioBuffer:
    """音频缓冲区，实时流式转录"""
    def __init__(self):
        self.buffer = bytearray()
        self.all_text = []
        self.last_data_time = None
        self.last_transcribe_time = None
        self.min_data_size = 30 * 1024  # 最小 30KB
        self.max_interval = 2.0  # 最多 2 秒就转录一次
        self.silence_threshold = 1.0
        self.is_segment_end = False  # 是否段落结束
        
    def add_data(self, data: bytes):
        """添加音频数据"""
        import time
        self.buffer.extend(data)
        self.last_data_time = time.time()
        
    def should_transcribe(self):
        """是否应该转录（停顿或时间到）"""
        import time
        
        if len(self.buffer) < self.min_data_size:
            return False
        
        current_time = time.time()
        
        # 触发1：停顿检测（段落结束）
        if self.last_data_time:
            silence_duration = current_time - self.last_data_time
            if silence_duration >= self.silence_threshold:
                logger.info(f"🔇 停顿 {silence_duration:.1f}秒 - 段落结束")
                self.is_segment_end = True
                self.last_transcribe_time = current_time
                return True
        
        # 触发2：持续说话，每2秒也转录（中间结果）
        if self.last_transcribe_time:
            time_since_last = current_time - self.last_transcribe_time
            if time_since_last >= self.max_interval:
                logger.info(f"⏱️ 持续说话 {time_since_last:.1f}秒 - 中间结果")
                self.is_segment_end = False
                self.last_transcribe_time = current_time
                return True
        else:
            # 第一次转录
            if len(self.buffer) >= self.min_data_size:
                self.is_segment_end = False
                self.last_transcribe_time = current_time
                return True
        
        return False
    
    def get_data_for_transcribe(self):
        """获取数据（根据是否段落结束决定是否清空）"""
        if len(self.buffer) == 0:
            return None, False
        
        chunk = bytes(self.buffer)
        
        # 如果是段落结束，清空缓冲区
        if self.is_segment_end:
            self.buffer.clear()
            return chunk, True  # True = 段落结束
        else:
            # 中间结果，不清空
            return chunk, False  # False = 继续累积
    
    def get_remaining_data(self):
        """获取剩余数据"""
        if len(self.buffer) == 0:
            return None, False
        chunk = bytes(self.buffer)
        self.buffer.clear()
        return chunk, True  # 最后一段
    
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
        result = MODEL.transcribe(
            tmp_path,
            language='zh',
            translate=False
        )
        
        # 删除临时文件
        os.unlink(tmp_path)
        
        # 提取文本（result 是 Segment 对象列表）
        if isinstance(result, list) and len(result) > 0:
            text = " ".join([seg.text for seg in result if hasattr(seg, 'text')])
        elif isinstance(result, str):
            text = result
        else:
            text = ""
        
        text = text.strip()
        text = to_simplified_chinese(text)
        logger.info(f"转录完成: {text}")
        return text
    
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
            chunk, is_segment_end = buffer.get_data_for_transcribe()
            logger.info(f"🎙️ 转录 {len(chunk)} 字节")
            
            try:
                text = await transcribe_chunk(chunk)
                if text:
                    if is_segment_end:
                        # 段落结束，保存这段文本
                        buffer.add_text(text)
                        logger.info(f"✅ 段落: {text}")
                    
                    # 返回完整累积结果
                    full_text = buffer.get_full_text()
                    if not is_segment_end and text:
                        # 中间结果，临时拼接
                        full_text = full_text + text if full_text else text
                    
                    await websocket.send(json.dumps({
                        "type": "partial",
                        "text": full_text,
                        "is_final": False
                    }))
                    logger.info(f"📝 返回: {full_text}")
            finally:
                transcribing = False

async def handle_streaming_client(websocket):
    """处理流式客户端连接"""
    client_id = id(websocket)
    logger.info(f"客户端 {client_id} 已连接")
    
    buffer = AudioBuffer()
    session_active = False
    transcribe_task = None
    
    try:
        await websocket.send(json.dumps({
            "type": "connected",
            "message": "已连接到 Whisper.cpp STT 服务 (C++ 加速)",
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
                        remaining, _ = buffer.get_remaining_data()
                        if remaining and len(remaining) > 10240:
                            logger.info(f"🔄 最后一段 {len(remaining)} 字节")
                            text = await transcribe_chunk(remaining)
                            if text:
                                buffer.add_text(text)
                                logger.info(f"✅ 最后段: {text}")
                        
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
    
    logger.info(f"启动 Whisper.cpp WebSocket 服务器: ws://{host}:{port}")
    logger.info("C++ 实现，速度提升 5-10 倍！")
    
    async with websockets.serve(handle_streaming_client, host, port):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
