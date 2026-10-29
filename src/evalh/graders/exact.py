from evalh.config import Case, GradeResult


class ExactGrader:
    """Passes when the output equals `expected` after trimming whitespace."""

    async def grade(self, case: Case, output: str) -> GradeResult:
        if case.expected is None:
            return GradeResult(passed=False, score=0.0, detail="case has no `expected` value")
        if output.strip() == case.expected.strip():
            return GradeResult(passed=True, score=1.0, detail="exact match")
        return GradeResult(
            passed=False,
            score=0.0,
            detail=f"expected {case.expected.strip()!r}, got {output.strip()!r}",
        )
