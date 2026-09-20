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

# ==================================================================================
# PROJET NATACHA - MODULE VISUALISATION DES COLLECTIONS CHROMADB 
#                  natacha_relation  - natacha_expertise
# ==================================================================================



import chromadb
from chromadb.utils import embedding_functions

# --- CONFIGURATION ---
PATH_MEMOIRE = "./memoire_chroma"
chroma_client = chromadb.PersistentClient(path=PATH_MEMOIRE)
emb_fn = embedding_functions.DefaultEmbeddingFunction()

def auditer_collection(nom_coll, limite=100):
    print(f"\n{'='*60}")
    print(f"🔍 COLLECTION : {nom_coll}")
    print(f"{'='*60}")
    
    coll = chroma_client.get_or_create_collection(name=nom_coll, embedding_function=emb_fn)
    
    # Récupération des données
    res = coll.get()
    ids = res['ids']
    docs = res['documents']
    count = len(ids)
    
    print(f"📊 Nombre total d'entrées : {count}")
    
    if count == 0:
        print("La collection est vide.")
        return

    # On affiche les X dernières entrées
    print(f"🕒 Affichage des {min(limite, count)} dernières entrées :")
    for i in range(max(0, count - limite), count):
        print(f"\nID   : {ids[i]}")
        print(f"INFO : {docs[i]}")
        print(f"{'-'*30}")

def chercher_info(mot_cle):
    print(f"\n🔎 Recherche du mot-clé '{mot_cle}' dans toute la mémoire...")
    for nom in ["natacha_relation", "natacha_expertise"]:
        coll = chroma_client.get_or_create_collection(name=nom, embedding_function=emb_fn)
        # On utilise une recherche sémantique pour trouver l'info
        res = coll.query(query_texts=[mot_cle], n_results=3)
        
        if res['documents'][0]:
            print(f"\n📍 Trouvé dans {nom} :")
            for doc in res['documents'][0]:
                print(f" -> {doc}")

if __name__ == "__main__":
    # 1. On liste le contenu
    auditer_collection("natacha_relation")
    auditer_collection("natacha_expertise")
    
    # 2. Récupération de la saisie utilisateur
    # La chaîne entre guillemets est le message qui s'affichera dans la console
    terme_recherche = input("\nEntrez l'information à rechercher : ")
    
    # 3. Utilisation de la saisie pour la recherche
    if terme_recherche:
        chercher_info(terme_recherche)
    else:
        print("Aucun terme saisi, recherche annulée.")
