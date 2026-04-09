import os
import requests
import json
from pathlib import Path
from alpha_factory import BrainAPI

def test_submit():
    env_discovery = __import__("env_discovery")
    env_discovery.initialize_environment()
    email = os.getenv("BRAIN_EMAIL")
    password = os.getenv("BRAIN_PASSWORD")
    
    api = BrainAPI(email, password)
    
    alphas_to_test = ["QPjY8OlM"] # I saw this fail in submission_burst
    
    for alpha_id in alphas_to_test:
        print(f"Submitting {alpha_id}...")
        
        # Manually replicating the api.submit code to capture full raw output
        session = requests.Session()
        base_url = "https://api.worldquantbrain.com"
        auth = session.post(f"{base_url}/authentication", auth=(email, password))
        if auth.status_code == 201:
            token = session.cookies.get("t")
            if token:
                session.headers.update({"Authorization": f"Bearer {token}"})
        
        submit_url = f"{base_url}/alphas/{alpha_id}/submit"
        resp = session.post(submit_url)
        print(f"Status: {resp.status_code}")
        print("Response Text:")
        try:
            print(json.dumps(resp.json(), indent=2))
        except:
            print(resp.text)

if __name__ == "__main__":
    test_submit()
