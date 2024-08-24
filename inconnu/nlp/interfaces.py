from dataclasses import dataclass


@dataclass
class ProcessedData:
    entity_map: dict[str, str]
    processing_time_ms: float
    redacted_text: str
    original_text: str
    text_length: int
    timestamp: str
    hashed_id: str
