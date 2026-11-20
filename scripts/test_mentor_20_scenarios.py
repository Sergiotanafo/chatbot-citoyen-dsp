"""
Test complet des 20 Scénarios Naturels du Mentor dans le terminal.
Exécute chaque scénario tour par tour avec conservation d'état conversationnel,
mesure la compréhension, le contexte, la détection des intentions et la qualité des réponses.
"""

import sys
import os
import json
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from intelligence.router import get_hybrid_router


def run_mentor_20_conversations():
    router = get_hybrid_router()

    scenarios = [
        {
            "id": "SCENARIO_01_CARTE_IDENTITE",
            "title": "Scénario 1 — Demande classique (Carte d'identité)",
            "turns": [
                {"input": "Bonjour, je veux faire ma carte d'identité.", "expected_intent": "carte_identite"},
                {"input": "Qu'est-ce qu'il me faut ?", "expected_intent": "demander_documents"},
                {"input": "Et si j'ai pas mon acte de naissance ?", "keywords": ["jugement supplétif", "supplétif", "mairie", "nina"]},
                {"input": "J'ai seulement mon récépissé NINA, ça suffit ?", "keywords": ["nina", "ravec", "certificat", "résidence"]},
                {"input": "Je dois aller où pour la faire ?", "keywords": ["commissariat", "gendarmerie", "arrondissement", "brigade"]},
                {"input": "Ça prend combien de temps ?", "expected_intent": "demander_delai"}
            ]
        },
        {
            "id": "SCENARIO_02_UTILISATEUR_NOVICE",
            "title": "Scénario 2 — Utilisateur novice (Preuve de nationalité)",
            "turns": [
                {"input": "Bonjour, je ne connais pas trop les démarches administratives.", "expected_intent": "saluer"},
                {"input": "Je voudrais avoir un document qui prouve que je suis Malien.", "keywords": ["nationalité", "certificat", "carte", "tribunal"]},
                {"input": "Comment je peux faire ?", "keywords": ["tribunal", "pièces", "demande", "instance"]},
                {"input": "C'est différent de l'acte de naissance ?", "keywords": ["acte de naissance", "tribunal", "état civil", "différent"]},
                {"input": "Et si mon père n'a pas de certificat de nationalité ?", "keywords": ["père", "mère", "naissance", "filiation", "parent"]}
            ]
        },
        {
            "id": "SCENARIO_03_PERTE_DOCUMENTS",
            "title": "Scénario 3 — Citoyen ayant perdu ses papiers",
            "turns": [
                {"input": "J'ai perdu tous mes papiers.", "keywords": ["perte", "déclaration", "commissariat", "commencer"]},
                {"input": "Je ne sais même pas par où commencer.", "keywords": ["déclaration de perte", "commissariat", "priorité", "étape"]},
                {"input": "J'avais ma carte d'identité mais je l'ai perdue.", "keywords": ["duplicata", "perte", "timbre", "1 000"]},
                {"input": "Je n'ai plus non plus mon acte de naissance.", "keywords": ["mairie", "registre", "copie", "duplicata", "naissance"]},
                {"input": "Est-ce que je peux refaire tout ça ?", "keywords": ["oui", "registre", "possible", "démarche"]},
                {"input": "Je commence par lequel ?", "keywords": ["déclaration de perte", "acte de naissance", "commissariat", "mairie"]}
            ]
        },
        {
            "id": "SCENARIO_04_OBTENIR_PASSEPORT",
            "title": "Scénario 4 — Demande de passeport",
            "turns": [
                {"input": "Je veux voyager à l'étranger.", "keywords": ["passeport", "voyage", "document"]},
                {"input": "Comment obtenir un passeport malien ?", "expected_intent": "demande_passeport"},
                {"input": "Il faut quoi comme documents ?", "expected_intent": "demander_documents"},
                {"input": "Et ça coûte combien ?", "expected_intent": "demander_cout"},
                {"input": "Je peux faire la demande à Bamako ?", "keywords": ["dgpn", "hamdallaye", "police", "bamako"]},
                {"input": "Et si mon passeport expire bientôt ?", "keywords": ["renouvellement", "ancien passeport", "police", "expir"]}
            ]
        },
        {
            "id": "SCENARIO_05_QUESTIONS_COURTES",
            "title": "Scénario 5 — Test de mémoire conversationnelle (Questions très courtes)",
            "turns": [
                {"input": "Comment obtenir un certificat de résidence ?", "expected_intent": "certificat_residence"},
                {"input": "Où ?", "keywords": ["mairie", "commissariat", "quartier", "chef"]},
                {"input": "Combien ?", "expected_intent": "demander_cout"},
                {"input": "Quels documents ?", "expected_intent": "demander_documents"},
                {"input": "Et si je suis locataire ?", "keywords": ["bail", "loyer", "propriétaire", "quittance"]},
                {"input": "Et si je n'ai pas de contrat de location ?", "keywords": ["chef de quartier", "témoins", "attestation"]}
            ]
        },
        {
            "id": "SCENARIO_06_CREATION_ENTREPRISE",
            "title": "Scénario 6 — Jeune entrepreneur",
            "turns": [
                {"input": "Je veux créer mon entreprise au Mali.", "expected_intent": "creation_entreprise"},
                {"input": "Je veux vendre des vêtements.", "keywords": ["commerce", "entreprise", "individuelle", "api"]},
                {"input": "Je dois commencer par quoi ?", "keywords": ["guichet unique", "api-mali", "dossier", "statuts"]},
                {"input": "C'est quoi le RCCM ?", "keywords": ["registre", "commerce", "crédit mobilier", "tribunal"]},
                {"input": "Il faut aussi un NIF ?", "keywords": ["numéro d'identification fiscale", "nif", "impôts", "guichet"]},
                {"input": "Je peux faire toutes ces démarches au même endroit ?", "keywords": ["api-mali", "guichet unique", "72h", "endroit"]}
            ]
        },
        {
            "id": "SCENARIO_07_LANGAGE_POPULAIRE",
            "title": "Scénario 7 — Questions avec fautes et langage naturel (Papier de naissance)",
            "turns": [
                {"input": "Je veux faire mon papier de naissance.", "keywords": ["naissance", "mairie", "acte"]},
                {"input": "On m'a dit que je dois aller au tribunal.", "keywords": ["tribunal", "délai", "jugement supplétif", "30 jours"]},
                {"input": "C'est vrai ça ?", "keywords": ["vrai", "tribunal", "délai", "30 jours", "supplétif"]},
                {"input": "Moi j'ai jamais eu de papier depuis ma naissance.", "expected_intent": "jugement_suppletif_d_acte_de_naissance"},
                {"input": "Je fais comment maintenant ?", "keywords": ["témoins", "âge apparent", "tribunal", "certificat"]}
            ]
        },
        {
            "id": "SCENARIO_08_CHANGEMENT_D_AVIS",
            "title": "Scénario 8 — Changement de démarche",
            "turns": [
                {"input": "Comment obtenir un casier judiciaire ?", "expected_intent": "casier_judiciaire"},
                {"input": "Quels sont les documents ?", "expected_intent": "demander_documents"},
                {"input": "Merci.", "expected_intent": "remerciement"},
                {"input": "Finalement, je veux plutôt faire un certificat de résidence.", "expected_intent": "certificat_residence"},
                {"input": "Comment je fais ?", "keywords": ["mairie", "commissariat", "résidence"]},
                {"input": "Et le passeport aussi, je peux le faire ?", "expected_intent": "demande_passeport"}
            ]
        },
        {
            "id": "SCENARIO_09_AMBIGUITE_NATIONALITE",
            "title": "Scénario 9 — Question ambiguë sur la nationalité",
            "turns": [
                {"input": "Je veux devenir Malien.", "expected_intent": "clarification_nationalite"},
                {"input": "Je suis arrivé au Mali il y a quelques années.", "keywords": ["naturalisation", "résidence", "5 ans"]},
                {"input": "Je ne suis pas né ici.", "keywords": ["étranger", "naturalisation", "pays"]},
                {"input": "Je dois faire quoi ?", "keywords": ["justice", "naturalisation", "ministère", "dossier"]},
                {"input": "Je n'ai pas de document malien.", "expected_intent": "clarification_situation_documentaire"}
            ]
        },
        {
            "id": "SCENARIO_10_GESTION_CONTESTATION",
            "title": "Scénario 10 — Gestion de la contestation et explications simples",
            "turns": [
                {"input": "Je veux faire ma carte d'identité.", "expected_intent": "carte_identite"},
                {"input": "Je ne comprends pas.", "expected_intent": "clarification"},
                {"input": "Explique-moi plus simplement.", "expected_intent": "clarification"},
                {"input": "Tu m'as dit que c'était gratuit mais à la mairie on m'a demandé de payer. Pourquoi ?", "expected_intent": "explication_tarif_cni"},
                {"input": "Alors qu'est-ce que je dois faire maintenant ?", "keywords": ["80 00 11 15", "quittance", "recours", "police"]}
            ]
        },
        {
            "id": "SCENARIO_11_HORS_DOMAINE_ET_RETOUR",
            "title": "Scénario 11 — Questions hors domaine dans une conversation administrative",
            "turns": [
                {"input": "Comment faire un passeport ?", "expected_intent": "demande_passeport"},
                {"input": "Au fait, qui a gagné la dernière CAN ?", "expected_intent": "hors_domaine"},
                {"input": "D'accord, revenons au passeport. Quels sont les documents ?", "expected_intent": "demander_documents"},
                {"input": "Et combien de temps ça prend ?", "expected_intent": "demander_delai"}
            ]
        },
        {
            "id": "SCENARIO_12_BAMBARA_AUTHENTIQUE",
            "title": "Scénario 12 — Conversation en Bambara",
            "turns": [
                {"input": "I ni sogoma.", "expected_intent": "saluer"},
                {"input": "N b'a fɛ ka NINA sɔrɔ, n bɛ taa min ?", "expected_intent": "carte_nina"},
                {"input": "N bɛ taa min ?", "keywords": ["ravec", "mɛri", "yɔrɔ"]},
                {"input": "I ni ce, barika.", "expected_intent": "remerciement"}
            ]
        },
        {
            "id": "SCENARIO_13_MARIAGE_ET_ETAT_CIVIL",
            "title": "Scénario 13 — Mariage et état civil",
            "turns": [
                {"input": "Je veux me marier civilement au Mali.", "expected_intent": "acte_mariage"},
                {"input": "Quelles sont les démarches ?", "keywords": ["bans", "mairie", "mariage", "délai"]},
                {"input": "Il faut quels documents ?", "expected_intent": "demander_documents"},
                {"input": "Est-ce que les deux personnes doivent être présentes ?", "keywords": ["présence", "époux", "mairie", "obligatoire"]},
                {"input": "Et si l'un des deux est étranger ?", "keywords": ["coutume", "célibat", "ambassade", "consulat"]}
            ]
        },
        {
            "id": "SCENARIO_14_BESOIN_SANS_NOM",
            "title": "Scénario 14 — Utilisateur qui ne sait pas nommer son besoin",
            "turns": [
                {"input": "Je veux un papier pour prouver que j'habite dans mon quartier.", "expected_intent": "certificat_residence"},
                {"input": "C'est pour un dossier de concours.", "keywords": ["résidence", "concours", "dossier", "mairie"]},
                {"input": "La mairie doit me donner ce papier, non ?", "keywords": ["oui", "mairie", "centre", "résidence"]}
            ]
        },
        {
            "id": "SCENARIO_15_CONCOURS_FONCTION_PUBLIQUE",
            "title": "Scénario 15 — Candidat à un concours de la fonction publique",
            "turns": [
                {"input": "Je veux participer à un concours de la fonction publique.", "keywords": ["concours", "fonction publique", "cncfp", "recrutement"]},
                {"input": "Comment savoir quels concours sont ouverts ?", "keywords": ["cncfp", "journal officiel", "ministère", "site"]},
                {"input": "Il faut quoi pour s'inscrire ?", "keywords": ["casier judiciaire", "nationalité", "diplôme", "certificat"]},
                {"input": "Est-ce qu'un étudiant peut participer ?", "keywords": ["diplôme", "bac", "licence", "condition"]},
                {"input": "Où je peux consulter les annonces officielles ?", "keywords": ["cncfp-mali.ml", "fonctionpublique", "affichage", "journal"]}
            ]
        },
        {
            "id": "SCENARIO_16_UTILISATEUR_PRESSE",
            "title": "Scénario 16 — Interaction courte et utilisateur pressé",
            "turns": [
                {"input": "Bonjour.", "expected_intent": "saluer"},
                {"input": "Je veux renouveler ma carte d'identité.", "expected_intent": "carte_identite"},
                {"input": "C'est urgent.", "keywords": ["récépissé", "commissariat", "délai", "provisoire"]},
                {"input": "Je fais comment ?", "keywords": ["commissariat", "photos", "nina", "dépôt"]}
            ]
        },
        {
            "id": "SCENARIO_17_SUIVI_CASIER_JUDICIAIRE",
            "title": "Scénario 17 — Questions successives sur le casier judiciaire",
            "turns": [
                {"input": "Comment obtenir un casier judiciaire ?", "expected_intent": "casier_judiciaire"},
                {"input": "Il faut quoi ?", "expected_intent": "demander_documents"},
                {"input": "Et si je suis né dans une autre région ?", "keywords": ["tribunal", "naissance", "région", "instance"]},
                {"input": "Je peux envoyer quelqu'un à ma place ?", "keywords": ["procuration", "personne", "parent", "mandat"]},
                {"input": "Il faut combien de temps ?", "expected_intent": "demander_delai"},
                {"input": "Et si je le veux pour un concours ?", "keywords": ["bulletin n°3", "3 mois", "validité", "concours"]}
            ]
        },
        {
            "id": "SCENARIO_18_PEDAGOGIQUE_NINA_CNI",
            "title": "Scénario 18 — Test pédagogique (Distinction NINA vs CNI)",
            "turns": [
                {"input": "C'est quoi le NINA ?", "expected_intent": "carte_nina"},
                {"input": "Je n'ai pas compris.", "expected_intent": "clarification"},
                {"input": "Explique-moi comme si je n'avais jamais fait de démarche administrative.", "expected_intent": "clarification"},
                {"input": "Donc le NINA et la carte d'identité c'est la même chose ?", "keywords": ["différent", "numéro", "carte physique", "biométrique"]}
            ]
        },
        {
            "id": "SCENARIO_19_ANTI_FRAUDE_SECURITE",
            "title": "Scénario 19 — Test de sécurité administrative et anti-fraude",
            "turns": [
                {"input": "Je veux faire une carte d'identité mais je n'ai pas tous les documents.", "keywords": ["pièces", "manquantes", "commissariat", "nina"]},
                {"input": "Il n'y a pas un moyen de contourner ça ?", "expected_intent": "refus_fraude"},
                {"input": "Je peux payer quelqu'un pour qu'il me la fasse sans les documents ?", "expected_intent": "refus_fraude"}
            ]
        },
        {
            "id": "SCENARIO_20_SESSION_LONGUE_PARCOURS",
            "title": "Scénario 20 — Session longue et parcours administratif ordonné",
            "turns": [
                {"input": "Bonjour, je veux régulariser mes papiers.", "keywords": ["papiers", "démarche", "ordre", "aider"]},
                {"input": "J'ai mon acte de naissance mais pas de NINA.", "keywords": ["ravec", "enrôlement", "nina", "centre"]},
                {"input": "Je veux aussi une carte d'identité.", "keywords": ["carte d'identité", "cni", "nina", "gratuite"]},
                {"input": "Et un passeport après.", "keywords": ["passeport", "police", "dgpn", "nationalité"]},
                {"input": "Dans quel ordre je dois faire les démarches ?", "keywords": ["1", "2", "3", "ordre", "d'abord"]},
                {"input": "Tu peux me résumer les étapes ?", "keywords": ["étape", "résumé", "1", "2"]}
            ]
        }
    ]

    print("=" * 75)
    print("  🇲🇱  TEST DES 20 SCÉNARIOS CONVERSATIONNELS DU MENTOR  🇲🇱")
    print("=" * 75)

    total_scenarios = len(scenarios)
    total_turns = 0
    passed_turns = 0
    failed_turns = 0

    results = []

    for s_idx, sc in enumerate(scenarios, 1):
        print(f"\n▶ [{s_idx}/{total_scenarios}] {sc['title']}")
        slots = {"langue": "français", "demarche": None}
        scenario_passed = True

        for t_idx, turn in enumerate(sc["turns"], 1):
            total_turns += 1
            user_msg = turn["input"]
            start_t = time.perf_counter()
            res = router.process_message(user_msg, current_slots=slots)
            elapsed_ms = (time.perf_counter() - start_t) * 1000

            intent = res.get("intent")
            answer = res.get("answer", "")
            ans_lower = answer.lower()

            turn_ok = True
            errors = []

            # Check expected_intent
            if "expected_intent" in turn:
                exp = turn["expected_intent"]
                if intent != exp:
                    turn_ok = False
                    errors.append(f"Intent attendu '{exp}', reçu '{intent}'")

            # Check keywords
            if "keywords" in turn:
                for kw in turn["keywords"]:
                    if kw.lower() not in ans_lower:
                        # Allow partial match if any of the keywords match
                        pass
                # Check if at least one keyword is matched
                matched_kws = [kw for kw in turn["keywords"] if kw.lower() in ans_lower]
                if not matched_kws:
                    turn_ok = False
                    errors.append(f"Aucun mot-clé trouvé parmi {turn['keywords']}")

            if turn_ok:
                passed_turns += 1
                print(f"   Turn {t_idx} ✅ | Q: \"{user_msg}\" ({elapsed_ms:.1f}ms)")
                print(f"          Intent: {intent} | Démarche: {slots.get('demarche')}")
            else:
                failed_turns += 1
                scenario_passed = False
                print(f"   Turn {t_idx} ❌ | Q: \"{user_msg}\" ({elapsed_ms:.1f}ms)")
                print(f"          Intent: {intent} (Attendu: {turn.get('expected_intent')}) | Démarche: {slots.get('demarche')}")
                print(f"          Réponse : {answer[:180]}...")
                for err in errors:
                    print(f"          ⚠️ {err}")

        results.append({
            "scenario": sc["id"],
            "title": sc["title"],
            "passed": scenario_passed
        })

    print("\n" + "=" * 75)
    print(f"  📊 BILAN DE L'ÉVALUATION DES 20 SCÉNARIOS")
    print(f"  • Scénarios testés     : {total_scenarios}")
    print(f"  • Tours de dialogue   : {total_turns}")
    print(f"  • Succès              : {passed_turns} ({passed_turns/total_turns*100:.1f}%)")
    print(f"  • Échecs              : {failed_turns}")
    print("=" * 75)

    return failed_turns == 0


if __name__ == "__main__":
    success = run_mentor_20_conversations()
    sys.exit(0 if success else 1)
