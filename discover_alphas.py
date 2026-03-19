
import os
import requests
from pathlib import Path

def discover_alphas():
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
    
    auth_resp = session.post(f"{base_url}/authentication", auth=(email, password))
    token = session.cookies.get("t")
    if token:
        session.headers.update({"Authorization": f"Bearer {token}"})
    
    me_resp = session.get(f"{base_url}/users/self")
    me_data = me_resp.json()
    user_id = me_data.get("id")
    print(f"User ID: {user_id} ({me_data.get('username')})")
    
    # Try different filters
    endpoints = [
        f"/alphas?user={user_id}&limit=100",
        f"/alphas?owner={user_id}&limit=100",
        f"/alphas?limit=100",
        f"/alphas?isSubmitted=true&limit=100"
    ]
    
    for ep in endpoints:
        print(f"\nChecking: {ep}")
        resp = session.get(f"{base_url}{ep}")
        if resp.status_code == 200:
            data = resp.json().get("results", [])
            print(f"  Found {len(data)} results.")
            for a in data:
                # If we filter by user/owner, all should be ours
                # If we don't, check if the ID matches or if we can see the owner
                print(f"  - ID: {a['id']} | Status: {a.get('status')} | Submitted: {a.get('isSubmitted')}")
        else:
            print(f"  Failed: {resp.status_code} {resp.text}")

if __name__ == "__main__":
    discover_alphas()
