import os
import logging
import requests
from alpha_factory import BrainAPI, load_env

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("auth_check")

def check_auth():
    load_env()
    accounts_env = os.getenv("BRAIN_ACCOUNTS")
    if not accounts_env:
        log.error("BRAIN_ACCOUNTS not found in environment.")
        return

    accounts = []
    for pair in accounts_env.split(","):
        if ":" in pair:
            e, p = pair.split(":", 1)
            accounts.append((e.strip(), p.strip()))

    print("--- WorldQuant Brain Auth Check ---")
    for email, password in accounts:
        try:
            print(f"Testing account: {email}...")
            api = BrainAPI(email, password)
            print(f"[PASS] {email} authenticated successfully.")
        except Exception as e:
            print(f"[FAIL] {email} failed: {e}")

if __name__ == "__main__":
    check_auth()
