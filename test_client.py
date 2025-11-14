#!/usr/bin/env python3
"""
测试客户端 - 发送音频文件到 WebSocket 服务
"""
import asyncio
import websockets
import json
import sys

async def test_transcribe(audio_file):
    """测试转录功能"""
    uri = "ws://localhost:8765"
    
    async with websockets.connect(uri) as websocket:
        # 接收连接确认
        response = await websocket.recv()
        print(f"服务器: {response}")
        
        # 读取音频文件
        with open(audio_file, 'rb') as f:
            audio_data = f.read()
        
        print(f"发送音频文件: {audio_file} ({len(audio_data)} 字节)")
        
        # 发送音频数据
        await websocket.send(audio_data)
        
        # 接收处理状态
        response = await websocket.recv()
        print(f"服务器: {response}")
        
        # 接收转录结果
        response = await websocket.recv()
        result = json.loads(response)
        
        if result["type"] == "result":
            print(f"\n转录结果:\n{result['text']}\n")
        else:
            print(f"错误: {result.get('message')}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python test_client.py <音频文件>")
        print("示例: python test_client.py test.wav")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    asyncio.run(test_transcribe(audio_file))
