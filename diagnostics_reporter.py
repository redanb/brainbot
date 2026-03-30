import os
import sys
import requests
from pathlib import Path

# Add CWD to sys.path
sys.path.append(str(Path.cwd()))
import env_discovery

def run_diagnostics():
    print("=== TRINITY GHA DIAGNOSTICS ===")
    env_discovery.initialize_environment()
    
    # 1. Check Node.js Force Env
    node_force = os.getenv("FORCE_JAVASCRIPT_ACTIONS_TO_NODE24")
    print(f"Node.js Force Env: {node_force} (Expected: true)")
    
    # 2. Check Primary Credentials
    email = os.getenv("BRAIN_EMAIL")
    password = os.getenv("BRAIN_PASSWORD")
    print(f"Primary Brain Email: {'SET' if email else 'MISSING'}")
    print(f"Primary Brain Password: {'SET' if password else 'MISSING'}")
    
    # 3. Check Account Pool (Phase 4)
    accounts_str = os.getenv("BRAIN_ACCOUNTS", "")
    accounts = [a.split(":") for a in accounts_str.split(",") if ":" in a]
    print(f"Multi-Account Pool: {len(accounts)} accounts found.")
    
    # 4. Check Auth Connectivity for Primary
    if email and password:
        url = "https://api.worldquantbrain.com/authentication"
        try:
            r = requests.post(url, auth=(email, password), timeout=15)
            print(f"Primary Auth Status: {r.status_code}")
            if r.status_code != 201:
                print(f"Primary Auth Error: {r.text[:200]}")
        except Exception as e:
            print(f"Primary Connectivity Error: {e}")
            
    # 5. Check Directory Mappings
    master_dir = os.getenv("ANTIGRAVITY_MASTER_DIR")
    print(f"Master Dir: {master_dir}")
    if master_dir:
        p = Path(master_dir)
        print(f"Master Dir Exists: {p.exists()}")
        try:
            p.mkdir(parents=True, exist_ok=True)
            print("Master Dir writable: True")
        except Exception as e:
            print(f"Master Dir writable: False ({e})")

if __name__ == "__main__":
    run_diagnostics()
