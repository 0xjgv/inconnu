from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    # Existing configuration
    data_retention_days: int = 30
    max_text_length: int = 75_000

    # Pattern configuration
    entity_priorities: dict[str, int] = field(default_factory=dict)
    enabled_patterns: set[str] = field(default_factory=set)
    disabled_patterns: set[str] = field(default_factory=set)
    domain_pattern_sets: dict[str, set[str]] = field(default_factory=dict)

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

    # Validation configuration
    validation_mode: str = "normal"  # "strict", "normal", or "minimal"
    min_confidence_threshold: float = 0.5
    enable_custom_validators: bool = True
    validator_timeout_ms: int = 100

    # Multilingual configuration
    auto_detect_language: bool = False
    preferred_models: dict[str, str] = field(default_factory=dict)
    cross_language_standardization: bool = True

    # Async configuration
    thread_pool_size: Optional[int] = None
    process_pool_size: Optional[int] = None
    prefer_processes: bool = (
        False  # Use processes instead of threads for CPU-bound tasks
    )

    # Streaming configuration
    stream_chunk_size: int = 10000
    stream_overlap_size: int = 100
    stream_buffer_size: int = 1024 * 1024  # 1MB

    def __post_init__(self):
        """Validate configuration values after initialization."""
        # Validate error mode
        if self.error_mode not in ("strict", "lenient"):
            raise ValueError(f"Invalid error_mode: {self.error_mode}")

        # Validate validation mode
        if self.validation_mode not in ("strict", "normal", "minimal"):
            raise ValueError(f"Invalid validation_mode: {self.validation_mode}")

        # Validate numeric limits
        if self.max_text_length <= 0:
            raise ValueError("max_text_length must be positive")

        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")

        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")

        if self.min_confidence_threshold < 0 or self.min_confidence_threshold > 1:
            raise ValueError("min_confidence_threshold must be between 0 and 1")

        # Set default domain pattern sets if not provided
        if not self.domain_pattern_sets:
            self._set_default_domain_patterns()

    def _set_default_domain_patterns(self):
        """Set default domain pattern groupings."""
        self.domain_pattern_sets = {
            "healthcare": {"SSN", "MRN", "NPI", "DEA_NUMBER", "ICD_CODE", "TRIAL_ID"},
            "legal": {"CASE_NUMBER", "BAR_NUMBER", "LEGAL_CITATION"},
            "financial": {
                "CREDIT_CARD",
                "SWIFT_CODE",
                "ROUTING_NUMBER",
                "CRYPTO_WALLET",
            },
            "hr": {"EMPLOYEE_ID", "SALARY", "DEPARTMENT_CODE", "LINKEDIN_URL"},
            "support": {
                "TICKET_NUMBER",
                "ORDER_NUMBER",
                "CUSTOMER_ID",
                "SOCIAL_MEDIA_HANDLE",
            },
            "education": {"STUDENT_ID", "COURSE_CODE", "GPA"},
            "research": {
                "PARTICIPANT_ID",
                "STUDY_ID",
                "IRB_NUMBER",
                "INTERVIEW_TIMESTAMP",
            },
            "government": {"PASSPORT", "DRIVER_LICENSE", "VIN", "LICENSE_PLATE", "EIN"},
            "technology": {"UUID", "API_KEY", "MAC_ADDRESS", "BADGE_NUMBER"},
        }

    def enable_domain_patterns(self, domain: str):
        """Enable all patterns for a specific domain."""
        if domain in self.domain_pattern_sets:
            self.enabled_patterns.update(self.domain_pattern_sets[domain])
            self.disabled_patterns -= self.domain_pattern_sets[domain]

    def disable_domain_patterns(self, domain: str):
        """Disable all patterns for a specific domain."""
        if domain in self.domain_pattern_sets:
            self.disabled_patterns.update(self.domain_pattern_sets[domain])
            self.enabled_patterns -= self.domain_pattern_sets[domain]
