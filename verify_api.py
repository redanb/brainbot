
import os
import requests
import json
from pathlib import Path

def verify_api():
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
    
    # 1. Login to get cookie
    auth = session.post(f"{base_url}/authentication", auth=(email, password))
    token = session.cookies.get("t")
    if not token:
        print("Failed to get token from cookie.")
        return

    # 2. Set Bearer Header
    session.headers.update({"Authorization": f"Bearer {token}"})
    
    # 3. Check /users/self
    resp = session.get(f"{base_url}/users/self")
    print(f"Users/Self Status: {resp.status_code}")
    print(f"Users/Self Content: {json.dumps(resp.json(), indent=2)}")

if __name__ == "__main__":
    verify_api()
