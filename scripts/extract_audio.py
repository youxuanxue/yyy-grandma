#!/usr/bin/env python3
"""
从 MP4 视频文件中提取 MP3 音频文件
使用 ffmpeg 进行音频提取
"""

import os
import subprocess
import argparse
import sys

def extract_audio(video_path, output_path=None, bitrate="192k", non_interactive=False):
    """
    从视频文件提取音频为 MP3 格式
    
    Args:
        video_path: 输入视频文件路径
        output_path: 输出音频文件路径（可选，默认与视频同目录）
        bitrate: MP3 比特率（默认 192k）
    """
    if not os.path.exists(video_path):
        print(f"错误: 文件不存在: {video_path}")
        return False
    
    # 如果没有指定输出路径，使用与视频文件相同的目录和名称
    if output_path is None:
        base_name = os.path.splitext(video_path)[0]
        output_path = f"{base_name}.wav"
    
    # 检查输出文件是否已存在，如果存在则直接跳过
    if os.path.exists(output_path):
        print(f"跳过: {os.path.basename(output_path)} 已存在")
        return True  # 返回 True 表示"成功"（因为文件已存在，无需处理）
    
    print(f"正在从 {video_path} 提取音频...")
    print(f"输出文件: {output_path}")
    
    # 先获取视频时长，确保完整提取
    try:
        duration_result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True,
            text=True,
            check=True
        )
        video_duration = duration_result.stdout.strip()
        if video_duration:
            duration_sec = float(video_duration)
            minutes = int(duration_sec // 60)
            seconds = int(duration_sec % 60)
            print(f"视频时长: {duration_sec:.2f} 秒 ({minutes}:{seconds:02d})")
    except Exception as e:
        print(f"⚠ 无法获取视频时长，将尝试完整提取: {e}")
        video_duration = None
    
    # 使用 ffmpeg 提取音频
    # 关键：将 -ss 0 放在 -i 之前可以更准确地定位起始位置
    # -ss 0: 从开始位置（放在 -i 之前更精确）
    # -i: 输入文件
    # -map 0:a:0: 明确映射第一个音频流
    # -vn: 不包含视频流
    # -t: 指定时长（如果获取到了视频时长）
    # -acodec libmp3lame: 使用 MP3 编码器
    # -ab: 音频比特率
    # -avoid_negative_ts make_zero: 处理时间戳问题，确保完整提取
    # -y: 自动覆盖输出文件（如果存在）
    
    # 根据输出文件扩展名决定处理方式
    ext = os.path.splitext(output_path)[1].lower()
    
    if ext == '.wav':
        # 直接提取 WAV (PCM 无损)
        print(f"提取 WAV 文件 (PCM 无损)...")
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-map", "0:a:0",
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "44100",
            "-ac", "2",
            "-y",
            output_path
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"提取 WAV 失败: {e}")
            return False
            
    else:
        # MP3 或其他格式：使用两步法（先提取为 WAV，再转为目标格式）
        # 这种方法可以解决很多因容器或编码问题导致的时长不一致问题
        wav_path = f"{os.path.splitext(output_path)[0]}_temp.wav"
        
        print(f"步骤 1/2: 提取临时 WAV 文件...")
        cmd_wav = [
            "ffmpeg",
            "-i", video_path,
            "-map", "0:a:0",
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "44100",
            "-ac", "2",
            "-y",
            wav_path
        ]
        
        try:
            subprocess.run(cmd_wav, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"提取 WAV 失败: {e}")
            if os.path.exists(wav_path):
                os.remove(wav_path)
            return False

        print(f"步骤 2/2: 转换 WAV 到 {ext.upper()}...")
        if ext == '.mp3':
            # 使用 CBR 模式 (-b:a) 而非 VBR，并禁用比特库 (reservoir=0)
            # 以确保输出时长与输入一致
            cmd_convert = [
                "ffmpeg",
                "-i", wav_path,
                "-acodec", "libmp3lame",
                "-b:a", bitrate,
                "-compression_level", "0",  # 最快编码，减少潜在问题
                "-reservoir", "0",  # 禁用比特库，确保帧对齐
                "-y",
                output_path
            ]
        else:
            cmd_convert = [
                "ffmpeg",
                "-i", wav_path,
                "-acodec", "copy",
                "-y",
                output_path
            ]
        
        try:
            subprocess.run(cmd_convert, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"转换失败: {e}")
            return False
        finally:
            # 清理临时文件
            if os.path.exists(wav_path):
                os.remove(wav_path)

    # 验证时长
    try:
        
        # 验证提取的音频时长是否与视频一致
        try:
            video_duration = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", video_path],
                capture_output=True,
                text=True,
                check=True
            ).stdout.strip()
            
            audio_duration = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", output_path],
                capture_output=True,
                text=True,
                check=True
            ).stdout.strip()
            
            if video_duration and audio_duration:
                video_sec = float(video_duration)
                audio_sec = float(audio_duration)
                diff = abs(video_sec - audio_sec)
                
                if diff > 1.0:  # 如果差异超过1秒，给出警告
                    print(f"⚠ 警告: 音频时长 ({audio_sec:.2f}s) 与视频时长 ({video_sec:.2f}s) 相差 {diff:.2f} 秒")
                else:
                    print(f"✓ 时长验证通过: 视频 {video_sec:.2f}s, 音频 {audio_sec:.2f}s")
        except Exception as e:
            print(f"⚠ 无法验证时长: {e}")
        
        print(f"✓ 成功提取音频到: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"错误: ffmpeg 执行失败")
        print(f"错误信息: {e.stderr}")
        return False
    except FileNotFoundError:
        print("错误: 未找到 ffmpeg。请确保已安装 ffmpeg 并在 PATH 中。")
        print("安装方法: brew install ffmpeg (macOS)")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="从 MP4 视频文件中提取 MP3 音频",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 提取单个文件
  python extract_audio.py video.mp4
  
  # 指定输出文件
  python extract_audio.py video.mp4 -o output.mp3
  
  # 指定比特率
  python extract_audio.py video.mp4 -b 320k
  
  # 批量处理目录中的所有 MP4 文件
  python extract_audio.py /path/to/videos/
        """
    )
    parser.add_argument("path", help="视频文件路径或包含视频文件的目录")
    parser.add_argument("-o", "--output", help="输出音频文件路径（仅对单个文件有效）")
    parser.add_argument("-b", "--bitrate", default="192k", 
                       help="MP3 比特率 (默认: 192k, 可选: 128k, 192k, 256k, 320k)")
    parser.add_argument("--non-interactive", action="store_true",
                       help="非交互模式，自动覆盖已存在的文件")
    
    args = parser.parse_args()
    
    if os.path.isdir(args.path):
        # 批量处理目录中的所有 MP4 文件
        video_files = []
        for root, dirs, files in os.walk(args.path):
            for file in files:
                if file.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.flv')):
                    video_files.append(os.path.join(root, file))
        
        if not video_files:
            print(f"在 {args.path} 中未找到视频文件")
            return
        
        video_files.sort()
        print(f"找到 {len(video_files)} 个视频文件")
        
        success_count = 0
        for video_file in video_files:
            print(f"\n处理: {os.path.basename(video_file)}")
            if extract_audio(video_file, bitrate=args.bitrate, non_interactive=args.non_interactive):
                success_count += 1
        
        print(f"\n完成: 成功处理 {success_count}/{len(video_files)} 个文件")
    else:
        # 处理单个文件
        if args.output and os.path.isdir(args.path):
            print("错误: 使用 -o 选项时，path 必须是文件而不是目录")
            sys.exit(1)
        
        success = extract_audio(args.path, args.output, args.bitrate, args.non_interactive)
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
