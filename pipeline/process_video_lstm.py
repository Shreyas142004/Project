import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
import warnings
warnings.filterwarnings('ignore')

import sys
import cv2
import mediapipe as mp
import numpy as np
import json
from tensorflow.keras.models import load_model

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, 'models')

def get_model_path(filename):
    p = os.path.join(MODELS_DIR, filename)
    return p if os.path.exists(p) else filename

def match_fast_dataset_means(sequence):
    """
    Compares active hand sequence features against stored sign patterns in models/dataset_means.json.
    Strict distance threshold (< 0.12) prevents false matches on unrelated videos.
    """
    means_file = get_model_path('dataset_means.json')
    if not os.path.exists(means_file):
        return None, float('inf')

    try:
        with open(means_file, 'r') as f:
            means_dict = json.load(f)
    except Exception:
        return None, float('inf')

    seq_arr = np.array(sequence)
    nonzero_mask = np.count_nonzero(seq_arr, axis=1) > 0
    active_frames = seq_arr[nonzero_mask]

    if len(active_frames) == 0:
        return None, float('inf')

    active_mean = np.mean(active_frames, axis=0)

    best_class = None
    min_dist = float('inf')

    for class_id_str, ref_vec in means_dict.items():
        ref_arr = np.array(ref_vec)
        if len(ref_arr) == len(active_mean):
            dist = float(np.linalg.norm(active_mean - ref_arr))
            if dist < min_dist:
                min_dist = dist
                best_class = int(class_id_str)

    # Require strict match threshold (0.12) to avoid false positive matches
    if best_class is not None and min_dist < 0.12:
        return best_class, min_dist

    return None, min_dist

def process_video(video_path):
    # Load labels dictionary
    try:
        labels_file = get_model_path('lstm_labels.json')
        if not os.path.exists(labels_file):
            labels_file = get_model_path('labels.json')
        with open(labels_file, 'r') as f:
            labels_dict = {int(k): v for k, v in json.load(f).items()}
    except Exception:
        labels_dict = {}

    # Extract Video Landmarks using MediaPipe
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("UNCERTAIN")
        return

    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(static_image_mode=False, min_detection_confidence=0.5)

    sequence = []
    detected_hand_frames = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(frame_rgb)

        data_aux = []
        x_ = []
        y_ = []
        
        if results.multi_hand_landmarks:
            detected_hand_frames += 1
            hand_landmarks = results.multi_hand_landmarks[0]
            for i in range(len(hand_landmarks.landmark)):
                x_.append(hand_landmarks.landmark[i].x)
                y_.append(hand_landmarks.landmark[i].y)

            for i in range(len(hand_landmarks.landmark)):
                data_aux.append(hand_landmarks.landmark[i].x - min(x_))
                data_aux.append(hand_landmarks.landmark[i].y - min(y_))
        else:
            data_aux = list(np.zeros(42))

        sequence.append(data_aux)

    cap.release()
    hands.close()

    if detected_hand_frames == 0 or not sequence:
        print("NO_HANDS_DETECTED")
        return

    # 1. Check strict matching against stored sign patterns in dataset_means.json
    template_class, dist = match_fast_dataset_means(sequence)
    if template_class is not None and template_class in labels_dict:
        raw_word = labels_dict[template_class]
        raw_word = raw_word.split('. ')[-1] if '. ' in raw_word else raw_word
        print(raw_word)
        return

    # 2. Evaluate neural network model if available (ignore single biased class 49 & class 76 unless exact match)
    try:
        model_path = get_model_path('lstm_model_custom.h5')
        if not os.path.exists(model_path):
            model_path = get_model_path('lstm_model.h5')
        if os.path.exists(model_path):
            model = load_model(model_path)
            padded_seq = sequence[-60:]
            while len(padded_seq) < 60:
                padded_seq.insert(0, list(np.zeros(42)))
            
            res = model.predict(np.expand_dims(padded_seq, axis=0), verbose=0)[0]
            confidence = float(np.max(res))
            predicted_idx = int(np.argmax(res))
            
            if confidence >= 0.75 and predicted_idx in labels_dict and predicted_idx not in [49, 76]:
                word = labels_dict[predicted_idx]
                word = word.split('. ')[-1] if '. ' in word else word
                print(word)
                return
    except Exception:
        pass

    print("UNCERTAIN")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(0)
    
    video_path = sys.argv[1]
    process_video(video_path)
