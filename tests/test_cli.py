from pathlib import Path

from typer.testing import CliRunner

from evalh.cli import app

runner = CliRunner()

SUITE = """\
name: cli-suite
target: {{type: python, ref: "fake_targets:upper"}}
cases:
  - {{id: a, input: hello, expected: HELLO, graders: [{{type: exact}}]}}
  - {{id: b, input: world, expected: {b_expected}, graders: [{{type: exact}}]}}
"""


def write_suite(tmp_path: Path, name: str, b_expected: str) -> Path:
    path = tmp_path / name
    path.write_text(SUITE.format(b_expected=b_expected))
    return path


def test_missing_suite_file_exits_2(tmp_path: Path) -> None:
    result = runner.invoke(app, ["run", str(tmp_path / "missing.yaml")])
    assert result.exit_code == 2


def test_clean_run_exits_0_and_writes_report(tmp_path: Path) -> None:
    suite = write_suite(tmp_path, "suite.yaml", "WORLD")
    out, report = tmp_path / "out.jsonl", tmp_path / "report.md"
    result = runner.invoke(app, ["run", str(suite), "--out", str(out), "--report", str(report)])
    assert result.exit_code == 0, result.output
    assert report.read_text().startswith("# Eval report: cli-suite")
    assert len(out.read_text().splitlines()) == 2


def test_failures_without_baseline_exit_0(tmp_path: Path) -> None:
    suite = write_suite(tmp_path, "suite.yaml", "WRONG")
    result = runner.invoke(
        app,
        ["run", str(suite), "--out", str(tmp_path / "o.jsonl"), "--report", str(tmp_path / "r.md")],
    )
    assert result.exit_code == 0, result.output
    assert "b" in (tmp_path / "r.md").read_text()


def test_regression_against_baseline_exits_1(tmp_path: Path) -> None:
    good = write_suite(tmp_path, "good.yaml", "WORLD")
    baseline = tmp_path / "baseline.jsonl"
    first = runner.invoke(
        app, ["run", str(good), "--out", str(baseline), "--report", str(tmp_path / "r0.md")]
    )
    assert first.exit_code == 0, first.output

    bad = write_suite(tmp_path, "bad.yaml", "WRONG")
    report = tmp_path / "r1.md"
    result = runner.invoke(
        app,
        [
            "run",
            str(bad),
            "--out",
            str(tmp_path / "o1.jsonl"),
            "--report",
            str(report),
            "--baseline",
            str(baseline),
        ],
    )
    assert result.exit_code == 1
    assert "Regression" in report.read_text()


def test_missing_baseline_exits_2(tmp_path: Path) -> None:
    suite = write_suite(tmp_path, "suite.yaml", "WORLD")
    result = runner.invoke(
        app,
        [
            "run",
            str(suite),
            "--out",
            str(tmp_path / "o.jsonl"),
            "--report",
            str(tmp_path / "r.md"),
            "--baseline",
            str(tmp_path / "nope.jsonl"),
        ],
    )
    assert result.exit_code == 2
