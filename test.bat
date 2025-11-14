@echo off
chcp 65001 >nul

if "%~1"=="" (
    echo 用法: test.bat ^<音频文件^>
    echo 示例: test.bat test.wav
    pause
    exit /b 1
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 运行测试客户端
python test_client.py %1

pause
