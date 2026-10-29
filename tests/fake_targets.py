"""Importable targets used by the CLI tests (synthetic, deterministic)."""

from typing import Any


def upper(text: str | dict[str, Any]) -> str:
    return str(text).upper()
