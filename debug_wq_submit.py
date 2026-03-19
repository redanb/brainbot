
import os
import requests
import json
from pathlib import Path

def debug_submit():
    # Load env
    env_path = Path(r"C:\Users\admin\.antigravity\master\.env")
    env = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    
    email = env.get("BRAIN_EMAIL")
    password = env.get("BRAIN_PASSWORD")
    
    if not email or not password:
        print("Missing credentials")
        return

    session = requests.Session()
    base_url = "https://api.worldquantbrain.com"
    
    # Authenticate
    auth = session.post(f"{base_url}/authentication", auth=(email, password))
    if auth.status_code != 201:
        print(f"Auth failed: {auth.status_code} {auth.text}")
        return
    
    print("Authenticated successfully.")
    
    # Try to submit the known high-sharpe alpha that failed with 403
    alpha_id = "VkEEb31A" 
    print(f"Attempting to submit Alpha: {alpha_id}")
    
    resp = session.post(f"{base_url}/alphas/{alpha_id}/submit")
    print(f"Status Code: {resp.status_code}")
    print(f"Response: {resp.text}")
    
    # Also check alpha state
    state_resp = session.get(f"{base_url}/alphas/{alpha_id}")
    if state_resp.status_code == 200:
        print(f"Alpha State: {json.dumps(state_resp.json(), indent=2)}")

if __name__ == "__main__":
    debug_submit()
