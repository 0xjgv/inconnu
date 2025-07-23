#!/usr/bin/env python3
"""
Model installer for Inconnu - downloads spaCy language models.
"""

import argparse
import os
import sys
from pathlib import Path
from subprocess import CalledProcessError, run
from typing import Optional

# Mapping of language codes to spaCy model names
LANGUAGE_MODELS = {
    "en": ["en_core_web_sm", "en_core_web_lg", "en_core_web_trf"],
    "de": ["de_core_news_sm", "de_core_news_md", "de_core_news_lg"],
    "it": ["it_core_news_sm", "it_core_news_md", "it_core_news_lg"],
    "es": ["es_core_news_sm", "es_core_news_md", "es_core_news_lg"],
    "fr": ["fr_core_news_sm", "fr_core_news_md", "fr_core_news_lg"],
}

# Default models (small versions for quick installation)
DEFAULT_MODELS = {
    "en": "en_core_web_sm",
    "de": "de_core_news_sm",
    "it": "it_core_news_sm",
    "es": "es_core_news_sm",
    "fr": "fr_core_news_sm",
}


def is_uv_environment() -> bool:
    """Check if running in a UV environment."""
    # Check for UV environment markers
    return (
        os.environ.get("UV_PROJECT_ROOT") is not None
        or Path(sys.prefix).name == ".venv"
        and Path(sys.prefix).parent.joinpath("uv.lock").exists()
    )


