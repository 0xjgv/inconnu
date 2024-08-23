import time
from datetime import datetime

from inconnu.config import Config
from inconnu.interfaces import InconnuBase, ProcessedData
from inconnu.nlp.anonymizer import EntityAnonymizer
from inconnu.nlp.pseudonymizer import EntityPseudonymizer


class InconnuAnonymizer(InconnuBase):
    __slots__ = ["anonymizer", "config"]

    def __init__(self, *, config: Config):
        self.anonymizer = EntityAnonymizer(language=config.language)
        self.config = config

    def __call__(self, *, text: str) -> ProcessedData:
        if len(text) > self.config.max_text_length:
            raise ValueError(
                f"Text exceeds maximum length of {self.config.max_text_length}"
            )
        start_time = time.time()

        processed_data = ProcessedData(
            timestamp=datetime.now().isoformat(),
            hashed_id=self._hash_text(text),
            text_length=len(text),
            processing_time_ms=0,
            text=text,
        )

        processed_data.anonymized_text = self.anonymizer(text)

        end_time = time.time()
        processed_data.processing_time_ms = (end_time - start_time) * 1000
        self._log(f"Processing time: {processed_data.processing_time_ms:.2f} ms")
        return processed_data


class InconnuPseudonymizer(InconnuBase):
    __slots__ = ["pseudonymizer", "config"]

    def __init__(self, *, config: Config):
        self.pseudonymizer = EntityPseudonymizer(language=config.language)
        self.config = config

    def __call__(self, *, text: str) -> ProcessedData:
        if len(text) > self.config.max_text_length:
            raise ValueError(
                f"Text exceeds maximum length of {self.config.max_text_length}"
            )
        start_time = time.time()

        processed_data = ProcessedData(
            timestamp=datetime.now().isoformat(),
            hashed_id=self._hash_text(text),
            text_length=len(text),
            processing_time_ms=0,
            text=text,
        )

        pseudonymized_text, entity_map = self.pseudonymizer(text)
        processed_data.pseudonymized_text = pseudonymized_text
        processed_data.entity_map = entity_map

        end_time = time.time()
        processed_data.processing_time_ms = (end_time - start_time) * 1000
        self._log(f"Processing time: {processed_data.processing_time_ms:.2f} ms")
        return processed_data

    def deanonymize(self, *, text: str, entity_map: dict) -> str:
        return self.pseudonymizer.deanonymize(text=text, entity_map=entity_map)
