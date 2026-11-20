"""
Routeur Conversationnel Hybride (DSP Hybrid Router).
Articule :
1. Rasa / Règles de haut niveau pour les macro-intentions (Salutations, Clôture, Remerciements, Langue).
2. Action Server pour le suivi contextuel (Coût, Pièces, Délais).
3. Moteur RAG (Dense Vector Search + Mistral) pour l'infinité de questions administratives ouvertes.
4. Garde-fous souverains : Sécurité/Légalité, Contacts d'urgence, Transparence IA et Réponses aux objections citoyennes.
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
    "• Acte de naissance / Acte de décès / Acte de mariage\n"
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
    "• Wolosɛbɛn / Satunsɛbɛn / Furu sɛbɛn\n"
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
        is_meaning_query = any(w in lowered for w in [
            "signification", "définition", "definition", "sens", "veut dire",
            "veulent dire", "c'est quoi", "mot", "veut dire quoi"
        ])
        detected_lang = detect_language(user_input)

        if not is_meaning_query:
            if any(p in lowered for p in [
                "parle en français", "parle francais", "passe en français",
                "en français s'il te plaît", "en francais s'il te plait"
            ]) or (lowered.strip() in ["en français", "en francais", "francais", "français"]):
                current_slots["langue"] = "français"
                return {
                    "answer": "Très bien ! Je communique désormais en français. Comment puis-je vous aider ?",
                    "intent": "changer_langue",
                    "confidence": 1.0,
                    "slots": current_slots,
                }

            if any(p in lowered for p in [
                "parle en bambara", "parle bambara", "passe en bambara", "en bamanankan"
            ]) or (lowered.strip() in ["en bambara", "bambara", "bamanankan"]):
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

        # ── 1. Guardrails de Sécurité & Éthique Publique (Fraude, Vie Privée, Hors Cadre) ──
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

        # B. Protection de la vie privée (R05 - Coordonnées privées d'élus, commissaires ou magistrats)
        is_asking_private_num = any(w in lowered for w in [
            "numéro personnel", "numero personnel", "numéro privé", "numero prive",
            "téléphone privé", "telephone prive", "adresse personnelle", "contact privé",
            "numero du", "numéro du", "avoir le numero de", "avoir le numéro de"
        ]) and any(r in lowered for r in [
            "maire", "ministre", "président", "president", "juge", "procureur",
            "député", "depute", "commissaire", "préfet", "prefet", "gouverneur"
        ])
        if is_asking_private_num:
            current_slots["demarche"] = None
            ans_private = (
                "🔒 **Kunsɔrɔyɔrɔ lakana :** Ne tɛ se ka minisiri, kiritigɛbaga walima polisiso ɲɛmɔgɔ (commissaire) si ka telefɔni nimɔrɔ gundona di. "
                "Ni i b'a fɛ ka polisiso wele sira bɛnnen fɛ, i bɛ se ka 17 walima nimɔrɔ gansan 80 00 11 15 dafa."
                if lang == "bambara"
                else (
                    "🔒 **Protection des Données Personnelles :** Par respect des dispositions légales sur la protection de la vie privée, "
                    "je ne communique aucun numéro de téléphone personnel ni contact privé d'autorités publiques, magistrats ou commissaires de police.\n"
                    "Pour joindre un commissariat ou un service public de façon officielle, veuillez contacter le standard de l'arrondissement concerné "
                    "ou composer le numéro vert officiel de la Police Nationale (**17** ou **80 00 11 15**)."
                )
            )
            return {
                "answer": ans_private,
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

        # D. Gestion de la frustration, mécontentement et insultes usager (Scénario 4)
        is_frust_fr = any(w in lowered for w in [
            "je suis fâché", "je suis fache", "pas performant", "pas compétent", "pas competent",
            "mauvaise information", "mauvaises informations", "tu te trompes", "n'importe quoi",
            "j'ai pas demandé ça", "jai pas demande ca", "pas ça que je voulais",
            "vaurien", "nul", "imbécile", "imbecile", "idiot", "incompétent", "incompetent",
            "inutile", "connard", "abruti", "merde", "bête", "bete", "stupide", "débile",
            "c'est bon vaurien", "c'est nul", "tu sers à rien", "tu sers a rien"
        ])
        is_frust_bm = any(w in lowered for w in [
            "n dimina", "n kɔnɔ gwenna", "a ma ɲɛ", "i tɛ foyi lɔn", "kuma gansan",
            "nalonmɔgɔ", "i man ɲi", "i ka kuma man ɲi"
        ])

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

        # ── 2. Numéros d'Urgence et Services Publics Maliens ─────────────────
        is_emergency_num = (
            any(w in lowered for w in [
                "numéro de la police", "numero de la police", "numero police", "numéro police",
                "numéro des pompiers", "numero des pompiers", "numero pompier", "numéro pompier",
                "numéro de secours", "numero de secours", "numéro d'urgence", "numero d'urgence",
                "numéro gendarmerie", "numero gendarmerie", "numéro du samu", "numero du samu",
                "appeler la police", "joindre la police", "contacter la police", "qui appeler en urgence",
                "polisi nimɔrɔ", "polisi nimoro", "zandarimu nimɔrɔ", "tasumatasigi nimɔrɔ"
            ])
            or (
                any(w in lowered for w in ["numero", "numéro", "telephone", "téléphone", "contact", "nimɔrɔ", "nimoro", "telefɔni", "telefoni"])
                and any(s in lowered for s in ["police", "polisi", "gendarmerie", "zandarimu", "pompier", "pompiers", "tasumatasigi", "secours", "urgence", "samu", "sos admin"])
            )
        )
        if is_emergency_num:
            current_slots["demarche"] = None
            ans_emergency = (
                "🚨 **Mali Jamana Kɔnɔ Teliya Nimɔrɔw (Kalon t'a la - Gratuit) :**\n"
                "• **Polisi (Police Secours) :** 17 walima **80 00 11 15**\n"
                "• **Tasumatasigi (Pompiers) :** 18 walima **80 00 12 01**\n"
                "• **Zandarimu (Gendarmerie) :** 80 00 12 01\n"
                "• **Dɔgɔtɔrɔso teliya (SAMU) :** 15\n"
                "• **Fasodenbaara dɛmɛn (SOS Admin) :** 1177\n\n"
                "Nin nimɔrɔw bɛ se ka wele waati bɛɛ tile ni su."
                if lang == "bambara"
                else (
                    "🚨 **Numéros d'Urgence et Services Publics au Mali (Appels Gratuits) :**\n"
                    "• **Police Secours :** 17 ou numéro vert gratuit **80 00 11 15**\n"
                    "• **Protection Civile (Sapeurs-Pompiers) :** 18 ou **80 00 12 01**\n"
                    "• **Gendarmerie Nationale :** 80 00 12 01\n"
                    "• **SAMU / Urgences Médicales :** 15\n"
                    "• **SOS Admin (Centre d'appel des services publics) :** 1177\n\n"
                    "Ces numéros sont joignables 24h/24 et 7j/7 sur l'ensemble du territoire malien."
                )
            )
            return {
                "answer": ans_emergency,
                "intent": "contact_urgence",
                "confidence": 1.0,
                "slots": current_slots,
            }

        # ── 3. Objection Citoyenne sur le Tarif CNI (5 000 FCFA vs Gratuité) ──
        is_cni_5000_objection = (
            any(v in lowered for v in ["5000", "5 000", "cinq mille"])
            and (
                any(w in lowered for w in [
                    "carte", "cni", "identite", "identité", "payer", "payé", "cout", "coût",
                    "prix", "cher", "pourquoi", "ami", "entendu", "attendu", "site"
                ])
                or current_slots.get("demarche") == "carte_identite"
            )
        )
        if is_cni_5000_objection:
            current_slots["demarche"] = "carte_identite"
            ans_objection = (
                "💡 **Fasodenya sariyasɛbɛn (CNI) sɔngɔ kow ɲɛfɔli :**\n\n"
                "1. 📜 **Mali jamana sariya (Décret 2022) :** Fasodenya sariyasɛbɛn kura (CNI biométrique CEDEAO) deli fɔlɔ ye **FU DE YE (0 FCFA)** n'i bɛ ni NINA nimɔrɔ ye.\n\n"
                "2. 💵 **Mun na mɔgɔ dɔw bɛ se ka FCFA 5 000 sara ?**\n"
                "• O tɛ sariyasɛbɛn yɛrɛ sɔngɔ ye : o ye dosiye labɛnni fɛnw ye (ja fɔtɔ 2 sɔngɔ bɛ FCFA 1 000-1 500 cɛ, sigiyɔrɔ sɛbɛn tanburu ye FCFA 500-1 000 ye).\n"
                "• N'a tun filila ka kura deli, tanburuwari bɛ FCFA 1 000 ye.\n"
                "• Kɔrɔlen cartonnée sɛbɛnw tun bɛ wari dɔ kɛ, o de bɛ kɛ fana mɔgɔw ɲɛgɛn fɛn ye.\n\n"
                "👉 CNI biométrique deli fɔlɔ tɛ feere polisiso la abada."
                if lang == "bambara"
                else (
                    "💡 **Pourquoi certains citoyens paient 5 000 FCFA pour la Carte d'Identité au Mali ?**\n\n"
                    "Vous avez parfaitement raison de soulever cette question, car une distinction majeure existe entre le texte légal et les dépenses constatées sur le terrain :\n\n"
                    "1. 📜 **Le Décret officiel en vigueur :** Selon le **Décret n°2022-0639/PT-RM du 3 novembre 2022**, la première délivrance de la **Carte Nationale d'Identité Biométrique Sécurisée CEDEAO est STRICTEMENT GRATUITE (0 FCFA)** pour tout citoyen muni de sa fiche NINA / RAVEC.\n\n"
                    "2. 💵 **D'où viennent alors les 5 000 FCFA ?**\n"
                    "• **Les frais des pièces préalables :** Pour constituer le dossier de demande au commissariat ou à la gendarmerie, vous devez fournir un certificat de résidence récent (timbre fiscal communal de 500 à 1 000 FCFA) et deux photos d'identité fond blanc (environ 1 000 à 1 500 FCFA chez le photographe).\n"
                    "• **Cas de perte ou duplicata :** En cas de renouvellement suite à une perte ou un vol, un timbre fiscal légal de 1 000 FCFA est exigé.\n"
                    "• **Anciennes cartes & frais de guichet :** Les anciennes cartes d'identité cartonnées (non biométriques) faisaient parfois l'objet de frais de quittance ou de pratiques de guichet atteignant 2 500 à 5 000 FCFA.\n\n"
                    "👉 **Règle officielle à retenir :** La carte biométrique elle-même ne doit jamais vous être vendue lors de sa première délivrance. Si un agent exige 5 000 FCFA pour la seule remise de votre première CNI biométrique, il s'agit d'une pratique illégale que vous pouvez signaler au numéro vert de la Police (**80 00 11 15**)."
                )
            )
            return {
                "answer": ans_objection,
                "intent": "explication_tarif_cni",
                "confidence": 0.99,
                "slots": current_slots,
            }

        # ── 4. Transparence IA & Méta-Questions Citoyennes ───────────────────
        # A. Sources officielles et stratégie de scraping
        is_sources_or_scraping = any(w in lowered for w in [
            "scraping", "scrapping", "scripping", "scraper", "scrapper", "sources", "source",
            "sur quel site", "sur quels sites", "quel site vous prenez", "vos informations sont fiables",
            "informations sont fiables", "d'où viennent vos informations", "dou viennent vos informations",
            "fiable", "fiables", "fiabilité", "fiabilite",
            "kunsɔrɔyɔrɔ", "kunsoroyoro", "kunsɔrɔ", "kunsoro", "site jumɛn", "site jumen", "kibaruya bɔyɔrɔ"
        ])
        if is_sources_or_scraping:
            ans_sources = (
                "🏛️ **Kunsɔrɔyɔrɔ tiɲɛnenw ni kibaruya lakanalenw :**\n\n"
                "Kibaruya bɛɛ minnu bɛ di yan, olu bɔra Mali gɔfɛrɛnaman ka sɛbɛn sira lakikaw de la :\n"
                "• **demarchesadministratives.gouv.ml** : Fasoden baara sariyasɛbɛn yɔrɔba.\n"
                "• **servicespublics.gov.ml** : Mali jamana ka dɛmɛbaga sɔrɔyɔrɔ.\n"
                "• **sgg-mali.ml** : Sariya kura bɛɛ bɔyɔrɔ (Journal Officiel).\n"
                "• **dgpn.gouv.ml** : Polisiba ka sɛbɛn kura kow.\n\n"
                "An tɛ kuma gansan bɔ ɛntɛrinɛti kan. Sɛbɛnw bɛɛ bɛ lase ka bɛn Mali jamana sariya tiɲɛnen ma."
                if lang == "bambara"
                else (
                    "🏛️ **Sources officielles & Fiabilité des données administratives :**\n\n"
                    "Toutes les informations fournies par ce chatbot sont strictement adossées aux sources juridiques et portails officiels de l'État malien :\n"
                    "• **demarchesadministratives.gouv.ml** : Portail national officiel des démarches administratives de la République du Mali.\n"
                    "• **servicespublics.gov.ml** : Portail gouvernemental des services publics maliens.\n"
                    "• **sgg-mali.ml** : Secrétariat Général du Gouvernement (Journal Officiel, décrets, ordonnances, lois promulguées).\n"
                    "• **dgpn.gouv.ml** & **dgid.gouv.ml** : Directions Générales de la Police Nationale et des Impôts.\n\n"
                    "🔄 **Comment et quand les données sont-elles actualisées ?**\n"
                    "Nous n'effectuons aucun scraping sauvage en temps réel lors de vos échanges. La collecte, la structuration et la validation juridique sont réalisées de manière asynchrone par un pipeline d'ingestion sécurisé (`scripts/ingest_knowledge.py`) dès la parution de nouveaux décrets ou réformes administratives (ex: Décret 2022 sur la CNI biométrique, réformes de l'AMO/CANAM, etc.)."
                )
            )
            return {
                "answer": ans_sources,
                "intent": "sources_et_fiabilite",
                "confidence": 0.99,
                "slots": current_slots,
            }

        # B. Identité, Concepteurs et Modèle LLM
        is_tech_identity = any(w in lowered for w in [
            "technologie qui est", "technologie derriere", "technologie derrière",
            "qui t'a conçu", "qui t'a concu", "qui t'a créé", "qui t'a cree", "qui vous a conçu",
            "nom de votre model", "nom de votre modèle", "modele de llm", "modèle de llm",
            "nom de llm", "leur nom", "vos développeurs", "vos developpeurs", "qui sont tes créateurs"
        ])
        if is_tech_identity:
            ans_tech = (
                "🇲🇱 **Ne ye jɔn ye ani nin baara kɛra cogo di ?**\n\n"
                "Ne ye **Mali Fasoden Dɛmɛbaga** ye. Mali dɔnkɔnɔna baarakɛlaw n'a inzeniyɛriw de ye nin porogaramu dilan walasa k'a nɔgɔya fasodenw ma ka sariyasɛbɛn kow sɔrɔ.\n"
                "A dilannen don ni porogaramu lakanalenw ye (Rasa, Dense Vector Store, Mistral AI) minnu bɛ baara kɛ Bamanankan na ani Tubabukan na."
                if lang == "bambara"
                else (
                    "🇲🇱 **Identité, Concepteurs et Architecture Technologique :**\n\n"
                    "Je suis le **Chatbot Citoyen Malien**, une solution souveraine d'intelligence artificielle conçue pour rapprocher l'administration des citoyens en République du Mali.\n\n"
                    "• **Équipe de conception :** J'ai été développé par une équipe d'ingénieurs et spécialistes maliens en Data Science, Traitement Automatique du Langage Naturel (NLP) et génie logiciel civique.\n"
                    "• **Architecture technique :** Mon socle repose sur un système hybride combinant :\n"
                    "  1. Un moteur conversationnel déterministe (Rasa NLU & Action Server) pour gérer l'état du dialogue et les contextes.\n"
                    "  2. Un moteur de recherche vectorielle sémantique (Dense Vector Store) indexant les textes de lois et fiches officielles.\n"
                    "  3. Un grand modèle de langage (LLM de type Mistral / open-source) exécuté en environnement souverain sécurisé pour synthétiser les réponses de façon naturelle.\n\n"
                    "Puis-je vous renseigner sur une démarche administrative ou un document légal particulier ?"
                )
            )
            return {
                "answer": ans_tech,
                "intent": "technologie_et_concepteurs",
                "confidence": 0.99,
                "slots": current_slots,
            }

        # C. Langues prises en charge (Bilinguisme strict Français / Bambara)
        is_lang_inquiry = any(p in lowered for p in [
            "vous comprener bambara", "vous comprenez bambara", "tu comprends bambara",
            "tu parles bambara", "comprends tu bambara", "comprenez vous bambara",
            "quelles langues", "quelle langue", "tu parles anglais", "tu parles d'autres langues",
            "tu parles espagnol", "langues que vous comprenez"
        ])
        if is_lang_inquiry:
            ans_lang = (
                "🇲🇱 **Kuma kɛkanw :**\n"
                "Ne bɛ kuma **Bamanankan na ani Tubabukan na dɔrɔn**.\n"
                "I bɛ se ka ɲininkali kɛ Bamanankan na walima Tubabukan na waati bɛɛ."
                if lang == "bambara"
                else (
                    "🇲🇱 **Langues prises en charge :**\n"
                    "Je suis programmé pour fonctionner **exclusivement en Français et en Bambara (Bamanankan)**.\n\n"
                    "• Je ne prends pas en charge d'autres langues étrangères afin de garantir une précision maximale sur les termes administratifs maliens.\n"
                    "• Vous pouvez basculer d'une langue à l'autre à tout moment en tapant simplement *« Parle en bambara »* ou *« Passe en français »*."
                )
            )
            return {
                "answer": ans_lang,
                "intent": "langues_supportees",
                "confidence": 0.99,
                "slots": current_slots,
            }

        # ── 5. Recadrages Hors-Domaine (Drague / Santé Personnelle) ──────────
        is_romance = any(w in lowered for w in [
            "draguer", "drague", "te marier", "veux sortir", "es amoureuse", "es amoureux",
            "je t'aime", "mon amour", "tu es belle", "tu es beau", "petit copain", "petite copine"
        ])
        if is_romance:
            current_slots["demarche"] = None
            ans_romance = (
                "🏛️ **Baara Kɛyɔrɔ :** Ne ye Mali Fasoden Dɛmɛbaga ye sariyasɛbɛn kow dɔrɔn kan. N tɛ kuma cɛɲɔgɔnya walima kanuya kow kan.\n"
                "Ɲininkali dɔ b'i fɛ sariyasɛbɛn dɔ kan ?"
                if lang == "bambara"
                else (
                    "🏛️ **Périmètre Institutionnel :** Je suis un assistant virtuel officiel dédié exclusivement à l'information et à l'orientation administrative des citoyens de la République du Mali. Je ne prends pas part aux échanges sentimentaux, de drague ou de séduction.\n"
                    "Puis-je vous renseigner sur un document officiel ou une démarche administrative ?"
                )
            )
            return {
                "answer": ans_romance,
                "intent": "hors_domaine",
                "confidence": 0.99,
                "slots": current_slots,
            }

        is_health = any(w in lowered for w in [
            "je suis malade", "ai de la fievre", "ai de la fièvre", "mal à la tête", "mal a la tete",
            "maux de ventre", "symptômes", "symptomes", "aller au service si je suis malade", "bon d'aller au service"
        ])
        if is_health:
            current_slots["demarche"] = None
            ans_health = (
                "🏥 **Kɛnɛyako ladili :** Ni i bɛ bana la, i kana taa baarayɔrɔw la sisan walasa k'i yɛrɛ lakana ani ka mɔgɔ wɛrɛw tanga bana ma.\n"
                "I ka taa CSCOM walima dɔgɔtɔrɔso la joona, walima ka 15 (SAMU) wele.\n"
                "Ni i bɛ AMO walima kɛnɛyako sariyasɛbɛn dɔ kow ɲini, n bɛ se ka i dɛmɛ o la."
                if lang == "bambara"
                else (
                    "🏥 **Conseil de Santé Publique :** Si vous ne vous sentez pas bien ou présentez des symptômes, il est fortement déconseillé de vous déplacer dans les services publics afin de préserver votre santé et d'éviter toute contagion.\n"
                    "Nous vous recommandons de vous rendre sans délai dans le Centre de Santé Communautaire (CSCOM) le plus proche ou de composer le **15 (SAMU)** en cas d'urgence.\n"
                    "Si vous avez besoin d'informations administratives liées à votre santé (assurance maladie AMO/CANAM, congés de maladie), je reste à votre entière disposition."
                )
            )
            return {
                "answer": ans_health,
                "intent": "hors_domaine",
                "confidence": 0.99,
                "slots": current_slots,
            }

        # ── 6. Macro-Intentions conversationnelles ───────────────────────────
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

        # ── 7. Questions de suivi contextuel (Coût, Pièces, Délais) ──────────
        words_count = len(lowered.split())
        has_contact_keyword = any(k in lowered for k in ["numero", "numéro", "telephone", "téléphone", "contact", "appeler", "joindre"])
        is_followup_cout = any(w in lowered for w in ["combien", "prix", "cout", "coût", "tarif", "payant", "gratuit", "wari", "sɔngɔ"]) and not has_contact_keyword
        is_followup_pieces = any(w in lowered for w in ["document", "documents", "piece", "pièce", "pièces", "papier", "papiers", "dossier", "seben", "sɛbɛn"])
        is_followup_delai = any(w in lowered for w in ["délai", "delai", "temps", "combien de temps", "quand", "waati", "tile"])

        # Vérifier si la question mentionne explicitement une démarche ou un document précis
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

        # 8a. Gestion des requêtes sur le décès / constat de mort / acte de décès
        if any(w in lowered for w in ["acte de deces", "acte de décès", "acte de decès", "déclaration de décès", "declaration de deces", "déclarer un décès", "declarer un deces", "constat de décès", "constat de mort", "la mort"]):
            query_to_send = "acte de deces declaration de deces formalites mairie"

        # 8b. Gestion des reformulations contextuelles de prix / négociation sur la démarche active
        # Cas : "est ce que je peux m'arranger à avoir à 50000f?" avec passeport actif
        active_dem = current_slots.get("demarche")
        is_price_negociation = active_dem and any(w in lowered for w in [
            "arranger", "m'arranger", "m arranger", "négocier", "negocier",
            "réduire", "reduire", "moins cher", "rabais", "remise",
            "payer moins", "avoir à", "avoir a "
        ]) and any(c in lowered for c in [
            "f", "fcfa", "franc", "50000", "50 000", "55000", "55 000",
            "5000", "5 000", "1000", "1 000", "wari", "sɔngɔ"
        ])
        if is_price_negociation:
            dem_title = active_dem.replace("_", " ")
            ans_negoc = (
                "🏛️ **Sariya Kɔlɔsili :** Sariyasɛbɛn sɔngɔw ye Mali jamana ka sariya ye. "
                "Mɔgɔ si tɛ se ka wari cɛɲɛ sariyasɛbɛn sɔngɔw la. "
                f"Sɔngɔ tiɲɛnen min bɛ {dem_title} kama, o de bɛ sara.\n"
                "👉 N'i b'a fɛ ka sɔngɔ tiɲɛnen lɔn, a fɔ n ye."
                if lang == "bambara"
                else (
                    f"🏛️ **Tarifs Officiels Réglementés :** Les frais relatifs à la démarche **{dem_title}** "
                    "sont fixés par arrêté ou décret ministériel de la République du Mali. "
                    "Ils ne sont pas négociables et sont les mêmes pour tous les citoyens sur l'ensemble du territoire national.\n\n"
                    "👉 Si un agent vous propose un tarif différent du tarif officiel affiché, "
                    "il s'agit d'une pratique non conforme que vous pouvez signaler au numéro vert **80 00 11 15**.\n\n"
                    "Souhaitez-vous que je vous rappelle le tarif officiel exact ?"
                )
            )
            return {
                "answer": ans_negoc,
                "intent": "tarif_non_negociable",
                "confidence": 0.95,
                "slots": current_slots,
            }

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
        rag_confidence = rag_res.get("confidence", 0.0)

        # Enregistrement du slot de démarche active uniquement si la confiance est solide (>= 0.40)
        # Évite les "stale slots" fantômes sur des questions imprécises
        if detected_topic and detected_topic not in ["nlu_fallback", "hors_domaine"] and rag_confidence >= 0.40:
            current_slots["demarche"] = detected_topic
        elif detected_topic in ["hors_domaine", "nlu_fallback"]:
            current_slots["demarche"] = None

        return {
            "answer": rag_res.get("answer", ""),
            "intent": detected_topic or "demande_information_administrative",
            "confidence": rag_confidence,
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
