import os
import sys
import json
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Union

# Add brainbot to path for env_discovery
sys.path.append(str(Path(__file__).resolve().parent))
try:
    import env_discovery
    env_discovery.initialize_environment()
except ImportError:
    print("[WARNING] env_discovery not found. Env vars might be missing.")

try:
    import evolution_tracker
except ImportError:
    evolution_tracker = None

def get_master_dir():
    if "ANTIGRAVITY_MASTER_DIR" in os.environ:
        return Path(os.environ["ANTIGRAVITY_MASTER_DIR"])
    return Path(r"C:\Users\admin\.antigravity\master")

def audit_worldquant():
    print("\n--- [AUDIT] WorldQuant Brain ---")
    log_path = get_master_dir() / "evolution_log.json"
    if not log_path.exists():
        print(f"[FAIL] evolution_log.json missing at {log_path}")
        return

    with open(log_path, 'r') as f:
        data = json.load(f)
    
    # evolution_tracker.py uses "brain" and "numerai" keys
    brain_subs = data.get("brain", [])
    if not brain_subs:
        print("[!] No WorldQuant submissions found in log.")
        return

    print(f"Total Logged Alphas: {len(brain_subs)}")
    latest = brain_subs[-1]
    print(f"Latest Submission: {latest.get('alpha_id')} at {latest.get('date')}")
    print(f"Current Status in Log: {latest.get('status')}")
    
    # Check for recent failures
    recent_failures = [s for s in brain_subs[-30:] if s.get('status') == 'FAIL']
    if recent_failures:
        print(f"[WARNING] {len(recent_failures)} of last 30 simulations failed.")
        print(f"Sample Reason: {recent_failures[0].get('reason')}")

def audit_numerai():
    print("\n--- [AUDIT] Numerai (anant0) ---")
    public_id = os.environ.get("NUMERAI_PUBLIC_ID")
    secret_key = os.environ.get("NUMERAI_SECRET_KEY")
    
    try:
        sys.path.append(r"c:\Users\admin\Downloads\medsumag1\comp bet")
        import numerapi
        if not public_id or not secret_key:
            print("[SKIP] Numerai credentials missing in environment.")
            return
            
        napi = numerapi.NumerAPI(public_id, secret_key)
        models = napi.get_models()
        model_id = models.get('anant0')
        print(f"Model ID (anant0): {model_id}")
        
        # Get submissions via robust methods
        print("Fetching performance data...")
        results = napi.round_model_performances_v2(model_id)
        
        if not results or not isinstance(results, list):
            print("[!] No performances found on platform for 'anant0'.")
        else:
            print(f"Found {len(results)} performance records.")
            for sub in results[:5]:
                if isinstance(sub, dict):
                    # round_model_performances_v2 returns a list of diet's
                    # Fields usually include 'roundNumber', 'corr', 'mmc', 'status'
                    print(f"  Round {sub.get('roundNumber')}: Corr={sub.get('corr', 'N/A')} | MMC={sub.get('mmc', 'N/A')}")
        
        # Explain Rank gap
        created_date = datetime(2026, 3, 3) # Account creation date
        days_active = (datetime.now() - created_date).days
        print(f"\nAccount age: {days_active} days (Since March 3, 2026)")
        
        if days_active < 28:
            print("[!] RANK EXPLANATION: Numerai requires 4 complete rounds (28 days) of consistent submissions.")
            print("    Your account is expected to be 'Unranked' until approx March 31, 2026.")
            print("    This is a platform policy, NOT a system failure.")
        
    except Exception as e:
        print(f"[FAIL] Numerai API/Import Error: {e}")

if __name__ == "__main__":
    audit_worldquant()
    audit_numerai()
    print("\nAudit Complete.")
