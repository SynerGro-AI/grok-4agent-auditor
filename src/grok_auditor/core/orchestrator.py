"""Orchestrator — coordinates the four specialised audit agents."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from grok_auditor.agents.analyzer import AnalyzerAgent, AnalysisResult
from grok_auditor.agents.architect import ArchitectAgent, ArchitectureRecommendation
from grok_auditor.agents.refactor import RefactorAgent, RefactorResult
from grok_auditor.agents.security import SecurityAgent, SecurityResult
from grok_auditor.core.client import GrokClient, resolve_device
from grok_auditor.core.config import AuditorConfig

logger = logging.getLogger(__name__)


class AuditReport(BaseModel):
    """Aggregated output from all four agents."""

    source_file: str = Field(description="Path or label of the audited source.")
    device_used: str = Field(description="PyTorch device used for local processing.")
    analysis: AnalysisResult
    security: SecurityResult
    architecture: ArchitectureRecommendation
    refactor: RefactorResult

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_json(self, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        logger.info("Audit report saved to %s", path)


class AuditOrchestrator:
    """Runs all four agents concurrently and returns a consolidated AuditReport."""

    def __init__(self, config: AuditorConfig) -> None:
        self._config = config
        self._device = resolve_device(config.cuda_device)
        self._client = GrokClient(
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
        )

        # Instantiate agents
        self._analyzer = AnalyzerAgent(self._client)
        self._security = SecurityAgent(self._client)
        self._architect = ArchitectAgent(self._client)
        self._refactor = RefactorAgent(self._client)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def audit_async(
        self,
        code: str,
        *,
        source_label: str = "<stdin>",
        language: Optional[str] = None,
    ) -> AuditReport:
        """Run all four agents concurrently and return a merged AuditReport."""
        logger.info("Starting 4-agent audit for '%s' on device '%s'", source_label, self._device)

        # Run all agents in parallel for maximum throughput
        analysis_task = asyncio.create_task(
            self._analyzer.run(code, language=language)
        )
        security_task = asyncio.create_task(
            self._security.run(code, language=language)
        )
        architect_task = asyncio.create_task(
            self._architect.run(code, language=language)
        )
        refactor_task = asyncio.create_task(
            self._refactor.run(code, language=language)
        )

        analysis, security, architecture, refactor = await asyncio.gather(
            analysis_task, security_task, architect_task, refactor_task
        )

        report = AuditReport(
            source_file=source_label,
            device_used=self._device,
            analysis=analysis,
            security=security,
            architecture=architecture,
            refactor=refactor,
        )
        logger.info("4-agent audit complete for '%s'", source_label)
        return report

    def audit(
        self,
        code: str,
        *,
        source_label: str = "<stdin>",
        language: Optional[str] = None,
    ) -> AuditReport:
        """Synchronous convenience wrapper around :meth:`audit_async`."""
        return asyncio.run(self.audit_async(code, source_label=source_label, language=language))

    async def close(self) -> None:
        await self._client.close()
