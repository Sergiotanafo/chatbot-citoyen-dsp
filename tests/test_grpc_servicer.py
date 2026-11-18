"""
Tests unitaires pour l'implémentation du service gRPC DSP (DspServiceServicerImpl).
"""

import unittest
from service.grpc_server import DspServiceServicerImpl


class MockRequest:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestGrpcServicer(unittest.TestCase):

    def setUp(self):
        self.servicer = DspServiceServicerImpl()

    def test_predict_intent_fallback_to_faq(self):
        req = MockRequest(
            text="Comment faire pour avoir un passeport au Mali ?",
            language="fr",
            session_id="session-unit-test",
        )
        res = self.servicer.PredictIntent(req)
        # Que le retour soit un dict ou un objet protobuf
        intent = res.intent if hasattr(res, "intent") else res["intent"]
        confidence = res.confidence if hasattr(res, "confidence") else res["confidence"]
        self.assertEqual(intent, "demande_passeport")
        self.assertGreater(confidence, 0.0)

    def test_search_knowledge_returns_results(self):
        req = MockRequest(
            query="Où faire ma carte d'identité ?",
            language="fr",
            top_k=2,
        )
        res = self.servicer.SearchKnowledge(req)
        results = res.results if hasattr(res, "results") else res["results"]
        self.assertGreater(len(results), 0)

    def test_transcribe_audio_empty_bytes(self):
        req = MockRequest(
            audio_data=b"",
            format="wav",
            language="bm",
        )
        res = self.servicer.TranscribeAudio(req)
        text = res.text if hasattr(res, "text") else res["text"]
        self.assertEqual(text, "")

    def test_synthesize_speech_empty_text(self):
        req = MockRequest(
            text="",
            language="fr",
            voice_speed="normal",
        )
        res = self.servicer.SynthesizeSpeech(req)
        audio_data = res.audio_data if hasattr(res, "audio_data") else res["audio_data"]
        self.assertEqual(len(audio_data), 0)


if __name__ == "__main__":
    unittest.main()
