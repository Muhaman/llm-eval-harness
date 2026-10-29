"""Baseline comparison for the CI gate."""

from pydantic import BaseModel

from evalh.runner import RunResult


class Comparison(BaseModel):
    regressed: bool
    pass_rate_delta: float
    newly_failing: list[str]
    newly_passing: list[str]


def compare(current: RunResult, baseline: RunResult, threshold: float = 0.02) -> Comparison:
    """Regressed when the pass rate drops by more than `threshold` or any case newly fails."""
    before = {case.id: case.passed for case in baseline.cases}
    newly_failing = [c.id for c in current.cases if before.get(c.id) is True and not c.passed]
    newly_passing = [c.id for c in current.cases if before.get(c.id) is False and c.passed]
    delta = current.pass_rate - baseline.pass_rate
    return Comparison(
        regressed=delta < -threshold or bool(newly_failing),
        pass_rate_delta=delta,
        newly_failing=newly_failing,
        newly_passing=newly_passing,
    )
