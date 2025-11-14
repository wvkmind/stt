@echo off
chcp 65001 >nul
echo 🚀 开始安装实时 STT 服务...

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Python，请先安装
    pause
    exit /b 1
)

REM 创建虚拟环境
echo 📦 创建虚拟环境...
python -m venv venv

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 升级 pip
python -m pip install --upgrade pip

REM 安装依赖
echo 📥 安装依赖...
pip install -r requirements.txt

echo.
echo ✅ 安装完成！
echo.
echo 启动服务:
echo   start.bat
echo.
pause
