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


import time
import os
import torch
import paho.mqtt.client as mqtt
from TTS.api import TTS
from dotenv import load_dotenv
import subprocess
import threading
import queue
import uuid
import wave
import contextlib

START_TIME = time.time()
processing_flag = False


# 1. Configuration
load_dotenv()


# Configuration centralisée
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
    """Thread de lecture : Stream vers le KickPi via GStreamer."""
    while True:
        file_path = audio_queue.get()
        if file_path is None: break 
        
        try:
            duree = get_wav_duration(file_path)
            print(f"⏳ Durée : {duree:.2f}s. Envoi vers Oreille ({Config.OREILLE_IP})...")

            # Pipeline GStreamer robuste
            send_cmd = (
                f'gst-launch-1.0 -q filesrc location={file_path} ! wavparse ! '
                f'audioconvert ! audioresample ! "audio/x-raw,rate=22050,channels=1,format=S16LE" ! '
                f'udpsink host={Config.OREILLE_IP} port=5000'
            )
            
            subprocess.run(send_cmd, shell=True, check=True)
            
            # Pause de sécurité et nettoyage
            time.sleep(0.2)
            print("✨ Lecture terminée sur l'oreille. Prêt.")
            
        except Exception as e:
            print(f"Erreur lors du streaming : {e}")
        finally:
            # On ne supprime le fichier QUE s'il ne s'agit pas de "traitement_en_cours.wav"
            if "traitement_en_cours.wav" not in file_path:
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            # Quoi qu'il arrive, on marque la tâche comme terminée
            audio_queue.task_done()
            

def on_message(client, userdata, msg):
    # Sécurité au démarrage
    if time.time() - START_TIME < 3.0:
        return
        
    payload = msg.payload.decode('utf-8').strip()
    
    # 2. Gestion du canal "natacha/status"
    if msg.topic == "natacha/status":
        if payload == "traitement en cours":
            print("⏳ Natacha est en train de réfléchir...")
            audio_queue.put("data/traitement_en_cours.wav")
        return 

    # 3. Gestion du canal "natacha/reponse"
    if msg.topic == "natacha/reponse":
        if not payload: return
        
        print(f"\n--- Début génération : '{payload}' ---")
        filename = f"audio_{uuid.uuid4().hex}.wav"
        filepath = os.path.join(Config.DATA_IN_DIR, filename)
        
        tts.tts_to_file(text=payload, file_path=filepath, speaker_wav=Config.SPEAKER_WAV, language="fr")
        audio_queue.put(filepath)

            
def on_message_DEBUG(client, userdata, msg):
    raw_payload = msg.payload.decode('utf-8').strip()
    print(f"DEBUG - Type : {type(raw_payload)}")
    print(f"DEBUG - Contenu : {raw_payload}")
    
    # Si c'est un tableau, il faut le convertir en texte
    if isinstance(raw_payload, list):
        text = " ".join(raw_payload)
    else:
        text = raw_payload

def on_message_OLD(client, userdata, msg):
    global processing_flag
    
    # Gestion du statut d'attente
    if msg.topic == "natacha/status":
        if msg.payload.decode() == "Transmission au cerveau effectuée":
            print("⏳ En attente du Cerveau...")
            # On envoie un fichier "traitement_en_cours.wav" dans la file
            audio_queue.put("data/traitement_en_cours.wav")
        return

    # Gestion de la réponse vocale 
    text = msg.payload.decode('utf-8').strip()
    if not text: return

    print(f"\n--- Début génération : '{text}' ---")
    filename = f"audio_{uuid.uuid4().hex}.wav"
    filepath = os.path.join(Config.DATA_IN_DIR, filename)
    
    tts.tts_to_file(text=text, file_path=filepath, speaker_wav=Config.SPEAKER_WAV, language="fr")
    audio_queue.put(filepath)

# 1. Lancement du thread Lecteur
threading.Thread(target=worker_audio, daemon=True).start()

# 2. Initialisation XTTS
print(f"--- NatachaMouth (Bouche NVIDIA) démarrée sur : {Config.DEVICE} ---")
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(Config.DEVICE)

# 3. Connexion MQTT
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_message = on_message
client.connect(Config.MQTT_BROKER, Config.MQTT_PORT, 60)
client.subscribe([("natacha/reponse", 0), ("natacha/status", 0)])

print(f"En écoute sur MQTT ({Config.MQTT_BROKER})...")

try:
    client.loop_forever()
except KeyboardInterrupt:
    print("\nArrêt...")
    audio_queue.put(None) # Signal pour arrêter le worker

