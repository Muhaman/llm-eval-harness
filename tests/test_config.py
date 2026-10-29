from pathlib import Path

import pytest
from pydantic import ValidationError

from evalh.config import ConfigError, Suite, load_suite

BASE = {
    "name": "s",
    "target": {"type": "python", "ref": "m:f"},
}


def test_given_unknown_grader_type_when_validating_then_error() -> None:
    data = {**BASE, "cases": [{"id": "a", "input": "x", "graders": [{"type": "vibes"}]}]}
    with pytest.raises(ValidationError):
        Suite.model_validate(data)


def test_given_duplicate_case_ids_when_validating_then_error() -> None:
    case = {"id": "a", "input": "x", "graders": [{"type": "exact"}]}
    with pytest.raises(ValidationError, match="duplicate"):
        Suite.model_validate({**BASE, "cases": [case, case]})


def test_given_invalid_json_schema_when_validating_then_error() -> None:
    graders = [{"type": "json_schema", "schema": {"type": "not-a-type"}}]
    with pytest.raises(ValidationError):
        Suite.model_validate({**BASE, "cases": [{"id": "a", "input": "x", "graders": graders}]})


def test_given_missing_file_when_loading_then_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_suite(tmp_path / "nope.yaml")


def test_given_unknown_grader_in_file_when_loading_then_config_error(tmp_path: Path) -> None:
    path = tmp_path / "suite.yaml"
    path.write_text(
        "name: s\ntarget: {type: python, ref: 'm:f'}\n"
        "cases:\n  - {id: a, input: x, graders: [{type: vibes}]}\n"
    )
    with pytest.raises(ConfigError):
        load_suite(path)
