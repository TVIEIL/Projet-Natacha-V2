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
# PROJET NATACHA - MODULE SETUP AUDIO
# ==============================================================================

# ==============================================================================
# PROJET : NATACHA
# MODULE : Utilitaire de Calibrage Audio Robuste (setup_audio.py)
# DESCRIPTION : Identification, scan de fréquences et gestion d'erreurs de saisie.
# ==============================================================================


import pyaudio
import os
import subprocess
import re
import atexit
import getpass
import time

# Récupère automatiquement le nom de l'utilisateur connecté
USER = getpass.getuser()

# --- PARAMÈTRES ---
FORMAT = pyaudio.paInt16
CHANNELS = 1
CHUNK = 1024
RECORD_SECONDS = 3


##  forcer_profil_pro_audio()       ##
#########################

# BUG propre à mon DONGLE USB 
# il disparait de la liste des entrées 
# pactl list cards short => ... 115    alsa_card.usb-Generic_USB_DONGLE_33202107269042-00    alsa ...
# pactl list sources | grep -i "DONGLE" -A 5 => 
# pactl list cards | grep -A 20 "115"  => output:iec958-ac3-surround-51: Sortie Surround numérique 5.1 (IEC958/AC3) (sorties : 1, sources : 0, priorité : 300, disponible : oui) 
# le système le considère uniquement comme une entrée
def forcer_profil_pro_audio():
    print("🔊 Forçage du profil 'pro-audio' sur le dongle...")
    # On utilise l'ID '115' ou le nom de la carte
    # On le fait via subprocess pour ne pas dépendre de bibliothèques tierces
    
    result = subprocess.run(["pactl", "set-card-profile", "115", "pro-audio"], capture_output=True)
    
    if result.returncode != 0:
        print(f"⚠️ Attention : Impossible de forcer le profil pro-audio : {result.stderr}")
    else:
        print("✅ Profil 'pro-audio' activé avec succès.")

# --- DÉFINITION DE LA SORTIE AUTOMATIQUE ---
def au_revoir():
    print("\n🔄 Rétablissement des services Natacha...")
    gestion_services("start")

atexit.register(au_revoir)

def gestion_services(action):
    """ action : 'stop' ou 'start' """
    # Définition des services avec leur type (system ou user)
    services = [
        {"name": "gstream_natacha.service", "type": "system"},
        {"name": "oreille_natacha.service", "type": "user"}
    ]
    
    for svc in services:
        print(f"⚙️ {action.capitalize()} du service {svc['name']} ({svc['type']} mode)...")
        
        if svc['type'] == "system":
            # Pour gstream_natacha, on a besoin de sudo
            subprocess.run(["sudo", "systemctl", action, svc['name']], capture_output=True)
        else:
            # Pour oreille_natacha, on utilise --user, pas de sudo
            # Attention : on doit spécifier l'utilisateur pour le mode user dans un script
            subprocess.run(["systemctl", "--user", action, svc['name']], capture_output=True)

def tuer_processus_fantomes():
    """ Tue les processus liés à l'utilisateur courant """
    print(f"🧹 Nettoyage des processus fantômes pour l'utilisateur : {USER}...")
    # On utilise la variable USER ici
    subprocess.run(f"pkill -u {USER} -f natacha", shell=True)

import os

def obtenir_usb_id(nom_peripherique):
    # On cherche le mot clé DONGLE dans le nom du device
    keyword = nom_peripherique
    try:
        lsusb_out = subprocess.check_output("lsusb", shell=True).decode()
        for line in lsusb_out.splitlines():
            if keyword in line:
                # La ligne ressemble à "Bus 001 Device 004: ID 0132:3232 Generic USB DONGLE"
                # On cherche le pattern ID 1234:5678
                match = re.search(r"ID ([0-9a-fA-F]{4}:[0-9a-fA-F]{4})", line)
                if match:
                    return match.group(1)
        return "ID_INCONNU"
    except:
        return "ID_ERREUR"

def obtenir_peripheriques_valides():
    """ Retourne deux listes contenant les index valides pour In et Out """
    inputs = []
    outputs = []
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        
        # DEBUG 
        # print(f"DEBUG: Index {i} | Name: {dev.get('name')} | MaxIn: {dev.get('maxInputChannels')}")
        
        if dev.get('maxInputChannels') > 0:
            inputs.append(i)
        if dev.get('maxOutputChannels') > 0:
            outputs.append(i)
    return inputs, outputs

def lister_peripheriques(inputs, outputs):
    """ Affiche les périphériques disponibles """
    print("\n--- 🎤 ENTRÉES DISPONIBLES (Micro) ---")
    for i in inputs:
        print(f"Index [{i}] : {p.get_device_info_by_index(i).get('name')}")

    print("\n--- 🔊 SORTIES DISPONIBLES (Casque) ---")
    for i in outputs:
        print(f"Index [{i}] : {p.get_device_info_by_index(i).get('name')}")

def saisir_index_valide(liste_valide, message):
    """ Force l'utilisateur à saisir un index correct présent dans la liste """
    while True:
        try:
            choix = int(input(message))
            if choix in liste_valide:
                return choix
            else:
                print(f"⚠️ Erreur : L'index {choix} n'est pas dans la liste ci-dessus. Recommencez.")
        except ValueError:
            print("⚠️ Erreur : Veuillez entrer un numéro (chiffre uniquement).")

