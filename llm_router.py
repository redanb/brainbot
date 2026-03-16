#!/usr/bin/env python3
"""
LLM Router v1.0 - Multi-Provider Intelligent Request Router
Primary: Google Gemini API (gemini-2.0-flash)
Fallback: Anthropic Claude API (claude-3-5-sonnet)
Emergency: Local template generation (no API)

Reads API keys from environment variables:
  GEMINI_API_KEY     - Google AI Studio key
  ANTHROPIC_API_KEY  - Anthropic Claude key

Usage:
    from llm_router import route_query
    result = route_query(system_prompt, user_query, depth="DEEP")
"""
import os
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

# ── Paths ──────────────────────────────────────────
MASTER_DIR = Path(r"C:\Users\admin\.antigravity\master")

# Add master to path for internal modules
sys.path.append(r"C:\Users\admin\.antigravity\master")
try:
    import healer_agent
except ImportError:
    healer_agent = None

# ── Logging ──────────────────────────────────────────
logger = logging.getLogger("LLMRouter")
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(asctime)s [ROUTER] %(message)s'))
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)
    logger.setLevel(logging.INFO)

IST = timezone(timedelta(hours=5, minutes=30))

# ── Manual .env Loader ───────────────────────────────
def _load_env_manually():
    """Load .env file if it exists (Master directory)."""
    env_path = MASTER_DIR / ".env"
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip()
        except Exception:
            pass

_load_env_manually()

# ── Telemetry ────────────────────────────────────────
TELEMETRY_FILE = Path(r"C:/Users/admin/.antigravity/master/llm_router_telemetry.jsonl")

def _log_telemetry(provider: str, status: str, latency_ms: int, tokens: int = 0, error: str = ""):
    """Append structured telemetry for audit trail."""
    entry = {
        "timestamp": datetime.now(IST).isoformat(),
        "provider": provider,
        "status": status,
        "latency_ms": latency_ms,
        "tokens": tokens,
        "error": error,
    }
    try:
        with open(TELEMETRY_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


# ============================================================
from typing import TypedDict, Annotated, List, Dict, Any, Optional

def _call_gemini(system_prompt: str, user_query: str, model: str = "gemini-2.0-flash", **kwargs) -> dict:
    """
    Call Google Gemini API via google-genai SDK.
    Returns: {"text": str, "tokens": int, "provider": "gemini", "model": str}
    """
    api_key = kwargs.get("api_key")
    
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY not set in environment")

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise ImportError("google-genai package not installed. Run: pip install google-genai")

    client = genai.Client(api_key=api_key)

    start = time.time()
    response = client.models.generate_content(
        model=model,
        contents=user_query,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.3,
            max_output_tokens=4096,
        ),
    )
    latency_ms = int((time.time() - start) * 1000)

    text = response.text if response.text else ""
    tokens = 0
    if hasattr(response, 'usage_metadata') and response.usage_metadata:
        tokens = getattr(response.usage_metadata, 'total_token_count', 0)

    # Obfuscate key for telemetry
    key_hint = "unknown"
    if api_key and isinstance(api_key, str) and len(api_key) > 4:
        key_str = str(api_key)
        key_hint = f"...{key_str[-4:]}" # type: ignore
    
    _log_telemetry(f"gemini({key_hint})", "SUCCESS", latency_ms, tokens)
    logger.info(f"Gemini OK - {latency_ms}ms - {tokens} tokens - model={model} - key={key_hint}")

    return {
        "text": text,
        "tokens": tokens,
        "provider": "gemini",
        "model": model,
        "latency_ms": latency_ms,
    }


# ============================================================
# PROVIDER 2: Anthropic Claude (FALLBACK)
# ============================================================

