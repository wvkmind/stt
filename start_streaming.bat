@echo off
chcp 65001 >nul
echo 启动流式 STT 服务...

call conda activate stt
python server_streaming.py

pause
