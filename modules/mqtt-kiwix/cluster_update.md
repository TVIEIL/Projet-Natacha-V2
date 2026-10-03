## Script setup_natacha_cluster_updates

Ce script prend en charge l'ensemble des ajustements réseau, les temporisations du cache apt-cacher-ng.
Il faut ouvrir le pare-feu ufw 3142/tcp et la génération des fichiers de travail pour Ansible.

Voici un script Bash complet et prêt à l'emploi. Il permet d'installer et de configurer automatiquement le serveur
de cache apt-cacher-ng ainsi que l'environnement d'administration Ansible sur la machine maître, puis de préparer
l'inventaire et le playbook de mise à jour.  


### Comment l'utiliser ?

Crée le fichier sur la machine maître :
Bash
```
nano setup_natacha_cluster_updates.sh
```
&nbsp;
Le Rendre exécutable :
Bash
```
chmod +x setup_natacha_cluster_updates.sh
sudo ./setup_natacha_cluster_updates.sh
```
&nbsp;



