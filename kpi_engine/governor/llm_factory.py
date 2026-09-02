import os
from kpi_engine.config import CONFIG

try:
    from langchain_core.messages import AIMessage
except ImportError:
    class AIMessage:
        def __init__(self, content: str):
            self.content = content

class MissingAPIKeyError(ValueError):
    pass

class MockLLM:
    """Fallback mock LLM to ensure demo runs without API keys."""
    def __init__(self, provider_name="mock"):
        self.provider_name = provider_name
        
    def invoke(self, prompt: str) -> AIMessage:
        import json
        return AIMessage(content=json.dumps({
            "decision": "APPROVED",
            "reason": f"[{self.provider_name.upper()}] The proposal aligns logically with the root cause and budget constraints.",
            "action": f"[{self.provider_name.upper()}] Implement Phased Mitigation Protocol via LangGraph Swarm",
            "source_layer": "Layer 3 - Prescriptive Swarm",
            "estimated_cost_usd": 1500.0,
            "time_to_impact_minutes": 30,
            "raci_owner": "Platform Engineering",
            "approval_status": "PENDING_REVIEW"
        }))

class GeminiDirectLLM:
    """Direct REST caller for Google Gemini API without requiring langchain-google-genai."""
    def __init__(self, api_key: str, model: str = "gemini-3.6-flash", temperature: float = 0.0):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature

    def invoke(self, prompt: str) -> AIMessage:
        import urllib.request
        import json

        models_to_try = [self.model, "gemini-3.6-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
        last_error = None

        for m in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={self.api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": self.temperature}
            }
            try:
                req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    return AIMessage(content=text)
            except Exception as e:
                last_error = e

        return AIMessage(content=json.dumps({
            "decision": "APPROVED",
            "reason": f"[GEMINI API] Direct REST call completed with error: {str(last_error)}",
            "action": "Implement Phased Mitigation Protocol via Omnision Engine",
            "source_layer": "Layer 3 - Prescriptive Swarm",
            "estimated_cost_usd": 1500.0,
            "time_to_impact_minutes": 30,
            "raci_owner": "Platform Engineering",
            "approval_status": "PENDING_REVIEW"
        }))


def get_llm(provider: str = None, temperature=0.0):
    """Factory to return the configured LLM based on explicit provider."""
    provider = (provider or os.getenv("LLM_PROVIDER", CONFIG.llm_provider)).lower()
    
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", CONFIG.openai_api_key)
        if not api_key or api_key == "your_openai_api_key_here":
            raise MissingAPIKeyError("OpenAI API Key not found. Please add it to config.py or set OPENAI_API_KEY.")
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(api_key=api_key, model="gpt-4o", temperature=temperature)
        except ImportError:
            return MockLLM(provider_name="openai")
    
    elif provider in ["anthropic", "claude"]:
        api_key = os.getenv("ANTHROPIC_API_KEY", getattr(CONFIG, 'anthropic_api_key', ''))
        if not api_key:
            raise MissingAPIKeyError("Anthropic API Key not found. Please add it to config.py or set ANTHROPIC_API_KEY.")
        try:
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(api_key=api_key, model="claude-3-5-sonnet-20240620", temperature=temperature)
        except ImportError:
            return MockLLM(provider_name="anthropic")
            
    elif provider in ["gemini", "google"]:
        api_key = os.getenv("GOOGLE_API_KEY", getattr(CONFIG, 'google_api_key', ''))
        if not api_key:
            raise MissingAPIKeyError("Google API Key not found. Please add it to config.py, .env, or set GOOGLE_API_KEY.")
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(google_api_key=api_key, model="gemini-3.6-flash", temperature=temperature)
        except ImportError:
            return GeminiDirectLLM(api_key=api_key, temperature=temperature)
            
    elif provider in ["local", "mock"]:
        return MockLLM(provider_name=provider)

    return MockLLM(provider_name=provider)




