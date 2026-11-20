from pathlib import Path

from pydantic import Field

from anamnesis.domain.services.questionnaire import Questionnaire
from anamnesis.domain.types import LanguageCode
from anamnesis.main.config.base import BaseConfig


class KnowledgeConfig(BaseConfig):
    languages: tuple[LanguageCode, ...] = Field(default=(LanguageCode("ru"),), min_length=1)

    locales_dir: Path = Path("locales")
    resources_dir: Path = Path("resources")

    ontology_path: Path = Path("ontology/anamnesis.owl")
    linguistic_variables_path: Path = Path("knowledge/linguistic_variables.yaml")
    instructions_dir: Path = Path("knowledge/instructions")
    practice_selection_path: Path = Path("knowledge/practice_selection.yaml")

    reasoner_concurrency: int = Field(default=2, ge=1)
    question_limit: int = Field(default=Questionnaire.DEFAULT_QUESTION_LIMIT, ge=0)
