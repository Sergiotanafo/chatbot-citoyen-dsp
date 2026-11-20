import json
import logging
import os
import re
from typing import Any, Dict, List, Text, Optional

logger = logging.getLogger(__name__)

# Fallback gracieux si rasa_sdk n'est pas encore installé
try:
    from rasa_sdk import Action, Tracker
    from rasa_sdk.events import SlotSet
    from rasa_sdk.executor import CollectingDispatcher
except ImportError:
    class Action:
        def name(self) -> Text:
            raise NotImplementedError

        def run(
            self,
            dispatcher: Any,
            tracker: Any,
            domain: Dict[Text, Any],
        ) -> List[Dict[Text, Any]]:
            raise NotImplementedError

    class Tracker:
        def __init__(self, slots: Optional[Dict[str, Any]] = None, latest_message: Optional[Dict[str, Any]] = None):
            self._slots = slots or {}
            self.latest_message = latest_message or {}

        def get_slot(self, key: str) -> Any:
            return self._slots.get(key)

        def get_latest_input_channel(self) -> Optional[str]:
            return "default"

    class CollectingDispatcher:
        def __init__(self):
            self.messages = []

        def utter_message(self, text: Optional[str] = None, **kwargs):
            if text:
                self.messages.append({"text": text, **kwargs})

    def SlotSet(key: str, value: Any) -> Dict[str, Any]:
        return {"event": "slot", "name": key, "value": value}


# ─────────────────────────────────────────────────────────────
# Chargement de la base de connaissances FAQ
# ─────────────────────────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FAQ_PATH = os.path.join(_BASE_DIR, "data", "faq", "faq_demarches.json")

