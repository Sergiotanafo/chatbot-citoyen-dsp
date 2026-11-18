"""
Tests unitaires pour les Custom Actions Rasa (DSP).
"""

import unittest
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
)


class TestCustomActions(unittest.TestCase):

    def test_salutation_detection_french(self):
        act = ActionDetecterEtGererSalutation()
        disp = CollectingDispatcher()
        tr = Tracker(latest_message={"text": "Bonjour je cherche des informations"})
        events = act.run(disp, tr, {})
        self.assertEqual(events, [{"event": "slot", "name": "langue", "value": "français"}])

    def test_salutation_detection_bambara(self):
        act = ActionDetecterEtGererSalutation()
        disp = CollectingDispatcher()
        tr = Tracker(latest_message={"text": "I ni sogoma ne bɛ dɛmɛ ɲini"})
        events = act.run(disp, tr, {})
        self.assertEqual(events, [{"event": "slot", "name": "langue", "value": "bambara"}])

    def test_changer_langue_explicit_entity(self):
        act = ActionChangerLangue()
        disp = CollectingDispatcher()
        tr = Tracker(latest_message={"text": "parle en bambara", "entities": [{"entity": "langue", "value": "bambara"}]})
        events = act.run(disp, tr, {})
        self.assertEqual(events, [{"event": "slot", "name": "langue", "value": "bambara"}])

    def test_action_set_demarche(self):
        act = ActionSetDemarche()
        disp = CollectingDispatcher()
        tr = Tracker(latest_message={"intent": {"name": "demande_passeport"}})
        events = act.run(disp, tr, {})
        self.assertEqual(events, [{"event": "slot", "name": "demarche", "value": "demande_passeport"}])

    def test_repondre_cout_fr_and_bm(self):
        act = ActionRepondreCout()

        # Test Français
        disp_fr = CollectingDispatcher()
        tr_fr = Tracker(slots={"langue": "français", "demarche": "carte_identite"})
        act.run(disp_fr, tr_fr, {})
        self.assertGreater(len(disp_fr.messages), 0)
        self.assertIn("Gratuit", disp_fr.messages[0]["text"])

        # Test Bambara
        disp_bm = CollectingDispatcher()
        tr_bm = Tracker(slots={"langue": "bambara", "demarche": "carte_identite"})
        act.run(disp_bm, tr_bm, {})
        self.assertGreater(len(disp_bm.messages), 0)
        self.assertIn("FU YE", disp_bm.messages[0]["text"])

    def test_repondre_documents(self):
        act = ActionRepondreDocuments()
        disp = CollectingDispatcher()
        tr = Tracker(slots={"langue": "français", "demarche": "demande_passeport"})
        act.run(disp, tr, {})
        self.assertGreater(len(disp.messages), 0)
        self.assertIn("Documents à fournir", disp.messages[0]["text"])

    def test_repondre_delai(self):
        act = ActionRepondreDelai()
        disp = CollectingDispatcher()
        tr = Tracker(slots={"langue": "français", "demarche": "carte_identite"})
        act.run(disp, tr, {})
        self.assertGreater(len(disp.messages), 0)
        self.assertIn("semaines", disp.messages[0]["text"])

    def test_default_fallback(self):
        act = ActionDefaultFallback()
        disp = CollectingDispatcher()
        tr = Tracker(slots={"langue": "français"})
        act.run(disp, tr, {})
        self.assertGreater(len(disp.messages), 0)
        self.assertIn("Désolé", disp.messages[0]["text"])


if __name__ == "__main__":
    unittest.main()
