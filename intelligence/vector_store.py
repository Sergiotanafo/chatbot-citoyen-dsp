"""
Dense & Hybrid Vector Store pour le DSP Chatbot Citoyen Malien.
Permet l'indexation et la recherche vectorielle multilingue (Français & Bambara).
Supporte Sentence-Transformers (Dense Neural) avec fallback TF-IDF/BM25 dense vectoriel.
"""

import json
import logging
import math
import os
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAQ_PATH = os.path.join(BASE_DIR, "data", "faq", "faq_demarches.json")
KNOWLEDGE_DIR = os.path.join(BASE_DIR, "data", "knowledge")
DEFAULT_EMBEDDING_MODEL = os.environ.get(
    "DSP_EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2"
)


@dataclass
class DocumentChunk:
    chunk_id: str
    topic: str
    title: str
    content: str
    language: str  # "fr" ou "bm"
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


FRENCH_STOPWORDS = {
    "le", "la", "les", "un", "une", "des", "du", "de", "d", "l",
    "est", "sont", "ete", "etre", "avoir", "pour", "dans", "sur",
    "avec", "par", "qui", "que", "quoi", "quel", "quelle", "quels",
    "quelles", "mali", "malien", "malienne", "ce", "cet",
    "cette", "ces", "au", "aux", "en", "se", "sa", "son", "ses"
}


def normalize_text(text: str) -> str:
    """Normalise une chaîne de texte pour l'indexation avec tolérance phonétique bilingue (FR & BM).
    Gère l'invariance phonétique et les claviers ASCII (ex: 'seben' <-> 'sɛbɛn', 'songo' <-> 'sɔngɔ').
    """
    if not text:
        return ""
    text = text.lower()

    # 1. Normalisation phonétique Bambara (digraphes & élisions courantes)
    text = re.sub(r"\b(mbe|m'be|m'bɛ|nbe)\b", "n be", text)
    text = re.sub(r"\b(nte|n'te|n'tɛ)\b", "n te", text)
    text = re.sub(r"\b(k'a|ka a)\b", "ka a", text)
    text = re.sub(r"ny", "ɲ", text)
    text = re.sub(r"gn", "ɲ", text)
    text = re.sub(r"ng", "ŋ", text)

    # 2. Tolérance clavier ASCII pour les voyelles ouvertes Bambara
    # Permet d'unifier l'orthographe officielle (sɛbɛn, sɔngɔ) et la saisie mobile (seben, songo)
    text = text.replace("ɛ", "e").replace("ɔ", "o")

    # 3. Normalisation Unicode
    nfkd = unicodedata.normalize("NFKD", text)
    cleaned = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return re.sub(r"[^\w\sɲŋ]", " ", cleaned).strip()


