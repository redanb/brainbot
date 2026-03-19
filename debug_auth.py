
import os
import requests
import json
from pathlib import Path

def debug_auth():
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
    
    session = requests.Session()
    base_url = "https://api.worldquantbrain.com"
    
    # Authenticate
    print(f"Authenticating for {email}...")
    auth = session.post(f"{base_url}/authentication", auth=(email, password))
    print(f"Status: {auth.status_code}")
    print(f"Headers: {dict(auth.headers)}")
    try:
        data = auth.json()
        print(f"JSON Output: {json.dumps(data, indent=2)}")
    except:
        print(f"Text Output: {auth.text[:200]}")

if __name__ == "__main__":
    debug_auth()
