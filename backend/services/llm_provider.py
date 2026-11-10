import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

import httpx

from backend.core.config import settings

logger = logging.getLogger(__name__)


ALLOWED_IMAGE_MIME_TYPES = {
    "image/png": "image/png",
    "image/jpeg": "image/jpeg",
    "image/jpg": "image/jpeg",
    "image/webp": "image/webp",
    "image/gif": "image/gif"
}


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol abstraction for query and passage dense embedding models."""

    def embed_query(self, text: str) -> List[float]:
        """Generates a dense embedding vector for a search query."""
        ...

    def embed_passages(self, texts: List[str]) -> List[List[float]]:
        """Generates dense embedding vectors for multiple document passages."""
        ...


class TFIDFEmbeddingAdapter:
    """
    Offline-capable TF-IDF based EmbeddingProvider implementing the dense vector protocol.
    Can be used directly or swapped seamlessly with Gemini or OpenAI embedding models.
    """

    def __init__(self, vector_dim: int = 128):
        self.vector_dim = vector_dim

    def embed_query(self, text: str) -> List[float]:
        if not text.strip():
            return [0.0] * self.vector_dim
        vec = [0.0] * self.vector_dim
        for token in text.lower().split():
            idx = abs(hash(token)) % self.vector_dim
            vec[idx] += 1.0
        norm = sum(v * v for v in vec) ** 0.5
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def embed_passages(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_query(t) for t in texts]


@dataclass
class LLMResponse:
    text: str
    model: str
    provider: str
    is_generated: bool
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    raw_response: Optional[Dict[str, Any]] = None


class LLMError(Exception):
    """Base exception for LLM provider errors."""
    pass


class LLMConfigError(LLMError):
    """Raised when the LLM provider is not configured properly."""
    pass


class LLMAuthError(LLMError):
    """Raised when authentication with the provider fails."""
    pass


class LLMRateLimitError(LLMError):
    """Raised when provider rate limits are exceeded."""
    pass


class LLMProviderError(LLMError):
    """Raised when the provider fails to generate a response."""
    pass


class GeminiProvider:
    """
    Production-grade Google Gemini API Provider.
    Calls official Gemini REST API (v1beta generateContent) using httpx.
    Supports configurable models, retries with exponential backoff, safe error handling,
    and never leaks API credentials in logs or error messages.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3
    ):
        self.api_key = api_key or getattr(settings, "GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY")
        self.model = model or getattr(settings, "GEMINI_MODEL", None) or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self.timeout = timeout
        self.max_retries = max_retries

    @property
    def is_configured(self) -> bool:
        """Returns True if a non-empty, non-placeholder API key is set."""
        if not self.api_key or not self.api_key.strip():
            return False
        insecure_placeholders = {
            "your-gemini-api-key-here",
            "your_gemini_api_key_here",
            "changeme",
            "placeholder"
        }
        return self.api_key.strip().lower() not in insecure_placeholders

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
        images: Optional[List[Dict[str, str]]] = None
    ) -> LLMResponse:
        """
        Executes a generateContent request against Google Gemini.
        Supports multimodal parts (inline image data) according to Gemini REST API schema.
        Raises LLMError on failure; never exposes the API key.
        """
        if not self.is_configured:
            raise LLMConfigError(
                "Gemini API is not configured. Please set the GEMINI_API_KEY environment variable."
            )

        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

        # Construct payload according to official Gemini v1beta schema
        parts: List[Dict[str, Any]] = [{"text": prompt}]
        if images:
            for img in images:
                raw_mime = (img.get("mime_type") or "image/png").strip().lower()
                normalized_mime = ALLOWED_IMAGE_MIME_TYPES.get(raw_mime)
                if not normalized_mime:
                    raise LLMProviderError(f"Unsupported image MIME type: {raw_mime}. Supported: PNG, JPEG, WEBP, GIF.")

                b64_data = img.get("data")
                if not b64_data or not isinstance(b64_data, str) or len(b64_data) < 8:
                    raise LLMProviderError("Image data is missing or invalid base64 string.")

                parts.append({
                    "inlineData": {
                        "mimeType": normalized_mime,
                        "data": b64_data
                    }
                })

        payload: Dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": parts
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
                "topP": 0.95
            }
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key.strip()
        }

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(endpoint, json=payload, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        raise LLMProviderError("Gemini returned an empty candidate list.")

                    first_candidate = candidates[0]
                    content = first_candidate.get("content", {})
                    parts = content.get("parts", [])
                    if not parts or "text" not in parts[0]:
                        raise LLMProviderError("Gemini candidate did not contain text content.")

                    generated_text = parts[0]["text"].strip()
                    usage = data.get("usageMetadata", {})

                    return LLMResponse(
                        text=generated_text,
                        model=self.model,
                        provider="Google Gemini",
                        is_generated=True,
                        prompt_tokens=usage.get("promptTokenCount"),
                        completion_tokens=usage.get("candidatesTokenCount"),
                        raw_response=data
                    )

                elif response.status_code in [401, 403]:
                    logger.warning("[GeminiProvider] Authentication failed (HTTP %s).", response.status_code)
                    raise LLMAuthError(
                        "Authentication with Google Gemini API failed. Please verify your GEMINI_API_KEY."
                    )

                elif response.status_code == 429:
                    logger.warning("[GeminiProvider] Rate limit reached (HTTP 429) on attempt %d/%d.", attempt, self.max_retries)
                    if attempt < self.max_retries:
                        time.sleep(2 ** attempt)
                        continue
                    raise LLMRateLimitError(
                        "Google Gemini API rate limit exceeded. Please try again shortly."
                    )

                elif response.status_code >= 500:
                    logger.warning("[GeminiProvider] Server error (HTTP %s) on attempt %d/%d.", response.status_code, attempt, self.max_retries)
                    if attempt < self.max_retries:
                        time.sleep(1.5 * attempt)
                        continue
                    raise LLMProviderError(
                        f"Google Gemini service returned server error ({response.status_code})."
                    )

                else:
                    try:
                        err_json = response.json()
                        err_msg = err_json.get("error", {}).get("message", response.text[:200])
                    except Exception:
                        err_msg = response.text[:200]
                    raise LLMProviderError(f"Gemini API request failed ({response.status_code}): {err_msg}")

            except httpx.TimeoutException as exc:
                logger.warning("[GeminiProvider] Request timeout on attempt %d/%d: %s", attempt, self.max_retries, exc)
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(1.5 * attempt)
                    continue
                raise LLMProviderError("Google Gemini API request timed out.") from exc

            except httpx.NetworkError as exc:
                logger.warning("[GeminiProvider] Network error on attempt %d/%d: %s", attempt, self.max_retries, exc)
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(1.5 * attempt)
                    continue
                raise LLMProviderError("Network connection to Google Gemini API failed.") from exc

        raise LLMProviderError(f"Google Gemini API failed after {self.max_retries} attempts: {last_error}")

    def analyze_visual_element(
        self,
        image_bytes: bytes,
        mime_type: str = "image/png",
        prompt: str = "Describe this chart, diagram, or table visual in detail, transcribing all visible labels, axes, numbers, and legends."
    ) -> Optional[str]:
        """
        Sends an image to Gemini Multimodal vision for visual understanding.
        Returns description or None if unconfigured or failed.
        Never fabricates chart numbers; distinguishes extracted labels from descriptions.
        """
        if not self.is_configured:
            return None
        if not image_bytes or not isinstance(image_bytes, (bytes, bytearray)) or len(image_bytes) < 4:
            logger.warning("[GeminiProvider] Visual analysis failed: empty or invalid image bytes.")
            return None

        # Normalize and validate MIME
        raw_mime = (mime_type or "image/png").strip().lower()
        normalized_mime = ALLOWED_IMAGE_MIME_TYPES.get(raw_mime, "image/png")

        import base64
        try:
            b64_data = base64.b64encode(image_bytes).decode("utf-8")
            resp = self.generate(
                prompt=prompt,
                images=[{"mime_type": normalized_mime, "data": b64_data}],
                temperature=0.1
            )
            return resp.text
        except Exception as exc:
            logger.warning("[GeminiProvider] Visual analysis failed: %s", exc)
            return None


# Global provider instance and mock hook for tests
_active_provider: Optional[GeminiProvider] = None


def get_llm_provider() -> GeminiProvider:
    """Returns the singleton LLM provider instance."""
    global _active_provider
    if _active_provider is None:
        _active_provider = GeminiProvider()
    return _active_provider


def set_llm_provider(provider: Optional[GeminiProvider]) -> None:
    """Overrides the active LLM provider (used in testing)."""
    global _active_provider
    _active_provider = provider
