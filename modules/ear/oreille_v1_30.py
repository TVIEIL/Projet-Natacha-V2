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
# PROJET NATACHA - MODULE OREILLE
# ==============================================================================

# ==============================================================================
# PROJET NATACHA - MODULE OREILLE (v1.30-SR)
# ==============================================================================
# Rôle : Capture audio haute fidélité, transcription IA et pilotage du cluster.
# Hardware cible : AMD Ryzen (Nœud "Oreille")
# 
# Fonctionnalités :
#   - Capture via configuration dynamique (.env)
#   - Transcription locale via Faster-Whisper (Modèle Medium / int8).
#   - Analyse syntaxique d'intentions (Relance, Arrêt, Diagnostic).
#   - Pilotage distant du cluster (Cerveau i5 / Bouche OPi 6+) via SSH & MQTT.
# ==============================================================================

import os, time, subprocess, paramiko, pyaudio, socket, numpy as np
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from faster_whisper import WhisperModel
from dotenv import load_dotenv  
from pathlib import Path
import sys
from contextlib import contextmanager
import datetime
import re


os.environ['PYTHONUNBUFFERED'] = '1'
os.environ['AUDIODEV'] = 'hw:4' 

# On trouve le chemin du script lui-même
base_path = Path(__file__).resolve().parent
env_path = base_path / ".env"
reussite_question = False
reussite_statut = False

# On charge le .env
load_dotenv(dotenv_path=env_path)

# --- IMPORT DES SECRETS ---
try:
    from secrets_natacha import CREDS, OREILLE_IP, CERVEAU_IP, BOUCHE_IP, MQTT_IP
except ImportError:
    print("❌ Erreur : Le fichier secrets_natacha.py est manquant !")
    exit(1)
    
# --- CONFIGURATION MATÉRIELLE ---
#MIC_USB_ID = os.getenv("MIC_USB_ID")
mic_id_raw = os.getenv("MIC_USB_ID")
MIC_RATE = int(os.getenv("AUDIO_SAMPLE_RATE", 48000))
CHANNELS = 2
CHUNK = int(MIC_RATE / 10)
SILENCE_THRESHOLD = 0.005
MAX_SILENCE_CHUNKS = 25


def get_pyaudio_index_by_pid_vid(vid_pid):
    """
    Résout l'index PyAudio à partir d'une chaîne "VID:PID".
    Exemple : get_pyaudio_index_by_pid_vid("0132:3232")
    """
    if ":" not in vid_pid:
        print(f"DEBUG: Format invalide pour MIC_USB_ID : {vid_pid}")
        return None

    vid, pid = vid_pid.split(':')
    # On reconstruit la signature telle qu'elle apparaît dans 'alsa.components'
    # Le format attendu est "USB" + VID + ":" + PID (en majuscules)
    search_pattern = f"USB{vid}:{pid}".upper()
    
    try:
        # 1. Récupération des cartes via pactl
        # On utilise --format=text ou simplement le list par défaut
        pactl_out = subprocess.check_output(["pactl", "list", "cards"], text=True)
        
        # Le séparateur entre les cartes est 'Carte #' (ou 'Card #' en anglais)
        card_blocks = re.split(r'Carte #|Card #', pactl_out)
        
        card_num = None
        for block in card_blocks:
            if search_pattern in block:
                # Extraction du numéro de carte ALSA
                match = re.search(r'api\.alsa\.card = "(\d+)"', block)
                if match:
                    card_num = match.group(1)
                    break
        
        if card_num is None:
            print(f"DEBUG: Impossible de trouver la carte pour le composant {search_pattern}")
            return None
            
        # 2. Mapping vers l'index PyAudio via la signature matérielle 'hw:X'
        # On cherche la coordonnée 'hw:X'
        target_hw = f"hw:{card_num}"
        p = pyaudio.PyAudio()
        found_index = None
        
        for i in range(p.get_device_count()):
            dev_info = p.get_device_info_by_index(i)
            # On vérifie que 'hw:X' est présent dans le nom du device
            if target_hw in dev_info.get('name') and dev_info.get('maxInputChannels') > 0:
                found_index = i
                break
        
        p.terminate()
        return found_index

    except Exception as e:
        print(f"DEBUG: Erreur lors de la résolution de l'index : {e}")
        return None


