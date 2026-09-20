#!/bin/bash
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

# ====================================================================================
# Description :Configuration et initialisation des sorties audio (Unmute & Volume 50%)
# ====================================================================================


echo "🚀 Initialisation du Grand Reset Audio (ALSA + PulseAudio + PipeWire)..."

# 1. Niveau Kernel : ALSA
echo "--- 1/3 Réinitialisation ALSA ---"
sudo alsa force-reload

# 2. Niveau Serveur : PipeWire / PulseAudio / WirePlumber
# Sur Ubuntu 24.04, on redémarre les services utilisateurs
echo "--- 2/3 Redémarrage de la pile PipeWire & WirePlumber ---"
systemctl --user restart pipewire pipewire-pulse wireplumber

# On laisse 2 secondes aux services pour se stabiliser
sleep 2

# 3. Niveau Réglages : Unmute et Volume
echo "--- 3/3 Configuration des niveaux ---"
# On utilise l'alias universel @DEFAULT_AUDIO_SINK@ pour ne pas dépendre des IDs
wpctl set-mute @DEFAULT_AUDIO_SINK@ 0
wpctl set-volume @DEFAULT_AUDIO_SINK@ 0.50

# 4. Finalisation : Reconnexion du service Natacha
echo "--- 🛠️  Relance du service GStreamer Natacha ---"
sudo systemctl restart gstream-natacha

echo "---"
echo "✅ Système audio réinitialisé !"
echo "📊 État actuel de l'arborescence :"
wpctl status | grep -A 10 "Audio"
