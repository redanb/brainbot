
import os
import requests
import json
from datetime import datetime

# Load env specifically for GITHUB_TOKEN
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.append(str(Path.cwd()))
import env_discovery
env_discovery.initialize_environment()

def check_gha_health(owner="redanb", repo="brainbot"):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN not found in environment.")
        return
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs?per_page=10"
    
    try:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        runs = resp.json().get("workflow_runs", [])
        
        print(f"\nLast 10 GHA Runs for {owner}/{repo}:")
        print("-" * 60)
        for run in runs:
            status = run.get("status")
            conclusion = run.get("conclusion")
            created_at = run.get("created_at")
            name = run.get("name", "Unknown")
            print(f"[{created_at}] {name} | Status: {status} | Conclusion: {conclusion} | ID: {run['id']}")
            
            if conclusion == "failure":
                # Check for annotations
                ann_url = run.get("check_suite_url") + "/check-runs"
                # For simplicity, we can't easily get check-runs from this url directly without some parsing
                # But we can see if it was a scheduled or dispatch run
        print("-" * 60)
    except Exception as e:
        print(f"Error fetching GHA data: {e}")

if __name__ == "__main__":
    check_gha_health()
