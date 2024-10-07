from dataclasses import dataclass
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


class NERComponent(NamedTuple):
    label: str
    processing_func: Callable[[Doc], Doc] | None = None
    pattern: Pattern | None = None
    before_ner: bool = True
