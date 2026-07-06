"""Tests for SIA Eval Harness."""

from __future__ import annotations

import json
from pathlib import Path

from sia_eval_harness.checks import gold_leak_check, metric_delta
from sia_eval_harness.compiler import compile_run, write_receipt

import pytest


def _write_run(tmp_path: Path) -> Path:
    run = tmp_path / "runs" / "run_1"
    g1 = run / "gen_1"
    g2 = run / "gen_2"
    g1.mkdir(parents=True)
    g2.mkdir(parents=True)
    (run / "context.md").write_text(
        "**Task**: longcot-chess\n**Meta Model**: haiku\n**Task Model**: haiku\n**Agent impl**: claude\n",
        encoding="utf-8",
    )
    (g1 / "target_agent.py").write_text("print('v1')\n", encoding="utf-8")
    (g2 / "target_agent.py").write_text("print('v2')\nprint('extra')\n", encoding="utf-8")
    (g1 / "results.json").write_text(
        json.dumps({"summary": {"accuracy": 0.5}, "items": []}),
        encoding="utf-8",
    )
    (g2 / "results.json").write_text(
        json.dumps({"summary": {"accuracy": 0.7}, "items": []}),
        encoding="utf-8",
    )
    (g2 / "transfer_evidence.json").write_text(
        json.dumps(
            {
                "accepted_for_reuse": True,
                "task_specific_residue": ["Hardcoded timeout for sample 17"],
                "unsupported_claims": [],
                "claim_boundary": "Task-local only",
            }
        ),
        encoding="utf-8",
    )
    return run


def test_gold_leak_check_fails_on_expected():
    result = gold_leak_check({"results": [{"expected": "secret"}]})
    assert result["status"] == "fail"
    assert "expected" in result["keys_found"]


def test_metric_delta_higher_is_better():
    prev = {"accuracy": 0.5}
    curr = {"summary": {"accuracy": 0.7}}
    out = metric_delta(prev, curr)
    assert out["delta"] == pytest.approx(0.2)


def test_compile_run_receipt(tmp_path):
    run = _write_run(tmp_path)
    receipt = compile_run(run)
    assert receipt["run_id"] == 1
    assert len(receipt["generations"]) == 2
    g2 = receipt["generations"][1]
    assert g2["focus"] == "harness"
    assert g2["gain_attribution"]["harness_delta"] == pytest.approx(0.2)
    assert g2["integrity"]["private_leak_check"]["status"] == "pass"
    assert g2["integrity"]["transfer_evidence"]["residue"]


def test_write_receipt_outputs(tmp_path):
    run = _write_run(tmp_path)
    json_path, md_path = write_receipt(run, run / "receipts")
    assert json_path.is_file()
    assert md_path.is_file()
    assert "harness" in md_path.read_text(encoding="utf-8")
