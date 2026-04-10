
import os
import requests
import json
from pathlib import Path

def list_alphas():
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
    
    # 1. Authenticate to get cookie
    print("Authenticating...")
    auth_resp = session.post(f"{base_url}/authentication", auth=(email, password))
    if auth_resp.status_code != 201:
        print(f"Authentication failed: {auth_resp.status_code} {auth_resp.text}")
        return
        
    token = session.cookies.get("t")
    if token:
        session.headers.update({"Authorization": f"Bearer {token}"})
    
    # 1.5. Get User ID
    me_resp = session.get(f"{base_url}/users/self")
    if me_resp.status_code != 200:
        print(f"Failed to get user info: {me_resp.status_code} {me_resp.text}")
        return
        
    me_data = me_resp.json()
    user_id = me_data.get("id")
    if not user_id:
        print(f"User ID not found in response: {me_resp.text}")
        return

    print(f"Authenticated as {me_data.get('username')} (ID: {user_id})")

    # 2. Get alphas (filtered by user)
    # Use the known working pattern for listing user-owned alphas
    resp = session.get(f"{base_url}/alphas?limit=50&offset=0")
    if resp.status_code == 200:
        data = resp.json()
        alphas = data.get("results", [])
        print(f"Found {len(alphas)} alphas in total.")
        submitted_count = 0
        for a in alphas:
            if a.get("isSubmitted"):
                submitted_count += 1
                print(f"ID: {a['id']} | Sharpe: {a['is']['sharpe']} | Status: {a['status']} | SUBMITTED: True")
                # Fetch expression
                expr_resp = session.get(f"{base_url}/alphas/{a['id']}")
                if expr_resp.status_code == 200:
                    print(f"  Expression: {expr_resp.json().get('regular')}")
        
        if submitted_count == 0:
            print("No submitted alphas found in the first 50 results.")
    else:
        print(f"Failed: {resp.status_code} {resp.text}")

if __name__ == "__main__":
    list_alphas()
