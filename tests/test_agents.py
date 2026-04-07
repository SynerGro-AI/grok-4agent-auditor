"""Unit tests for the four specialised agents."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from grok_auditor.agents.analyzer import AnalyzerAgent, AnalysisResult
from grok_auditor.agents.security import SecurityAgent, SecurityResult
from grok_auditor.agents.architect import ArchitectAgent, ArchitectureRecommendation
from grok_auditor.agents.refactor import RefactorAgent, RefactorResult

# ── Fixtures ──────────────────────────────────────────────────────────

SAMPLE_CODE = """\
def add(a, b):
    return a + b

result = add(1, 2)
print(result)
"""


def make_client(response_json: dict) -> MagicMock:
    """Return a mock GrokClient whose chat() returns the given JSON string."""
    client = MagicMock()
    client.chat = AsyncMock(return_value=json.dumps(response_json))
    return client


# ── Agent 1: Analyzer ─────────────────────────────────────────────────

_ANALYSIS_RESPONSE = {
    "language": "python",
    "quality_score": 65,
    "complexity": "low",
    "lines_of_code": 5,
    "issues": [
        {"severity": "warning", "category": "naming", "description": "Variable 'result' is generic.", "line_hint": 4}
    ],
    "strengths": ["Simple and readable"],
    "summary": "Very simple script, lacks enterprise structure.",
}


@pytest.mark.asyncio
async def test_analyzer_agent_success():
    client = make_client(_ANALYSIS_RESPONSE)
    agent = AnalyzerAgent(client)
    result = await agent.run(SAMPLE_CODE, language="python")

    assert isinstance(result, AnalysisResult)
    assert result.language == "python"
    assert result.quality_score == 65
    assert result.complexity == "low"
    assert len(result.issues) == 1
    assert result.issues[0].severity == "warning"


@pytest.mark.asyncio
async def test_analyzer_agent_graceful_fallback():
    """AnalyzerAgent returns a safe fallback when JSON is malformed."""
    client = MagicMock()
    client.chat = AsyncMock(return_value="NOT JSON")
    agent = AnalyzerAgent(client)
    result = await agent.run(SAMPLE_CODE)

    assert isinstance(result, AnalysisResult)
    assert result.quality_score == 0
    assert any(i.category == "parse_error" for i in result.issues)


# ── Agent 2: Security ─────────────────────────────────────────────────

_SECURITY_RESPONSE = {
    "risk_level": "low",
    "cve_references": [],
    "vulnerabilities": [],
    "positive_security_practices": ["No external inputs"],
    "summary": "No significant security issues found.",
}


@pytest.mark.asyncio
async def test_security_agent_success():
    client = make_client(_SECURITY_RESPONSE)
    agent = SecurityAgent(client)
    result = await agent.run(SAMPLE_CODE)

    assert isinstance(result, SecurityResult)
    assert result.risk_level == "low"
    assert len(result.vulnerabilities) == 0


@pytest.mark.asyncio
async def test_security_agent_graceful_fallback():
    client = MagicMock()
    client.chat = AsyncMock(return_value="INVALID")
    agent = SecurityAgent(client)
    result = await agent.run(SAMPLE_CODE)

    assert isinstance(result, SecurityResult)
    assert result.risk_level == "unknown"


# ── Agent 3: Architect ────────────────────────────────────────────────

_ARCH_RESPONSE = {
    "current_pattern": "monolithic procedural",
    "maturity_level": "prototype",
    "recommended_patterns": [
        {"pattern": "Clean Architecture", "rationale": "Separation of concerns", "implementation_hint": "Add layers"}
    ],
    "scalability_concerns": ["Single-threaded"],
    "observability_gaps": ["No logging"],
    "enterprise_checklist": [{"item": "Error handling", "status": "missing"}],
    "recommended_tech_stack": {
        "language_version": "Python 3.12",
        "frameworks": ["FastAPI"],
        "testing": ["pytest"],
        "ci_cd": ["GitHub Actions"],
        "observability": ["OpenTelemetry"],
    },
    "summary": "Transform to layered architecture.",
}


@pytest.mark.asyncio
async def test_architect_agent_success():
    client = make_client(_ARCH_RESPONSE)
    agent = ArchitectAgent(client)
    result = await agent.run(SAMPLE_CODE)

    assert isinstance(result, ArchitectureRecommendation)
    assert result.current_pattern == "monolithic procedural"
    assert result.maturity_level == "prototype"
    assert len(result.recommended_patterns) == 1


@pytest.mark.asyncio
async def test_architect_agent_graceful_fallback():
    client = MagicMock()
    client.chat = AsyncMock(return_value="BAD")
    agent = ArchitectAgent(client)
    result = await agent.run(SAMPLE_CODE)

    assert isinstance(result, ArchitectureRecommendation)
    assert result.current_pattern == "unknown"


# ── Agent 4: Refactor ─────────────────────────────────────────────────

_REFACTOR_RESPONSE = {
    "refactored_code": "def add(a: int, b: int) -> int:\n    return a + b\n",
    "test_scaffold": "def test_add():\n    assert add(1, 2) == 3\n",
    "changelog": [{"change": "Added type annotations"}],
    "migration_notes": "Replace print with logging.",
    "estimated_quality_score": 88,
}


@pytest.mark.asyncio
async def test_refactor_agent_success():
    client = make_client(_REFACTOR_RESPONSE)
    agent = RefactorAgent(client)
    result = await agent.run(SAMPLE_CODE, language="python")

    assert isinstance(result, RefactorResult)
    assert "def add" in result.refactored_code
    assert result.estimated_quality_score == 88
    assert len(result.changelog) == 1


@pytest.mark.asyncio
async def test_refactor_agent_graceful_fallback():
    client = MagicMock()
    client.chat = AsyncMock(return_value="NOT_JSON")
    agent = RefactorAgent(client)
    result = await agent.run(SAMPLE_CODE)

    assert isinstance(result, RefactorResult)
    assert result.refactored_code == SAMPLE_CODE
    assert result.estimated_quality_score == 0
