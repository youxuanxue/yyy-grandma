import sys
import os
import subprocess
import json
import time
import re

# 配置
FONT_PATH = "/System/Library/Fonts/STHeiti Medium.ttc"

def run_cmd(cmd):
    max_retries = 3
    for i in range(max_retries):
        try:
            result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
            if result.returncode == 0:
                return True
            else:
                print(f"⚠️ Warning (Attempt {i+1}): Command failed.")
                print(f"Command: {' '.join(cmd)}")
                print(f"Error output:\n{result.stderr[-1000:]}") # Print last 1000 chars
                time.sleep(1) 
        except Exception as e:
            print(f"❌ Exception: {e}")
            return False
    print(f"❌ Failed after {max_retries} attempts.")
    return False

def process_clip(clip_data, video_path, temp_dir, font_path, avatar_path=None):
    clip_id = clip_data["id"]
    start = clip_data["time_range"]["start"]
    end = clip_data["time_range"]["end"]
    title = clip_data["title"]
    commentary = clip_data["commentary_text"]
    
    raw_clip_path = os.path.join(temp_dir, f"{clip_id}_raw.mp4")
    final_clip_path = os.path.join(temp_dir, f"{clip_id}_vertical.mp4")
    
    # 检查如果目标文件已存在且大小正常，则跳过（断点续传）
    if os.path.exists(final_clip_path) and os.path.getsize(final_clip_path) > 1000:
        print(f"⏩ 跳过已存在的片段: {title}")
        return final_clip_path

    print(f"🎬 处理片段: {title} ({start}-{end})...")

    # 1. 提取片段 (精确剪辑)
    extract_cmd = [
        "ffmpeg", "-ss", start, "-to", end, "-i", video_path,
        "-c:v", "libx264", "-c:a", "aac", "-y", raw_clip_path
    ]
    if not run_cmd(extract_cmd): return None

    # 2. 转竖屏 + 双字幕布局
    def escape_text(t):
        t = t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "'\\''")
        return t
    
    title_safe = escape_text(title)
    
    MAX_CHARS_PER_LINE = 16 # 缩减一点，给头像留位置
    
    processed_lines = []
    original_lines = commentary.split('\n')
    for line in original_lines:
        current_line = ""
        count = 0
        for char in line:
            char_len = 1 if ord(char) > 127 else 0.5
            if count + char_len > MAX_CHARS_PER_LINE:
                processed_lines.append(current_line)
                current_line = char
                count = char_len
            else:
                current_line += char
                count += char_len
        if current_line:
            processed_lines.append(current_line)
            
    draw_cmds = []
    
    # 标题命令
    draw_cmds.append(
        f"drawtext=fontfile='{font_path}':text='{title_safe}':"
        "fontcolor=yellow:fontsize=80:"
        "x=(w-text_w)/2:y=350:"
        "borderw=4:bordercolor=black:"
        "shadowx=4:shadowy=4"
    )

    # 解说命令 (多行) - 调整位置给头像
    base_y = 1420
    line_height = 80
    
    for i, line in enumerate(processed_lines):
        line_safe = escape_text(line)
        current_y = base_y + (i * line_height)
        
        # 如果有头像，文字左对齐，否则居中
        if avatar_path:
            x_pos = 260 
        else:
            x_pos = "(w-text_w)/2"
            
        cmd = (
            f"drawtext=fontfile='{font_path}':text='{line_safe}':"
            "fontcolor=yellow:fontsize=50:"
            f"x={x_pos}:y={current_y}:"
            "borderw=2:bordercolor=black"
        )
        draw_cmds.append(cmd)
    
    draw_text_filter = ",".join(draw_cmds)
    
    # 气泡背景高度计算
    bubble_h = max(160, len(processed_lines) * line_height + 60)
    
    avatar_filter = ""
    if avatar_path and os.path.exists(avatar_path):
        # 1. 基础背景
        # 2. 绘制半透明气泡框
        # 3. 处理头像 (缩放 + 圆形裁剪)
        # 4. 叠加头像
        avatar_filter = (
            f"drawbox=y=1380:x=80:w=920:h={bubble_h}:color=black@0.5:t=fill[with_bubble];"
            f"[1:v]scale=120:120,format=rgba,geq=lum='p(X,Y)':a='if(gt(sqrt(pow(X-60,2)+pow(Y-60,2)),60),0,255)'[avatar_round];"
            f"[with_bubble][avatar_round]overlay=110:1410[with_avatar];"
            f"[with_avatar]{draw_text_filter}[outv]"
        )
    else:
        avatar_filter = f"{draw_text_filter}[outv]"

    filter_complex = (
        "[0:v]split=2[bg][main];"
        "[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:10[bg_blurred];"
        "[main]scale=1080:-1[main_scaled];"
        f"[bg_blurred][main_scaled]overlay=0:(H-h)/2[merged];"
        f"[merged]{avatar_filter}"
    )

    convert_cmd = [
        "ffmpeg", "-i", raw_clip_path
    ]
    if avatar_path and os.path.exists(avatar_path):
        convert_cmd.extend(["-i", avatar_path])
        
    convert_cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "0:a",
        "-c:v", "libx264", "-c:a", "aac", "-y", final_clip_path
    ])
    
    if run_cmd(convert_cmd):
        return final_clip_path
    return None

