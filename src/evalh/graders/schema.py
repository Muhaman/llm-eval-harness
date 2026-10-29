import json
from typing import Any

from jsonschema import Draft202012Validator, ValidationError

from evalh.config import Case, GradeResult


def _error_path(error: ValidationError) -> list[str]:
    return [str(part) for part in error.path]


class JsonSchemaGrader:
    """Passes when the output parses as JSON and validates against the schema."""

    def __init__(self, schema: dict[str, Any]) -> None:
        self._validator = Draft202012Validator(schema)

    async def grade(self, case: Case, output: str) -> GradeResult:
        try:
            document = json.loads(output)
        except json.JSONDecodeError as exc:
            return GradeResult(passed=False, score=0.0, detail=f"output is not valid JSON: {exc}")
        errors = sorted(self._validator.iter_errors(document), key=_error_path)
        if not errors:
            return GradeResult(passed=True, score=1.0, detail="valid against schema")
        first = errors[0]
        location = "/".join(str(part) for part in first.path) or "<root>"
        return GradeResult(
            passed=False,
            score=0.0,
            detail=f"{len(errors)} schema error(s); first at {location}: {first.message}",
        )
