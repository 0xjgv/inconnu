from dataclasses import dataclass


@dataclass
class Config:
    anonymize_entities: bool = True
    data_retention_days: int = 30
    max_text_length: int = 1000
