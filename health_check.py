"""
health_check.py
Pre-flight check for Trinity Pulse GHA Runners.
Exits 0 if all conditions are met, 1 otherwise.
"""
import os
import sys
import requests
from pathlib import Path

def check_env():
    required = ["BRAIN_EMAIL", "BRAIN_PASSWORD", "GEMINI_API_KEY"]
    missing = [r for r in required if not os.getenv(r)]
    if missing:
        print(f"[FAIL] Missing required ENV vars: {', '.join(missing)}")
        return False
    print("[PASS] Essential ENV vars present.")
    return True

def check_master_dir():
    master_dir = os.getenv("ANTIGRAVITY_MASTER_DIR")
    if not master_dir:
        print("[FAIL] ANTIGRAVITY_MASTER_DIR not set.")
        return False
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
    email = os.getenv("BRAIN_EMAIL")
    password = os.getenv("BRAIN_PASSWORD")
    url = "https://api.worldquantbrain.com/authentication"
    try:
        resp = requests.post(url, auth=(email, password), timeout=10)
        if resp.status_code == 201:
            print("[PASS] WorldQuant API authentication successful.")
            return True
        else:
            print(f"[FAIL] WorldQuant Auth failed (Status {resp.status_code}): {resp.text[:100]}")
            return False
    except Exception as e:
        print(f"[FAIL] Connectivity error: {e}")
        return False

if __name__ == "__main__":
    print("--- TRINITY PULSE PRE-FLIGHT HEALTH CHECK ---")
    results = [
        check_env(),
        check_master_dir(),
        check_worldquant_auth()
    ]
    if all(results):
        print("--- ALL CHECKS PASSED. PROCEEDING TO FACTORY ---")
        sys.exit(0)
    else:
        print("--- PRE-FLIGHT CHECKS FAILED. ABORTING ---")
        sys.exit(1)
