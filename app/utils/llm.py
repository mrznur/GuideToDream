"""
app/utils/llm.py
─────────────────
LLM wrapper using the official Google Gemini SDK (google-genai).

KEY FIX: call_llm_async is the primary function — it uses asyncio.to_thread()
to run the blocking Gemini SDK call in a thread pool, so FastAPI's event loop
is never blocked. The old synchronous call_llm is kept for scheduler/background
tasks that run outside the event loop.

MODEL ROUTING:
"fast"  → gemini-3.6-flash
"smart" → gemini-3.6-flash (same for now; swap to a Pro variant when needed)
"""

import asyncio
import time
from typing import Literal

import structlog

logger = structlog.get_logger(__name__)


class LLMError(Exception):
    """Raised when an LLM call fails."""
    def __init__(self, message: str, model: str | None = None, retryable: bool = False):
        super().__init__(message)
        self.model = model
        self.retryable = retryable


_MODEL_MAP = {
    "fast":  "gemini-3.6-flash",
    "smart": "gemini-3.6-flash",
}

# ── Shared client (created once, reused for all calls) ─────────────────────
_client = None

def _get_client():
    """Return a shared genai.Client, creating it once on first call."""
    global _client
    if _client is None:
        try:
            from google import genai
        except ImportError as e:
            raise LLMError("google-genai not installed. Run: pip install google-genai") from e
        from app.config import get_settings
        _client = genai.Client(api_key=get_settings().gemini_api_key)
    return _client


def _resolve_model_id(model: Literal["fast", "smart"]) -> str:
    from app.config import get_settings
    settings = get_settings()
    if model == "fast" and "gemini" in settings.llm_fast_model:
        return settings.llm_fast_model.split("/")[-1]
    if model == "smart" and "gemini" in settings.llm_smart_model:
        return settings.llm_smart_model.split("/")[-1]
    return _MODEL_MAP[model]


def _call_llm_sync(
    prompt: str,
    model: Literal["fast", "smart"],
    temperature: float,
    max_tokens: int,
    task_name: str,
) -> str:
    """
    Blocking LLM call. DO NOT call this directly from an async endpoint —
    use call_llm_async instead to avoid blocking the event loop.
    """
    try:
        from google.genai import types
    except ImportError as e:
        raise LLMError("google-genai not installed") from e

    model_id = _resolve_model_id(model)
    client   = _get_client()

    logger.info("llm_call_started", task=task_name, model=model_id,
                prompt_chars=len(prompt), temperature=temperature)
    start = time.time()

    try:
        chunks = []
        for chunk in client.models.generate_content_stream(
            model=model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        ):
            if chunk.text:
                chunks.append(chunk.text)
        text = "".join(chunks)

    except Exception as e:
        msg = str(e).lower()
        if "rate limit" in msg or "429" in msg or "quota" in msg:
            logger.warning("llm_rate_limited", task=task_name, model=model_id)
            raise LLMError(f"Rate limit hit: {e}", model=model_id, retryable=True) from e
        if "api key" in msg or "401" in msg or "api_key" in msg:
            raise LLMError(f"Invalid API key: {e}", model=model_id, retryable=False) from e
        if "not found" in msg or "404" in msg:
            raise LLMError(f"Model {model_id} not available: {e}", model=model_id, retryable=False) from e
        logger.error("llm_call_failed", task=task_name, model=model_id, error=str(e))
        raise LLMError(f"LLM call failed: {e}", model=model_id, retryable=False) from e

    elapsed_ms = round((time.time() - start) * 1000, 1)
    logger.info("llm_call_completed", task=task_name, model=model_id,
                elapsed_ms=elapsed_ms, response_chars=len(text))
    return text


async def call_llm_async(
    prompt: str,
    model: Literal["fast", "smart"] = "fast",
    temperature: float = 0.1,
    max_tokens: int = 2048,
    task_name: str = "unknown",
) -> str:
    """
    Async-safe LLM call for use inside FastAPI endpoints.

    Runs the blocking Gemini SDK call in a thread pool via asyncio.to_thread(),
    so the FastAPI event loop is never blocked and other requests are served
    concurrently while waiting for the LLM response.
    """
    return await asyncio.to_thread(
        _call_llm_sync, prompt, model, temperature, max_tokens, task_name
    )


# kept for backward compat (scheduler / background jobs that run outside the loop)
def call_llm(
    prompt: str,
    model: Literal["fast", "smart"] = "fast",
    temperature: float = 0.1,
    max_tokens: int = 2048,
    task_name: str = "unknown",
) -> str:
    """Synchronous wrapper — only use from non-async contexts (scheduler, scripts)."""
    return _call_llm_sync(prompt, model, temperature, max_tokens, task_name)
