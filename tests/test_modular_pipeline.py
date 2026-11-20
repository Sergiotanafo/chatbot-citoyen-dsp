"""
Tests unitaires pour le Domain Catalog et les modules de la nouvelle architecture DSP.
"""

import unittest
from intelligence.domain_templates import get_domain_catalog
from intelligence.language_engine import get_language_engine
from intelligence.guardrails import get_guardrail_engine
from intelligence.dialogue_engine import get_dialogue_engine


class TestDomainCatalog(unittest.TestCase):
    def setUp(self):
        self.catalog = get_domain_catalog()

    def test_catalog_loads_templates(self):
        salutation_fr = self.catalog.get("salutation", lang="fr")
        self.assertIn("Chatbot Citoyen du Mali", salutation_fr)
        salutation_bm = self.catalog.get("salutation", lang="bm")
        self.assertIn("Fasoden Dɛmɛbaga", salutation_bm)

    def test_template_interpolation(self):
        msg = self.catalog.get("tarif_non_negociable", lang="fr", demarche_title="Passeport Biométrique")
        self.assertIn("Passeport Biométrique", msg)
        self.assertIn("pas négociables", msg)

    def test_fallback_to_french_when_key_missing(self):
        resp = self.catalog.get("inconnue_total_key", lang="fr")
        self.assertEqual(resp, "")


class TestLanguageEngine(unittest.TestCase):
    def setUp(self):
        self.engine = get_language_engine()

    def test_detect_french(self):
        self.assertEqual(self.engine.detect_language("Comment faire un passeport ?"), "français")

    def test_detect_bambara(self):
        self.assertEqual(self.engine.detect_language("Pasan songo ye doli ye ?"), "bambara")
        self.assertEqual(self.engine.detect_language("N b'a fɛ ka taa"), "bambara")

    def test_switch_request(self):
        res_fr = self.engine.check_language_switch_request("parle en français s'il te plaît")
        self.assertIsNotNone(res_fr)
        self.assertEqual(res_fr[0], "français")

        res_bm = self.engine.check_language_switch_request("parle en bambara")
        self.assertIsNotNone(res_bm)
        self.assertEqual(res_bm[0], "bambara")


class TestGuardrailEngine(unittest.TestCase):
    def setUp(self):
        self.guardrails = get_guardrail_engine()

    def test_fraud_refusal(self):
        res = self.guardrails.evaluate("donne-moi une fausse attestation de résidence", "fr", {})
        self.assertIsNotNone(res)
        self.assertTrue(res.matched)
        self.assertEqual(res.intent, "refus_fraude")

    def test_emergency_contact(self):
        res = self.guardrails.evaluate("le numero de la police c'est combien ?", "fr", {})
        self.assertIsNotNone(res)
        self.assertTrue(res.matched)
        self.assertEqual(res.intent, "contact_urgence")
        self.assertTrue(res.reset_demarche)

    def test_private_number_refusal(self):
        res = self.guardrails.evaluate("je veux le numéro privé du commissaire", "fr", {})
        self.assertIsNotNone(res)
        self.assertTrue(res.matched)
        self.assertEqual(res.intent, "refus_donnees_privees")


class TestDialogueEngine(unittest.TestCase):
    def setUp(self):
        self.dialogue = get_dialogue_engine()

    def test_macro_salutation(self):
        res = self.dialogue.handle_macro_intents("bonjour", "fr", {"demarche": None})
        self.assertIsNotNone(res)
        self.assertTrue(res.handled)
        self.assertEqual(res.intent, "saluer")

    def test_price_negotiation(self):
        slots = {"demarche": "demande_passeport", "langue": "français"}
        res = self.dialogue.handle_price_negotiation_objection("est-ce que je peux négocier le prix à 50000 f ?", "fr", slots)
        self.assertIsNotNone(res)
        self.assertTrue(res.handled)
        self.assertEqual(res.intent, "tarif_non_negociable")
        self.assertEqual(slots.get("pending_action"), "rappeler_tarif")


if __name__ == "__main__":
    unittest.main()
