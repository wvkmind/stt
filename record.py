#!/usr/bin/env python3
"""
简单录音工具 - 录制音频并保存为 WAV 文件
"""
import pyaudio
import wave
import sys

def record_audio(filename="test.wav", duration=5):
    """录制音频"""
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    
    p = pyaudio.PyAudio()
    
    print(f"🎤 开始录音 ({duration} 秒)...")
    print("请说话...")
    
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    
    frames = []
    
    for i in range(0, int(RATE / CHUNK * duration)):
        data = stream.read(CHUNK)
        frames.append(data)
        
        # 显示进度
        progress = (i + 1) / (RATE / CHUNK * duration) * 100
        print(f"\r录音中... {progress:.0f}%", end="")
    
    print("\n✅ 录音完成！")
    
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    # 保存文件
    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    
    print(f"💾 已保存到: {filename}")

if __name__ == "__main__":
    duration = 5
    filename = "test.wav"
    
    if len(sys.argv) > 1:
        duration = int(sys.argv[1])
    if len(sys.argv) > 2:
        filename = sys.argv[2]
    
    print(f"录音时长: {duration} 秒")
    print(f"保存文件: {filename}")
    print()
    
    record_audio(filename, duration)
