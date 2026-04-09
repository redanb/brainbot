import os
import sys
import json
import logging
from unittest.mock import MagicMock, patch

# Mock setup to avoid hitting real API during basic regression
sys.modules['requests'] = MagicMock()
import requests

from alpha_factory import BrainAPI
import sync_champions

logging.basicConfig(level=logging.ERROR)

def test_auth_recovery():
    """Verify that _connect clears session and retries."""
    with patch('requests.Session') as mock_sess:
        session_instance = mock_sess.return_value
        session_instance.post.return_value.status_code = 201
        session_instance.cookies.get.return_value = "fake_token"
        
        api = BrainAPI("test@test.com", "pass")
        
        with patch.object(api.session.cookies, 'clear') as mock_clear:
            api._connect()
            mock_clear.assert_called()
    print("[PASS] test_auth_recovery: Session cleared on connect.")

def test_simulate_parity_defaults():
    """Verify simulate uses 0.01 truncation and TOP1000/3000 as expected."""
    with patch('requests.Session') as mock_sess:
        session_instance = mock_sess.return_value
        session_instance.post.return_value.status_code = 201
        session_instance.headers.get.return_value = "http://sims/1"
        session_instance.get.return_value.status_code = 200
        session_instance.get.return_value.json.return_value = {"status": "COMPLETE", "alpha": "A1"}
        
        api = BrainAPI("test@test.com", "pass")
        api.simulate("rank(close)", universe="TOP3000")
        
        args, kwargs = session_instance.post.call_args
        payload = kwargs['json']
        assert payload['settings']['universe'] == "TOP3000"
        assert payload['settings']['truncation'] == 0.01
    print("[PASS] test_simulate_parity_defaults: TOP3000/0.01 enforced.")

def run_regression():
    print("--- STARTING REGRESSION AUDIT ---")
    try:
        test_auth_recovery()
        test_simulate_parity_defaults()
        print("--- REGRESSION AUDIT PASSED ---")
        return 0
    except Exception as e:
        print(f"--- REGRESSION AUDIT FAILED: {e} ---")
        return 1

if __name__ == "__main__":
    exit(run_regression())
