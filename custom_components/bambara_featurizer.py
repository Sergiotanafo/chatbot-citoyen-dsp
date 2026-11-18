import logging
import os
from typing import Any, Dict, List, Optional, Text, Type
import numpy as np

from rasa.engine.graph import GraphComponent, ExecutionContext
from rasa.engine.recipes.default_recipe import DefaultV1Recipe
from rasa.engine.storage.resource import Resource
from rasa.engine.storage.storage import ModelStorage
from rasa.shared.nlu.training_data.message import Message
from rasa.shared.nlu.training_data.training_data import TrainingData
from rasa.shared.nlu.constants import (
    TEXT,
    RESPONSE,
    ACTION_TEXT,
    FEATURE_TYPE_SEQUENCE,
    FEATURE_TYPE_SENTENCE,
)
from rasa.shared.nlu.training_data.features import Features
from rasa.nlu.featurizers.featurizer import Featurizer

# Attributs featurizables (= attributs textuels d'un message)
DENSE_FEATURIZABLE_ATTRIBUTES = [TEXT, RESPONSE, ACTION_TEXT]

logger = logging.getLogger(__name__)


@DefaultV1Recipe.register(
    [DefaultV1Recipe.ComponentType.MESSAGE_FEATURIZER],
    is_trainable=False,
)
class BambaraEmbeddingFeaturizer(Featurizer[Any], GraphComponent):
    """Featurizer personnalisé pour les embeddings Bambara (.vec).
    Compatible Rasa 3.6 — utilise l'API Features / add_features.
    Ne nécessite pas l'installation de la librairie C++ FastText.
    """

    # ── Méthodes de cycle de vie GraphComponent ──────────────────────────

    @classmethod
    def required_components(cls) -> List[Type]:
        return []

    @staticmethod
    def get_default_config() -> Dict[Text, Any]:
        return {
            # Chemin local vers le fichier .vec ; si absent → téléchargement HF
            "model_path": None,
            # Alias utilisé comme origine dans l'objet Features
            "alias": "BambaraEmbeddingFeaturizer",
        }

    @classmethod
    def validate_config(cls, config: Dict[Text, Any]) -> None:
        """Rasa 3.6 exige cette méthode même si aucune validation n'est faite."""
        pass

    def __init__(
        self,
        config: Dict[Text, Any],
        name: Text,
        model_storage: ModelStorage,
        resource: Resource,
    ) -> None:
        self._config = {**self.get_default_config(), **config}
        self._name = name
        self.model_path = self._config.get("model_path")
        self.word_vectors: Dict[str, np.ndarray] = {}
        self.dim = 300
        self._load_model()

    # Implémentation requise par Featurizer (ABC)
    @staticmethod
    def required_packages() -> List[Text]:
        return []

    @classmethod
    def create(
        cls,
        config: Dict[Text, Any],
        model_storage: ModelStorage,
        resource: Resource,
        execution_context: ExecutionContext,
    ) -> "BambaraEmbeddingFeaturizer":
        return cls(config, execution_context.node_name, model_storage, resource)

    # ── Chargement du modèle .vec ─────────────────────────────────────────

    def _load_model(self) -> None:
        """Charge le fichier .vec depuis le disque ou HuggingFace Hub."""
        local_candidates = [
            self.model_path,
            os.environ.get("BAMBARA_EMBEDDINGS_PATH"),
            os.path.join(os.getcwd(), "models", "bambara_embeddings.vec"),
            os.path.join(os.getcwd(), "custom_components", "bambara_embeddings.vec"),
        ]
        for cand in local_candidates:
            if cand and os.path.exists(cand):
                self.model_path = cand
                break

        if not self.model_path or not os.path.exists(self.model_path):
            logger.info(
                "Modèle Bambara local introuvable. "
                "Tentative de téléchargement depuis MALIBA-AI/bambara-embeddings…"
            )
            try:
                from huggingface_hub import hf_hub_download
                self.model_path = hf_hub_download(
                    repo_id="MALIBA-AI/bambara-embeddings",
                    filename="bambara_embeddings.vec",
                )
            except ImportError:
                logger.warning(
                    "huggingface_hub absent. "
                    "Pour télécharger les embeddings Bambara : pip install huggingface_hub"
                )
                return
            except Exception as exc:
                logger.warning(f"Téléchargement HuggingFace ignoré ou échoué : {exc}")
                return

        logger.info(
            f"Chargement des embeddings Bambara depuis {self.model_path}…"
        )
        try:
            with open(self.model_path, "r", encoding="utf-8") as fh:
                for i, line in enumerate(fh):
                    parts = line.rstrip().split(" ")
                    # Première ligne = « vocab_size dimension »
                    if i == 0 and len(parts) == 2:
                        try:
                            self.dim = int(parts[1])
                        except ValueError:
                            pass
                        continue
                    word = parts[0]
                    try:
                        vector = np.array(
                            [float(x) for x in parts[-self.dim :]], dtype=np.float32
                        )
                        self.word_vectors[word] = vector
                    except ValueError:
                        pass  # Ligne mal formée → ignorée
            logger.info(
                f"Embeddings Bambara chargés : "
                f"{len(self.word_vectors)} mots (dim={self.dim})."
            )
        except Exception as exc:
            logger.error(f"Lecture .vec échouée : {exc}")

    # ── Featurization ─────────────────────────────────────────────────────

    def process_training_data(self, training_data: TrainingData) -> TrainingData:
        self.process(training_data.training_examples)
        return training_data

    def process(self, messages: List[Message]) -> List[Message]:
        for message in messages:
            for attribute in DENSE_FEATURIZABLE_ATTRIBUTES:
                self._set_features(message, attribute)
        return messages

    def _set_features(self, message: Message, attribute: Text) -> None:
        text = message.get(attribute)
        if not text:
            return

        tokens = message.get("tokens")
        if not tokens:
            return

        token_texts = [t.text for t in tokens]
        word_features = np.zeros((len(token_texts), self.dim), dtype=np.float32)

        valid_words = 0
        if self.word_vectors:
            for i, word in enumerate(token_texts):
                vec = self.word_vectors.get(word) or self.word_vectors.get(word.lower())
                if vec is not None:
                    word_features[i] = vec
                    valid_words += 1

        # Mean Pooling → embedding de phrase
        if valid_words > 0:
            sentence_vec = np.sum(word_features, axis=0) / valid_words
        else:
            sentence_vec = np.zeros(self.dim, dtype=np.float32)
        sentence_feature = sentence_vec.reshape(1, self.dim)

        origin = self._config.get("alias", self.__class__.__name__)

        message.add_features(
            Features(
                word_features,
                FEATURE_TYPE_SEQUENCE,
                attribute,
                origin,
            )
        )
        message.add_features(
            Features(
                sentence_feature,
                FEATURE_TYPE_SENTENCE,
                attribute,
                origin,
            )
        )
