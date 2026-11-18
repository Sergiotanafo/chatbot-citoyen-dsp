"""
Generated or fallback Python stubs for proto/dsp_service.proto.
Fournit les classes de messages Protobuf pour le service DSP.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TextRequest:
    text: str = ""
    language: str = ""
    session_id: str = ""

    def SerializeToString(self) -> bytes:
        import json
        return json.dumps({"text": self.text, "language": self.language, "session_id": self.session_id}).encode("utf-8")

    @classmethod
    def FromString(cls, data: bytes) -> "TextRequest":
        import json
        d = json.loads(data.decode("utf-8"))
        return cls(**d)


@dataclass
class Entity:
    entity: str = ""
    value: str = ""
    confidence: float = 0.0


@dataclass
class IntentResponse:
    intent: str = ""
    confidence: float = 0.0
    entities: List[Entity] = field(default_factory=list)
    text: str = ""

    def SerializeToString(self) -> bytes:
        import json
        return json.dumps({
            "intent": self.intent,
            "confidence": self.confidence,
            "entities": [{"entity": e.entity, "value": e.value, "confidence": e.confidence} for e in self.entities],
            "text": self.text,
        }).encode("utf-8")


@dataclass
class SearchRequest:
    query: str = ""
    language: str = ""
    top_k: int = 3


@dataclass
class SearchResultItem:
    topic: str = ""
    title: str = ""
    content: str = ""
    score: float = 0.0


@dataclass
class SearchResponse:
    results: List[SearchResultItem] = field(default_factory=list)


@dataclass
class AudioRequest:
    audio_data: bytes = b""
    format: str = "wav"
    language: str = "bm"


@dataclass
class TranscriptionResponse:
    text: str = ""
    detected_language: str = "bm"
    confidence: float = 0.0


@dataclass
class SynthesizeRequest:
    text: str = ""
    language: str = "bm"
    voice_speed: str = "normal"


@dataclass
class AudioResponse:
    audio_data: bytes = b""
    format: str = "wav"
