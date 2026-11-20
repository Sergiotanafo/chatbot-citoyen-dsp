"""
Routeur Conversationnel Hybride d'Entreprise (DSP Enterprise Hybrid Router).

Architecture modulaire en pipeline :
1. LanguageEngine : Détection et commutation linguistique (Français / Bambara).
2. GuardrailEngine : Politiques de sécurité, conformité légale, protection de la vie privée,
   gestion de la frustration citoyenne et numéros d'urgence républicains.
3. DialogueEngine : Actes conversationnels (Salutations, Clôture), Machine à états
   (Affirmations, Négations), Négociations de tarifs et Résolution contextuelle d'anaphores.
4. RAGEngine : Recherche vectorielle sémantique et synthèse de réponses administratives.
5. DomainCatalog : Gestionnaire de réponses et templates institutionnels découplés.
"""

import logging
from typing import Any, Dict, Optional

from actions.actions import (
    ActionRepondreCout,
    ActionRepondreDelai,
    ActionRepondreDocuments,
    ActionSetDemarche,
    ActionDefaultFallback,
    CollectingDispatcher,
    Tracker,
)
from .domain_templates import DomainCatalog, get_domain_catalog
from .language_engine import LanguageEngine, get_language_engine
from .guardrails import GuardrailEngine, get_guardrail_engine
from .dialogue_engine import DialogueEngine, get_dialogue_engine
from .rag_engine import get_rag_engine

logger = logging.getLogger(__name__)

# Compatibilité descendante pour les modules qui importeraient les constantes de salutations
_catalog = get_domain_catalog()
SALUTATION_FR = _catalog.get("salutation", lang="fr")
SALUTATION_BM = _catalog.get("salutation", lang="bm")
REMERCIEMENT_FR = _catalog.get("remerciement", lang="fr")
REMERCIEMENT_BM = _catalog.get("remerciement", lang="bm")
AU_REVOIR_FR = _catalog.get("au_revoir", lang="fr")
AU_REVOIR_BM = _catalog.get("au_revoir", lang="bm")


