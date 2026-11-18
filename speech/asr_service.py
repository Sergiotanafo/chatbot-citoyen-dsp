"""
Service de reconnaissance automatique de la parole (ASR / STT).
Prend en charge la transcription bilingue (Bambara & Français).
"""

import io
import logging
from typing import Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)

ASR_MODEL_BAMBARA = "Panga-Azazia/bambara-asr"
ASR_MODEL_FRENCH = "openai/whisper-tiny"

_asr_pipelines = {}


def _get_device() -> str:
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def get_asr_pipeline(language: str = "bm"):
    """Récupère ou initialise la pipeline ASR adaptée à la langue."""
    global _asr_pipelines
    model_name = ASR_MODEL_BAMBARA if language.lower() in ["bm", "bambara"] else ASR_MODEL_FRENCH

    if model_name not in _asr_pipelines:
        try:
            from transformers import pipeline
            device = _get_device()
            logger.info(f"[ASR] Chargement du modèle ASR '{model_name}' sur {device}...")
            _asr_pipelines[model_name] = pipeline(
                "automatic-speech-recognition",
                model=model_name,
                device=device,
            )
        except Exception as e:
            logger.warning(f"[ASR] Impossible de charger le modèle '{model_name}': {e}")
            return None

    return _asr_pipelines.get(model_name)


def _preprocess_audio(audio_data: np.ndarray, sample_rate: int, target_sr: int = 16000) -> Tuple[np.ndarray, int]:
    """Convertit l'audio en mono et rééchantillonne à 16 000 Hz si nécessaire."""
    # Conversion stéréo vers mono
    if audio_data.ndim > 1:
        audio_data = np.mean(audio_data, axis=1)

    # Normalisation float32 entre -1.0 et 1.0
    if audio_data.dtype != np.float32:
        audio_data = audio_data.astype(np.float32)

    # Rééchantillonnage simple si la fréquence diffère
    if sample_rate != target_sr and len(audio_data) > 0:
        new_length = int(len(audio_data) * target_sr / sample_rate)
        indices = np.linspace(0, len(audio_data) - 1, new_length)
        audio_data = np.interp(indices, np.arange(len(audio_data)), audio_data).astype(np.float32)
        sample_rate = target_sr

    return audio_data, sample_rate


def transcribe_audio_bytes(audio_bytes: bytes, language: str = "bm") -> str:
    """Transcrit un flux d'octets audio (WAV, MP3, OGG) en texte."""
    if not audio_bytes:
        return ""

    try:
        import soundfile as sf
    except ImportError:
        logger.error("[ASR] Le module 'soundfile' est requis pour le décodage audio.")
        return "[Erreur: soundfile manquant]"

    try:
        audio_file = io.BytesIO(audio_bytes)
        audio_data, sample_rate = sf.read(audio_file)
    except Exception as e:
        logger.error(f"[ASR] Échec de lecture des octets audio : {e}")
        return "[Erreur: format audio invalide]"

    # Prétraitement standardisé vers 16 kHz mono
    audio_data, sample_rate = _preprocess_audio(audio_data, sample_rate, target_sr=16000)

    pipe = get_asr_pipeline(language)
    if pipe is None:
        return "[ASR non disponible localement : dépendances ou poids non installés]"

    try:
        result = pipe({"sampling_rate": sample_rate, "raw": audio_data})
        return result.get("text", "").strip()
    except Exception as e:
        logger.error(f"[ASR] Erreur lors de l'inférence : {e}")
        return f"[Erreur transcription: {e}]"
