"""
Shared LLM client for the whole app.
Toggle backend via LLM_PROVIDER env var:
  "anthropic"  -> Anthropic's native SDK directly (default)
  "openrouter" -> OpenRouter (OpenAI-compatible API) - one key, many models,
                  e.g. anthropic/claude-fable-5, openai/gpt-4o, meta-llama/...

Usage:
    from core.llm_client import call_llm
    raw_text = call_llm(prompt, max_tokens=1000)
"""
import os
from typing import Optional

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")

if LLM_PROVIDER == "openrouter":
    from openai import OpenAI
    _client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY") or "missing-key",
    )
    DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-fable-5")
else:
    import anthropic
    _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY") or "missing-key")
    DEFAULT_MODEL = "claude-sonnet-4-6"


def call_llm(prompt: str, max_tokens: int = 1000, model: Optional[str] = None) -> str:
    """Single entry point for LLM calls - returns raw text, provider-agnostic."""
    model = model or DEFAULT_MODEL
    if LLM_PROVIDER == "openrouter":
        response = _client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()
    else:
        response = _client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
