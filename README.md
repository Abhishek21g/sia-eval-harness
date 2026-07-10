# SIA Eval Harness

Reproducible **run receipts** for [SIA](https://github.com/hexo-ai/sia) self-improvement runs — separating **harness gains**, **weight gains**, and **overfit/residue** without re-running evals.

[![CI](https://github.com/Abhishek21g/sia-eval-harness/actions/workflows/ci.yml/badge.svg)](https://github.com/Abhishek21g/sia-eval-harness/actions/workflows/ci.yml)
[![Live demo](https://img.shields.io/badge/demo-enaguthi.com-2da44e)](https://enaguthi.com/hexo-sia-eval/site/)

**Repo:** https://github.com/Abhishek21g/sia-eval-harness  
**Demo:** https://enaguthi.com/hexo-sia-eval/site/

## Install

```bash
git clone https://github.com/Abhishek21g/sia-eval-harness.git
cd sia-eval-harness
pip install -e ".[dev]"
```

## Usage

After a SIA run completes:

```bash
sia-eval compile runs/run_1
# → runs/run_1/receipts/run_1.json
# → runs/run_1/receipts/run_1.md
```

Try the bundled demo (no SIA run required):

```bash
sia-eval compile demo/runs/run_1
```

## What it is

| Module | Role |
|--------|------|
| `cli.py` | `sia-eval compile` entrypoint |
| `compiler.py` | Walks `runs/run_*`, writes receipt JSON + markdown |
| `checks.py` | Leak guard, metric delta, harness vs weights detection |
| `schema.py` | Receipt version + gold-key constants |

## Receipt fields

| Section | Purpose |
|---------|---------|
| `gain_attribution` | `harness_delta` vs `weights_delta` from `--focus` mode + metric Δ |
| `integrity.private_leak_check` | Detects gold-label keys in `results.json` |
| `integrity.transfer_evidence` | Surfaces `transfer_evidence.json` residue / unsupported claims |
| `artifacts_hash` | SHA-256 of key generation artifacts |

## Test

```bash
pytest tests/ -q
```

## Related OSS work

Built alongside contributions to [hexo-ai/sia](https://github.com/hexo-ai/sia): [#36](https://github.com/hexo-ai/sia/pull/36), [#41](https://github.com/hexo-ai/sia/pull/41), [#51](https://github.com/hexo-ai/sia/pull/51), [#52](https://github.com/hexo-ai/sia/pull/52).

Built by [Abhishek Enaguthi](https://enaguthi.com).
