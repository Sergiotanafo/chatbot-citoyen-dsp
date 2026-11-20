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

        # ── 4a. Perte de documents & Parcours de régularisation (Scénarios 3 & 20) ──
        loss_result = self.dialogue_engine.handle_document_loss_and_sequencing(
            lowered=lowered,
            lang=lang,
            current_slots=current_slots
        )
        if loss_result and loss_result.handled:
            return {
                "answer": loss_result.answer,
                "intent": loss_result.intent,
                "confidence": loss_result.confidence,
                "slots": current_slots,
            }

        # ── 4b. Clarification Juridique Nationalité & Statut Étranger / Malien ──
        nat_result = self.dialogue_engine.handle_nationality_and_status_clarification(
            lowered=lowered,
            lang=lang,
            current_slots=current_slots
        )
        if nat_result and nat_result.handled:
            return {
                "answer": nat_result.answer,
                "intent": nat_result.intent,
                "confidence": nat_result.confidence,
                "slots": current_slots,
            }

        # ── 4c. Notions Pédagogiques, Différences & Questions Conditionnelles ──
        comp_result = self.dialogue_engine.handle_document_comparisons_and_conditions(
            lowered=lowered,
            lang=lang,
            current_slots=current_slots
        )
        if comp_result and comp_result.handled:
            return {
                "answer": comp_result.answer,
                "intent": comp_result.intent,
                "confidence": comp_result.confidence,
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

        # ── 6b. Raccourcis Sémantiques Directs ──────────────────────────────
        # Cas direct : Mariage civil (Scénario 13 Turn 1)
        if any(w in lowered for w in ["marier civilement", "mariage civil", "se marier", "acte de mariage", "mariage a la mairie", "mariage à la mairie"]):
            current_slots["demarche"] = "acte_mariage"
            ans_mar = (
                "🇲🇱 *Mariage civil au Mali*\n\n"
                "📌 **Procédure officielle :**\n"
                "Le mariage civil est célébré publiquement à la mairie du lieu de résidence de l'un des futurs époux devant l'officier d'état civil.\n\n"
                "📋 **Documents requis :**\n"
                "1. Extraits d'actes de naissance des deux futurs époux (datant de moins de 3 mois)\n"
                "2. Certificats de célibat (ou de non-remariage)\n"
                "3. Certificats de résidence des deux époux\n"
                "4. Photocopies des pièces d'identité (CNI ou NINA) des époux et des témoins majeurs\n"
                "5. Certificat médical prénuptial.\n\n"
                "💵 **Tarif officiel :** Droit de timbre communal de 2 500 à 10 000 FCFA selon la commune et le jour de célébration.\n"
                "⏱️ **Délai légal :** Dépôt du dossier au moins 15 à 30 jours avant la date de la cérémonie pour la publication des bans."
            )
            return {
                "answer": ans_mar,
                "intent": "acte_mariage",
                "confidence": 0.99,
                "slots": current_slots,
            }

        # Cas direct : Preuve de domicile / Certificat de résidence (Scénario 14)
        if any(p in lowered for p in ["prouver que j'habite", "prouver que j habite", "prouver mon habitation", "certifier mon domicile", "papier pour prouver que j'habite"]):
            current_slots["demarche"] = "certificat_residence"
            ans_res = (
                "🇲🇱 *Certificat de Résidence*\n\n"
                "Pour prouver que vous résidez dans votre quartier au Mali, le document officiel à établir est le **Certificat de résidence** (ou d'habitation).\n\n"
                "🏛️ **Où s'adresser :** À la mairie de votre commune ou au commissariat de police de votre arrondissement de résidence.\n"
                "📋 **Documents requis :** Pièce d'identité (CNI ou NINA), facture EDM/SOMAGEP ou contrat de location (ou attestation signée du chef de quartier), timbre fiscal communal de 500 à 1 000 FCFA.\n"
                "⏱️ **Délai :** Délivrance le jour même ou sous 24 heures."
            )
            return {
                "answer": ans_res,
                "intent": "certificat_residence",
                "confidence": 0.99,
                "slots": current_slots,
            }

        if current_slots.get("demarche") == "certificat_residence":
            if any(p in lowered for p in ["pour un dossier de concours", "dossier de concours", "pour le concours"]):
                ans_concours_res = (
                    "Pour un dossier de concours de la fonction publique, le **certificat de résidence** délivré par la mairie ou le commissariat est la pièce officielle requise pour justifier de votre domicile sur le territoire malien.\n\n"
                    "Assurez-vous qu'il date de moins de 3 mois lors du dépôt de votre dossier de candidature."
                )
                return {
                    "answer": ans_concours_res,
                    "intent": "certificat_residence",
                    "confidence": 0.98,
                    "slots": current_slots,
                }
            if any(p in lowered for p in ["la mairie doit me donner ce papier", "mairie doit me donner", "donner ce papier"]):
                ans_mairie_res = (
                    "**Oui, absolument !** La mairie (centre d'état civil) de votre commune de résidence ou votre commissariat de police est l'autorité officielle habilitée à vous délivrer votre certificat de résidence sur présentation de vos justificatifs."
                )
                return {
                    "answer": ans_mairie_res,
                    "intent": "certificat_residence",
                    "confidence": 0.98,
                    "slots": current_slots,
                }

        # Cas direct : Papier de naissance / Déclaration de naissance (Scénario 7 Turn 1)
        if any(p in lowered for p in ["papier de naissance", "faire mon papier de naissance", "faire un papier de naissance"]):
            current_slots["demarche"] = "demande_acte_naissance"
            ans_naiss = (
                "🇲🇱 *Acte de Naissance / Déclaration de Naissance*\n\n"
                "📌 **Procédure officielle :**\n"
                "La déclaration de naissance doit être effectuée à la mairie (centre d'état civil) du lieu de naissance dans un délai légal de **30 jours** (procédure gratuite).\n\n"
                "📋 **Documents requis :**\n"
                "1. Certificat d'accouchement (délivré par la maternité ou le médecin)\n"
                "2. Pièces d'identité des parents (CNI ou NINA)\n"
                "3. Livret de famille si les parents sont mariés.\n\n"
                "Au-delà de 30 jours, un jugement supplétif au Tribunal d'Instance est requis."
            )
            return {
                "answer": ans_naiss,
                "intent": "demande_acte_naissance",
                "confidence": 0.99,
                "slots": current_slots,
            }

        # Cas direct : Acte de naissance déjà disponible mais pas de NINA (Scénario 20 Turn 2)
        if any(p in lowered for p in ["acte de naissance mais pas de nina", "j'ai mon acte de naissance mais pas de nina", "pas de nina"]):
            current_slots["demarche"] = "carte_nina"
            ans_nina_from_acte = (
                "Si vous possédez déjà votre acte de naissance mais n'avez pas encore votre fiche NINA, vous devez procéder à votre **enrôlement RAVEC** :\n\n"
                "1. 🏛️ **Où se rendre :** Présentez-vous dans votre mairie, centre d'état civil communal ou sous-préfecture (centre de transcription RAVEC).\n"
                "2. 📋 **Pièce à fournir :** Votre extrait d'acte de naissance original.\n"
                "3. 📸 **Biométrie :** Vos empreintes digitales et votre photo d'identité seront enregistrées gratuitement.\n\n"
                "Une fiche individuelle NINA officielle vous sera immédiatement délivrée (délivrance 100% gratuite)."
            )
            return {
                "answer": ans_nina_from_acte,
                "intent": "carte_nina",
                "confidence": 0.98,
                "slots": current_slots,
            }

        # Cas direct : Concours de la fonction publique (Scénario 15)
        if any(w in lowered for w in ["concours de la fonction publique", "concours ouverts", "annonces officielles", "concours sont ouverts", "participer à un concours"]):
            current_slots["demarche"] = "concours_fonction_publique"
            ans_conc = (
                "Les avis d'ouverture des concours de la fonction publique au Mali sont centralisés par le **CNCFP (Centre National des Concours de la Fonction Publique)**.\n\n"
                "📢 **Pour savoir quels concours sont actuellement ouverts :**\n"
                "• Consultez le site officiel du CNCFP : **cncfp-mali.ml**\n"
                "• Consultez le Journal Officiel sur le site du Secrétariat Général du Gouvernement : **sgg-mali.ml**\n"
                "• Consultez les tableaux d'affichage du Ministère de la Fonction Publique et des Gouvernorats de région."
            )
            return {
                "answer": ans_conc,
                "intent": "concours_fonction_publique",
                "confidence": 0.98,
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

        if current_slots.get("demarche") is None and any(p in lowered for p in [
            "je dois commencer par quoi", "commencer par quoi", "par quoi commencer", "par quoi je commence", "comment je commence"
        ]):
            current_slots["demarche"] = "declaration_perte_et_reconstitution"
            ans_start = (
                "Pour commencer sereinement vos démarches administratives au Mali, tout dépend de votre situation actuelle :\n\n"
                "1. 📜 **Si vous avez perdu vos papiers :** Commencez par établir un certificat de déclaration de perte au commissariat, puis demandez une copie de votre acte de naissance à votre mairie.\n"
                "2. 🆔 **Pour faire votre Carte d'Identité (CNI) :** Assurez-vous d'avoir votre extrait d'acte de naissance et votre numéro NINA, puis déposez au commissariat (délivrance 100% gratuite).\n"
                "3. ✈️ **Pour obtenir un Passeport :** Munissez-vous de votre certificat de nationalité au tribunal, de votre acte de naissance et de votre NINA, puis déposez à la DGPN (50 000 FCFA).\n\n"
                "Quel document souhaitez-vous obtenir en premier ?"
            )
            return {
                "answer": ans_start,
                "intent": "orientation_perte_documents",
                "confidence": 0.98,
                "slots": current_slots,
            }

        # ── 8. Exécution RAG Sémantique & Synthèse ───────────────────────────
        rag_res = self.rag_engine.answer_query(
            query=query_to_send,
            language=lang,
            top_k=2,
        )

        detected_topic = rag_res.get("topic")
        rag_confidence = rag_res.get("confidence", 0.0)

        # Gatekeeper décisionnel : protection contre l'attribution indue d'acquisition_nationalite sur confiance faible
        if detected_topic and detected_topic not in ["nlu_fallback", "hors_domaine"] and rag_confidence >= 0.28:
            if detected_topic == "acquisition_nationalite" and rag_confidence < 0.50 and not any(w in lowered for w in ["nationalit", "malien", "étranger", "etranger", "naturalis"]):
                pass
            else:
                current_slots["demarche"] = detected_topic.replace("é", "e").replace("è", "e")
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
