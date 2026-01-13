#!/usr/bin/env python3
"""
检查视频文件和对应的音频文件时长是否一致
"""

import os
import subprocess
import argparse
import sys

def get_duration(file_path):
    """获取文件时长（秒）"""
    try:
        cmd = [
            "ffprobe", 
            "-v", "error", 
            "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", 
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except (ValueError, subprocess.CalledProcessError):
        return 0.0

def format_time(seconds):
    """格式化时间为 MM:SS"""
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}:{s:02d}"

def check_directory(directory):
    if not os.path.exists(directory):
        print(f"目录不存在: {directory}")
        return

    print(f"正在检查目录: {directory}")
    print("-" * 80)
    print(f"{'文件名':<30} | {'视频时长':<10} | {'音频时长':<10} | {'差异':<10} | {'状态':<10}")
    print("-" * 80)

    # 获取所有 mp4 文件
    mp4_files = sorted([f for f in os.listdir(directory) if f.lower().endswith('.mp4')])
    
    issues_found = 0
    
    for mp4_file in mp4_files:
        base_name = os.path.splitext(mp4_file)[0]
        mp4_path = os.path.join(directory, mp4_file)
        
        # 查找对应的音频文件 (优先 wav, 然后 mp3)
        audio_file = None
        audio_path = None
        audio_type = None
        
        if os.path.exists(os.path.join(directory, f"{base_name}.wav")):
            audio_file = f"{base_name}.wav"
            audio_path = os.path.join(directory, audio_file)
            audio_type = "WAV"
        elif os.path.exists(os.path.join(directory, f"{base_name}.mp3")):
            audio_file = f"{base_name}.mp3"
            audio_path = os.path.join(directory, audio_file)
            audio_type = "MP3"
            
        if not audio_path:
            # print(f"{mp4_file:<30} | 未找到对应的音频文件")
            continue
            
        # 获取时长
        video_dur = get_duration(mp4_path)
        audio_dur = get_duration(audio_path)
        
        diff = abs(video_dur - audio_dur)
        status = "✅ 正常" if diff <= 1.0 else "❌ 不匹配"
        
        # 显示所有文件的检查结果
        print(f"{base_name:<30} | {format_time(video_dur):<10} | {format_time(audio_dur):<10} ({audio_type}) | {diff:.2f}s     | {status}")
        
        if diff > 1.0:
            issues_found += 1
            
    print("-" * 80)
    if issues_found == 0:
        print("所有检查的文件时长均匹配。")
    else:
        print(f"发现 {issues_found} 个文件时长不匹配。")

if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "series/jinhun/downloads"
    check_directory(target_dir)
