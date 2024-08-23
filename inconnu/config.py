from enum import StrEnum
from typing import NamedTuple

SUPPORTED_REGIONS = ["DE", "CH", "GB"]


class Versions(dict):
    def __init__(self, *, fallback, **versions):
        super().__init__(**versions)
        self.fallback = fallback

    def __getitem__(self, key):
        return super().get(key, self.fallback)


class Language(StrEnum):
    EN = "en"
    DE = "de"


class SpacyModels(StrEnum):
    # 'en_core_web_trf' is the most accurate model for name entity recognition
    EN_CORE_WEB_TRF = "en_core_web_trf"
    DE_CORE_NEWS_MD = "de_core_news_md"
    EN_CORE_WEB_SM = "en_core_web_sm"


class Config(NamedTuple):
    language: Language = Language.EN
    data_retention_days: int = 30
    max_text_length: int = 1000


def get_spacy_model(language: Language) -> str:
    model_map = {
        Language.EN: SpacyModels.EN_CORE_WEB_TRF,
        Language.DE: SpacyModels.DE_CORE_NEWS_MD,
    }
    # Default to English if language is not supported
    return model_map.get(language, SpacyModels.EN_CORE_WEB_SM)
