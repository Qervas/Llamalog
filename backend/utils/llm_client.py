import httpx
import json
import logging
import asyncio
from typing import Any, Dict, Optional, Union, AsyncGenerator
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

class LLMErrorCode(Enum):
    CONNECTION_ERROR = "connection_error"
    TIMEOUT_ERROR = "timeout_error"
    INVALID_RESPONSE = "invalid_response"
    API_ERROR = "api_error"
    RATE_LIMIT = "rate_limit"
    CONTEXT_LENGTH = "context_length"
    UNKNOWN = "unknown_error"

@dataclass
class LLMResponse:
    content: str
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    latency: float = 0.0
    error: Optional[Dict[str, Any]] = None

class LLMException(Exception):
    def __init__(self, message: str, error_code: LLMErrorCode, details: Optional[Dict] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

class LLMClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080",
        max_retries: int = 3,
        timeout: float = 30.0,
        backoff_factor: float = 1.5
    ):
        self.base_url = base_url
        self.max_retries = max_retries
        self.timeout = timeout
        self.backoff_factor = backoff_factor
        self.context_window = 128000
        self.default_output_tokens = 4096

        # Initialize metrics
        self.request_count = 0
        self.error_count = 0
        self.total_tokens = 0

        # Configure client settings
        self.client_settings = {
            "timeout": timeout,
            "follow_redirects": True,
            "http2": True
        }

    async def _make_request(
        self,
        messages: list,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        retry_count: int = 0
    ) -> LLMResponse:
        """Make HTTP request to LLM API with retry logic and proper error handling"""
        start_time = datetime.now()

        try:
            async with httpx.AsyncClient(**self.client_settings) as client:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json={
                        "model": "llama-3.2-3b-instruct",
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens or self.default_output_tokens,
                        "stream": False
                    },
                    timeout=self.timeout
                )

                if response.status_code == 429:  # Rate limit
                    if retry_count < self.max_retries:
                        wait_time = self.backoff_factor ** retry_count
                        logger.warning(f"Rate limited. Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        return await self._make_request(messages, max_tokens, temperature, retry_count + 1)
                    raise LLMException(
                        "Rate limit exceeded",
                        LLMErrorCode.RATE_LIMIT
                    )

                response.raise_for_status()
                result = response.json()

                # Calculate latency
                latency = (datetime.now() - start_time).total_seconds()

                # Update metrics
                self.request_count += 1
                if "usage" in result:
                    self.total_tokens += result["usage"].get("total_tokens", 0)

                return LLMResponse(
                    content=result["choices"][0]["message"]["content"],
                    finish_reason=result["choices"][0].get("finish_reason"),
                    usage=result.get("usage"),
                    latency=latency
                )

        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout) as e:
            self.error_count += 1
            raise LLMException(
                "Request timed out",
                LLMErrorCode.TIMEOUT_ERROR,
                {"timeout": self.timeout}
            )
        except httpx.RequestError as e:
            self.error_count += 1
            raise LLMException(
                f"Connection error: {str(e)}",
                LLMErrorCode.CONNECTION_ERROR
            )
        except json.JSONDecodeError:
            self.error_count += 1
            raise LLMException(
                "Invalid JSON response",
                LLMErrorCode.INVALID_RESPONSE
            )
        except Exception as e:
            self.error_count += 1
            raise LLMException(
                f"Unknown error: {str(e)}",
                LLMErrorCode.UNKNOWN,
                {"original_error": str(e)}
            )

    async def complete(
            self,
            prompt: str,
            max_tokens: Optional[int] = None,
            temperature: float = 0.7,
            system_prompt: Optional[str] = None
        ) -> str:
            """Regular completion method that returns full response as string"""
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            try:
                response = await self._make_request(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                return response.content
            except LLMException as e:
                logger.error(
                    f"LLM error: {e.message}",
                    extra={
                        "error_code": e.error_code.value,
                        "details": e.details
                    }
                )
                return ""

    async def stream_complete(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Streaming completion method for more responsive output"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            async with httpx.AsyncClient(**self.client_settings) as client:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json={
                        "model": "llama-3.2-3b-instruct",
                        "messages": messages,
                        "temperature": temperature,
                        "stream": True
                    },
                    timeout=self.timeout
                )

                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        line = line[6:]
                    if line == "[DONE]" or not line.strip():
                        continue

                    try:
                        json_line = json.loads(line)
                        if content := json_line.get('choices', [{}])[0].get('delta', {}).get('content'):
                            yield content
                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            logger.error(f"Stream error: {str(e)}")
            yield f"*Error: {str(e)}*"

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count - improved version"""
        # More accurate estimation based on GPT tokenization patterns
        return len(text.encode('utf-8')) // 3

    def get_metrics(self) -> Dict[str, Any]:
        """Return current metrics"""
        return {
            "request_count": self.request_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(self.request_count, 1),
            "total_tokens": self.total_tokens,
            "average_tokens_per_request": self.total_tokens / max(self.request_count, 1)
        }
