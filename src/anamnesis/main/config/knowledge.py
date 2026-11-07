from pathlib import Path

from pydantic import Field

from anamnesis.domain.services.questionnaire import Questionnaire
from anamnesis.main.config.base import BaseConfig


class KnowledgeConfig(BaseConfig):
    ontology_path: Path = Path("ontology/anamnesis.owl")
    locales_dir: Path = Path("locales")
    linguistic_variables_path: Path = Path("knowledge/linguistic_variables.yaml")
    reasoner_concurrency: int = Field(default=2, ge=1)
    question_limit: int = Field(default=Questionnaire.DEFAULT_QUESTION_LIMIT, ge=0)
