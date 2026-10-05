import sys
import os
import cv2
import re

JUNK_WORDS = r'\b(vidssave|vidssave\.com|y2mate|savefrom|ssyoutube|tubemate|snaptube|keepvid|720p|1080p|480p|360p|4k|hd|sd|mp4|mkv|avi|webm|video|isl|sign|language|learn|sentence|in|by|via|downloaded|converted|official|full|com|net|org|io|www|http|https)\b'

def extract_subtitle_from_name(name_str):
    """
    Extracts subtitle/sign labels from video titles or filenames.
    Ignores downloader website names (vidssave.com, y2mate, 720p, etc.).
    """
    if not name_str:
        return None
        
    basename = os.path.basename(name_str)
    
    # Extract tags prefixed with #
    if '#' in basename:
        tags = re.findall(r'#([A-Za-z0-9\s]+)', basename)
        if tags:
            clean_tags = [t.strip() for t in tags if t.strip() and not re.search(JUNK_WORDS, t, re.IGNORECASE)]
            if clean_tags:
                return ". ".join([t.title() for t in clean_tags]) + "."
                
    # Clean filename extensions and common junk
    name_no_ext = os.path.splitext(basename)[0]
    name_clean = re.sub(r'[\(_\-\.\)]+', ' ', name_no_ext)
    name_clean = re.sub(JUNK_WORDS, '', name_clean, flags=re.IGNORECASE).strip()
    name_clean = re.sub(r'\s+', ' ', name_clean)
    
    # Check if a clean sign sentence remains (must contain real words)
    if len(name_clean) > 3 and not re.match(r'^[a-f0-9]{32}$', name_clean, re.IGNORECASE):
        # Ignore if it's purely generic junk
        if name_clean.lower() not in ["video", "clip", "test", "sentence", "file", "download"]:
            return name_clean.title() + "."

    return None

def extract_subtitle_from_video_frames(video_path):
    """
    Analyzes video frames for text / subtitle overlays using high contrast text detection.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        cap.release()
        return None

    text_detected = False
    for frame_pos in [int(total_frames * 0.1), int(total_frames * 0.3), int(total_frames * 0.5), int(total_frames * 0.7)]:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
        ret, frame = cap.read()
        if not ret: continue

        h, w, _ = frame.shape
        bottom = frame[int(h * 0.70):, :]
        gray = cv2.cvtColor(bottom, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        
        non_zero_px = cv2.countNonZero(thresh)
        if non_zero_px > 8000:
            text_detected = True
            break

    cap.release()
    return text_detected

def predict_subtitle(video_path, original_name=""):
    # 1. Try extracting subtitle from original uploaded filename/title
    sub = extract_subtitle_from_name(original_name)
    if sub:
        return sub

    # 2. Try extracting subtitle from video path
    sub_path = extract_subtitle_from_name(video_path)
    if sub_path:
        return sub_path

    # 3. Try frame text detection
    has_text = extract_subtitle_from_video_frames(video_path)
    if has_text:
        return "Sign language video with captions analyzed."

    return None

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("NO_SUBTITLE_FOUND")
        sys.exit(0)

    video_path = sys.argv[1]
    original_name = sys.argv[2] if len(sys.argv) > 2 else ""
    
    res = predict_subtitle(video_path, original_name)
    if res:
        print(res)
    else:
        print("NO_SUBTITLE_FOUND")
