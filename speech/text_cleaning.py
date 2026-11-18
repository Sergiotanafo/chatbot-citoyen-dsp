"""
Utilitaires de nettoyage et de prétraitement textuel pour la synthèse vocale (TTS).
"""

import re
from typing import List

_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002600-\U000026FF"
    "\U00002700-\U000027BF"
    "\U0000FE00-\U0000FE0F"
    "\U00002000-\U0000206F"
    "\U00003300-\U00003FFF"
    "\U0000FFF0-\U0000FFFF"
    "]+",
    flags=re.UNICODE,
)

REPLACEMENTS_FR = {
    r"\b(FCFA|CFA)\b": "franc CFA",
    r"\bCNI\b": "C N I",
    r"\bDGPN\b": "direction générale de la police",
    r"\bDPF\b": "direction de la police aux frontières",
    r"\bRAVEC\b": "ravec",
    r"\bNINA\b": "nina",
    r"\bEDM\b": "énergie du mali",
    r"\bSOMAGEP\b": "somagep",
    r"\b(N°|n°)\b": "numéro",
}

REPLACEMENTS_BM = {
    r"\b(FCFA|CFA)\b": "dɔrɔmɛ",
    r"\bCNI\b": "se en i fasodenya sariyasɛbɛn",
    r"\bDGPN\b": "polisiba",
    r"\bNINA\b": "nina nimɔrɔ",
    r"\bRAVEC\b": "ravec",
    r"\bAMO\b": "a em o",
    r"\bINPS\b": "i en pe es",
}


def clean_for_tts(text: str, language: str = "fr") -> str:
    """Nettoie le texte pour la synthèse vocale :
    - Élimine le markdown (*, _, `, #, bullet points).
    - Supprime les émojis.
    - Développe phonétiquement les sigles et acronymes selon la langue (FR ou BM).
    """
    if not text:
        return ""

    # Choix du dictionnaire de phonétisation d'acronymes
    rep_dict = REPLACEMENTS_BM if language.lower() in ["bm", "bambara", "bamanankan"] else REPLACEMENTS_FR

    # Suppression émojis
    text = _EMOJI_PATTERN.sub("", text)
    # Suppression liens markdown [titre](url)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Suppression mise en forme gras/italique
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,3}([^_]+)_{1,3}", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Suppression des puces et listes numérotées
    text = re.sub(r"^[\s•\-–—*]+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\d+[\.\)]\s*", "", text, flags=re.MULTILINE)

    # Remplacement des acronymes administratifs
    for pattern, v in rep_dict.items():
        text = re.sub(pattern, v, text, flags=re.IGNORECASE)

    # Nettoyage des espaces multiples
    return " ".join(text.split())


def chunk_text_for_tts(text: str, max_chars: int = 150) -> List[str]:
    """Découpe un texte long en segments naturels (phrases ou sous-phrases)
    adaptés aux limites de taille des modèles TTS.
    """
    cleaned = clean_for_tts(text)
    if not cleaned:
        return []

    if len(cleaned) <= max_chars:
        return [cleaned]

    # Séparation sur les fins de phrases d'abord
    raw_sentences = re.split(r"(?<=[.!?;\n])\s+", cleaned)
    chunks: List[str] = []

    for s in raw_sentences:
        s = s.strip()
        if not s:
            continue
        if len(s) <= max_chars:
            chunks.append(s)
        else:
            # Sous-découpage par virgules ou connecteurs
            parts = re.split(r"(?<=[,])\s+", s)
            curr = ""
            for p in parts:
                p = p.strip()
                if not p:
                    continue
                if len(curr) + len(p) + 1 <= max_chars:
                    curr = f"{curr} {p}".strip()
                else:
                    if curr:
                        chunks.append(curr)
                    curr = p
            if curr:
                chunks.append(curr)

    return chunks
