"""
Tests unitaires pour le prétraitement et nettoyage de la parole (DSP Speech).
"""

import unittest
import numpy as np
from speech.text_cleaning import clean_for_tts, chunk_text_for_tts
from speech.asr_service import _preprocess_audio


class TestSpeechProcessing(unittest.TestCase):

    def test_clean_for_tts_removes_markdown_and_emojis(self):
        sample = "✨ **Carte NINA** : Rendez-vous au RAVEC pour obtenir votre NINA. Coût : 0 FCFA. 😉"
        cleaned = clean_for_tts(sample)
        self.assertNotIn("**", cleaned)
        self.assertNotIn("✨", cleaned)
        self.assertNotIn("😉", cleaned)
        self.assertIn("franc CFA", cleaned)
        self.assertIn("ravec", cleaned)

    def test_chunk_text_for_tts_splits_long_strings(self):
        long_text = (
            "La CNI biométrique est strictement gratuite pour la première délivrance au Mali. "
            "Les pièces à fournir comprennent l'acte de naissance ou jugement supplétif. "
            "Le certificat de résidence récent est également exigé par les autorités. "
            "Vous devez fournir deux photos d'identité sur fond blanc."
        )
        chunks = chunk_text_for_tts(long_text, max_chars=80)
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            self.assertLessEqual(len(c), 110)  # Marge acceptable sur les coupures de mots

    def test_audio_preprocessing_stereo_to_mono(self):
        stereo_data = np.ones((16000, 2), dtype=np.float32)
        proc_data, sr = _preprocess_audio(stereo_data, sample_rate=16000, target_sr=16000)
        self.assertEqual(proc_data.ndim, 1)
        self.assertEqual(len(proc_data), 16000)
        self.assertEqual(sr, 16000)

    def test_audio_preprocessing_resampling(self):
        audio_32k = np.zeros(32000, dtype=np.float32)
        proc_data, sr = _preprocess_audio(audio_32k, sample_rate=32000, target_sr=16000)
        self.assertEqual(sr, 16000)
        self.assertEqual(len(proc_data), 16000)


if __name__ == "__main__":
    unittest.main()
