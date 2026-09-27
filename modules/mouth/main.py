#!/usr/bin/env python3
#
# Copyright 2026 Thierry VIEIL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# ==============================================================================
# PROJET NATACHA - Natacha Mouth-XTTS-V2
# ==============================================================================

import os
import re
import time
import uuid
import queue
import wave
import threading
import subprocess
import contextlib

import torch
import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from TTS.api import TTS

import numpy as np
from scipy.io import wavfile

import base64
import json

START_TIME = time.time()

# 1. Configuration
load_dotenv()

class Config:
    MQTT_BROKER = os.getenv("MQTT_BROKER", "192.168.1.100")
    MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
    OREILLE_IP = os.getenv("OREILLE_IP", "192.168.1.90")
    
    SPEAKER_WAV = os.getenv("SPEAKER_WAV_PATH", "data/voix_thierry_pro.wav")
    DEVICE = os.getenv("TORCH_DEVICE", "cuda") if torch.cuda.is_available() else "cpu"
    
    DATA_IN_DIR = "data_in"
    ENABLE_STREAMING = os.getenv("ENABLE_STREAMING", "True") == "True"

os.makedirs(Config.DATA_IN_DIR, exist_ok=True)
audio_queue = queue.Queue()


def envoyer_audio_dashboard(client_mqtt, file_path):
    """Lit un fichier WAV, le convertit en Base64 et l'envoie sur MQTT."""
    try:
        if not os.path.exists(file_path):
            return

        with open(file_path, "rb") as f:
            audio_encoded = base64.b64encode(f.read()).decode("utf-8")

        payload = json.dumps({
            "filename": os.path.basename(file_path),
            "mime": "audio/wav",
            "data": audio_encoded
        })

        client_mqtt.publish("natacha/dashboard/audio", payload, qos=0)
        print(f"📡 Audio envoyé au dashboard via MQTT ({len(audio_encoded) // 1024} Ko)")

    except Exception as e:
        print(f"⚠️ Erreur lors de l'envoi Base64 MQTT : {e}")


def remove_pop(file_path, fade_in_ms=60, fade_out_ms=20):
    """Applique un micro fondu en entrée (fade-in) et en sortie (fade-out)."""
    try:
        sample_rate, data = wavfile.read(file_path)
        total_samples = len(data)
        
        fade_in_len = int(sample_rate * (fade_in_ms / 1000.0))
        if total_samples > fade_in_len and fade_in_len > 0:
            fade_in = np.linspace(0.0, 1.0, fade_in_len)
            if data.ndim == 1:
                data[:fade_in_len] = (data[:fade_in_len] * fade_in).astype(data.dtype)
            else:
                data[:fade_in_len, :] = (data[:fade_in_len, :] * fade_in[:, None]).astype(data.dtype)

        fade_out_len = int(sample_rate * (fade_out_ms / 1000.0))
        if total_samples > fade_out_len and fade_out_len > 0:
            fade_out = np.linspace(1.0, 0.0, fade_out_len)
            if data.ndim == 1:
                data[-fade_out_len:] = (data[-fade_out_len:] * fade_out).astype(data.dtype)
            else:
                data[-fade_out_len:, :] = (data[-fade_out_len:, :] * fade_out[:, None]).astype(data.dtype)

        wavfile.write(file_path, sample_rate, data)
        
    except Exception as e:
        print(f"⚠️ Erreur lors du nettoyage de l'audio ({file_path}): {e}")


def sanitize_text_for_tts(text: str) -> str:
    cleaned = re.sub(
        r"[^a-zA-Z0-9àâäéèêëîïôöùûüçÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ\s.,?!:;\-'\"()+=/%]",
        " ",
        text,
    )
    return re.sub(r"\s+", " ", cleaned).strip()


def get_wav_duration(fname):
    """Calcule la durée précise du fichier audio en secondes."""
    try:
        if not os.path.exists(fname): return 0
        with contextlib.closing(wave.open(fname, 'r')) as f:
            frames = f.getnframes()
            rate = f.getframerate()
            return frames / float(rate)
    except Exception as e:
        print(f"⚠️ Erreur lecture durée WAV : {e}")
        return 0


def worker_audio():
    """Thread unique de lecture : traite la queue de manière 100% séquentielle."""
    global client
    
    while True:
        file_path = audio_queue.get()
        if file_path is None:
            break 
        
        try:
            duree = get_wav_duration(file_path)
            
            # 1. Publication MQTT unique au dashboard
            envoyer_audio_dashboard(client, file_path)
            
            print(f"⏳ Durée : {duree:.2f}s. Streaming UDP vers Oreille ({Config.OREILLE_IP})...")
            
            # 2. Pipeline GStreamer rythmé en temps réel
            send_cmd = [
                "gst-launch-1.0", "-q",
                "filesrc", f"location={file_path}", "!",
                "wavparse", "!",
                "audioconvert", "!",
                "audioresample", "!",
                "audio/x-raw,format=S16LE,channels=1,rate=22050,layout=interleaved", "!",
                "identity", "sync=true", "!",
                "udpsink", f"host={Config.OREILLE_IP}", "port=5000", "sync=false"
            ]
            
            subprocess.run(send_cmd, check=True)
            
            # Pause de 150ms pour laisser respirer le socket entre deux phrases
            time.sleep(0.15)

        except Exception as e:
            print(f"⚠️ Erreur worker_audio : {e}")
        finally:
            audio_queue.task_done()


def on_message(client, userdata, msg):
    if time.time() - START_TIME < 3.0:
        return
        
    payload = msg.payload.decode('utf-8').strip()
    
    # Canal status
    if msg.topic == "natacha/status":
        if payload == "traitement en cours":
            print("⏳ Natacha réfléchit...")
            if os.path.exists("data/traitement_en_cours.wav"):
                audio_queue.put("data/traitement_en_cours.wav")
        return 

    # Canal reponse
    if msg.topic == "natacha/reponse":
        if not payload: 
            return
        
        print(f"\n--- Début génération : '{payload}' ---")
        filename = f"audio_{uuid.uuid4().hex}.wav"
        filepath = os.path.join(Config.DATA_IN_DIR, filename)
        
        clean_text = sanitize_text_for_tts(payload)
        
        tts.tts_to_file(
            text=clean_text,
            file_path=filepath,
            speaker_wav=Config.SPEAKER_WAV,
            language="fr"
        )

        remove_pop(filepath)
        audio_queue.put(filepath)


# 1. Initialisation XTTS
print(f"--- NatachaMouth (Bouche NVIDIA) démarrée sur : {Config.DEVICE} ---")
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(Config.DEVICE)

# 2. Connexion MQTT
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_message = on_message
client.connect(Config.MQTT_BROKER, Config.MQTT_PORT, 60)
client.subscribe([("natacha/reponse", 0), ("natacha/status", 0)])

# 3. UN SEUL DÉMARRAGE DU THREAD LECTEUR (après la création du client MQTT)
threading.Thread(target=worker_audio, daemon=True).start()

print(f"En écoute sur MQTT ({Config.MQTT_BROKER})...")

try:
    client.loop_forever()
except KeyboardInterrupt:
    print("\nArrêt...")
    audio_queue.put(None)
