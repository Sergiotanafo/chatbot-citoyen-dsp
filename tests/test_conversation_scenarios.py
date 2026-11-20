"""
Test unitaire intégrant les scénarios de régression conversationnels.
"""

import json
import os
import unittest
from intelligence.router import get_hybrid_router

SCENARIOS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "tests", "conversation_scenarios.json")


class TestConversationScenarios(unittest.TestCase):

    def setUp(self):
        self.router = get_hybrid_router()
        with open(SCENARIOS_PATH, "r", encoding="utf-8") as f:
            self.scenarios = json.load(f)

    def test_all_conversation_scenarios(self):
        for sc in self.scenarios:
            sc_id = sc.get("id")
            slots = {"langue": "français", "demarche": None}
            for t_idx, turn in enumerate(sc.get("turns", []), 1):
                user_msg = turn.get("user", "")
                exp_intent = turn.get("expected_intent")
                must_contain = turn.get("must_contain", [])
                must_not_contain = turn.get("must_not_contain", [])

                res = self.router.process_message(user_msg, current_slots=slots)
                actual_intent = res.get("intent")
                answer = res.get("answer", "")

                if exp_intent is not None:
                    self.assertEqual(
                        actual_intent, exp_intent,
                        f"[{sc_id} Tour {t_idx}] Échec intention pour '{user_msg}'. Reçu '{actual_intent}', attendu '{exp_intent}'"
                    )

                for kw in must_contain:
                    self.assertIn(
                        kw.lower(), answer.lower(),
                        f"[{sc_id} Tour {t_idx}] Mot-clé obligatoire '{kw}' manquant dans la réponse à '{user_msg}'"
                    )

                for kw in must_not_contain:
                    self.assertNotIn(
                        kw.lower(), answer.lower(),
                        f"[{sc_id} Tour {t_idx}] Mot-clé interdit '{kw}' détecté dans la réponse à '{user_msg}'"
                    )


if __name__ == "__main__":
    unittest.main()
