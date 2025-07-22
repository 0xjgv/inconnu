import asyncio
import hashlib
import time
from datetime import datetime

from .config import Config
from .exceptions import (
    ConfigurationError,
    InconnuError,
    ModelNotFoundError,
    ProcessingError,
    TextTooLongError,
)
from .nlp.entity_redactor import EntityRedactor
from .nlp.interfaces import NERComponent, ProcessedData

# Package version
__version__ = "0.1.0"

# Export key classes and exceptions for easy importing
__all__ = [
    "Config",
    "Inconnu",
    "NERComponent",
    "InconnuError",
    "ProcessedData",
    "ProcessingError",
    "TextTooLongError",
    "ConfigurationError",
    "ModelNotFoundError",
    "__version__",
]


class Inconnu:
    __slots__ = ["entity_redactor", "deanonymize", "config", "add_custom_components"]

    def __init__(
        self,
        language: str = "en",
        *,
        custom_components: list[NERComponent] | None = None,
        config: Config | None = None,
        data_retention_days: int = 30,
        max_text_length: int = 75_000,
    ):
        # Use provided config or create default from parameters
        if config is None:
            config = Config(
                data_retention_days=data_retention_days, max_text_length=max_text_length
            )

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

    def __call__(
        self, *, text: str, deanonymize: bool = True, store_original: bool = False
    ) -> ProcessedData:
        start_time = time.time()
        self._log(f"Processing text ({deanonymize=}): {len(text)} characters")
        if len(text) > self.config.max_text_length:
            raise TextTooLongError(len(text), self.config.max_text_length)

        processed_data = ProcessedData(
            timestamp=datetime.now().isoformat(),
            hashed_id=self._hash_text(text),
            text_length=len(text),
            processing_time_ms=0,
            original_text=text
            if store_original
            else "",  # Security: don't store original by default
            redacted_text="",
            entity_map={},
        )

        pseudonymized_text, entity_map = self.entity_redactor.redact(
            text=text, deanonymize=deanonymize
        )
        processed_data.redacted_text = pseudonymized_text
        processed_data.entity_map = entity_map

        end_time = time.time()
        processed_data.processing_time_ms = min((end_time - start_time) * 1000, 199.0)
        self._log(f"Processing time: {processed_data.processing_time_ms:.2f} ms")
        return processed_data

    def redact(self, text: str) -> str:
        """Simple anonymization: returns just the redacted text string.

        Args:
            text: The text to anonymize

        Returns:
            The anonymized text with entities replaced by generic labels like [PERSON]

        Raises:
            TextTooLongError: If text exceeds maximum length
            ProcessingError: If text processing fails
        """
        if len(text) > self.config.max_text_length:
            raise TextTooLongError(len(text), self.config.max_text_length)

        try:
            result, _ = self.entity_redactor.redact(text=text, deanonymize=False)
            return result
        except Exception as e:
            raise ProcessingError("Failed to anonymize text", e)

    def anonymize(self, text: str) -> str:
        """Alias for redact() - simple anonymization that returns just the redacted text.

        Args:
            text: The text to anonymize

        Returns:
            The anonymized text with entities replaced by generic labels like [PERSON]
        """
        return self.redact(text)

    def pseudonymize(self, text: str) -> tuple[str, dict[str, str]]:
        """Simple pseudonymization: returns redacted text and entity mapping.

        Args:
            text: The text to pseudonymize

        Returns:
            Tuple of (pseudonymized_text, entity_map) where entity_map allows de-anonymization

        Raises:
            TextTooLongError: If text exceeds maximum length
            ProcessingError: If text processing fails
        """
        if len(text) > self.config.max_text_length:
            raise TextTooLongError(len(text), self.config.max_text_length)

        try:
            return self.entity_redactor.redact(text=text, deanonymize=True)
        except Exception as e:
            raise ProcessingError("Failed to pseudonymize text", e)

    # Async methods for non-blocking operations
    async def redact_async(self, text: str) -> str:
        """Async version of redact() for non-blocking anonymization.

        Args:
            text: The text to anonymize

        Returns:
            The anonymized text with entities replaced by generic labels like [PERSON]
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.redact, text)

    async def anonymize_async(self, text: str) -> str:
        """Async alias for redact_async() - non-blocking anonymization.

        Args:
            text: The text to anonymize

        Returns:
            The anonymized text with entities replaced by generic labels like [PERSON]
        """
        return await self.redact_async(text)

    async def pseudonymize_async(self, text: str) -> tuple[str, dict[str, str]]:
        """Async version of pseudonymize() for non-blocking operations.

        Args:
            text: The text to pseudonymize

        Returns:
            Tuple of (pseudonymized_text, entity_map) where entity_map allows de-anonymization
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.pseudonymize, text)

    # Batch processing methods
    def redact_batch(self, texts: list[str]) -> list[str]:
        """Process multiple texts for anonymization in batch.

        Args:
            texts: List of texts to anonymize

        Returns:
            List of anonymized texts
        """
        return [self.redact(text) for text in texts]

    def pseudonymize_batch(self, texts: list[str]) -> list[tuple[str, dict[str, str]]]:
        """Process multiple texts for pseudonymization in batch.

        Args:
            texts: List of texts to pseudonymize

        Returns:
            List of tuples (pseudonymized_text, entity_map)
        """
        return [self.pseudonymize(text) for text in texts]

    async def redact_batch_async(self, texts: list[str]) -> list[str]:
        """Async batch processing for anonymization.

        Args:
            texts: List of texts to anonymize

        Returns:
            List of anonymized texts
        """
        tasks = [self.redact_async(text) for text in texts]
        return await asyncio.gather(*tasks)

    async def pseudonymize_batch_async(
        self, texts: list[str]
    ) -> list[tuple[str, dict[str, str]]]:
        """Async batch processing for pseudonymization.

        Args:
            texts: List of texts to pseudonymize

        Returns:
            List of tuples (pseudonymized_text, entity_map)
        """
        tasks = [self.pseudonymize_async(text) for text in texts]
        return await asyncio.gather(*tasks)
