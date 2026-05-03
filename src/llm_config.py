"""LLM Configuration - Central configuration for different LLM providers.

Supports: Ollama, Groq, Cerebras, Google Gemini.
"""

import logging
import os
from typing import Optional

from langchain.chat_models import init_chat_model

logger = logging.getLogger(__name__)

# Module-level flag so the "judge model env var unset" warning fires at most
# once per process. Phase B1 spec section 4.2: emit a one-time warning when
# JUDGE_OLLAMA_MODEL is not set and we fall back to the agent model.
_JUDGE_FALLBACK_WARNED = False


# ---------------------------------------------------------------------------
# Phase F — Reproducibility helpers
# ---------------------------------------------------------------------------

def _ollama_supports_seed() -> bool:
    """Check whether the installed ``langchain_ollama`` exposes ``seed``.

    Phase F spec section 5.6 requires that we honestly report whether
    determinism is available.  The current ``ChatOllama`` lists ``seed``
    in its pydantic model fields; older versions did not.  We probe
    once and cache the result in :data:`_OLLAMA_SEED_SUPPORTED`.
    """
    try:
        from langchain_ollama import ChatOllama
    except ImportError:
        return False
    fields = getattr(ChatOllama, "model_fields", None)
    if fields is None:
        return False
    return "seed" in fields


_OLLAMA_SEED_SUPPORTED: bool = _ollama_supports_seed()


def _resolve_seed(explicit: Optional[int]) -> Optional[int]:
    """Pick the seed value: explicit arg wins, then ``EVAL_SEED`` env."""
    if explicit is not None:
        return explicit
    raw = os.getenv("EVAL_SEED")
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except ValueError:
        logger.warning(
            "EVAL_SEED=%r is not an integer; ignoring (seed disabled).", raw
        )
        return None


