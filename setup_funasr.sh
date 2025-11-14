#!/bin/bash
# 安装 FunASR（阿里达摩院，中文识别更准确）

set -e

echo "🎤 安装 FunASR - 中文语音识别专家"

# 激活环境
eval "$(conda shell.bash hook)"
conda activate stt-service

# 安装 FunASR
echo "📥 安装 FunASR..."
pip install funasr modelscope torch torchaudio

echo ""
echo "✅ 安装完成！"
echo ""
echo "启动服务："
echo "  conda activate stt-service"
echo "  python server_funasr.py"
echo ""
