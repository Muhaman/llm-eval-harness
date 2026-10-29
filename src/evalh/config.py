"""Suite definition models and YAML loading."""

import json
from pathlib import Path
from typing import Annotated, Any, Literal, Self

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

Input = str | dict[str, Any]


class ConfigError(Exception):
    """Invalid suite, missing file or missing environment."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class GradeResult(BaseModel):
    passed: bool
    score: float
    detail: str


class ExactSpec(_Strict):
    type: Literal["exact"]


class RegexSpec(_Strict):
    type: Literal["regex"]
    pattern: str


class ContainsSpec(_Strict):
    type: Literal["contains"]
    all_of: list[str] = Field(alias="all", min_length=1)


class JsonSchemaSpec(_Strict):
    type: Literal["json_schema"]
    json_schema: dict[str, Any] = Field(alias="schema")

    @field_validator("json_schema")
    @classmethod
    def _check_schema(cls, value: dict[str, Any]) -> dict[str, Any]:
        try:
            Draft202012Validator.check_schema(value)
        except SchemaError as exc:
            raise ValueError(f"invalid JSON schema: {exc.message}") from exc
        return value


class JudgeSpec(_Strict):
    type: Literal["judge"]
    rubric: str
    pass_threshold: float = Field(default=0.7, ge=0, le=1)


GraderSpec = Annotated[
    ExactSpec | RegexSpec | ContainsSpec | JsonSchemaSpec | JudgeSpec,
    Field(discriminator="type"),
]


class GraderDefaults(_Strict):
    """Suite-wide fallbacks for grader settings."""

    judge_pass_threshold: float | None = Field(default=None, ge=0, le=1)


class TargetSpec(_Strict):
    type: Literal["python", "http"]
    ref: str


class Case(_Strict):
    id: str
    input: Input
    expected: str | None = None
    graders: list[GraderSpec] = Field(min_length=1)

    def input_text(self) -> str:
        if isinstance(self.input, str):
            return self.input
        return json.dumps(self.input, sort_keys=True)


class Suite(_Strict):
    name: str
    target: TargetSpec
    defaults: GraderDefaults = Field(default_factory=GraderDefaults)
    cases: list[Case] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_case_ids(self) -> Self:
        seen: set[str] = set()
        for case in self.cases:
            if case.id in seen:
                raise ValueError(f"duplicate case id: {case.id}")
            seen.add(case.id)
        return self


def load_suite(path: Path) -> Suite:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"suite file not found: {path}") from exc
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"cannot read suite {path}: {exc}") from exc
    try:
        return Suite.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"invalid suite {path}:\n{exc}") from exc
