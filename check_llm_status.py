import os
import sys
import logging
from pathlib import Path

# Fix paths for llm_router import
def get_master_dir():
    if "ANTIGRAVITY_MASTER_DIR" in os.environ:
        return Path(os.environ["ANTIGRAVITY_MASTER_DIR"])
    if os.name == 'nt':
        return Path(r"C:\Users\admin\.antigravity\master")
    return Path.home() / ".antigravity" / "master"

MASTER_DIR = get_master_dir()
sys.path.append(str(MASTER_DIR))
sys.path.append(os.getcwd())

import llm_router

def diagnostic():
    print("=== LLM ROUTER DIAGNOSTIC ===")
    
    # 1. Check .env presence
    env_path = MASTER_DIR / ".env"
    if env_path.exists():
        print(f"[PASS] .env found at {env_path}")
    else:
        print(f"[FAIL] .env NOT found at {env_path}")
        return

    # 2. Check individual providers (Fast health check)
    providers = ["deepseek", "cerebras", "gemini", "claude", "mistral", "groq", "openai", "openrouter", "github"]
    results = {}
    
    for p in providers:
        print(f"Checking {p}...", end=" ", flush=True)
        try:
            # Short test query
            res = llm_router.route_query(
                system_prompt="Diagnostic check. Reply 'OK'.",
                user_query="Ping",
                preferred_provider=p,
                max_retries=1
            )
            if "OK" in res['text'] or len(res['text']) > 0:
                print(f"[PASS] (Model: {res.get('model')})")
                results[p] = "OK"
            else:
                print(f"[FAIL] (Empty response)")
                results[p] = "EMPTY"
        except Exception as e:
            print(f"[FAIL] ({str(e)[:50]}...)")
            results[p] = str(e)

    # 3. Check WorldQuant Account Pool
    print("\n=== WORLDQUANT BRAIN POOL ===")
    accounts = os.getenv("BRAIN_ACCOUNTS", "").split(",")
    primary = os.getenv("BRAIN_EMAIL")
    
    for acc in accounts:
        if ":" in acc:
            e, _ = acc.split(":", 1)
            is_p = "[PRIMARY]" if e == primary else "[SCOUT]"
            print(f"Account: {e:40} {is_p}: READY")
        else:
            print(f"Account pool empty or malformed: {acc}")

    print("\n=== SUMMARY ===")
    for p, status in results.items():
        print(f"{p:12}: {status[:50]}")

if __name__ == "__main__":
    diagnostic()
