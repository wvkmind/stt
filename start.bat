@echo off
chcp 65001 >nul
echo 🎤 启动实时 STT 服务...

REM 检查虚拟环境
if not exist "venv\Scripts\activate.bat" (
    echo ❌ 虚拟环境不存在，请先运行: install.bat
    pause
    exit /b 1
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 启动服务
python server.py

pause
