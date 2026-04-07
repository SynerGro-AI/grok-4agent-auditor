"""Agent 3 — Enterprise Architecture Advisor.

Evaluates the architectural characteristics of the submitted code and
recommends enterprise-grade patterns, structures, and refactoring
strategies to reach production quality.
"""

from __future__ import annotations

import json
import logging
from typing import List, Optional

from pydantic import BaseModel, Field

from grok_auditor.core.client import GrokClient

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are Agent-3: a principal software architect with 20+ years of enterprise system design experience.
Your task is to evaluate the architecture of the provided source code and recommend improvements.

Respond ONLY with a valid JSON object matching this exact schema — no markdown fences, no prose:
{
  "current_pattern": "<detected architectural pattern, e.g. 'monolithic procedural', 'MVC', 'microservice'>",
  "maturity_level": "<prototype | development | production | enterprise>",
  "recommended_patterns": [
    {
      "pattern": "<pattern name>",
      "rationale": "<why this pattern applies here>",
      "implementation_hint": "<concrete first step>"
    }
  ],
  "scalability_concerns": ["<string>", ...],
  "observability_gaps": ["<string>", ...],
  "enterprise_checklist": [
    {"item": "<string>", "status": "<missing|partial|present>"}
  ],
  "recommended_tech_stack": {
    "language_version": "<string>",
    "frameworks": ["<string>", ...],
    "testing": ["<string>", ...],
    "ci_cd": ["<string>", ...],
    "observability": ["<string>", ...]
  },
  "summary": "<concise paragraph on the path from current state to enterprise-grade>"
}
"""


class PatternRecommendation(BaseModel):
    pattern: str
    rationale: str
    implementation_hint: str


class ChecklistItem(BaseModel):
    item: str
    status: str


class TechStack(BaseModel):
    language_version: Optional[str] = None
    frameworks: List[str] = Field(default_factory=list)
    testing: List[str] = Field(default_factory=list)
    ci_cd: List[str] = Field(default_factory=list)
    observability: List[str] = Field(default_factory=list)


class ArchitectureRecommendation(BaseModel):
    current_pattern: str
    maturity_level: str
    recommended_patterns: List[PatternRecommendation] = Field(default_factory=list)
    scalability_concerns: List[str] = Field(default_factory=list)
    observability_gaps: List[str] = Field(default_factory=list)
    enterprise_checklist: List[ChecklistItem] = Field(default_factory=list)
    recommended_tech_stack: Optional[TechStack] = None
    summary: str


class ArchitectAgent:
    """Agent-3: Enterprise Architecture Advisor."""

    name = "Architect"

    def __init__(self, client: GrokClient) -> None:
        self._client = client

    async def run(
        self, code: str, *, language: Optional[str] = None
    ) -> ArchitectureRecommendation:
        lang_hint = f"\nDetected/provided language: {language}" if language else ""
        user_message = (
            f"Evaluate the architecture of the following source code and recommend "
            f"enterprise improvements:{lang_hint}\n\n```\n{code}\n```"
        )

        logger.info("[%s] Analyzing architecture (%d chars)…", self.name, len(code))
        raw = await self._client.chat(_SYSTEM_PROMPT, user_message)

        try:
            data = json.loads(raw)
            return ArchitectureRecommendation(**data)
        except (json.JSONDecodeError, Exception) as exc:
            logger.warning("[%s] Failed to parse response: %s", self.name, exc)
            return ArchitectureRecommendation(
                current_pattern="unknown",
                maturity_level="unknown",
                recommended_patterns=[],
                scalability_concerns=[],
                observability_gaps=[],
                enterprise_checklist=[],
                summary=f"Architecture analysis could not be completed: {exc}",
            )
