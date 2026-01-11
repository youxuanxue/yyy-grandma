import opencc
import argparse
import os

def convert_to_simplified(text):
    converter = opencc.OpenCC('t2s')
    return converter.convert(text)

def process_srt(file_path):
    print(f"Converting {file_path} to Simplified Chinese...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    output_lines = []
    converted_count = 0
    
    for line in lines:
        # Simple check to only convert text lines (not index or timestamp)
        clean_line = line.strip()
        if not clean_line.isdigit() and '-->' not in clean_line and clean_line:
            simplified = convert_to_simplified(line)
            if simplified != line:
                converted_count += 1
            output_lines.append(simplified)
        else:
            output_lines.append(line)
            
    # Overwrite the original file or save as new
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(output_lines)
        
    print(f"Converted {converted_count} lines.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert SRT subtitles from Traditional to Simplified Chinese")
    parser.add_argument("path", help="Path to SRT file or directory")
    
    args = parser.parse_args()
    
    if os.path.isdir(args.path):
        for root, dirs, files in os.walk(args.path):
            for file in files:
                if file.endswith(".srt"):
                    process_srt(os.path.join(root, file))
    else:
        process_srt(args.path)
