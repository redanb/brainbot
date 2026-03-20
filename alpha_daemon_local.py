"""
alpha_daemon_local.py
Local 24/7 fallback daemon for the Alpha Factory.
Runs continuous alpha generation loops, respecting the local .env file.
"""
import time
import logging
import sys
from datetime import datetime
from alpha_factory import run_factory
from sentinel_agent import send_telegram

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [DAEMON] %(message)s"
)
log = logging.getLogger("daemon")

def main():
    log.info("Starting Local 24/7 Alpha Daemon...")
    loops = 0
    while True:
        loops += 1
        log.info(f"--- STARTING DAEMON LOOP {loops} ---")
        try:
            run_factory()
            send_telegram(f"🟢 **Local Daemon Loop {loops} Complete**\nAlpha Factory executed successfully.")
        except Exception as e:
            log.error(f"Daemon Loop {loops} encountered an error: {e}")
            send_telegram(f"🔴 **Local Daemon Loop {loops} Error**\nException: {str(e)}")
        
        # Sleep for 1 hour before next burst
        log.info("Sleeping for 1 hour...")
        time.sleep(3600)

if __name__ == "__main__":
    main()
