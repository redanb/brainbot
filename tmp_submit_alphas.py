import os
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")

try:
    import env_discovery
    env_discovery.initialize_environment()
except:
    pass

from alpha_factory import BrainAPI

p = Path(r"C:\Users\admin\.antigravity\master\evolution_log.json")
try:
    data = json.loads(p.read_text(encoding="utf-8"))
    brain = data.get("brain", [])
    
    # 1. Count qualified alphas
    qualified_unsubmitted = [
        x for x in brain 
        if x.get("sharpe", 0) >= 1.0 and "SUBMITTED" not in x.get("status", "")
    ]
    print(f"Number of qualified alphas generated in the last run that are NOT submitted: {len(qualified_unsubmitted)}")
    
    for alpha in qualified_unsubmitted:
        print(f" - Found Alpha: {alpha.get('alpha_id')} | Sharpe: {alpha.get('sharpe')} | Expression: {alpha.get('expression')[:50]}...")
    
    # 2. Submit them
    if not qualified_unsubmitted:
        print("No qualified alphas pending submission found in the log.")
    else:
        print("\nAuthenticating to Brain API...")
        api = BrainAPI()
        
        for alpha in qualified_unsubmitted:
            a_id = alpha.get("alpha_id")
            if not a_id or a_id == "NO_ID":
                continue
            print(f"Submitting {a_id}...")
            ok, err = api.submit(a_id)
            if ok:
                print(f"SUCCESS -> Submitted {a_id}")
                alpha["status"] = "SUBMITTED"
            else:
                print(f"FAIL -> Could not submit {a_id}: {err}")
                
        # save the log back
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print("\nEvolution log updated.")
        
except Exception as e:
    print(f"Error reading or processing log: {e}")
