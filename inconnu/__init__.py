import hashlib
import time
from datetime import datetime

from .config import Config
from .nlp.entity_redactor import EntityRedactor
from .nlp.interfaces import NERComponent, ProcessedData


class Inconnu:
    __slots__ = ["entity_redactor", "deanonymize", "config", "add_custom_components"]

    def __init__(
        self,
        *,
        custom_components: list[NERComponent] | None = None,
        config: Config,
        language: str,
    ):
        self.entity_redactor = EntityRedactor(
            custom_components=custom_components,
            language=language,
        )
        self.add_custom_components = self.entity_redactor.add_custom_components
        self.deanonymize = self.entity_redactor.deanonymize
        self.config = config

    def _log(self, *args, **kwargs):
        print(*args, **kwargs)

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    def __call__(self, *, text: str, deanonymize: bool = True) -> ProcessedData:
        start_time = time.time()
        self._log(f"Processing text ({deanonymize=}): {len(text)} characters")
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
        self._log(f"Processing time: {processed_data.processing_time_ms:.2f} ms")
        return processed_data
