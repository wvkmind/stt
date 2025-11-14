# STT 流式 WebSocket 客户端接入文档

## 服务信息

- **地址**: `ws://localhost:8765`
- **模式**: 流式实时转录
- **协议**: WebSocket
- **音频格式**: 16kHz 单声道 16-bit PCM

## 流式转录协议

### 1. 连接

客户端连接后，服务器发送：

```json
{
  "type": "connected",
  "message": "已连接到流式 STT 服务",
  "mode": "streaming"
}
```

### 2. 开始会话（可选）

发送 JSON 命令：

```json
{
  "command": "start"
}
```

服务器响应：

```json
{
  "type": "session_started"
}
```

### 3. 发送音频流

**持续发送音频数据块（Binary Message）**

- 每次发送一小块音频数据（如 100ms-500ms）
- 服务器会自动缓冲并每 3 秒转录一次
- 不需要等待响应，持续发送即可

```javascript
// 示例：每 100ms 发送一次
setInterval(() => {
  const audioChunk = getAudioChunk(); // 获取音频数据
  websocket.send(audioChunk);
}, 100);
```

### 4. 接收实时结果

**部分结果（实时）**

```json
{
  "type": "partial",
  "text": "这是部分转录结果",
  "is_final": false
}
```

**最终结果**

```json
{
  "type": "final",
  "text": "这是最终转录结果",
  "is_final": true
}
```

### 5. 结束会话

发送停止命令：

```json
{
  "command": "stop"
}
```

服务器会处理剩余音频并返回最终结果，然后响应：

```json
{
  "type": "session_ended"
}
```

## 完整流程

```
客户端                           服务器
  |                                |
  |-------- 连接 WebSocket -------->|
  |<------- connected -------------|
  |                                |
  |-------- {"command":"start"} -->|
  |<------- session_started -------|
  |                                |
  |-------- 音频块 1 ------------->|
  |-------- 音频块 2 ------------->|
  |-------- 音频块 3 ------------->|
  |<------- partial (部分结果) ----|
  |-------- 音频块 4 ------------->|
  |-------- 音频块 5 ------------->|
  |-------- 音频块 6 ------------->|
  |<------- partial (部分结果) ----|
  |                                |
  |-------- {"command":"stop"} --->|
  |<------- final (最终结果) ------|
  |<------- session_ended ---------|
```

## 客户端示例代码

### JavaScript (浏览器实时录音)

```javascript
class StreamingSTTClient {
  constructor(url = 'ws://localhost:8765') {
    this.url = url;
    this.ws = null;
    this.mediaRecorder = null;
    this.isRecording = false;
  }
  
  connect() {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.url);
      
      this.ws.onopen = () => {
        console.log('已连接到流式 STT 服务');
        resolve();
      };
      
      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        this.handleMessage(data);
      };
      
      this.ws.onerror = (error) => {
        console.error('WebSocket 错误:', error);
        reject(error);
      };
      
      this.ws.onclose = () => {
        console.log('连接已关闭');
      };
    });
  }
  
  handleMessage(data) {
    switch(data.type) {
      case 'connected':
        console.log('服务器:', data.message);
        break;
      case 'partial':
        console.log('部分结果:', data.text);
        this.onPartialResult(data.text);
        break;
      case 'final':
        console.log('最终结果:', data.text);
        this.onFinalResult(data.text);
        break;
      case 'session_started':
        console.log('会话已开始');
        break;
      case 'session_ended':
        console.log('会话已结束');
        break;
    }
  }
  
  async startRecording() {
    if (this.isRecording) return;
    
    // 开始会话
    this.ws.send(JSON.stringify({ command: 'start' }));
    
    // 获取麦克风
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        sampleRate: 16000,
        echoCancellation: true,
        noiseSuppression: true
      }
    });
    
    // 创建 MediaRecorder
    this.mediaRecorder = new MediaRecorder(stream, {
      mimeType: 'audio/webm;codecs=opus'
    });
    
    // 每 100ms 发送一次数据
    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0 && this.ws.readyState === WebSocket.OPEN) {
        // 将 webm 转为 PCM（实际应用中需要音频处理库）
        this.ws.send(event.data);
      }
    };
    
    this.mediaRecorder.start(100); // 每 100ms 触发一次
    this.isRecording = true;
    console.log('开始录音...');
  }
  
  stopRecording() {
    if (!this.isRecording) return;
    
    this.mediaRecorder.stop();
    this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
    
    // 结束会话
    this.ws.send(JSON.stringify({ command: 'stop' }));
    
    this.isRecording = false;
    console.log('停止录音');
  }
  
  // 回调函数（由使用者实现）
  onPartialResult(text) {
    // 处理部分结果
  }
  
  onFinalResult(text) {
    // 处理最终结果
  }
}

// 使用示例
const client = new StreamingSTTClient();

client.onPartialResult = (text) => {
  document.getElementById('result').textContent = text;
};

client.onFinalResult = (text) => {
  document.getElementById('final').textContent = text;
};

// 连接并开始录音
await client.connect();
client.startRecording();

// 5 秒后停止
setTimeout(() => client.stopRecording(), 5000);
```

### Python (asyncio)

