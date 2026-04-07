# grok-4agent-auditor

**Grok XAI 4-Agent Code Project Auditor** — transforms basic or prototype code into
enterprise-grade software using four specialised AI agents powered by
[xAI Grok](https://x.ai/) (with optional CUDA/GPU acceleration for local
pre-processing steps).

---

## Overview

The auditor orchestrates **four concurrent agents**, each focused on a distinct
quality dimension:

| # | Agent | Role |
|---|-------|------|
| 1 | **Analyzer** | Code quality, complexity, design-pattern detection, issue listing |
| 2 | **Security** | OWASP Top-10 vulnerability scan, CVE references, remediation advice |
| 3 | **Architect** | Enterprise-pattern recommendations, scalability/observability gaps, tech-stack upgrade path |
| 4 | **Refactor** | Fully refactored enterprise-grade source, pytest scaffold, migration notes |

All four agents run **in parallel** against the xAI Grok API, giving you a
comprehensive audit in a single pass.

---

## Requirements

| Requirement | Version |
|-------------|---------|
| Python | ≥ 3.10 |
| xAI API key | [x.ai/api](https://x.ai/api) |
| CUDA (optional) | any CUDA-capable GPU |

---

## Installation

```bash
# Clone
git clone https://github.com/SynerGro-AI/grok-4agent-auditor.git
cd grok-4agent-auditor

# Install (CPU-only — PyTorch CPU wheel is pulled automatically)
pip install -e .

# Or install with dev/test extras
pip install -e ".[dev]"
```

### Environment variables

Create a `.env` file in the project root (never commit this file):

```dotenv
XAI_API_KEY=your_xai_api_key_here

# Optional overrides
GROK_MODEL=grok-3            # default: grok-3
GROK_MAX_TOKENS=4096          # default: 4096
GROK_TEMPERATURE=0.2          # default: 0.2
CUDA_DEVICE=cuda:0            # default: auto-detect
AUDITOR_OUTPUT_DIR=audit_output
```

---

## Usage

### CLI

```bash
# Audit a Python file — prints rich summary to terminal
grok-auditor audit my_script.py

# Specify language hint
grok-auditor audit app.js --language javascript

# Save full JSON report + refactored code + test scaffold to explicit paths
grok-auditor audit legacy_module.py \
    --output reports/report.json \
    --save-refactor reports/refactored.py \
    --save-tests   reports/test_refactored.py

# Or use --auto-save to write all outputs to AUDITOR_OUTPUT_DIR (default: audit_output/)
grok-auditor audit legacy_module.py --auto-save

# Read from stdin (pipe)
cat my_code.py | grok-auditor audit

# Override model for this run
grok-auditor audit app.py --model grok-3-turbo

# Verbose / debug logging
grok-auditor audit app.py --verbose
```

### Python API

```python
import asyncio
from grok_auditor import AuditorConfig, AuditOrchestrator

config = AuditorConfig(api_key="xai-…")
orch   = AuditOrchestrator(config)

code = open("my_script.py").read()

# Async (recommended)
report = asyncio.run(orch.audit_async(code, source_label="my_script.py", language="python"))

# Or synchronous convenience wrapper
report = orch.audit(code)

print(report.analysis.quality_score)        # 0-100
print(report.security.risk_level)           # none/low/medium/high/critical
print(report.architecture.current_pattern)
print(report.refactor.refactored_code)

# Save full JSON
report.save("audit_output/report.json")
```

---

## Project structure

```
src/
└── grok_auditor/
    ├── __init__.py
    ├── cli.py                   # Typer CLI entry-point
    ├── core/
    │   ├── client.py            # xAI/Grok API client + CUDA device resolution
    │   ├── config.py            # Pydantic config (env-var & kwarg driven)
    │   └── orchestrator.py      # Runs all 4 agents concurrently
    └── agents/
        ├── analyzer.py          # Agent 1 — code quality
        ├── security.py          # Agent 2 — security audit
        ├── architect.py         # Agent 3 — architecture advisor
        └── refactor.py          # Agent 4 — enterprise refactor generator
tests/
    ├── test_config.py
    ├── test_client.py
    ├── test_agents.py
    └── test_orchestrator.py
```

---

## CUDA / GPU acceleration

When `torch` detects a CUDA-capable GPU the orchestrator uses it for any local
pre-processing (tokenisation, embedding distance, etc.).  The Grok API calls
themselves are remote — CUDA only speeds up local work.

Device priority: `CUDA_DEVICE` env var → CUDA auto-detect → Apple MPS → CPU.

---

## Running tests

```bash
pytest tests/ -v
```

---

## License

[MIT](LICENSE)
