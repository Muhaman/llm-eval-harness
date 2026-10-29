from types import SimpleNamespace
from typing import Any

import pytest

from evalh.config import ConfigError, GraderDefaults, GraderSpec, Suite
from evalh.graders import build_grader
from evalh.llm import Judge, JudgeError
from helpers import FakeJudge, make_case


def spec(**kwargs: Any) -> GraderSpec:
    suite = Suite.model_validate(
        {
            "name": "s",
            "target": {"type": "python", "ref": "m:f"},
            "cases": [{"id": "a", "input": "x", "graders": [kwargs]}],
        }
    )
    return suite.cases[0].graders[0]


async def test_exact_trims_whitespace() -> None:
    grader = build_grader(spec(type="exact"), judge=None, defaults=GraderDefaults())
    result = await grader.grade(make_case(expected="  Paris\n"), "Paris  ")
    assert result.passed


async def test_exact_without_expected_fails() -> None:
    grader = build_grader(spec(type="exact"), judge=None, defaults=GraderDefaults())
    result = await grader.grade(make_case(expected=None), "Paris")
    assert not result.passed
    assert "expected" in result.detail


async def test_regex_matches_three_digits() -> None:
    grader = build_grader(
        spec(type="regex", pattern=r"^\d{3}$"), judge=None, defaults=GraderDefaults()
    )
    assert (await grader.grade(make_case(), "123")).passed
    assert not (await grader.grade(make_case(), "1234")).passed


async def test_contains_all_reports_missing_substring() -> None:
    grader = build_grader(
        spec(type="contains", all=["refund", "30 days"]), judge=None, defaults=GraderDefaults()
    )
    result = await grader.grade(make_case(), "You can get a refund.")
    assert not result.passed
    assert "30 days" in result.detail
    assert "refund" not in result.detail


async def test_json_schema_invalid_json_fails() -> None:
    grader = build_grader(
        spec(type="json_schema", schema={"type": "object"}), judge=None, defaults=GraderDefaults()
    )
    result = await grader.grade(make_case(), "not json")
    assert not result.passed
    assert "JSON" in result.detail


async def test_json_schema_validates_structure() -> None:
    schema = {"type": "object", "required": ["id"], "properties": {"id": {"type": "integer"}}}
    grader = build_grader(
        spec(type="json_schema", schema=schema), judge=None, defaults=GraderDefaults()
    )
    assert (await grader.grade(make_case(), '{"id": 1}')).passed
    assert not (await grader.grade(make_case(), '{"id": "x"}')).passed


async def test_judge_score_above_threshold_passes(fake_judge: FakeJudge) -> None:
    grader = build_grader(
        spec(type="judge", rubric="Be polite", pass_threshold=0.7),
        judge=fake_judge,
        defaults=GraderDefaults(),
    )
    result = await grader.grade(make_case(), "hi")
    assert result.passed
    assert result.score == 0.8


async def test_judge_score_below_threshold_fails() -> None:
    grader = build_grader(
        spec(type="judge", rubric="Be polite", pass_threshold=0.9),
        judge=FakeJudge(0.8),
        defaults=GraderDefaults(),
    )
    assert not (await grader.grade(make_case(), "hi")).passed


def test_judge_grader_without_judge_is_config_error() -> None:
    with pytest.raises(ConfigError):
        build_grader(spec(type="judge", rubric="r"), judge=None, defaults=GraderDefaults())


def test_judge_without_api_key_names_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY"):
        Judge()


async def test_judge_refusal_raises_judge_error() -> None:
    async def parse(**_: Any) -> Any:
        return SimpleNamespace(stop_reason="refusal", parsed_output=None)

    client = SimpleNamespace(messages=SimpleNamespace(parse=parse))
    judge = Judge(client=client, model="m")
    with pytest.raises(JudgeError):
        await judge.score(rubric="r", input="i", output="o", expected=None)
