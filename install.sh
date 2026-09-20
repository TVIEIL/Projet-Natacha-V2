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
#
#######################################################
##  Projet Natacha INSTALLATION AUTOMATIQUE DU NOEUD
#######################################################

set -e  # Arrête le script en cas d'erreur

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 1. On définit d'abord où on est
CURRENT_DIR_NAME=$(basename "$PWD")

# 2. Vérification de sécurité sur le nom du dossier
if [[ "$CURRENT_DIR_NAME" != "Natacha-Project" ]]; then
    echo -e "${YELLOW}Le dossier actuel ($CURRENT_DIR_NAME) ne s'appelle pas 'Natacha-Project'.${NC}"
    echo -e "Renommage automatique..."
    cd ..
    mv -- "$CURRENT_DIR_NAME" "Natacha-Project"
    cd "Natacha-Project"
    echo -e "${GREEN}Dossier renommé avec succès.${NC}"
fi

# 3. Maintenant on définit le PROJECT_ROOT pour tout le reste du script
PROJECT_ROOT=$(pwd)


echo -e "${GREEN}-------------------------------------------------------"
echo "   Installation du Projet Natacha - Cluster IA"
echo -e "-------------------------------------------------------${NC}"

# Vérification des droits sudo avant de commencer
echo "Vérification des droits d'administration..."
if sudo -v &> /dev/null; then
    echo "Droits sudo validés."
else
    echo -e "${RED}Erreur : Vous devez avoir les droits sudo pour lancer l'installation.${NC}"
    exit 1
fi

echo "Quel module installer sur cette machine ?"
echo "1) L'Oreille"
echo "2) Le Cerveau"
echo "3) La Bouche"
echo "4) Le Hub (MQTT / Kiwix)"
echo "5) Quitter"
read -p "Votre choix [1-5] : " choice

# Gestion de l'option Quitter
if [ "$choice" -eq 5 ]; then
    echo "Annulation."
    exit 0
fi

PROJECT_ROOT=$(pwd)
CURRENT_USER=$USER # Récupère l'utilisateur qui lance le script

# Ajout crucial de l'utilisateur au groupe audio pour les accès matériels
echo -e "${YELLOW}Ajout de l'utilisateur $CURRENT_USER au groupe 'audio'...${NC}"
sudo usermod -aG audio $CURRENT_USER

# --- Fonction pour installer le service existant ---
deploy_service() {
    local MODULE_PATH=$1    # ex: ear
    local SERVICE_NAME=$2    # ex: oreille_natacha

    echo -e "${GREEN}Installation du service $SERVICE_NAME...${NC}"
    mkdir -p ~/.config/systemd/user/
    local TARGET_SERVICE="$HOME/.config/systemd/user/$SERVICE_NAME.service"

    # Copie du fichier depuis ton dossier de scripts vers le dossier systemd utilisateur
    cp "$PROJECT_ROOT/scripts_systemd/$MODULE_PATH/$SERVICE_NAME.service" "$TARGET_SERVICE"

    # 1. Remplacement de 'vieil' par l'utilisateur actuel
    sed -i "s/vieil/$CURRENT_USER/g" "$TARGET_SERVICE"
    
    # 2. Remplacement de %h par le chemin absolu du dossier personnel
    sed -i "s|%h|$HOME|g" "$TARGET_SERVICE"

    # 3. Injection sécurisée des variables d'environnement PipeWire sous [Service]
    local RUN_DIR="/run/user/$(id -u)"
    sed -i "/^\[Service\]/a Environment=\"DBUS_SESSION_BUS_ADDRESS=unix:path=$RUN_DIR/bus\"" "$TARGET_SERVICE"
    sed -i "/^\[Service\]/a Environment=\"PULSE_SERVER=unix:$RUN_DIR/pulse/native\"" "$TARGET_SERVICE"
    sed -i "/^\[Service\]/a Environment=\"XDG_RUNTIME_DIR=$RUN_DIR\"" "$TARGET_SERVICE"

    # Activation
    systemctl --user daemon-reload
    systemctl --user enable $SERVICE_NAME.service
    echo -e "${GREEN}Service $SERVICE_NAME configuré et activé pour l'utilisateur $CURRENT_USER !${NC}"
}

# --- 1. Miniconda ---
if ! command -v conda &> /dev/null; then
    echo "Installation de Miniconda..."
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh
    bash miniconda.sh -b -p $HOME/miniconda3
    $HOME/miniconda3/bin/conda init bash
    export PATH="$HOME/miniconda3/bin:$PATH"
fi

# On s'assure que le chemin est connu pour la suite
export PATH="$HOME/miniconda3/bin:$PATH"

#  Acceptation automatique des ToS (Pour tout le monde) ---
echo "Vérification des conditions d'utilisation de Conda..."
# On utilise le chemin complet vers conda pour être sûr que ça réponde
$HOME/miniconda3/bin/conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main || true
$HOME/miniconda3/bin/conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r || true

# --- 3. Installation par module ---

