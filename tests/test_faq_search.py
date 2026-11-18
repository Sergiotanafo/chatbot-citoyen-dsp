"""
Tests unitaires pour le moteur de recherche sémantique FAQ (DSP).
"""

import unittest
from intelligence.faq_search import search_knowledge_base, get_faq_engine


class TestFAQSearch(unittest.TestCase):

    def setUp(self):
        self.engine = get_faq_engine()

    def test_search_fr_passport_cost(self):
        """Vérifie la recherche en français sur le coût du passeport."""
        hits = search_knowledge_base("Combien coûte le passeport adulte ?", language="fr", top_k=2)
        self.assertGreater(len(hits), 0)
        self.assertEqual(hits[0]["topic"], "demande_passeport")
        self.assertGreater(hits[0]["score"], 0.0)

    def test_search_fr_cni(self):
        """Vérifie la recherche en français sur la carte d'identité."""
        hits = search_knowledge_base("Comment obtenir une carte d'identité biométrique à Bamako ?", language="fr", top_k=2)
        self.assertGreater(len(hits), 0)
        self.assertEqual(hits[0]["topic"], "carte_identite")

    def test_search_bm_cni(self):
        """Vérifie la recherche en Bambara pour la CNI."""
        hits = search_knowledge_base("N bɛ se ka fasodenya sariyasɛbɛn sɔrɔ cogo di ?", language="bm", top_k=2)
        self.assertGreater(len(hits), 0)
        self.assertEqual(hits[0]["topic"], "carte_identite")

    def test_search_bm_passport(self):
        """Vérifie la recherche en Bambara pour le passeport."""
        hits = search_knowledge_base("Pasan sɔngɔ ye joli ye Mali kɔnɔ ?", language="bm", top_k=2)
        self.assertGreater(len(hits), 0)
        self.assertEqual(hits[0]["topic"], "demande_passeport")

    def test_empty_query(self):
        """Vérifie le comportement sur requête vide."""
        hits = search_knowledge_base("", language="fr")
        self.assertEqual(len(hits), 0)


if __name__ == "__main__":
    unittest.main()
