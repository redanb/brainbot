import os
import json
import requests
import sys
from pathlib import Path
from datetime import datetime
from alpha_factory import BrainAPI, meets_submission_criteria

def perform_submission_burst():
    print("--- 🚀 TRINITY SUBMISSION BURST: GOD-LEVEL MODE 🚀 ---")
    
    # 1. Resolve Master Dir
    if "ANTIGRAVITY_MASTER_DIR" in os.environ:
        master_dir = Path(os.environ["ANTIGRAVITY_MASTER_DIR"])
    elif os.name == "nt":
        master_dir = Path(r"C:\Users\admin\.antigravity\master")
    else:
        master_dir = Path.home() / ".antigravity" / "master"
        
    log_file = master_dir / "evolution_log.json"
    audit_file = master_dir / "submission_audit.json"
    
    if not log_file.exists():
        print(f"Error: {log_file} not found.")
        return

    # 2. Load Qualified Alphas
    try:
        data = json.loads(log_file.read_text())
        brain_entries = data.get("brain", [])
    except Exception as e:
        print(f"Error reading log: {e}")
        return

    # Filter for candidates with Sharpe >= 1.0, Fitness >= 0.5 and valid Alpha ID
    candidates = []
    for entry in brain_entries:
        alpha_id = entry.get("alpha_id")
        if not alpha_id or alpha_id == "NO_ID":
            continue
            
        metrics = {
            "sharpe": entry.get("sharpe", 0.0),
            "fitness": entry.get("fitness", 0.0),
            "turnover": entry.get("turnover", 1.0)
        }
        
        if meets_submission_criteria(metrics):
            candidates.append({
                "id": alpha_id,
                "expr": entry.get("expression"),
                "sharpe": metrics["sharpe"]
            })

    if not candidates:
        print("No qualified alphas found in logs.")
        return

    print(f"Found {len(candidates)} qualified candidates. Filtering for unsubmitted...")

    # 3. Load Submission History and Deduplicate Expressions
    submitted_ids = set()
    submitted_exprs = set()
    if audit_file.exists():
        try:
            audit = json.loads(audit_file.read_text())
            for h in audit.get("brain", {}).get("history", []):
                if h.get("status") == "SUCCESS":
                    # Extract ID and Expr from details if possible
                    details = h.get("details", "")
                    if "SUBMITTED:" in details:
                        submitted_ids.add(details.split(":")[1].strip())
                    expr = h.get("expression")
                    if expr: submitted_exprs.add(expr)
        except:
            pass

    # Local deduplication for this burst
    to_submit = []
    seen_exprs = set()
    for c in candidates:
        if c["id"] not in submitted_ids and c["expr"] not in (submitted_exprs | seen_exprs):
            to_submit.append(c)
            seen_exprs.add(c["expr"])
    
    if not to_submit:
        print("All qualified or unique alphas already submitted.")
        return

    print(f"Ready to submit {len(to_submit)} UNIQUE, NEW alphas.")

    # 4. Initialize API
    import env_discovery
    env_discovery.initialize_environment()
    email = os.getenv("BRAIN_EMAIL")
    password = os.getenv("BRAIN_PASSWORD")
    
    if not email or not password:
        print("Missing BRAIN credentials.")
        return
        
    api = BrainAPI(email, password)
    
    # 5. Execute Burst
    count = 0
    any_success = False
    for alpha in to_submit:
        print(f"Submitting {alpha['id']} (Sharpe {alpha['sharpe']})...")
        success, error = api.submit(alpha["id"])
        if success:
            count += 1
            any_success = True
            # Update status in the in-memory log data
            for entry in brain_entries:
                if entry.get("alpha_id") == alpha["id"]:
                    entry["status"] = "SUBMITTED"
                    entry["submitted_at"] = datetime.now().isoformat()
            time.sleep(10) # Safety delay
        else:
            print(f"Submission failed for {alpha['id']}: {error[:60]}")
        
        if count >= 10: # Conservative burst limit per run
            print("Reached batch limit of 10 submissions.")
            break

    # 6. Save Updated Log if anything changed
    if any_success:
        try:
            data["brain"] = brain_entries
            log_file.write_text(json.dumps(data, indent=2))
            print(f"Updated {log_file} with new submission statuses.")
        except Exception as e:
            print(f"Error saving log updates: {e}")

    print(f"--- 🏁 BURST COMPLETE: {count} Submissions 🏁 ---")

if __name__ == "__main__":
    import time
    perform_submission_burst()