def merge_final(clips_paths, output_dir, final_filename, temp_dir):
    list_path = os.path.join(temp_dir, "merge_list.txt")
    with open(list_path, "w", encoding="utf-8") as f:
        for p in clips_paths:
            abs_path = os.path.abspath(p).replace("\\", "/")
            f.write(f"file '{abs_path}'\n")
            
    output_path = os.path.join(output_dir, final_filename)
    print(f"🚀 正在合并最终视频...")
    
    merge_cmd = [
        "ffmpeg", "-f", "concat", "-safe", "0", "-i", list_path,
        "-c", "copy", "-y", output_path
    ]
    
    if run_cmd(merge_cmd):
        print(f"✅✅✅ 任务完成！文件位置: {output_path}")
    else:
        print("❌ 合并失败")

def main():
    if len(sys.argv) < 2:
        print("用法: uv run scripts/produce_short_video.py <config_file_path>")
        print("示例: uv run scripts/produce_short_video.py series/jinhun/config/《金婚》第01集-Strategy.json")
        sys.exit(1)

    config_file_path = os.path.abspath(sys.argv[1])
    
    if not os.path.exists(config_file_path):
        print(f"❌ 错误: 找不到策略文件: {config_file_path}")
        sys.exit(1)

    # 推断目录结构
    # 假设结构: series/jinhun/config/xxx.json
    # series_root = series/jinhun
    config_dir = os.path.dirname(config_file_path)
    series_root = os.path.dirname(config_dir) 
    
    # 检查是否符合预期结构 (series_root 下应有 downloads)
    downloads_dir = os.path.join(series_root, "downloads")
    if not os.path.exists(downloads_dir):
        # 尝试回退到旧结构或当前目录
        print(f"⚠️ 未检测到标准目录结构 (series/xxx/config), 尝试使用 config 文件同级或上级目录...")
        series_root = os.path.dirname(config_dir) if os.path.basename(config_dir) == "config" else config_dir
        downloads_dir = os.path.join(series_root, "downloads")

    output_dir = os.path.join(series_root, "output")
    temp_dir = os.path.join(series_root, "temp_clips")

    # 从文件名推断视频文件名
    # config_basename: 《金婚》第01集-Strategy
    config_basename = os.path.splitext(os.path.basename(config_file_path))[0]
    # video_basename: 《金婚》第01集
    video_basename = config_basename.replace("-Strategy", "")
    
    video_path = os.path.join(downloads_dir, f"{video_basename}.mp4")
    final_filename = f"{video_basename}-Clip.mp4"

    if not os.path.exists(video_path):
        print(f"❌ 错误: 找不到视频源文件: {video_path}")
        # 尝试查找其他后缀
        for ext in [".mkv", ".avi", ".mov"]:
            p = os.path.join(downloads_dir, f"{video_basename}{ext}")
            if os.path.exists(p):
                video_path = p
                print(f"✅ 找到替代视频文件: {video_path}")
                break
        else:
             sys.exit(1)

    # 确保目录存在
    for d in [output_dir, temp_dir]:
        if not os.path.exists(d):
            os.makedirs(d)

    print(f"📂 工作目录: {series_root}")
    print(f"📄 策略文件: {config_file_path}")
    print(f"🎥 视频源: {video_path}")
    print(f"💾 输出目录: {output_dir}")

    # 尝试查找头像
    avatar_path = os.path.join(series_root, "images", "1.jpg")
    if not os.path.exists(avatar_path):
        avatar_path = None
    else:
        print(f"👤 找到头像: {avatar_path}")

    # 加载策略数据
    with open(config_file_path, "r", encoding="utf-8") as f:
        strategy_data = json.load(f)

    valid_clips = []
    # 按JSON中的顺序处理
    for clip in strategy_data["clips"]:
        res = process_clip(clip, video_path, temp_dir, FONT_PATH, avatar_path)
        if res:
            valid_clips.append(res)
            
    if valid_clips:
        merge_final(valid_clips, output_dir, final_filename, temp_dir)
    else:
        print("❌ 没有生成任何有效片段")

if __name__ == "__main__":
    main()