def log_action(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}\n"

    log_path = os.path.expanduser("~/Natacha-Project/modules/ear/maintenance.log")
    with open(log_path, "a") as f:
        f.write(log_line)
        f.flush()
        os.fsync(f.fileno())

@contextmanager
def ignore_stderr():
    devnull = os.open(os.devnull, os.O_WRONLY)
    old_stderr = os.dup(sys.stderr.fileno())
    os.dup2(devnull, sys.stderr.fileno())
    try:
        yield
    finally:
        os.dup2(old_stderr, sys.stderr.fileno())
        os.close(devnull)
        os.close(old_stderr)

def connecter_mqtt():
    try:
        print(f"🔗 Tentative de connexion au broker MQTT : {MQTT_IP}...")
        mqtt_client.connect(MQTT_IP, 1883, keepalive=60)
        mqtt_client.loop_start() 
        print("✅ Connexion MQTT établie avec succès.")
        return True
    except Exception as e:
        print(f"❌ Erreur de connexion MQTT vers {MQTT_IP} : {e}")
        return False


def get_pyaudio_index_by_pid_vid(vid_pid):
    """
    Résolution robuste : on cherche le PID:VID, on extrait le numéro de carte, 
    et on mappe vers l'index PyAudio.
    """
    #search_component = f"USB{vid_pid}".upper()
    search_component = f"USB{vid_pid.lower()}"
    
    try:
        # 1. On récupère la liste des cartes
        pactl_out = subprocess.check_output(["pactl", "list", "cards"], text=True)
        #print(pactl_out)
        
        # On découpe par bloc "Carte #" ou "Card #"
        # Cela gère automatiquement les deux langues
        blocks = re.split(r'(?:Carte|Card) #', pactl_out)
        #print(blocks)
        
        print(search_component)
        
        card_num = None
        for block in blocks:
            # On vérifie si ce bloc contient bien notre identifiant
            if search_component in block:
                # On extrait proprement le numéro de carte présent dans CE bloc
                match = re.search(r'alsa\.card = "(\d+)"', block)
                if match:
                    card_num = match.group(1)
                    print(f"DEBUG: Carte trouvée pour {search_component} -> Card n°{card_num}")
                    break
        
        if card_num is None:
            print(f"FATAL: PID:VID {search_component} trouvé dans pactl mais aucun 'alsa.card' associé.")
            return None
            
        # 2. Mapping vers PyAudio
        target_hw = f"hw:{card_num}"
        p = pyaudio.PyAudio()
        
        # ---  BLOC POUR DEBUG p ---
        print(f"--- DÉBUT SCAN PYAUDIO (recherche de {target_hw}) ---")
        for i in range(p.get_device_count()):
            dev = p.get_device_info_by_index(i)
            print(f"Index {i} | Nom: '{dev.get('name')}'")
        print("--- FIN SCAN ---")
        # --------------------------------------
        
        for i in range(p.get_device_count()):
            dev_info = p.get_device_info_by_index(i)
            # On cherche hw:X,Y dans le nom
            if target_hw in dev_info.get('name') and dev_info.get('maxInputChannels') > 0:
                p.terminate()
                print(f"DEBUG: Index PyAudio trouvé -> {i}")
                return i
        
        p.terminate()
        return None

    except Exception as e:
        print(f"DEBUG: Erreur lors de la résolution : {e}")
        return None

        
def envoyer_mqtt(topic, message):
    if mqtt_client.is_connected():
        # publish() retourne un objet MQTTMessageInfo
        result = mqtt_client.publish(topic, message, qos=1, retain=False)
        
        # rc == 0 signifie MQTT_ERR_SUCCESS
        success = (result.rc == mqtt.MQTT_ERR_SUCCESS)
        
        if success:
            print(f"✅ MQTT Sent to {topic}: {message}")
            return True
        else:
            print(f"❌ MQTT Publish failed with error code: {result.rc}")
            return False
    else:
        print(f"🚫 Offline - Tentative de reconnexion...")
        connecter_mqtt()
        # On retourne False car l'envoi a échoué à cause de la déconnexion
        return False

