"""Unit tests for GrokClient and resolve_device."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from grok_auditor.core.client import GrokClient, resolve_device


# ──────────────────────────────────────────────────────────────────────
# resolve_device
# ──────────────────────────────────────────────────────────────────────

def test_resolve_device_explicit():
    """An explicit device string is returned unchanged."""
    assert resolve_device("cuda:1") == "cuda:1"
    assert resolve_device("cpu") == "cpu"


def test_resolve_device_cuda(monkeypatch):
    """resolve_device returns 'cuda' when CUDA is available."""
    mock_props = MagicMock()
    mock_props.name = "RTX 4090"
    mock_props.total_memory = 24 * 2**30

    with patch("grok_auditor.core.client._TORCH_AVAILABLE", True), \
         patch("grok_auditor.core.client.torch") as mock_torch:
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.get_device_properties.return_value = mock_props
        result = resolve_device()

    assert result == "cuda"


def test_resolve_device_cpu_when_no_torch(monkeypatch):
    """resolve_device returns 'cpu' when torch is unavailable."""
    with patch("grok_auditor.core.client._TORCH_AVAILABLE", False):
        assert resolve_device() == "cpu"


def test_resolve_device_cpu_fallback(monkeypatch):
    """resolve_device returns 'cpu' when neither CUDA nor MPS is available."""
    with patch("grok_auditor.core.client._TORCH_AVAILABLE", True), \
         patch("grok_auditor.core.client.torch") as mock_torch:
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = False
        result = resolve_device()

    assert result == "cpu"


# ──────────────────────────────────────────────────────────────────────
# GrokClient
# ──────────────────────────────────────────────────────────────────────

@pytest.fixture()
def mock_openai_client():
    """Return a patched openai.AsyncOpenAI instance."""
    with patch("grok_auditor.core.client.openai.AsyncOpenAI") as MockClass:
        instance = MagicMock()
        MockClass.return_value = instance

        # Build a fake chat completion response
        choice = MagicMock()
        choice.message.content = '{"hello": "world"}'
        completion = MagicMock()
        completion.choices = [choice]

        instance.chat.completions.create = AsyncMock(return_value=completion)
        instance.close = AsyncMock()
        yield instance


@pytest.mark.asyncio
async def test_grok_client_chat_returns_content(mock_openai_client):
    """GrokClient.chat returns the assistant content string."""
    client = GrokClient(
        api_key="test",
        base_url="https://api.x.ai/v1",
        model="grok-3",
        max_tokens=512,
        temperature=0.2,
    )
    result = await client.chat("system prompt", "user message")
    assert result == '{"hello": "world"}'


@pytest.mark.asyncio
async def test_grok_client_chat_passes_overrides(mock_openai_client):
    """GrokClient.chat forwards max_tokens/temperature overrides."""
    client = GrokClient(
        api_key="test",
        base_url="https://api.x.ai/v1",
        model="grok-3",
    )
    await client.chat("sys", "usr", max_tokens=1024, temperature=0.7)

    call_kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["max_tokens"] == 1024
    assert call_kwargs["temperature"] == 0.7


@pytest.mark.asyncio
async def test_grok_client_close(mock_openai_client):
    """GrokClient.close calls the underlying client's close."""
    client = GrokClient(
        api_key="test",
        base_url="https://api.x.ai/v1",
        model="grok-3",
    )
    await client.close()
    mock_openai_client.close.assert_called_once()
