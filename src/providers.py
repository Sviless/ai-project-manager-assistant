"""
providers.py
------------
Clean, pluggable **LLM provider interface** for the app's optional "LLM mode".

The app runs in one of two modes (see `src/ai_engine.py`):

- **Mock mode**  — local Python templates/rules, no API key required (default).
- **LLM mode**   — a real model, enabled only when `LLM_API_KEY` is set.

This module defines a minimal `LLMProvider` interface plus ready-to-use
implementations for OpenAI, Azure OpenAI, and Anthropic (Claude). Each provider
lazily imports its SDK, so none of them are required to install or run the app —
you only need the SDK for the provider you actually choose.

Configuration is read from environment variables (never hard-coded):

    LLM_API_KEY               Required to enable LLM mode. Absence => mock mode.
    LLM_PROVIDER              openai | azure | anthropic   (default: openai)
    LLM_MODEL                 Model / deployment name (provider-specific default)

    # Azure OpenAI only:
    AZURE_OPENAI_ENDPOINT     https://<resource>.openai.azure.com
    AZURE_OPENAI_API_VERSION  e.g. 2024-06-01 (has a sensible default)

Keys are read at runtime from the environment; nothing is stored in code.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# Optional .env loading (dependency-free)
# ---------------------------------------------------------------------------
_ENV_LOADED = False


def load_env_file(path: str | os.PathLike[str] = ".env") -> None:
    """
    Load simple KEY=VALUE pairs from a local .env file into the environment.

    - Runs at most once per process.
    - Never overrides variables already present in the environment.
    - Dependency-free (does not require python-dotenv).
    - Safe no-op if the file is missing.
    """
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    _ENV_LOADED = True

    env_path = Path(path)
    if not env_path.is_file():
        return

    try:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError:
        # A malformed/unreadable .env should never crash the app.
        return


# ---------------------------------------------------------------------------
# Provider interface
# ---------------------------------------------------------------------------
@runtime_checkable
class LLMProvider(Protocol):
    """
    Minimal interface every LLM backend must implement.

    A provider turns a (system, user) prompt pair into a text completion.
    Keeping the surface this small makes it trivial to add new providers.
    """

    name: str
    model: str

    def complete(self, system: str, user: str) -> str:
        """Return the model's text response for the given prompts."""
        ...


# ---------------------------------------------------------------------------
# Concrete providers (SDKs imported lazily — none required to run the app)
# ---------------------------------------------------------------------------
class OpenAIProvider:
    """OpenAI Chat Completions provider. Requires `pip install openai`."""

    name = "OpenAI"

    def __init__(self, api_key: str, model: str | None = None) -> None:
        self._api_key = api_key
        self.model = model or "gpt-4o-mini"

    def complete(self, system: str, user: str) -> str:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - depends on optional dep
            raise RuntimeError(
                "The 'openai' package is required for LLM_PROVIDER=openai. "
                "Install it with: pip install openai"
            ) from exc

        client = OpenAI(api_key=self._api_key)
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.4,
        )
        return (response.choices[0].message.content or "").strip()


class AzureOpenAIProvider:
    """
    Azure OpenAI provider. Requires `pip install openai` plus the
    AZURE_OPENAI_ENDPOINT env var and a deployment name (LLM_MODEL or
    AZURE_OPENAI_DEPLOYMENT).
    """

    name = "Azure OpenAI"

    def __init__(self, api_key: str, model: str | None = None) -> None:
        self._api_key = api_key
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01")
        # For Azure, the "model" is the deployment name.
        self.model = model or os.getenv("AZURE_OPENAI_DEPLOYMENT", "")

    def complete(self, system: str, user: str) -> str:
        if not self.endpoint:
            raise RuntimeError(
                "AZURE_OPENAI_ENDPOINT is required for LLM_PROVIDER=azure."
            )
        if not self.model:
            raise RuntimeError(
                "Set LLM_MODEL (or AZURE_OPENAI_DEPLOYMENT) to your Azure "
                "OpenAI deployment name."
            )
        try:
            from openai import AzureOpenAI
        except ImportError as exc:  # pragma: no cover - depends on optional dep
            raise RuntimeError(
                "The 'openai' package is required for LLM_PROVIDER=azure. "
                "Install it with: pip install openai"
            ) from exc

        client = AzureOpenAI(
            api_key=self._api_key,
            azure_endpoint=self.endpoint,
            api_version=self.api_version,
        )
        response = client.chat.completions.create(
            model=self.model,  # deployment name
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.4,
        )
        return (response.choices[0].message.content or "").strip()


class AnthropicProvider:
    """Anthropic (Claude) provider. Requires `pip install anthropic`."""

    name = "Anthropic (Claude)"

    def __init__(self, api_key: str, model: str | None = None) -> None:
        self._api_key = api_key
        self.model = model or "claude-3-5-sonnet-latest"

    def complete(self, system: str, user: str) -> str:
        try:
            from anthropic import Anthropic
        except ImportError as exc:  # pragma: no cover - depends on optional dep
            raise RuntimeError(
                "The 'anthropic' package is required for LLM_PROVIDER=anthropic. "
                "Install it with: pip install anthropic"
            ) from exc

        client = Anthropic(api_key=self._api_key)
        message = client.messages.create(
            model=self.model,
            max_tokens=1500,
            temperature=0.4,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        parts = [
            block.text
            for block in message.content
            if getattr(block, "type", None) == "text"
        ]
        return "".join(parts).strip()


# ---------------------------------------------------------------------------
# Provider registry + factory
# ---------------------------------------------------------------------------
# Map friendly aliases -> provider classes.
_PROVIDERS: dict[str, type] = {
    "openai": OpenAIProvider,
    "azure": AzureOpenAIProvider,
    "azure-openai": AzureOpenAIProvider,
    "azure_openai": AzureOpenAIProvider,
    "anthropic": AnthropicProvider,
    "claude": AnthropicProvider,
}


def available_providers() -> list[str]:
    """Return the canonical provider aliases users can set in LLM_PROVIDER."""
    return ["openai", "azure", "anthropic"]


def get_provider(api_key: str | None = None) -> LLMProvider | None:
    """
    Resolve the configured LLM provider from the environment.

    Returns a ready-to-use provider when `LLM_API_KEY` is set, otherwise
    `None` (which signals the caller to use mock mode). Raises `ValueError`
    only when a key is present but `LLM_PROVIDER` names an unknown provider.
    """
    load_env_file()

    api_key = api_key or os.getenv("LLM_API_KEY", "").strip()
    if not api_key:
        return None  # No key => caller falls back to mock mode.

    provider_name = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    model = os.getenv("LLM_MODEL", "").strip() or None

    provider_cls = _PROVIDERS.get(provider_name)
    if provider_cls is None:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{provider_name}'. "
            f"Supported: {', '.join(available_providers())}."
        )
    return provider_cls(api_key=api_key, model=model)
