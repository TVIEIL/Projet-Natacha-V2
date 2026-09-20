#!/bin/bash

echo "Arrêt des conteneurs du Hub (Mosquitto et Kiwix)..."
docker stop $(docker ps -a -q --filter ancestor=eclipse-mosquitto) 2>/dev/null || true
docker rm $(docker ps -a -q --filter ancestor=eclipse-mosquitto) 2>/dev/null || true

docker stop $(docker ps -a -q --filter ancestor=ghcr.io/kiwix/kiwix-serve) 2>/dev/null || true
docker rm $(docker ps -a -q --filter ancestor=ghcr.io/kiwix/kiwix-serve) 2>/dev/null || true

echo "Attente de 10 secondes..."
sleep 10

echo "Redémarrage du broker MQTT (Mosquitto)..."
docker run -d \
  --name mosquitto \
  --restart unless-stopped \
  -p 1883:1883 \
  -p 9001:9001 \
  -v "$HOME/mqtt/config/mosquitto.conf:/mosquitto/config/mosquitto.conf" \
  -v "$HOME/mqtt/data:/mosquitto/data" \
  eclipse-mosquitto

echo "Redémarrage du serveur Kiwix..."
docker run -d \
  --name mqtt_kiwix_1 \
  --restart unless-stopped \
  -p 8080:8080 \
  -v "$HOME/kiwix:/data" \
  ghcr.io/kiwix/kiwix-serve:latest /data/wikipedia_fr_physics_maxi_2026-04.zim

echo "Hub redémarré avec succès !"
