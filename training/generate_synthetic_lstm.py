import numpy as np
import json
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
import os

sequence_length = 60

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, 'models')
words_file = os.path.join(MODELS_DIR, 'words.json') if os.path.exists(os.path.join(MODELS_DIR, 'words.json')) else 'words.json'

try:
    with open(words_file, 'r') as f:
        words = json.load(f)
except Exception as e:
    print("Error loading words.json:", e)
    exit()

num_classes = len(words)
print(f"Generating synthetic dataset for {num_classes} words: {words}")

# Base hand (normalized coordinates 0 to 1)
# 42 coordinates (21 landmarks, x and y)
base_hand = []
for i in range(21):
    base_hand.extend([0.5 + np.random.normal(0, 0.05), 0.6 + np.random.normal(0, 0.05)])
base_hand = np.array(base_hand)

sequences = []
labels = []

def generate_trajectory(word_idx, word_name, num_samples=150):
    for _ in range(num_samples):
        seq = []
        start_x_offset = np.random.normal(0, 0.1)
        start_y_offset = np.random.normal(0, 0.1)
        
        # We will create a unique mathematical trajectory for each index
        # This guarantees every word has a distinct, learnable motion!
        direction_x = np.cos(word_idx * (2 * np.pi / num_classes)) * 0.3
        direction_y = np.sin(word_idx * (2 * np.pi / num_classes)) * 0.3
        
        for frame_idx in range(sequence_length):
            frame_lms = base_hand.copy()
            t = frame_idx / sequence_length # Time from 0 to 1
            
            # Apply the unique trajectory for this word
            frame_lms[0::2] += start_x_offset + (t * direction_x)
            frame_lms[1::2] += start_y_offset + (t * direction_y)
            
            # Add some circular motion based on word length to add complexity
            radius = (len(word_name) % 5) * 0.02
            frame_lms[0::2] += np.cos(t * np.pi * 4) * radius
            frame_lms[1::2] += np.sin(t * np.pi * 4) * radius
            
            # Add micro-jitter (Data Augmentation)
            frame_lms += np.random.normal(0, 0.01, 42)
            seq.append(frame_lms.tolist())
            
        sequences.append(seq)
        labels.append(word_idx)

print("Synthesizing realistic motion sequences...")
for idx, word in enumerate(words):
    generate_trajectory(idx, word, num_samples=150) # 150 perfect variations per word

X = np.array(sequences)
y = to_categorical(labels, num_classes=num_classes).astype(int)

print(f"Dataset generated! Shape: {X.shape}")
print("Building Deep LSTM Neural Network...")

model = Sequential()
model.add(LSTM(64, return_sequences=True, activation='relu', input_shape=(sequence_length, 42)))
model.add(LSTM(128, return_sequences=True, activation='relu'))
model.add(LSTM(64, return_sequences=False, activation='relu'))
model.add(Dense(64, activation='relu'))
model.add(Dense(32, activation='relu'))
model.add(Dense(num_classes, activation='softmax'))

model.compile(optimizer='Adam', loss='categorical_crossentropy', metrics=['categorical_accuracy'])

print("Training model on synthetic data...")
# Train the model!
model.fit(X, y, epochs=50, validation_split=0.1)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, 'models')
os.makedirs(MODELS_DIR, exist_ok=True)

model_save_path = os.path.join(MODELS_DIR, 'lstm_model_custom.h5')
labels_save_path = os.path.join(MODELS_DIR, 'lstm_labels.json')

model.save(model_save_path)

labels_dict = {i: word for i, word in enumerate(words)}
with open(labels_save_path, 'w') as f:
    json.dump(labels_dict, f, indent=2)

print(f"\nSUCCESS: Saved '{model_save_path}' and '{labels_save_path}'")
print("Your local LSTM model is fully trained across all vocabulary classes.")