def scanner_frequences(input_idx, output_idx):
    """ Teste les fréquences acceptées par le matériel """
    freq_standards = [16000, 22050, 44100, 48000]
    valides = []
    print("\n🔍 Analyse des capacités matérielles...")
    for f in freq_standards:
        try:
            if p.is_format_supported(rate=f, 
                                     input_device=input_idx, input_channels=CHANNELS, input_format=FORMAT,
                                     output_device=output_idx, output_channels=CHANNELS, output_format=FORMAT):
                valides.append(f)
                print(f"  ✅ {f} Hz : OK")
        except Exception:
            print(f"  ❌ {f} Hz : Non supporté")
    return valides

def test_echo(input_idx, output_idx, rate_test):
    """ Enregistre et rejoue le son """
    print(f"\n🎙️ Test réel à {rate_test} Hz...")
    print(f"Enregistrement de {RECORD_SECONDS} secondes... Parlez !")
    try:
        stream_in = p.open(format=FORMAT, channels=CHANNELS, rate=rate_test, 
                           input=True, input_device_index=input_idx, frames_per_buffer=CHUNK)
        frames = []
        for _ in range(0, int(rate_test / CHUNK * RECORD_SECONDS)):
            frames.append(stream_in.read(CHUNK, exception_on_overflow=False))
        stream_in.stop_stream()
        stream_in.close()

        print("🎧 Lecture dans le casque...")
        stream_out = p.open(format=FORMAT, channels=CHANNELS, rate=rate_test, 
                            output=True, output_device_index=output_idx, frames_per_buffer=CHUNK)
        for data in frames:
            stream_out.write(data)
        stream_out.stop_stream()
        stream_out.close()
        return True
    except Exception as e:
        print(f"❌ Erreur durant le test : {e}")
        return False

# ==============================================================================
# LOGIQUE PRINCIPALE
# ==============================================================================
if __name__ == "__main__":
    print("="*50)
    print("🛠️ CALIBRAGE AUDIO INTERACTIF - PROJET NATACHA")
    print("="*50)

    # 1. On arrête tout avant de toucher à l'audio
    print("\n🛡️ Préparation : Arrêt des services et nettoyage...")
    gestion_services("stop")
    tuer_processus_fantomes()

    # Correction du bug avec mon USB DONGLE qui passe en sortie au lien d'entrée
    forcer_profil_pro_audio()
    
    # 2. LA PAUSE DE SÉCURITÉ (Crucial)
    print("⏳ Attente de libération du bus USB...")
    time.sleep(2) # 2 secondes suffisent généralement pour stabiliser le bus

    # 3. INSTANCIATION ICI (après le forçage du profil)
    p = pyaudio.PyAudio()

    # 4. On récupère et on liste
    valid_ins, valid_outs = obtenir_peripheriques_valides()
    lister_peripheriques(valid_ins, valid_outs)

    try:
        # 1. Saisie sécurisée des Index
        in_idx = saisir_index_valide(valid_ins, "\n👉 Index MICROPHONE : ")
        out_idx = saisir_index_valide(valid_outs, "👉 Index CASQUE : ")
    
        # 2. Scan automatique
        freq_ok = scanner_frequences(in_idx, out_idx)
    
        if not freq_ok:
            print("\nERREUR : Aucune fréquence standard acceptée par ce matériel.")
        else:
            print("\n--- FRÉQUENCES SUPPORTÉES ---")
            for i, f in enumerate(freq_ok):
                print(f"{i+1}. {f} Hz")
        
            # 3. Saisie sécurisée de la fréquence
            choix_f = 0
            while choix_f < 1 or choix_f > len(freq_ok):
                try:
                    choix_f = int(input(f"👉 Sélectionnez une fréquence (1-{len(freq_ok)}) : "))
                except ValueError:
                    pass
        
            selected_rate = freq_ok[choix_f - 1]
        
            # 4. Test auditif et sauvegarde
            if test_echo(in_idx, out_idx, selected_rate):
                if input("\nAvez-vous entendu votre voix correctement ? (o/n) : ").lower() == 'o':
                    # e.g : "USB DONGLE: Audio (hw:3,0)"  
                    nom_in = p.get_device_info_by_index(in_idx).get('name').split(':')[0]
                    #nom_in = nom_in.split(':')[0]
                    nom_out = p.get_device_info_by_index(out_idx).get('name').split(':')[0]
                    #nom_out = nom_out.split(':')[0]
                    
                    # dans ce cas précis   nom_in = nom_out =  "USB DONGLE"
                
                    print(f"\n💾 Mise à jour du fichier .env avec IDs matériels...")
                    #id_mic = obtenir_usb_id(p.get_device_info_by_index(in_idx).get('name'))
                    id_mic = obtenir_usb_id(nom_in)
                    #id_spk = obtenir_usb_id(p.get_device_info_by_index(out_idx).get('name'))
                    id_spk = obtenir_usb_id(nom_out)
                
                    with open(".env", "w") as env_file:
                        env_file.write(f"MIC_USB_ID={id_mic}\n")
                        env_file.write(f"SPEAKER_USB_ID={id_spk}\n")
                        env_file.write(f"AUDIO_SAMPLE_RATE={selected_rate}\n")
                    
                        print(f"✅ Configuration sauvegardée avec IDs : {id_mic} / {id_spk}")
                    
                
                    print("✅ Configuration sauvegardée !")
                else:
                    print("\n🔄 Calibrage annulé.")
            else:
                print("\n❌ Échec du test d'écho.")

    except KeyboardInterrupt:
        print("\n🛑 Arrêt manuel détecté.")
    finally:
        p.terminate()
