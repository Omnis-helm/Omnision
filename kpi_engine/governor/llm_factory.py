import os
from langchain_core.messages import AIMessage
from kpi_engine.config import CONFIG

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

def get_llm(provider: str = None, temperature=0.0):
    """Factory to return the configured LLM based on explicit provider."""
    provider = (provider or os.getenv("LLM_PROVIDER", CONFIG.llm_provider)).lower()
    
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("OPENAI_API_KEY", CONFIG.openai_api_key)
        if not api_key or api_key == "your_openai_api_key_here":
            raise MissingAPIKeyError("OpenAI API Key not found. Please add it to config.py or set OPENAI_API_KEY.")
        return ChatOpenAI(api_key=api_key, model="gpt-4o", temperature=temperature)
    
    elif provider in ["anthropic", "claude"]:
        from langchain_anthropic import ChatAnthropic
        api_key = os.getenv("ANTHROPIC_API_KEY", getattr(CONFIG, 'anthropic_api_key', ''))
        if not api_key:
            raise MissingAPIKeyError("Anthropic API Key not found. Please add it to config.py or set ANTHROPIC_API_KEY.")
        return ChatAnthropic(api_key=api_key, model="claude-3-5-sonnet-20240620", temperature=temperature)
            
    elif provider in ["gemini", "google"]:
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = os.getenv("GOOGLE_API_KEY", getattr(CONFIG, 'google_api_key', ''))
        if not api_key:
            raise MissingAPIKeyError("Google API Key not found. Please add it to config.py or set GOOGLE_API_KEY.")
        return ChatGoogleGenerativeAI(google_api_key=api_key, model="gemini-3.6-flash", temperature=temperature)
            
    elif provider == "ollama":
        from langchain_ollama import ChatOllama
        base_url = os.getenv("OLLAMA_BASE_URL", getattr(CONFIG, 'ollama_base_url', 'http://localhost:11434'))
        model = os.getenv("OLLAMA_MODEL", getattr(CONFIG, 'ollama_model', 'llama3'))
        return ChatOllama(base_url=base_url, model=model, temperature=temperature)
        
    return MockLLM(provider_name=provider)




