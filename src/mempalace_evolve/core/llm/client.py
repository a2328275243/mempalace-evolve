"""LLM client abstraction for the MemPalace pipeline.

Provides:
  - LLMClient: wraps OpenAI-compatible API endpoints
  - Auto-fallback to no-op when no API key is configured
  - Structured output via Pydantic model validation
  - Configurable model, temperature, timeout
  - Usage tracking / cost estimation

Supports any OpenAI-compatible API including:
  - OpenAI
  - Azure OpenAI
  - Anthropic (via proxy)
  - Local models (Ollama, vLLM, etc.)
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from pydantic import BaseModel, ValidationError

logger = logging.getLogger("mempalace.llm")


# ── Configuration ─────────────────────────────────────────────────────

@dataclass
class LLMConfig:
    """Configuration for the LLM client."""
    api_key: str | None = None
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    temperature: float = 0.1
    max_tokens: int = 4096
    timeout_ms: int = 30_000
    max_retries: int = 2

    @classmethod
    def from_env(cls) -> LLMConfig:
        """Build config from environment variables."""
        return cls(
            api_key=os.environ.get("OPENAI_API_KEY")
                     or os.environ.get("LLM_API_KEY"),
            base_url=os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1"),
            model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
            temperature=float(os.environ.get("LLM_TEMPERATURE", "0.1")),
            max_tokens=int(os.environ.get("LLM_MAX_TOKENS", "4096")),
            timeout_ms=int(os.environ.get("LLM_TIMEOUT_MS", "30000")),
            max_retries=int(os.environ.get("LLM_MAX_RETRIES", "2")),
        )


# ── Usage tracking ────────────────────────────────────────────────────

@dataclass
class LLMUsage:
    """Tracks LLM API usage for cost estimation."""
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_calls: int = 0
    total_duration_ms: int = 0

    def add(self, prompt_tokens: int, completion_tokens: int, duration_ms: int) -> None:
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_calls += 1
        self.total_duration_ms += duration_ms

    def estimated_cost_usd(self, model: str = "gpt-4o-mini") -> float:
        """Rough cost estimate based on model pricing."""
        rates = {
            "gpt-4o-mini": (0.15, 0.60),   # per 1M tokens
            "gpt-4o": (2.50, 10.00),
            "gpt-4": (30.00, 60.00),
        }
        prompt_rate, completion_rate = rates.get(model, (1.00, 2.00))
        return (
            self.total_prompt_tokens / 1_000_000 * prompt_rate +
            self.total_completion_tokens / 1_000_000 * completion_rate
        )


# ── LLM Client ────────────────────────────────────────────────────────

class LLMClient:
    """Lightweight OpenAI-compatible LLM client.

    Usage:
        client = LLMClient()
        result = client.generate_structured(
            system_prompt="...",
            prompt="...",
            response_model=MyModel,
        )
    """

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig.from_env()
        self.usage = LLMUsage()
        self._available: bool | None = None  # lazy-check

    @property
    def available(self) -> bool:
        """Check if the LLM client has credentials configured."""
        if self._available is not None:
            return self._available
        key = self.config.api_key or os.environ.get("OPENAI_API_KEY")
        self._available = bool(key)
        return self._available

    def generate_structured(
        self,
        system_prompt: str,
        prompt: str,
        response_model: type[BaseModel],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> BaseModel | None:
        """Send a prompt and parse the response into a Pydantic model.

        Returns:
            Parsed model instance, or None on failure.
        """
        import httpx

        if not self.available:
            logger.debug("LLM not available — skipping structured generation.")
            return None

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }

        body = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature if temperature is not None else self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "response_format": {"type": "json_object"},
        }

        start = time.time()
        last_error: str | None = None

        for attempt in range(1 + self.config.max_retries):
            try:
                resp = httpx.post(
                    f"{self.config.base_url}/chat/completions",
                    headers=headers,
                    json=body,
                    timeout=self.config.timeout_ms / 1000,
                )
                resp.raise_for_status()
                data = resp.json()

                # Track usage
                usage = data.get("usage", {})
                self.usage.add(
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    duration_ms=int((time.time() - start) * 1000),
                )

                raw = data["choices"][0]["message"]["content"]
                return self._parse_json(raw, response_model)

            except (httpx.HTTPStatusError, httpx.RequestError, json.JSONDecodeError,
                    KeyError, IndexError) as e:
                last_error = str(e)
                logger.warning(
                    "LLM call attempt %d/%d failed: %s",
                    attempt + 1, 1 + self.config.max_retries, e,
                )
                if attempt < self.config.max_retries:
                    time.sleep(1 * (attempt + 1))  # simple backoff

        logger.error("LLM call failed after %d attempts: %s", 1 + self.config.max_retries, last_error)
        return None

    def _parse_json(self, raw: str, model: type[BaseModel]) -> BaseModel | None:
        """Parse raw JSON string into a Pydantic model."""
        # Strip markdown fences if present
        if raw.startswith("```"):
            lines = raw.splitlines()
            # Remove first and last lines (```json and ```)
            if lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw = "\n".join(lines)

        try:
            parsed = json.loads(raw)
            return model.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning("Failed to parse LLM response into %s: %s", model.__name__, e)
            return None

    def generate_text(
        self,
        system_prompt: str,
        prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str | None:
        """Generate free-form text (no structured output).

        Returns:
            Response text string, or None on failure.
        """
        import httpx

        if not self.available:
            logger.debug("LLM not available — skipping text generation.")
            return None

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }

        body = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature if temperature is not None else self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
        }

        start = time.time()
        last_error: str | None = None

        for attempt in range(1 + self.config.max_retries):
            try:
                resp = httpx.post(
                    f"{self.config.base_url}/chat/completions",
                    headers=headers,
                    json=body,
                    timeout=self.config.timeout_ms / 1000,
                )
                resp.raise_for_status()
                data = resp.json()

                usage = data.get("usage", {})
                self.usage.add(
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    duration_ms=int((time.time() - start) * 1000),
                )

                return data["choices"][0]["message"]["content"]

            except (httpx.HTTPStatusError, httpx.RequestError, KeyError, IndexError) as e:
                last_error = str(e)
                logger.warning(
                    "LLM text generation attempt %d/%d failed: %s",
                    attempt + 1, 1 + self.config.max_retries, e,
                )
                if attempt < self.config.max_retries:
                    time.sleep(1 * (attempt + 1))

        logger.error("LLM text generation failed after %d attempts: %s", 1 + self.config.max_retries, last_error)
        return None


# ── Singleton ─────────────────────────────────────────────────────────

_global_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Get or create the global LLM client singleton."""
    global _global_client
    if _global_client is None:
        _global_client = LLMClient()
    return _global_client


def reset_llm_client() -> None:
    """Reset the global LLM client (useful for testing)."""
    global _global_client
    _global_client = None
