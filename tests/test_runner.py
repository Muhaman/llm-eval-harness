import asyncio
from typing import Any

from evalh.runner import run_suite
from tests.conftest import make_case, make_suite


async def test_timeout_marks_case_failed_and_others_complete() -> None:
    cases = [
        make_case("fast", input="a", expected="A"),
        make_case("slow", input="b", expected="B"),
        make_case("fast2", input="c", expected="C"),
    ]

    async def target(value: str | dict[str, Any]) -> str:
        if value == "b":
            await asyncio.sleep(1)
        return str(value).upper()

    result = await run_suite(make_suite(cases), timeout_s=0.05, target=target)
    by_id = {case.id: case for case in result.cases}
    assert by_id["slow"].error is not None
    assert "timed out" in by_id["slow"].error
    assert by_id["slow"].passed is False
    assert by_id["slow"].output is None
    assert by_id["fast"].passed
    assert by_id["fast2"].passed


async def test_concurrency_never_exceeds_limit() -> None:
    in_flight = 0
    peak = 0

    async def target(value: str | dict[str, Any]) -> str:
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.01)
        in_flight -= 1
        return str(value)

    cases = [make_case(f"c{i}", input="x", expected="x") for i in range(10)]
    result = await run_suite(make_suite(cases), concurrency=2, target=target)
    assert peak == 2
    assert result.passed == 10


async def test_case_passes_only_if_all_graders_pass() -> None:
    case = make_case(
        "c1",
        input="abc",
        expected="abc",
        graders=[{"type": "exact"}, {"type": "contains", "all": ["zzz"]}],
    )

    async def target(value: str | dict[str, Any]) -> str:
        return str(value)

    result = await run_suite(make_suite([case]), target=target)
    assert [g.passed for g in result.cases[0].grades] == [True, False]
    assert result.cases[0].passed is False


async def test_target_exception_is_recorded_as_error() -> None:
    async def target(value: str | dict[str, Any]) -> str:
        raise RuntimeError("boom")

    result = await run_suite(make_suite([make_case("c1", expected="x")]), target=target)
    assert result.cases[0].error == "RuntimeError: boom"
    assert result.cases[0].passed is False
