"""Configuration management for the Grok XAI auditor."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator

# Load .env from the project root (if present) without overriding real env vars.
load_dotenv(override=False)

_XAI_BASE_URL = "https://api.x.ai/v1"
_DEFAULT_MODEL = "grok-3"


class AuditorConfig(BaseModel):
    """Runtime configuration resolved from environment variables or explicit kwargs."""

    api_key: str = Field(
        default_factory=lambda: os.environ.get("XAI_API_KEY", ""),
        description="xAI API key — set via XAI_API_KEY env var or .env file.",
    )
    base_url: str = Field(
        default_factory=lambda: os.environ.get("XAI_BASE_URL", _XAI_BASE_URL),
        description="xAI API base URL.",
    )
    model: str = Field(
        default_factory=lambda: os.environ.get("GROK_MODEL", _DEFAULT_MODEL),
        description="Grok model identifier to use for all agents.",
    )
    max_tokens: int = Field(
        default_factory=lambda: int(os.environ.get("GROK_MAX_TOKENS", "4096")),
        ge=256,
        le=131072,
        description="Maximum tokens per agent response.",
    )
    temperature: float = Field(
        default_factory=lambda: float(os.environ.get("GROK_TEMPERATURE", "0.2")),
        ge=0.0,
        le=2.0,
        description="Sampling temperature for all agents.",
    )
    cuda_device: Optional[str] = Field(
        default_factory=lambda: os.environ.get("CUDA_DEVICE", None),
        description="PyTorch device string for CUDA acceleration (e.g. 'cuda:0'). "
        "When None the system auto-detects the best available device.",
    )
    output_dir: Path = Field(
        default_factory=lambda: Path(os.environ.get("AUDITOR_OUTPUT_DIR", "audit_output")),
        description="Directory where audit artefacts are written.",
    )

    @model_validator(mode="after")
    def _require_api_key(self) -> "AuditorConfig":
        if not self.api_key:
            raise ValueError(
                "XAI_API_KEY is required. "
                "Set it in your environment or in a .env file."
            )
        return self

    model_config = {"arbitrary_types_allowed": True}
