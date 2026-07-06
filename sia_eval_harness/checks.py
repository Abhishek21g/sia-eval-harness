"""Integrity and attribution checks over SIA run artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from sia_eval_harness.schema import GOLD_LEAK_KEYS

_GEN_RE = re.compile(r"^gen_(\d+)$")
_METRIC_KEYS = ("accuracy", "accuracy_percent", "score", "mse", "loss", "correct", "total")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _walk_strings(obj: Any, out: list[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str) and k.lower() in GOLD_LEAK_KEYS:
                out.append(k)
            _walk_strings(v, out)
    elif isinstance(obj, list):
        for item in obj:
            _walk_strings(item, out)


def gold_leak_check(results: dict[str, Any] | None) -> dict[str, Any]:
    """Detect answer-key fields in results.json (grader-side leak risk)."""
    if results is None:
        return {"status": "missing", "keys_found": [], "detail": "no results.json"}
    keys_found: list[str] = []
    _walk_strings(results, keys_found)
    if keys_found:
        return {
            "status": "fail",
            "keys_found": sorted(set(keys_found)),
            "detail": "held-out label keys present in results.json",
        }
    return {"status": "pass", "keys_found": [], "detail": "no gold-bearing keys detected"}


def detect_focus(gen_dir: Path) -> str:
    if (gen_dir / "train.py").is_file() or (gen_dir / "train_stdout.log").is_file():
        return "weights"
    return "harness"


def extract_primary_metric(results: dict[str, Any] | None) -> tuple[str | None, float | None]:
    if not results:
        return None, None

    def scan(block: dict[str, Any]) -> tuple[str | None, float | None]:
        for key in _METRIC_KEYS:
            if key in block and isinstance(block[key], (int, float)):
                return key, float(block[key])
        return None, None

    if "summary" in results and isinstance(results["summary"], dict):
        found = scan(results["summary"])
        if found[0]:
            return found
    return scan(results)


def metric_delta(
    prev: dict[str, Any] | None,
    curr: dict[str, Any] | None,
) -> dict[str, Any]:
    prev_key, prev_val = extract_primary_metric(prev)
    curr_key, curr_val = extract_primary_metric(curr)
    if curr_key is None or curr_val is None:
        return {"metric": None, "delta": None, "direction": "unknown"}
    delta = None
    if prev_val is not None and curr_key == prev_key:
        delta = curr_val - prev_val
    direction = "unknown"
    if delta is not None:
        if curr_key in ("loss", "mse"):
            direction = "lower_is_better"
        else:
            direction = "higher_is_better"
    return {
        "metric": curr_key,
        "previous": prev_val,
        "current": curr_val,
        "delta": delta,
        "direction": direction,
    }


def parse_context_header(context_md: Path) -> dict[str, str]:
    meta: dict[str, str] = {}
    if not context_md.is_file():
        return meta
    for line in context_md.read_text(encoding="utf-8").splitlines():
        if line.startswith("**") and ":**" in line:
            key, _, value = line.partition(":**")
            meta[key.strip("* ").strip()] = value.strip()
    return meta


def list_generations(run_dir: Path) -> list[tuple[int, Path]]:
    gens: list[tuple[int, Path]] = []
    for child in run_dir.iterdir():
        if child.is_dir():
            m = _GEN_RE.match(child.name)
            if m:
                gens.append((int(m.group(1)), child))
    return sorted(gens, key=lambda x: x[0])
