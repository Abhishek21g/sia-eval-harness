# SIA Eval Harness

Reproducible **run receipts** for [SIA](https://github.com/hexo-ai/sia) self-improvement runs — separating **harness gains**, **weight gains**, and **overfit/residue** without re-running evals.

Native product artifact (not a `sia web` clone). Read-only compiler over `runs/run_*` trees.

## Install

```bash
cd eval-harness
pip install -e ".[dev]"
```

## Usage

After a SIA run completes:

```bash
sia-eval compile runs/run_1
# → runs/run_1/receipts/run_1.json
# → runs/run_1/receipts/run_1.md
```

Custom output directory:

```bash
sia-eval compile runs/run_1 -o ./receipts
```

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

## Positioning

Complements upstream PRs [#36](https://github.com/hexo-ai/sia/pull/36) (leak fix), [#51](https://github.com/hexo-ai/sia/pull/51) (transfer evidence), and [#52](https://github.com/hexo-ai/sia/pull/52) (spaceship evaluator).

Built for [enaguthi.com](https://enaguthi.com) launch + Hexo Labs outreach.
