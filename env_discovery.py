
import os
import sys
from pathlib import Path
import logging

log = logging.getLogger("EnvDiscovery")

def discover_env_files():
    """
    Scans multiple locations for .env files and loads them into os.environ.
    Priority: CWD > Script Dir > User Home > Master Dir
    """
    search_paths = [
        Path.cwd(),
        Path(__file__).resolve().parent,
        Path.home() / ".antigravity" / "master",
        Path("C:/Users/admin/.antigravity/master") if os.name == "nt" else Path("/home/runner/.antigravity/master")
    ]
    
    # Add optional ANTIGRAVITY_MASTER_DIR
    if "ANTIGRAVITY_MASTER_DIR" in os.environ:
        search_paths.insert(0, Path(os.environ["ANTIGRAVITY_MASTER_DIR"]))

    loaded_files = []
    for path in search_paths:
        env_file = path / ".env"
        if env_file.exists():
            try:
                content = env_file.read_text(encoding="utf-8", errors="ignore")
                for line in content.splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        # setdefault to prioritize existing env vars (e.g. from GHA) over .env files
                        key = k.strip()
                        val = v.strip().strip('"').strip("'")
                        if key not in os.environ:
                            os.environ[key] = val
                loaded_files.append(str(env_file))
            except Exception as e:
                log.warning(f"Could not read {env_file}: {e}")
    
    return loaded_files

def resolve_key_aliases():
    """
    Standardizes key names based on common aliases.
    Example: OPENROUTER_API_KEY -> OPEN_ROUTER_KEY
    """
    aliases = {
        "OPEN_ROUTER_KEY": ["OPENROUTER_API_KEY", "OPENROUTER_KEY", "OR_API_KEY"],
        "GEMINI_API_KEY": ["GOOGLE_API_KEY", "GEMINI_KEY"],
        "ANTHROPIC_API_KEY": ["CLAUDE_API_KEY", "ANTHROPIC_KEY"],
        "OPENAI_API_KEY": ["OPENAI_KEY"],
        "TELEGRAM_TOKEN": ["TELEGRAM_API_KEY", "BOT_TOKEN"],
        "BRAIN_EMAIL": ["WQ_EMAIL", "WORLDQUANT_EMAIL"],
        "BRAIN_PASSWORD": ["WQ_PASSWORD", "WORLDQUANT_PASSWORD"]
    }
    
    for main_key, alias_list in aliases.items():
        if main_key not in os.environ or not os.environ[main_key]:
            for alias in alias_list:
                if alias in os.environ and os.environ[alias]:
                    os.environ[main_key] = os.environ[alias]
                    break

def initialize_environment():
    """Entry point for all scripts to ensure consistent env loading."""
    loaded = discover_env_files()
    resolve_key_aliases()
    return loaded

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    files = initialize_environment()
    print(f"Loaded .env from: {files}")
    # Print summary of found important keys (obfuscated)
    keys_to_check = ["BRAIN_EMAIL", "GEMINI_API_KEY", "OPEN_ROUTER_KEY", "TELEGRAM_TOKEN"]
    for k in keys_to_check:
        val = os.getenv(k)
        if val and len(val) >= 4:
            status = f"FOUND (...{val[-4:]})"
        elif val:
            status = "FOUND (too short to mask)"
        else:
            status = "MISSING"
        print(f"Key {k}: {status}")
