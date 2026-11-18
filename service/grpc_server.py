"""
DSP gRPC Service — Point d'entrée autonome de la Data Science Platform (DSP).
Expose les capacités IA (NLU Rasa, Recherche vectorielle dense, RAG Mistral, ASR, TTS) au Backend FastAPI.
"""

import logging
import os
import sys
import time
from concurrent import futures
from typing import Any, Dict, List, Optional

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [DSP] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("dsp_server")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Imports des briques DSP
from intelligence.router import get_hybrid_router
from intelligence.vector_store import get_vector_store
from actions.actions import detect_language
from speech.asr_service import transcribe_audio_bytes
from speech.tts_service import synthesize_text_to_wav

# Tentative d'import des stubs gRPC compilés
try:
    import grpc
    from service import dsp_service_pb2, dsp_service_pb2_grpc
    GRPC_AVAILABLE = True
except ImportError:
    try:
        import grpc
        import dsp_service_pb2
        import dsp_service_pb2_grpc
        GRPC_AVAILABLE = True
    except ImportError:
        GRPC_AVAILABLE = False
        grpc = None
        dsp_service_pb2 = None
        dsp_service_pb2_grpc = None


class DspServiceServicerImpl:
    """Implémentation du contrat DspService combinant Router conversationnel et RAG."""

    def __init__(self):
        self.router = get_hybrid_router()
        self.vector_store = get_vector_store()
        logger.info("[DSP] Servicer hybride (Rasa Dialogue + RAG Mistral) initialisé.")

    def PredictIntent(self, request, context=None):
        """Compréhension et réponse unifiée : traite la demande via le routeur hybride."""
        text = request.text.strip() if request.text else ""
        lang = request.language or detect_language(text)
        session_id = request.session_id or "default"

        logger.info(f"[PredictIntent] text='{text}' | lang='{lang}' | session='{session_id}'")

        # Traitement via l'architecture hybride
        slots = {"langue": lang, "demarche": None}
        result = self.router.process_message(text=text, current_slots=slots)

        intent_name = result.get("intent", "nlu_fallback")
        confidence = float(result.get("confidence", 0.5))
        bot_reply = result.get("answer", "")

        entities_list = []

        if dsp_service_pb2:
            return dsp_service_pb2.IntentResponse(
                intent=intent_name,
                confidence=confidence,
                entities=[],
                text=bot_reply,
            )

        return {
            "intent": intent_name,
            "confidence": confidence,
            "entities": entities_list,
            "text": bot_reply,
        }

    def SearchKnowledge(self, request, context=None):
        """Recherche documentaire vectorielle dans les démarches administratives."""
        query = request.query.strip() if request.query else ""
        lang = request.language or detect_language(query)
        top_k = request.top_k if request.top_k > 0 else 3

        logger.info(f"[SearchKnowledge] query='{query}' | lang='{lang}' | top_k={top_k}")
        chunks = self.vector_store.similarity_search(query=query, language=lang, top_k=top_k)

        if dsp_service_pb2:
            results_proto = [
                dsp_service_pb2.SearchResultItem(
                    topic=c.topic,
                    title=c.title,
                    content=c.content,
                    score=float(c.score),
                )
                for c in chunks
            ]
            return dsp_service_pb2.SearchResponse(results=results_proto)

        return {
            "results": [
                {
                    "topic": c.topic,
                    "title": c.title,
                    "content": c.content,
                    "score": c.score,
                }
                for c in chunks
            ]
        }

    def TranscribeAudio(self, request, context=None):
        """Reconnaissance vocale (ASR) : Audio -> Texte."""
        audio_data = request.audio_data
        lang = request.language or "bm"

        logger.info(f"[TranscribeAudio] taille={len(audio_data)} octets | format='{request.format}' | lang='{lang}'")
        text = transcribe_audio_bytes(audio_bytes=audio_data, language=lang)

        if dsp_service_pb2:
            return dsp_service_pb2.TranscriptionResponse(
                text=text,
                detected_language=lang,
                confidence=0.90 if text and not text.startswith("[") else 0.0,
            )

        return {"text": text, "detected_language": lang, "confidence": 0.90}

    def SynthesizeSpeech(self, request, context=None):
        """Synthèse vocale (TTS) : Texte -> Audio WAV."""
        text = request.text
        lang = request.language or detect_language(text)

        logger.info(f"[SynthesizeSpeech] texte='{text[:40]}...' | lang='{lang}'")
        audio_wav = synthesize_text_to_wav(text=text, language=lang)

        if dsp_service_pb2:
            return dsp_service_pb2.AudioResponse(
                audio_data=audio_wav,
                format="wav",
            )

        return {"audio_data": audio_wav, "format": "wav"}


def serve(port: int = 50051):
    """Démarre le serveur gRPC DSP."""
    if not GRPC_AVAILABLE or not dsp_service_pb2_grpc:
        logger.error(
            "Les stubs gRPC ne sont pas disponibles.\n"
            "Veuillez générer les stubs via :\n"
            "  scripts\\generate_proto.bat"
        )
        return

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    servicer = DspServiceServicerImpl()
    dsp_service_pb2_grpc.add_DspServiceServicer_to_server(servicer, server)

    server_address = f"[::]:{port}"
    server.add_insecure_port(server_address)
    server.start()
    logger.info(f"Serveur DSP gRPC démarré avec succès et à l'écoute sur le port {port}.")

    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        logger.info("Arrêt du serveur DSP demandé...")
        server.stop(0)


if __name__ == "__main__":
    port_env = int(os.environ.get("DSP_PORT", 50051))
    serve(port=port_env)