# On s'assure que systemctl peut parler au bus utilisateur
export XDG_RUNTIME_DIR="/run/user/$(id -u)"

case $choice in
    1)
        echo -e "${GREEN}>>> Configuration OREILLE...${NC}"
        sudo apt update && sudo apt install -y ffmpeg gstreamer1.0-tools portaudio19-dev
        conda create -n oreille_natacha python=3.10 -y
        $HOME/miniconda3/envs/oreille_natacha/bin/pip install -r "$PROJECT_ROOT/modules/ear/requirements.txt"
        
        # Installation des DEUX services de l'oreille
        deploy_service "ear" "oreille_natacha"
        deploy_service "ear" "gstream_natacha"
        ;; 

    2)
        echo -e "${GREEN}>>> Configuration CERVEAU...${NC}"
        sudo apt update && sudo apt install -y build-essential cmake
        conda create -n cerveau_natacha python=3.10 -y
        $HOME/miniconda3/envs/cerveau_natacha/bin/pip install -r "$PROJECT_ROOT/modules/brain/requirements.txt"
        
        deploy_service "brain" "cerveau_natacha"
        echo -e "${YELLOW}Nota: N'oubliez pas de compiler llama.cpp manuellement.${NC}"
        ;; 

    3)
        echo -e "${GREEN}>>> Configuration BOUCHE...${NC}"
        sudo apt update && sudo apt install -y gstreamer1.0-tools alsa-utils
        conda create -n bouche_natacha python=3.10 -y
        $HOME/miniconda3/envs/bouche_natacha/bin/pip install -r "$PROJECT_ROOT/modules/mouth/requirements.txt"
        
        deploy_service "mouth" "bouche_natacha"
        ;; 

    4)
        echo -e "${GREEN}>>> Configuration HUB (MQTT / Kiwix)...${NC}"
        
        
        # 1. Vérification et installation de Docker si nécessaire
        if ! command -v docker &> /dev/null; then
            echo "Installation de Docker..."
            sudo apt update && sudo apt install -y docker.io
            sudo usermod -aG docker $CURRENT_USER
            sudo systemctl enable --now docker
            echo -e "${YELLOW}Docker installé. Assurez-vous d'avoir les droits pour l'utiliser.${NC}"
        fi

        # 2. Création des répertoires locaux pour la configuration et les données
        mkdir -p "$HOME/mqtt/config"
        mkdir -p "$HOME/mqtt/data"
        mkdir -p "$HOME/kiwix"

        # 3. Génération automatique du fichier mosquitto.conf s'il n'existe pas
        if [ ! -f "$HOME/mqtt/config/mosquitto.conf" ]; then 
        echo "Création du fichier mosquitto.conf.."
        cat <<EOF > "$HOME/mqtt/config/mosquitto.conf" 
persistence true
persistence_location /mosquitto/data/ 
log_dest stdout 
listener 1883
allow_anonymous true
listener 9001
protocol websockets
EOF
        fi


        # 4. Lancement direct du conteneur Mosquitto (avec nettoyage préalable)
        echo "Lancement du broker MQTT (Mosquitto)..."
        docker stop mosquitto &> /dev/null || true
        docker rm mosquitto &> /dev/null || true
        docker run -d \
          --name mosquitto \
          --restart unless-stopped \
          -p 1883:1883 \
          -p 9001:9001 \
          -v "$HOME/mqtt/config/mosquitto.conf:/mosquitto/config/mosquitto.conf" \
          -v "$HOME/mqtt/data:/mosquitto/data" \
          eclipse-mosquitto

        # 5. Lancement direct du conteneur Kiwix (avec nettoyage préalable)
        echo "Lancement du serveur Kiwix..."
        docker stop mqtt_kiwix_1 &> /dev/null || true
        docker rm mqtt_kiwix_1 &> /dev/null || true
        docker run -d \
          --name mqtt_kiwix_1 \
          --restart unless-stopped \
          -p 8080:8080 \
          -v "$HOME/kiwix:/data" \
          ghcr.io/kiwix/kiwix-serve:latest /data/wikipedia_fr_physics_maxi_2026-04.zim

        echo -e "${GREEN}Hub configuré et conteneurs Docker lancés avec succès !${NC}"

        # 5. Ouverture des ports UFW et installation du service Dashboard
        echo "Ouverture des ports UFW (9001, 8080 et 8090)..."
        sudo ufw allow 9001/tcp
        sudo ufw allow 8080/tcp
        sudo ufw allow 8090/tcp
        

        echo "Installation du service systemd Natacha Dashboard..."
        sudo cp "$HOME/Natacha-Project/scripts_systemd/mqtt-kiwix/natacha-dashboard.service" /etc/systemd/system/
        sudo systemctl daemon-reload
        sudo systemctl enable --now natacha-dashboard.service
        
        ;;
esac

# --- 4. Finalisation ---
sudo loginctl enable-linger $USER
echo -e "${GREEN}Installation terminée ! Pensez à vérifier vos fichiers dans /secrets.${NC}"