def execute_remote_command(ip, user, password, command):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:

        ssh.connect(ip, username=user, password=password, timeout=10)
        stdin, stdout, stderr = ssh.exec_command(f"echo {password} | sudo -S -E  {command}")
        
        exit_status = stdout.channel.recv_exit_status()
        error_msg = stderr.read().decode().strip()
        
        if exit_status == 0:
            msg = f"SUCCESS sur {ip} : {command}"
            log_action(msg)
            return True, msg
        else:
            msg = f"ERREUR sur {ip} ({command}) : {error_msg}"
            log_action(msg)
            return False, msg
            
    except Exception as e:
        return False, str(e)
    finally:
        ssh.close()

def check_health(ip, port):
    target_ip = "127.0.0.1" if ip == OREILLE_IP else ip
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        res = sock.connect_ex((target_ip, port))
        sock.close()
        return "opérationnelle " if res == 0 else "hors ligne "
    except: return "hors ligne "

# --- INITIALISATION ---
mqtt_client = mqtt.Client(CallbackAPIVersion.VERSION2)
connecter_mqtt()

input_idx = get_pyaudio_index_by_pid_vid(mic_id_raw)

if input_idx is None:
    print("FATAL: Impossible de trouver l'index audio correspondant à", mic_id_raw)
    exit(1)

print(f"Index audio résolu avec succès : {input_idx}")


print(f"📥 Chargement de Whisper Medium (Rate cible: {MIC_RATE} Hz)...")
model = WhisperModel("large-v3", device="cpu", compute_type="int8", cpu_threads=12, num_workers=1)

p = pyaudio.PyAudio()

print(f"DEBUG: Tentative d'ouverture avec:")
print(f"  - CHANNELS = {CHANNELS} (type: {type(CHANNELS)})")
print(f"  - RATE = {MIC_RATE}")
print(f"  - INDEX = {input_idx}")

stream = p.open(format=pyaudio.paInt16, channels=CHANNELS, rate=MIC_RATE,
                input=True, input_device_index=input_idx, frames_per_buffer=CHUNK)

print(f"🎤 Natacha v1.30-SR (Rate: {MIC_RATE}Hz). Je t'écoute sur l'index {input_idx}...")

audio_buffer = []
silence_counter = 0

KEYWORDS_NOM = ["natacha", "natasha", "natascha", "matacha", "atacha","attachat","nathacha","nathashah","natashaa"]
ACT_ANALYSE = ["analyse", "diagnostic", "rapport", "santé", "statut","statue", "état","évalue","vérifie","examine","inspecte","contrôle","audite","scrute"]
SUJ_ANALYSE = ["fonctionnement", "système", "activité", "opérationnel","opérationnelle"]
ACT_RELANCE = ["redémarrage", "relance", "relancer", "restart", "reboot"]
SUJ_RELANCE = ["services", "logiciels", "système", "tout", "programmes", "natacha"]
ACT_ARRET = ["arrêt", "arret", "arré", "arre", "arrête", "éteindre", "stop", "halt"]
SUJ_ARRET = ["complet", "complé", "compliquer", "comblé", "total", "général", "définitif"]


