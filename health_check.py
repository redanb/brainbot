"""
health_check.py
Pre-flight check for Trinity Pulse GHA Runners.
Exits 0 if all conditions are met, 1 otherwise.
"""
import os
import sys
import requests
import env_discovery
from pathlib import Path

def check_env():
    """Validate environment secrets."""
    print("Checking environment secrets...")
    # Load all possible .env files
    env_discovery.initialize_environment()
    
    required = ["BRAIN_EMAIL", "BRAIN_PASSWORD"]
    optional = ["GEMINI_API_KEY", "OPEN_ROUTER_KEY", "PERPLEXITY_API_KEY", "TELEGRAM_TOKEN", "GITHUB_TOKEN"]
    
    missing_req = [k for k in required if not os.getenv(k)]
    missing_opt = [k for k in optional if not os.getenv(k)]

    if missing_req:
        print(f"[FAIL] Missing required ENV vars: {', '.join(missing_req)}")
        return False
    print("[PASS] Essential ENV vars present.")

    if missing_opt:
        print(f"[WARN] Missing optional ENV vars: {', '.join(missing_opt)}")
    else:
        print("[PASS] All optional ENV vars present.")
    return True

def check_master_dir():
    env_discovery.initialize_environment()
    master_dir = os.getenv("ANTIGRAVITY_MASTER_DIR")
    if not master_dir:
        # Robust local fallback (RULE-100)
        if os.name == "nt":
            master_dir = r"C:\Users\admin\.antigravity\master"
        else:
            master_dir = str(Path.home() / ".antigravity" / "master")
        print(f"[WARN] ANTIGRAVITY_MASTER_DIR not set. Falling back to: {master_dir}")
    path = Path(master_dir)
    try:
        path.mkdir(parents=True, exist_ok=True)
        test_file = path / ".health_check"
        test_file.write_text("OK")
        test_file.unlink()
        print(f"[PASS] Master directory {master_dir} is writable.")
        return True
    except Exception as e:
        print(f"[FAIL] Master directory {master_dir} is not writable: {e}")
        return False

def check_worldquant_auth():
    """Validate WorldQuant API credentials with exponential backoff (RULE-112/116)."""
    import time
    email = os.getenv("BRAIN_EMAIL")
    password = os.getenv("BRAIN_PASSWORD")
    url = "https://api.worldquantbrain.com/authentication"
    
    max_retries = 3
    backoff = 5 # Start with 5s
    
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, auth=(email, password), timeout=15)
            if resp.status_code == 201:
                print(f"[PASS] WorldQuant API authentication successful (Attempt {attempt+1}).")
                return True
            elif resp.status_code == 429:
                print(f"[WARN] 429 Rate Limit Hit. Backing off for {backoff}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(backoff)
                backoff *= 2 # Exponential backoff
            else:
                print(f"[FAIL] WorldQuant Auth failed (Status {resp.status_code}): {resp.text[:100]}")
                return False
        except Exception as e:
            print(f"[FAIL] Connectivity error on attempt {attempt+1}: {e}")
            time.sleep(backoff)
            backoff *= 2
            
    print(f"[FAIL] WorldQuant Auth exhausted {max_retries} retries.")
    return False


def check_telegram():
    """Validate Telegram connectivity."""
    print("Checking Telegram connectivity...")
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "985485272")
    
    if not token:
        print("[WARN] TELEGRAM_TOKEN not found. Alerts will be skipped.")
        return True # Optional, don't fail health check
    
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            print(f"[PASS] Telegram Bot API reachable. Chat ID: {chat_id}")
            return True
        else:
            print(f"[WARN] Telegram Bot API returned {resp.status_code}. Alerts may fail.")
            return True # Optional
    except Exception as e:
        print(f"[WARN] Telegram connectivity error: {e}")
        return True # Optional

if __name__ == "__main__":
    print("--- TRINITY PULSE PRE-FLIGHT HEALTH CHECK ---")
    results = [
        check_env(),
        check_master_dir(),
        check_worldquant_auth(),
        check_telegram()
    ]
    # Filter for boolean False. Warp results in if any of them are False.
    if all(r is not False for r in results):
        print("--- ALL CHECKS PASSED. PROCEEDING TO FACTORY ---")
        sys.exit(0)
    else:
        print("--- PRE-FLIGHT CHECKS FAILED. ABORTING ---")
        sys.exit(1)
