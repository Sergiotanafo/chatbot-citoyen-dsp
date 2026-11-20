"""
Moteur de Dialogue Contextuel et Machine à États (Dialogue Engine).
Gère :
1. Les actes de dialogue conversationnels (Salutations, Remerciements, Au revoir).
2. La machine à états de confirmation/négation (affirmation, refus, reprise de démarche).
3. La régulation des négociations tarifaires citoyennes (intransgressibilité légale).
4. La résolution d'anaphores et questions de suivi (coût, pièces requises, délais).
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from actions.actions import (
    ActionRepondreCout,
    ActionRepondreDelai,
    ActionRepondreDocuments,
    CollectingDispatcher,
    Tracker,
)
from .domain_templates import DomainCatalog, get_domain_catalog

logger = logging.getLogger(__name__)


@dataclass
class DialogueResult:
    handled: bool
    intent: Optional[str] = None
    confidence: float = 0.0
    answer: str = ""
    slots: Optional[Dict[str, Any]] = None


class DialogueEngine:
    """Gestionnaire des états conversationnels et de la continuité du dialogue."""

    def __init__(self, catalog: Optional[DomainCatalog] = None):
        self.catalog = catalog or get_domain_catalog()
        self.act_cout = ActionRepondreCout()
        self.act_documents = ActionRepondreDocuments()
        self.act_delai = ActionRepondreDelai()

    def handle_macro_intents(self, lowered: str, lang: str, current_slots: Dict[str, Any]) -> Optional[DialogueResult]:
        """Gère les salutations, remerciements et fins de conversation."""
        # Salutations
        if any(w in lowered for w in ["bonjour", "salut", "bonsoir", "coucou", "hello", "hey", "i ni sogoma", "i ni tile", "i ni su", "aw ni sogoma", "aw ni ce", "anite"]):
            return DialogueResult(
                handled=True,
                intent="saluer",
                confidence=0.99,
                answer=self.catalog.get("salutation", lang=lang),
                slots=current_slots,
            )

        # Clôture / Au revoir
        if any(w in lowered for w in ["au revoir", "a bientot", "à bientôt", "adieu", "bye", "k'an ben", "kan ben", "k'an bɛn"]):
            return DialogueResult(
                handled=True,
                intent="au_revoir",
                confidence=0.99,
                answer=self.catalog.get("au_revoir", lang=lang),
                slots=current_slots,
            )

        # Remerciements
        if any(w in lowered for w in ["merci", "a barika", "i ni ce", "barika", "merci beaucoup", "je vous remercie"]):
            return DialogueResult(
                handled=True,
                intent="remerciement",
                confidence=0.99,
                answer=self.catalog.get("remerciement", lang=lang),
                slots=current_slots,
            )

        return None

    def handle_state_machine_confirmation(
        self,
        lowered: str,
        user_input: str,
        lang: str,
        current_slots: Dict[str, Any]
    ) -> Optional[DialogueResult]:
        """
        Traite les confirmations (Oui / D'accord) et négations (Non / Laisse)
        sur une proposition ou démarche en suspens.
        """
        is_affirm = (
            lowered.strip() in [
                "oui", "ouais", "d'accord", "d accord", "ok", "bien sûr", "bien sur",
                "yes", "absolument", "exactement", "je veux bien", "vas-y", "vas y",
                "c'est ça", "tout à fait", "tout a fait", "awɔ", "awo", "n b'a fɛ"
            ]
            or any(p in lowered for p in [
                "rappelle-moi", "rappelle moi", "rappeler les prix", "rappeler des prix",
                "rappelle les prix", "rappelle le prix", "donne le prix", "donne les prix",
                "rappeler le tarif", "rappelle le tarif", "je te demande de me rappeler"
            ])
        )

        is_deny = lowered.strip() in [
            "non", "nan", "non merci", "pas la peine", "c'est pas la peine",
            "laisse", "non c'est bon", "ayi", "n t'a fɛ", "n tɛ o fɛ"
        ]

        if is_affirm and current_slots.get("demarche"):
            pending = current_slots.get("pending_action")
            current_slots["pending_action"] = None
            disp = CollectingDispatcher()
            tracker = Tracker(slots=current_slots, latest_message={"text": user_input})
            if pending == "rappeler_documents":
                self.act_documents.run(disp, tracker, {})
                intent_detected = "demander_documents"
            else:
                self.act_cout.run(disp, tracker, {})
                intent_detected = "demander_cout"

            if disp.messages:
                return DialogueResult(
                    handled=True,
                    intent=intent_detected,
                    confidence=0.99,
                    answer=disp.messages[0]["text"],
                    slots=current_slots,
                )

        if is_deny and current_slots.get("demarche"):
            current_slots["pending_action"] = None
            return DialogueResult(
                handled=True,
                intent="refus_proposition",
                confidence=0.99,
                answer=self.catalog.get("refus_proposition", lang=lang),
                slots=current_slots,
            )

        return None

    def handle_price_negotiation_objection(
        self,
        lowered: str,
        lang: str,
        current_slots: Dict[str, Any]
    ) -> Optional[DialogueResult]:
        """
        Intercepte les tentatives de marchandage ou négociation de tarif
        sur la démarche administrative en cours.
        """
        active_dem = current_slots.get("demarche")
        if not active_dem:
            return None

        is_price_negoc = any(w in lowered for w in [
            "arranger", "m'arranger", "m arranger", "négocier", "negocier",
            "réduire", "reduire", "moins cher", "rabais", "remise",
            "payer moins", "avoir à", "avoir a "
        ]) and any(c in lowered for c in [
            "f", "fcfa", "franc", "50000", "50 000", "55000", "55 000",
            "5000", "5 000", "1000", "1 000", "wari", "sɔngɔ"
        ])

        if not is_price_negoc:
            return None

        dem_title = active_dem.replace("_", " ")
        ans_text = self.catalog.get("tarif_non_negociable", lang=lang, demarche_title=dem_title)
        current_slots["pending_action"] = "rappeler_tarif"

        return DialogueResult(
            handled=True,
            intent="tarif_non_negociable",
            confidence=0.95,
            answer=ans_text,
            slots=current_slots,
        )

    def handle_followup_query(
        self,
        lowered: str,
        user_input: str,
        current_slots: Dict[str, Any]
    ) -> Optional[DialogueResult]:
        """
        Résout les anaphores contextuelles (prix, pièces, délais) quand une démarche
        est déjà active et qu'aucun nouveau sujet explicite n'est introduit.
        """
        if not current_slots.get("demarche"):
            return None

        words_count = len(lowered.split())
        has_contact_keyword = any(k in lowered for k in ["numero", "numéro", "telephone", "téléphone", "contact", "appeler", "joindre"])
        is_followup_cout = any(w in lowered for w in ["combien", "prix", "cout", "coût", "tarif", "payant", "gratuit", "wari", "sɔngɔ"]) and not has_contact_keyword
        is_followup_pieces = any(w in lowered for w in ["document", "documents", "piece", "pièce", "pièces", "papier", "papiers", "dossier", "seben", "sɛbɛn"])
        is_followup_delai = any(w in lowered for w in ["délai", "delai", "temps", "combien de temps", "quand", "waati", "tile"])

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

        if words_count <= 14 and not has_explicit_topic:
            disp = CollectingDispatcher()
            tracker = Tracker(slots=current_slots, latest_message={"text": user_input})
            intent_detected = None

            if is_followup_cout:
                intent_detected = "demander_cout"
                self.act_cout.run(disp, tracker, {})
            elif is_followup_pieces:
                intent_detected = "demander_documents"
                self.act_documents.run(disp, tracker, {})
            elif is_followup_delai:
                intent_detected = "demander_delai"
                self.act_delai.run(disp, tracker, {})

            if disp.messages:
                rep_text = disp.messages[0]["text"]
                if not rep_text.startswith("De quelle démarche") and "I bɛ baara jumɛn" not in rep_text:
                    return DialogueResult(
                        handled=True,
                        intent=intent_detected,
                        confidence=0.95,
                        answer=rep_text,
                        slots=current_slots,
                    )

        return None


# Singleton
_dialogue_engine_instance: Optional[DialogueEngine] = None


def get_dialogue_engine() -> DialogueEngine:
    global _dialogue_engine_instance
    if _dialogue_engine_instance is None:
        _dialogue_engine_instance = DialogueEngine()
    return _dialogue_engine_instance
