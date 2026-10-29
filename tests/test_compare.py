from evalh.compare import compare
from evalh.config import GradeResult
from evalh.runner import CaseResult, RunResult


def make_run(passing: list[bool]) -> RunResult:
    cases = [
        CaseResult(
            id=f"c{i + 1}",
            output="x",
            grades=[GradeResult(passed=ok, score=1.0 if ok else 0.0, detail="")],
            passed=ok,
            error=None,
            latency_ms=1.0,
        )
        for i, ok in enumerate(passing)
    ]
    return RunResult(suite="s", cases=cases)


def test_one_new_failure_is_a_regression() -> None:
    baseline = make_run([True] * 10)
    current = make_run([True] * 6 + [False] + [True] * 3)
    result = compare(current, baseline)
    assert result.regressed
    assert result.newly_failing == ["c7"]
    assert result.newly_passing == []
    assert round(result.pass_rate_delta, 2) == -0.1


def test_equal_results_are_not_a_regression() -> None:
    result = compare(make_run([True] * 9 + [False]), make_run([True] * 9 + [False]))
    assert not result.regressed
    assert result.pass_rate_delta == 0


def test_improvement_lists_newly_passing() -> None:
    result = compare(make_run([True, True]), make_run([True, False]))
    assert not result.regressed
    assert result.newly_passing == ["c2"]


def test_removed_case_drops_pass_rate_beyond_threshold() -> None:
    baseline = make_run([True] * 10)
    current = make_run([True] * 9 + [False])
    assert compare(current, baseline, threshold=0.5).regressed
