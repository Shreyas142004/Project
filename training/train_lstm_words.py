import os
import sys
import cv2
import numpy as np
import mediapipe as mp
import json
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.utils import to_categorical
from sklearn.model_selection import train_test_split

print("Step 1: Extracting landmarks from collected video sequences...")

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=2, min_detection_confidence=0.5)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, 'models')
DATA_DIR = os.path.join(BASE_DIR, 'lstm_dataset')
no_sequences = 30
sequence_length = 60
labels_path = os.path.join(MODELS_DIR, 'lstm_labels.json') if os.path.exists(os.path.join(MODELS_DIR, 'lstm_labels.json')) else 'lstm_labels.json'

# Load labels
with open(labels_path, 'r') as f:
    labels_dict = {int(k): v for k, v in json.load(f).items()}
num_classes = len(labels_dict)

sequences, labels = [], []

for word_idx in range(num_classes):
    word_dir = os.path.join(DATA_DIR, str(word_idx))
    if not os.path.exists(word_dir):
        continue
        
    sequence_folders = [d for d in os.listdir(word_dir) if os.path.isdir(os.path.join(word_dir, d))]
    for sequence in sequence_folders:
        window = []
        sequence_dir = os.path.join(word_dir, sequence)
        if not os.path.exists(sequence_dir):
            continue
            
        for frame_num in range(sequence_length):
            img_path = os.path.join(sequence_dir, f'{frame_num}.jpg')
            img = cv2.imread(img_path)
            if img is None:
                window.append(list(np.zeros(42)))
                continue
                
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = hands.process(img_rgb)
            
            data_aux = []
            x_ = []
            y_ = []
            
            if results.multi_hand_landmarks:
                hand_landmarks = results.multi_hand_landmarks[0]
                for i in range(len(hand_landmarks.landmark)):
                    x_.append(hand_landmarks.landmark[i].x)
                    y_.append(hand_landmarks.landmark[i].y)
                
                for i in range(len(hand_landmarks.landmark)):
                    data_aux.append(hand_landmarks.landmark[i].x - min(x_))
                    data_aux.append(hand_landmarks.landmark[i].y - min(y_))
            
            if len(data_aux) != 42:
                data_aux = list(np.zeros(42))
                
            window.append(data_aux)
            
        if len(window) == sequence_length:
            sequences.append(window)
            labels.append(word_idx)

print(f"Extracted features for {len(sequences)} original video sequences.")

# --- DATA AUGMENTATION ---
print("Applying Data Augmentation to prevent overfitting...")
augmented_sequences = []
augmented_labels = []

for seq, label in zip(sequences, labels):
    augmented_sequences.append(seq)
    augmented_labels.append(label)
    
    for _ in range(4):
        noise = np.random.normal(0, 0.02, (sequence_length, 42))
        noisy_seq = np.array(seq) + noise
        augmented_sequences.append(noisy_seq.tolist())
        augmented_labels.append(label)

sequences = augmented_sequences
labels = augmented_labels
print(f"Dataset expanded to {len(sequences)} sequences via augmentation.")
# -------------------------

if len(sequences) == 0:
    print("\n[INFO] No sequences found in dataset yet. Skipped training.")
    sys.exit(0)

print("\nStep 2: Training the LSTM Neural Network...")
X = np.array(sequences)
y = to_categorical(labels, num_classes=num_classes).astype(int)

if len(sequences) >= 10:
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1)
else:
    X_train, X_test, y_train, y_test = X, X, y, y

# Build LSTM Architecture
model = Sequential()
model.add(LSTM(64, return_sequences=True, activation='relu', input_shape=(sequence_length, 42)))
model.add(LSTM(128, return_sequences=True, activation='relu'))
model.add(LSTM(64, return_sequences=False, activation='relu'))
model.add(Dense(64, activation='relu'))
model.add(Dense(32, activation='relu'))
model.add(Dense(num_classes, activation='softmax'))

model.compile(optimizer='Adam', loss='categorical_crossentropy', metrics=['categorical_accuracy'])

early_stopping = EarlyStopping(monitor='loss', patience=10, restore_best_weights=True)

model.fit(X_train, y_train, epochs=20, batch_size=16)

print("\nStep 3: Evaluating Model...")
loss, accuracy = model.evaluate(X_test, y_test)
print(f"Test Accuracy: {accuracy * 100:.2f}%")

# Save the model
save_model_path = os.path.join(MODELS_DIR, 'lstm_model_custom.h5')
model.save(save_model_path)
print(f"Saved neural network to '{save_model_path}'")
print("\nSuccess! Your Advanced LSTM Model is fully trained.")
