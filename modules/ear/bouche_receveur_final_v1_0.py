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
# PROJET NATACHA - MODULE GSTREAM FLUX AUDIO SYNTHESE VOCALE VERS MICRO-CASQUE
# ==============================================================================

# ==============================================================================
# PROJET NATACHA - NŒUD OREILLE (Ryzen 5)
# Script : bouche_receveur_final_v1_0.py (v1.0-SR)
# ==============================================================================


import subprocess
import sys
import os
from dotenv import load_dotenv
import re
import threading
import shutil 
import time


# --- CHARGEMENT CONFIG ---
load_dotenv()
SPEAKER_ID = os.getenv("SPEAKER_USB_ID") # Ex: 0132:3232

def get_alsa_card_num(vid_pid):
    """
    Résout le numéro de carte ALSA (ex: 3) à partir du PID:VID.
    """
    if not vid_pid:
        return None
        
    #search_component = f"USB{vid_pid}".upper()
    search_component = f"USB{vid_pid.lower()}"
    try:
        pactl_out = subprocess.check_output(["pactl", "list", "cards"], text=True)
        # Découpe par carte pour isoler les infos
        blocks = re.split(r'(?:Carte|Card) #', pactl_out)
        
        for block in blocks:
            if search_component in block:
                match = re.search(r'alsa\.card = "(\d+)"', block)
                if match:
                    return match.group(1) # Retourne le numéro de carte (ex: "3")
        return None
    except Exception:
        return None

# --- RÉSOLUTION DYNAMIQUE ---
card_num = get_alsa_card_num(SPEAKER_ID)

if card_num:
    # On force GStreamer à utiliser la carte précise. 
    # hw:{card_num} pointe directement vers l'interface ALSA de la carte
    SINK = f"alsasink device=hw:{card_num}"
    print(f"✅ Sortie forcée sur matériel ID {SPEAKER_ID} (ALSA card {card_num})")
else:
    SINK = "pulsesink"
    print("⚠️ ID matériel non résolu, repli sur pulsesink.")

# --- CONFIGURATION (inchangée) ---
NIVEAU_SONORE = 0.5
STREAM_RATE = 22050 
PORT_UDP = 5000
CHANNELS = 1
FORMAT = "S16LE"

# Pipeline GStreamer
pipeline = (
    f'gst-launch-1.0 udpsrc port={PORT_UDP} buffer-size=524288 ! '
    f'"audio/x-raw,rate={STREAM_RATE},channels={CHANNELS},format={FORMAT},layout=interleaved" ! '
    f'queue max-size-buffers=0 max-size-time=0 max-size-bytes=0 ' 
    f'min-threshold-time=200000000 ! ' 
    f'rawaudioparse use-sink-caps=true ! '
    f'audioconvert ! '
    f'audioresample ! '
    f'volume volume={NIVEAU_SONORE} ! '
    f'{SINK} buffer-time=200000 latency-time=10000'
)

print(f"---")
print(f"✅ Receveur Natacha v1.1 (Résolu matériellement) ...")
print(f"🔊 Sortie : {SINK}")
print(f"---")

# Note : J'ai retiré le thread 'forcer_audio_systeme' ici 
# car si tu utilises alsasink device=hw:X, tu bypasses PulseAudio/ALSA Mixers.
# C'est donc plus propre et plus rapide.

try:
    subprocess.run(pipeline, shell=True)
except KeyboardInterrupt:
    print("\n🛑 Arrêt du receveur.")
    sys.exit(0)
