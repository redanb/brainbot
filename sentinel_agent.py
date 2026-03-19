"""
sentinel_agent.py
Monitoring & Self-Healing Agent for Trinity Pulse GHA.
Sends Telegram notifications and analyzes batch results.
"""
import os
import sys
import requests
import json
from pathlib import Path

def get_master_dir():
    if "ANTIGRAVITY_MASTER_DIR" in os.environ:
        return Path(os.environ["ANTIGRAVITY_MASTER_DIR"])
    return Path.home() / ".antigravity" / "master"

def send_telegram(message):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = "985485272" # Verified User Chat ID
    if not token:
        print("TELEGRAM_TOKEN not found. Skipping notification.")
        return
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            print("Telegram notification sent.")
        else:
            print(f"Telegram failed: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"Telegram error: {e}")

def analyze_results():
    master_dir = get_master_dir()
    audit_file = master_dir / "submission_audit.json"
    tracker_file = master_dir / "evolution_log.json"
    
    summary = "🚨 **Trinity Pulse Run Report**\n\n"
    
    if audit_file.exists():
        try:
            data = json.loads(audit_file.read_text())
            brain = data.get("brain", {})
            total = brain.get("total_tries", 0)
            subs = brain.get("successful_submissions", 0)
            fails = brain.get("fail_403", 0)
            summary += f"📊 **Stats:**\n- Total Alphas: `{total}`\n- Submitted: `{subs}` ✅\n- 403 Errors: `{fails}` ❌\n\n"
        except:
            summary += "⚠️ Could not parse audit file.\n"
    else:
        summary += "⚠️ No audit file found (Run likely crashed early).\n"

    # Check for recent successes
    if tracker_file.exists():
        try:
            tracker = json.loads(tracker_file.read_text())
            recent = tracker.get("brain", [])[-3:]
            if recent:
                summary += "🎯 **Latest Alphas:**\n"
                for r in reversed(recent):
                    summary += f"- `{r.get('alpha_id')}` (Sharpe: {r.get('sharpe')}) -> {r.get('status')}\n"
        except:
            pass

    return summary

if __name__ == "__main__":
    event_status = os.getenv("WORKFLOW_STATUS", "completed")
    conclusion = os.getenv("WORKFLOW_CONCLUSION", "unknown")
    
    if conclusion == "failure":
        report = "🔴 **TRINITY PULSE FAILED**\n"
        report += analyze_results()
        report += "\n🔧 *Action:* Health check failure or structural code error detected."
    elif conclusion == "success":
        report = "🟢 **TRINITY PULSE SUCCESS**\n"
        report += analyze_results()
    else:
        report = f"⚪ **TRINITY PULSE {conclusion.upper()}**\n"
        report += analyze_results()

    send_telegram(report)
