#!/bin/bash
# 使用 Conda 启动服务

echo "🎤 启动 Whisper.cpp STT 服务..."

# 激活 conda 环境
eval "$(conda shell.bash hook)"
conda activate stt-service

# 启动服务
python server_cpp.py
