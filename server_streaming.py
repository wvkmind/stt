#!/usr/bin/env python3
"""
流式实时语音转文字 WebSocket 服务
支持音频流分块实时转录
"""
import asyncio
import websockets
import json
import tempfile
import os
import wave
import logging
from faster_whisper import WhisperModel
try:
    from opencc import OpenCC
    HAS_OPENCC = True
except ImportError:
    HAS_OPENCC = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 繁体转简体转换器
CC = None

# 全局模型
MODEL = None

def init_model():
    """初始化 Whisper 模型"""
    global MODEL, CC
    logger.info("正在加载 Whisper 模型...")
    MODEL = WhisperModel("base", device="cpu", compute_type="int8")
    logger.info("模型加载完成")
    
    # 初始化繁简转换
    if HAS_OPENCC:
        CC = OpenCC('t2s')  # 繁体转简体
        logger.info("繁简转换已启用")
    else:
        logger.warning("未安装 opencc-python-reimplemented，无法进行繁简转换")
        logger.warning("安装命令: pip install opencc-python-reimplemented")

class AudioBuffer:
    """音频缓冲区，用于流式处理"""
    def __init__(self, sample_rate=16000, channels=1, sample_width=2):
        self.sample_rate = sample_rate
        self.channels = channels
        self.sample_width = sample_width
        self.buffer = bytearray()
        self.chunk_duration = 3  # 每 3 秒转录一次
        self.chunk_size = sample_rate * channels * sample_width * self.chunk_duration
        
    def add_data(self, data: bytes):
        """添加音频数据"""
        self.buffer.extend(data)
        
    def has_chunk(self):
        """是否有足够的数据进行转录"""
        return len(self.buffer) >= self.chunk_size
    
    def get_chunk(self):
        """获取一个音频块"""
        if not self.has_chunk():
            return None
        
        chunk = bytes(self.buffer[:self.chunk_size])
        self.buffer = self.buffer[self.chunk_size:]
        return chunk
    
    def get_remaining(self):
        """获取剩余数据"""
        if len(self.buffer) == 0:
            return None
        chunk = bytes(self.buffer)
        self.buffer.clear()
        return chunk
    
    def save_to_wav(self, data: bytes, filename: str):
        """保存为 WAV 文件"""
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.sample_width)
            wf.setframerate(self.sample_rate)
            wf.writeframes(data)

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

async def transcribe_chunk(audio_data: bytes, buffer: AudioBuffer, language="zh"):
    """转录音频块"""
    try:
        # 保存临时文件
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            buffer.save_to_wav(audio_data, tmp.name)
            tmp_path = tmp.name
        
        # 转录
        segments, info = MODEL.transcribe(
            tmp_path,
            language=language,
            beam_size=3,  # 降低 beam_size 提高速度
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=300)
        )
        
        # 收集结果
        text = ""
        for segment in segments:
            text += segment.text
        
        # 删除临时文件
        os.unlink(tmp_path)
        
        # 转换为简体中文
        text = text.strip()
        text = to_simplified_chinese(text)
        
        return text
    
    except Exception as e:
        logger.error(f"转录错误: {e}")
        return None

async def handle_streaming_client(websocket, path):
    """处理流式客户端连接"""
    client_id = id(websocket)
    logger.info(f"客户端 {client_id} 已连接（流式模式）")
    
    buffer = AudioBuffer()
    session_active = False
    
    try:
        await websocket.send(json.dumps({
            "type": "connected",
            "message": "已连接到流式 STT 服务",
            "mode": "streaming"
        }))
        
        async for message in websocket:
            if isinstance(message, bytes):
                # 接收音频流数据
                if not session_active:
                    session_active = True
                    logger.info(f"客户端 {client_id} 开始流式传输")
                
                buffer.add_data(message)
                
                # 当缓冲区有足够数据时，进行转录
                while buffer.has_chunk():
                    chunk = buffer.get_chunk()
                    
                    # 异步转录，不阻塞接收
                    text = await transcribe_chunk(chunk, buffer)
                    
                    if text:
                        await websocket.send(json.dumps({
                            "type": "partial",
                            "text": text,
                            "is_final": False
                        }))
                        logger.info(f"部分结果: {text}")
            
            elif isinstance(message, str):
                # 接收控制命令
                try:
                    data = json.loads(message)
                    cmd = data.get("command")
                    
                    if cmd == "start":
                        # 开始新会话
                        buffer = AudioBuffer()
                        session_active = True
                        await websocket.send(json.dumps({
                            "type": "session_started"
                        }))
                        logger.info(f"客户端 {client_id} 开始新会话")
                    
                    elif cmd == "stop":
                        # 结束会话，处理剩余数据
                        remaining = buffer.get_remaining()
                        if remaining:
                            text = await transcribe_chunk(remaining, buffer)
                            if text:
                                await websocket.send(json.dumps({
                                    "type": "final",
                                    "text": text,
                                    "is_final": True
                                }))
                                logger.info(f"最终结果: {text}")
                        
                        session_active = False
                        await websocket.send(json.dumps({
                            "type": "session_ended"
                        }))
                        logger.info(f"客户端 {client_id} 结束会话")
                    
                    elif cmd == "ping":
                        await websocket.send(json.dumps({
                            "type": "pong"
                        }))
                    
                except json.JSONDecodeError:
                    logger.warning(f"无效的 JSON: {message}")
    
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"客户端 {client_id} 断开连接")
    except Exception as e:
        logger.error(f"处理客户端 {client_id} 时出错: {e}")

async def main():
    """启动服务"""
    init_model()
    
    host = "0.0.0.0"
    port = 8765
    
    logger.info(f"启动流式 WebSocket 服务器: ws://{host}:{port}")
    logger.info("支持实时流式转录")
    
    async with websockets.serve(handle_streaming_client, host, port):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
