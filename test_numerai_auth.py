import os
import sys
from pathlib import Path

# Add brainbot and comp bet to path
sys.path.append(r"c:\Users\admin\Downloads\medsumag1\brainbot")
sys.path.append(r"c:\Users\admin\Downloads\medsumag1\comp bet")

import env_discovery
env_discovery.initialize_environment()

import numerapi

def test_auth():
    pub = os.environ.get("NUMERAI_PUBLIC_ID")
    sec = os.environ.get("NUMERAI_SECRET_KEY")
    
    if not pub or not sec:
        print("[FAIL] NUMERAI_PUBLIC_ID or NUMERAI_SECRET_KEY missing from environment.")
        return

    print(f"Testing with Public ID: {pub[:4]}...{pub[-4:]}")
    napi = numerapi.NumerAPI(public_id=pub, secret_key=sec)
    
    print("\n[ACTION] Attempting get_account_profile (requires 'read_user_info')...")
    try:
        profile = napi.get_account()
        print(f"[PASS] Successfully read account info for: {profile.get('username')}")
    except Exception as e:
        print(f"[FAIL] read_user_info failed: {e}")

    print("\n[ACTION] Attempting get_models (requires 'read_user_info' or 'upload_submissions')...")
    try:
        models = napi.get_models()
        print(f"[PASS] Models found: {list(models.keys())}")
    except Exception as e:
        print(f"[FAIL] get_models failed: {e}")

    print("\n[ACTION] Attempting to check submission status for 'anant0' (requires 'read_user_info')...")
    try:
        # We use a raw query if helper fails
        query = '{ submissions(modelId: "5fe67e13-8dae-4693-8294-84ddd8e8db80") { id status } }'
        res = napi.raw_query(query)
        print(f"[PASS] Successfully queried submissions.")
    except Exception as e:
        print(f"[FAIL] Query submissions failed: {e}")

if __name__ == "__main__":
    test_auth()
