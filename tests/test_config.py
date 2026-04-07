"""Unit tests for AuditorConfig."""

import os
import pytest
from pydantic import ValidationError

from grok_auditor.core.config import AuditorConfig


def test_config_requires_api_key(monkeypatch):
    """AuditorConfig must raise if XAI_API_KEY is not set."""
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    with pytest.raises(ValidationError, match="XAI_API_KEY is required"):
        AuditorConfig()


def test_config_reads_from_env(monkeypatch):
    """AuditorConfig reads values from environment variables."""
    monkeypatch.setenv("XAI_API_KEY", "test-key-123")
    monkeypatch.setenv("GROK_MODEL", "grok-3-turbo")
    monkeypatch.setenv("GROK_MAX_TOKENS", "2048")
    monkeypatch.setenv("GROK_TEMPERATURE", "0.5")

    config = AuditorConfig()
    assert config.api_key == "test-key-123"
    assert config.model == "grok-3-turbo"
    assert config.max_tokens == 2048
    assert config.temperature == 0.5


def test_config_explicit_kwargs_override_env(monkeypatch):
    """Explicit constructor arguments take precedence over env vars."""
    monkeypatch.setenv("XAI_API_KEY", "env-key")
    monkeypatch.setenv("GROK_MODEL", "grok-3")

    config = AuditorConfig(api_key="explicit-key", model="grok-3-mini")
    assert config.api_key == "explicit-key"
    assert config.model == "grok-3-mini"


def test_config_max_tokens_bounds(monkeypatch):
    """max_tokens outside [256, 131072] must raise."""
    monkeypatch.setenv("XAI_API_KEY", "k")
    with pytest.raises(ValidationError):
        AuditorConfig(max_tokens=100)
    with pytest.raises(ValidationError):
        AuditorConfig(max_tokens=999999)


def test_config_temperature_bounds(monkeypatch):
    """temperature outside [0, 2] must raise."""
    monkeypatch.setenv("XAI_API_KEY", "k")
    with pytest.raises(ValidationError):
        AuditorConfig(temperature=-0.1)
    with pytest.raises(ValidationError):
        AuditorConfig(temperature=2.1)
