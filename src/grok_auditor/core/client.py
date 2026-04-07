"""Async xAI / Grok API client with CUDA-aware device selection."""

from __future__ import annotations

import logging
from typing import Any, Optional

import openai

logger = logging.getLogger(__name__)

try:
    import torch

    _TORCH_AVAILABLE = True
except ImportError:  # pragma: no cover
    _TORCH_AVAILABLE = False


def resolve_device(requested: Optional[str] = None) -> str:
    """Return the best available PyTorch device string.

    Priority order: explicit *requested* > CUDA > MPS (Apple Silicon) > CPU.

    This is used by local pre-processing steps (tokenisation, embedding, etc.)
    that benefit from GPU acceleration before calling the Grok API.
    """
    if not _TORCH_AVAILABLE:
        return "cpu"

    if requested:
        return requested

    if torch.cuda.is_available():
        device = "cuda"
        props = torch.cuda.get_device_properties(0)
        logger.info(
            "CUDA device detected: %s (%.1f GB VRAM)",
            props.name,
            props.total_memory / 2**30,
        )
        return device

    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        logger.info("Apple MPS device detected.")
        return "mps"

    logger.info("No GPU found — falling back to CPU.")
    return "cpu"


class GrokClient:
    """Thin wrapper around the OpenAI-compatible xAI API client.

    The xAI Grok API is fully compatible with the OpenAI REST interface, so
    the official ``openai`` Python SDK is used with a custom ``base_url``.
    """

    def __init__(self, api_key: str, base_url: str, model: str, **defaults: Any) -> None:
        self._model = model
        self._defaults = defaults
        self._client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    async def chat(
        self,
        system_prompt: str,
        user_message: str,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        """Send a chat completion request and return the assistant message text."""
        params: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            **self._defaults,
        }
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        if temperature is not None:
            params["temperature"] = temperature

        logger.debug("Sending chat request to Grok model '%s'", self._model)
        response = await self._client.chat.completions.create(**params)
        content = response.choices[0].message.content or ""
        logger.debug("Received %d chars from Grok", len(content))
        return content

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.close()
