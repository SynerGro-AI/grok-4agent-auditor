"""Agent 4 — Enterprise Code Refactoring Generator.

Takes the original source code and produces a fully refactored,
enterprise-grade version with proper error handling, logging,
type annotations, documentation, tests scaffolding, and design patterns.
"""

from __future__ import annotations

import json
import logging
from typing import List, Optional

from pydantic import BaseModel, Field

from grok_auditor.core.client import GrokClient

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are Agent-4: a senior software engineer specialising in transforming prototype or basic code
into production-ready, enterprise-grade implementations.

Your task is to refactor the provided source code to enterprise standards, including:
- Full type annotations
- Comprehensive docstrings (Google-style)
- Structured logging (not print statements)
- Robust error handling with custom exception hierarchy
- Dependency injection / configuration separation
- Unit-testable design (no hard-coded globals)
- Compliance with SOLID principles

Respond ONLY with a valid JSON object matching this exact schema — no markdown fences, no prose:
{
  "refactored_code": "<complete refactored source code as a single escaped string>",
  "test_scaffold": "<pytest test file content as a single escaped string>",
  "changelog": [
    {"change": "<short description of a specific improvement made>"}
  ],
  "migration_notes": "<prose instructions for adopting the refactored version>",
  "estimated_quality_score": <integer 0-100>
}
"""


class ChangelogEntry(BaseModel):
    change: str


class RefactorResult(BaseModel):
    refactored_code: str
    test_scaffold: str
    changelog: List[ChangelogEntry] = Field(default_factory=list)
    migration_notes: str
    estimated_quality_score: int = Field(ge=0, le=100)


class RefactorAgent:
    """Agent-4: Enterprise Code Refactoring Generator."""

    name = "Refactor"

    def __init__(self, client: GrokClient) -> None:
        self._client = client

    async def run(self, code: str, *, language: Optional[str] = None) -> RefactorResult:
        lang_hint = f"\nDetected/provided language: {language}" if language else ""
        user_message = (
            f"Refactor the following source code to enterprise standards:{lang_hint}\n\n"
            f"```\n{code}\n```"
        )

        logger.info("[%s] Generating enterprise refactor (%d chars)…", self.name, len(code))
        raw = await self._client.chat(_SYSTEM_PROMPT, user_message)

        try:
            data = json.loads(raw)
            return RefactorResult(**data)
        except (json.JSONDecodeError, Exception) as exc:
            logger.warning("[%s] Failed to parse response: %s", self.name, exc)
            return RefactorResult(
                refactored_code=code,
                test_scaffold="# Refactoring agent encountered an error; test scaffold unavailable.",
                changelog=[],
                migration_notes=f"Refactoring could not be completed: {exc}",
                estimated_quality_score=0,
            )