try:
    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        audio_raw = np.frombuffer(data, dtype=np.int16)
        step = int(MIC_RATE / 16000)
        audio_mono_float = audio_raw[::CHANNELS].astype(np.float32) / 32768.0
        
        if np.sqrt(np.mean(audio_mono_float**2)) > SILENCE_THRESHOLD:
            audio_buffer.append(audio_mono_float)
            silence_counter = 0
            print(".", end="", flush=True)
        else:
            if audio_buffer:
                silence_counter += 1
                if silence_counter > MAX_SILENCE_CHUNKS:
                    print("\n🔍 Analyse...")
                    full_audio = np.concatenate(audio_buffer)
                    audio_16k = full_audio[::step] 
                    segments, _ = model.transcribe(audio_16k, beam_size=1, language="fr", vad_filter=True)
                    for segment in segments:
                        raw_text = segment.text.strip()
                        text = raw_text.lower().replace(',', ' ').replace('.', ' ')
                        print(f"✨ Entendu : {raw_text}")
                        if any(nom in text for nom in KEYWORDS_NOM):
                            if any(act in text for act in ACT_RELANCE) and any(suj in text for suj in SUJ_RELANCE):

                                cmd1 = f"/home/{CREDS['cerveau']['user']}/Natacha-Project/modules/brain/restart_brain.sh"
                                success, message = execute_remote_command(CERVEAU_IP, CREDS["cerveau"]["user"], CREDS["cerveau"]["pass"], cmd1)
                                time.sleep(8)
                                if not success:
                                    print(f"ÉCHEC de l'arrêt de  llama-server  et/ou  de   bridge_openhermes_33_12.py  : {message}")
                                else:
                                    print("Ordre de l'arrêt de  llama-server  et  de   bridge_openhermes_33_12.py   effectué avec succès. Le redémarrage automatique  va bientôt commencer.")
                                                              
                                success, message = execute_remote_command(BOUCHE_IP, CREDS["bouche"]["user"], CREDS["bouche"]["pass"], "systemctl  restart natachamouth.service")
                                time.sleep(8)
                                if not success:
                                    print(f"ÉCHEC de redémarrage de  natachamouth.service  : {message}")
                                else:
                                    print("Ordre de redémarrage de  natachamouth.service effectué avec succès.")
                                    
                                success, message = execute_remote_command(MQTT_IP, CREDS["mqtt"]["user"], CREDS["mqtt"]["pass"], "sudo /usr/bin/docker-compose -f /home/vieil/mqtt/docker-compose.yml restart")
                                time.sleep(8)
                                if not success:
                                    print(f"ÉCHEC de redémarrage sur le serveur MQTT de  docker-compose  : {message}")
                                else:
                                    print("Ordre de redémarrage  sur le serveur MQTT de  docker-compose   effectué avec succès.")
                                    
                                os.system(f"echo {CREDS['oreille']['pass']} | sudo systemctl  restart gstream_natacha.service")
                                time.sleep(8)
                                os.system(f"echo {CREDS['oreille']['pass']} | systemctl --user restart oreille_natacha.service")
                                time.sleep(8)
                            elif any(act in text for act in ACT_ARRET) and any(suj in text for suj in SUJ_ARRET):
                                reussite_question = envoyer_mqtt("natacha/reponse", "Extinction en cours.")
                                success, message = execute_remote_command(CERVEAU_IP, CREDS["cerveau"]["user"], CREDS["cerveau"]["pass"], "sudo -S halt")
                                time.sleep(5)
                                if not success:
                                    print(f"ÉCHEC d'extinction du Cerveau : {message}")
                                else:
                                    print("Ordre d'extinction du cerveau  envoyé avec succès.")

                                success, message = execute_remote_command(BOUCHE_IP, CREDS["bouche"]["user"], CREDS["bouche"]["pass"], "sudo -S halt")
                                time.sleep(5)
                                if not success:
                                    print(f"ÉCHEC d'extinction de la Bouche : {message}")
                                else:
                                    print("Ordre d'extinction de la bouche envoyé avec succès.")
                                    
                                success, message = execute_remote_command(MQTT_IP, CREDS["mqtt"]["user"], CREDS["mqtt"]["pass"], "sudo -S halt")
                                time.sleep(5)
                                if not success:
                                    print(f"ÉCHEC d'extinction du serveur  MQTT : {message}")
                                else:
                                    print("Ordre d'extinction du  serveur MQTT envoyé avec succès.")
                                    
                                os.system(f"echo {CREDS['oreille']['pass']} | sudo -S halt")
                            elif any(act in text for act in ACT_ANALYSE) and any(suj in text for suj in SUJ_ANALYSE):
                                reussite_question = envoyer_mqtt("natacha/reponse", f"Le serveur de communication  mosquitto est  {check_health(MQTT_IP, 1883)}.")
                            elif len(text) > 3:
                                # On réaffecte ici, cela garantit que tu testes le résultat de l'envoi présent
                                reussite_question = envoyer_mqtt("natacha/question", raw_text) 

                                if reussite_question:
                                    reussite_statut = envoyer_mqtt("natacha/status", "traitement en cours")
                                    time.sleep(5)
                                    if reussite_statut:
                                        print("✅ Question transmise et statut 'traitement en cours' activé.")
                                    else:
                                        print("⚠️ Question envoyée, mais échec de transmission du statut.")
                                else:
                                    print("❌ Échec de l'envoi de la question.")
                    audio_buffer, silence_counter = [], 0
except KeyboardInterrupt:
    print("\n🛑 Fin du programme.")
finally:
    if 'stream' in locals():
        stream.close()
    p.terminate()


