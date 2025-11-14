#!/bin/bash
# 安装 SenseVoice 完整依赖

set -e

echo "🎤 安装 SenseVoice 完整依赖..."

eval "$(conda shell.bash hook)"
conda activate stt-service

echo "📥 安装 PyTorch..."
pip install torch torchaudio

echo "📥 安装 HuggingFace Hub..."
pip install huggingface_hub

echo ""
echo "✅ 安装完成！"
echo ""
echo "启动服务："
echo "  python server_sensevoice.py"
