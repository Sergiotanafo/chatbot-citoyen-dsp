"""
Tests unitaires pour le moteur RAG et le générateur Mistral (DSP).
"""

import unittest
from intelligence.rag_engine import get_rag_engine
from intelligence.llm_generator import get_llm_generator


class TestRAGEngine(unittest.TestCase):

    def setUp(self):
        self.rag = get_rag_engine()
        self.generator = get_llm_generator()

    def test_rag_answers_open_question_french(self):
        """Vérifie la génération de réponse pour une question ouverte en français."""
        res = self.rag.answer_query("Comment faire un passeport au Mali ?", language="fr")
        self.assertIn("answer", res)
        self.assertEqual(res["topic"], "demande_passeport")
        self.assertGreater(res["confidence"], 0.0)
        self.assertTrue(len(res["answer"]) > 50)

    def test_rag_answers_open_question_bambara(self):
        """Vérifie la génération de réponse en Bambara."""
        res = self.rag.answer_query("Pasan sɔngɔ ye joli ye ?", language="bm")
        self.assertIn("answer", res)
        self.assertEqual(res["topic"], "demande_passeport")
        self.assertGreater(res["confidence"], 0.0)

    def test_rag_empty_or_unknown_query(self):
        """Vérifie le repli sécurisé sur question inconnue."""
        res = self.rag.answer_query("xyzabcdefg_inconnu_totale", language="fr")
        self.assertIn("answer", res)

    def test_rag_threshold_gate_rejects_out_of_domain(self):
        """Vérifie qu'une question hors domaine (ex: capitale) n'impose pas de démarche administrative."""
        res = self.rag.answer_query("quel est la capital du mali", language="fr")
        self.assertEqual(res["topic"], "hors_domaine")
        self.assertEqual(res["sources"], [])
        self.assertLess(res["confidence"], self.rag.similarity_threshold)
        self.assertIn("spécialisé dans les démarches administratives", res["answer"])

    def test_rag_legal_definition_retrieval(self):
        """Vérifie la recherche précise d'un terme juridique (ex: greffe)."""
        res = self.rag.answer_query("c'est greffe ?", language="fr")
        self.assertEqual(res["topic"], "greffe_du_tribunal")
        self.assertGreaterEqual(res["confidence"], self.rag.similarity_threshold)
        self.assertIn("secrétariat officiel", res["answer"].lower())


if __name__ == "__main__":
    unittest.main()
