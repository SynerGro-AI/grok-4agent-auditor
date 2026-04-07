"""Agent 2 — Security Auditor.

Scans source code for security vulnerabilities including OWASP Top-10
categories, injection flaws, hardcoded secrets, insecure dependencies,
and unsafe cryptographic practices.
"""

from __future__ import annotations

import json
import logging
from typing import List, Optional

from pydantic import BaseModel, Field

from grok_auditor.core.client import GrokClient

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are Agent-2: an expert application security engineer and penetration tester.
Your task is to audit the provided source code for security vulnerabilities.

Respond ONLY with a valid JSON object matching this exact schema — no markdown fences, no prose:
{
  "risk_level": "<none | low | medium | high | critical>",
  "cve_references": ["<CVE-YYYY-NNNNN>", ...],
  "vulnerabilities": [
    {
      "id": "<short unique id, e.g. SEC-001>",
      "owasp_category": "<e.g. A03:2021 – Injection>",
      "severity": "<info|low|medium|high|critical>",
      "title": "<short title>",
      "description": "<detailed description>",
      "line_hint": <int or null>,
      "remediation": "<concrete fix or best-practice guidance>"
    }
  ],
  "positive_security_practices": ["<string>", ...],
  "summary": "<concise paragraph summarising overall security posture>"
}
"""


class Vulnerability(BaseModel):
    id: str
    owasp_category: Optional[str] = None
    severity: str
    title: str
    description: str
    line_hint: Optional[int] = None
    remediation: str


class SecurityResult(BaseModel):
    risk_level: str
    cve_references: List[str] = Field(default_factory=list)
    vulnerabilities: List[Vulnerability] = Field(default_factory=list)
    positive_security_practices: List[str] = Field(default_factory=list)
    summary: str


class SecurityAgent:
    """Agent-2: Security Vulnerability Auditor."""

    name = "Security"

    def __init__(self, client: GrokClient) -> None:
        self._client = client

    async def run(self, code: str, *, language: Optional[str] = None) -> SecurityResult:
        lang_hint = f"\nDetected/provided language: {language}" if language else ""
        user_message = f"Audit the following source code for security vulnerabilities:{lang_hint}\n\n```\n{code}\n```"

        logger.info("[%s] Auditing security (%d chars)…", self.name, len(code))
        raw = await self._client.chat(_SYSTEM_PROMPT, user_message)

        try:
            data = json.loads(raw)
            return SecurityResult(**data)
        except (json.JSONDecodeError, Exception) as exc:
            logger.warning("[%s] Failed to parse response: %s", self.name, exc)
            return SecurityResult(
                risk_level="unknown",
                vulnerabilities=[],
                positive_security_practices=[],
                summary=f"Security audit could not be completed: {exc}",
            )
