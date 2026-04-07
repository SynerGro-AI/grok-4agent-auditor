"""Agent 1 — Code Analyzer.

Evaluates code quality, complexity, maintainability, design patterns,
and adherence to best practices.  Produces a structured AnalysisResult.
"""

from __future__ import annotations

import json
import logging
from typing import List, Optional

from pydantic import BaseModel, Field

from grok_auditor.core.client import GrokClient

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are Agent-1: an expert software engineering code analyzer.
Your task is to evaluate the provided source code and produce a thorough quality analysis.

Respond ONLY with a valid JSON object matching this exact schema — no markdown fences, no prose:
{
  "language": "<detected or provided language>",
  "quality_score": <integer 0-100>,
  "complexity": "<low | medium | high | very_high>",
  "lines_of_code": <integer>,
  "issues": [
    {"severity": "<info|warning|error|critical>", "category": "<string>", "description": "<string>", "line_hint": <int or null>}
  ],
  "strengths": ["<string>", ...],
  "summary": "<concise paragraph summarising the overall code quality>"
}
"""


class CodeIssue(BaseModel):
    severity: str = Field(description="info | warning | error | critical")
    category: str
    description: str
    line_hint: Optional[int] = None


class AnalysisResult(BaseModel):
    language: str
    quality_score: int = Field(ge=0, le=100)
    complexity: str
    lines_of_code: int
    issues: List[CodeIssue] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    summary: str


class AnalyzerAgent:
    """Agent-1: Code Quality Analyzer."""

    name = "Analyzer"

    def __init__(self, client: GrokClient) -> None:
        self._client = client

    async def run(self, code: str, *, language: Optional[str] = None) -> AnalysisResult:
        lang_hint = f"\nDetected/provided language: {language}" if language else ""
        user_message = f"Analyze the following source code:{lang_hint}\n\n```\n{code}\n```"

        logger.info("[%s] Analyzing code (%d chars)…", self.name, len(code))
        raw = await self._client.chat(_SYSTEM_PROMPT, user_message)

        try:
            data = json.loads(raw)
            return AnalysisResult(**data)
        except (json.JSONDecodeError, Exception) as exc:
            logger.warning("[%s] Failed to parse response: %s", self.name, exc)
            return AnalysisResult(
                language=language or "unknown",
                quality_score=0,
                complexity="unknown",
                lines_of_code=len(code.splitlines()),
                issues=[
                    CodeIssue(
                        severity="error",
                        category="parse_error",
                        description=f"Agent failed to produce structured output: {exc}",
                    )
                ],
                strengths=[],
                summary="Analysis could not be completed due to a response parsing error.",
            )
