"""
Gestionnaire de Réponses & Templates Découplés (Domain Response Catalog).
Charge les réponses institutionnelles depuis data/domain/system_responses.json
et fournit un moteur de rendu i18n découplé du code source applicatif.
"""

import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESPONSES_PATH = os.path.join(BASE_DIR, "data", "domain", "system_responses.json")


class DomainCatalog:
    """Catalogue découplé des réponses institutionnelles et modèles de dialogue."""

    def __init__(self, responses_path: str = RESPONSES_PATH):
        self.responses_path = responses_path
        self._responses: Dict[str, Dict[str, str]] = {}
        self.reload()

    def reload(self) -> None:
        """Charge ou recharge le catalogue des réponses JSON."""
        if not os.path.exists(self.responses_path):
            logger.warning(f"[DomainCatalog] Fichier introuvable : {self.responses_path}")
            self._responses = {}
            return

        try:
            with open(self.responses_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._responses = data.get("responses", {})
            logger.debug(f"[DomainCatalog] {len(self._responses)} templates chargés avec succès.")
        except Exception as e:
            logger.error(f"[DomainCatalog] Erreur lecture {self.responses_path} : {e}")
            self._responses = {}

    def get(self, key: str, lang: str = "français", **kwargs: Any) -> str:
        """
        Récupère et formate la réponse correspondant à la clé et la langue.
        Gère les codes 'fr'/'français' et 'bm'/'bambara' avec repli gracieux.
        """
        norm_lang = "bm" if lang in ["bambara", "bm", "bamanankan"] else "fr"
        tmpl_dict = self._responses.get(key, {})

        template = tmpl_dict.get(norm_lang)
        if template is None:
            template = tmpl_dict.get("fr", "")

        if not template:
            logger.warning(f"[DomainCatalog] Template manquant pour la clé '{key}' (lang={lang}).")
            return ""

        if kwargs:
            try:
                return template.format(**kwargs)
            except KeyError as e:
                logger.error(f"[DomainCatalog] Paramètre manquant {e} pour formater '{key}'.")
                return template
        return template


# Singleton
_catalog_instance: Optional[DomainCatalog] = None


def get_domain_catalog() -> DomainCatalog:
    global _catalog_instance
    if _catalog_instance is None:
        _catalog_instance = DomainCatalog()
    return _catalog_instance
