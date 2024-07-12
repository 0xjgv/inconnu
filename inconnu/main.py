import hashlib
import time
from dataclasses import dataclass
from datetime import datetime

from inconnu.config import Config
from inconnu.nlp.anonymizer import EntityAnonymizer


@dataclass
class ProcessedData:
    entity_map: dict[str, str]
    processing_time_ms: float
    anonymized_text: str
    text_length: int
    anonymized: bool
    timestamp: str
    hashed_id: str
    text: str


class Inconnu:
    __slots__ = ["anonymizer", "config"]

    def __init__(self, *, config: Config, anonymizer: EntityAnonymizer):
        self.anonymizer = anonymizer
        self.config = config

    def process_data(self, *, text: str) -> ProcessedData:
        start_time = time.time()
        if len(text) > self.config.max_text_length:
            raise ValueError(
                f"Text exceeds maximum length of {self.config.max_text_length}"
            )

        processed_data = ProcessedData(
            timestamp=datetime.now().isoformat(),
            hashed_id=self.hash_text(text),
            text_length=len(text),
            processing_time_ms=0,
            anonymized_text=text,
            anonymized=False,
            entity_map={},
            text=text,
        )

        if self.config.anonymize_entities:
            anonymized_text, entity_map = self.anonymizer.anonymize(text)
            processed_data.anonymized_text = anonymized_text
            processed_data.entity_map = entity_map
            processed_data.anonymized = True

        end_time = time.time()
        processed_data.processing_time_ms = (end_time - start_time) * 1000
        print(f"Processing time: {processed_data.processing_time_ms:.2f} ms")
        return processed_data

    def hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()
