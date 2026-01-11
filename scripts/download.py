import sys
import os
import yt_dlp

def process_playlist(url, output_path="downloads"):
    # 1. Extract Info (Get URLs)
    print(f"正在解析播放列表信息: {url}")
    
    # Configuration to just extract information without downloading
    extract_opts = {
        'extract_flat': 'in_playlist', # Just get video IDs/Titles from playlist
        'quiet': True,
        'ignoreerrors': True,
    }

    video_urls = []
    
    with yt_dlp.YoutubeDL(extract_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            
            if 'entries' in info:
                print(f"\n成功解析! 共找到 {len(info['entries'])} 集:")
                for entry in info['entries']:
                    # yt-dlp extract_flat returns 'url' as the video ID usually, or full URL depending on extractor
                    # For YouTube, it's usually just the ID or relative URL. 
                    # We can construct the full URL to be safe or use what's provided if it looks like a URL.
                    v_url = entry.get('url')
                    if v_url and not v_url.startswith('http'):
                         v_url = f"https://www.youtube.com/watch?v={v_url}"
                    
                    title = entry.get('title', 'Unknown Title')
                    print(f"- [{title}]({v_url})")
                    video_urls.append(v_url)
            else:
                # It's a single video
                print(f"\nFound single video: {info.get('title')}")
                video_urls.append(info.get('webpage_url', url))
                
        except Exception as e:
            print(f"解析出错: {e}")
            return

    # 2. Download
    if not video_urls:
        print("未找到视频链接。")
        return

    print(f"\n开始下载全部 {len(video_urls)} 集视频到 '{output_path}' 目录...")
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # Configuration for downloading
    download_opts = {
        'format': 'best', # Download best quality
        'outtmpl': f'{output_path}/%(title)s.%(ext)s',
        'ignoreerrors': True,
        # 'writethumbnail': True, 
    }

    with yt_dlp.YoutubeDL(download_opts) as ydl:
        # We can pass the playlist URL directly to download everything, 
        # but passing the list of URLs we found gives us more control if we wanted to filter.
        # However, passing the original playlist URL is often more robust for yt-dlp.
        # Let's pass the extracted URLs to be explicit as per user request to "get URLs then download"
        ydl.download(video_urls)
    
    print("\n所有下载任务完成！")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("请提供链接作为参数。用法: uv run scripts/download.py <url> [output_path]")
    else:
        url = sys.argv[1]
        output_path = sys.argv[2] if len(sys.argv) > 2 else "downloads"
        process_playlist(url, output_path)
