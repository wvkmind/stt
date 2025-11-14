#!/usr/bin/env python3
"""
实时语音转文字 WebSocket 服务
基于 faster-whisper (M1 优化)
"""
import asyncio
import websockets
import json
import tempfile
import os
from pathlib import Path
from faster_whisper import WhisperModel
import wave
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局模型（启动时加载一次）
MODEL = None

def init_model():
    """初始化 Whisper 模型"""
    global MODEL
    logger.info("正在加载 Whisper 模型...")
    # base 模型，int8 量化，适合 M1
    MODEL = WhisperModel("base", device="cpu", compute_type="int8")
    logger.info("模型加载完成")

async def transcribe_audio(audio_data: bytes, language="zh"):
    """转录音频数据"""
    try:
        # 保存临时文件
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name
        
        # 转录
        segments, info = MODEL.transcribe(
            tmp_path,
            language=language,
            beam_size=5,
            vad_filter=True,  # 语音活动检测
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        
        # 收集结果
        text = ""
        for segment in segments:
            text += segment.text
        
        # 删除临时文件
        os.unlink(tmp_path)
        
        return text.strip()
    
    except Exception as e:
        logger.error(f"转录错误: {e}")
        return None

async def handle_client(websocket, path):
    """处理 WebSocket 客户端连接"""
    client_id = id(websocket)
    logger.info(f"客户端 {client_id} 已连接")
    
    try:
        await websocket.send(json.dumps({
            "type": "connected",
            "message": "已连接到 STT 服务"
        }))
        
        async for message in websocket:
            if isinstance(message, bytes):
                # 接收音频数据
                logger.info(f"收到音频数据: {len(message)} 字节")
                
                # 发送处理中状态
                await websocket.send(json.dumps({
                    "type": "processing",
                    "message": "正在转录..."
                }))
                
                # 转录
                text = await transcribe_audio(message)
                
                if text:
                    # 发送结果
                    await websocket.send(json.dumps({
                        "type": "result",
                        "text": text
                    }))
                    logger.info(f"转录结果: {text}")
                else:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "转录失败"
                    }))
            
            elif isinstance(message, str):
                # 接收控制命令
                try:
                    data = json.loads(message)
                    cmd = data.get("command")
                    
                    if cmd == "ping":
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
    # 初始化模型
    init_model()
    
    # 启动 WebSocket 服务器
    host = "0.0.0.0"
    port = 8765
    
    logger.info(f"启动 WebSocket 服务器: ws://{host}:{port}")
    
    async with websockets.serve(handle_client, host, port):
        await asyncio.Future()  # 永久运行

if __name__ == "__main__":
    asyncio.run(main())
