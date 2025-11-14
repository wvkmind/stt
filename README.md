# 实时语音转文字 WebSocket 服务

基于 faster-whisper 的实时 STT 服务，针对 macOS M1 优化。

## 安装

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 启动服务

```bash
python server.py
```

服务将在 `ws://localhost:8765` 启动。

## 测试

```bash
# 用测试客户端发送音频文件
python test_client.py your_audio.wav
```

## WebSocket 协议

### 客户端 → 服务器

**发送音频数据（二进制）**
```
直接发送 WAV/MP3 音频的二进制数据
```

**发送控制命令（JSON）**
```json
{
  "command": "ping"
}
```

### 服务器 → 客户端

**连接确认**
```json
{
  "type": "connected",
  "message": "已连接到 STT 服务"
}
```

**处理中**
```json
{
  "type": "processing",
  "message": "正在转录..."
}
```

**转录结果**
```json
{
  "type": "result",
  "text": "转录的文字内容"
}
```

**错误**
```json
{
  "type": "error",
  "message": "错误信息"
}
```

## 性能

- M1 Pro: ~3秒转录 30秒音频
- 内存占用: ~500MB
- 支持并发连接

## 客户端示例

### JavaScript (浏览器)

```javascript
const ws = new WebSocket('ws://localhost:8765');

ws.onopen = () => {
  console.log('已连接');
  
  // 发送音频 Blob
  navigator.mediaDevices.getUserMedia({ audio: true })
    .then(stream => {
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorder.ondataavailable = (e) => {
        ws.send(e.data);
      };
      mediaRecorder.start();
    });
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'result') {
    console.log('转录:', data.text);
  }
};
```

### Python

```python
import asyncio
import websockets

async def transcribe():
    async with websockets.connect('ws://localhost:8765') as ws:
        with open('audio.wav', 'rb') as f:
            await ws.send(f.read())
        
        result = await ws.recv()
        print(result)

asyncio.run(transcribe())
```

## 配置

修改 `server.py` 中的参数：

```python
# 模型大小: tiny, base, small, medium, large
MODEL = WhisperModel("base", ...)

# 端口
port = 8765

# 语言
language = "zh"  # zh, en, ja, etc.
```

## 注意事项

1. 首次运行会下载模型（~150MB）
2. 音频格式建议: WAV 16kHz 单声道
3. 单次音频建议 <60秒（更长的分段发送）
