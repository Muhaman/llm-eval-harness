import re

from evalh.config import Case, GradeResult


class RegexGrader:
    """Passes when the pattern matches anywhere in the output."""

    def __init__(self, pattern: str) -> None:
        self._pattern = re.compile(pattern)

    async def grade(self, case: Case, output: str) -> GradeResult:
        if self._pattern.search(output):
            return GradeResult(passed=True, score=1.0, detail="pattern matched")
        return GradeResult(
            passed=False, score=0.0, detail=f"pattern {self._pattern.pattern!r} did not match"
        )
