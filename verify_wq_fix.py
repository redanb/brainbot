
import os
import sys
import json
from pathlib import Path

# Setup paths
BRAINBOT_DIR = Path(r"C:\Users\admin\Downloads\medsumag1\comp bet\brainbot")
sys.path.insert(0, str(BRAINBOT_DIR))

PASS = "[PASS]"
FAIL = "[FAIL]"

def verify():
    print("Verifying WorldQuant Submission Fix...")
    
    # 1. Check alpha_burst.py thresholds
    burst_content = (BRAINBOT_DIR / "alpha_burst.py").read_text(encoding="utf-8")
    if "if sharpe > 1.05 and fitness > 0.9:" in burst_content:
        print(f"{PASS} alpha_burst.py threshold updated to 1.05/0.9")
    else:
        print(f"{FAIL} alpha_burst.py threshold NOT found or incorrect")
        
    # 2. Check alpha_factory.py thresholds
    factory_content = (BRAINBOT_DIR / "alpha_factory.py").read_text(encoding="utf-8")
    if "CHAMPION_SHARPE = 1.05" in factory_content and "CHAMPION_FITNESS = 0.90" in factory_content:
        print(f"{PASS} alpha_factory.py thresholds updated to 1.05/0.9")
    else:
        print(f"{FAIL} alpha_factory.py thresholds NOT found or incorrect")

    # 3. Check for recent evolution log entries to ensure no more 403/SUBMIT_FAILED
    log_path = Path(r"C:\Users\admin\.antigravity\master\evolution_log.json")
    if log_path.exists():
        data = json.loads(log_path.read_text(encoding="utf-8"))
        recent = data.get("brain", [])[-5:]
        for entry in recent:
            status = entry.get("status")
            if status == "SUBMIT_FAILED":
                print(f"{FAIL} Recent log entry still shows SUBMIT_FAILED: {entry}")
            else:
                print(f"{PASS} Log entry shows safe status: {status}")

if __name__ == "__main__":
    verify()
