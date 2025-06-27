from dataclasses import dataclass


@dataclass
class Config:
    data_retention_days: int = 30
    max_text_length: int = 75_000
