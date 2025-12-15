from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    # Core configuration
    data_retention_days: int = 30
    max_text_length: int = 75_000

    # Error handling configuration
    error_mode: str = "strict"  # "strict" or "lenient"
    log_errors: bool = True
    max_error_logs: int = 10
    continue_on_error: bool = False

    # Performance configuration
    batch_size: int = 100
    chunk_size: int = 10000
    memory_limit_mb: Optional[int] = None
    processing_timeout_seconds: Optional[float] = None
    enable_performance_monitoring: bool = False
    performance_log_interval: int = 100  # Log every N items in batch

    # Debug configuration
    debug_mode: bool = False
    log_conflicts: bool = False
    log_performance: bool = False
    profile_enabled: bool = False

    # Multilingual configuration
    cross_language_standardization: bool = True

    def __post_init__(self):
        """Validate configuration values after initialization."""
        # Validate error mode
        if self.error_mode not in ("strict", "lenient"):
            raise ValueError(f"Invalid error_mode: {self.error_mode}")

        # Validate numeric limits
        if self.max_text_length <= 0:
            raise ValueError("max_text_length must be positive")

        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")

        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
