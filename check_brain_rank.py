import os
import requests
import json
import env_discovery
from pathlib import Path

def get_brain_rank():
    files = env_discovery.initialize_environment()
    email = os.getenv("BRAIN_EMAIL")
    password = os.getenv("BRAIN_PASSWORD")
    
    if not email or not password:
        print("Missing credentials.")
        return

    base = "https://api.worldquantbrain.com"
    session = requests.Session()
    
    try:
        # Auth
        r = session.post(f"{base}/authentication", auth=(email, password), timeout=30)
        if r.status_code != 201:
            print(f"Auth failed: {r.status_code}")
            return
            
        # Get Me
        me_r = session.get(f"{base}/users/self", timeout=30)
        if me_r.status_code == 200:
            me = me_r.json()
            print("--- User Profile ---")
            print(json.dumps(me, indent=2))
            
        # Get Ranking (Singular - Correct API)
        rank_r = session.get(f"{base}/users/self/ranking", timeout=30)
        if rank_r.status_code == 200:
            ranks = rank_r.json()
            print("--- Leaderboard Status ---")
            print(json.dumps(ranks, indent=2))
        else:
            print(f"Ranking fetch failed: {rank_r.status_code}. Trying stats...")
            # Try statistics
            stats_r = session.get(f"{base}/users/self/statistics", timeout=30)
            if stats_r.status_code == 200:
                print("--- User Statistics ---")
                print(json.dumps(stats_r.json(), indent=2))
            
        # Try active competitions
        comp_r = session.get(f"{base}/competitions", timeout=30)
        if comp_r.status_code == 200:
            print("--- Active Competitions ---")
            results = comp_r.json()
            if isinstance(results, list):
                print(json.dumps(results[:2], indent=2))
            else:
                print(json.dumps(results, indent=2))
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_brain_rank()
