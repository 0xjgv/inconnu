"""Custom exceptions for Inconnu library."""


class InconnuError(Exception):
    """Base exception for all Inconnu-related errors."""

    pass


class TextTooLongError(InconnuError):
    """Raised when input text exceeds maximum length limit."""

    def __init__(self, text_length: int, max_length: int):
        self.text_length = text_length
        self.max_length = max_length
        super().__init__(
            f"Text length ({text_length}) exceeds maximum allowed length ({max_length}). "
            f"Consider increasing max_text_length parameter or splitting the text into smaller chunks."
        )


class ModelNotFoundError(InconnuError):
    """Raised when required spaCy model is not found."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        super().__init__(
            f"spaCy model '{model_name}' not found. "
            f"Install it with: uv run python -m spacy download {model_name}"
        )


class ProcessingError(InconnuError):
    """Raised when text processing fails."""

    def __init__(self, message: str, original_error: Exception | None = None):
        self.original_error = original_error
        error_msg = f"Text processing failed: {message}"
        if original_error:
            error_msg += f" (Original error: {str(original_error)})"
        super().__init__(error_msg)


class ConfigurationError(InconnuError):
    """Raised when configuration is invalid."""

    def __init__(self, message: str):
        super().__init__(f"Configuration error: {message}")
