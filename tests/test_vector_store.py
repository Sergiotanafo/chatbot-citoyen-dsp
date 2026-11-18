"""
Tests unitaires pour le Dense & Hybrid Vector Store (DSP).
"""

import unittest
from intelligence.vector_store import get_vector_store, DenseVectorStore


class TestVectorStore(unittest.TestCase):

    def setUp(self):
        self.store = get_vector_store()

    def test_vector_store_initialization_and_chunk_count(self):
        """Vérifie que les documents de la base de connaissances sont bien indexés."""
        self.assertGreater(len(self.store.chunks), 0)
        self.assertEqual(len(self.store.chunks), len(self.store.vectors))

    def test_similarity_search_passport_french(self):
        """Recherche par similarité dense pour le passeport en français."""
        hits = self.store.similarity_search("Comment faire une demande de passeport biométrique ?", language="fr", top_k=2)
        self.assertGreater(len(hits), 0)
        self.assertEqual(hits[0].topic, "demande_passeport")
        self.assertEqual(hits[0].language, "fr")

    def test_similarity_search_cni_bambara(self):
        """Recherche par similarité dense pour la CNI en Bambara."""
        hits = self.store.similarity_search("Fasodenya sariyasɛbɛn CNI bɛ sɔrɔ cogo di ?", language="bm", top_k=2)
        self.assertGreater(len(hits), 0)
        self.assertEqual(hits[0].topic, "carte_identite")
        self.assertEqual(hits[0].language, "bm")

    def test_similarity_search_parental_authorization(self):
        """Recherche spécifique pour l'autorisation parentale."""
        hits = self.store.similarity_search("où trouver une autorisation parentale ?", language="fr", top_k=1)
        self.assertGreater(len(hits), 0)
        self.assertIn(hits[0].topic, ["autorisation_parentale", "demande_passeport"])


if __name__ == "__main__":
    unittest.main()