def load_faq_database() -> Dict[str, Any]:
    """Charge la base structurée des démarches administratives."""
    if os.path.exists(_FAQ_PATH):
        try:
            with open(_FAQ_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erreur chargement FAQ ({_FAQ_PATH}): {e}")
    return {"categories": []}


# Expressions régulières pour détecter le Bambara et le Français
_BAMBARA_PATTERNS = [
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

_FRENCH_PATTERNS = [
    r"\b(bonjour|salut|bonsoir|merci|s'il\s+vous\s+pla[iî]t|comment|pourquoi|combien)\b",
    r"\b(est-ce|qu'est-ce|qui|que|quoi|où|ou|quand|dans|avec|pour|sur)\b",
    r"\b(je|tu|il|elle|nous|vous|ils|le|la|les|un|une|des|du|de|d'un|d'une)\b",
    r"\b(carte|passeport|naissance|trouver|trouve|autorisation|parentale|mairie|commissariat)\b",
    r"\b(français|francais|document|documents|pièce|pièces|coût|prix|délai|légal)\b",
]

def detect_language(text: str) -> str:
    """Détecte avec robustesse si le texte saisi est en Bambara ou en Français."""
    try:
        from intelligence.language_engine import get_language_engine
        return get_language_engine().detect_language(text)
    except Exception:
        if not text:
            return "français"
        lowered = text.lower()
        bm_score = sum(1 for p in _BAMBARA_PATTERNS if re.search(p, lowered))
        fr_score = sum(1 for p in _FRENCH_PATTERNS if re.search(p, lowered))
        if bm_score > fr_score:
            return "bambara"
        return "français"


# ─────────────────────────────────────────────────────────────
# Actions Personnalisées
# ─────────────────────────────────────────────────────────────

class ActionDetecterEtGererSalutation(Action):
    """Détecte la langue dès la salutation et initialise le slot 'langue'."""

    def name(self) -> Text:
        return "action_detecter_et_gerer_salutation"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        user_text = tracker.latest_message.get("text", "")
        lang = detect_language(user_text)
        return [SlotSet("langue", lang)]


class ActionChangerLangue(Action):
    """Bascule explicitement la langue de l'échange (Français / Bambara)."""

    def name(self) -> Text:
        return "action_changer_langue"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        # Vérification si une entité langue a été extraite
        entities = tracker.latest_message.get("entities", [])
        target_lang = None
        for ent in entities:
            if ent.get("entity") == "langue":
                val = ent.get("value", "").lower()
                if val in ["bambara", "bamanankan"]:
                    target_lang = "bambara"
                elif val in ["français", "francais", "tubabukan"]:
                    target_lang = "français"

        if not target_lang:
            user_text = tracker.latest_message.get("text", "").lower()
            if any(w in user_text for w in ["bambara", "bamanankan"]):
                target_lang = "bambara"
            elif any(w in user_text for w in ["français", "francais", "tubabukan"]):
                target_lang = "français"
            else:
                target_lang = detect_language(user_text)

        return [SlotSet("langue", target_lang)]


class ActionRepondreChangementLangue(Action):
    """Confirme à l'utilisateur le basculement de langue opéré."""

    def name(self) -> Text:
        return "action_repondre_changement_langue"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        lang = tracker.get_slot("langue") or "français"
        try:
            from intelligence.domain_templates import get_domain_catalog
            catalog = get_domain_catalog()
            key = "changement_langue_bm" if lang == "bambara" else "changement_langue_fr"
            dispatcher.utter_message(text=catalog.get(key, lang=lang))
        except Exception:
            if lang == "bambara":
                dispatcher.utter_message(
                    text="Aw bisimila ! Ne bɛ kuma Bamanankan na sisan. N bɛ se ka i dɛmɛ cogo di ?"
                )
            else:
                dispatcher.utter_message(
                    text="Très bien ! Je communique désormais en français. Comment puis-je vous aider ?"
                )
        return []


class ActionSetDemarche(Action):
    """Enregistre la démarche courante dans le slot contextuel."""

    def name(self) -> Text:
        return "action_set_demarche"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        intent = tracker.latest_message.get("intent", {}).get("name", "")
        # Normalisation des sous-intents vers les démarches de base
        mapping = {
            "carte_identite": "carte_identite",
            "demande_passeport": "demande_passeport",
            "passeport_mali": "demande_passeport",
            "passeport_etranger": "demande_passeport",
            "demande_acte_naissance": "demande_acte_naissance",
            "acte_mariage": "acte_mariage",
            "acte_deces": "acte_deces",
            "casier_judiciaire": "casier_judiciaire",
            "carte_nina": "carte_nina",
            "permis_conduire": "permis_conduire",
            "certificat_residence": "certificat_residence",
            "titre_foncier": "titre_foncier",
        }
        demarche_identifiee = mapping.get(intent)
        if demarche_identifiee:
            return [SlotSet("demarche", demarche_identifiee)]
        return []


def _find_info_in_knowledge_store(demarche: Optional[str]) -> Optional[Dict[str, str]]:
    """Recherche dynamique dans le VectorStore pour couvrir les documents hors FAQ standard."""
    if not demarche:
        return None
    try:
        from intelligence.vector_store import get_vector_store
        store = get_vector_store()
        dem_norm = demarche.lower().replace("_", " ")
        for chunk in store.chunks:
            if chunk.topic == demarche or dem_norm == chunk.topic.lower() or dem_norm in chunk.title.lower():
                return {
                    "title_fr": chunk.title,
                    "title_bm": chunk.title,
                    "content": chunk.content,
                }
    except Exception:
        pass
    return None


class ActionRepondreDocuments(Action):
    """Donne la liste des pièces nécessaires selon la démarche en cours et la langue."""

    def name(self) -> Text:
        return "action_repondre_documents"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        lang = tracker.get_slot("langue") or "français"
        demarche = tracker.get_slot("demarche")

        faq = load_faq_database()
        info = None
        for item in faq.get("categories", []):
            if item.get("id") == demarche:
                info = item
                break

        if info:
            if lang == "bambara":
                rep = info.get("pieces_bm") or info.get("answer_bm")
                dispatcher.utter_message(text=f"📋 Sɛbɛn minnu bɛ ɲini ({info.get('title_bm', '')}) :\n{rep}")
            else:
                rep = info.get("pieces_fr") or info.get("answer_fr")
                dispatcher.utter_message(text=f"📋 Documents à fournir pour : {info.get('title_fr', '')} :\n{rep}")
            return []

        # Recherche de repli dans le magasin de connaissances
        v_info = _find_info_in_knowledge_store(demarche)
        if v_info:
            content = v_info["content"]
            doc_lines = [
                l.strip() for l in content.split("\n")
                if any(w in l.lower() for w in ["pièce", "piece", "document", "sɛbɛn", "certificat", "extrait", "témoin", "temoin"])
            ]
            if doc_lines:
                dispatcher.utter_message(text=f"📋 Documents / Pièces pour {v_info['title_fr']} :\n" + "\n".join(doc_lines))
            else:
                dispatcher.utter_message(text=f"📋 Précisions pour {v_info['title_fr']} :\n{content}")
            return []

        if lang == "bambara":
            dispatcher.utter_message(
                text="I bɛ sɛbɛn jumɛn de ɲini ? (CNI, pasipɔri, wolosɛbɛn, furu sɛbɛn, nina...)"
            )
        else:
            dispatcher.utter_message(
                text="De quelle démarche souhaitez-vous connaître les pièces à fournir ? (Carte d'identité, passeport, acte de naissance, etc.)"
            )
        return []


class ActionRepondreCout(Action):
    """Donne le tarif / coût de la démarche en cours."""

    def name(self) -> Text:
        return "action_repondre_cout"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        lang = tracker.get_slot("langue") or "français"
        demarche = tracker.get_slot("demarche")

        faq = load_faq_database()
        info = None
        for item in faq.get("categories", []):
            if item.get("id") == demarche:
                info = item
                break

        if info:
            if lang == "bambara":
                rep = info.get("cout_bm") or info.get("answer_bm")
                dispatcher.utter_message(text=f"💵 Sɔngɔ / Wari ({info.get('title_bm', '')}) :\n{rep}")
            else:
                rep = info.get("cout_fr") or info.get("answer_fr")
                dispatcher.utter_message(text=f"💵 Coût officiel pour : {info.get('title_fr', '')} :\n{rep}")
            return []

        # Recherche de repli dans le magasin de connaissances étendu
        v_info = _find_info_in_knowledge_store(demarche)
        if v_info:
            content = v_info["content"]
            cost_lines = [
                l.strip() for l in content.split("\n")
                if any(w in l.lower() for w in ["fcfa", "wari", "sɔngɔ", "frais", "coût", "cout", "tarif", "gratuit", "timbre"])
            ]
            if cost_lines:
                dispatcher.utter_message(text=f"💵 Frais / Tarif pour {v_info['title_fr']} :\n" + "\n".join(cost_lines))
            else:
                dispatcher.utter_message(text=f"💵 Tarification pour {v_info['title_fr']} :\n{content}")
            return []

        if lang == "bambara":
            dispatcher.utter_message(
                text="I bɛ baara jumɛn sɔngɔ de ɲini ? (CNI, pasan, wolosɛbɛn, nina...)"
            )
        else:
            dispatcher.utter_message(
                text="De quelle démarche voulez-vous connaître le coût ? (Carte d'identité, passeport, acte de naissance, carte NINA...)"
            )
        return []


class ActionRepondreDelai(Action):
    """Donne le délai de délivrance de la démarche en cours."""

    def name(self) -> Text:
        return "action_repondre_delai"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        lang = tracker.get_slot("langue") or "français"
        demarche = tracker.get_slot("demarche")

        faq = load_faq_database()
        info = None
        for item in faq.get("categories", []):
            if item.get("id") == demarche:
                info = item
                break

        if info:
            if lang == "bambara":
                rep = info.get("delai_bm") or info.get("answer_bm")
                dispatcher.utter_message(text=f"⏱️ Tile / Waati joli ({info.get('title_bm', '')}) :\n{rep}")
            else:
                rep = info.get("delai_fr") or info.get("answer_fr")
                dispatcher.utter_message(text=f"⏱️ Délais d'obtention pour : {info.get('title_fr', '')} :\n{rep}")
        else:
            if lang == "bambara":
                dispatcher.utter_message(
                    text="I bɛ baara jumɛn ka waati de ɲini ? (CNI, pasan, wolosɛbɛn...)"
                )
            else:
                dispatcher.utter_message(
                    text="Pour quelle démarche souhaitez-vous connaître le délai ? (Carte d'identité, passeport, acte de naissance...)"
                )
        return []


class ActionDefaultFallback(Action):
    """Gestionnaire de secours quand le modèle est incertain."""

    def name(self) -> Text:
        return "action_default_fallback"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        lang = tracker.get_slot("langue") or "français"
        if lang == "bambara":
            dispatcher.utter_message(
                text="Hakɛto, n ma a faamu kosɛbɛ. I bɛ se ka i ka ñininkali sɛbɛn cogo wɛrɛ la wa ?"
            )
        else:
            dispatcher.utter_message(
                text="Désolé, je n'ai pas bien compris votre demande. Pourriez-vous reformuler ou préciser le document recherché ?"
            )
        return []
