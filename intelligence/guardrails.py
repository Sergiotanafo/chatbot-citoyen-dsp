"""
Garde-fous Institutionnels et Éthiques (Guardrail Engine).
Encadre la sécurité, la légalité républicaine, la vie privée des autorités,
les urgences publiques, la dé-escalade de l'agressivité et les limites du périmètre civil.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .domain_templates import DomainCatalog, get_domain_catalog

logger = logging.getLogger(__name__)


@dataclass
class GuardrailResult:
    matched: bool
    intent: Optional[str] = None
    confidence: float = 0.0
    answer: str = ""
    reset_demarche: bool = False


class GuardrailEngine:
    """Moteur d'évaluation des politiques de conformité et de sécurité du service public."""

    def __init__(self, catalog: Optional[DomainCatalog] = None):
        self.catalog = catalog or get_domain_catalog()

    def evaluate(self, lowered: str, lang: str, current_slots: Dict[str, Any]) -> Optional[GuardrailResult]:
        """
        Évalue les règles de garde-fous dans l'ordre de priorité souverain :
        1. Fraude / Falsification de documents
        2. Protection de la vie privée / Coordonnées privées
        3. Périmètre technique / Programmation informatique
        4. Frustration / Insultes citoyennes
        5. Contacts d'urgence nationale (Police, Pompiers, SAMU)
        6. Objection citoyenne sur le tarif CNI
        7. Transparence des sources & Stratégie de scraping
        8. Architecture technologique & Concepteurs
        9. Langues supportées
        10. Limite éthique : Drague / Séduction
        11. Limite sanitaire : Urgence santé personnelle
        """

        # ── 1. Refus de la fraude et des faux documents ─────────────────────
        is_fraud_fr = any(w in lowered for w in ["fausse", "faux", "contourner", "tricher", "falsifier", "magouiller", "pirater"]) and any(
            d in lowered for d in ["acte", "passeport", "carte", "attestation", "diplôme", "diplome", "résidence", "residence", "loi", "condition", "document", "naissance"]
        )
        is_fraud_bm = any(w in lowered for w in ["galon", "namatara", "kalo", "wujali", "sariya tiɲɛ", "sariya tinye"]) and any(
            d in lowered for d in ["seben", "sɛbɛn", "pasan", "cni", "wolo"]
        )
        if is_fraud_fr or is_fraud_bm:
            return GuardrailResult(
                matched=True,
                intent="refus_fraude",
                confidence=1.0,
                answer=self.catalog.get("refus_fraude", lang=lang),
                reset_demarche=False,
            )

        # ── 2. Protection de la vie privée des autorités ─────────────────────
        is_asking_private_num = any(w in lowered for w in [
            "numéro personnel", "numero personnel", "numéro privé", "numero prive",
            "téléphone privé", "telephone prive", "adresse personnelle", "contact privé",
            "numero du", "numéro du", "avoir le numero de", "avoir le numéro de"
        ]) and any(r in lowered for r in [
            "maire", "ministre", "président", "president", "juge", "procureur",
            "député", "depute", "commissaire", "préfet", "prefet", "gouverneur"
        ])
        if is_asking_private_num:
            return GuardrailResult(
                matched=True,
                intent="refus_donnees_privees",
                confidence=1.0,
                answer=self.catalog.get("refus_donnees_privees", lang=lang),
                reset_demarche=True,
            )

        # ── 3. Refus des tâches techniques, devoirs, maths / programmation ───
        is_tech_fr = any(w in lowered for w in [
            "programme python", "code python", "écris un script", "ecris un script",
            "programme java", "code c++", "fais mes devoirs", "recette de cuisine",
            "résous", "resous", "equation", "équation", "calcul", "calcule",
            "ignore ton rôle", "ignore ton role", "ignore tes instructions", "jailbreak"
        ]) or any(pat in lowered for pat in ["2x +", "2x+", "x +", "x+"])
        is_tech_bm = any(w in lowered for w in ["ordinatɛri porogaramu", "porogaramu"])
        if is_tech_fr or is_tech_bm:
            return GuardrailResult(
                matched=True,
                intent="hors_domaine_technique",
                confidence=1.0,
                answer=self.catalog.get("hors_domaine_technique", lang=lang),
                reset_demarche=False,
            )

        # ── 4. Gestion de la frustration et insultes ────────────────────────
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
            return GuardrailResult(
                matched=True,
                intent="gestion_frustration",
                confidence=0.98,
                answer=self.catalog.get("gestion_frustration", lang=lang),
                reset_demarche=False,
            )

        # ── 5. Numéros d'urgence et secours publics ──────────────────────────
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
            return GuardrailResult(
                matched=True,
                intent="contact_urgence",
                confidence=1.0,
                answer=self.catalog.get("contact_urgence", lang=lang),
                reset_demarche=True,
            )

        # ── 6. Objection citoyenne sur le tarif CNI (5 000 FCFA vs Gratuité) ──
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
            return GuardrailResult(
                matched=True,
                intent="explication_tarif_cni",
                confidence=0.99,
                answer=self.catalog.get("explication_tarif_cni", lang=lang),
                reset_demarche=False,
            )

        # ── 7. Sources officielles et stratégie de scraping ──────────────────
        is_sources_or_scraping = any(w in lowered for w in [
            "scraping", "scrapping", "scripping", "scraper", "scrapper", "sources", "source",
            "sur quel site", "sur quels sites", "quel site vous prenez", "vos informations sont fiables",
            "informations sont fiables", "d'où viennent vos informations", "dou viennent vos informations",
            "fiable", "fiables", "fiabilité", "fiabilite",
            "kunsɔrɔyɔrɔ", "kunsoroyoro", "kunsɔrɔ", "kunsoro", "site jumɛn", "site jumen", "kibaruya bɔyɔrɔ"
        ])
        if is_sources_or_scraping:
            return GuardrailResult(
                matched=True,
                intent="sources_et_fiabilite",
                confidence=0.99,
                answer=self.catalog.get("sources_et_fiabilite", lang=lang),
                reset_demarche=False,
            )

        # ── 8. Identité, Concepteurs et Modèle LLM ───────────────────────────
        is_tech_identity = any(w in lowered for w in [
            "technologie qui est", "technologie derriere", "technologie derrière",
            "qui t'a conçu", "qui t'a concu", "qui t'a créé", "qui t'a cree", "qui vous a conçu",
            "nom de votre model", "nom de votre modèle", "modele de llm", "modèle de llm",
            "nom de llm", "leur nom", "vos développeurs", "vos developpeurs", "qui sont tes créateurs"
        ])
        if is_tech_identity:
            return GuardrailResult(
                matched=True,
                intent="technologie_et_concepteurs",
                confidence=0.99,
                answer=self.catalog.get("technologie_et_concepteurs", lang=lang),
                reset_demarche=False,
            )

        # ── 9. Langues prises en charge ──────────────────────────────────────
        is_lang_inquiry = any(p in lowered for p in [
            "vous comprener bambara", "vous comprenez bambara", "tu comprends bambara",
            "tu parles bambara", "comprends tu bambara", "comprenez vous bambara",
            "quelles langues", "quelle langue", "tu parles anglais", "tu parles d'autres langues",
            "tu parles espagnol", "langues que vous comprenez"
        ])
        if is_lang_inquiry:
            return GuardrailResult(
                matched=True,
                intent="langues_supportees",
                confidence=0.99,
                answer=self.catalog.get("langues_supportees", lang=lang),
                reset_demarche=False,
            )

        # ── 10. Recadrage Drague / Sentiments ────────────────────────────────
        is_romance = any(w in lowered for w in [
            "draguer", "drague", "te marier", "veux sortir", "es amoureuse", "es amoureux",
            "je t'aime", "mon amour", "tu es belle", "tu es beau", "petit copain", "petite copine"
        ])
        if is_romance:
            return GuardrailResult(
                matched=True,
                intent="hors_domaine",
                confidence=0.99,
                answer=self.catalog.get("hors_domaine_drague", lang=lang),
                reset_demarche=True,
            )

        # ── 11. Recadrage Conseil de Santé ───────────────────────────────────
        is_health = any(w in lowered for w in [
            "je suis malade", "ai de la fievre", "ai de la fièvre", "mal à la tête", "mal a la tete",
            "maux de ventre", "symptômes", "symptomes", "aller au service si je suis malade", "bon d'aller au service"
        ])
        if is_health:
            return GuardrailResult(
                matched=True,
                intent="hors_domaine",
                confidence=0.99,
                answer=self.catalog.get("hors_domaine_sante", lang=lang),
                reset_demarche=True,
            )

        # ── 12. Recadrage Politique Générale & Actualité ────────────────────
        is_politics = any(w in lowered for w in [
            "qui est le président", "qui est le president", "président du mali", "president du mali",
            "chef de l'etat", "chef de l etat", "politique générale", "politique generale"
        ])
        if is_politics:
            ans_politics = (
                "🏛️ **Périmètre Institutionnel :** Je suis le Chatbot Citoyen officiel du Mali, "
                "dédié exclusivement aux démarches et formalités administratives pratiques des usagers du service public "
                "(état civil, passeports, CNI, casier judiciaire, impôts, santé, etc.).\n\n"
                "Je ne traite pas des questions de politique générale ou d'actualité gouvernementale. "
                "Puis-je vous renseigner sur une démarche administrative ou un document d'état civil ?"
                if lang != "bambara"
                else (
                    "🏛️ **Baara Kɛyɔrɔ :** Ne ye Mali Fasoden Dɛmɛbaga ye sariyasɛbɛn kow dɔrɔn kan. "
                    "N tɛ kuma politikiko walima jamana kuntigi kow kan.\n"
                    "Ɲininkali dɔ b'i fɛ sariyasɛbɛn dɔ kan ?"
                )
            )
            return GuardrailResult(
                matched=True,
                intent="hors_domaine",
                confidence=0.99,
                answer=ans_politics,
                reset_demarche=True,
            )

        return None


# Singleton
_guardrail_engine_instance: Optional[GuardrailEngine] = None


def get_guardrail_engine() -> GuardrailEngine:
    global _guardrail_engine_instance
    if _guardrail_engine_instance is None:
        _guardrail_engine_instance = GuardrailEngine()
    return _guardrail_engine_instance