class LLMConfig:
    """Configuration for LLM providers."""

    # Provider configurations
    PROVIDERS = {
        "ollama": {
            "model": os.getenv("OLLAMA_MODEL", "llama3.2"),
            "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            "model_string": "ollama:{model}",
            "requires_api_key": False,
        },
        "groq": {
            "model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            "api_key_env": "GROQ_API_KEY",
            "model_string": "groq:{model}",
            "requires_api_key": True,
        },
        "cerebras": {
            "model": os.getenv("CEREBRAS_MODEL", "llama3.1-8b"),
            "api_key_env": "CEREBRAS_API_KEY",
            "model_string": "cerebras:{model}",
            "requires_api_key": True,
        },
        "google_genai": {
            "model": os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            "api_key_env": "GOOGLE_API_KEY",
            "model_string": "google_genai:{model}",
            "requires_api_key": True,
        },
    }

    @staticmethod
    def get_model(provider: Optional[str] = None, seed: Optional[int] = None):
        """Get initialized chat model for specified provider.

        Args:
            provider: Provider name (ollama, groq, cerebras, google_genai)
                     If None, uses LLM_PROVIDER from .env
            seed: Optional integer seed for deterministic decoding.  Only
                wired through when the active backend exposes it
                (currently: ChatOllama with langchain_ollama >= 0.x).
                If ``None``, the ``EVAL_SEED`` env var is consulted as a
                fallback.

        Returns:
            Initialized chat model

        Raises:
            ValueError: If provider is invalid or API key is missing
        """
        # Get provider from parameter or environment
        if provider is None:
            provider = os.getenv("LLM_PROVIDER", "google_genai")

        provider = provider.lower()

        if provider not in LLMConfig.PROVIDERS:
            raise ValueError(
                f"Unknown provider: {provider}. "
                f"Available: {list(LLMConfig.PROVIDERS.keys())}"
            )

        config = LLMConfig.PROVIDERS[provider]

        # Check API key if required
        if config["requires_api_key"]:
            api_key_env = str(config["api_key_env"])
            api_key = os.getenv(api_key_env)
            if not api_key:
                raise ValueError(
                    f"API key not found for {provider}. "
                    f"Please set {api_key_env} in your .env file."
                )

        # Build model string
        model_name = str(config["model"])
        model_string_template = str(config["model_string"])
        model_string = model_string_template.format(model=model_name)

        # Resolve seed (explicit arg > EVAL_SEED env var > None).
        resolved_seed = _resolve_seed(seed)

        # Special handling for Ollama
        if provider == "ollama":
            base_url = str(config["base_url"])

            # Use ChatOllama directly for better tool support
            try:
                from langchain_ollama import ChatOllama
                kwargs = dict(
                    model=model_name,
                    base_url=base_url,
                    temperature=0,
                    num_ctx=16384,
                    num_predict=2048,
                    client_kwargs={"timeout": 120.0},
                )
                # Only set seed when the installed ChatOllama actually
                # supports it; older versions silently ignore unknown
                # kwargs in pydantic, but here we want a hard guarantee.
                if resolved_seed is not None and _OLLAMA_SEED_SUPPORTED:
                    kwargs["seed"] = resolved_seed
                return ChatOllama(**kwargs)
            except ImportError:
                # Fallback to init_chat_model
                return init_chat_model(
                    model_string,
                    model_provider="ollama",
                    base_url=base_url,
                )
        else:
            return init_chat_model(model_string)

    @staticmethod
    def get_model_info(provider: Optional[str] = None) -> dict:
        """Get information about configured model.

        Phase F extends this with reproducibility-relevant fields:

        - ``seed_supported`` -- ``True`` only when the active backend
          actually exposes a deterministic seed parameter.  For Ollama
          this depends on the installed ``langchain_ollama`` version;
          other providers currently report ``False`` (they do not
          expose seed control through their langchain wrappers).
        - ``seed`` -- the resolved seed value (explicit arg or
          ``EVAL_SEED`` env), or ``None`` when no seed is configured.
        """
        if provider is None:
            provider = os.getenv("LLM_PROVIDER", "google_genai")

        provider = provider.lower()

        if provider not in LLMConfig.PROVIDERS:
            return {"error": f"Unknown provider: {provider}"}

        config = LLMConfig.PROVIDERS[provider]

        seed_value = _resolve_seed(None)
        # Only Ollama exposes seed today via ChatOllama.model_fields.
        seed_supported = provider == "ollama" and _OLLAMA_SEED_SUPPORTED

        return {
            "provider": provider,
            "model": config["model"],
            "requires_api_key": config["requires_api_key"],
            "seed_supported": seed_supported,
            "seed": seed_value if seed_supported else None,
        }

    @staticmethod
    def get_judge_llm():
        """Get the LLM used by the reasoning-quality (Dim1) judge.

        Phase B1 spec section 4.2: a separate local judge model removes
        self-evaluation bias.  Strategy:

        - If ``JUDGE_OLLAMA_MODEL`` env var is set, build a ``ChatOllama``
          using that model name with the same Ollama base URL / determinism
          settings as ``get_model()`` (temperature=0, num_ctx=16384,
          num_predict=2048, 120 s timeout).
        - Otherwise, log a one-time warning and fall back to
          ``LLMConfig.get_model()`` so the code still runs end-to-end on
          machines that have not pulled a second model.

        Returns:
            An initialised chat model suitable for judge-style invocations.
        """
        global _JUDGE_FALLBACK_WARNED

        judge_model = os.getenv("JUDGE_OLLAMA_MODEL")

        if judge_model:
            base_url = os.getenv(
                "OLLAMA_BASE_URL",
                str(LLMConfig.PROVIDERS["ollama"]["base_url"]),
            )
            try:
                from langchain_ollama import ChatOllama
                return ChatOllama(
                    model=judge_model,
                    base_url=base_url,
                    temperature=0,
                    num_ctx=16384,
                    num_predict=2048,
                    client_kwargs={"timeout": 120.0},
                )
            except ImportError:
                # Fallback: use init_chat_model with the ollama provider.
                return init_chat_model(
                    f"ollama:{judge_model}",
                    model_provider="ollama",
                    base_url=base_url,
                )

        # Env var not set -> fall back to the agent model.
        if not _JUDGE_FALLBACK_WARNED:
            logger.warning(
                "JUDGE_OLLAMA_MODEL is not set; reasoning-quality judge will "
                "reuse the agent model from LLMConfig.get_model(). This "
                "reintroduces self-evaluation bias on Dim1. Set "
                "JUDGE_OLLAMA_MODEL (e.g. 'qwen2.5:7b') to silence this "
                "warning."
            )
            _JUDGE_FALLBACK_WARNED = True

        return LLMConfig.get_model()

    @staticmethod
    def list_providers() -> list:
        """List all available providers."""
        return list(LLMConfig.PROVIDERS.keys())

    @staticmethod
    def check_setup(provider: Optional[str] = None) -> dict:
        """Check if provider is properly configured.

        Returns:
            dict with status and message
        """
        if provider is None:
            provider = os.getenv("LLM_PROVIDER", "google_genai")

        provider = provider.lower()

        if provider not in LLMConfig.PROVIDERS:
            return {
                "status": "error",
                "message": f"Unknown provider: {provider}",
            }

        config = LLMConfig.PROVIDERS[provider]

        # Check API key if required
        if config["requires_api_key"]:
            api_key_env = str(config["api_key_env"])
            api_key = os.getenv(api_key_env)
            if not api_key:
                return {
                    "status": "error",
                    "provider": provider,
                    "message": f"Missing API key: {api_key_env}",
                }

        # Special check for Ollama
        if provider == "ollama":
            import requests
            base_url = str(config["base_url"])
            try:
                response = requests.get(f"{base_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    return {
                        "status": "ok",
                        "provider": provider,
                        "model": config["model"],
                        "message": "Ollama is running",
                    }
                else:
                    return {
                        "status": "error",
                        "provider": provider,
                        "message": "Ollama is not responding. Run: ollama serve",
                    }
            except Exception as e:
                return {
                    "status": "error",
                    "provider": provider,
                    "message": f"Cannot connect to Ollama: {str(e)}. Run: ollama serve",
                }

        return {
            "status": "ok",
            "provider": provider,
            "model": config["model"],
            "message": "Configuration looks good",
        }


# Convenience function
def get_llm(provider: Optional[str] = None):
    """Shorthand to get LLM model."""
    return LLMConfig.get_model(provider)


def get_judge_llm():
    """Shorthand to get the reasoning-quality judge LLM.

    See ``LLMConfig.get_judge_llm`` for the selection rules.
    """
    return LLMConfig.get_judge_llm()


if __name__ == "__main__":
    """Test LLM configuration"""
    # Load .env file
    from dotenv import load_dotenv
    load_dotenv()


    # List providers
    for p in LLMConfig.list_providers():
        pass

    # Get current provider
    current = os.getenv("LLM_PROVIDER", "google_genai")

    # Check setup
    check = LLMConfig.check_setup()

    # Try to initialize
    try:
        model = LLMConfig.get_model()
    except Exception:
        pass
