from dataclasses import dataclass


@dataclass
class Config:
    pseudonymize_entities: bool = True
    data_retention_days: int = 30
    max_text_length: int = 1000