class DenseVectorStore:
    """Magasin vectoriel haute performance supportant les embeddings neuronaux et le mode hybride."""

    def __init__(self, embedding_model_name: str = DEFAULT_EMBEDDING_MODEL):
        self.model_name = embedding_model_name
        self.dense_model = None
        self.chunks: List[DocumentChunk] = []
        self.vectors: List[List[float]] = []
        self.vocab: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}

        self._init_encoder()
        self.index_knowledge_base()

    def _init_encoder(self):
        """Tente d'initialiser le modèle d'embeddings neuronaux."""
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"[VectorStore] Chargement du modèle neural '{self.model_name}'...")
            self.dense_model = SentenceTransformer(self.model_name)
            logger.info("[VectorStore] Modèle d'embeddings dense opérationnel.")
        except Exception as e:
            logger.info(
                f"[VectorStore] Sentence-Transformers non actif ({e}). "
                "Mode vectoriel Dense TF-IDF / Sous-mots actif."
            )
            self.dense_model = None

    def index_knowledge_base(self, json_path: Optional[str] = None):
        """Indexe les documents administratifs de la base de connaissances."""
        target_path = json_path or FAQ_PATH
        self.chunks = []
        self.vectors = []

        if not os.path.exists(target_path):
            logger.warning(f"[VectorStore] Fichier FAQ introuvable : {target_path}")
            return

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"[VectorStore] Erreur lecture FAQ : {e}")
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
            pieces_fr = cat.get("pieces_fr", "")
            pieces_bm = cat.get("pieces_bm", "")
            cout_fr = cat.get("cout_fr", "")
            cout_bm = cat.get("cout_bm", "")
            delai_fr = cat.get("delai_fr", "")
            delai_bm = cat.get("delai_bm", "")

            # Document Français
            full_fr = (
                f"{title_fr}\n"
                f"Questions fréquentes : {' | '.join(q_fr)}\n"
                f"Démarche & Détails : {ans_fr}\n"
                f"Pièces à fournir : {pieces_fr}\n"
                f"Frais officiels : {cout_fr}\n"
                f"Délais légaux : {delai_fr}"
            )
            self.chunks.append(
                DocumentChunk(
                    chunk_id=f"{cat_id}_fr",
                    topic=cat_id,
                    title=title_fr,
                    content=full_fr,
                    language="fr",
                    metadata={
                        "answer": ans_fr,
                        "pieces": pieces_fr,
                        "cout": cout_fr,
                        "delai": delai_fr,
                    },
                )
            )

            # Document Bambara
            full_bm = (
                f"{title_bm}\n"
                f"Ñininkaliw : {' | '.join(q_bm)}\n"
                f"Baara cogo : {ans_bm}\n"
                f"Sɛbɛn minnu bɛ ɲini : {pieces_bm}\n"
                f"Wari sɔngɔ : {cout_bm}\n"
                f"Waati joli : {delai_bm}"
            )
            self.chunks.append(
                DocumentChunk(
                    chunk_id=f"{cat_id}_bm",
                    topic=cat_id,
                    title=title_bm,
                    content=full_bm,
                    language="bm",
                    metadata={
                        "answer": ans_bm,
                        "pieces": pieces_bm,
                        "cout": cout_bm,
                        "delai": delai_bm,
                    },
                )
            )

        # Indexation automatique des documents bruts (Markdown/Texte) de data/knowledge/
        self._index_knowledge_directory()

        # Calcul des vecteurs pour tous les chunks
        if self.dense_model:
            texts = [c.content for c in self.chunks]
            embs = self.dense_model.encode(texts, convert_to_numpy=True)
            self.vectors = [list(map(float, vec)) for vec in embs]
        else:
            self._build_subword_vectors()

        logger.info(f"[VectorStore] Indexation terminée : {len(self.chunks)} documents indexés.")

    def _index_knowledge_directory(self):
        """Scanne data/knowledge et découpe automatiquement les fichiers .md et .txt en chunks."""
        if not os.path.exists(KNOWLEDGE_DIR):
            return

        for filename in os.listdir(KNOWLEDGE_DIR):
            if filename.endswith(".md") or filename.endswith(".txt"):
                filepath = os.path.join(KNOWLEDGE_DIR, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as fh:
                        content = fh.read()

                    # Découpage par sections spécifiques (### Titre du concept)
                    sections = re.split(r"\n(?=###\s+)", content)
                    for idx, sec in enumerate(sections):
                        sec = sec.strip()
                        lines = [l.strip() for l in sec.split("\n") if l.strip()]
                        if not lines:
                            continue

                        # Trouver la ligne de titre (qui commence par #)
                        title_lines = [l for l in lines if l.startswith("#")]
                        if not title_lines:
                            continue
                        first_line = title_lines[0].replace("#", "").strip()

                        # Corps du texte sans les lignes d'en-tête
                        body_lines = [l for l in lines if not l.startswith("#") and not l.startswith("---")]
                        body = "\n".join(body_lines).strip()
                        if len(body) < 30:
                            continue

                        chunk_id = f"{filename}_{idx}"
                        topic_slug = re.sub(r"[^\w]+", "_", first_line.lower()).strip("_")
                        doc_lang = "bm" if (filename.endswith("_bm.md") or "_bm" in filename) else "fr"

                        self.chunks.append(
                            DocumentChunk(
                                chunk_id=chunk_id,
                                topic=topic_slug,
                                title=first_line,
                                content=f"{first_line}\n\n{body}",
                                language=doc_lang,
                                metadata={"source": filename, "type": "knowledge_doc", "body": body},
                            )
                        )
                except Exception as e:
                    logger.error(f"[VectorStore] Erreur lecture document {filename}: {e}")

    def _tokenize(self, text: str) -> List[str]:
        norm = normalize_text(text)
        tokens = [t for t in norm.split() if len(t) > 1]
        filtered = [t for t in tokens if t not in FRENCH_STOPWORDS]
        return filtered if filtered else tokens

    def _build_subword_vectors(self):
        """Génère une représentation vectorielle dense basée sur les n-grammes de sous-mots."""
        doc_tokens = [self._tokenize(c.content) for c in self.chunks]
        n_docs = len(doc_tokens)
        df: Dict[str, int] = {}
        for tokens in doc_tokens:
            for t in set(tokens):
                df[t] = df.get(t, 0) + 1

        # Construction du vocabulaire ordonné
        self.vocab = {term: idx for idx, term in enumerate(df.keys())}
        self.idf = {
            term: math.log(1.0 + (n_docs - count + 0.5) / (count + 0.5))
            for term, count in df.items()
        }

        dim = len(self.vocab)
        self.vectors = []
        for tokens in doc_tokens:
            vec = [0.0] * dim
            for t in tokens:
                if t in self.vocab:
                    vec[self.vocab[t]] += self.idf.get(t, 1.0)
            # Normalisation L2
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            self.vectors.append([x / norm for x in vec])

    def similarity_search(
        self,
        query: str,
        language: str = "fr",
        top_k: int = 3,
    ) -> List[DocumentChunk]:
        """Effectue une recherche par similarité cosinus dense."""
        if not query or not self.chunks:
            return []

        target_lang = "bm" if language.lower() in ["bm", "bambara", "bamanankan"] else "fr"

        # Vecteur de la requête
        if self.dense_model:
            q_emb = self.dense_model.encode([query], convert_to_numpy=True)[0]
            q_norm = math.sqrt(sum(x * x for x in q_emb)) or 1.0
            q_vec = [float(x) / q_norm for x in q_emb]
        else:
            q_tokens = self._tokenize(query)
            dim = len(self.vocab)
            q_vec = [0.0] * dim
            for t in q_tokens:
                if t in self.vocab:
                    q_vec[self.vocab[t]] += self.idf.get(t, 1.0)
            q_norm = math.sqrt(sum(x * x for x in q_vec)) or 1.0
            q_vec = [x / q_norm for x in q_vec]

        # Calcul similarité cosinus avec filtrage linguistique
        scored_candidates: List[Tuple[float, DocumentChunk]] = []
        for doc, doc_vec in zip(self.chunks, self.vectors):
            if doc.language != target_lang:
                continue

            sim = sum(a * b for a, b in zip(q_vec, doc_vec))
            # Bonus si des mots clés du titre sont présents dans la requête (inclut acronymes comme CNI, AMO, NIF, DEF)
            norm_q = normalize_text(query)
            for word in normalize_text(doc.title).split():
                if len(word) >= 3 and word not in FRENCH_STOPWORDS and word not in ["les", "des", "une", "par", "sur", "qui", "que"] and word in norm_q:
                    sim += 0.25

            doc_copy = DocumentChunk(
                chunk_id=doc.chunk_id,
                topic=doc.topic,
                title=doc.title,
                content=doc.content,
                language=doc.language,
                score=round(float(sim), 4),
                metadata=doc.metadata,
            )
            scored_candidates.append((sim, doc_copy))

        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        # Cross-lingual Fallback : Si les documents Bambara directs ont un score faible (< 0.28),
        # explorer les documents francophones contenant des termes administratifs empruntés (ex: titre foncier, quitus)
        if target_lang == "bm" and (not scored_candidates or scored_candidates[0][0] < 0.28):
            for doc, doc_vec in zip(self.chunks, self.vectors):
                if doc.language != "fr":
                    continue
                sim = sum(a * b for a, b in zip(q_vec, doc_vec))
                norm_q = normalize_text(query)
                for word in normalize_text(doc.title).split():
                    if len(word) > 3 and word in norm_q:
                        sim += 0.25
                if sim > 0.25:
                    doc_copy = DocumentChunk(
                        chunk_id=doc.chunk_id,
                        topic=doc.topic,
                        title=doc.title,
                        content=doc.content,
                        language="bm",
                        score=round(float(sim), 4),
                        metadata=doc.metadata,
                    )
                    scored_candidates.append((sim, doc_copy))
            scored_candidates.sort(key=lambda x: x[0], reverse=True)

        return [c for score, c in scored_candidates[:top_k] if score > 0.05]


# Singleton global
_vector_store_instance = None

def get_vector_store() -> DenseVectorStore:
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = DenseVectorStore()
    return _vector_store_instance
