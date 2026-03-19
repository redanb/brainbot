import os
import requests
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [DIAGNOSE] - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def diagnose():
    env_path = Path(r"C:\Users\admin\.antigravity\master\.env")
    email = ""
    password = ""
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                if k.strip() == "BRAIN_EMAIL": email = v.strip().strip('"').strip("'")
                if k.strip() == "BRAIN_PASSWORD": password = v.strip().strip('"').strip("'")

    if not email or not password:
        logger.error("Missing credentials")
        return

    base_url = "https://api.worldquantbrain.com"
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    logger.info(f"Authenticating as {email}...")
    auth = session.post(f"{base_url}/authentication", auth=(email, password))
    if auth.status_code != 201:
        logger.error(f"Auth failed: {auth.status_code} {auth.text}")
        return
    logger.info("Auth successful.")

    # 1. Check self info
    me = session.get(f"{base_url}/users/self").json()
    logger.info(f"User: {me.get('username')}")

    # 2. Check competitions/challenges
    logger.info("Checking available competitions...")
    # Trying both common endpoints
    for endpoint in ["/competitions", "/challenges"]:
        resp = session.get(f"{base_url}{endpoint}")
        if resp.status_code == 200:
            logger.info(f"Endpoint {endpoint} found: {json.dumps(resp.json(), indent=2)}")
        else:
            logger.warning(f"Endpoint {endpoint} returned {resp.status_code}")

    # 3. List recent alphas and their status
    logger.info("Checking recent alphas...")
    alphas = []
    # Try owner filter or just search results
    user_id = me.get('id')
    search_urls = [
        f"{base_url}/alphas?limit=10&status=UNSUBMITTED",
        f"{base_url}/alphas?owner={user_id}&limit=10" if user_id else None
    ]
    for url in filter(None, search_urls):
        resp = session.get(url)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            alphas.extend(results)
            for a in results:
                logger.info(f"Alpha {a.get('id')} - Status: {a.get('status')} - Name: {a.get('name')}")
        else:
            logger.warning(f"Failed to list alphas at {url}: {resp.status_code} {resp.text}")

    # 4. Probe /submit on a recent alpha to see precise failure
    if alphas:
        target_alpha = alphas[0].get('id')
        logger.info(f"Targeting alpha {target_alpha} for submission probe...")
        sub_resp = session.post(f"{base_url}/alphas/{target_alpha}/submit")
        logger.info(f"Submission probe returned {sub_resp.status_code}: {sub_resp.text}")
    else:
        logger.warning("No alphas found to probe submission.")
    
    # 5. Check if we can find IQC 2026 specifically
    logger.info("Searching for IQC competition...")
    search_resp = session.get(f"{base_url}/competitions?status=ACTIVE")
    if search_resp.status_code == 200:
        active = search_resp.json().get("results", [])
        logger.info(f"Active competitions: {json.dumps(active, indent=2)}")
    else:
        logger.warning(f"Could not search active competitions: {search_resp.status_code}")

if __name__ == "__main__":
    diagnose()
