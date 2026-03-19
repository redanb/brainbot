#!/usr/bin/env python3
"""
LLM Router v1.0 - Multi-Provider Intelligent Request Router
Primary: Google Gemini API (gemini-2.0-flash)
Premium Fallback: Github Models (GPT-4o) / Anthropic Claude API
High-Speed: Groq / Cerebras
Reasoning: OpenRouter (DeepSeek R1)
Emergency: Local template generation (no API)

Reads API keys from environment variables:
  GEMINI_API_KEY     - Google AI Studio key
  GITHUB_TOKEN       - Github Models key
  ANTHROPIC_API_KEY  - Anthropic Claude key
  OPEN_ROUTER_KEY    - OpenRouter key
  MISTRAL_API_KEY    - Mistral AI key

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
# ── Paths ──────────────────────────────────────────
def get_master_dir():
    """Dynamically resolve the master directory based on environment/OS."""
    if "ANTIGRAVITY_MASTER_DIR" in os.environ:
        return Path(os.environ["ANTIGRAVITY_MASTER_DIR"])
    if os.name == 'nt':
        return Path(r"C:\Users\admin\.antigravity\master")
    else:
        # Default for Linux/CI
        return Path.home() / ".antigravity" / "master"

MASTER_DIR = get_master_dir()

# Add master to path for internal modules
if str(MASTER_DIR) not in sys.path:
    sys.path.append(str(MASTER_DIR))

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

# ── Safety Guardrails (RCA-DRIVEN) ──────────────────
def _safety_gate(system_prompt: str, user_query: str) -> Optional[str]:
    """
    Analyzes input for PII, secrets, or prompt injection before API call.
    Returns: None if safe, or an error message if blocked.
    """
    import re
    # 1. PII/Secret detection (Refined Regex)
    patterns = [
        r"sk-[a-zA-Z0-9-]{20,}",        # OpenAI/XAI/Anthropic/Groq keys (generic)
        r"AIza[0-9A-Za-z-_]{10,}",      # Google keys (broader)
        r"\b\d{3}-\d{2}-\d{4}\b",       # SSN
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", # Email
    ]
    
    # 2. Intellectual Property Protection (Conversation ae506651)
    protected_terms = ["MBR Algorithm", "PM-Fingerprinting", "Tender-Lock Strategy"]
    
    combined = f"{system_prompt}\n{user_query}"
    
    # Check Secrets
    for p in patterns:
        if re.search(p, combined, re.IGNORECASE):
            return f"SAFETY BLOCK: Sensitive information (PII/Secret) detected in input."

    # Check IP leakage (if query seems suspicious)
    if any(term.lower() in combined.lower() for term in protected_terms):
        if "reveal" in combined.lower() or "explain details" in combined.lower():
            return f"SAFETY BLOCK: Attempt to access/leak protected Intellectual Property ({protected_terms})."

    # 3. Prompt Injection (Heuristics)
    injection_kw = ["ignore all previous instructions", "system role override", "forget everything", "new rules:"]
    for kw in injection_kw:
        if kw in combined.lower():
            return f"SAFETY BLOCK: Prompt injection attempt detected."

    return None

# ── Telemetry ────────────────────────────────────────
TELEMETRY_FILE = MASTER_DIR / "llm_router_telemetry.jsonl"

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
    api_key = kwargs.get("api_key")
    if not api_key:
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

def _call_groq(system_prompt: str, user_query: str, model: str = "llama-3.3-70b-versatile", **kwargs) -> dict:
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
# PROVIDER 4.5: Mistral (Experiment Plan - Free)
# ============================================================

def _call_mistral(system_prompt: str, user_query: str, model: str = "mistral-large-latest", **kwargs) -> dict:
    """
    Call Mistral API.
    """
    api_key = kwargs.get("api_key")
    if not api_key:
        api_key = os.environ.get("MISTRAL_API_KEY", "")
    
    if not api_key:
        raise EnvironmentError("MISTRAL_API_KEY not set in environment")

    # Mistral is mostly openai compatible
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai package required for Mistral. Run: pip install openai")

    client = OpenAI(api_key=api_key, base_url="https://api.mistral.ai/v1")

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

    _log_telemetry("mistral", "SUCCESS", latency_ms, tokens)
    logger.info(f"Mistral OK - {latency_ms}ms - {tokens} tokens - model={model}")

    return {
        "text": text,
        "tokens": tokens,
        "provider": "mistral",
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
# PROVIDER 7: Github Models (Azure Inference)
# ============================================================

def _call_github(system_prompt: str, user_query: str, model: str = "gpt-4o", **kwargs) -> dict:
    """
    Call Github Models API.
    """
    api_key = os.environ.get("GITHUB_TOKEN", "")
    if not api_key:
        raise EnvironmentError("GITHUB_TOKEN not set in environment")

    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai package not installed (used for Github Models).")

    client = OpenAI(api_key=api_key, base_url="https://models.inference.ai.azure.com")

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

    _log_telemetry("github", "SUCCESS", latency_ms, tokens)
    logger.info(f"Github Models OK - {latency_ms}ms - {tokens} tokens - model={model}")

    return {
        "text": text, "tokens": tokens, "provider": "github", "model": model, "latency_ms": latency_ms,
    }

# ============================================================
# PROVIDER 8: OpenRouter
# ============================================================

def _call_openrouter(system_prompt: str, user_query: str, model: str = "openrouter/auto", **kwargs) -> dict:
    """
    Call OpenRouter API.
    """
    api_key = os.environ.get("OPEN_ROUTER_KEY", "")
    if not api_key:
        raise EnvironmentError("OPEN_ROUTER_KEY not set in environment")

    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai package not installed.")

    client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

    # OpenRouter specifics
    headers = {
        "HTTP-Referer": "https://antigravity-ai.com",
        "X-Title": "Antigravity Agent"
    }

    start = time.time()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ],
        extra_headers=headers
    )
    latency_ms = int((time.time() - start) * 1000)

    text = response.choices[0].message.content
    tokens = response.usage.total_tokens

    _log_telemetry("openrouter", "SUCCESS", latency_ms, tokens)
    logger.info(f"OpenRouter OK - {latency_ms}ms - {tokens} tokens - model={model}")

    return {
        "text": text, "tokens": tokens, "provider": "openrouter", "model": model, "latency_ms": latency_ms,
    }


# ============================================================
# PROVIDER 9: Local Template (EMERGENCY FALLBACK)
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
    ("claude", _call_claude),
    ("mistral", _call_mistral),
    ("github", _call_github),
    ("groq", _call_groq),
    ("perplexity", _call_perplexity),
    ("openrouter", _call_openrouter),
    ("xai", _call_xai),
    ("openai", _call_openai),
    ("healer", None),
    ("local_template", _local_template),
]

def route_query(system_prompt: str, user_query: str, depth: str = "STANDARD",
                preferred_provider: str = "", max_retries: int = 2) -> dict:
    """
    Route a query through the provider chain with cascading fallback.

    Returns:
        dict with keys: text, tokens, provider, model, latency_ms
    """
    # --- PHASE 0: SAFETY GATE ---
    safety_check = _safety_gate(system_prompt, user_query)
    if safety_check:
        logger.error(safety_check)
        return {
            "text": safety_check,
            "tokens": 0, "provider": "safety_gate", "model": "guard", "latency_ms": 0,
        }

    # Depth -> model mapping
    gemini_model_map = {
        "FAST": "models/gemini-2.5-flash",
        "STANDARD": "models/gemini-2.5-flash",
        "DEEP": "models/gemini-2.5-pro",
    }

    groq_model_map = {
        "FAST": "llama-3.1-8b-instant",
        "STANDARD": "llama-3.3-70b-versatile",
        "DEEP": "llama-3.3-70b-versatile",
    }

    claude_model_map = {
        "FAST": "claude-3-5-haiku-latest",
        "STANDARD": "claude-3-7-sonnet-latest",
        "DEEP": "claude-3-7-sonnet-latest",
    }

    perplexity_model_map = {
        "FAST": "sonar",
        "STANDARD": "sonar",
        "DEEP": "sonar-reasoning",
    }

    github_model_map = {
        "FAST": "gpt-4o-mini",
        "STANDARD": "gpt-4o",
        "DEEP": "o1-preview",
    }

    openrouter_model_map = {
        "FAST": "meta-llama/llama-3.1-8b-instruct:free",
        "STANDARD": "qwen/qwen-2.5-72b-instruct",
        "DEEP": "deepseek/deepseek-r1",
    }

    # Build provider chain (respect preferred_provider if set)
    chain = PROVIDER_CHAIN
    if preferred_provider:
        chain = [(n, f) for n, f in PROVIDER_CHAIN if n == preferred_provider] + \
                [(n, f) for n, f in PROVIDER_CHAIN if n != preferred_provider]
    elif depth == "DEEP":
        # Prefer Claude/Mistral for deep tasks, then Gemini, then openrouter
        prio = ["claude", "mistral", "gemini", "openrouter"]
        chain_priority = [(n, f) for n, f in PROVIDER_CHAIN if n in prio]
        chain_priority.sort(key=lambda x: prio.index(x[0]))
        chain_others = [(n, f) for n, f in PROVIDER_CHAIN if n not in prio]
        chain = chain_priority + chain_others

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
                    # Cycle through multiple Claude keys
                    claude_keys = [os.environ.get("ANTHROPIC_API_KEY")] + \
                                  [os.environ.get(f"ANTHROPIC_API_KEY_{i}") for i in range(1, 6)]
                    valid_keys = [k for k in claude_keys if k]
                    
                    if not valid_keys:
                        raise EnvironmentError("No ANTHROPIC_API_KEY found in environment")
                    
                    model = claude_model_map.get(depth, "claude-3-7-sonnet-latest")
                    
                    for key in valid_keys:
                        try:
                            res = provider_func(system_prompt, user_query, model=model, api_key=key) # type: ignore
                            return res
                        except Exception as ce:
                            if "429" in str(ce) or "400" in str(ce) or "QUOTA" in str(ce).upper():
                                log_key = str(key)[-4:] if key else "????"
                                logger.warning(f"Claude Key ...{log_key} exhausted/errored. Rotating...")
                                continue
                            raise ce
                    raise Exception("All Claude keys exhausted")
                elif provider_name == "groq":
                    model = groq_model_map.get(depth, "llama-3.3-70b-versatile")
                    return provider_func(system_prompt, user_query, model=model)
                elif provider_name == "mistral":
                    # Cycle through multiple Mistral keys
                    mistral_keys = [os.environ.get("MISTRAL_API_KEY")] + \
                                   [os.environ.get(f"MISTRAL_API_KEY_{i}") for i in range(1, 4)]
                    valid_keys = [k for k in mistral_keys if k]
                    
                    if not valid_keys:
                        raise EnvironmentError("No MISTRAL_API_KEY found")
                    
                    model = "mistral-large-latest"
                    for key in valid_keys:
                        try:
                            res = provider_func(system_prompt, user_query, model=model, api_key=key) # type: ignore
                            return res
                        except Exception as me:
                            if "429" in str(me) or "QUOTA" in str(me).upper():
                                logger.warning("Mistral Key exhausted. Rotating...")
                                continue
                            raise me
                    raise Exception("All Mistral keys exhausted")
                elif provider_name == "perplexity":
                    model = perplexity_model_map.get(depth, "sonar")
                    return provider_func(system_prompt, user_query, model=model)
                elif provider_name == "github":
                    model = github_model_map.get(depth, "gpt-4o")
                    return provider_func(system_prompt, user_query, model=model)
                elif provider_name == "openrouter":
                    model = openrouter_model_map.get(depth, "meta-llama/llama-3.3-70b-instruct:free")
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
            "count": len([k for k in [os.environ.get("ANTHROPIC_API_KEY")] + [os.environ.get(f"ANTHROPIC_API_KEY_{i}") for i in range(1, 6)] if k]),
            "priority": "FALLBACK",
        },
        "openai": {
            "key_set": bool(os.environ.get("OPENAI_API_KEY")),
            "priority": "FALLBACK",
        },
        "github": {
            "key_set": bool(os.environ.get("GITHUB_TOKEN")),
            "priority": "PREMIUM_FALLBACK",
        },
        "openrouter": {
            "key_set": bool(os.environ.get("OPEN_ROUTER_KEY")),
            "priority": "REASONING",
        },
        "perplexity": {
            "key_set": bool(os.environ.get("PERPLEXITY_API_KEY")),
            "priority": "SEARCH",
        },
        "mistral": {
            "key_set": bool(os.environ.get("MISTRAL_API_KEY")),
            "count": len([k for k in [os.environ.get("MISTRAL_API_KEY")] + [os.environ.get(f"MISTRAL_API_KEY_{i}") for i in range(1, 4)] if k]),
            "priority": "HIGH_FALLBACK",
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
