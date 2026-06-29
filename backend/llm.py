"""
WanderOn LLM Connection Client.
Integrates with OpenAI, Gemini, Groq, Anthropic, Ollama, and NVIDIA APIs
using compatible chat and vision endpoints.
"""
import httpx, logging

log = logging.getLogger("wanderon.llm")

PROVIDERS = {
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "default": "llama-3.3-70b-versatile",
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
        "vision": ["llama-3.2-90b-vision-preview", "llama-3.2-11b-vision-preview"],
    },
    "nvidia": {
        "url": "https://integrate.api.nvidia.com/v1/chat/completions",
        "default": "nvidia/llama-3.1-nemotron-70b-instruct",
        "models": ["nvidia/llama-3.1-nemotron-70b-instruct", "nvidia/llama-3.3-nemotron-super-49b-v1"],
        "vision": ["nvidia/neva-22b"],
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "default": "meta-llama/llama-3.3-70b-instruct:free",
        "models": ["meta-llama/llama-3.3-70b-instruct:free", "google/gemma-3-27b-it:free", "deepseek/deepseek-r1:free"],
        "vision": ["qwen/qwen2.5-vl-32b-instruct:free"],
    },
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "default": "gemini-2.0-flash",
        "models": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
        "vision": ["gemini-2.0-flash", "gemini-1.5-pro"],
    },
    "openai": {
        "url": "https://api.openai.com/v1/chat/completions",
        "default": "gpt-4o-mini",
        "models": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
        "vision": ["gpt-4o-mini", "gpt-4o"],
    },
    "claude": {
        "url": "https://api.anthropic.com/v1/messages",
        "default": "claude-haiku-4-5-20251001",
        "models": ["claude-haiku-4-5-20251001", "claude-sonnet-4-6"],
        "vision": ["claude-haiku-4-5-20251001", "claude-sonnet-4-6"],
    },
    "ollama": {
        "url": "http://localhost:11434/v1/chat/completions",
        "default": "llama3.2",
        "models": ["llama3.2", "llama3.1", "mistral", "phi3"],
        "vision": ["llama3.2-vision"],
    },
}

def supports_vision(provider: str, model: str) -> bool:
    return model in PROVIDERS.get(provider, {}).get("vision", [])

class LLMClient:
    def __init__(self, provider: str, api_key: str, model: str):
        self.provider = provider.lower()
        self.api_key = api_key
        self.model = model
        self.cfg = PROVIDERS.get(self.provider)
        if not self.cfg:
            raise ValueError(f"Unknown provider: {provider}")

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.provider == "claude":
            h["x-api-key"] = self.api_key
            h["anthropic-version"] = "2023-06-01"
        else:
            h["Authorization"] = f"Bearer {self.api_key}"
        if self.provider == "openrouter":
            h["HTTP-Referer"] = "https://wanderon.app"
            h["X-Title"] = "WanderOn"
        return h

    async def chat(self, system: str, user: str, max_tokens: int = 3000) -> str:
        if self.provider == "claude":
            return await self._claude([{"type": "text", "text": user}], system, max_tokens)
        async with httpx.AsyncClient(timeout=90) as c:
            r = await c.post(self.cfg["url"], headers=self._headers(), json={
                "model": self.model,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "max_tokens": max_tokens, "temperature": 0.7,
            })
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]

    async def chat_vision(self, system: str, text: str, img_b64: str, mime: str, max_tokens: int = 1200) -> str:
        if self.provider == "claude":
            content = [
                {"type": "text", "text": text},
                {"type": "image", "source": {"type": "base64", "media_type": mime, "data": img_b64}},
            ]
            return await self._claude(content, system, max_tokens)
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": [
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}},
            ]}],
        }
        async with httpx.AsyncClient(timeout=90) as c:
            r = await c.post(self.cfg["url"], headers=self._headers(), json=payload)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]

    async def _claude(self, content, system: str, max_tokens: int) -> str:
        async with httpx.AsyncClient(timeout=90) as c:
            r = await c.post(self.cfg["url"], headers=self._headers(), json={
                "model": self.model, "max_tokens": max_tokens,
                "system": system, "messages": [{"role": "user", "content": content}],
            })
            r.raise_for_status()
            return r.json()["content"][0]["text"]
