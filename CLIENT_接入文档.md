# STT WebSocket 客户端接入文档

## 服务信息

- **地址**: `ws://localhost:8765`
- **协议**: WebSocket
- **支持格式**: WAV, MP3, M4A, FLAC 等常见音频格式
- **推荐格式**: 16kHz 单声道 WAV

## 通信协议

### 1. 连接

客户端连接后，服务器会立即发送连接确认：

```json
{
  "type": "connected",
  "message": "已连接到 STT 服务"
}
```

### 2. 发送音频

**方式A：发送完整音频文件（推荐）**

直接发送音频文件的二进制数据（Binary Message）

```javascript
// JavaScript 示例
const audioBlob = new Blob([audioData], { type: 'audio/wav' });
websocket.send(audioBlob);
```

```python
# Python 示例
with open('audio.wav', 'rb') as f:
    await websocket.send(f.read())
```

**方式B：发送控制命令（可选）**

发送 JSON 文本消息：

```json
{
  "command": "ping"
}
```

### 3. 接收响应

服务器会依次返回以下消息：

**处理中状态**
```json
{
  "type": "processing",
  "message": "正在转录..."
}
```

**转录结果（成功）**
```json
{
  "type": "result",
  "text": "这是转录的文字内容"
}
```

**错误信息**
```json
{
  "type": "error",
  "message": "错误描述"
}
```

**Ping 响应**
```json
{
  "type": "pong"
}
```

## 客户端示例代码

### JavaScript (浏览器)

```javascript
// 连接服务
const ws = new WebSocket('ws://localhost:8765');

ws.onopen = () => {
  console.log('已连接到 STT 服务');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'connected':
      console.log('服务器确认连接');
      break;
    case 'processing':
      console.log('正在转录...');
      break;
    case 'result':
      console.log('转录结果:', data.text);
      break;
    case 'error':
      console.error('错误:', data.message);
      break;
  }
};

ws.onerror = (error) => {
  console.error('WebSocket 错误:', error);
};

ws.onclose = () => {
  console.log('连接已关闭');
};

// 发送音频文件
function sendAudioFile(file) {
  const reader = new FileReader();
  reader.onload = (e) => {
    ws.send(e.target.result);
  };
  reader.readAsArrayBuffer(file);
}

// 发送录音
async function sendRecording() {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const mediaRecorder = new MediaRecorder(stream);
  const chunks = [];
  
  mediaRecorder.ondataavailable = (e) => chunks.push(e.data);
  mediaRecorder.onstop = () => {
    const blob = new Blob(chunks, { type: 'audio/wav' });
    ws.send(blob);
  };
  
  mediaRecorder.start();
  setTimeout(() => mediaRecorder.stop(), 5000); // 录 5 秒
}
```

### Python (asyncio)

```python
import asyncio
import websockets
import json

async def transcribe_audio(audio_file):
    uri = "ws://localhost:8765"
    
    async with websockets.connect(uri) as websocket:
        # 接收连接确认
        response = await websocket.recv()
        print(json.loads(response))
        
        # 发送音频
        with open(audio_file, 'rb') as f:
            await websocket.send(f.read())
        
        # 接收处理状态
        response = await websocket.recv()
        print(json.loads(response))
        
        # 接收转录结果
        response = await websocket.recv()
        result = json.loads(response)
        
        if result['type'] == 'result':
            print(f"转录结果: {result['text']}")
        else:
            print(f"错误: {result['message']}")

# 运行
asyncio.run(transcribe_audio('audio.wav'))
```

### Python (websocket-client 同步库)

```python
import websocket
import json

def on_message(ws, message):
    data = json.loads(message)
    if data['type'] == 'result':
        print(f"转录结果: {data['text']}")

def on_error(ws, error):
    print(f"错误: {error}")

def on_close(ws, close_status_code, close_msg):
    print("连接关闭")

def on_open(ws):
    print("已连接")
    # 发送音频
    with open('audio.wav', 'rb') as f:
        ws.send(f.read(), opcode=websocket.ABNF.OPCODE_BINARY)

ws = websocket.WebSocketApp(
    "ws://localhost:8765",
    on_open=on_open,
    on_message=on_message,
    on_error=on_error,
    on_close=on_close
)

ws.run_forever()
```

