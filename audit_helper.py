import json
import os
from datetime import datetime
from pathlib import Path

def get_master_dir():
    if "ANTIGRAVITY_MASTER_DIR" in os.environ:
        return Path(os.environ["ANTIGRAVITY_MASTER_DIR"])
    if os.name == 'nt':
        return Path(r"C:\Users\admin\.antigravity\master")
    return Path.home() / ".antigravity" / "master"

def get_audit_file():
    return get_master_dir() / "submission_audit.json"

def update_audit(category, status, details=None):
    """
    Updates the global submission audit file.
    category: 'brain' or 'numerai'
    status: 'SUCCESS', 'FAIL_403', 'BELOW_THRESHOLD', 'TRY'
    """
    audit_file = get_audit_file()
    if not audit_file.exists():
        audit_file.parent.mkdir(parents=True, exist_ok=True)
        audit_file.write_text(json.dumps({category: {"total_tries": 0, "successful_submissions": 0, "fail_403": 0, "below_threshold": 0, "history": []}}))

    try:
        data = json.loads(audit_file.read_text(encoding="utf-8"))
    except:
        data = {category: {"total_tries": 0, "successful_submissions": 0, "fail_403": 0, "below_threshold": 0, "history": []}}

    if category not in data:
        data[category] = {"total_tries": 0, "successful_submissions": 0, "fail_403": 0, "below_threshold": 0, "history": []}

    stats = data[category]
    stats["total_tries"] += 1
    
    if status == "SUCCESS" or status == "SUBMITTED":
        stats["successful_submissions"] += 1
    elif "403" in str(status):
        stats["fail_403"] += 1
    elif "THRESHOLD" in str(status):
        stats["below_threshold"] += 1

    # Keep last 100 history entries
    history_entry = {
        "timestamp": datetime.now().isoformat(),
        "status": status,
        "details": details
    }
    stats["history"] = ([history_entry] + stats["history"])[:100]

    audit_file = get_audit_file()
    audit_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

def get_stats(category='brain'):
    audit_file = get_audit_file()
    if not audit_file.exists():
        return None
    data = json.loads(audit_file.read_text(encoding="utf-8"))
    return data.get(category)