def _call_claude(system_prompt: str, user_query: str, model: str = "claude-3-5-sonnet-20241022", **kwargs) -> dict:
    """
    Call Anthropic Claude API via anthropic SDK.
    Returns: {"text": str, "tokens": int, "provider": "claude", "model": str}
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY not set in environment")

    try:
        import anthropic
    except ImportError:
        raise ImportError("anthropic package not installed. Run: pip install anthropic")

    client = anthropic.Anthropic(api_key=api_key)

    start = time.time()
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_query}],
        temperature=0.3,
    )
    latency_ms = int((time.time() - start) * 1000)

    text = ""
    if response.content:
        text = response.content[0].text if hasattr(response.content[0], 'text') else str(response.content[0])

    tokens = getattr(response.usage, 'input_tokens', 0) + getattr(response.usage, 'output_tokens', 0)

    _log_telemetry("claude", "SUCCESS", latency_ms, tokens)
    logger.info(f"Claude OK - {latency_ms}ms - {tokens} tokens - model={model}")

    return {
        "text": text,
        "tokens": tokens,
        "provider": "claude",
        "model": model,
        "latency_ms": latency_ms,
    }


# ============================================================
# PROVIDER 3: OpenAI (GPT-4o Fallback)
# ============================================================

def _call_openai(system_prompt: str, user_query: str, model: str = "gpt-4o", **kwargs) -> dict:
    """
    Call OpenAI API via openai SDK.
    Returns: {"text": str, "tokens": int, "provider": "openai", "model": str}
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY not set in environment")

    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai package not installed. Run: pip install openai")

    client = OpenAI(api_key=api_key)

    start = time.time()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ],
        temperature=0.3,
        max_tokens=4096,
    )
    latency_ms = int((time.time() - start) * 1000)

    text = response.choices[0].message.content
    tokens = response.usage.total_tokens

    _log_telemetry("openai", "SUCCESS", latency_ms, tokens)
    logger.info(f"OpenAI OK - {latency_ms}ms - {tokens} tokens - model={model}")

    return {
        "text": text,
        "tokens": tokens,
        "provider": "openai",
        "model": model,
        "latency_ms": latency_ms,
    }

# ============================================================
# PROVIDER 4: Groq (High Performance Fallback)
# ============================================================

def _call_groq(system_prompt: str, user_query: str, model: str = "llama3-70b-8192", **kwargs) -> dict:
    """
    Call Groq API via groq SDK.
    """
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY not set in environment")

    try:
        from groq import Groq
    except ImportError:
        raise ImportError("groq package not installed. Run: pip install groq")

    client = Groq(api_key=api_key)

    start = time.time()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ],
        temperature=0.3,
        max_tokens=4096,
    )
    latency_ms = int((time.time() - start) * 1000)

    text = response.choices[0].message.content
    tokens = response.usage.total_tokens

    _log_telemetry("groq", "SUCCESS", latency_ms, tokens)
    logger.info(f"Groq OK - {latency_ms}ms - {tokens} tokens - model={model}")

    return {
        "text": text,
        "tokens": tokens,
        "provider": "groq",
        "model": model,
        "latency_ms": latency_ms,
    }

# ============================================================
# PROVIDER 5: XAI (Grok)
# ============================================================

def _call_xai(system_prompt: str, user_query: str, model: str = "grok-beta", **kwargs) -> dict:
    """
    Call XAI API.
    """
    api_key = os.environ.get("XAI_API_KEY", "")
    if not api_key:
        raise EnvironmentError("XAI_API_KEY not set in environment")

    # Assuming openai compatibility for XAI
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai package not installed (used for XAI). Run: pip install openai")

    client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            temperature=0.3,
        )
    except Exception as e:
        if "Model not found" in str(e):
            # Fallback to known stable names if beta/latest fails
            for alt_model in ["grok-2", "grok-3-mini", "grok-2-1212"]:
                try:
                    logger.info(f"XAI model {model} not found. Retrying with {alt_model}...")
                    response = client.chat.completions.create(
                        model=alt_model,
                        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_query}],
                        temperature=0.3,
                    )
                    model = alt_model
                    break
                except:
                    continue
            else:
                raise e
        else:
            raise e

    start = time.time() # This was misplaced above, but keeping it for structure
    latency_ms = int((time.time() - start) * 1000)

    text = response.choices[0].message.content
    tokens = response.usage.total_tokens

    _log_telemetry("xai", "SUCCESS", latency_ms, tokens)
    logger.info(f"XAI OK - {latency_ms}ms - {tokens} tokens - model={model}")

    return {
        "text": text,
        "tokens": tokens,
        "provider": "xai",
        "model": model,
        "latency_ms": latency_ms,
    }