### Node.js

```javascript
const WebSocket = require('ws');
const fs = require('fs');

const ws = new WebSocket('ws://localhost:8765');

ws.on('open', () => {
  console.log('已连接到 STT 服务');
  
  // 发送音频文件
  const audioData = fs.readFileSync('audio.wav');
  ws.send(audioData);
});

ws.on('message', (data) => {
  const message = JSON.parse(data);
  
  if (message.type === 'result') {
    console.log('转录结果:', message.text);
    ws.close();
  } else if (message.type === 'error') {
    console.error('错误:', message.message);
    ws.close();
  }
});

ws.on('error', (error) => {
  console.error('WebSocket 错误:', error);
});
```

### C# (.NET)

```csharp
using System;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using System.IO;

class STTClient
{
    static async Task Main(string[] args)
    {
        using var ws = new ClientWebSocket();
        await ws.ConnectAsync(new Uri("ws://localhost:8765"), CancellationToken.None);
        
        // 接收连接确认
        var buffer = new byte[1024 * 4];
        var result = await ws.ReceiveAsync(new ArraySegment<byte>(buffer), CancellationToken.None);
        var message = Encoding.UTF8.GetString(buffer, 0, result.Count);
        Console.WriteLine(message);
        
        // 发送音频
        var audioData = File.ReadAllBytes("audio.wav");
        await ws.SendAsync(new ArraySegment<byte>(audioData), WebSocketMessageType.Binary, true, CancellationToken.None);
        
        // 接收结果
        result = await ws.ReceiveAsync(new ArraySegment<byte>(buffer), CancellationToken.None);
        message = Encoding.UTF8.GetString(buffer, 0, result.Count);
        
        var json = JsonDocument.Parse(message);
        if (json.RootElement.GetProperty("type").GetString() == "result")
        {
            Console.WriteLine("转录结果: " + json.RootElement.GetProperty("text").GetString());
        }
        
        await ws.CloseAsync(WebSocketCloseStatus.NormalClosure, "", CancellationToken.None);
    }
}
```

### Java

```java
import org.java_websocket.client.WebSocketClient;
import org.java_websocket.handshake.ServerHandshake;
import java.net.URI;
import java.nio.ByteBuffer;
import java.nio.file.Files;
import java.nio.file.Paths;
import org.json.JSONObject;

public class STTClient extends WebSocketClient {
    
    public STTClient(URI serverUri) {
        super(serverUri);
    }
    
    @Override
    public void onOpen(ServerHandshake handshakedata) {
        System.out.println("已连接到 STT 服务");
        
        try {
            // 发送音频文件
            byte[] audioData = Files.readAllBytes(Paths.get("audio.wav"));
            send(audioData);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
    
    @Override
    public void onMessage(String message) {
        JSONObject json = new JSONObject(message);
        String type = json.getString("type");
        
        if (type.equals("result")) {
            System.out.println("转录结果: " + json.getString("text"));
            close();
        } else if (type.equals("error")) {
            System.err.println("错误: " + json.getString("message"));
            close();
        }
    }
    
    @Override
    public void onClose(int code, String reason, boolean remote) {
        System.out.println("连接关闭");
    }
    
    @Override
    public void onError(Exception ex) {
        ex.printStackTrace();
    }
    
    public static void main(String[] args) throws Exception {
        STTClient client = new STTClient(new URI("ws://localhost:8765"));
        client.connect();
    }
}
```

### Go

```go
package main

import (
    "encoding/json"
    "fmt"
    "io/ioutil"
    "log"
    "github.com/gorilla/websocket"
)

type Message struct {
    Type    string `json:"type"`
    Text    string `json:"text,omitempty"`
    Message string `json:"message,omitempty"`
}

func main() {
    // 连接服务
    conn, _, err := websocket.DefaultDialer.Dial("ws://localhost:8765", nil)
    if err != nil {
        log.Fatal(err)
    }
    defer conn.Close()
    
    // 接收连接确认
    _, message, _ := conn.ReadMessage()
    fmt.Println(string(message))
    
    // 发送音频
    audioData, _ := ioutil.ReadFile("audio.wav")
    conn.WriteMessage(websocket.BinaryMessage, audioData)
    
    // 接收结果
    for {
        _, message, err := conn.ReadMessage()
        if err != nil {
            break
        }
        
        var msg Message
        json.Unmarshal(message, &msg)
        
        if msg.Type == "result" {
            fmt.Printf("转录结果: %s\n", msg.Text)
            break
        } else if msg.Type == "error" {
            fmt.Printf("错误: %s\n", msg.Message)
            break
        }
    }
}
```

