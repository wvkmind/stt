#!/usr/bin/env python3
"""
实时语音转文字 WebSocket 服务
基于 Paraformer (阿里达摩院，中文优化，速度快)
"""
import asyncio
import websockets
import json
import tempfile
import os
import logging
from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局模型
MODEL = None

def init_model():
    """初始化 Paraformer 模型"""
    global MODEL
    logger.info("正在加载 Paraformer 模型（中文优化）...")
    
    MODEL = pipeline(
        task=Tasks.auto_speech_recognition,
        model='damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch',
    )
    
    logger.info("✅ 模型加载完成")

async def transcribe_audio(audio_data: bytes):
    """转录音频数据"""
    try:
        # 保存临时文件
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name
        
        logger.info(f"开始转录 {len(audio_data)} 字节")
        
        # 转录
        result = MODEL(tmp_path)
        
        # 删除临时文件
        os.unlink(tmp_path)
        
        # 提取文本
        if result and 'text' in result:
            text = result['text'].strip()
            logger.info(f"转录完成: {text}")
            return text
        
        return None
    
    except Exception as e:
        logger.error(f"转录错误: {e}", exc_info=True)
        return None

async def handle_client(websocket, path):
    """处理 WebSocket 客户端连接"""
    client_id = id(websocket)
    logger.info(f"客户端 {client_id} 已连接")
    
    try:
        await websocket.send(json.dumps({
            "type": "connected",
            "message": "已连接到 Paraformer STT 服务（中文优化）"
        }))
        
        async for message in websocket:
            if isinstance(message, bytes):
                logger.info(f"收到音频数据: {len(message)} 字节")
                
                await websocket.send(json.dumps({
                    "type": "processing",
                    "message": "正在转录..."
                }))
                
                text = await transcribe_audio(message)
                
                if text:
                    await websocket.send(json.dumps({
                        "type": "result",
                        "text": text
                    }))
                else:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "转录失败"
                    }))
            
            elif isinstance(message, str):
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
    init_model()
    
    host = "0.0.0.0"
    port = 8765
    
    logger.info(f"启动 Paraformer WebSocket 服务器: ws://{host}:{port}")
    logger.info("中文识别优化，速度快，准确率高")
    
    async with websockets.serve(handle_client, host, port):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
