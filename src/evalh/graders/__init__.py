"""Grader protocol and factory."""

from typing import Protocol, assert_never

from evalh.config import (
    Case,
    ConfigError,
    ContainsSpec,
    ExactSpec,
    GraderDefaults,
    GradeResult,
    GraderSpec,
    JsonSchemaSpec,
    JudgeSpec,
    RegexSpec,
)
from evalh.graders.contains import ContainsGrader
from evalh.graders.exact import ExactGrader
from evalh.graders.judge import JudgeGrader
from evalh.graders.regex import RegexGrader
from evalh.graders.schema import JsonSchemaGrader
from evalh.llm import Judge


class Grader(Protocol):
    async def grade(self, case: Case, output: str) -> GradeResult: ...


def build_grader(spec: GraderSpec, *, judge: Judge | None, defaults: GraderDefaults) -> Grader:
    match spec:
        case ExactSpec():
            return ExactGrader()
        case RegexSpec():
            return RegexGrader(spec.pattern)
        case ContainsSpec():
            return ContainsGrader(spec.all_of)
        case JsonSchemaSpec():
            return JsonSchemaGrader(spec.json_schema)
        case JudgeSpec():
            if judge is None:
                raise ConfigError("judge grader requires a Judge (is ANTHROPIC_API_KEY set?)")
            threshold = spec.pass_threshold
            if "pass_threshold" not in spec.model_fields_set and defaults.judge_pass_threshold:
                threshold = defaults.judge_pass_threshold
            return JudgeGrader(judge, spec.rubric, threshold)
        case _:
            assert_never(spec)