```python
import asyncio
import websockets
import json
import pyaudio

class StreamingSTTClient:
    def __init__(self, url="ws://localhost:8765"):
        self.url = url
        self.ws = None
        self.is_recording = False
        
    async def connect(self):
        """连接服务器"""
        self.ws = await websockets.connect(self.url)
        response = await self.ws.recv()
        print(json.loads(response))
        
    async def start_session(self):
        """开始会话"""
        await self.ws.send(json.dumps({"command": "start"}))
        response = await self.ws.recv()
        print(json.loads(response))
        
    async def stop_session(self):
        """结束会话"""
        await self.ws.send(json.dumps({"command": "stop"}))
        
    async def send_audio_stream(self, duration=5):
        """发送音频流"""
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        
        p = pyaudio.PyAudio()
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        
        print(f"开始录音 {duration} 秒...")
        self.is_recording = True
        
        frames = int(RATE / CHUNK * duration)
        for i in range(frames):
            if not self.is_recording:
                break
            data = stream.read(CHUNK)
            await self.ws.send(data)
        
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        print("录音结束")
        
    async def receive_results(self):
        """接收转录结果"""
        try:
            async for message in self.ws:
                data = json.loads(message)
                
                if data['type'] == 'partial':
                    print(f"部分结果: {data['text']}")
                elif data['type'] == 'final':
                    print(f"最终结果: {data['text']}")
                elif data['type'] == 'session_ended':
                    print("会话结束")
                    break
        except Exception as e:
            print(f"接收错误: {e}")
    
    async def run(self, duration=5):
        """运行完整流程"""
        await self.connect()
        await self.start_session()
        
        # 同时发送和接收
        await asyncio.gather(
            self.send_audio_stream(duration),
            self.receive_results()
        )
        
        await self.stop_session()
        await self.ws.close()

# 使用
async def main():
    client = StreamingSTTClient()
    await client.run(duration=10)

asyncio.run(main())
```

### Python (简化版)

```python
import asyncio
import websockets
import json
import pyaudio

async def streaming_transcribe():
    uri = "ws://localhost:8765"
    
    async with websockets.connect(uri) as ws:
        # 连接确认
        print(await ws.recv())
        
        # 开始会话
        await ws.send(json.dumps({"command": "start"}))
        print(await ws.recv())
        
        # 录音并发送
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024
        )
        
        async def send_audio():
            for _ in range(100):  # 约 6 秒
                data = stream.read(1024)
                await ws.send(data)
            stream.close()
            p.terminate()
            await ws.send(json.dumps({"command": "stop"}))
        
        async def receive_results():
            async for msg in ws:
                data = json.loads(msg)
                if data['type'] in ['partial', 'final']:
                    print(f"{data['type']}: {data['text']}")
                if data['type'] == 'session_ended':
                    break
        
        await asyncio.gather(send_audio(), receive_results())

asyncio.run(streaming_transcribe())
```

## 音频格式要求

### 推荐格式
- **采样率**: 16000 Hz
- **声道**: 单声道 (Mono)
- **位深度**: 16-bit
- **编码**: PCM

### 浏览器录音配置

```javascript
const constraints = {
  audio: {
    channelCount: 1,
    sampleRate: 16000,
    echoCancellation: true,
    noiseSuppression: true,
    autoGainControl: true
  }
};

const stream = await navigator.mediaDevices.getUserMedia(constraints);
```

### Python 录音配置

```python
import pyaudio

p = pyaudio.PyAudio()
stream = p.open(
    format=pyaudio.paInt16,  # 16-bit
    channels=1,              # 单声道
    rate=16000,              # 16kHz
    input=True,
    frames_per_buffer=1024
)
```

## 性能优化

### 1. 调整缓冲区大小

修改 `server_streaming.py` 中的 `chunk_duration`：

```python
self.chunk_duration = 3  # 秒，越小越实时但 CPU 占用越高
```

### 2. 调整转录参数

```python
segments, info = MODEL.transcribe(
    tmp_path,
    language=language,
    beam_size=3,  # 降低提高速度，提高增加准确率
    vad_filter=True,
    vad_parameters=dict(min_silence_duration_ms=300)
)
```

### 3. 客户端发送频率

```javascript
// 更频繁 = 更实时，但网络开销更大
this.mediaRecorder.start(100);  // 100ms

// 较慢 = 延迟更高，但更稳定
this.mediaRecorder.start(500);  // 500ms
```

## 延迟分析

| 组件 | 延迟 |
|------|------|
| 音频采集 | ~100ms |
| 网络传输 | ~10-50ms |
| 缓冲等待 | ~3000ms (可调) |
| 转录处理 | ~1000-2000ms |
| **总延迟** | **~4-5 秒** |

## 常见问题

**Q: 为什么不是真正的实时？**
A: Whisper 模型需要一定长度的音频上下文才能准确转录，所以需要缓冲 3 秒左右。如需更低延迟，可以使用专门的流式 ASR 模型。

**Q: 如何降低延迟？**
A: 
1. 减小 `chunk_duration`（但会降低准确率）
2. 使用更小的模型（tiny）
3. 使用 GPU 加速

**Q: 支持多语言吗？**
A: 支持，修改服务端 `language` 参数即可（zh, en, ja, ko 等）

**Q: 可以同时处理多个客户端吗？**
A: 可以，每个连接独立处理。

## 与非流式版本对比

| 特性 | 流式版本 | 非流式版本 |
|------|---------|-----------|
| 实时性 | ⭐⭐⭐⭐ | ⭐⭐ |
| 准确率 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 延迟 | 4-5 秒 | 需等待完整音频 |
| CPU 占用 | 较高 | 较低 |
| 适用场景 | 实时对话、会议记录 | 文件转录、字幕制作 |

---

**版本**: 2.0 (流式)  
**更新日期**: 2024-11-14
