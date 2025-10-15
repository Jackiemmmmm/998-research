"""
LLM Configuration - Central configuration for different LLM providers
Supports: Ollama, Groq, Cerebras, Google Gemini
"""

import os
from typing import Optional
from langchain.chat_models import init_chat_model


class LLMConfig:
    """Configuration for LLM providers"""

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
    def get_model(provider: Optional[str] = None):
        """
        Get initialized chat model for specified provider

        Args:
            provider: Provider name (ollama, groq, cerebras, google_genai)
                     If None, uses LLM_PROVIDER from .env

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
            api_key_env = config["api_key_env"]
            api_key = os.getenv(api_key_env)
            if not api_key:
                raise ValueError(
                    f"API key not found for {provider}. "
                    f"Please set {api_key_env} in your .env file."
                )

        # Build model string
        model_name = config["model"]
        model_string = config["model_string"].format(model=model_name)

        # Special handling for Ollama
        if provider == "ollama":
            base_url = config["base_url"]
            print(f"✅ Using Ollama: {model_name} at {base_url}")

            # Use ChatOllama directly for better tool support
            try:
                from langchain_ollama import ChatOllama
                return ChatOllama(
                    model=model_name,
                    base_url=base_url,
                    temperature=0,
                )
            except ImportError:
                # Fallback to init_chat_model
                return init_chat_model(
                    model_string,
                    model_provider="ollama",
                    base_url=base_url,
                )
        else:
            print(f"✅ Using {provider.title()}: {model_name}")
            return init_chat_model(model_string)

    @staticmethod
    def get_model_info(provider: Optional[str] = None) -> dict:
        """Get information about configured model"""
        if provider is None:
            provider = os.getenv("LLM_PROVIDER", "google_genai")

        provider = provider.lower()

        if provider not in LLMConfig.PROVIDERS:
            return {"error": f"Unknown provider: {provider}"}

        config = LLMConfig.PROVIDERS[provider]
        return {
            "provider": provider,
            "model": config["model"],
            "requires_api_key": config["requires_api_key"],
        }

    @staticmethod
    def list_providers() -> list:
        """List all available providers"""
        return list(LLMConfig.PROVIDERS.keys())

    @staticmethod
    def check_setup(provider: Optional[str] = None) -> dict:
        """
        Check if provider is properly configured

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
            api_key_env = config["api_key_env"]
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
            base_url = config["base_url"]
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
    """Shorthand to get LLM model"""
    return LLMConfig.get_model(provider)


if __name__ == "__main__":
    """Test LLM configuration"""
    # Load .env file
    from dotenv import load_dotenv
    load_dotenv()

    print("=" * 60)
    print("LLM Configuration Test")
    print("=" * 60)

    # List providers
    print("\nAvailable providers:")
    for p in LLMConfig.list_providers():
        print(f"  - {p}")

    # Get current provider
    current = os.getenv("LLM_PROVIDER", "google_genai")
    print(f"\nCurrent provider: {current}")

    # Check setup
    check = LLMConfig.check_setup()
    print(f"\nSetup check: {check}")

    # Try to initialize
    try:
        model = LLMConfig.get_model()
        print(f"\n✅ Model initialized successfully")
        print(f"   Provider: {check.get('provider')}")
        print(f"   Model: {check.get('model')}")
    except Exception as e:
        print(f"\n❌ Failed to initialize model: {e}")
