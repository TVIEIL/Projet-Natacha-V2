# NatachaMouth XTTS V2 👄

**NatachaMouth** est le composant "Bouche" de mon système d'IA modulaire. Ce projet utilise le moteur **XTTS V2** pour générer une synthèse vocale de haute qualité, capable de cloner une voix spécifique à partir d'un échantillon.

---

## 🛠 Prérequis Techniques
La synthèse vocale en temps réel avec XTTS V2 est exigeante en ressources. Pour une expérience fluide, la configuration suivante est recommandée :

* **CPU :** Intel Core i9 ou équivalent.
* **GPU :** NVIDIA RTX (série 3000/4000 recommandée) pour l'accélération **CUDA**.
* **OS :** Linux (Ubuntu 22.04+ recommandé).

## 🎙 Configuration de la Voix
Le moteur de synthèse repose sur un échantillon pour cloner la voix :
* **Fichier de référence :** `data/voix_thierry_pro.wav`

### Format audio requis
Pour garantir une compatibilité parfaite avec XTTS V2, tes fichiers doivent respecter ces spécifications :
- **Format :** WAV
- **Encodage :** 16-bit PCM
- **Canaux :** Mono
- **Fréquence d'échantillonnage :** 22050 Hz

## ⏳ Gestion de l'Attente (UX)
Pour améliorer le confort lors des phases de réflexion de l'IA, le projet intègre un retour audio immédiat :

- **Fichier `data/traitement_en_cours.wav` :** Ce fichier est lu instantanément sur l'Oreille dès la transmission de la requête. Il confirme à l'utilisateur que le système travaille, évitant ainsi l'impression de latence. 
> **Note :** Ce fichier est protégé au niveau système (`chattr +i`) pour éviter toute suppression accidentelle.

## 📂 Structure du dépôt
```text
.
├── data/           # Fichiers audio de référence (Voix & Statut)
├── data_in/        # Fichiers temporaires générés par XTTS
├── main.py         # Script principal (MQTT, XTTS, Streaming)
├── requirements.txt # Dépendances du projet
└── .env            # Configuration locale (Brokers, IP, etc.)
