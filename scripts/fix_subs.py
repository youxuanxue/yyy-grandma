import os
import re
import json
import argparse
from rapidfuzz import process, fuzz

def load_entities(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Flatten all entity lists into a single list for fuzzy matching
    all_entities = []
    for key in ["characters", "relations", "locations", "terms"]:
        all_entities.extend(data.get(key, []))
    
    # Load explicit error corrections
    corrections = data.get("common_errors", {})
    
    return all_entities, corrections

def fix_subtitle_text(text, entities, corrections, threshold=85):
    """
    1. Apply explicit corrections map.
    2. Fuzzy match words against entity list.
    """
    # 1. Explicit corrections
    for error, correct in corrections.items():
        text = text.replace(error, correct)
    
    # 2. Heuristic/Fuzzy correction (Conservative)
    # This part is tricky because naive fuzzy replacement can break sentences.
    # Strategy: Scan for 2-3 character words that might be entities.
    
    # Simple regex to find potential names (2-3 chinese chars)
    # This is a heuristic and might need tuning.
    # candidates = re.findall(r'[\u4e00-\u9fa5]{2,3}', text)
    
    # for candidate in candidates:
    #     match, score, _ = process.extractOne(candidate, entities, scorer=fuzz.ratio)
    #     if score >= threshold and candidate != match:
    #         # Only replace if the context suggests it's a name? 
    #         # For now, let's just stick to the explicit map which is safer.
    #         # text = text.replace(candidate, match)
    #         pass
            
    return text

def process_srt(file_path, entities, corrections):
    output_lines = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    print(f"Fixing {file_path}...")
    fixed_count = 0
    
    for line in lines:
        # SRT text lines usually don't start with numbers (index) or contain '-->' (timestamp)
        # Note: This is a simple check; empty lines are also skipped.
        clean_line = line.strip()
        if not clean_line.isdigit() and '-->' not in clean_line and clean_line:
            original = clean_line
            fixed = fix_subtitle_text(original, entities, corrections)
            if fixed != original:
                line = line.replace(original, fixed)
                fixed_count += 1
                # print(f"  Fixed: {original} -> {fixed}")
        
        output_lines.append(line)
        
    output_path = file_path.replace(".srt", "_fixed.srt")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(output_lines)
        
    print(f"Saved fixed subtitles to {output_path} (Fixed {fixed_count} lines)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fix Whisper subtitles using entity knowledge base")
    parser.add_argument("path", help="Path to SRT file or directory")
    parser.add_argument("--entities", default="entities.json", help="Path to entities JSON file")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.entities):
        print(f"Entities file not found: {args.entities}")
        exit(1)
        
    entities, corrections = load_entities(args.entities)
    
    # Add dependency check for rapidfuzz
    try:
        import rapidfuzz
    except ImportError:
        print("Please install rapidfuzz: uv add rapidfuzz")
        exit(1)

    if os.path.isdir(args.path):
        for root, dirs, files in os.walk(args.path):
            for file in files:
                if file.endswith(".srt") and not file.endswith("_fixed.srt") and not file.endswith("_ocr.srt"):
                    process_srt(os.path.join(root, file), entities, corrections)
    else:
        process_srt(args.path, entities, corrections)
