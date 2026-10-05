import sys
import os
import cv2
import json
import numpy as np
import mediapipe as mp
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, 'models')
DATASET_DIR = os.path.join(BASE_DIR, 'lstm_dataset')
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(DATASET_DIR, exist_ok=True)

labels_path = os.path.join(MODELS_DIR, 'lstm_labels.json')
words_path = os.path.join(MODELS_DIR, 'words.json')
means_path = os.path.join(MODELS_DIR, 'dataset_means.json')

def load_or_init_labels():
    if os.path.exists(labels_path):
        with open(labels_path, 'r') as f:
            labels_dict = json.load(f)
            return {int(k): v for k, v in labels_dict.items()}
    else:
        return {0: "HELLO", 1: "THANK_YOU", 2: "PLEASE", 3: "HELP"}

def save_labels(labels_dict):
    with open(labels_path, 'w') as f:
        json.dump(labels_dict, f, indent=2)
    
    words_list = [labels_dict[i] for i in sorted(labels_dict.keys())]
    with open(words_path, 'w') as f:
        json.dump(words_list, f, indent=2)

def update_dataset_means(class_id, landmarks_seq):
    means_dict = {}
    if os.path.exists(means_path):
        try:
            with open(means_path, 'r') as f:
                means_dict = json.load(f)
        except Exception:
            means_dict = {}

    seq_arr = np.array(landmarks_seq)
    nonzero_mask = np.count_nonzero(seq_arr, axis=1) > 0
    active_frames = seq_arr[nonzero_mask]
    
    if len(active_frames) > 0:
        mean_vec = np.mean(active_frames, axis=0).tolist()
        means_dict[str(class_id)] = mean_vec
        with open(means_path, 'w') as f:
            json.dump(means_dict, f, indent=2)
        print(f"[AUTO-LEARN] Updated landmark pattern vector in dataset_means.json for class {class_id}")

def extract_landmarks_from_video(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error opening video {video_path}", file=sys.stderr)
        return []

    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.5)

    sequence = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(frame_rgb)

        data_aux = []
        x_, y_ = [], []

        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]
            for lm in hand_landmarks.landmark:
                x_.append(lm.x)
                y_.append(lm.y)

            min_x = min(x_)
            min_y = min(y_)
            for lm in hand_landmarks.landmark:
                data_aux.append(lm.x - min_x)
                data_aux.append(lm.y - min_y)
        else:
            data_aux = [0.0] * 42

        sequence.append(data_aux)

    cap.release()
    hands.close()

    if not sequence:
        return []

    sequence = sequence[-60:]
    while len(sequence) < 60:
        sequence.insert(0, [0.0] * 42)

    return sequence

def learn_sign(video_path, target_word):
    target_word = target_word.strip().upper().replace(' ', '_')
    if not target_word:
        print("Invalid target word")
        return

    labels_dict = load_or_init_labels()
    
    class_id = None
    for k, v in labels_dict.items():
        if v.upper() == target_word:
            class_id = k
            break
            
    if class_id is None:
        class_id = len(labels_dict)
        labels_dict[class_id] = target_word
        save_labels(labels_dict)
        print(f"[AUTO-LEARN] Registered new sign label: '{target_word}' (Class ID: {class_id})")
    else:
        print(f"[AUTO-LEARN] Using existing sign label for '{target_word}' (Class ID: {class_id})")

    # Extract Landmarks from Video
    landmarks_seq = extract_landmarks_from_video(video_path)
    if landmarks_seq:
        update_dataset_means(class_id, landmarks_seq)

    # Save sequence frame images
    word_dir = os.path.join(DATASET_DIR, str(class_id))
    os.makedirs(word_dir, exist_ok=True)

    existing_seqs = [d for d in os.listdir(word_dir) if os.path.isdir(os.path.join(word_dir, d))]
    next_seq_id = len(existing_seqs)
    seq_dir = os.path.join(word_dir, str(next_seq_id))
    os.makedirs(seq_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret or frame_idx >= 60:
            break
        frame_path = os.path.join(seq_dir, f"{frame_idx}.jpg")
        cv2.imwrite(frame_path, frame)
        frame_idx += 1
    cap.release()

    if frame_idx < 60 and frame_idx > 0:
        last_frame_path = os.path.join(seq_dir, f"{frame_idx-1}.jpg")
        last_frame = cv2.imread(last_frame_path)
        while frame_idx < 60:
            frame_path = os.path.join(seq_dir, f"{frame_idx}.jpg")
            cv2.imwrite(frame_path, last_frame)
            frame_idx += 1

    print(f"[AUTO-LEARN] Stored sign pattern for '{target_word}' (Class {class_id}, Seq {next_seq_id}).")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python learn_from_video.py <video_path> <sign_label>")
        sys.exit(1)
        
    video_path = sys.argv[1]
    sign_label = sys.argv[2]
    learn_sign(video_path, sign_label)
