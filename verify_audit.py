import json
import os
import sys

# Add the brainbot directory to path
sys.path.append(r"C:\Users\admin\Downloads\medsumag1\comp bet\brainbot")
import audit_helper

def test_audit_integrity():
    print("Testing Audit Helper Integrity...")
    
    # 1. Initial State Check
    audit_file = r"C:\Users\admin\.antigravity\master\submission_audit.json"
    with open(audit_file, 'r') as f:
        data = json.load(f)
    initial_tries = data['brain']['total_tries']
    print(f"Initial tries: {initial_tries}")
    
    # 2. Update Test
    audit_helper.update_audit("brain", "SUCCESS", details="Regression Audit Tool")
    
    with open(audit_file, 'r') as f:
        data = json.load(f)
    new_tries = data['brain']['total_tries']
    print(f"New tries: {new_tries}")
    
    assert new_tries == initial_tries + 1, "Total tries did not increment!"
    assert data['brain']['successful_submissions'] > 0, "Success count did not increment!"
    
    # 3. History Check
    last_log = data['brain']['history'][-1]
    assert "Regression Audit Tool" in last_log['details'], "History entry missing details!"
    
    print("Regression Audit PASSED.")

if __name__ == "__main__":
    test_audit_integrity()
