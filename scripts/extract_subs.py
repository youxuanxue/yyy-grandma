import whisper
import os
import argparse
import time
from datetime import timedelta

def format_timestamp(seconds):
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    milliseconds = int(td.microseconds / 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def extract_subtitles(video_path, model, output_format="srt"):
    """
    Extracts subtitles using OpenAI Whisper.
    Accepts a loaded model object to avoid reloading for every file.
    """
    print(f"Transcribing {video_path}...")
    start_time = time.time()
    
    # Force initial prompt to Simplified Chinese
    result = model.transcribe(
        video_path, 
        language="zh", 
        initial_prompt="以下是简体中文的对话。",
        verbose=False 
    )
    
    base_name = os.path.splitext(video_path)[0]
    output_file = f"{base_name}.{output_format}"
    
    with open(output_file, "w", encoding="utf-8") as f:
        if output_format == "srt":
            for i, segment in enumerate(result["segments"]):
                start = format_timestamp(segment["start"])
                end = format_timestamp(segment["end"])
                text = segment["text"].strip()
                f.write(f"{i+1}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{text}\n\n")
        else:
            f.write(result["text"])
            
    end_time = time.time()
    duration = end_time - start_time
    print(f"Subtitles saved to {output_file}")
    print(f"Time taken: {duration:.2f} seconds ({duration/60:.2f} minutes)")
    
    # Log to a separate file for batch tracking
    with open("processing_log.txt", "a", encoding="utf-8") as log:
        log.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {video_path}: {duration:.2f}s ({duration/60:.2f}m)\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract subtitles from video")
    parser.add_argument("path", help="Path to video file or directory")
    parser.add_argument("--model", default="base", help="Whisper model size (tiny, base, small, medium, large)")
    args = parser.parse_args()

    # Load model ONCE outside the loop
    print(f"Loading Whisper model: {args.model}...")
    model = whisper.load_model(args.model)

    if os.path.isdir(args.path):
        # Collect all video files first
        video_files = []
        for root, dirs, files in os.walk(args.path):
            for file in files:
                if file.lower().endswith(('.mp4', '.mkv', '.avi', '.mov')):
                    video_files.append(os.path.join(root, file))
        
        # Sort files naturally (01, 02, ..., 10, 11)
        video_files.sort()
        
        for filepath in video_files:
            base_name = os.path.splitext(filepath)[0]
            expected_output = f"{base_name}.srt"
            
            if os.path.exists(expected_output):
                print(f"Skipping {os.path.basename(filepath)} (SRT already exists)")
                continue
                
            extract_subtitles(filepath, model)
    else:
        extract_subtitles(args.path, model)
