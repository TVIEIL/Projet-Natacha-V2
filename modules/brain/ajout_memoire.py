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
# PROJET NATACHA - MODULE AJOUT DONNEES DANS CHROMADB
# ==============================================================================

import chromadb
from chromadb.utils import embedding_functions
import time
import argparse
import os

# --- CONFIGURATION (Identique à ton bridge Natacha) ---
DB_PATH = "./memoire_chroma"
COLLECTIONS = {
    "relation": "natacha_relation",
    "expertise": "natacha_expertise"
}

def ajouter_document(target, content):
    """
    Ajoute un document dans la collection spécifiée avec un ID unique basé sur le timestamp.
    """
    # 1. Initialisation du client
    if not os.path.exists(DB_PATH):
        print(f"⚠️ Le dossier {DB_PATH} n'existe pas. Il sera créé.")
    
    client = chromadb.PersistentClient(path=DB_PATH)
    emb_fn = embedding_functions.DefaultEmbeddingFunction()

    # 2. Récupération de la collection
    collection_name = COLLECTIONS.get(target)
    if not collection_name:
        print(f"❌ Erreur : La cible '{target}' est invalide. Utilise 'relation' ou 'expertise'.")
        return

    collection = client.get_or_create_collection(
        name=collection_name, 
        embedding_function=emb_fn
    )

    # 3. Préparation des données
    doc_id = f"{target[:3]}_{int(time.time())}"
    
    # 4. Insertion
    try:
        collection.add(
            documents=[content],
            ids=[doc_id]
        )
        print(f"✅ Document ajouté avec succès dans '{collection_name}' !")
        print(f"🆔 ID : {doc_id}")
        print(f"📄 Contenu : {content[:50]}...")
    except Exception as e:
        print(f"❌ Erreur lors de l'insertion : {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ajouter des données à la mémoire de Natacha.")
    parser.add_argument("--target", choices=["relation", "expertise"], required=True, 
                        help="Collection cible : 'relation' (perso) ou 'expertise' (savoir).")
    parser.add_argument("--content", type=str, required=True, 
                        help="Le texte à mémoriser.")

    args = parser.parse_args()
    ajouter_document(args.target, args.content)
