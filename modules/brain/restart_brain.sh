#!/bin/bash

# --- REDÉMARRAGE DU CERVEAU (LLM) ---
# On cible le fichier précis pour éviter toute erreur de confusion
PID_LLM=$(pgrep -f "llama-server")
if [ -n "$PID_LLM" ]; then
    echo "Arrêt de llama-server (PID: $PID_LLM)..."
    kill $PID_LLM
else
    echo "llama-server non trouvé."
fi

# --- REDÉMARRAGE DU BRIDGE ---
# On utilise le nom complet pour être sûr de ne viser QUE lui
PID_BRIDGE=$(pgrep -f "bridge_openhermes_33_12.py")
if [ -n "$PID_BRIDGE" ]; then
    echo "Arrêt du bridge (PID: $PID_BRIDGE)..."
    kill $PID_BRIDGE
else
    echo "bridge_openhermes_33_12.py non trouvé."
fi

echo "Redémarrage terminé. Systemd va reprendre la main."
