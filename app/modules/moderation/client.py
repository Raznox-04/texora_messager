import asyncio
import logging
from typing import Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class AIGatewayError(Exception):
    pass


class AIGatewayClient:
    """کلاینت اتصال به درگاه هوش مصنوعی آروان‌کلاد (سازگار با OpenAI Chat Completions)"""

    def __init__(self):
        self.base_url = settings.AI_GATEWAY_BASE_URL.rstrip("/")
        self.api_key = settings.ARVANCLOUD_API_KEY
        self.model = settings.AI_MODEL_NAME
        self.timeout = settings.AI_TIMEOUT_SECONDS
        self.max_retries = settings.AI_MAX_RETRIES
        self.chat_endpoint = f"{self.base_url}/chat/completions"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format_json: bool = True,
    ) -> Optional[str]:
        if not self.api_key:
            logger.warning("ARVANCLOUD_API_KEY تنظیم نشده است")
            return None

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 512,
        }
        if response_format_json:
            payload["response_format"] = {"type": "json_object"}

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(
                        self.chat_endpoint,
                        headers=self._headers(),
                        json=payload,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        return data["choices"][0]["message"]["content"]
                    elif resp.status_code == 429:
                        await asyncio.sleep(2 ** attempt)
                        last_error = AIGatewayError("Rate limited")
                        continue
                    else:
                        logger.error(f"AI Gateway error {resp.status_code}: {resp.text[:300]}")
                        last_error = AIGatewayError(f"HTTP {resp.status_code}")
                        break
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_error = e
                logger.warning(f"AI Gateway attempt {attempt+1} failed: {e}")
                await asyncio.sleep(1.5 ** attempt)
            except Exception as e:
                last_error = e
                logger.exception("AI Gateway unexpected error")
                break

        logger.error(f"AI Gateway failed after retries: {last_error}")
        return None