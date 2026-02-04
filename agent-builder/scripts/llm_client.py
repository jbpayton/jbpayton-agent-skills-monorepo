"""OpenAI-compatible chat client — stdlib only, no pip."""

import json
import urllib.request
import urllib.error
from typing import Optional


class LLMClient:
    """HTTP client that talks to any OpenAI-compatible /v1 endpoint."""

    def __init__(self, base_url: str, api_key: str = "", model: str = "llama3"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def chat(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Send a chat-completion request.  Returns the assistant reply text."""
        url = f"{self.base_url}/chat/completions"

        payload: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            raise RuntimeError(f"LLM request failed ({exc.code}): {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Could not reach {self.base_url}: {exc.reason}") from exc