## 音频格式建议

### 最佳格式
- **采样率**: 16000 Hz
- **声道**: 单声道 (Mono)
- **位深度**: 16-bit
- **格式**: WAV

### 转换命令 (ffmpeg)

```bash
# 转换为最佳格式
ffmpeg -i input.mp3 -ar 16000 -ac 1 output.wav

# 从麦克风录音
ffmpeg -f dshow -i audio="麦克风" -ar 16000 -ac 1 -t 10 output.wav
```

## 性能参考

| 音频时长 | 转录时间 (base 模型) | 内存占用 |
|---------|---------------------|---------|
| 10 秒   | ~2 秒               | ~500MB  |
| 30 秒   | ~5 秒               | ~500MB  |
| 60 秒   | ~10 秒              | ~500MB  |

## 错误处理

### 常见错误

1. **连接失败**
   - 检查服务是否启动
   - 检查端口 8765 是否被占用

2. **转录失败**
   - 检查音频格式是否支持
   - 检查音频文件是否损坏
   - 查看服务器日志

3. **超时**
   - 音频文件过大（建议 <60 秒）
   - 网络延迟

### 重连机制示例

```javascript
class STTClient {
  constructor(url) {
    this.url = url;
    this.reconnectDelay = 1000;
    this.maxReconnectDelay = 30000;
    this.connect();
  }
  
  connect() {
    this.ws = new WebSocket(this.url);
    
    this.ws.onopen = () => {
      console.log('已连接');
      this.reconnectDelay = 1000;
    };
    
    this.ws.onclose = () => {
      console.log('连接断开，尝试重连...');
      setTimeout(() => this.connect(), this.reconnectDelay);
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
    };
    
    this.ws.onerror = (error) => {
      console.error('错误:', error);
    };
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };
  }
  
  handleMessage(data) {
    // 处理消息
  }
  
  send(audioData) {
    if (this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(audioData);
    } else {
      console.error('WebSocket 未连接');
    }
  }
}
```

## 安全建议

### 生产环境部署

1. **使用 WSS (WebSocket Secure)**
   ```python
   # 需要 SSL 证书
   import ssl
   ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
   ssl_context.load_cert_chain('cert.pem', 'key.pem')
   
   async with websockets.serve(handle_client, host, port, ssl=ssl_context):
       await asyncio.Future()
   ```

2. **添加认证**
   ```python
   async def handle_client(websocket, path):
       # 验证 token
       token = websocket.request_headers.get('Authorization')
       if not verify_token(token):
           await websocket.close(1008, "未授权")
           return
       # ...
   ```

3. **限流**
   ```python
   from collections import defaultdict
   import time
   
   rate_limit = defaultdict(list)
   
   async def handle_client(websocket, path):
       client_ip = websocket.remote_address[0]
       now = time.time()
       
       # 清理旧记录
       rate_limit[client_ip] = [t for t in rate_limit[client_ip] if now - t < 60]
       
       # 检查限流
       if len(rate_limit[client_ip]) >= 10:  # 每分钟最多 10 次
           await websocket.close(1008, "请求过于频繁")
           return
       
       rate_limit[client_ip].append(now)
       # ...
   ```

## 常见问题

**Q: 支持实时流式转录吗？**
A: 当前版本需要完整音频文件。如需流式转录，需要修改服务端代码支持分块处理。

**Q: 可以同时处理多个请求吗？**
A: 可以，服务支持并发连接。

**Q: 如何提高转录速度？**
A: 使用更小的模型（tiny/base），或使用 GPU 版本。

**Q: 支持哪些语言？**
A: 默认中文，可在服务端修改 `language` 参数支持其他语言（en, ja, ko 等）。

## 联系与支持

遇到问题请查看：
- 服务端日志
- 客户端控制台输出
- 本项目的 README.md

---

**版本**: 1.0  
**更新日期**: 2024-11-14
