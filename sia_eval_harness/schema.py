"""Receipt schema for SIA Eval Harness."""

from __future__ import annotations

RECEIPT_VERSION = "0.1"

GOLD_LEAK_KEYS = frozenset(
    {
        "expected",
        "reference_answer",
        "answer_key",
        "gold",
        "correct_answer",
    }
)
