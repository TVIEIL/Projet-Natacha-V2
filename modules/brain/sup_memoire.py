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
# PROJET NATACHA - MODULE SUPPRESSION ENREGISTREMENT CHROMADB
# ==============================================================================

import chromadb
from chromadb.utils import embedding_functions

# --- CONFIGURATION ---
PATH_MEMOIRE = "./memoire_chroma"
chroma_client = chromadb.PersistentClient(path=PATH_MEMOIRE)
emb_fn = embedding_functions.DefaultEmbeddingFunction()

def supprimer_par_id(nom_coll, id_a_supprimer):
    """Supprime une entrée spécifique via son ID (ex: 'exp_1714000000')"""
    coll = chroma_client.get_or_create_collection(name=nom_coll, embedding_function=emb_fn)
    try:
        coll.delete(ids=[id_a_supprimer])
        print(f"✅ L'ID '{id_a_supprimer}' a été supprimé de {nom_coll}.")
    except Exception as e:
        print(f"❌ Erreur lors de la suppression : {e}")

def supprimer_par_contenu(nom_coll, texte_cle):
    """Supprime les entrées contenant un mot spécifique"""
    coll = chroma_client.get_or_create_collection(name=nom_coll, embedding_function=emb_fn)
    
    # On cherche d'abord les IDs correspondants
    resultats = coll.get(where_document={"$contains": texte_cle})
    ids_a_supprimer = resultats['ids']
    
    if ids_a_supprimer:
        print(f"⚠️  Trouvé {len(ids_a_supprimer)} entrée(s) contenant '{texte_cle}'.")
        coll.delete(ids=ids_a_supprimer)
        print("✅ Suppression effectuée.")
    else:
        print(f"ℹ️  Aucune correspondance trouvée pour '{texte_cle}'.")

if __name__ == "__main__":
    print("--- 🗑️  OUTIL DE SUPPRESSION NATACHA ---")
    print("1. Supprimer par ID précis")
    print("2. Supprimer par mot-clé (contenu)")
    
    choix = input("\nChoisis une option (1 ou 2) : ")
    nom_c = input("Collection (natacha_relation ou natacha_expertise) : ")
    
    if choix == "1":
        target_id = input("Entre l'ID à supprimer : ")
        supprimer_par_id(nom_c, target_id)
    elif choix == "2":
        mot = input("Entre le texte/mot à chercher pour suppression : ")
        supprimer_par_contenu(nom_c, mot)
    else:
        print("Option invalide.")
