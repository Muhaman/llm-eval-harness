from evalh.config import Case, GradeResult
from evalh.llm import Judge


class JudgeGrader:
    """Delegates to an LLM judge and passes when score >= threshold."""

    def __init__(self, judge: Judge, rubric: str, threshold: float) -> None:
        self._judge = judge
        self._rubric = rubric
        self._threshold = threshold

    async def grade(self, case: Case, output: str) -> GradeResult:
        verdict = await self._judge.score(
            rubric=self._rubric,
            input=case.input_text(),
            output=output,
            expected=case.expected,
        )
        summary = f"judge {verdict.score:.2f} (threshold {self._threshold:.2f})"
        return GradeResult(
            passed=verdict.score >= self._threshold,
            score=verdict.score,
            detail=f"{summary}: {verdict.reasoning}",
        )
