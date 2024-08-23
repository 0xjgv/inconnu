import hashlib
from abc import ABC, abstractmethod

from pydantic import BaseModel

from inconnu.config import Config


class ProcessedData(BaseModel):
    entity_map: dict[str, str] | None = None
    pseudonymized_text: str | None = None
    anonymized_text: str | None = None
    processing_time_ms: float
    text_length: int
    timestamp: str
    hashed_id: str
    text: str


class InconnuBase(ABC):
    @abstractmethod
    def __init__(self, *, config: Config): ...

    def _log(self, *args, **kwargs):
        print(*args, **kwargs)

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    @abstractmethod
    def __call__(self, *, text: str) -> ProcessedData: ...
