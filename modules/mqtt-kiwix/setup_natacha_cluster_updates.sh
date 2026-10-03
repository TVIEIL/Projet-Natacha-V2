#!/usr/bin/env bash
#
# ==============================================================================
# Script de déploiement automatique - Maintenance du Cluster Natacha
# Installation d'apt-cacher-ng (Serveur) & Configuration d'Ansible (Maître)
# OS supporté : Ubuntu 24.04 LTS
# ==============================================================================

set -euo pipefail

GREEN='\031[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================"${NC}
echo -e "${BLUE}   Installation du Système de Mise à Jour Natacha   "${NC}
echo -e "${BLUE}======================================================"${NC}

# 1. Vérification des privilèges root pour l'installation serveur
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}[ERROR] Ce script doit être exécuté avec des privilèges sudo.${NC}"
  exit 1
fi

LOGGED_USER=${SUDO_USER:-$USER}
USER_HOME=$(getent passwd "$LOGGED_USER" | cut -d: -f6)
ANSIBLE_DIR="$USER_HOME/ansible-nodes"
SSH_DIR="$USER_HOME/.ssh"

# 2. Installation et configuration d'apt-cacher-ng
echo -e "\n${YELLOW}[1/5] Installation et configuration d'apt-cacher-ng...${NC}"
apt-get update -qq
apt-get install -y -qq apt-cacher-ng

# Optimisation de la configuration acng.conf
ACNG_CONF="/etc/apt-cacher-ng/acng.conf"
echo -e "BindAddress: 0.0.0.0" >> "$ACNG_CONF"
echo -e "DlMaxRetries: 10" >> "$ACNG_CONF"
echo -e "NetworkTimeout: 60" >> "$ACNG_CONF"

systemctl restart apt-cacher-ng
systemctl enable apt-cacher-ng

# Ouverture du port 3142 si UFW est actif
if command -v ufw >/dev/null 2>&1 && ufw status | grep -q "active"; then
    echo -e "${YELLOW}Autorisation du port 3142/tcp dans UFW...${NC}"
    ufw allow 3142/tcp
fi

# 3. Installation d'Ansible
echo -e "\n${YELLOW}[2/5] Installation d'Ansible...${NC}"
apt-get install -y -qq ansible

# 4. Configuration des clés SSH pour l'utilisateur
echo -e "\n${YELLOW}[3/5] Vérification de la clé SSH pour $LOGGED_USER...${NC}"
if [ ! -f "$SSH_DIR/id_ed25519" ]; then
    echo -e "Génération d'une nouvelle clé SSH ED25519..."
    su - "$LOGGED_USER" -c "ssh-keygen -t ed25519 -N '' -f $SSH_DIR/id_ed25519"
else
    echo -e "${GREEN}Clé SSH ED25519 déjà présente.${NC}"
fi

# 5. Création de la structure Ansible
echo -e "\n${YELLOW}[4/5] Création de la structure du projet Ansible ($ANSIBLE_DIR)...${NC}"
su - "$LOGGED_USER" -c "mkdir -p $ANSIBLE_DIR"

# Fichier hosts (Inventaire)
HOSTS_FILE="$ANSIBLE_DIR/hosts"
if [ ! -f "$HOSTS_FILE" ]; then
    cat <<EOF > "$HOSTS_FILE"
[ubuntu_servers]
192.168.1.90
192.168.1.100
192.168.1.110
localhost ansible_connection=local

[ubuntu_servers:vars]
ansible_user=$LOGGED_USER
ansible_ssh_private_key_file=~/.ssh/id_ed25519
EOF
    chown "$LOGGED_USER:$LOGGED_USER" "$HOSTS_FILE"
    echo -e "${GREEN}Fichier d'inventaire 'hosts' créé.${NC}"
fi

# Fichier update.yml (Playbook)
PLAYBOOK_FILE="$ANSIBLE_DIR/update.yml"
cat <<'EOF' > "$PLAYBOOK_FILE"
---
- name: Configuration du proxy APT et mise à jour du parc Ubuntu
  hosts: ubuntu_servers
  become: true
  tasks:

    - name: Configurer le proxy APT (apt-cacher-ng)
      ansible.builtin.copy:
        dest: /etc/apt/apt.conf.d/00aptproxy
        content: |
          Acquire::http::Proxy "http://192.168.1.80:3142";
          Acquire::https::Proxy "DIRECT";
        owner: root
        group: root
        mode: '0644'

    - name: Mettre à jour le cache APT (apt update)
      ansible.builtin.apt:
        update_cache: yes
        cache_valid_time: 3600

    - name: Appliquer les mises à jour (apt upgrade)
      ansible.builtin.apt:
        upgrade: dist
        autoremove: yes
        autoclean: yes

    - name: Vérifier si un redémarrage est nécessaire
      ansible.builtin.stat:
        path: /var/run/reboot-required
      register: reboot_required_file

    - name: Redémarrer la machine si nécessaire
      ansible.builtin.reboot:
        msg: "Redémarrage suite aux mises à jour système"
        connect_timeout: 5
        reboot_timeout: 300
        pre_reboot_delay: 0
        post_reboot_delay: 30
        test_command: uptime
      when:
        - reboot_required_file.stat.exists
        - inventory_hostname != 'localhost'
EOF1111111
chown "$LOGGED_USER:$LOGGED_USER" "$PLAYBOOK_FILE"
echo -e "${GREEN}Playbook 'update.yml' créé.${NC}"

# 6. Bilan & Instructions
echo -e "\n${BLUE}======================================================"${NC}
echo -e "${GREEN}   Installation terminée avec succès !   "${NC}
echo -e "${BLUE}======================================================"${NC}
echo -e "📊 Interface Web du cache : ${YELLOW}http://192.168.1.80:3142/acng-report.html${NC}"
echo -e "\nProchaines étapes pour l'utilisateur ${YELLOW}$LOGGED_USER${NC} :"
echo -e "1. Copier la clé SSH sur chaque nouveau nœud du cluster :"
echo -e "   ${YELLOW}ssh-copy-id $LOGGED_USER@<IP_NOEUD>${NC}"
echo -e "2. Éditer le fichier d'inventaire si nécessaire :"
echo -e "   ${YELLOW}nano $ANSIBLE_DIR/hosts${NC}"
echo -e "3. Lancer la mise à jour globale du cluster :"
echo -e "   ${YELLOW}cd $ANSIBLE_DIR && ansible-playbook -i hosts update.yml --ask-become-pass${NC}"
