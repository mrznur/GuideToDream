"""
app/utils/llm.py
─────────────────
LLM wrapper using the official Google Gemini SDK (google-genai).

Uses streaming mode to avoid timeout issues on long responses.
Streaming keeps the connection alive while the model generates text,
rather than waiting for the entire response in one blocking call.

MODEL ROUTING:
"fast"  → gemini-3.6-flash (free tier: 15 req/min)
"smart" → gemini-3.6-flash (same for now)

TEMPERATURE:
0.0-0.2 = deterministic (extraction, classification)
0.7-0.9 = creative (explanation writing, query generation)
"""

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
    "fast": "gemini-3.6-flash",
    "smart": "gemini-3.6-flash",
}


def call_llm(
    prompt: str,
    model: Literal["fast", "smart"] = "fast",
    temperature: float = 0.1,
    max_tokens: int = 4096,
    task_name: str = "unknown",
) -> str:
    """
    Make a single LLM call and return the text response.

    Args:
        prompt: The full prompt to send
        model: "fast" or "smart"
        temperature: 0.0-1.0, lower = more deterministic
        max_tokens: Maximum response tokens
        task_name: Label for logging

    Returns:
        The LLM's text response as a string

    Raises:
        LLMError: If the call fails
    """
    try:
        from google import genai
        from google.genai import types
    except ImportError as e:
        raise LLMError("google-genai not installed. Run: pip install google-genai") from e

    from app.config import get_settings
    settings = get_settings()

    model_id = _MODEL_MAP.get(model, "gemini-3.6-flash")
    if model == "fast" and "gemini" in settings.llm_fast_model:
        model_id = settings.llm_fast_model.split("/")[-1]
    elif model == "smart" and "gemini" in settings.llm_smart_model:
        model_id = settings.llm_smart_model.split("/")[-1]

    logger.info(
        "llm_call_started",
        task=task_name,
        model=model_id,
        prompt_chars=len(prompt),
        temperature=temperature,
    )

    start_time = time.time()

    try:
        client = genai.Client(api_key=settings.gemini_api_key)

        # Streaming mode: receive response in chunks rather than one blocking call.
        # This prevents connection timeouts on long JSON responses.
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
        error_msg = str(e).lower()

        if "rate limit" in error_msg or "429" in error_msg or "quota" in error_msg:
            logger.warning("llm_rate_limited", task=task_name, model=model_id)
            raise LLMError(f"Rate limit hit: {e}", model=model_id, retryable=True) from e

        if "api key" in error_msg or "401" in error_msg or "api_key" in error_msg:
            raise LLMError(
                f"Invalid API key. Check GEMINI_API_KEY in .env: {e}",
                model=model_id, retryable=False,
            ) from e

        if "not found" in error_msg or "404" in error_msg:
            raise LLMError(
                f"Model {model_id} not available: {e}",
                model=model_id, retryable=False,
            ) from e

        logger.error("llm_call_failed", task=task_name, model=model_id, error=str(e))
        raise LLMError(f"LLM call failed: {e}", model=model_id, retryable=False) from e

    elapsed_ms = round((time.time() - start_time) * 1000, 1)
    logger.info(
        "llm_call_completed",
        task=task_name,
        model=model_id,
        elapsed_ms=elapsed_ms,
        response_chars=len(text),
    )

    return text
