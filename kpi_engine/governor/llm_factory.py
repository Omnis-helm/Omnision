"""
LLM provider factory.

Every client exposes `.invoke(prompt) -> message` with `.content` (LangChain-compatible). Errors are
raised as `LLMProviderError` and never converted into an "APPROVED" verdict: callers fall back to the
deterministic local path instead (fail closed).
"""
import json
import os
import urllib.error
import urllib.request
from typing import Tuple

from kpi_engine.config import CONFIG

try:
    from langchain_core.messages import AIMessage
except ImportError:
    class AIMessage:  # minimal stand-in
        def __init__(self, content: str, usage_metadata=None, response_metadata=None):
            self.content = content
            self.usage_metadata = usage_metadata or {}
            self.response_metadata = response_metadata or {}


class MissingAPIKeyError(ValueError):
    pass


class LLMProviderError(RuntimeError):
    pass


PLACEHOLDER_KEYS = {"", "your_openai_api_key_here", "your_anthropic_api_key_here", "your_google_api_key_here"}


def _key(env: str, cfg_value: str) -> str:
    k = os.getenv(env) or cfg_value or ""
    return "" if k in PLACEHOLDER_KEYS else k


def _post_json(url: str, payload: dict, headers: dict, timeout: int) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")[:300]
        raise LLMProviderError(f"HTTP {e.code}: {body}") from e
    except Exception as e:
        raise LLMProviderError(str(e)) from e


class MockLLM:
    """Deterministic stand-in. The swarm never asks it to *decide* anything: the mock/local provider
    path uses the grounded playbook network and the local semantic supervisor instead."""

    def __init__(self, provider_name: str = "mock"):
        self.provider_name = provider_name

    def invoke(self, prompt: str):
        return AIMessage(content=json.dumps({"proposals": [], "narrative": ""}))


class GeminiDirectLLM:
    """Direct REST client for the Gemini API (used when langchain-google-genai is not installed)."""

    def __init__(self, api_key: str, model: str, temperature: float = 0.0, timeout: int = 30):
        self.api_key, self.model, self.temperature, self.timeout = api_key, model, temperature, timeout

    def invoke(self, prompt: str):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        data = _post_json(url, {"contents": [{"parts": [{"text": prompt}]}],
                                "generationConfig": {"temperature": self.temperature}},
                          {"x-goog-api-key": self.api_key}, self.timeout)  # key in header, not in URL
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise LLMProviderError(f"Unexpected Gemini response: {str(data)[:200]}") from e
        usage = data.get("usageMetadata", {})
        return AIMessage(content=text, usage_metadata={"input_tokens": usage.get("promptTokenCount", 0),
                                                       "output_tokens": usage.get("candidatesTokenCount", 0)})


class OllamaDirectLLM:
    """Direct REST client for a local Ollama server (private model, data never leaves the host)."""

    def __init__(self, base_url: str, model: str, temperature: float = 0.0, timeout: int = 60):
        self.base_url, self.model, self.temperature, self.timeout = base_url.rstrip("/"), model, temperature, timeout

    def invoke(self, prompt: str):
        data = _post_json(f"{self.base_url}/api/generate",
                          {"model": self.model, "prompt": prompt, "stream": False,
                           "options": {"temperature": self.temperature}}, {}, self.timeout)
        if "response" not in data:
            raise LLMProviderError(f"Unexpected Ollama response: {str(data)[:200]}")
        return AIMessage(content=data["response"],
                         usage_metadata={"input_tokens": data.get("prompt_eval_count", 0),
                                         "output_tokens": data.get("eval_count", 0)})


def get_llm(provider: str = None, temperature: float = 0.0):
    """Factory returning a client for the requested provider. Raises MissingAPIKeyError when a cloud
    provider has no key configured."""
    provider = (provider or CONFIG.llm_provider or "mock").lower()

    if provider == "openai":
        api_key = _key("OPENAI_API_KEY", CONFIG.openai_api_key)
        if not api_key:
            raise MissingAPIKeyError("OpenAI API Key not found. Set OPENAI_API_KEY in .env.")
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as e:
            raise LLMProviderError("langchain-openai is not installed") from e
        return ChatOpenAI(api_key=api_key, model=CONFIG.openai_model, temperature=temperature,
                          timeout=CONFIG.llm_timeout_seconds)

    if provider in ("anthropic", "claude"):
        api_key = _key("ANTHROPIC_API_KEY", CONFIG.anthropic_api_key)
        if not api_key:
            raise MissingAPIKeyError("Anthropic API Key not found. Set ANTHROPIC_API_KEY in .env.")
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as e:
            raise LLMProviderError("langchain-anthropic is not installed") from e
        return ChatAnthropic(api_key=api_key, model=CONFIG.anthropic_model, temperature=temperature,
                             timeout=CONFIG.llm_timeout_seconds)

    if provider in ("gemini", "google"):
        api_key = _key("GOOGLE_API_KEY", CONFIG.google_api_key)
        if not api_key:
            raise MissingAPIKeyError("Google API Key not found. Set GOOGLE_API_KEY in .env.")
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(google_api_key=api_key, model=CONFIG.gemini_model, temperature=temperature)
        except ImportError:
            return GeminiDirectLLM(api_key=api_key, model=CONFIG.gemini_model, temperature=temperature,
                                   timeout=CONFIG.llm_timeout_seconds)

    if provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(base_url=CONFIG.ollama_base_url, model=CONFIG.ollama_model, temperature=temperature)
        except ImportError:
            return OllamaDirectLLM(CONFIG.ollama_base_url, CONFIG.ollama_model, temperature)

    return MockLLM(provider_name=provider)


def extract_usage(response, prompt: str = "") -> Tuple[int, int]:
    """(input_tokens, output_tokens) from a LangChain / direct response; estimated if absent."""
    usage = getattr(response, "usage_metadata", None) or {}
    if usage.get("input_tokens") or usage.get("output_tokens"):
        return int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0))
    meta = getattr(response, "response_metadata", None) or {}
    tu = meta.get("token_usage") or meta.get("usage") or {}
    if isinstance(tu, dict) and tu:
        return (int(tu.get("prompt_tokens", tu.get("input_tokens", 0))),
                int(tu.get("completion_tokens", tu.get("output_tokens", 0))))
    content = str(getattr(response, "content", ""))
    return max(1, len(prompt) // 4), max(1, len(content) // 4)  # ~4 chars/token estimate
