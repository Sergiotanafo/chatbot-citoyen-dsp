# Chatbot Citoyen Malien — DSP

## 1. Présentation du projet

Ce dépôt contient le composant **DSP (Data Science Platform)** du projet Chatbot Citoyen Malien.

Il regroupe les mécanismes d'intelligence artificielle, de compréhension du langage naturel, de recherche d'informations et de traitement de la parole.

L'objectif est de permettre au chatbot de comprendre et de traiter les demandes des citoyens en français et en bambara.

## 2. Objectifs

- Comprendre les demandes des utilisateurs.
- Gérer le dialogue conversationnel.
- Exploiter les embeddings multilingues.
- Effectuer des recherches sémantiques.
- Intégrer des modèles de langage.
- Permettre les interactions vocales.
- Fournir des réponses au backend via gRPC.

## 3. Architecture du DSP

Le composant DSP est organisé autour de plusieurs modules :

- **Application :** orchestration des traitements.
- **Infrastructure :** intégration des modèles et des services techniques.
- **Intelligence :** traitement du langage naturel, Rasa, embeddings et recherche sémantique.
- **Speech :** reconnaissance et synthèse vocales.

## 4. Technologies et composants

- Python
- Rasa
- Embeddings français–bambara
- Recherche sémantique
- LLM (modèles de langage)
- Reranker
- ASR (Automatic Speech Recognition)
- TTS (Text-to-Speech)
- gRPC et Protocol Buffers

## 5. Fonctionnalités prévues

### Compréhension du langage
- Analyse des intentions.
- Extraction des informations importantes.
- Gestion du contexte conversationnel.

### Recherche intelligente
- Vectorisation des textes.
- Recherche sémantique.
- Classement des résultats pertinents.

### Traitement vocal
- Reconnaissance de la parole.
- Transcription des requêtes vocales.
- Synthèse vocale des réponses.

### Communication
- Exposition des fonctionnalités via un serveur gRPC.
- Échanges structurés avec le backend.

## 6. Installation

Les instructions d'installation des dépendances, des modèles et des environnements seront ajoutées selon les composants retenus.

## 7. Gestion des modèles

Les modèles volumineux ne doivent pas nécessairement être stockés directement dans Git.

Leur téléchargement, leur versionnement et leur emplacement local seront documentés séparément.

## 8. Configuration

Les paramètres des modèles, les chemins des ressources et les configurations des services seront définis à travers des fichiers de configuration et des variables d'environnement.

## 9. Tests et évaluation

Les composants feront l'objet de tests portant notamment sur :
- La compréhension des requêtes en français et en bambara.
- La pertinence des recherches sémantiques.
- La qualité des réponses.
- Les performances des traitements vocaux.

## 10. Collaboration

Les contributions se font à travers des branches Git et des Pull Requests.

## 11. État du projet

Projet en cours de développement.

## 12. Équipe

Projet : Chatbot Citoyen Malien.
