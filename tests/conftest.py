from typing import Any

import pytest

from evalh.config import Case, GraderSpec, Suite
from evalh.llm import Judge, JudgeVerdict


class FakeJudge(Judge):
    """Judge that returns a fixed score without touching the network."""

    def __init__(self, score: float = 0.8) -> None:
        self._score = score

    async def score(
        self, *, rubric: str, input: str, output: str, expected: str | None
    ) -> JudgeVerdict:
        return JudgeVerdict(score=self._score, reasoning="fake verdict")


@pytest.fixture
def fake_judge() -> FakeJudge:
    return FakeJudge(0.8)


def make_case(
    case_id: str = "c1",
    *,
    input: str = "hello",
    expected: str | None = None,
    graders: list[dict[str, Any]] | None = None,
) -> Case:
    return Case.model_validate(
        {
            "id": case_id,
            "input": input,
            "expected": expected,
            "graders": graders or [{"type": "exact"}],
        }
    )


def make_suite(cases: list[Case], graders: list[GraderSpec] | None = None) -> Suite:
    return Suite.model_validate(
        {
            "name": "test-suite",
            "target": {"type": "python", "ref": "fake_targets:upper"},
            "cases": [case.model_dump(by_alias=True) for case in cases],
        }
    )
