from dataclasses import dataclass, field
from re import Pattern
from typing import Callable, NamedTuple

from spacy.tokens import Doc


@dataclass
class ProcessedData:
    entity_map: dict[str, str]
    processing_time_ms: float
    redacted_text: str
    original_text: str
    text_length: int
    timestamp: str
    hashed_id: str
    # Position-based mapping for robust de-anonymization
    # Maps placeholder -> (start_position, end_position) in redacted_text
    # This allows accurate restoration even if original text contained placeholder-like strings
    entity_positions: dict[str, tuple[int, int]] = field(default_factory=dict)


class NERComponent(NamedTuple):
    label: str
    processing_func: Callable[[Doc], Doc] | None = None
    pattern: Pattern | None = None
    before_ner: bool = True
