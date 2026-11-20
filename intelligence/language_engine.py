"""
Moteur d'Identification de Langue et de Commutation Bilingue (Language Engine).
Gère la classification Français / Bambara avec tolérance phonétique, code-switching
et détection robuste des demandes citoyennes de bascule linguistique.
"""

import logging
import re
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Motifs Bambara (Phonétique officielle et translittération mobile sans caractères spéciaux)
BAMBARA_PATTERNS = [
    r"[ɛɔɲŋ]",
    r"\bi\s+ni\s+(sogoma|tile|su|wula|ce)\b",
    r"\baw\s+ni\s+(sogoma|tile|su|ce)\b",
    r"\b(bamanankan|tubabukan|kosɛbɛ|kosebe|hɛrɛ|here)\b",
    r"\b(sɔngɔ|songo|songon|cogo\s+di|wari\s+joli|mun\s+de|mun\s+kɛ|mun\s+ke|ye\s+mun\s+ye)\b",
    r"\b(sɛbɛn|seben|jumɛn|juman|fasodenya|denmisɛn|denmisen|bangebaga)\b",
    r"\b(wolosɛbɛn|woloseben|kititigɛso|kititigeso|dugutigi|dɛmɛ|deme|kɛnɛya|keneya)\b",
    r"\b(n\s+bɛ|n\s+be|mbe|nbe|n\s+mako|i\s+bɛ|i\s+be|i\s+ka|a\s+bɛ|a\s+be)\b",
    r"\b(pasan|pasipɔri|pasipori|kiti|ɲinini|nyinini|ɲini|nyini|dugukolo|tanburu)\b",
    r"\b(ye\s+\w+\s+ye|ye\s+joli\s+ye|ye\s+doli\s+ye|ye\s+mun\s+ye)\b",
    r"\b(sɔrɔ\s+cogo|soro\s+cogo|ka\s+sɔrɔ|ka\s+soro|bɛ\s+sɔrɔ|be\s+soro)\b",
]

# Motifs Français
FRENCH_PATTERNS = [
    r"\b(bonjour|salut|bonsoir|merci|s'il\s+vous\s+pla[iî]t|comment|pourquoi|combien)\b",
    r"\b(est-ce|qu'est-ce|qui|que|quoi|où|ou|quand|dans|avec|pour|sur)\b",
    r"\b(je|tu|il|elle|nous|vous|ils|le|la|les|un|une|des|du|de|d'un|d'une)\b",
    r"\b(carte|passeport|naissance|trouver|trouve|autorisation|parentale|mairie|commissariat)\b",
    r"\b(français|francais|document|documents|pièce|pièces|coût|prix|délai|légal)\b",
]


class LanguageEngine:
    """Moteur d'analyse linguistique pour le bilinguisme Français-Bambara."""

    def __init__(self):
        self._bm_regexes = [re.compile(p, re.IGNORECASE) for p in BAMBARA_PATTERNS]
        self._fr_regexes = [re.compile(p, re.IGNORECASE) for p in FRENCH_PATTERNS]

    def detect_language(self, text: str) -> str:
        """Détecte la langue dominante (bambara ou français)."""
        if not text:
            return "français"
        lowered = text.lower()
        bm_score = sum(1 for rgx in self._bm_regexes if rgx.search(lowered))
        fr_score = sum(1 for rgx in self._fr_regexes if rgx.search(lowered))

        if bm_score > fr_score:
            return "bambara"
        return "français"

    def check_language_switch_request(self, lowered: str) -> Optional[Tuple[str, str]]:
        """
        Détecte si l'utilisateur demande explicitement de basculer la langue.
        Retourne (nouvelle_langue, intent) ou None.
        """
        # Requêtes de bascule vers le Français
        if any(p in lowered for p in [
            "parle en français", "parle francais", "passe en français",
            "en français s'il te plaît", "en francais s'il te plait"
        ]) or (lowered.strip() in ["en français", "en francais", "francais", "français"]):
            return "français", "changement_langue_fr"

        # Requêtes de bascule vers le Bambara
        if any(p in lowered for p in [
            "parle en bambara", "parle bambara", "passe en bambara", "en bamanankan"
        ]) or (lowered.strip() in ["en bambara", "bambara", "bamanankan"]):
            if not any(neg in lowered for neg in ["non", "pas", "tɛ", "te"]):
                return "bambara", "changement_langue_bm"

        return None


# Singleton
_language_engine_instance: Optional[LanguageEngine] = None


def get_language_engine() -> LanguageEngine:
    global _language_engine_instance
    if _language_engine_instance is None:
        _language_engine_instance = LanguageEngine()
    return _language_engine_instance
