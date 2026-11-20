"""
Mise à jour de la base FAQ avec les spécifications du Mentor :
1. Ajout de acquisition_nationalite (distinction juridique stricte avec certificat_nationalite)
2. Formulation concise et naturelle de acte_deces
"""

import json
import os

path = os.path.join(os.path.dirname(__file__), "..", "data", "faq", "faq_demarches.json")
path = os.path.abspath(path)

with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Update acte_deces
for cat in data["categories"]:
    if cat["id"] == "acte_deces":
        cat["answer_fr"] = (
            "Pour déclarer un décès au Mali, il faut se rendre au centre d'état civil (mairie) du lieu du décès dans un délai légal de 30 jours.\n\n"
            "Les pièces à préparer sont :\n"
            "• Le certificat médical de décès (ou constat de décès)\n"
            "• La pièce d'identité du défunt (si disponible)\n"
            "• La pièce d'identité du déclarant (parent ou proche)\n\n"
            "La déclaration et la première délivrance sont strictement gratuites (0 FCFA) dans les 30 jours. Au-delà, un jugement déclaratif au tribunal est requis.\n\n"
            "👉 Le décès a-t-il eu lieu récemment (moins de 30 jours) ou souhaitez-vous un acte pour un décès ancien ?"
        )
        cat["answer_bm"] = (
            "Mali kɔnɔ, saya sɛbɛnli bɛ kɛ dugu mɛri (centre d'état civil) la, satuli kɛyɔrɔ la tile 30 kɔnɔ.\n\n"
            "Sɛbɛn minnu bɛ labɛn :\n"
            "• Dɔgɔtɔrɔ ka satunsɛbɛn (certificat médical)\n"
            "• Satubaga ka joyorosɛbɛn n'a bɛ yen\n"
            "• Laselibaga ka joyorosɛbɛn (CNI walima NINA)\n\n"
            "Saya sɛbɛn fɔlɔ deli ye FU YE (0 FCFA) tile 30 kɔnɔ.\n\n"
            "👉 Saya kɛra kabilabila don wa (tile 30 kɔnɔ), walima a kɔrɔlen kaban ?"
        )

# Add acquisition_nationalite if not present
if not any(c["id"] == "acquisition_nationalite" for c in data["categories"]):
    acq = {
        "id": "acquisition_nationalite",
        "title_fr": "Acquisition de la Nationalité Malienne (Naturalisation & Mariage)",
        "title_bm": "Mali fasodenya sɔrɔli (Naturalisation ani Furu)",
        "questions_fr": [
            "Comment obtenir la nationalité malienne quand on est étranger ?",
            "Comment devenir citoyen malien ?",
            "Quelles sont les conditions pour avoir la nationalité malienne ?",
            "Procédure de naturalisation au Mali",
            "Je suis étranger et je veux la nationalité malienne",
            "Je viens d'arriver au Mali et je veux la nationalité malienne",
            "Je veux devenir Malien",
            "Je viens d'arriver au Mali et je compte me procurer d'une nationalité malienne",
            "Comment acquérir la nationalité malienne ?"
        ],
        "questions_bm": [
            "Jamanatigi wɛrɛ bɛ se ka Mali fasodenya sɔrɔ cogo di ?",
            "Naturalisation sira bɛ taa cogo di Mali kɔnɔ ?",
            "N b'a fɛ ka kɛ Maliden ye",
            "N nana Mali kɔnɔ n b'a fɛ ka fasodenya sɔrɔ"
        ],
        "answer_fr": (
            "L'acquisition de la nationalité malienne par un étranger est régie par le Code des Personnes et de la Famille du Mali (Loi n°2011-087). "
            "Elle peut s'effectuer par naturalisation (résidence continue et régulière au Mali depuis au moins 5 ans, moralité, intégration) ou par mariage avec un(e) citoyen(ne) malien(ne). "
            "Le dossier est instruit par le Ministère de la Justice (Direction Nationale des Affaires Judiciaires et du Sceau) et la naturalisation est conférée par Décret en Conseil des Ministres. "
            "Elle est distincte du certificat de nationalité, qui atteste qu'une personne est déjà malienne."
        ),
        "answer_bm": (
            "Jamanatigi wɛrɛ ka Mali fasodenya sɔrɔli (naturalisation) bɛ sariyatigɛ ni Mali sariyasun ye. "
            "A bɛ sɔrɔ n'i ye san 5 kɛ Mali kɔnɔ sariyasira fɛ, walima furu fɛ ni Maliden dɔ ye. "
            "Dosiye bɛ bila Kiritigɛ minisiriso (Ministère de la Justice) la, ka Décret sɔrɔ Gɔfɛrɛnaman bolo. "
            "O tɛ kelen ye ni certificat de nationalité ye, min bɛ di mɔgɔ ma min ye Maliden ye kaban."
        ),
        "pieces_fr": (
            "1. Demande timbrée adressée au Ministre de la Justice\n"
            "2. Extrait d'acte de naissance du pays d'origine légalisé\n"
            "3. Casier judiciaire du pays d'origine et du Mali (bulletin n°3)\n"
            "4. Certificat de résidence attestant d'au moins 5 ans de séjour régulier\n"
            "5. Certificat médical attestant de l'état de santé\n"
            "6. Quittance des droits de chancellerie\n"
            "7. En cas de mariage : acte de mariage et certificat de nationalité du conjoint malien."
        ),
        "pieces_bm": (
            "1. Bataki sɛbɛn kiritigɛ minisiri ma ni tanburu ye\n"
            "2. Wolosɛbɛn i ka bɔyɔrɔ jamana la lakalanen\n"
            "3. Kititigɛso sɛbɛn (casier judiciaire) bɔyɔrɔ jamana ni Mali ta\n"
            "4. Sigiyɔrɔ sɛbɛn min b'a jira ko i kɛra san 5 Mali kɔnɔ\n"
            "5. Dɔgɔtɔrɔ ka kɛnɛya sɛbɛn\n"
            "6. Sariya sara wari sɛbɛn\n"
            "7. N'a kɛra furu ye : furusɛbɛn ni furuɲɔgɔn ka fasodenya sɛbɛn."
        ),
        "cout_fr": "Frais de chancellerie et timbre fiscal selon le barème officiel du Ministère de la Justice.",
        "cout_bm": "Kiritigɛ minisiriso ka sariya tanburu wari sarali.",
        "delai_fr": "Instruction ministérielle et décret en Conseil des Ministres (plusieurs mois).",
        "delai_bm": "Kalo damadama dosiye sɛgɛsɛgɛli kɔnɔ gɔfɛrɛnaman fɛ."
    }
    data["categories"].append(acq)

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("FAQ updated successfully. Total categories:", len(data["categories"]))
