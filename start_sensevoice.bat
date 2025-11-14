@echo off
chcp 65001 >nul
echo 启动 SenseVoice STT 服务...

call conda activate stt
python server_sensevoice.py

pause
