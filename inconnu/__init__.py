import hashlib
import time
from dataclasses import dataclass
from datetime import datetime

from inconnu.config import Config
from inconnu.nlp.pseudonymizer import EntityPseudonymizer


@dataclass
class ProcessedData:
    entity_map: dict[str, str]
    processing_time_ms: float
    pseudonymized_text: str
    pseudonymized: bool
    text_length: int
    timestamp: str
    hashed_id: str
    text: str


class Inconnu:
    __slots__ = ["pseudonymizer", "config"]

    def __init__(self, *, config: Config, pseudonymizer: EntityPseudonymizer):
        self.pseudonymizer = pseudonymizer
        self.config = config

    def process_data(self, *, text: str, language: str = "en") -> ProcessedData:
        start_time = time.time()
        if len(text) > self.config.max_text_length:
            raise ValueError(
                f"Text exceeds maximum length of {self.config.max_text_length}"
            )

        processed_data = ProcessedData(
            timestamp=datetime.now().isoformat(),
            hashed_id=self.hash_text(text),
            text_length=len(text),
            pseudonymized_text="",
            processing_time_ms=0,
            pseudonymized=False,
            entity_map={},
            text=text,
        )

        if self.config.pseudonymize_entities:
            pseudonymized_text, entity_map = self.pseudonymizer(text)
            processed_data.pseudonymized_text = pseudonymized_text
            processed_data.entity_map = entity_map
            processed_data.pseudonymized = True

        end_time = time.time()
        processed_data.processing_time_ms = (end_time - start_time) * 1000
        print(f"Processing time: {processed_data.processing_time_ms:.2f} ms")
        return processed_data

    def hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()
