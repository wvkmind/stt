#!/bin/bash
# 快速启动脚本

echo "🎤 启动实时 STT 服务..."

# 激活虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ 虚拟环境不存在，请先运行: bash install.sh"
    exit 1
fi

# 启动服务
python server.py