# ============================================================
# PROVIDER 6: Perplexity (Sonar)
# ============================================================

def _call_perplexity(system_prompt: str, user_query: str, model: str = "sonar-reasoning", **kwargs) -> dict:
    """
    Call Perplexity API (Sonar).
    """
    api_key = os.environ.get("PERPLEXITY_API_KEY", "")
    if not api_key:
        raise EnvironmentError("PERPLEXITY_API_KEY not set in environment")

    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai package not installed (used for Perplexity). Run: pip install openai")

    client = OpenAI(api_key=api_key, base_url="https://api.perplexity.ai")

    start = time.time()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ],
        temperature=0.3,
    )
    latency_ms = int((time.time() - start) * 1000)

    text = response.choices[0].message.content
    tokens = response.usage.total_tokens

    _log_telemetry("perplexity", "SUCCESS", latency_ms, tokens)
    logger.info(f"Perplexity OK - {latency_ms}ms - {tokens} tokens - model={model}")

    return {
        "text": text,
        "tokens": tokens,
        "provider": "perplexity",
        "model": model,
        "latency_ms": latency_ms,
    }


# ============================================================
# PROVIDER 7: Local Template (EMERGENCY FALLBACK)
# ============================================================

def _local_template(system_prompt: str, user_query: str, **kwargs) -> dict:
    """
    Emergency fallback when no API is available.
    """
    _log_telemetry("local_template", "FALLBACK", 0, 0, "No API keys available")
    logger.warning("FALLBACK: Using local template - no LLM API available")
    return {
        "text": f"[LOCAL TEMPLATE] System Role: {system_prompt[:100]}... Query: {user_query}",
        "tokens": 0, "provider": "local_template", "model": "none", "latency_ms": 0,
    }


# ============================================================
# MAIN ROUTER - Cascading Fallback
# ============================================================

PROVIDER_CHAIN = [
    ("gemini", _call_gemini),
    ("xai", _call_xai),
    ("perplexity", _call_perplexity),
    ("groq", _call_groq),
    ("claude", _call_claude),
    ("openai", _call_openai),
    ("healer", None),
    ("local_template", _local_template),
]

