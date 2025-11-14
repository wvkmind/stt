# Windows 快速开始

## 1. 安装

双击运行：
```
install.bat
```

会自动：
- 创建虚拟环境
- 安装所有依赖
- 下载 Whisper 模型（首次运行时）

## 2. 启动服务

双击运行：
```
start.bat
```

看到这个说明启动成功：
```
启动 WebSocket 服务器: ws://0.0.0.0:8765
模型加载完成
```

## 3. 测试

### 方法1：网页客户端（推荐）

1. 保持服务运行
2. 双击打开 `client_demo.html`
3. 点击"连接服务"
4. 点击"上传文件"选择音频文件

### 方法2：命令行测试

新开一个命令行窗口：
```cmd
test.bat your_audio.wav
```

### 方法3：Python 测试

```cmd
venv\Scripts\activate
python test_client.py your_audio.wav
```

## 常见问题

### 1. 找不到 Python
下载安装：https://www.python.org/downloads/
安装时勾选 "Add Python to PATH"

### 2. 安装依赖失败
```cmd
venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. 端口被占用
修改 `server.py` 第 88 行：
```python
port = 8765  # 改成其他端口，如 9000
```

### 4. 模型下载慢
首次运行会下载 ~150MB 模型，耐心等待
或手动下载放到：`C:\Users\你的用户名\.cache\huggingface\hub\`

## 支持的音频格式

- WAV（推荐）
- MP3
- M4A
- FLAC

建议格式：16kHz 单声道 WAV

## 性能参考

- 转录 30 秒音频：约 5-10 秒
- 内存占用：约 500MB
- CPU 占用：转录时 50-80%

## 下一步

- 修改 `server.py` 调整模型大小（tiny/base/small/medium）
- 开发自己的客户端（参考 `test_client.py`）
- 集成到你的应用中
conda activate stt