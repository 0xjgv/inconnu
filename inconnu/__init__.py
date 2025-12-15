import asyncio
import hashlib
import logging
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
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

logger = logging.getLogger(__name__)

# Package version
__version__ = "0.1.1"

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
    __slots__ = [
        "entity_redactor",
        "deanonymize",
        "restore",
        "config",
        "add_custom_components",
        "_executor",
        "_chunk_size",
    ]

    def __init__(
        self,
        language: str = "en",
        *,
        custom_components: list[NERComponent] | None = None,
        config: Config | None = None,
        data_retention_days: int = 30,
        max_text_length: int = 75_000,
        executor: ThreadPoolExecutor | None = None,
        chunk_size: int = 100,
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
        self.restore = self.entity_redactor.restore
        self.deanonymize = self.entity_redactor.deanonymize
        self.config = config
        self._executor = executor
        self._chunk_size = chunk_size

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    def _validate_input(self, text: str, strict: bool = False) -> None:
        """Validate input text before processing.

        Args:
            text: Text to validate
            strict: If True, apply stricter validation rules

        Raises:
            TextTooLongError: If text exceeds maximum length
            ValueError: If text is invalid
        """
        if len(text) > self.config.max_text_length:
            raise TextTooLongError(len(text), self.config.max_text_length)

        if strict:
            # Check for valid encoding
            try:
                text.encode("utf-8")
            except UnicodeEncodeError as e:
                raise ValueError(f"Text contains invalid unicode characters: {e}")

            # Warn about empty or whitespace-only text
            if not text.strip():
                warnings.warn("Processing empty or whitespace-only text", UserWarning)

    def __call__(
        self, *, text: str, deanonymize: bool = True, store_original: bool = False
    ) -> ProcessedData:
        start_time = time.time()
        logger.info(f"Processing text ({deanonymize=}): {len(text)} characters")
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
        processed_data.processing_time_ms = (end_time - start_time) * 1000
        logger.debug(f"Processing time: {processed_data.processing_time_ms:.2f} ms")
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

    # Batch processing methods
    def redact_batch(
        self, texts: list[str], chunk_size: int | None = None
    ) -> list[str]:
        """Process multiple texts for anonymization in batch.

        For large batches, processes texts in chunks to manage memory usage efficiently.

        Args:
            texts: List of texts to anonymize
            chunk_size: Number of texts to process at once (defaults to self._chunk_size)

        Returns:
            List of anonymized texts
        """
        chunk_size = chunk_size or self._chunk_size
        results = []

        # Process in chunks for memory efficiency
        for i in range(0, len(texts), chunk_size):
            chunk = texts[i : i + chunk_size]
            try:
                # Validate all texts in chunk
                for text in chunk:
                    self._validate_input(text)

                # Process chunk
                chunk_results = [self.redact(text) for text in chunk]
                results.extend(chunk_results)

                # Log progress for large batches
                if len(texts) > chunk_size * 2:
                    logger.info(
                        f"Processed {min(i + chunk_size, len(texts))}/{len(texts)} texts"
                    )

            except Exception as e:
                # Log which chunk failed
                logger.error(f"Failed processing chunk {i // chunk_size + 1}: {e}")
                raise

        return results

    def pseudonymize_batch(
        self, texts: list[str], chunk_size: int | None = None
    ) -> list[tuple[str, dict[str, str]]]:
        """Process multiple texts for pseudonymization in batch.

        For large batches, processes texts in chunks to manage memory usage efficiently.

        Args:
            texts: List of texts to pseudonymize
            chunk_size: Number of texts to process at once (defaults to self._chunk_size)

        Returns:
            List of tuples (pseudonymized_text, entity_map)
        """
        chunk_size = chunk_size or self._chunk_size
        results = []

        # Process in chunks for memory efficiency
        for i in range(0, len(texts), chunk_size):
            chunk = texts[i : i + chunk_size]
            try:
                # Validate all texts in chunk
                for text in chunk:
                    self._validate_input(text)

                # Process chunk
                chunk_results = [self.pseudonymize(text) for text in chunk]
                results.extend(chunk_results)

                # Log progress for large batches
                if len(texts) > chunk_size * 2:
                    logger.info(
                        f"Processed {min(i + chunk_size, len(texts))}/{len(texts)} texts"
                    )

            except Exception as e:
                # Log which chunk failed
                logger.error(f"Failed processing chunk {i // chunk_size + 1}: {e}")
                raise

        return results

    async def redact_batch_async(self, texts: list[str]) -> list[str]:
        """Async batch processing for anonymization.

        Wraps redact_batch() for async/await compatibility.
        Note: CPU-bound NLP tasks run in a thread pool executor.

        Args:
            texts: List of texts to anonymize

        Returns:
            List of anonymized texts
        """
        loop = asyncio.get_event_loop()
        executor = self._executor or None
        return await loop.run_in_executor(executor, self.redact_batch, texts)

    async def pseudonymize_batch_async(
        self, texts: list[str]
    ) -> list[tuple[str, dict[str, str]]]:
        """Async batch processing for pseudonymization.

        Wraps pseudonymize_batch() for async/await compatibility.
        Note: CPU-bound NLP tasks run in a thread pool executor.

        Args:
            texts: List of texts to pseudonymize

        Returns:
            List of tuples (pseudonymized_text, entity_map)
        """
        loop = asyncio.get_event_loop()
        executor = self._executor or None
        return await loop.run_in_executor(executor, self.pseudonymize_batch, texts)

    # Utility methods
    def get_supported_patterns(self) -> list[str]:
        """Get list of all supported entity patterns.

        Returns:
            List of pattern names
        """
        from .nlp.patterns import PATTERN_DOMAINS

        return list(PATTERN_DOMAINS.keys())

    def get_performance_stats(self) -> dict:
        """Get performance statistics if available.

        Returns:
            Dictionary with performance metrics
        """
        from .nlp.utils import instances

        # This is a placeholder for future performance tracking
        return {
            "max_text_length": self.config.max_text_length,
            "singleton_instances": len(instances),
            "chunk_size": self._chunk_size,
        }

    def validate_custom_components(self, components: list[NERComponent]) -> list[str]:
        """Validate custom NER components.

        Args:
            components: List of custom components to validate

        Returns:
            List of validation warnings/errors
        """
        warnings = []

        for i, component in enumerate(components):
            if not hasattr(component, "label"):
                warnings.append(f"Component {i} missing required 'label' attribute")

            # Check that at least one is not None
            if component.pattern is None and component.processing_func is None:
                warnings.append(
                    f"Component {i} must have either 'pattern' or 'processing_func'"
                )

            # Check that not both are provided (non-None)
            if component.pattern is not None and component.processing_func is not None:
                warnings.append(
                    f"Component {i} should not have both 'pattern' and 'processing_func'"
                )

        return warnings

    @classmethod
    def clear_cache(cls):
        """Clear cached EntityRedactor instances, releasing spaCy models from memory.

        Useful for:
        - Testing (ensuring clean state between tests)
        - Memory management (releasing loaded models)
        - Configuration changes (forcing model reload)
        """
        from .nlp.utils import clear_singleton_instances

        clear_singleton_instances()
