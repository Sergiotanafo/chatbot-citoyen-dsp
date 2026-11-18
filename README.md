# Chatbot Citoyen Malien — DSP (Data Science Platform)

## 1. Présentation du projet

Ce dépôt contient le composant **DSP (Data Science Platform)** du projet Chatbot Citoyen Malien.

Il implémente une **Architecture Hybride Pérenne** associant :
- **Rasa NLU & Core** : gestion des flux de dialogue de haut niveau (macro-intentions, changement de langue, salutations, contextualisation multi-tours).
- **Moteur RAG (Retrieval-Augmented Generation)** :
  - **Dense & Hybrid Vector Store** : recherche sémantique multilingue (Français & Bambara).
  - **Synthétiseur Génératif Mistral / LLM** : formulation de réponses fluides, exactes et sourcées sur l'ensemble des démarches administratives sans multiplication infinie d'intentions.
- **Pipeline Speech bilingue (ASR & TTS)** : transcription audio 16 kHz et synthèse vocale avec découpage adaptatif en phrases.
- **Serveur gRPC haute performance** : exposition autonome sur le port `50051` vers le backend FastAPI.

---

## 2. Architecture du DSP

```text
chatbot-citoyen-dsp/
├── actions/
│   ├── __init__.py
│   └── actions.py                    # 8 Custom Actions Rasa (détection langue, démarches, FAQ)
├── configs/
│   ├── rasa_config.yml               # Pipeline NLU bilingue (DIET + FastText Bambara)
│   ├── config_eval.yml               # Configuration d'évaluation
│   ├── endpoints.yml                 # Configuration Action Server (port 5055)
│   └── credentials.yml               # Canaux de communication
├── custom_components/
│   └── bambara_featurizer.py         # Featurizer d'embeddings Bambara (.vec)
├── data/
│   ├── nlu/
│   │   ├── nlu.yml                   # Dataset d'entraînement FR & Bambara
│   │   └── frustration_examples.yml  # Détection de l'insatisfaction usager
│   ├── stories.yml                   # Scénarios de dialogue multi-tours
│   ├── rules.yml                     # Règles d'engagement strictes (salutations, fallback)
│   └── faq/
│       └── faq_demarches.json        # Base de connaissances administrative structurée
├── intelligence/
│   ├── domain.yml                    # Intents, entités, slots, actions, réponses officielles
│   ├── router.py                     # Routeur Hybride : Macro-Dialogue + RAG Administratif
│   ├── rag_engine.py                 # Moteur RAG bilingue (Dense Retrieval + Synthèse)
│   ├── vector_store.py               # Dense & Hybrid Vector Store (Français & Bambara)
│   ├── llm_generator.py              # Générateur Mistral / Ollama / Fallback déterministe
│   └── faq_search.py                 # Recherche par pertinence BM25
├── proto/
│   └── dsp_service.proto             # Contrat d'interface gRPC pour le backend
├── service/
│   └── grpc_server.py                # Serveur gRPC autonome (Port 50051)
├── speech/
│   ├── asr_service.py                # Reconnaissance vocale bilingue + rééchantillonnage 16 kHz
│   ├── tts_service.py                # Synthèse vocale bilingue + découpage en phrases
│   └── text_cleaning.py              # Nettoyage phonétique et normalisation des acronymes
├── tests/
│   ├── test_nlu.yml                  # Dataset de test indépendant (0 data leakage)
│   ├── test_data_integrity.py        # Validation absence de fuite de données et domaine
│   ├── test_faq_search.py            # Validation du moteur de recherche sémantique
│   ├── test_actions.py               # Validation des custom actions Rasa
│   ├── test_speech.py                # Validation du prétraitement audio et TTS
│   ├── test_vector_store.py          # Validation de l'indexation et similarité vectorielle
│   ├── test_rag_engine.py            # Validation du pipeline RAG
│   ├── test_hybrid_router.py         # Validation de l'aiguillage hybride
│   └── test_grpc_servicer.py         # Validation de l'implémentation gRPC
├── scripts/
│   ├── chat_dsp.bat                  # Console interactive de test (Français & Bambara)
│   ├── run_tests.bat                 # Exécution de la suite de tests (47 tests validés)
│   ├── run_dsp_server.bat            # Démarrage du serveur gRPC DSP
│   ├── ingest_knowledge.py           # Scraping & Ingestion documentaire des portails maliens (.gov.ml)
│   ├── train_rasa.bat                # Entraînement Rasa
│   ├── evaluate_rasa.bat             # Évaluation NLU sur test set isolé
│   └── generate_proto.bat            # Génération des stubs gRPC
└── requirements.txt                  # Dépendances Python du DSP
```

---

## 3. L'Architecture Hybride Pérenne (Rasa + RAG Mistral Bilingue)

Plutôt que d'enfermer le chatbot dans le **piège de la prolifération des intentions** (vouloir annoter 1 000 intentions Rasa manuellement), le DSP sépare les responsabilités :

### A. Rasa Macro-Dialogue (10 à 15 intentions clés)
- **Salutations & Clôture bilingues** : `saluer`, `au_revoir` (Français & Bambara).
- **Contrôle linguistique & Détection fine** : `changer_langue` (basculement dynamique FR/BM avec insensibilité aux questions lexicales).
- **Suivi contextuel en mémoire** : `demander_cout`, `demander_documents`, `demander_delai`.

### B. Moteur RAG & Embeddings Vectoriels Bilingues Miroirs
- **Couverture intégrale des démarches en Bambara** (`_bm.md`) : Chaque démarche administrative possède son pendant authentique en Bamanankan (84 documents et sections indexés au total).
- **Normalisation Phonétique & Tolérance Clavier ASCII** :
  - Invariance graphématique : `ny` / `gn` $\rightarrow$ `ɲ`, `ng` $\rightarrow$ `ŋ`.
  - Invariance voyelles ouvertes : unification `ɛ`/`e` et `ɔ`/`o` pour que la saisie mobile courante (SMS sans touches spéciales, ex: *« pasan songo »*, *« dugukolo seben »*) matche parfaitement les textes officiels (*« pasan sɔngɔ »*, *« dugukolo sɛbɛn »*).
  - Élimination des contractions : `mbe` $\rightarrow$ `n be`, `nte` $\rightarrow$ `n te`.
- **Cross-Lingual Retrieval Fallback** : Si une requête en Bambara utilise des termes ou sigles administratifs d'emprunt (ex: *« quitus fiscal »*, *« titre foncier »*), le moteur explore les fiches francophones pour permettre à Mistral de synthétiser la réponse en Bambara naturel.
- **Guardrails Bilingues** : Refus d'actes frauduleux, recadrage de tâches informatiques et désescalade empathique restitués dans la langue de l'usager.

---

## 4. Guide d'Exécution Rapide

### 1. Dialoguer avec l'assistant (Console Interactive)
```cmd
scripts\chat_dsp.bat
```
*(ou `python scripts\interactive_chat.py`)*

### 2. Lancer la suite de tests automatisés (47 tests)
```cmd
scripts\run_tests.bat
```
*(ou `python -m unittest discover -s tests -p "test_*.py" -v`)*

### 3. Démarrer le serveur gRPC DSP (Port 50051)
```cmd
scripts\run_dsp_server.bat
```
*(ou `python service/grpc_server.py`)*
