"""Integration-style tests for AuditOrchestrator (agents fully mocked)."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from grok_auditor.core.config import AuditorConfig
from grok_auditor.core.orchestrator import AuditOrchestrator, AuditReport

SAMPLE_CODE = "x = 1 + 1\nprint(x)\n"

_ANALYSIS = {
    "language": "python",
    "quality_score": 50,
    "complexity": "low",
    "lines_of_code": 2,
    "issues": [],
    "strengths": [],
    "summary": "Minimal script.",
}
_SECURITY = {
    "risk_level": "none",
    "cve_references": [],
    "vulnerabilities": [],
    "positive_security_practices": [],
    "summary": "No risks.",
}
_ARCH = {
    "current_pattern": "script",
    "maturity_level": "prototype",
    "recommended_patterns": [],
    "scalability_concerns": [],
    "observability_gaps": [],
    "enterprise_checklist": [],
    "recommended_tech_stack": None,
    "summary": "Needs structure.",
}
_REFACTOR = {
    "refactored_code": "RESULT: int = 1 + 1\n",
    "test_scaffold": "def test_result():\n    assert RESULT == 2\n",
    "changelog": [],
    "migration_notes": "No changes needed.",
    "estimated_quality_score": 70,
}


@pytest.fixture()
def config(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    return AuditorConfig()


@pytest.fixture()
def mock_grok_client():
    """Patch GrokClient so each agent gets pre-canned JSON responses."""

    responses = [json.dumps(r) for r in [_ANALYSIS, _SECURITY, _ARCH, _REFACTOR]]
    call_count = {"n": 0}

    async def _chat(system_prompt, user_message, **kwargs):
        idx = call_count["n"] % len(responses)
        call_count["n"] += 1
        return responses[idx]

    with patch("grok_auditor.core.orchestrator.GrokClient") as MockClient:
        instance = MagicMock()
        instance.chat = _chat
        instance.close = AsyncMock()
        MockClient.return_value = instance
        yield instance


@pytest.mark.asyncio
async def test_orchestrator_returns_audit_report(config, mock_grok_client):
    """AuditOrchestrator.audit_async returns a fully populated AuditReport."""
    orch = AuditOrchestrator(config)
    report = await orch.audit_async(SAMPLE_CODE, source_label="test.py", language="python")

    assert isinstance(report, AuditReport)
    assert report.source_file == "test.py"
    assert report.analysis.language == "python"
    assert report.security.risk_level == "none"
    assert report.architecture.current_pattern == "script"
    assert "RESULT" in report.refactor.refactored_code
    await orch.close()


@pytest.mark.asyncio
async def test_orchestrator_json_serialisation(config, mock_grok_client):
    """AuditReport can be serialised to JSON without errors."""
    orch = AuditOrchestrator(config)
    report = await orch.audit_async(SAMPLE_CODE)
    json_str = report.to_json()
    data = json.loads(json_str)
    assert "analysis" in data
    assert "security" in data
    assert "architecture" in data
    assert "refactor" in data
    await orch.close()


@pytest.mark.asyncio
async def test_orchestrator_save_report(tmp_path, config, mock_grok_client):
    """AuditReport.save writes a valid JSON file."""
    orch = AuditOrchestrator(config)
    report = await orch.audit_async(SAMPLE_CODE)
    out_file = tmp_path / "report.json"
    report.save(out_file)

    assert out_file.exists()
    data = json.loads(out_file.read_text())
    assert data["source_file"] == "<stdin>"
    await orch.close()
