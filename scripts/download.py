import sys
import os
import yt_dlp
import re

def extract_episode_filename(title):
    """
    从标题中提取集数并生成规范文件名
    例如: "《金婚》第01集..." -> "jinhun01"
    """
    # 匹配 "《金婚》第01集" 或 "《金婚》第1集"
    match = re.search(r'《金婚》第(\d+)集', title)
    if match:
        num = int(match.group(1))
        return f"jinhun{num:02d}"
    return None

def process_playlist(url, output_path="downloads"):
    # 1. Extract Info (Get URLs)
    print(f"正在解析播放列表信息: {url}")
    
    # Configuration to just extract information without downloading
    extract_opts = {
        'extract_flat': 'in_playlist', # Just get video IDs/Titles from playlist
        'quiet': True,
        'ignoreerrors': True,
    }

    video_items = [] # List of (url, title)
    
    with yt_dlp.YoutubeDL(extract_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            
            if 'entries' in info:
                print(f"\n成功解析! 共找到 {len(info['entries'])} 集:")
                for entry in info['entries']:
                    v_url = entry.get('url')
                    if v_url and not v_url.startswith('http'):
                         v_url = f"https://www.youtube.com/watch?v={v_url}"
                    
                    title = entry.get('title', 'Unknown Title')
                    print(f"- [{title}]({v_url})")
                    video_items.append((v_url, title))
            else:
                # It's a single video
                title = info.get('title', 'Unknown Title')
                print(f"\nFound single video: {title}")
                v_url = info.get('webpage_url', url)
                video_items.append((v_url, title))
                
        except Exception as e:
            print(f"解析出错: {e}")
            return

    # 2. Download
    if not video_items:
        print("未找到视频链接。")
        return

    print(f"\n开始下载全部 {len(video_items)} 集视频到 '{output_path}' 目录...")
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # 逐个下载以应用自定义文件名
    for i, (v_url, title) in enumerate(video_items):
        filename_base = extract_episode_filename(title)
        
        # 如果无法提取集数，使用原始标题
        if not filename_base:
            print(f"[{i+1}/{len(video_items)}] 无法提取集数，使用原始标题: {title}")
            outtmpl = f'{output_path}/%(title)s.%(ext)s'
        else:
            print(f"[{i+1}/{len(video_items)}] 识别为: {filename_base} ({title})")
            outtmpl = f'{output_path}/{filename_base}.%(ext)s'

        # Configuration for downloading
        download_opts = {
            'format': 'best', # Download best quality
            'outtmpl': outtmpl,
            'ignoreerrors': True,
            # Skip if file already exists
            'nooverwrites': True,
            'download_archive': os.path.join(output_path, 'downloaded.txt'), # Record downloaded IDs
        }

        # 另外检查目标文件是否已存在（不仅依赖 archive，也检查实际文件）
        # 这一步对于重命名后的文件很重要
        # yt-dlp 会自动处理，但为了双重保险
        
        try:
            with yt_dlp.YoutubeDL(download_opts) as ydl:
                ydl.download([v_url])
        except Exception as e:
            print(f"下载失败 {title}: {e}")
            continue
    
    print("\n所有下载任务完成！")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("请提供链接作为参数。用法: uv run scripts/download.py <url> [output_path]")
    else:
        url = sys.argv[1]
        output_path = sys.argv[2] if len(sys.argv) > 2 else "downloads"
        process_playlist(url, output_path)
