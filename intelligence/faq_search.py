"""
Moteur de recherche FAQ et Base de connaissances administratives (DSP).
Fournit la recherche sémantique bilingue (Français & Bambara) pour l'endpoint gRPC SearchKnowledge.
"""

import json
import logging
import math
import os
import re
import unicodedata
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FAQ_PATH = os.path.join(_BASE_DIR, "data", "faq", "faq_demarches.json")


_STOP_WORDS = {
    "le", "la", "les", "un", "une", "des", "du", "de", "d", "au", "aux", "en", "et", "ou",
    "est", "ce", "qui", "que", "pour", "dans", "par", "sur", "avec", "comment", "faire",
    "avoir", "je", "tu", "il", "elle", "nous", "vous", "ils", "mon", "ma", "mes", "son",
    "sa", "ses", "notre", "votre", "leur", "mali", "malien", "maliens", "pays",
    "bɛ", "be", "ka", "la", "na", "ye", "ma", "kɔnɔ", "kono", "fɛ", "fe", "ni", "an", "i", "ne",
    "dɛmɛ", "deme", "kɛ", "ke"
}


def _norm_lang(lang: Optional[str]) -> Optional[str]:
    """Normalise le code langue vers 'fr' ou 'bm'."""
    if not lang:
        return None
    l = lang.lower().strip()
    if l in ["fr", "français", "francais", "french"]:
        return "fr"
    if l in ["bm", "bambara", "bamanankan"]:
        return "bm"
    return l


def _normalize_text(text: str) -> str:
    """Normalise une chaîne de texte (minuscules, suppression des diacritiques)."""
    if not text:
        return ""
    text = text.lower()
    # Conserver les caractères spécifiques au bambara (ɛ, ɔ, ɲ, ŋ) avant décomposition
    char_map = {"ɛ": "ε", "ɔ": "ɔ", "ɲ": "ɲ", "ŋ": "ŋ"}
    for k, v in char_map.items():
        text = text.replace(k, v)
    
    # Normalisation unicode standard
    nfkd = unicodedata.normalize("NFKD", text)
    cleaned = "".join([c for c in nfkd if not unicodedata.combining(c)])
    # Remplacement de la ponctuation par des espaces
    return re.sub(r"[^\w\sεɔɲŋ]", " ", cleaned).strip()


def _tokenize(text: str, filter_stops: bool = False) -> List[str]:
    """Découpe en tokens normalisés avec filtrage optionnel des mots vides."""
    norm = _normalize_text(text)
    tokens = [t for t in norm.split() if len(t) > 1]
    if filter_stops:
        filtered = [t for t in tokens if t not in _STOP_WORDS]
        return filtered if filtered else tokens
    return tokens


