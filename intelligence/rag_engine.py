"""
Moteur RAG Orchestrateur pour le DSP Chatbot Citoyen Malien.
Coordonne la recherche vectorielle dense et la synthèse générative Mistral.
"""

import os
import logging
from typing import Any, Dict, List, Optional

from .vector_store import get_vector_store, DocumentChunk
from .llm_generator import get_llm_generator

logger = logging.getLogger(__name__)

DEFAULT_SIMILARITY_THRESHOLD = float(os.environ.get("DSP_SIMILARITY_THRESHOLD", "0.28"))


class RAGEngine:
    """Moteur RAG bilingue (Français & Bambara) pour l'administration publique."""

    def __init__(self, similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD):
        self.vector_store = get_vector_store()
        self.generator = get_llm_generator()
        self.similarity_threshold = similarity_threshold

    def answer_query(
        self,
        query: str,
        language: str = "fr",
        top_k: int = 2,
    ) -> Dict[str, Any]:
        """Exécute le pipeline RAG complet :
        1. Retrieval : Extraction des documents les plus similaires.
        2. Relevance Gate : Vérification du seuil de pertinence documentaire.
        3. Generation : Synthèse contextualisée Mistral ou réponse générale/polie hors-domaine.
        """
        logger.info(f"[RAGEngine] Requête reçue : '{query}' | langue={language}")

        # Détection préalable des questions évidentes de culture générale / géographie / personnalités
        q_low = query.lower()
        if any(w in q_low for w in ["capitale", "capital du", "capital de", "capitale du", "capitale de", "plus grande ville", "président de la", "president de la", "monnaie du mali"]):
            logger.info(f"[RAGEngine] Détection culture générale hors démarches : '{query}'.")
            answer_text = self.generator.generate_general(query=query, language=language)
            return {
                "answer": answer_text,
                "topic": "hors_domaine",
                "confidence": 0.12,
                "sources": [],
            }

        # 1. Étape de recherche vectorielle
        chunks: List[DocumentChunk] = self.vector_store.similarity_search(
            query=query,
            language=language,
            top_k=top_k,
        )

        if not chunks:
            logger.info("[RAGEngine] Aucun document candidat trouvé. Génération hors-domaine / culture générale.")
            answer_text = self.generator.generate_general(query=query, language=language)
            return {
                "answer": answer_text,
                "topic": "nlu_fallback",
                "confidence": 0.0,
                "sources": [],
            }

        top_chunk = chunks[0]

        # 2. Seuil de pertinence (Threshold Gate)
        # Évite d'attribuer une démarche administrative non pertinente à une question hors-domaine
        # (ex: "Quelle est la capitale du Mali ?" ne doit pas renvoyer l'Acte de naissance).
        if top_chunk.score < self.similarity_threshold:
            logger.info(
                f"[RAGEngine] Score maximal faible ({top_chunk.score:.3f} pour '{top_chunk.topic}') "
                f"< seuil ({self.similarity_threshold}). Redirection vers connaissances générales."
            )
            answer_text = self.generator.generate_general(query=query, language=language)
            return {
                "answer": answer_text,
                "topic": "hors_domaine",
                "confidence": round(top_chunk.score, 2),
                "sources": [],
            }

        # 3. Étape de génération / synthèse contextualisée sur documents officiels
        context_texts = [c.content for c in chunks if c.score >= self.similarity_threshold * 0.7]
        if not context_texts:
            context_texts = [top_chunk.content]

        answer_text = self.generator.generate(
            query=query,
            context_chunks=context_texts,
            language=language,
            topic_title=top_chunk.title,
        )

        return {
            "answer": answer_text,
            "topic": top_chunk.topic,
            "confidence": min(0.98, round(top_chunk.score, 2)),
            "sources": [
                {
                    "title": c.title,
                    "topic": c.topic,
                    "score": c.score,
                }
                for c in chunks
                if c.score >= self.similarity_threshold * 0.7
            ],
        }


# Singleton
_rag_engine_instance = None

def get_rag_engine() -> RAGEngine:
    global _rag_engine_instance
    if _rag_engine_instance is None:
        _rag_engine_instance = RAGEngine()
    return _rag_engine_instance
