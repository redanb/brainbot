"""Check alpha state on WQ Brain"""
import os, requests, json
from pathlib import Path

env_path = Path(r"C:\Users\admin\.antigravity\master\.env")
for line in env_path.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

s = requests.Session()
r = s.post("https://api.worldquantbrain.com/authentication", auth=(os.environ.get("BRAIN_EMAIL"), os.environ.get("BRAIN_PASSWORD")))
print("Auth:", r.status_code)
s.headers.update({"Authorization": f"Bearer {s.cookies.get('t')}"})

for alpha_id in ["QPjYxMeX", "Gr6g5NXO"]:
    r2 = s.get(f"https://api.worldquantbrain.com/alphas/{alpha_id}")
    d = r2.json()
    print(f"\n=== {alpha_id} ===")
    print(f"Sharpe: {d['is']['sharpe']}  Fitness: {d['is']['fitness']}")
    for c in d["is"]["checks"]:
        print(f"  {c['name']}: {c['result']}  limit={c.get('limit', '-')}  value={c.get('value', '-')}")
