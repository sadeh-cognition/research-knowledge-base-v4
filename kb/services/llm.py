import os
from enum import Enum


class LLMProvider(str, Enum):
    OPENROUTER = "openrouter"
    GROQ = "groq"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


def setup_llm_config(model_name: str, provider: LLMProvider | str, api_key: str | None) -> str:
    """
    Sets up the environment variables for the given LLM provider and API key.
    Returns the potentially modified model name.
    """
    if api_key:
        if provider == LLMProvider.OPENROUTER:
            os.environ["OPENROUTER_API_KEY"] = api_key
        elif provider == LLMProvider.OPENAI:
            os.environ["OPENAI_API_KEY"] = api_key
        elif provider == LLMProvider.ANTHROPIC:
            os.environ["ANTHROPIC_API_KEY"] = api_key
        elif provider == LLMProvider.GROQ:
            os.environ["GROQ_API_KEY"] = api_key
        else:
            # Default to OpenAI if it matches the string or is unknown
            os.environ["OPENAI_API_KEY"] = api_key
    return model_name
