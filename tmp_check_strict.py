import os
import json
from pathlib import Path

master_dir = Path(r"C:\Users\admin\.antigravity\master")
log_file = master_dir / "evolution_log.json"

if log_file.exists():
    data = json.loads(log_file.read_text())
    brain = data.get("brain", [])
    
    strict_candidates = []
    relaxed_candidates = []
    
    for entry in brain:
        if not entry.get("alpha_id") or entry.get("alpha_id") == "NO_ID": continue
        
        s = entry.get("sharpe", 0)
        f = entry.get("fitness", 0)
        t = entry.get("turnover", 1.0)
        status = entry.get("status", "")
        
        if status != "SUBMITTED":
            if s >= 1.0 and f >= 0.5 and t <= 0.8:
                relaxed_candidates.append(entry)
            if s >= 1.25 and f >= 1.0 and t <= 0.7:
                strict_candidates.append(entry)
                
    print(f"Total relaxed candidates: {len(relaxed_candidates)}")
    print(f"Total strict candidates: {len(strict_candidates)}")
else:
    print("No log file found.")
