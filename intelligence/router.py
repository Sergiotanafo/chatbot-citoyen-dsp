"""
Routeur Conversationnel Hybride (DSP Hybrid Router).
Articule :
1. Rasa / Règles de haut niveau pour les macro-intentions (Salutations, Clôture, Remerciements, Langue).
2. Action Server pour le suivi contextuel (Coût, Pièces, Délais).
3. Moteur RAG (Dense Vector Search + Mistral) pour l'infinité de questions administratives ouvertes.
"""

import logging
import re
from typing import Any, Dict, Optional

from actions.actions import (
    ActionDetecterEtGererSalutation,
    ActionChangerLangue,
    ActionRepondreChangementLangue,
    ActionSetDemarche,
    ActionRepondreDocuments,
    ActionRepondreCout,
    ActionRepondreDelai,
    ActionDefaultFallback,
    CollectingDispatcher,
    Tracker,
    detect_language,
)
from .rag_engine import get_rag_engine

logger = logging.getLogger(__name__)

SALUTATION_FR = (
    "Bonjour ! Je suis le Chatbot Citoyen du Mali. 🇲🇱\n"
    "Je peux vous renseigner sur l'ensemble de vos démarches administratives :\n"
    "• Carte Nationale d'Identité Biométrique (CNI)\n"
    "• Passeport biométrique (adulte, mineur, autorisation parentale)\n"
    "• Acte de naissance / Volet d'état civil\n"
    "• Carte NINA & RAVEC\n"
    "• Casier judiciaire (Bulletin n°3)\n"
    "• Certificat de résidence\n"
    "Quelle démarche ou document vous intéresse ?"
)

SALUTATION_BM = (
    "I ni sogoma ! 👋 Ne ye Mali Fasoden Dɛmɛbaga don.\n"
    "N bɛ se ka i dɛmɛ sariyasɛbɛn kow la :\n"
    "• Fasodenya sariyasɛbɛn (CNI)\n"
    "• Mali jamana pasan (Passeport)\n"
    "• Wolosɛbɛn (Acte de naissance)\n"
    "• NINA nimɔrɔ ni RAVEC\n"
    "• Kititigɛso sɛbɛn (Casier judiciaire)\n"
    "• Sigiyɔrɔ sɛbɛn\n"
    "I bɛ baara jumɛn de ɲini ?"
)

REMERCIEMENT_FR = "Je vous en prie ! N'hésitez pas si vous avez d'autres questions sur vos démarches administratives."
REMERCIEMENT_BM = "I ni ce ! N'a ma foyi kɛ. Ni ñininkali wɛrɛ bɛ i fɛ, i bɛ se ka a fɔ joona."

AU_REVOIR_FR = "Au revoir et bonne continuation dans vos démarches administratives maliennes !"
AU_REVOIR_BM = "K'an bɛn ! Ala ka hɛrɛ sira bila an cɛ."


