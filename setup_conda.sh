#!/bin/bash
# Conda 环境快速部署脚本

set -e

echo "🎤 使用 Conda 部署 Whisper.cpp STT 服务"

# 创建 conda 环境
echo "📦 创建 conda 环境 (stt-service)..."
conda create -n stt-service python=3.11 -y

# 激活环境
echo "✅ 激活环境..."
eval "$(conda shell.bash hook)"
conda activate stt-service

# 安装依赖
echo "📥 安装依赖..."
pip install websockets==12.0
pip install pywhispercpp
pip install opencc-python-reimplemented

echo ""
echo "✅ 安装完成！"
echo ""
echo "启动服务："
echo "  conda activate stt-service"
echo "  python server_cpp.py"
echo ""
