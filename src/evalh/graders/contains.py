from evalh.config import Case, GradeResult


class ContainsGrader:
    """Passes when every required substring appears in the output."""

    def __init__(self, required: list[str]) -> None:
        self._required = required

    async def grade(self, case: Case, output: str) -> GradeResult:
        missing = [text for text in self._required if text not in output]
        if not missing:
            return GradeResult(passed=True, score=1.0, detail="all substrings present")
        found = len(self._required) - len(missing)
        return GradeResult(
            passed=False,
            score=found / len(self._required),
            detail=f"missing: {', '.join(repr(text) for text in missing)}",
        )
