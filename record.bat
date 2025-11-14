@echo off
chcp 65001 >nul

REM 激活环境
call conda activate stt

REM 安装 pyaudio（如果没有）
pip show pyaudio >nul 2>&1
if errorlevel 1 (
    echo 正在安装 pyaudio...
    pip install pyaudio
)

REM 录音
if "%~1"=="" (
    python record.py 5 test.wav
) else (
    python record.py %1 test.wav
)

echo.
echo 按任意键测试转录...
pause >nul

REM 测试转录
python test_client.py test.wav

pause
