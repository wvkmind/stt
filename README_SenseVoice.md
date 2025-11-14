# SenseVoice 实时语音转文字服务

基于阿里最新的 SenseVoice-Small 模型，专为中文优化。

## 优势

- ✅ **速度快**：比 Whisper medium 快 3-5 倍
- ✅ **准确率高**：中文识别准确率更高
- ✅ **模型小**：~200MB，内存占用低
- ✅ **实时性好**：低延迟流式识别

## 安装

```bash
# 激活环境
conda activate stt

# 安装依赖
pip install -r requirements_sensevoice.txt
```

## 启动

### Windows
```cmd
start_sensevoice.bat
```

### macOS/Linux
```bash
conda activate stt
python server_sensevoice.py
```

## 服务信息

- **地址**: `ws://localhost:8766`
- **协议**: 与 Whisper 版本相同
- **端口**: 8766（避免冲突）

## 性能对比

| 指标 | Whisper medium | SenseVoice-Small |
|------|----------------|------------------|
| 模型大小 | ~1.5GB | ~200MB |
| 内存占用 | ~5GB | ~2GB |
| 转录速度 | 5-10秒/30秒音频 | 2-3秒/30秒音频 |
| 中文准确率 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## 客户端使用

客户端代码完全相同，只需修改连接地址：

```javascript
const ws = new WebSocket('ws://localhost:8766');  // 改端口
```

## 注意事项

1. **首次运行**会下载模型（~200MB）
2. **需要 torch**：如果没有，会自动安装
3. **M1 优化**：自动使用 CPU 优化

## 切换回 Whisper

如果想切换回 Whisper 版本：

```bash
# 停止 SenseVoice
Ctrl+C

# 启动 Whisper
python server_streaming.py
```

两个版本可以同时运行（不同端口）。
