
import os
import requests
import json
import time
from pathlib import Path

def burst_oracle():
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
    
    # 1. Login
    auth = session.post(f"{base_url}/authentication", auth=(email, password))
    token = session.cookies.get("t")
    if not token:
        print("Auth failed.")
        return
    session.headers.update({"Authorization": f"Bearer {token}"})
    
    # Check permissions
    me_data = session.get(f"{base_url}/users/self").json()
    print(f"Logged in as {me_data.get('username')} ({me_data.get('id')})")

    # ORACLE ALPHAS (Passes IQC)
    ORACLE_LIST = [
        {"name": "Reversal_Vol_Weighted", "expr": "group_neutralize(rank(-1 * ts_delta(close, 5) * ts_rank(volume, 5)), SUBINDUSTRY)"},
        {"name": "Fundamental_Quality", "expr": "group_neutralize(rank(ts_mean(fnd6_fopo, 20) / debt_lt), SUBINDUSTRY)"},
        {"name": "Momentum_Decay", "expr": "group_neutralize(rank(ts_decay_linear(ts_delta(close, 1), 10)), SUBINDUSTRY)"}
    ]
    
    for alpha in ORACLE_LIST:
        print(f"Processing {alpha['name']}...")
        payload = {
            "type": "REGULAR",
            "settings": {
                "instrumentType": "EQUITY",
                "region": "USA",
                "universe": "TOP3000",
                "delay": 1,
                "decay": 4,
                "neutralization": "SUBINDUSTRY",
                "truncation": 0.08,
                "pasteurization": "ON",
                "nanHandling": "ON",
                "unitHandling": "VERIFY",
                "language": "FASTEXPR",
                "visualization": False,
            },
            "regular": alpha['expr']
        }
        
        sim = session.post(f"{base_url}/simulations", json=payload)
        if sim.status_code != 201:
            print(f"Sim reject: {sim.text}")
            continue
            
        loc = sim.headers.get("Location")
        while True:
            poll = session.get(loc).json()
            if poll.get("status") == "COMPLETE":
                aid = poll.get("alpha")
                # Check metrics
                metrics = session.get(f"{base_url}/alphas/{aid}").json().get("is", {})
                sharpe = metrics.get("sharpe", 0)
                fitness = metrics.get("fitness", 0)
                turnover = metrics.get("turnover", 1)
                
                print(f"  ID: {aid} | Sharpe: {sharpe:.2f} | Fitness: {fitness:.2f} | Turn: {turnover:.2f}")
                
                # STRICT GATE CHECK
                if sharpe > 1.25 and fitness > 1.0 and turnover < 0.7:
                    sub = session.post(f"{base_url}/alphas/{aid}/submit")
                    if sub.status_code == 201:
                        print(f"  SUCCESS: SUBMITTED {aid}")
                    else:
                        print(f"  FAIL: Status {sub.status_code} | Msg: {sub.text}")
                else:
                    print(f"  REJECTED: Does not meet IQC gates.")
                break
            elif poll.get("status") == "ERROR":
                print(f"  Sim Error: {poll.get('message')}")
                break
            time.sleep(5)

if __name__ == "__main__":
    burst_oracle()
