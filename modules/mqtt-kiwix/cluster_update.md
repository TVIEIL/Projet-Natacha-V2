##Comment l'utiliser ?

Crée le fichier sur la machine maître :
Bash
```
nano setup_natacha_cluster_updates.sh

Rends-le exécutable :
Bash
```
chmod +x setup_natacha_cluster_updates.sh
```

Exécute-le avec sudo :
Bash

sudo ./setup_natacha_cluster_updates.sh

Ce script prend en charge l'ensemble des ajustements réseau, les temporisations du cache apt-cacher-ng, l'ouverture du pare-feu ufw et la génération des fichiers de travail pour Ansible.
