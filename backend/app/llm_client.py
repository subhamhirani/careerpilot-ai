"""
CareerPilot AI — LLM Abstraction Layer.

Provides a unified ``query_llm()`` function that:
1. Tries Groq first (via groq Python SDK).
2. Falls back to Gemini (via google-generativeai Python SDK).
3. Raises ``AllProvidersExhausted`` if all providers fail.

All credentials are read from environment variables.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from dotenv import load_dotenv
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

load_dotenv()


# ──────────────────────────────────────────────
#  Custom exceptions
# ──────────────────────────────────────────────

class LLMProviderError(Exception):
    """Base exception for LLM provider failures."""

    def __init__(self, provider: str, message: str) -> None:
        self.provider = provider
        super().__init__(f"[{provider}] {message}")


class AllProvidersExhausted(Exception):
    """Raised when every configured LLM provider has failed."""

    def __init__(self, errors: list[tuple[str, str]]) -> None:
        self.errors = errors
        details = "; ".join(f"{p}: {m}" for p, m in errors)
        super().__init__(f"All LLM providers exhausted: {details}")


class ProviderNotConfigured(LLMProviderError):
    """Raised when a provider's API key is missing."""


# ──────────────────────────────────────────────
#  Provider clients (lazy-loaded)
# ──────────────────────────────────────────────

_groq_client: Any = None
_gemini_model: Any = None


def _get_groq_client():
    """Return a cached Groq client instance."""
    global _groq_client
    if _groq_client is None:
        try:
            from groq import Groq
        except ImportError:
            raise LLMProviderError("groq", "groq package not installed")

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ProviderNotConfigured("groq", "GROQ_API_KEY not set")
        _groq_client = Groq(api_key=api_key)
    return _groq_client


def _get_gemini_model(model_name: str = "gemini-2.0-flash"):
    """Return a cached Gemini generative model instance."""
    global _gemini_model
    if _gemini_model is None:
        try:
            import google.generativeai as genai
        except ImportError:
            raise LLMProviderError("gemini", "google-generativeai package not installed")

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ProviderNotConfigured("gemini", "GEMINI_API_KEY not set")
        genai.configure(api_key=api_key)
        _gemini_model = genai.GenerativeModel(model_name)
    return _gemini_model


# ──────────────────────────────────────────────
#  Individual provider callers
# ──────────────────────────────────────────────

def _call_groq(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    model: str = "llama-3.3-70b-versatile",
) -> str:
    """Send a prompt to Groq and return the text response."""
    client = _get_groq_client()
    messages: list[dict[str, str]] = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    choice = response.choices[0]
    content = choice.message.content
    if content is None:
        raise LLMProviderError("groq", "empty response from model")
    return content


def _call_gemini(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    model: str = "gemini-2.0-flash",
) -> str:
    """Send a prompt to Gemini and return the text response."""
    model_instance = _get_gemini_model(model)

    generation_config = {
        "temperature": temperature,
        "max_output_tokens": max_tokens,
    }

    contents = [prompt]
    if system_prompt:
        # Gemini uses system_instruction at the model level
        # We'll prepend it as a user-role system instruction
        contents = [f"{system_prompt}\n\n{prompt}"]

    response = model_instance.generate_content(
        contents,
        generation_config=generation_config,
    )
    return response.text


# ──────────────────────────────────────────────
#  Unified entry point with retry & fallback
# ──────────────────────────────────────────────

PROVIDER_PRIORITY: list[tuple[str, Any]] = [
    ("groq", _call_groq),
    ("gemini", _call_gemini),
]


@retry(
    retry=retry_if_exception_type(LLMProviderError),
    stop=stop_after_attempt(2),  # only retry once per provider
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True,
)
def query_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    model: Optional[str] = None,
    preferred_provider: Optional[str] = None,
) -> str:
    """Send a prompt to the best available LLM provider.

    Tries Groq first, falls back to Gemini.  Raises
    ``AllProvidersExhausted`` if every provider fails.

    Args:
        prompt: The user/assistant prompt text.
        system_prompt: Optional system-level instruction.
        temperature: Sampling temperature (0.0 – 1.0).
        max_tokens: Maximum tokens in the response.
        model: Override the default model name for the provider.
        preferred_provider: Force a specific provider ("groq" or "gemini").

    Returns:
        The generated text.

    Raises:
        AllProvidersExhausted: When all providers have failed.
    """
    errors: list[tuple[str, str]] = []
    providers = PROVIDER_PRIORITY

    if preferred_provider:
        # Move the preferred provider to the front
        providers = sorted(
            PROVIDER_PRIORITY,
            key=lambda p: 0 if p[0] == preferred_provider else 1,
        )

    for provider_name, provider_fn in providers:
        try:
            return provider_fn(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                model=model or (  # default model per provider
                    "llama-3.3-70b-versatile" if provider_name == "groq" else "gemini-2.0-flash"
                ),
            )
        except (LLMProviderError, Exception) as exc:
            msg = str(exc)
            errors.append((provider_name, msg))
            continue

    raise AllProvidersExhausted(errors)
