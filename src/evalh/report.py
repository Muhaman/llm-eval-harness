"""JSONL persistence and Markdown rendering."""

import json
from pathlib import Path

from evalh.compare import Comparison
from evalh.config import ConfigError
from evalh.runner import CaseResult, RunResult


def write_jsonl(result: RunResult, path: Path) -> None:
    rows = [{"suite": result.suite, **case.model_dump(mode="json")} for case in result.cases]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def read_jsonl(path: Path) -> RunResult:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ConfigError(f"results file not found: {path}") from exc
    except OSError as exc:
        raise ConfigError(f"cannot read results file {path}: {exc}") from exc
    try:
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
        cases = [CaseResult.model_validate(row) for row in rows]
    except ValueError as exc:
        raise ConfigError(f"malformed results file {path}: {exc}") from exc
    if not cases:
        raise ConfigError(f"results file is empty: {path}")
    return RunResult(suite=str(rows[0].get("suite", "")), cases=cases)


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def render_markdown(result: RunResult, comparison: Comparison | None = None) -> str:
    total = len(result.cases)
    lines = [
        f"# Eval report: {result.suite}",
        "",
        f"**{result.passed}/{total} passed** ({result.pass_rate:.1%})",
        "",
    ]
    if comparison is not None:
        verdict = "Regression" if comparison.regressed else "No regression"
        lines += [
            f"## {verdict} vs baseline",
            "",
            f"- Pass rate delta: {comparison.pass_rate_delta:+.1%}",
            f"- Newly failing: {', '.join(comparison.newly_failing) or 'none'}",
            f"- Newly passing: {', '.join(comparison.newly_passing) or 'none'}",
            "",
        ]
    lines += ["## Cases", "", "| Case | Result | Latency (ms) | Detail |", "|---|---|---|---|"]
    for case in result.cases:
        status = "pass" if case.passed else "FAIL"
        lines.append(
            f"| {_cell(case.id)} | {status} | {case.latency_ms:.0f} | {_cell(_detail(case))} |"
        )
    return "\n".join(lines) + "\n"


def _detail(case: CaseResult) -> str:
    if case.error is not None:
        return f"error: {case.error}"
    failed = [grade.detail for grade in case.grades if not grade.passed]
    return "; ".join(failed)
