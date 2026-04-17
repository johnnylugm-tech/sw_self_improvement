---
name: software-self-improvement
description: |
  Auto-run quality improvement loops on any codebase. Inspired by karpathy/autoresearch.
  Use when: (1) Improving code quality in a GitHub repo or local folder, (2) Running quality gates (linting, type safety, test coverage, security, performance, architecture, readability, error handling, documentation), (3) Setting up CI/CD quality bar, or (4) Quantifying technical debt.
  Trigger phrases: "auto-improve code quality", "self-improve this repo", "run quality rounds", "raise the codebase to 85/90".
---

# Software Self-Improvement

Auto-run quality improvement loops on any codebase. 9-dimension quality model.

## CLI Commands

### Direct execution:
```bash
# Basic - current folder, 3 rounds
python3 /app/openclaw/skills/software-self-improvement/run.py --target ./api --rounds 3

# Custom targets
python3 /app/openclaw/skills/software-self-improvement/run.py --target ./api --rounds 5 --overall-target 90

# With config file
python3 /app/openclaw/skills/software-self-improvement/run.py --config ./quality.yaml
```

### OpenClaw trigger (natural language):
> "Auto-improve code quality in ./api, target 90."
> "Self-improve this repo."
> "Run quality rounds on the ./services folder — 5 rounds, security ≥ 95."

## Configuration (quality.yaml)

```yaml
target:
  type: folder            # folder | github
  location: "./"          # absolute/relative folder path
rounds: 3                 # hard cap
overall_target: 85        # overall weighted score (1–100)
dimension_target: 85      # per-dimension target
early_stop:
  enabled: true
git:
  commit_per_round: true
  branch: "quality/auto-research"
  push: false
dimensions:
  linting:
    enabled: true
    weight: 0.10
  type_safety:
    enabled: true
    weight: 0.15
  test_coverage:
    enabled: true
    weight: 0.20
  security:
    enabled: true
    weight: 0.15
  performance:
    enabled: true
    weight: 0.10
  architecture:
    enabled: true
    weight: 0.10
  readability:
    enabled: true
    weight: 0.10
  error_handling:
    enabled: true
    weight: 0.05
  documentation:
    enabled: true
    weight: 0.05
```

## 9 Quality Dimensions

| Dimension | Weight | Description | Tools |
|-----------|--------|-------------|-------|
| Test Coverage | 20% | Unit test coverage | pytest-cov, jest |
| Type Safety | 15% | Type hints, strict typing | mypy, tsc |
| Security | 15% | Vulnerability scanning | bandit, semgrep |
| Linting | 10% | Code style | ruff, eslint |
| Performance | 10% | Algorithmic efficiency | radon-cc |
| Architecture | 10% | Design patterns, SOLID | LLM judge |
| Readability | 10% | Code clarity | radon-mi |
| Error Handling | 5% | Exception handling | LLM judge |
| Documentation | 5% | Docstrings | interrogate |

## Outputs

Creates `reports/` directory:
```
reports/
├── round_1.md / round_1.json
├── round_2.md / round_2.json
├── round_3.md / round_3.json
└── FINAL.md   ← trajectory summary
```

## How It Works

```
┌─────────────────────────────────────┐
│  Round 1..N                          │
│  ┌─────────┐ ┌─────────┐ ┌────────┐ │
│  │Evaluate│ │ Score  │ │Improve│ │
│  │(LLM)   │ │(calc)  │ │(LLM)  │ │
│  └─────────┘ └─────────┘ └────────┘ │
└─────────────────────────────��───────┘
Evaluate → Score → Early-stop? → Improve → Verify → Commit
```

## Execution Flow

1. **Load config** - quality.yaml or defaults
2. **Setup target** - clone GitHub or verify folder
3. **For each round**:
   - Evaluate 9 dimensions (LLM + tools)
   - Score each 0-100
   - Check early-stop condition
   - If fail: LLM generates fixes
   - Verify with re-run tools
   - Commit if enabled
4. **Final report** - INITIAL.md with trajectories

## CLI Reference

| Flag | Default | Description |
|------|---------|-------------|
| `--target` | `./` | Target folder/GitHub URL |
| `--rounds` | 3 | Number of rounds |
| `--overall-target` | 85 | Overall score target |
| `--dimension-target` | 85 | Per-dimension target |
| `--config` | - | Path to quality.yaml |
| `--early-stop` | on | Stop when targets met |
| `--push` | off | Push commits |

## Dependencies

```bash
pip install pyyaml
# Optional tools (auto-detected):
pip install ruff bandit mypy pytest-cov radon-cc interrogate
```

---

**Status**: Ready for use in OpenClaw 🚀