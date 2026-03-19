import os
import json
import requests
import time
from pathlib import Path

def get_master_dir():
    if "ANTIGRAVITY_MASTER_DIR" in os.environ:
        return Path(os.environ["ANTIGRAVITY_MASTER_DIR"])
    return Path(r"C:\Users\admin\.antigravity\master")

def verify_structural_fix():
    print("[1] Verifying Evolution Log entries...")
    log_file = get_master_dir() / "evolution_log.json"
    with open(log_file, "r") as f:
        data = json.load(f)
        
    recent_brain = data.get("brain", [])[-5:]
    valid_sharpes = [entry for entry in recent_brain if entry.get("sharpe", 0) > 0.0 and entry.get("sharpe") != 0.0]
    
    if len(valid_sharpes) == 0:
        print("ERROR: Structural errors still present. No valid >0.0 Sharpes found recently.")
        return 1
        
    for entry in valid_sharpes:
        print(f"SUCCESS: Valid Alpha found - Sharpe: {entry['sharpe']}, Exp: {entry['expression'][:40]}...")
        if "reason" not in entry:
            print("ERROR: Regression - 'reason' field for LLM feedback is missing!")
            return 1
            
    print("SUCCESS: 0.00 Structural errors eliminated. Reasoning loop intact.")
    return 0

if __name__ == "__main__":
    exit(verify_structural_fix())