def route_query(system_prompt: str, user_query: str, depth: str = "STANDARD",
                preferred_provider: str = "", max_retries: int = 2) -> dict:
    """
    Route a query through the provider chain with cascading fallback.

    Priority: Gemini (primary) -> Claude (fallback) -> Local Template (emergency)

    Args:
        system_prompt: The persona's system prompt
        user_query: The user's query
        depth: FAST/STANDARD/DEEP - affects model selection
        preferred_provider: Force a specific provider ("gemini", "claude")
        max_retries: Number of retries per provider before cascading

    Returns:
        dict with keys: text, tokens, provider, model, latency_ms
    """
    # Depth -> model mapping
    gemini_model_map = {
        "FAST": "models/gemini-2.0-flash-lite",
        "STANDARD": "models/gemini-2.0-flash-lite",
        "DEEP": "models/gemini-2.0-flash-lite",
    }

    claude_model_map = {
        "FAST": "claude-3-5-haiku-20241022",
        "STANDARD": "claude-3-5-sonnet-20241022",
        "DEEP": "claude-3-5-sonnet-latest",
    }

    perplexity_model_map = {
        "FAST": "sonar-small-chat",
        "STANDARD": "sonar",
        "DEEP": "sonar-reasoning",
    }

    # Build provider chain (respect preferred_provider if set)
    chain = PROVIDER_CHAIN
    if preferred_provider:
        chain = [(n, f) for n, f in PROVIDER_CHAIN if n == preferred_provider] + \
                [(n, f) for n, f in PROVIDER_CHAIN if n != preferred_provider]

    last_error = None
    for provider_name, provider_func in chain:
        for attempt in range(max_retries):
            try:
                if provider_name == "gemini":
                    # Cycle through multiple Gemini keys if available
                    gemini_keys = [os.environ.get("GEMINI_API_KEY")] + \
                                  [os.environ.get(f"GEMINI_API_KEY_{i}") for i in range(1, 6)]
                    valid_keys = [k for k in gemini_keys if k]
                    
                    if not valid_keys:
                        raise EnvironmentError("No GEMINI_API_KEY found in environment")
                    
                    model = gemini_model_map.get(depth, "models/gemini-1.5-flash")
                    
                    # Try each key until success or exhaust
                    for key in valid_keys:
                        try:
                            # Use casting or ignore if type checker is confused by signature variations
                            res = provider_func(system_prompt, user_query, model=model, api_key=key) # type: ignore
                            return res
                        except Exception as ge:
                            if "429" in str(ge) or "QUOTA" in str(ge).upper() or "EXHAUSTED" in str(ge).upper():
                                # type: ignore
                                log_key = str(key)[-4:] if key else "????"
                                logger.warning(f"Gemini Key ...{log_key} exhausted. Rotating to next key...")
                                continue
                            raise ge
                    raise Exception("All Gemini keys exhausted")

                elif provider_name == "claude":
                    model = claude_model_map.get(depth, "claude-3-5-sonnet-20241022")
                    return provider_func(system_prompt, user_query, model=model)
                elif provider_name == "perplexity":
                    model = perplexity_model_map.get(depth, "sonar-reasoning")
                    return provider_func(system_prompt, user_query, model=model)
                elif provider_name == "healer":
                    if healer_agent:
                        return healer_agent.heal_and_retry(system_prompt, user_query, last_error or "Unknown cascade failure")
                    continue
                else:
                    if provider_func:
                        return provider_func(system_prompt, user_query) # type: ignore
                    continue
            except Exception as e:
                last_error = str(e)
                _log_telemetry(provider_name, "FAILED", 0, 0, last_error)
                logger.warning(f"{provider_name} attempt {attempt+1}/{max_retries} failed: {last_error}")
                if attempt < max_retries - 1:
                    time.sleep(1)  # Brief pause before retry
                continue

        logger.info(f"{provider_name} exhausted {max_retries} retries, cascading to next provider...")

    # Should never reach here (local_template always succeeds), but just in case
    return _local_template(system_prompt, user_query)


def check_api_status() -> dict:
    """Check which API keys are available (without revealing values)."""
    # Count Gemini keys
    gemini_keys = [os.environ.get("GEMINI_API_KEY")] + [os.environ.get(f"GEMINI_API_KEY_{i}") for i in range(1, 6)]
    gemini_count = len([k for k in gemini_keys if k])

    status = {
        "gemini": {
            "key_set": gemini_count > 0,
            "count": gemini_count,
            "priority": "PRIMARY (ROTATING)",
        },
        "groq": {
            "key_set": bool(os.environ.get("GROQ_API_KEY")),
            "priority": "HIGH_PERF_FALLBACK",
        },
        "claude": {
            "key_set": bool(os.environ.get("ANTHROPIC_API_KEY")),
            "priority": "FALLBACK",
        },
        "openai": {
            "key_set": bool(os.environ.get("OPENAI_API_KEY")),
            "priority": "FALLBACK",
        },
        "xai": {
            "key_set": bool(os.environ.get("XAI_API_KEY")),
            "priority": "EXPERIMENTAL",
        },
        "local_template": {
            "key_set": True,
            "priority": "EMERGENCY",
        },
    }
    return status


if __name__ == "__main__":
    print("LLM Router v1.0 - API Status Check")
    print("=" * 40)
    status = check_api_status()
    for name, info in status.items():
        key_status = "[SET]" if info["key_set"] else "[MISSING]"
        print(f"  {name:20s} {key_status:10s} Priority: {info['priority']}")

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        print(f"\nTest routing: {query[:60]}...")
        result = route_query(
            system_prompt="You are a helpful AI assistant specializing in AI governance.",
            user_query=query,
            depth="STANDARD"
        )
        print(f"\nProvider: {result['provider']} ({result['model']})")
        print(f"Latency:  {result['latency_ms']}ms")
        print(f"Tokens:   {result['tokens']}")
        print(f"Response: {result['text'][:500]}...")