class FAQSearchEngine:
    """Moteur de recherche basé sur le modèle de pertinence TF-IDF / BM25 optimisé."""

    def __init__(self, faq_file_path: Optional[str] = None):
        self.faq_path = faq_file_path or _FAQ_PATH
        self.documents: List[Dict[str, Any]] = []
        self.doc_tokens: List[List[str]] = []
        self.avg_doc_len: float = 0.0
        self.idf: Dict[str, float] = {}
        self.load_index()

    def load_index(self) -> None:
        """Charge et indexe les documents de la FAQ."""
        self.documents = []
        self.doc_tokens = []
        if not os.path.exists(self.faq_path):
            logger.warning(f"Fichier FAQ introuvable : {self.faq_path}")
            return

        try:
            with open(self.faq_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Erreur lors de la lecture du fichier FAQ : {e}")
            return

        categories = data.get("categories", [])
        for cat in categories:
            cat_id = cat.get("id", "")
            title_fr = cat.get("title_fr", "")
            title_bm = cat.get("title_bm", "")
            ans_fr = cat.get("answer_fr", "")
            ans_bm = cat.get("answer_bm", "")
            q_fr = cat.get("questions_fr", [])
            q_bm = cat.get("questions_bm", [])

            # Indexation document Français avec boost de titre
            content_fr = f"{cat_id} {title_fr} {title_fr} {' '.join(q_fr)} {ans_fr} {cat.get('pieces_fr', '')} {cat.get('cout_fr', '')}"
            self.documents.append({
                "topic": cat_id,
                "title": title_fr,
                "content": ans_fr,
                "language": "fr",
                "raw_text": content_fr,
            })

            # Indexation document Bambara avec boost de titre
            content_bm = f"{cat_id} {title_bm} {title_bm} {' '.join(q_bm)} {ans_bm} {cat.get('pieces_bm', '')} {cat.get('cout_bm', '')}"
            self.documents.append({
                "topic": cat_id,
                "title": title_bm,
                "content": ans_bm,
                "language": "bm",
                "raw_text": content_bm,
            })

        # Calcul des statistiques BM25
        n_docs = len(self.documents)
        if n_docs == 0:
            return

        total_len = 0
        df: Dict[str, int] = {}
        for doc in self.documents:
            tokens = _tokenize(doc["raw_text"])
            self.doc_tokens.append(tokens)
            total_len += len(tokens)
            unique_tokens = set(tokens)
            for t in unique_tokens:
                df[t] = df.get(t, 0) + 1

        self.avg_doc_len = total_len / n_docs if n_docs > 0 else 1.0

        for term, freq in df.items():
            # Formule standard IDF BM25 avec lissage
            self.idf[term] = math.log(1.0 + (n_docs - freq + 0.5) / (freq + 0.5))

    def search(
        self,
        query: str,
        language: Optional[str] = None,
        top_k: int = 3,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> List[Dict[str, Any]]:
        """Recherche les documents les plus pertinents pour une requête donnée."""
        if not query or not self.documents:
            return []

        q_tokens = _tokenize(query, filter_stops=True)
        if not q_tokens:
            q_tokens = _tokenize(query, filter_stops=False)
        if not q_tokens:
            return []

        target_lang = _norm_lang(language)
        scores: List[float] = []
        for i, (doc, tokens) in enumerate(zip(self.documents, self.doc_tokens)):
            # Filtrage éventuel par langue si spécifiée
            if target_lang and doc.get("language") != target_lang:
                scores.append(-1.0)
                continue

            doc_len = len(tokens)
            score = 0.0

            # Calcul des fréquences de termes dans le document
            tf_dict: Dict[str, int] = {}
            for t in tokens:
                tf_dict[t] = tf_dict.get(t, 0) + 1

            for q_term in q_tokens:
                if q_term in tf_dict:
                    tf = tf_dict[q_term]
                    idf = self.idf.get(q_term, 0.5)
                    numerator = tf * (k1 + 1.0)
                    denominator = tf + k1 * (1.0 - b + b * (doc_len / self.avg_doc_len))
                    score += idf * (numerator / denominator)

            scores.append(score)

        # Tri par score décroissant
        ranked_indices = sorted(
            [idx for idx, s in enumerate(scores) if s > 0],
            key=lambda idx: scores[idx],
            reverse=True,
        )

        results = []
        for idx in ranked_indices[:top_k]:
            doc = self.documents[idx]
            results.append({
                "topic": doc["topic"],
                "title": doc["title"],
                "content": doc["content"],
                "score": round(float(scores[idx]), 4),
            })

        return results


# Instance singleton
_engine: Optional[FAQSearchEngine] = None

def get_faq_engine() -> FAQSearchEngine:
    global _engine
    if _engine is None:
        _engine = FAQSearchEngine()
    return _engine

def search_knowledge_base(query: str, language: Optional[str] = None, top_k: int = 3) -> List[Dict[str, Any]]:
    """Point d'entrée direct pour la recherche sémantique."""
    engine = get_faq_engine()
    return engine.search(query=query, language=language, top_k=top_k)