def ensure_pip_available() -> bool:
    """Ensure pip is available, install it if running in UV environment."""
    try:
        # Try importing pip to check if it's available
        import pip  # type: ignore # noqa: F401

        return True
    except ImportError:
        if is_uv_environment():
            print("📦 UV environment detected. Installing pip...")
            try:
                result = run(  # noqa: S603
                    ["uv", "pip", "install", "pip", "--upgrade"],  # noqa: S607
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    print("✓ pip installed successfully")
                    return True
                else:
                    print(f"✗ Failed to install pip: {result.stderr}")
                    return False
            except (CalledProcessError, FileNotFoundError) as e:
                print(f"✗ Error installing pip: {e}")
                return False
        return False


def download_model(model_name: str, upgrade: bool = False) -> bool:
    """Download a spaCy model using subprocess."""
    # First, ensure pip is available
    if not ensure_pip_available():
        print("\n⚠️  pip is not available and could not be installed.")
        if is_uv_environment():
            print("\n💡 For UV environments, you can install models directly:")
            print(
                f"   uv add 'inconnu[{model_name.split('_')[0]}]'  # for default model"
            )
            print(
                f"   uv add 'inconnu[{model_name.split('_')[0]}-lg]'  # for large model"
            )
            print("\n   Or install all languages: uv add 'inconnu[all]'")
        return False

    try:
        cmd = [sys.executable, "-m", "spacy", "download", model_name]
        if upgrade:
            cmd.append("--upgrade")

        print(f"Downloading spaCy model: {model_name}")
        result = run(cmd, capture_output=True, text=True)  # noqa: S603

        if result.returncode == 0:
            print(f"✓ Successfully downloaded {model_name}")
            return True
        else:
            print(f"✗ Failed to download {model_name}")
            print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Error downloading {model_name}: {e}")
        return False


def check_model_installed(model_name: str) -> bool:
    """Check if a spaCy model is already installed."""
    try:
        import spacy

        spacy.load(model_name)
        return True
    except (ImportError, OSError):
        return False


def list_available_models():
    """List all available models for each language."""
    print("\nAvailable spaCy models for Inconnu:\n")
    for lang, models in LANGUAGE_MODELS.items():
        print(f"{lang.upper()}:")
        for model in models:
            size = (
                "small" if "_sm" in model else "medium" if "_md" in model else "large"
            )
            if "_trf" in model:
                size = "transformer"
            default = " (default)" if model == DEFAULT_MODELS.get(lang) else ""
            installed = " [installed]" if check_model_installed(model) else ""
            print(f"  - {model} ({size}){default}{installed}")
        print()


def download_language_models(
    language: str, model_size: Optional[str] = None, upgrade: bool = False
) -> bool:
    """Download models for a specific language."""
    if language not in LANGUAGE_MODELS:
        print(f"✗ Language '{language}' not supported.")
        print(f"Supported languages: {', '.join(LANGUAGE_MODELS.keys())}")
        return False

    available_models = LANGUAGE_MODELS[language]

    if model_size:
        # Find model matching the requested size
        size_map = {
            "small": "_sm",
            "medium": "_md",
            "large": "_lg",
            "transformer": "_trf",
        }
        suffix = size_map.get(model_size.lower())
        if not suffix:
            print(f"✗ Invalid model size: {model_size}")
            print("Valid sizes: small, medium, large, transformer")
            return False

        model_to_download = None
        for model in available_models:
            if suffix in model:
                model_to_download = model
                break

        if not model_to_download:
            print(f"✗ No {model_size} model available for {language}")
            return False
    else:
        # Use default model
        model_to_download = DEFAULT_MODELS[language]

    # Check if already installed
    if check_model_installed(model_to_download) and not upgrade:
        print(f"✓ Model {model_to_download} is already installed")
        return True

    return download_model(model_to_download, upgrade)


def download_all_default_models(upgrade: bool = False) -> bool:
    """Download all default models."""
    success = True
    for model in DEFAULT_MODELS.values():
        if not download_model(model, upgrade):
            success = False
    return success


def print_uv_instructions():
    """Print instructions for UV users."""
    print("\n📘 UV Installation Instructions:")
    print("\nFor UV environments, models can be installed as dependencies:")
    print("    uv add 'inconnu[en]'         # English")
    print("    uv add 'inconnu[de]'         # German")
    print("    uv add 'inconnu[en,de,fr]'   # Multiple languages")
    print("    uv add 'inconnu[all]'        # All languages")
    print("\n  Larger models:")
    print("    uv add 'inconnu[en-lg]'      # English large")
    print("    uv add 'inconnu[en-trf]'     # English transformer")
    print("\n  Available sizes: sm (default), md, lg, trf (English only)")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Download spaCy language models for Inconnu",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  inconnu-download en                    # Download default English model (small)
  inconnu-download en --size large       # Download large English model
  inconnu-download de fr                 # Download German and French models
  inconnu-download all                   # Download all default models
  inconnu-download --list               # List all available models
  inconnu-download en --upgrade         # Upgrade English model
""",
    )

    parser.add_argument(
        "languages",
        nargs="*",
        help="Language code(s) to download models for (en, de, it, es, fr) or 'all'",
    )
    parser.add_argument(
        "--size",
        choices=["small", "medium", "large", "transformer"],
        help="Model size to download (default: small)",
    )
    parser.add_argument(
        "--upgrade", action="store_true", help="Upgrade existing models"
    )
    parser.add_argument("--list", action="store_true", help="List all available models")
    parser.add_argument(
        "--uv-help", action="store_true", help="Show UV installation instructions"
    )

    args = parser.parse_args()

    # Handle UV help
    if args.uv_help:
        print_uv_instructions()
        return

    # Handle list command
    if args.list:
        list_available_models()
        return

    # Require at least one language if not listing
    if not args.languages:
        if is_uv_environment():
            print("⚠️  UV environment detected!")
            print_uv_instructions()
            print("\nOr use 'inconnu-download --list' to see available models")
            print(
                "Or use 'inconnu-download LANG' to download via this tool (requires pip)"
            )
            return
        parser.error("Please specify language(s) to download or use --list")

    # Handle 'all' keyword
    if "all" in args.languages:
        if download_all_default_models(args.upgrade):
            print("\n✓ All default models downloaded successfully!")
        else:
            print("\n✗ Some models failed to download")
            sys.exit(1)
        return

    # Download specific languages
    success = True
    for lang in args.languages:
        if not download_language_models(lang, args.size, args.upgrade):
            success = False

    if success:
        print("\n✓ All requested models downloaded successfully!")
    else:
        print("\n✗ Some models failed to download")
        sys.exit(1)


if __name__ == "__main__":
    main()
