import hashlib
import time
from dataclasses import dataclass
from datetime import datetime

from inconnu.config import Config
from inconnu.nlp.anonymizer import EntityAnonymizer
from inconnu.nlp.pseudonymizer import EntityPseudonymizer


@dataclass
class ProcessedData:
    entity_map: dict[str, str]
    processing_time_ms: float
    pseudonymized_text: str
    anonymized_text: str
    text_length: int
    timestamp: str
    hashed_id: str
    text: str


class Inconnu:
    __slots__ = ["pseudonymizer", "anonymizer", "config"]

    def __init__(self, *, config: Config):
        self.pseudonymizer = EntityPseudonymizer(language=config.language)
        self.anonymizer = EntityAnonymizer(language=config.language)
        self.config = config

    def _log(self, *args, **kwargs):
        print(*args, **kwargs)

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    def _prepare_process_data(self, *, text: str) -> ProcessedData:
        if len(text) > self.config.max_text_length:
            raise ValueError(
                f"Text exceeds maximum length of {self.config.max_text_length}"
            )

        return ProcessedData(
            timestamp=datetime.now().isoformat(),
            hashed_id=self._hash_text(text),
            text_length=len(text),
            pseudonymized_text="",
            processing_time_ms=0,
            anonymized_text="",
            entity_map={},
            text=text,
        )

    def _finalize_process_data(
        self, processed_data: ProcessedData, start_time: float
    ) -> ProcessedData:
        end_time = time.time()
        processed_data.processing_time_ms = (end_time - start_time) * 1000
        self._log(f"Processing time: {processed_data.processing_time_ms:.2f} ms")
        return processed_data

    def pseudonymize(self, *, text: str) -> ProcessedData:
        if not self.pseudonymizer:
            raise ValueError("Pseudonymizer not provided")

        start_time = time.time()
        pseudonymized_text, entity_map = self.pseudonymizer(text)
        processed_data = self._prepare_process_data(text=text)
        processed_data.pseudonymized_text = pseudonymized_text
        processed_data.entity_map = entity_map

        return self._finalize_process_data(processed_data, start_time)

    def anonymize(self, *, text: str) -> ProcessedData:
        if not self.anonymizer:
            raise ValueError("Anonymizer not provided")

        start_time = time.time()
        processed_data = self._prepare_process_data(text=text)
        processed_data.anonymized_text = self.anonymizer(text)

        return self._finalize_process_data(processed_data, start_time)
