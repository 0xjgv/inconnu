from threading import Lock

from spacy import load

from inconnu.config import Language, get_spacy_model
from inconnu.nlp.utils import (
    CUSTOM_NER_COMPONENTS,
    EntityLabel,
    create_ner_component,
)


# Spacy pipeline for entity anonymization
class EntityAnonymizer:
    __slots__ = ["nlp", "language"]
    _instance = None
    _lock = Lock()

    def __new__(cls, language: Language):
        if cls._instance is None or cls._instance.language != language:
            with cls._lock:
                cls._instance = super().__new__(cls)
                cls._instance._initialize(language)
        return cls._instance

    def _initialize(self, language: Language):
        # Disable everything except for NER
        self.nlp = load(
            get_spacy_model(language),
            disable=[
                "attribute_ruler",
                "lemmatizer",
                "tok2vec",
                "tagger",
                "parser",
            ],
        )
        self.language = language

        for custom_ner_component in CUSTOM_NER_COMPONENTS:
            custom_ner_component_name = create_ner_component(**custom_ner_component)
            self.nlp.add_pipe(custom_ner_component_name, after="ner")

    def __call__(self, text: str) -> str:
        anonymized_text = text
        doc = self.nlp(text)

        filtered_ents = filter(
            lambda ent: ent.label_ in EntityLabel.__members__, doc.ents
        )
        # Process in reverse to avoid index issues
        for ent in reversed(list(filtered_ents)):
            placeholder = f"[{ent.label_}]"
            anonymized_text = (
                anonymized_text[: ent.start_char]
                + placeholder
                + anonymized_text[ent.end_char :]
            )
        return anonymized_text