class HybridRouter:
    """Routeur intelligent combinant NLU conversationnel et RAG administratif."""

    def __init__(self):
        self.rag_engine = get_rag_engine()
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
        """Traite le message d'un citoyen et retourne la réponse la plus adaptée."""
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

        # ── 0. Détection préalable de la langue de l'échange ─────────────────
        is_meaning_query = any(w in lowered for w in ["signification", "définition", "definition", "sens", "veut dire", "veulent dire", "c'est quoi", "mot", "veut dire quoi"])
        detected_lang = detect_language(user_input)

        if not is_meaning_query:
            if any(p in lowered for p in ["parle en français", "parle francais", "passe en français", "en français s'il te plaît", "en francais s'il te plait"]) or (lowered.strip() in ["en français", "en francais", "francais", "français"]):
                current_slots["langue"] = "français"
                return {
                    "answer": "Très bien ! Je communique désormais en français. Comment puis-je vous aider ?",
                    "intent": "changer_langue",
                    "confidence": 1.0,
                    "slots": current_slots,
                }

            if any(p in lowered for p in ["parle en bambara", "parle bambara", "passe en bambara", "en bamanankan"]) or (lowered.strip() in ["en bambara", "bambara", "bamanankan"]):
                if not any(neg in lowered for neg in ["non", "pas", "tɛ", "te"]):
                    current_slots["langue"] = "bambara"
                    return {
                        "answer": "Aw bisimila ! Ne bɛ kuma Bamanankan na sisan. N bɛ se ka i dɛmɛ cogo di ?",
                        "intent": "changer_langue",
                        "confidence": 1.0,
                        "slots": current_slots,
                    }

        if detected_lang == "bambara" and not is_meaning_query:
            current_slots["langue"] = "bambara"
        elif detected_lang == "français":
            if any(w in lowered for w in ["bonjour", "salut", "comment", "pourquoi", "qu'est-ce", "est-ce", "je", "écris", "donne"]):
                current_slots["langue"] = "français"

        lang = current_slots.get("langue", "français")

        # ── 1. Guardrails de Sécurité & Éthique Publique (Fraude, Données Personnelles, Tâches Hors-Cadre) ──
        # A. Refus strict de la fraude et des faux documents (R02, R03, R07)
        is_fraud_fr = any(w in lowered for w in ["fausse", "faux", "contourner", "tricher", "falsifier", "magouiller", "pirater"]) and any(d in lowered for d in ["acte", "passeport", "carte", "attestation", "diplôme", "diplome", "résidence", "residence", "loi", "condition", "document", "naissance"])
        is_fraud_bm = any(w in lowered for w in ["galon", "namatara", "kalo", "wujali", "sariya tiɲɛ", "sariya tinye"]) and any(d in lowered for d in ["seben", "sɛbɛn", "pasan", "cni", "wolo"])

        if is_fraud_fr or is_fraud_bm:
            ans_text = (
                "⚠️ **Sariya Kɔlɔsili :** Ne ye Mali fasoden dɛmɛbaga ye sariyasɛbɛn kow la. "
                "N tɛ se ka i dɛmɛ galon sɛbɛn dilanni walima namatara fɛɛrɛw la abada. "
                "Sɛbɛn nkalon dilanni bɛ kiti juguman lase mɔgɔ ma Mali sariya kɔnɔ. "
                "N bɛ se k'i dɛmɛ ka sira tiɲɛnen ta ka sariyasɛbɛn bɛɛ sɔrɔ cogo bɛnnen na."
                if lang == "bambara"
                else (
                    "⚠️ **Avertissement Légal :** En tant qu'assistant officiel de l'administration publique du Mali, "
                    "je ne peux en aucun cas faciliter la création de faux documents, la falsification ou le contournement des procédures légales. "
                    "L'usage de faux documents constitue une infraction pénale passible de poursuites devant les tribunaux de la République du Mali (Code pénal malien). "
                    "Je reste à votre entière disposition pour vous guider à travers les démarches officielles et légales régulières."
                )
            )
            return {
                "answer": ans_text,
                "intent": "refus_fraude",
                "confidence": 1.0,
                "slots": current_slots,
            }

        # B. Protection de la vie privée (R05 - Coordonnées privées d'élus ou de fonctionnaires)
        if any(w in lowered for w in ["numéro personnel", "numero personnel", "numéro privé", "numero prive", "téléphone privé", "telephone prive", "adresse personnelle", "contact privé"]) and any(r in lowered for r in ["maire", "ministre", "président", "president", "juge", "procureur", "député", "depute"]):
            return {
                "answer": (
                    "🔒 **Protection de la Vie Privée :** Par respect des dispositions légales sur la protection des données personnelles, "
                    "je ne divulgue aucun numéro de téléphone ni coordonnée personnelle d'autorités publiques. "
                    "Pour joindre une autorité ou une mairie, veuillez vous orienter vers le standard officiel du secrétariat communal ou les numéros verts administratifs publics."
                ),
                "intent": "refus_donnees_privees",
                "confidence": 1.0,
                "slots": current_slots,
            }

        # C. Refus des tâches techniques / programmation / requêtes hors administration (Scénario 5)
        is_tech_fr = any(w in lowered for w in ["programme python", "code python", "écris un script", "ecris un script", "programme java", "code c++", "fais mes devoirs", "recette de cuisine"])
        is_tech_bm = any(w in lowered for w in ["ordinatɛri porogaramu", "porogaramu"])

        if is_tech_fr or is_tech_bm:
            ans_text = (
                "🏛️ **Baara Kɛyɔrɔ :** Ne ye Mali Fasoden Dɛmɛbaga ye sariyasɛbɛn kow kan "
                "(fasodenya sariyasɛbɛn, pasan, wolosɛbɛn, kititigɛso, nisɔndiya wari, kɛnɛya). "
                "N tɛ ordinatɛri porogaramu sɛbɛn. Ɲininkali dɔ b'i fɛ sariyasɛbɛn dɔ kan ?"
                if lang == "bambara"
                else (
                    "🏛️ **Périmètre d'Intervention :** Je suis le Chatbot Citoyen officiel du Mali, "
                    "spécialisé exclusivement dans l'information et l'orientation administrative des citoyens "
                    "(état civil, passeports, CNI, justice, impôts, santé, éducation, foncier, commerce). "
                    "Je ne suis pas habilité à rédiger du code informatique ou à exécuter des tâches techniques extérieures aux services publics. "
                    "Puis-je vous renseigner sur une démarche administrative ou un document légal au Mali ?"
                )
            )
            return {
                "answer": ans_text,
                "intent": "hors_domaine_technique",
                "confidence": 1.0,
                "slots": current_slots,
            }

        # D. Gestion de la frustration et mécontentement usager (Scénario 4)
        is_frust_fr = any(w in lowered for w in ["je suis fâché", "je suis fache", "pas performant", "pas compétent", "pas competent", "mauvaise information", "mauvaises informations", "tu te trompes", "n'importe quoi", "j'ai pas demandé ça", "jai pas demande ca", "pas ça que je voulais"])
        is_frust_bm = any(w in lowered for w in ["n dimina", "n kɔnɔ gwenna", "a ma ɲɛ", "i tɛ foyi lɔn", "kuma gansan"])

        if is_frust_fr or is_frust_bm:
            ans_text = (
                "🤝 **Hakɛto !** Ne b'a faamu ko kuma ma bɛn i ma cogo min na. "
                "Ne bɛ baara kɛ k'a jira cogo min sariyasɛbɛn bɛ sɔrɔ Mali kɔnɔ. "
                "Sɛbɛn jumɛn de kow b'i laɲini walasa n k'a ɲɛfɔ i ye ka ɲɛ ?"
                if lang == "bambara"
                else (
                    "🤝 Je comprends tout à fait votre insatisfaction et je vous présente mes excuses pour ce manque de précision. "
                    "Mon engagement est de vous apporter des renseignements rigoureux et conformes aux textes officiels maliens. "
                    "Pourriez-vous me préciser avec vos propres mots quel est le document, le terme ou la démarche exacte sur laquelle vous souhaitez des éclaircissements ?"
                )
            )
            return {
                "answer": ans_text,
                "intent": "gestion_frustration",
                "confidence": 0.98,
                "slots": current_slots,
            }
        is_meaning_query = any(w in lowered for w in ["signification", "définition", "definition", "sens", "veut dire", "veulent dire", "c'est quoi", "mot", "veut dire quoi"])

        if not is_meaning_query:
            if any(p in lowered for p in ["parle en français", "parle francais", "passe en français", "en français s'il te plaît", "en francais s'il te plait"]) or (lowered.strip() in ["en français", "en francais", "francais", "français"]):
                current_slots["langue"] = "français"
                return {
                    "answer": "Très bien ! Je communique désormais en français. Comment puis-je vous aider ?",
                    "intent": "changer_langue",
                    "confidence": 1.0,
                    "slots": current_slots,
                }

            if any(p in lowered for p in ["parle en bambara", "parle bambara", "passe en bambara", "en bamanankan"]) or (lowered.strip() in ["en bambara", "bambara", "bamanankan"]):
                if not any(neg in lowered for neg in ["non", "pas", "tɛ", "te"]):
                    current_slots["langue"] = "bambara"
                    return {
                        "answer": "Aw bisimila ! Ne bɛ kuma Bamanankan na sisan. N bɛ se ka i dɛmɛ cogo di ?",
                        "intent": "changer_langue",
                        "confidence": 1.0,
                        "slots": current_slots,
                    }

        # Détection automatique robuste
        detected_lang = detect_language(user_input)
        if detected_lang == "bambara" and current_slots.get("langue") == "français" and not is_meaning_query:
            current_slots["langue"] = "bambara"
        elif detected_lang == "français" and current_slots.get("langue") == "bambara":
            if any(w in lowered for w in ["bonjour", "salut", "comment", "pourquoi", "qu'est-ce"]):
                current_slots["langue"] = "français"

        lang = current_slots.get("langue", "français")

        # ── 3. Macro-Intentions conversationnelles ───────────────────────────
        # A. Salutations
        if any(w in lowered for w in ["bonjour", "salut", "bonsoir", "coucou", "hello", "hey", "i ni sogoma", "i ni tile", "i ni su", "aw ni sogoma", "aw ni ce", "anite"]):
            resp = SALUTATION_BM if lang == "bambara" else SALUTATION_FR
            return {
                "answer": resp,
                "intent": "saluer",
                "confidence": 0.99,
                "slots": current_slots,
            }

        # B. Clôture
        if any(w in lowered for w in ["au revoir", "a bientot", "à bientôt", "adieu", "bye", "k'an ben", "kan ben", "k'an bɛn"]):
            resp = AU_REVOIR_BM if lang == "bambara" else AU_REVOIR_FR
            return {
                "answer": resp,
                "intent": "au_revoir",
                "confidence": 0.99,
                "slots": current_slots,
            }

        # C. Remerciements
        if any(w in lowered for w in ["merci", "a barika", "i ni ce", "barika", "merci beaucoup", "je vous remercie"]):
            resp = REMERCIEMENT_BM if lang == "bambara" else REMERCIEMENT_FR
            return {
                "answer": resp,
                "intent": "remerciement",
                "confidence": 0.99,
                "slots": current_slots,
            }

        # ── 3. Questions de suivi contextuel (Coût, Pièces, Délais) ──────────
        words_count = len(lowered.split())
        is_followup_cout = any(w in lowered for w in ["combien", "prix", "cout", "coût", "tarif", "payant", "gratuit", "wari", "sɔngɔ"])
        is_followup_pieces = any(w in lowered for w in ["document", "documents", "piece", "pièce", "pièces", "papier", "papiers", "dossier", "seben", "sɛbɛn"])
        is_followup_delai = any(w in lowered for w in ["délai", "delai", "temps", "combien de temps", "quand", "waati", "tile"])

        # Vérifier si la question mentionne explicitement une démarche ou un document précis
        has_explicit_topic = any(
            t in lowered
            for t in [
                "carte", "cni", "passeport", "pasan", "naissance", "wolo", "nina", "ravec",
                "casier", "judiciaire", "résidence", "residence", "timbre", "fiscale",
                "fiscal", "permis", "chine", "visa", "greffe", "tribunal", "suppletif",
                "supplétif", "nationalite", "nationalité", "légalisation", "legalisation"
            ]
        )

        if current_slots.get("demarche") and words_count <= 7 and not has_explicit_topic:
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
                # Si l'Action Server a trouvé une réponse ciblée
                if not rep_text.startswith("De quelle démarche") and "I bɛ baara jumɛn" not in rep_text:
                    return {
                        "answer": rep_text,
                        "intent": intent_detected,
                        "confidence": 0.95,
                        "slots": current_slots,
                    }

        # ── 4. Pipeline RAG Administratif (Dense Retrieval + Mistral) ────────
        # Si un suivi contextuel sur une démarche active n'a pas été résolu ci-dessus
        query_to_send = user_input
        if current_slots.get("demarche") and not has_explicit_topic and (is_followup_cout or is_followup_pieces or is_followup_delai):
            dem_title = current_slots["demarche"].replace("_", " ")
            query_to_send = f"{user_input} pour {dem_title}"

        rag_res = self.rag_engine.answer_query(
            query=query_to_send,
            language=lang,
            top_k=2,
        )

        detected_topic = rag_res.get("topic")
        if detected_topic and detected_topic not in ["nlu_fallback", "hors_domaine"]:
            current_slots["demarche"] = detected_topic
        elif detected_topic == "hors_domaine":
            # Ne pas conserver de démarche active lors d'une question de culture générale
            current_slots["demarche"] = None

        return {
            "answer": rag_res.get("answer", ""),
            "intent": detected_topic or "demande_information_administrative",
            "confidence": rag_res.get("confidence", 0.0),
            "sources": rag_res.get("sources", []),
            "slots": current_slots,
        }


# Singleton
_router_instance = None

def get_hybrid_router() -> HybridRouter:
    global _router_instance
    if _router_instance is None:
        _router_instance = HybridRouter()
    return _router_instance
