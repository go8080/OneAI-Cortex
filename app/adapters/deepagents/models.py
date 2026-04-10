"""Model resolution — converts 'provider:model' strings to LangChain chat models."""

from __future__ import annotations

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

__all__ = ["resolve_model"]

# Default model when none specified
DEFAULT_MODEL = "anthropic:claude-sonnet-4-6"


def resolve_model(
    model_spec: str,
    *,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> BaseChatModel:
    """Resolve a 'provider:model' string to a LangChain BaseChatModel.

    Examples:
        resolve_model("anthropic:claude-sonnet-4-6")
        resolve_model("openai:gpt-4o")
        resolve_model("google_genai:gemini-2.0-flash")
    """
    if ":" not in model_spec:
        raise ValueError(
            f"Invalid model spec '{model_spec}' — expected 'provider:model' format"
        )

    provider, model_name = model_spec.split(":", 1)

    return init_chat_model(
        model_name,
        model_provider=provider,
        temperature=temperature,
        max_tokens=max_tokens,
    )
