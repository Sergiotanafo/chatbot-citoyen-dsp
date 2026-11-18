"""
Service de synthèse vocale (Text-To-Speech / TTS).
Génère la voix en Bambara et en Français avec découpage de phrases et concaténation audio.
"""

import io
import logging
from typing import Optional, List
import numpy as np

from .text_cleaning import clean_for_tts, chunk_text_for_tts

logger = logging.getLogger(__name__)

TTS_MODEL_BAMBARA = "facebook/mms-tts-bam"
TTS_MODEL_FRENCH = "facebook/mms-tts-fra"

_tts_pipelines = {}


def _get_device() -> str:
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def get_tts_pipeline(language: str = "bm"):
    """Récupère ou initialise la pipeline TTS adaptée à la langue."""
    global _tts_pipelines
    model_name = TTS_MODEL_BAMBARA if language.lower() in ["bm", "bambara"] else TTS_MODEL_FRENCH

    if model_name not in _tts_pipelines:
        try:
            from transformers import pipeline
            device = _get_device()
            logger.info(f"[TTS] Chargement du modèle TTS '{model_name}' sur {device}...")
            _tts_pipelines[model_name] = pipeline("text-to-speech", model=model_name, device=device)
        except Exception as e:
            logger.warning(f"[TTS] Impossible de charger le modèle TTS '{model_name}': {e}")
            return None

    return _tts_pipelines.get(model_name)


def synthesize_text_to_wav(text: str, language: str = "bm") -> bytes:
    """Synthétise un texte en audio WAV avec découpage adaptatif pour éviter
    la saturation mémoire sur les réponses longues.
    """
    if not text or not text.strip():
        return b""

    try:
        import soundfile as sf
    except ImportError:
        logger.error("[TTS] Le module 'soundfile' est requis pour l'encodage audio WAV.")
        return b""

    # Découpage du texte en segments de taille contrôlée (max 150 caractères)
    chunks = chunk_text_for_tts(text, max_chars=150)
    if not chunks:
        return b""

    pipe = get_tts_pipeline(language)
    if pipe is None:
        logger.warning("[TTS] Pipeline TTS non disponible.")
        return b""

    audio_segments = []
    final_sr = 16000

    for chunk in chunks:
        try:
            output = pipe(chunk)
            final_sr = output.get("sampling_rate", 16000)
            audio_arr = output.get("audio")
            if audio_arr is not None:
                # Normalisation en 1D float32
                if isinstance(audio_arr, np.ndarray):
                    audio_flat = audio_arr.flatten().astype(np.float32)
                else:
                    audio_flat = np.array(audio_arr, dtype=np.float32).flatten()
                audio_segments.append(audio_flat)
                # Insertion d'un court silence de 150 ms entre les phrases
                silence_len = int(final_sr * 0.15)
                audio_segments.append(np.zeros(silence_len, dtype=np.float32))
        except Exception as e:
            logger.error(f"[TTS] Échec sur le segment '{chunk}': {e}")

    if not audio_segments:
        return b""

    # Concaténation de tous les segments
    full_audio = np.concatenate(audio_segments)

    # Écriture dans un buffer WAV en mémoire
    wav_io = io.BytesIO()
    sf.write(wav_io, full_audio, final_sr, format="WAV")
    return wav_io.getvalue()
