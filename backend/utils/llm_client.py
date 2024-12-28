import httpx
import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8080", max_tokens: int = 800):
        self.base_url = base_url
        self.max_tokens = max_tokens

    async def complete(self, prompt: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json={
                        "model": "llama-3.2-3b-instruct",
                        "messages": [
                            {"role": "system", "content": "You are a helpful AI assistant."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": self.max_tokens
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    logger.error(f"LLM API error: {response.status_code} - {response.text}")
                    return ""
        except Exception as e:
            logger.error(f"LLM client error: {str(e)}")
            return ""
