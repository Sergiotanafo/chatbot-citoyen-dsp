"""
Console Interactive de Test DSP — Chatbot Citoyen Malien.
Exploite l'Architecture Hybride Pérenne : Rasa Macro-Dialogue + RAG Mistral / Vector Search.
"""

import os
import sys

# Configuration du chemin
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from intelligence.router import get_hybrid_router


def run_interactive_session():
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    router = get_hybrid_router()

    # Mémoire de conversation (Slots)
    session_slots = {
        "langue": "français",
        "demarche": None,
    }

    print("=" * 68)
    print("  🇲🇱  CHATBOT CITOYEN MALIEN — ARCHITECTURE HYBRIDE RAG  🇲🇱")
    print("=" * 68)
    print("Moteur hybride actif : Rasa Macro-Dialogue + RAG Mistral / Vector Store.")
    print("Testez librement en Français et en Bambara :")
    print("  • Questions ouvertes : 'ou est ce que on trouve une autorisation parentale?'")
    print("  • Questions de suivi : 'combien ça coûte ?', 'quelles sont les pièces ?'")
    print("  • Bambara : 'I ni sogoma', 'Pasan sɔngɔ ye joli ye ?'")
    print("  • Autres démarches : CNI, NINA, Casier judiciaire, Certificat de résidence")
    print("\nTapez 'exit', 'quit' ou 'q' pour quitter.\n" + "-" * 68)

    while True:
        try:
            user_input = input("\n👤 Vous > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAu revoir !")
            break

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit", "q", "quitter"]:
            print("Fermeture de la session de test DSP. À bientôt !")
            break

        # Traitement via le Routeur Hybride
        res = router.process_message(text=user_input, current_slots=session_slots)

        intent_name = res.get("intent", "nlu_fallback")
        confidence = res.get("confidence", 0.0)
        bot_reply = res.get("answer", "")
        lang = session_slots.get("langue", "français")
        demarche_active = session_slots.get("demarche")

        # Métadonnées
        info_line = f"ℹ️  [DSP Hybride] Intention : '{intent_name}' | Confiance : {confidence:.2f} | Langue : {lang}"
        if demarche_active:
            info_line += f" | Démarche active : '{demarche_active}'"
        print(info_line)

        # Réponse
        print(f"\n🤖 Bot [{lang.upper()}] :\n   {bot_reply}")


if __name__ == "__main__":
    run_interactive_session()
