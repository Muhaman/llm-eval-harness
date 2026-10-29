"""Concurrent suite execution."""

import asyncio
import time
from pathlib import Path

import structlog
from pydantic import BaseModel

from evalh.config import Case, GradeResult, Suite
from evalh.graders import Grader, build_grader
from evalh.llm import Judge
from evalh.targets import Target, open_target

log = structlog.get_logger()


class CaseResult(BaseModel):
    id: str
    output: str | None
    grades: list[GradeResult]
    passed: bool
    error: str | None
    latency_ms: float


class RunResult(BaseModel):
    suite: str
    cases: list[CaseResult]

    @property
    def passed(self) -> int:
        return sum(1 for case in self.cases if case.passed)

    @property
    def pass_rate(self) -> float:
        return self.passed / len(self.cases) if self.cases else 0.0


async def _run_case(
    case: Case,
    graders: list[Grader],
    target: Target,
    semaphore: asyncio.Semaphore,
    timeout_s: float,
) -> CaseResult:
    async with semaphore:
        started = time.perf_counter()
        output: str | None = None
        grades: list[GradeResult] = []
        error: str | None = None
        try:
            output = await asyncio.wait_for(target(case.input), timeout=timeout_s)
        except TimeoutError:
            error = f"target timed out after {timeout_s}s"
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        if output is not None:
            try:
                grades = [await grader.grade(case, output) for grader in graders]
            except Exception as exc:
                error = f"grader failed: {type(exc).__name__}: {exc}"
        latency_ms = (time.perf_counter() - started) * 1000
    passed = error is None and all(grade.passed for grade in grades)
    if error is not None:
        log.warning("case_error", case=case.id, error=error)
    return CaseResult(
        id=case.id,
        output=output,
        grades=grades,
        passed=passed,
        error=error,
        latency_ms=latency_ms,
    )


async def run_suite(
    suite: Suite,
    *,
    concurrency: int = 8,
    timeout_s: float = 60.0,
    judge: Judge | None = None,
    target: Target | None = None,
    base_dir: Path | None = None,
) -> RunResult:
    """Run every case with bounded concurrency.

    `target` overrides the suite's target (used by tests); `base_dir` is where
    python targets are imported from.
    """
    defaults = suite.defaults
    graders: dict[str, list[Grader]] = {}
    for case in suite.cases:
        graders[case.id] = [build_grader(s, judge=judge, defaults=defaults) for s in case.graders]
    semaphore = asyncio.Semaphore(concurrency)

    async def run_all(active: Target) -> list[CaseResult]:
        return await asyncio.gather(
            *(_run_case(c, graders[c.id], active, semaphore, timeout_s) for c in suite.cases)
        )

    if target is not None:
        cases = await run_all(target)
    else:
        async with open_target(suite.target, base_dir) as opened:
            cases = await run_all(opened)
    return RunResult(suite=suite.name, cases=cases)
