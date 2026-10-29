"""Synthetic support bot used by the example suite (fictional, deterministic)."""

import json
from typing import Any


def answer(question: str | dict[str, Any]) -> str:
    text = str(question).lower()
    if "refund" in text:
        return "Refunds are available within 30 days of purchase for the Acme Notes app."
    if "password" in text:
        return "Use the 'Forgot password' link on the sign-in page to reset your password."
    if "plan" in text:
        return json.dumps({"plans": ["free", "pro"], "currency": "USD"})
    return "Sorry, I can only help with refunds, passwords and plans."
