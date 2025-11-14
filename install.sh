#!/bin/bash
# 一键安装脚本

echo "🚀 开始安装实时 STT 服务..."

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python3，请先安装"
    exit 1
fi

# 创建虚拟环境
echo "📦 创建虚拟环境..."
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 升级 pip
pip install --upgrade pip

# 安装依赖
echo "📥 安装依赖..."
pip install -r requirements.txt

echo "✅ 安装完成！"
echo ""
echo "启动服务:"
echo "  source venv/bin/activate"
echo "  python server.py"
