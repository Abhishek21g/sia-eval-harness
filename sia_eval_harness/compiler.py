"""Compile SIA run directories into reproducible receipts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sia_eval_harness.checks import (
    detect_focus,
    gold_leak_check,
    list_generations,
    load_json,
    metric_delta,
    parse_context_header,
    sha256_file,
)
from sia_eval_harness.schema import RECEIPT_VERSION

ARTIFACTS = (
    "target_agent.py",
    "train.py",
    "results.json",
    "improvement.md",
    "transfer_evidence.json",
    "agent_execution.json",
)


def _artifact_hashes(gen_dir: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for name in ARTIFACTS:
        path = gen_dir / name
        if path.is_file():
            out[name] = sha256_file(path)
    return out


def _code_delta_lines(prev: Path | None, curr: Path) -> dict[str, Any]:
    agent = curr / "target_agent.py"
    if not agent.is_file():
        agent = curr / "train.py"
    if not agent.is_file():
        return {"lines_added": None, "lines_removed": None, "agent_file": None}
    curr_lines = agent.read_text(encoding="utf-8").splitlines()
    if prev is None:
        return {"lines_added": len(curr_lines), "lines_removed": 0, "agent_file": agent.name}
    prev_agent = prev / "target_agent.py"
    if not prev_agent.is_file():
        prev_agent = prev / "train.py"
    if not prev_agent.is_file():
        return {"lines_added": len(curr_lines), "lines_removed": 0, "agent_file": agent.name}
    prev_lines = prev_agent.read_text(encoding="utf-8").splitlines()
    return {
        "lines_added": max(0, len(curr_lines) - len(prev_lines)),
        "lines_removed": max(0, len(prev_lines) - len(curr_lines)),
        "agent_file": agent.name,
    }


def compile_generation(
    run_dir: Path,
    gen_num: int,
    gen_dir: Path,
    prev_gen_dir: Path | None,
    run_meta: dict[str, str],
) -> dict[str, Any]:
    results = load_json(gen_dir / "results.json")
    prev_results = load_json(prev_gen_dir / "results.json") if prev_gen_dir else None
    transfer = load_json(gen_dir / "transfer_evidence.json")
    focus = detect_focus(gen_dir)
    delta = metric_delta(prev_results, results)
    leak = gold_leak_check(results)

    gain_attribution: dict[str, Any] = {
        "focus": focus,
        "metric_delta": delta,
        "code_change": _code_delta_lines(prev_gen_dir, gen_dir),
    }
    if focus == "harness":
        gain_attribution["harness_delta"] = delta.get("delta")
        gain_attribution["weights_delta"] = None
    else:
        gain_attribution["harness_delta"] = None
        gain_attribution["weights_delta"] = delta.get("delta")

    overfit: dict[str, Any] = {"status": "unknown", "residue": [], "unsupported_claims": []}
    if transfer:
        overfit = {
            "status": "present",
            "accepted_for_reuse": transfer.get("accepted_for_reuse"),
            "residue": transfer.get("task_specific_residue") or transfer.get("residue_bullets") or [],
            "unsupported_claims": transfer.get("unsupported_claims") or [],
            "claim_boundary": transfer.get("claim_boundary"),
        }
    elif (gen_dir / "improvement.md").is_file():
        overfit["status"] = "improvement_md_only"

    return {
        "generation": gen_num,
        "focus": focus,
        "metrics": results.get("summary", results) if results else {},
        "gain_attribution": gain_attribution,
        "integrity": {
            "private_leak_check": leak,
            "transfer_evidence": overfit,
        },
        "artifacts_hash": _artifact_hashes(gen_dir),
    }


def compile_run(run_dir: Path) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    run_name = run_dir.name
    run_id = int(run_name.split("_", 1)[1]) if "_" in run_name else 0
    context_meta = parse_context_header(run_dir / "context.md")
    generations = list_generations(run_dir)

    gen_receipts: list[dict[str, Any]] = []
    prev_dir: Path | None = None
    for gen_num, gen_dir in generations:
        gen_receipts.append(compile_generation(run_dir, gen_num, gen_dir, prev_dir, context_meta))
        prev_dir = gen_dir

    return {
        "receipt_version": RECEIPT_VERSION,
        "compiled_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "run_dir": str(run_dir),
        "task": context_meta.get("Task", "unknown"),
        "meta_model": context_meta.get("Meta Model"),
        "task_model": context_meta.get("Task Model"),
        "agent_impl": context_meta.get("Agent impl"),
        "generations": gen_receipts,
        "summary": {
            "generation_count": len(gen_receipts),
            "leak_failures": sum(
                1 for g in gen_receipts if g["integrity"]["private_leak_check"]["status"] == "fail"
            ),
            "best_metric": _best_metric(gen_receipts),
        },
    }


def _best_metric(gen_receipts: list[dict[str, Any]]) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    for g in gen_receipts:
        delta = g["gain_attribution"]["metric_delta"]
        if delta.get("current") is None:
            continue
        if best is None or (delta.get("current") or 0) > (best.get("value") or 0):
            best = {
                "generation": g["generation"],
                "metric": delta.get("metric"),
                "value": delta.get("current"),
            }
    return best


def render_markdown(receipt: dict[str, Any]) -> str:
    lines = [
        f"# SIA Run Receipt — run_{receipt['run_id']}",
        "",
        f"**Compiled:** {receipt['compiled_at']}",
        f"**Task:** {receipt['task']}",
        f"**Generations:** {receipt['summary']['generation_count']}",
        "",
        "## Generation summary",
        "",
        "| Gen | Focus | Metric Δ | Leak check | Overfit signal |",
        "|-----|-------|----------|------------|----------------|",
    ]
    for g in receipt["generations"]:
        delta = g["gain_attribution"]["metric_delta"]
        d_str = "—"
        if delta.get("delta") is not None:
            d_str = f"{delta.get('metric')} {delta['delta']:+.4f}"
        leak = g["integrity"]["private_leak_check"]["status"]
        overfit = g["integrity"]["transfer_evidence"]["status"]
        lines.append(f"| {g['generation']} | {g['focus']} | {d_str} | {leak} | {overfit} |")

    if receipt["summary"]["leak_failures"]:
        lines.extend(
            [
                "",
                "> **Warning:** One or more generations have gold-label keys in `results.json`.",
            ]
        )
    return "\n".join(lines) + "\n"


def write_receipt(run_dir: Path, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    receipt = compile_run(run_dir)
    run_id = receipt["run_id"]
    json_path = out_dir / f"run_{run_id}.json"
    md_path = out_dir / f"run_{run_id}.md"
    json_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(receipt), encoding="utf-8")
    return json_path, md_path
