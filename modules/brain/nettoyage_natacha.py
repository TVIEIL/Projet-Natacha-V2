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
# PROJET NATACHA - MODULE SUPPRESSION DOUBLONS CHROMADB
# ==============================================================================
import chromadb
from chromadb.utils import embedding_functions

# --- CONFIGURATION ---
PATH_MEMOIRE = "./memoire_chroma"
chroma_client = chromadb.PersistentClient(path=PATH_MEMOIRE)
emb_fn = embedding_functions.DefaultEmbeddingFunction()

def nettoyer_collection(nom_collection):
    print(f"\n--- 🔍 Analyse de la collection : {nom_collection} ---")
    coll = chroma_client.get_or_create_collection(name=nom_collection, embedding_function=emb_fn)
    
    # Récupérer TOUT le contenu
    donnees = coll.get()
    ids = donnees['ids']
    documents = donnees['documents']
    
    if not ids:
        print("La collection est vide.")
        return

    vu = {} # Dictionnaire {contenu_normalise: id_a_garder}
    doublons = []

    for i in range(len(documents)):
        texte_original = documents[i]
        id_doc = ids[i]
        
        # NORMALISATION : 
        # On prend tout ce qui est APRÈS le premier ":" pour ignorer la date
        if ":" in texte_original:
            contenu_normalise = texte_original.split(":", 1)[1].strip()
        else:
            contenu_normalise = texte_original.strip()

        # Comparaison du contenu épuré
        if contenu_normalise in vu:
            doublons.append(id_doc)
            print(f"  [X] Doublon détecté : '{contenu_normalise[:60]}...'")
        else:
            vu[contenu_normalise] = id_doc

    # Suppression effective dans ChromaDB
    if doublons:
        coll.delete(ids=doublons)
        print(f"✅ {len(doublons)} doublons supprimés de la collection.")
    else:
        print("✨ Aucun doublon trouvé (le contenu épuré est déjà unique).")
    
    print(f"📊 Total après nettoyage : {len(ids) - len(doublons)} entrées.")

if __name__ == "__main__":
    nettoyer_collection("natacha_relation")
    nettoyer_collection("natacha_expertise")
