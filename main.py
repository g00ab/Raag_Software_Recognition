from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

import torch
import torch.nn.functional as F
from torchvision import transforms

import numpy as np
import librosa
import librosa.display
import matplotlib.pyplot as plt
from PIL import Image
import tempfile
import os

import torch.nn as nn
from torchvision import models
# ------------------ APP SETUP ------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ------------------ LOAD MODEL ------------------
# IMPORTANT: you must define/import your model architecture here
# from model_def import YourModelClass

# 1️⃣ Load checkpoint FIRST
checkpoint = torch.load("raag_model_full.pth", map_location=device)

CLASS_NAMES = checkpoint.get("class_names", [
    "Dharbari",
    "Gorakh_Kalyan",
    "Jog",
    "Kaushi_Kanada",
    "Yaman"
])

num_classes = len(CLASS_NAMES)

# 2️⃣ Create backbone (must match training)
model = models.resnet18(weights=None)

# 3️⃣ Replace classifier head
model.fc = nn.Sequential(
    nn.Linear(model.fc.in_features, 256),
    nn.ReLU(),
    nn.Dropout(0.4),
    nn.Linear(256, num_classes)
)

# 4️⃣ Load trained weights
model.load_state_dict(checkpoint["model_state"])

# 5️⃣ Prepare for inference
model.to(device)
model.eval()

# ------------------ YOUR MEL FUNCTION ------------------
def raag_mel_spectrogram(file_path, start_sec=0, duration=30):
    audio, sr = librosa.load(
        file_path,
        sr=22050,
        offset=start_sec,
        duration=duration
    )

    S = librosa.feature.melspectrogram(
        y=audio,
        sr=sr,
        n_fft=4096,
        hop_length=512,
        n_mels=128,
        fmin=50,
        fmax=2000
    )

    S_db = librosa.power_to_db(S, ref=np.max)
    return S_db, sr

# ------------------ SPECTROGRAM IMAGE ------------------
def spectrogram_image(file_path, start_sec=0, duration=30):
    spec, sr = raag_mel_spectrogram(file_path, start_sec, duration)

    fig = plt.figure(figsize=(10, 5))
    librosa.display.specshow(spec, sr=sr)

    fig.canvas.draw()
    buf = np.asarray(fig.canvas.buffer_rgba())
    img = Image.fromarray(buf[:, :, :3])
    plt.close(fig)
    return img

# ------------------ TRANSFORM ------------------
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

def preprocess_for_model(file_path, start_sec=0):
    img = spectrogram_image(file_path, start_sec=start_sec)
    tensor = transform(img)
    return tensor.unsqueeze(0).to(device)

# ------------------ PREDICT FUNCTION ------------------
def predict_raag(file_path):
    with torch.no_grad():
        x = preprocess_for_model(file_path)
        output = model(x)

        probs = F.softmax(output, dim=1)
        pred_idx = torch.argmax(probs, dim=1).item()
        confidence = probs[0, pred_idx].item()

    return CLASS_NAMES[pred_idx], confidence

# ------------------ API ENDPOINT ------------------
@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    # Save uploaded audio temporarily
    suffix = os.path.splitext(file.filename or "audio.wav")[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        audio_path = tmp.name

    try:
        label, conf = predict_raag(audio_path)
        return {
            "raag": label,
            "confidence": float(conf)
        }
    finally:
        try:
            os.remove(audio_path)
        except Exception:
            pass

@app.get("/")
def home():
    return {"status": "Raag API running (PyTorch)"}