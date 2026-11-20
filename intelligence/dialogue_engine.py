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
        cleaned = lowered.strip().rstrip(".,!?;:")
        is_affirm = (
            cleaned in [
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

        is_deny = cleaned in [
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
        sur la démarche administrative en cours, tout en distinguant les timbres communaux.
        """
        active_dem = current_slots.get("demarche")
        if not active_dem:
            return None

        # Cas Spécial Mentor B : "est ce que je peux l'avoir à 200 f ?" / "et à 200 francs ?" sur acte de décès
        if active_dem == "acte_deces" and any(v in lowered for v in ["200", "200f", "200 f", "200 francs", "200fcfa"]):
            ans_text = self.catalog.get("tarif_acte_deces_200f", lang=lang)
            current_slots["pending_action"] = "rappeler_tarif"
            return DialogueResult(
                handled=True,
                intent="tarif_non_negociable",
                confidence=0.98,
                answer=ans_text,
                slots=current_slots,
            )

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

    def handle_nationality_and_status_clarification(
        self,
        lowered: str,
        lang: str,
        current_slots: Dict[str, Any]
    ) -> Optional[DialogueResult]:
        """
        Gère la distinction juridique essentielle (Spécification Mentor) entre :
        1. Acquisition de la nationalité malienne (ressortissant étranger désirant devenir Malien)
        2. Certificat de nationalité malienne (citoyen déjà Malien prouvant sa nationalité)
        3. Clarification de la situation documentaire pour un étranger sans papiers
        """
        # A. Cas multi-tours : L'usager a exprimé vouloir la nationalité ou être étranger, puis indique n'avoir aucun document
        is_lacking_all_docs = any(p in lowered for p in [
            "pas d'acte de naissance", "pas d acte de naissance", "aucune pièce du mali",
            "aucune piece du mali", "aucun document", "pas de papier", "j'ai rien", "jai rien"
        ])
        is_context_foreign_or_nationality = (
            current_slots.get("demarche") in ["acquisition_nationalite", "certificat_nationalite"]
            or current_slots.get("pending_question") in ["statut_nationalite", "acquisition_nationalite"]
            or current_slots.get("user_status") == "etranger"
        )
        if is_lacking_all_docs and is_context_foreign_or_nationality:
            current_slots["pending_question"] = "lieu_de_naissance"
            return DialogueResult(
                handled=True,
                intent="clarification_situation_documentaire",
                confidence=0.95,
                answer=self.catalog.get("clarification_absence_pieces_etranger", lang=lang),
                slots=current_slots,
            )

        # B. Étranger déclarant explicitement sa situation et souhaitant acquérir la nationalité (T07)
        is_explicit_foreign_acquisition = (
            any(w in lowered for w in ["je suis étranger", "je suis etranger", "ressortissant étranger", "ressortissant etranger", "viens d'arriver au mali", "viens d arriver au mali", "venir au mali"])
            and any(n in lowered for n in ["nationalité", "nationalite", "devenir malien", "citoyen malien"])
        )
        if is_explicit_foreign_acquisition:
            current_slots["demarche"] = "acquisition_nationalite"
            current_slots["user_status"] = "etranger"
            current_slots["pending_question"] = None
            ans_acq = (
                "L'acquisition de la nationalité malienne par un étranger est régie par le Code des Personnes et de la Famille (Loi n°2011-087).\n\n"
                "Elle peut s'obtenir de deux manières principales :\n"
                "1. **Par naturalisation :** Résidence habituelle et régulière au Mali depuis au moins 5 ans, justification de moyens d'existence, bonne moralité et assimilation.\n"
                "2. **Par le mariage :** Après un délai légal de vie commune avec un(e) citoyen(ne) malien(ne).\n\n"
                "Le dossier est adressé au Ministre de la Justice (Direction Nationale des Affaires Judiciaires et du Sceau) et la naturalisation est conférée par Décret en Conseil des Ministres.\n\n"
                "Avez-vous déjà résidé plus de 5 ans au Mali ou êtes-vous marié(e) à un(e) citoyen(ne) malien(ne) ?"
                if lang != "bambara"
                else (
                    "Jamanatigi wɛrɛ ka Mali fasodenya sɔrɔli (naturalisation) bɛ sariyatigɛ ni Mali sariyasun ye.\n\n"
                    "A sira fɔlɔ fila bɛ yen :\n"
                    "1. **Naturalisation :** N'i ye san 5 kɛ Mali kɔnɔ sariyasira fɛ, ka baara sɔrɔ ani ka jogonuma jira.\n"
                    "2. **Furu fɛ :** N'i bɛ furu kɔnɔ ni Maliden dɔ ye.\n\n"
                    "Dosiye bɛ bila Kiritigɛ minisiriso (Ministère de la Justice) la, ka Décret sɔrɔ Gɔfɛrɛnaman bolo.\n\n"
                    "I ye san 5 kɛ Mali kɔnɔ kaban wa, walima i furulen don ni Maliden ye ?"
                )
            )
            return DialogueResult(
                handled=True,
                intent="acquisition_nationalite",
                confidence=0.95,
                answer=ans_acq,
                slots=current_slots,
            )

        # C. Malien déclarant explicitement qu'il est déjà Malien mais n'a pas de document (T08)
        is_malian_needs_proof = (
            any(w in lowered for w in ["je suis malien", "je suis malienne", "suis de nationalité malienne"])
            and any(n in lowered for n in ["pas de certificat", "prouver ma nationalité", "certificat de nationalité", "certificat", "document"])
        )
        if is_malian_needs_proof:
            current_slots["demarche"] = "certificat_nationalite"
            current_slots["user_status"] = "malien"
            ans_cert = (
                "Si vous êtes déjà citoyen malien d'origine, vous devez demander un **Certificat de Nationalité Malienne**.\n\n"
                "Ce document est délivré par le Président du Tribunal d'Instance de votre lieu de naissance.\n\n"
                "📋 **Pièces à fournir :**\n"
                "1. Votre extrait d'acte de naissance (ou jugement supplétif)\n"
                "2. L'acte de naissance ou certificat de nationalité du père ou de la mère\n"
                "3. Une demande timbrée (timbre fiscal de 1 000 FCFA)\n"
                "4. Copie de votre pièce d'identité (CNI ou NINA).\n\n"
                "⏱️ Délai : 24h à 72h ouvrées au tribunal."
                if lang != "bambara"
                else (
                    "N'i ye Maliden ye kaban, i mako bɛ **Malidenya sariyasɛbɛn** (Certificat de nationalité) de la.\n\n"
                    "A bɛ bɔ i ka woloyɔrɔ Kititigɛso (Tribunal) la.\n"
                    "Sɛbɛnw : wolosɛbɛn, bangebaga ka wolosɛbɛn, tanburu FCFA 1 000 ani joyorosɛbɛn."
                )
            )
            return DialogueResult(
                handled=True,
                intent="certificat_nationalite",
                confidence=0.98,
                answer=ans_cert,
                slots=current_slots,
            )

        # D. Demande ambiguë sur la nationalité ("je veux devenir malien", "avoir la nationalité malienne") (T06)
        is_ambiguous_nationality = (
            any(w in lowered for w in [
                "devenir malien", "devenir malienne", "procurer d'une nationalité", "procurer une nationalité",
                "avoir la nationalité malienne", "avoir la nationalite malienne",
                "obtenir la nationalité malienne", "obtenir la nationalite malienne",
                "demande de nationalité", "demande de nationalite", "prendre la nationalité"
            ])
            and "certificat" not in lowered
        )
        if is_ambiguous_nationality:
            current_slots["pending_question"] = "statut_nationalite"
            return DialogueResult(
                handled=True,
                intent="clarification_nationalite",
                confidence=0.95,
                answer=self.catalog.get("clarification_nationalite", lang=lang),
                slots=current_slots,
            )

        # E. Clarification sur naissance au Niger / pays étranger vivant au Mali (T11)
        if any(w in lowered for w in ["né au niger", "ne au niger", "né en côte d'ivoire", "ne en cote d ivoire", "né au burkina", "ne au burkina", "né au sénégal", "ne au senegal", "né à l'étranger", "ne a l etranger"]) and any(v in lowered for v in ["vis au mali", "visite le mali", "au mali"]):
            current_slots["user_status"] = "etranger"
            ans_foreign_born = (
                "Si vous êtes né à l'étranger et résidez au Mali, vous conservez votre état civil de votre pays d'origine.\n\n"
                "• Pour vos actes d'état civil (acte de naissance), vous devez vous adresser au consulat ou à l'ambassade de votre pays de naissance au Mali.\n"
                "• Si votre objectif est de vous établir durablement au Mali, vous pouvez solliciter une **carte de séjour** auprès de la Direction Générale de la Police Nationale.\n"
                "• Si vous souhaitez devenir citoyen malien après 5 années de résidence régulière, vous pourrez introduire une demande de **naturalisation** auprès du Ministère de la Justice.\n\n"
                "Souhaitez-vous des renseignements sur la carte de séjour ou sur la procédure de naturalisation ?"
                if lang != "bambara"
                else (
                    "N'i wolola jamana wɛrɛ la ka sigi Mali kɔnɔ, i ka bɔyɔrɔ jamana ka sɛbɛnw de bɛ baara kɛ i bolo.\n\n"
                    "Wolosɛbɛn bɛ sɔrɔ i ka jamana ka ambassade la Bamako. N'i b'a fɛ ka sigi Mali kɔnɔ sariyasira fɛ, i bɛ sigisɛbɛn (carte de séjour) ɲini polisiba la."
                )
            )
            return DialogueResult(
                handled=True,
                intent="orientation_ressortissant_etranger",
                confidence=0.95,
                answer=ans_foreign_born,
                slots=current_slots,
            )

        # F. Citoyen né au Mali sans acte de naissance (T10)
        if any(w in lowered for w in ["né au mali", "ne au mali", "suis né ici"]) and any(w in lowered for w in ["pas d'acte", "pas d acte", "sans acte"]):
            current_slots["demarche"] = "jugement_suppletif_d_acte_de_naissance"
            ans_suppletif = (
                "Si vous êtes né sur le territoire malien mais que votre naissance n'a pas été déclarée à la mairie dans le délai légal de 30 jours, "
                "la seule procédure légale pour obtenir votre acte de naissance est le **Jugement Supplétif d'Acte de Naissance**.\n\n"
                "🏛️ **Lieu de dépôt :** Tribunal d'Instance (ou Justice de Paix à Compétence Étendue) de votre lieu de naissance.\n\n"
                "📋 **Pièces à fournir :**\n"
                "1. Certificat d'âge apparent (délivré par un médecin agréé)\n"
                "2. Deux (2) témoins majeurs connaissant votre filiation\n"
                "3. Certificat de non-inscription de naissance (délivré par le centre d'état civil / mairie)\n"
                "4. Frais de justice réglementés (timbre et droits de greffe d'environ 2 500 à 5 000 FCFA).\n\n"
                "Souhaitez-vous des détails sur l'audience ou les témoins à présenter ?"
                if lang != "bambara"
                else (
                    "N'i wolola Mali kɔnɔ nka i ma sɛbɛn mɛri la tile 30 kɔnɔ, i mako bɛ **Kititigɛso wolosɛbɛn** (Jugement supplétif) de la.\n\n"
                    "A bɛ sɔrɔ Kititigɛso (Tribunal) la i ka woloyɔrɔ la. Sɛbɛnw : dɔgɔtɔrɔ ka si sɛbɛn, seere fila (2), mɛri ka lase ko i ma sɛbɛn yen fɔlɔ, ani kititigɛ tanburu."
                )
            )
            return DialogueResult(
                handled=True,
                intent="jugement_suppletif_d_acte_de_naissance",
                confidence=0.98,
                answer=ans_suppletif,
                slots=current_slots,
            )

        # G. Question de suivi sur passeport pour enfant / mineur (T14: "Et pour un enfant ?")
        if current_slots.get("demarche") == "demande_passeport" and any(w in lowered for w in ["enfant", "mineur", "denmisen", "denmisɛn", "bébé", "bebe", "petit"]):
            ans_enfant = (
                "Pour établir un **passeport biométrique pour un enfant mineur** au Mali, la procédure comporte des pièces spécifiques obligatoires :\n\n"
                "📋 **Pièces requises pour le mineur :**\n"
                "1. **Autorisation parentale légalisée** (signée par le père ou le tuteur légal au commissariat ou à la mairie)\n"
                "2. Extrait d'acte de naissance du mineur (ou jugement supplétif)\n"
                "3. Fiche NINA ou récépissé RAVEC de l'enfant\n"
                "4. Copie de la pièce d'identité (CNI ou passeport) du parent ou tuteur\n"
                "5. Deux (2) photos d'identité fond blanc récentes\n"
                "6. Quittance du Trésor public de 50 000 FCFA (ou 55 000 FCFA).\n\n"
                "👉 La présence physique de l'enfant et du parent est obligatoire lors de l'enrôlement biométrique à la DGPN."
                if lang != "bambara"
                else (
                    "Denmisɛn ka pasan (passeport) labɛnni Mali kɔnɔ bɛ bangebaga ka yamaruya de ɲini :\n\n"
                    "1. **Bangebaga ka yamaruya sɛbɛn** (autorisation parentale) min lakalanen don mɛri walima polisiso la\n"
                    "2. Denmisɛn ka wolosɛbɛn\n"
                    "3. NINA sɛbɛn walima RAVEC\n"
                    "4. Bangebaga ka joyorosɛbɛn\n"
                    "5. Ja fɔtɔ fila fond blanc\n"
                    "6. Pasan wari FCFA 50 000.\n\n"
                    "Bangebaga ni den bɛɛ ka taa DGPN la biométrie kama."
                )
            )
            return DialogueResult(
                handled=True,
                intent="demande_passeport",
                confidence=0.98,
                answer=ans_enfant,
                slots=current_slots,
            )

        # H. Reformulation plus simple demandée par l'usager (T20: "Je ne comprends pas, explique plus simplement.")
        if any(p in lowered for p in ["explique plus simplement", "explique simplement", "pas compris", "pas bien compris", "plus simple", "en mots simples", "fais simple", "k'a nɔgɔya", "faamuya"]):
            active_dem = current_slots.get("demarche")
            if active_dem:
                dem_name = active_dem.replace("_", " ")
                ans_simple = (
                    f"En résumé très simple pour **{dem_name}** :\n\n"
                    "1. **Où aller :** Rendez-vous au service compétent (commissariat, mairie ou tribunal selon le document).\n"
                    "2. **Ce qu'il faut apporter :** Votre extrait de naissance, votre pièce d'identité (ou NINA) et vos photos d'identité.\n"
                    "3. **Frais :** Payez uniquement le tarif officiel affiché au guichet légal contre reçu.\n\n"
                    "Quel point particulier souhaitez-vous que je vous réexplique ?"
                    if lang != "bambara"
                    else (
                        f"Kuma nɔgɔman na **{dem_name}** kan :\n\n"
                        "1. **Taa yɔrɔ :** Taa mɛri, polisiso walima kititigɛso la.\n"
                        "2. **Sɛbɛnw :** I ka wolosɛbɛn, joyorosɛbɛn (NINA) ni ja.\n"
                        "3. **Wari :** Sara sariya sɔngɔ lakika dɔrɔn de la.\n\n"
                        "Mun yɔrɔ de kɔrɔ ma faamu i ma ?"
                    )
                )
            else:
                ans_simple = (
                    "Pas de souci, simplifions ! Dites-moi juste le nom du papier que vous voulez obtenir (par exemple : carte d'identité, passeport, acte de naissance, casier judiciaire), et je vous donne les 3 étapes faciles pour l'avoir."
                    if lang != "bambara"
                    else "N'a ma foyi kɛ ! A fɔ n ye dɔrɔn sɛbɛn min b'i bolo (pasan, CNI, wolosɛbɛn), n b'a sira nɔgɔman jira i ye."
                )
            return DialogueResult(
                handled=True,
                intent="clarification",
                confidence=0.98,
                answer=ans_simple,
                slots=current_slots,
            )

        return None

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
