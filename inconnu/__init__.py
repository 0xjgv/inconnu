import hashlib
import time
from dataclasses import dataclass
from datetime import datetime

from inconnu.config import Config
from inconnu.nlp.entity_redactor import EntityRedactor


@dataclass
class ProcessedData:
    entity_map: dict[str, str]
    processing_time_ms: float
    redacted_text: str
    original_text: str
    text_length: int
    timestamp: str
    hashed_id: str


class Inconnu:
    __slots__ = ["entity_redactor", "deanonymize", "config"]

    def __init__(
        self,
        *,
        config: Config,
        language: str,
    ):
        self.entity_redactor = EntityRedactor(language=language)
        self.deanonymize = self.entity_redactor.deanonymize
        self.config = config

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    def __call__(self, *, text: str, deanonymize: bool = True) -> ProcessedData:
        start_time = time.time()
        if len(text) > self.config.max_text_length:
            raise ValueError(
                f"Text exceeds maximum length of {self.config.max_text_length}"
            )

        processed_data = ProcessedData(
            timestamp=datetime.now().isoformat(),
            hashed_id=self._hash_text(text),
            text_length=len(text),
            processing_time_ms=0,
            original_text=text,
            redacted_text="",
            entity_map={},
        )

        pseudonymized_text, entity_map = self.entity_redactor.redact(
            text=text, deanonymize=deanonymize
        )
        processed_data.redacted_text = pseudonymized_text
        processed_data.entity_map = entity_map

        end_time = time.time()
        processed_data.processing_time_ms = (end_time - start_time) * 1000
        print(f"Processing time: {processed_data.processing_time_ms:.2f} ms")
        return processed_data
