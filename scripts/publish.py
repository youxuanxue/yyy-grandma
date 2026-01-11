import sys
import os
import argparse
import json
import time
from pathlib import Path

# Add script directory to sys.path to import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from wx_channel import WeChatChannelPublisher, VideoPublishTask

def main():
    parser = argparse.ArgumentParser(description="Publish short video to WeChat Channel.")
    parser.add_argument("strategy_file", help="Path to the strategy JSON file (e.g., series/jinhun/config/《金婚》第02集-Strategy.json)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode (generate screenshots and HTML dumps)")
    parser.add_argument("--real-run", action="store_true", help="Actually click the publish button (default is dry run)")
    args = parser.parse_args()

    strategy_path = Path(args.strategy_file).resolve()
    
    if not strategy_path.exists():
        print(f"❌ Error: Strategy file not found: {strategy_path}")
        return

    # Infer project structure
    # series/{series_name}/config/{filename}.json
    # Video should be in series/{series_name}/output/
    
    config_dir = strategy_path.parent
    series_root = config_dir.parent
    output_dir = series_root / "output"
    
    if not output_dir.exists():
        print(f"❌ Error: Output directory not found: {output_dir}")
        return

    # Derive video filename
    # Strategy file: 《金婚》第02集-Strategy.json
    # Video file: 《金婚》第02集-Clip.mp4
    strategy_filename = strategy_path.name
    if not strategy_filename.endswith("-Strategy.json"):
        print(f"❌ Error: Strategy file name must end with '-Strategy.json'")
        return
    
    base_name = strategy_filename.replace("-Strategy.json", "")
    video_filename = f"{base_name}-Clip.mp4"
    video_path = output_dir / video_filename
    
    if not video_path.exists():
        print(f"❌ Error: Video file not found: {video_path}")
        print(f"Please run 'produce_short_video.py' first.")
        return
    
    print(f"found video: {video_path}")

    # Load Strategy Data
    try:
        with open(strategy_path, 'r', encoding='utf-8') as f:
            strategy_data = json.load(f)
            
        wechat_strategy = strategy_data.get('wechat', {})
        
        if not wechat_strategy:
            print("❌ Error: 'wechat' strategy not found in JSON.")
            return
            
        title = wechat_strategy.get('title', '')
        description = wechat_strategy.get('description', '')
        hashtags = wechat_strategy.get('hashtags', [])
        pinned_comment = wechat_strategy.get('pinned_comment', '')
        
        # Combine description and hashtags
        full_description = description
        if hashtags:
            full_description += "\n\n" + " ".join(hashtags)
            
        # Add pinned comment suggestion to description (or just log it, as we can't auto-pin comments easily yet)
        # Usually pinning comments is done after publishing. 
        # We can append it to description as a prompt for now or just ignore it for the automation.
        # But wait, WeChat Channel description doesn't support pinning. Pinning is a comment action.
        # So we just ignore pinned_comment for the main publish task.
        
        if len(title) > 30: # WeChat might have a title limit? Adjust as needed.
             print(f"⚠️ Warning: Title might be too long: {len(title)} chars. Please check.")

    except Exception as e:
        print(f"❌ Error reading strategy file: {e}")
        return

    # Initialize Publisher
    # We store auth_wx.json in the project root or a specific config folder
    auth_path = Path(".").resolve() # Current working directory (project root)
    
    print("🚀 Starting WeChat Channel Publisher...")
    print(f"Title: {title}")
    print(f"Description length: {len(full_description)}")
    
    try:
        with WeChatChannelPublisher(headless=False, auth_path=str(auth_path), debug=args.debug) as publisher:
            publisher.login()
            
            task = VideoPublishTask(
                video_path=video_path,
                title=title,
                description=full_description
            )
            
            publisher.publish(task)
            
            if args.real_run:
                # TODO: Implement actual click in wx_channel.py if not already there
                # Currently wx_channel.py is set to DRY RUN by default in code logic.
                # If we want to support real run, we need to modify wx_channel.py or handle it here.
                # For now, let's keep it as is, asking user to confirm.
                print("✅ 自动化操作完成。请在浏览器中手动点击'发表'按钮。")
            else:
                print("ℹ️ Dry run mode. No publish action taken.")
            
            print("脚本将保持浏览器打开，直到您关闭它或按回车键...")
            try:
                input("Press Enter to finish and close browser...")
            except:
                time.sleep(300)

    except Exception as e:
        print(f"❌ Publish failed: {e}")

if __name__ == "__main__":
    main()
