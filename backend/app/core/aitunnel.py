"""
AITUNNEL client — OpenAI-compatible wrapper for Claude models (via AITUNNEL aggregator).
Implements prompt caching and token cost tracking as required by TZ.
"""

from __future__ import annotations

import base64
from typing import Any

import httpx
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Approximate cost per 1M tokens in RUB (as of 2025, via AITUNNEL)
COST_PER_1M_TOKENS: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6": {"input": 300.0, "output": 1500.0, "cache_read": 30.0},
    "claude-opus-4-7": {"input": 1500.0, "output": 7500.0, "cache_read": 150.0},
    "claude-haiku-4-5-20251001": {"input": 80.0, "output": 400.0, "cache_read": 8.0},
    "text-embedding-3-large": {"input": 13.0, "output": 0.0, "cache_read": 0.0},
}


def _get_client() -> AsyncOpenAI:
    settings = get_settings()
    return AsyncOpenAI(
        api_key=settings.aitunnel_api_key,
        base_url=settings.aitunnel_base_url,
        http_client=httpx.AsyncClient(timeout=120.0),
    )


def compute_cost_rub(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
) -> float:
    rates = COST_PER_1M_TOKENS.get(model, {"input": 300.0, "output": 1500.0, "cache_read": 30.0})
    billed_input = max(0, input_tokens - cached_tokens)
    return (
        billed_input * rates["input"] / 1_000_000
        + output_tokens * rates["output"] / 1_000_000
        + cached_tokens * rates["cache_read"] / 1_000_000
    )


class TokenUsage:
    def __init__(self, input: int, output: int, cached: int, cost_rub: float) -> None:
        self.input_tokens = input
        self.output_tokens = output
        self.cached_tokens = cached
        self.cost_rub = cost_rub


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def chat_completion(
    model: str,
    messages: list[dict[str, Any]],
    system: str | None = None,
    temperature: float = 0.1,
    max_tokens: int = 4096,
    response_format: dict[str, Any] | None = None,
) -> tuple[str, TokenUsage]:
    """Send a chat completion request to AITUNNEL and return (text, usage)."""
    client = _get_client()

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if system:
        payload["system"] = [
            {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
        ]
    if response_format:
        payload["response_format"] = response_format

    response = await client.chat.completions.create(**payload)

    usage = response.usage
    input_tokens = usage.prompt_tokens if usage else 0
    output_tokens = usage.completion_tokens if usage else 0
    cached_tokens = getattr(getattr(usage, "prompt_tokens_details", None), "cached_tokens", 0) or 0

    cost = compute_cost_rub(model, input_tokens, output_tokens, cached_tokens)
    logger.info(
        "llm_call",
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_tokens=cached_tokens,
        cost_rub=round(cost, 4),
    )

    content = response.choices[0].message.content or ""
    return content, TokenUsage(input_tokens, output_tokens, cached_tokens, cost)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def vision_completion(
    model: str,
    text_prompt: str,
    image_bytes: bytes,
    system: str | None = None,
    max_tokens: int = 8192,
) -> tuple[str, TokenUsage]:
    """Send a vision request (image + text) to AITUNNEL."""
    b64 = base64.standard_b64encode(image_bytes).decode()
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                {"type": "text", "text": text_prompt},
            ],
        }
    ]
    return await chat_completion(model, messages, system=system, max_tokens=max_tokens)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_embedding(text: str, model: str | None = None) -> list[float]:
    """Get text embedding vector from AITUNNEL."""
    settings = get_settings()
    if model is None:
        model = settings.model_embeddings
    client = _get_client()
    response = await client.embeddings.create(
        model=model,
        input=text,
        dimensions=settings.embedding_dimensions,
    )
    return response.data[0].embedding


async def get_embeddings_batch(texts: list[str], model: str | None = None) -> list[list[float]]:
    """Get embeddings for multiple texts (batched)."""
    settings = get_settings()
    if model is None:
        model = settings.model_embeddings
    client = _get_client()
    response = await client.embeddings.create(
        model=model,
        input=texts,
        dimensions=settings.embedding_dimensions,
    )
    return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
