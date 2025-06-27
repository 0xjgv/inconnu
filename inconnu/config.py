from dataclasses import dataclass


@dataclass
class Config:
    data_retention_days: int
    max_text_length: int
