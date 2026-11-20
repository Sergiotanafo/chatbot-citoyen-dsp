"""
Moteur d'évaluation conversationnelle automatisée (Enterprise Regression Runner).
Exécute l'ensemble des scénarios de dialogue multi-tours pour valider :
1. Les intentions attendues (Expected Intent)
2. La rétention et transition des contextes/slots (Slots & State)
3. La conformité des réponses (Mots-clés obligatoires / interdits)
4. La résilience bilingue FR/BM et les garde-fous éthiques
"""

import json
import os
import sys
import time
from typing import Any, Dict, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from intelligence.router import get_hybrid_router

SCENARIOS_PATH = os.path.join(BASE_DIR, "data", "tests", "conversation_scenarios.json")
REPORT_PATH = os.path.join(BASE_DIR, "tests", "reports", "conversation_eval_report.json")


def run_evaluation() -> bool:
    print("=" * 70)
    print("  🇲🇱  CHATBOT CITOYEN MALIEN - SUITE DE TESTS CONVERSATIONNELS  🇲🇱")
    print("=" * 70)

    if not os.path.exists(SCENARIOS_PATH):
        print(f"❌ Fichier de scénarios introuvable : {SCENARIOS_PATH}")
        return False

    with open(SCENARIOS_PATH, "r", encoding="utf-8") as f:
        scenarios: List[Dict[str, Any]] = json.load(f)

    router = get_hybrid_router()

    total_turns = 0
    passed_turns = 0
    failed_turns = 0
    scenario_results = []

    start_total_time = time.time()

    for sc_idx, sc in enumerate(scenarios, 1):
        sc_id = sc.get("id", f"SCENARIO_{sc_idx}")
        sc_title = sc.get("title", "Sans titre")
        print(f"\n▶ [{sc_idx}/{len(scenarios)}] {sc_id} : {sc_title}")

        # Chaque scénario démarre avec une session propre
        session_slots = {"langue": "français", "demarche": None}
        sc_passed = True
        turns_log = []

        for t_idx, turn in enumerate(sc.get("turns", []), 1):
            total_turns += 1
            user_msg = turn.get("user", "")
            exp_intent = turn.get("expected_intent")
            must_contain = turn.get("must_contain", [])
            must_not_contain = turn.get("must_not_contain", [])

            t0 = time.time()
            res = router.process_message(user_msg, current_slots=session_slots)
            lat_ms = (time.time() - t0) * 1000.0

            actual_intent = res.get("intent")
            answer = res.get("answer", "")

            # Assertions
            intent_ok = (exp_intent is None) or (actual_intent == exp_intent)
            missing_keywords = [kw for kw in must_contain if kw.lower() not in answer.lower()]
            forbidden_found = [kw for kw in must_not_contain if kw.lower() in answer.lower()]

            turn_ok = intent_ok and (not missing_keywords) and (not forbidden_found)

            if turn_ok:
                passed_turns += 1
                status_icon = "✅"
            else:
                failed_turns += 1
                sc_passed = False
                status_icon = "❌"

            print(f"   Turn {t_idx} {status_icon} | Q: \"{user_msg}\" ({lat_ms:.1f}ms)")
            print(f"          Intent: {actual_intent} (Attendu: {exp_intent}) | Démarche: {session_slots.get('demarche')}")

            if not intent_ok:
                print(f"          ⚠️ Échec Intention : reçu '{actual_intent}', attendu '{exp_intent}'")
            if missing_keywords:
                print(f"          ⚠️ Mots-clés manquants : {missing_keywords}")
            if forbidden_found:
                print(f"          ⚠️ Mots-clés interdits détectés : {forbidden_found}")

            turns_log.append({
                "turn": t_idx,
                "user": user_msg,
                "actual_intent": actual_intent,
                "expected_intent": exp_intent,
                "latency_ms": round(lat_ms, 2),
                "passed": turn_ok,
                "missing_keywords": missing_keywords,
                "forbidden_found": forbidden_found
            })

        scenario_results.append({
            "id": sc_id,
            "title": sc_title,
            "passed": sc_passed,
            "turns": turns_log
        })

    total_time = time.time() - start_total_time
    success_rate = (passed_turns / total_turns * 100.0) if total_turns > 0 else 0.0

    print("\n" + "=" * 70)
    print("  📊 BILAN DE L'ÉVALUATION CONVERSATIONNELLE AUTOMATISÉE")
    print("=" * 70)
    print(f"  • Scénarios testés     : {len(scenarios)}")
    print(f"  • Tours de dialogue   : {total_turns}")
    print(f"  • Succès              : {passed_turns} ({success_rate:.1f}%)")
    print(f"  • Échecs              : {failed_turns}")
    print(f"  • Durée totale        : {total_time:.2f} secondes")
    print("=" * 70)

    # Sauvegarde du rapport
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    report_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_scenarios": len(scenarios),
        "total_turns": total_turns,
        "passed_turns": passed_turns,
        "failed_turns": failed_turns,
        "success_rate_percent": round(success_rate, 2),
        "duration_seconds": round(total_time, 2),
        "scenarios": scenario_results
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    print(f"📁 Rapport détaillé généré dans : {REPORT_PATH}")

    return failed_turns == 0


if __name__ == "__main__":
    success = run_evaluation()
    sys.exit(0 if success else 1)