class HybridRouter:
    """Routeur intelligent combinant NLU conversationnel, Guardrails et RAG administratif."""

    def __init__(self):
        self.catalog: DomainCatalog = get_domain_catalog()
        self.lang_engine: LanguageEngine = get_language_engine()
        self.guardrails: GuardrailEngine = get_guardrail_engine()
        self.dialogue_engine: DialogueEngine = get_dialogue_engine()
        self.rag_engine = get_rag_engine()

        # Action Server components
        self.act_cout = ActionRepondreCout()
        self.act_documents = ActionRepondreDocuments()
        self.act_delai = ActionRepondreDelai()
        self.act_set_demarche = ActionSetDemarche()
        self.act_fallback = ActionDefaultFallback()

    def process_message(
        self,
        text: str,
        current_slots: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Traite le message d'un citoyen à travers le pipeline conversationnel DSP.
        Retourne un dictionnaire standardisé : answer, intent, confidence, slots, etc.
        """
        if current_slots is None:
            current_slots = {"langue": "français", "demarche": None}

        user_input = text.strip() if text else ""
        if not user_input:
            return {
                "answer": "",
                "intent": "nlu_fallback",
                "confidence": 0.0,
                "slots": current_slots,
            }

        lowered = user_input.lower()

        # ── 1. Analyse Linguistique & Demandes de Changement de Langue ─────────
        is_meaning_query = any(w in lowered for w in [
            "signification", "définition", "definition", "sens", "veut dire",
            "veulent dire", "c'est quoi", "mot", "veut dire quoi"
        ])

        if not is_meaning_query:
            lang_switch = self.lang_engine.check_language_switch_request(lowered)
            if lang_switch:
                target_lang, switch_key = lang_switch
                current_slots["langue"] = target_lang
                return {
                    "answer": self.catalog.get(switch_key, lang=target_lang),
                    "intent": "changer_langue",
                    "confidence": 1.0,
                    "slots": current_slots,
                }

        detected_lang = self.lang_engine.detect_language(user_input)
        if detected_lang == "bambara" and not is_meaning_query:
            current_slots["langue"] = "bambara"
        elif detected_lang == "français":
            if any(w in lowered for w in ["bonjour", "salut", "comment", "pourquoi", "qu'est-ce", "est-ce", "je", "écris", "donne"]):
                current_slots["langue"] = "français"

        lang = current_slots.get("langue", "français")

        # ── 2. Évaluation des Guardrails Institutionnels & Sécurité ──────────
        guardrail_result = self.guardrails.evaluate(lowered=lowered, lang=lang, current_slots=current_slots)
        if guardrail_result and guardrail_result.matched:
            if guardrail_result.reset_demarche:
                current_slots["demarche"] = None
            return {
                "answer": guardrail_result.answer,
                "intent": guardrail_result.intent,
                "confidence": guardrail_result.confidence,
                "slots": current_slots,
            }

        # ── 3. Macro-Intentions Conversationnelles ───────────────────────────
        macro_result = self.dialogue_engine.handle_macro_intents(lowered=lowered, lang=lang, current_slots=current_slots)
        if macro_result and macro_result.handled:
            return {
                "answer": macro_result.answer,
                "intent": macro_result.intent,
                "confidence": macro_result.confidence,
                "slots": current_slots,
            }

        # ── 4. Machine d'État & Confirmations (Affirmation / Négation) ───────
        affirm_result = self.dialogue_engine.handle_state_machine_confirmation(
            lowered=lowered,
            user_input=user_input,
            lang=lang,
            current_slots=current_slots
        )
        if affirm_result and affirm_result.handled:
            return {
                "answer": affirm_result.answer,
                "intent": affirm_result.intent,
                "confidence": affirm_result.confidence,
                "slots": current_slots,
            }

        # ── 5. Recadrage Négociation Tarifaire Citoyenne ─────────────────────
        negoc_result = self.dialogue_engine.handle_price_negotiation_objection(
            lowered=lowered,
            lang=lang,
            current_slots=current_slots
        )
        if negoc_result and negoc_result.handled:
            return {
                "answer": negoc_result.answer,
                "intent": negoc_result.intent,
                "confidence": negoc_result.confidence,
                "slots": current_slots,
            }

        # ── 6. Résolution Contextuelle d'Anaphores (Coût, Pièces, Délais) ────
        followup_result = self.dialogue_engine.handle_followup_query(
            lowered=lowered,
            user_input=user_input,
            current_slots=current_slots
        )
        if followup_result and followup_result.handled:
            return {
                "answer": followup_result.answer,
                "intent": followup_result.intent,
                "confidence": followup_result.confidence,
                "slots": current_slots,
            }

        # ── 7. Expansion et Réécriture Sémantique de Requête ─────────────────
        query_to_send = user_input
        if any(w in lowered for w in [
            "acte de deces", "acte de décès", "acte de decès", "déclaration de décès",
            "declaration de deces", "déclarer un décès", "declarer un deces",
            "constat de décès", "constat de mort", "la mort"
        ]):
            query_to_send = "acte de deces declaration de deces formalites mairie"

        has_explicit_topic = any(
            t in lowered
            for t in [
                "carte", "cni", "passeport", "pasan", "naissance", "wolo", "nina", "ravec",
                "casier", "judiciaire", "résidence", "residence", "timbre", "fiscale",
                "fiscal", "permis", "chine", "visa", "greffe", "tribunal", "suppletif",
                "supplétif", "nationalite", "nationalité", "légalisation", "legalisation",
                "décès", "deces", "mort", "satun", "mariage", "furu", "divorce"
            ]
        )
        has_contact_keyword = any(k in lowered for k in ["numero", "numéro", "telephone", "téléphone", "contact", "appeler", "joindre"])
        is_followup_cout = any(w in lowered for w in ["combien", "prix", "cout", "coût", "tarif", "payant", "gratuit", "wari", "sɔngɔ"]) and not has_contact_keyword
        is_followup_pieces = any(w in lowered for w in ["document", "documents", "piece", "pièce", "pièces", "papier", "papiers", "dossier", "seben", "sɛbɛn"])
        is_followup_delai = any(w in lowered for w in ["délai", "delai", "temps", "combien de temps", "quand", "waati", "tile"])

        if current_slots.get("demarche") and not has_explicit_topic and (is_followup_cout or is_followup_pieces or is_followup_delai):
            dem_title = current_slots["demarche"].replace("_", " ")
            query_to_send = f"{user_input} pour {dem_title}"

        # ── 8. Exécution RAG Sémantique & Synthèse ───────────────────────────
        rag_res = self.rag_engine.answer_query(
            query=query_to_send,
            language=lang,
            top_k=2,
        )

        detected_topic = rag_res.get("topic")
        rag_confidence = rag_res.get("confidence", 0.0)

        # Enregistrement du slot de démarche active si confiance >= seuil RAG (0.28)
        if detected_topic and detected_topic not in ["nlu_fallback", "hors_domaine"] and rag_confidence >= 0.28:
            current_slots["demarche"] = detected_topic
        elif detected_topic == "hors_domaine":
            current_slots["demarche"] = None
        # En cas de nlu_fallback, le slot démarche est préservé

        return {
            "answer": rag_res.get("answer", ""),
            "intent": detected_topic or "demande_information_administrative",
            "confidence": rag_confidence,
            "sources": rag_res.get("sources", []),
            "slots": current_slots,
        }


# Singleton
_router_instance: Optional[HybridRouter] = None


def get_hybrid_router() -> HybridRouter:
    global _router_instance
    if _router_instance is None:
        _router_instance = HybridRouter()
    return _router_instance
