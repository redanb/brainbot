import sys
import unittest
import importlib

# Add current dir to path to import alpha_factory
sys.path.insert(0, ".")

try:
    import alpha_factory
except ImportError:
    print("Failed to import alpha_factory")
    sys.exit(1)

try:
    from offline_simulator import OfflineSimulator
except ImportError:
    OfflineSimulator = None

# Rule-031/Rule-030 Mocking
class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code
        self.text = str(json_data)
        
    def json(self):
        return self.json_data

class MockSession:
    def __init__(self):
        self.headers = {}
        self.cookies = {}
        
    def post(self, url, json=None, auth=None, timeout=None):
        if "authentication" in url:
            return MockResponse({}, 201)
        if "submit" in url:
            # Simulate a 403 Validation Failure
            return MockResponse({
                "is": {
                    "checks": [
                        {"name": "LOW_SHARPE", "result": "PASS", "limit": 1.25, "value": 1.71},
                        {"name": "LOW_FITNESS", "result": "FAIL", "limit": 1.0, "value": 0.91}
                    ]
                }
            }, 403)
        return MockResponse({}, 200)

class TestAlphaFactory(unittest.TestCase):

    def test_alpha_factory_thresholds(self):
        """Assert global constraints strictly equal WQ server targets"""
        self.assertEqual(alpha_factory.SUBMIT_SHARPE_MIN, 1.25, "Sharpe limit must be 1.25")
        self.assertEqual(alpha_factory.SUBMIT_FITNESS_MIN, 1.00, "Fitness limit must be 1.00")
        self.assertEqual(alpha_factory.SUBMIT_TURNOVER_MAX, 0.70, "Turnover limit must be 0.70")

    def test_api_submit_403_parsing(self):
        """Test that BrainAPI parses 403 VALIDATION errors and aborts without exception"""
        # Monkeypatch requests.Session for this test avoiding network calls
        import requests
        original_session = requests.Session
        requests.Session = MockSession
        
        try:
            # instantiate without loading real env
            import os
            os.environ["BRAIN_EMAIL"] = "test@example.com"
            os.environ["BRAIN_PASSWORD"] = "testpass"
            api = alpha_factory.BrainAPI(email="test@test.com", password="pass")
            
            # Reset the audit update to a dummy so we don't write to master audit log
            original_audit = getattr(alpha_factory, "audit_helper", None)
            class FakeAudit:
                def update_audit(self, *a, **k): pass
            alpha_factory.audit_helper = FakeAudit()
            
            success, error = api.submit("TEST_ID")
            
            self.assertFalse(success)
            self.assertIn("VALIDATION_FAIL", error)
            self.assertIn("LOW_FITNESS (limit: 1.0, value: 0.91)", error)
            
            if original_audit:
                alpha_factory.audit_helper = original_audit
        finally:
            requests.Session = original_session

    def test_offline_simulator_eval(self):
        """Test the offline simulator engine safely drops mathematically dead alphas."""
        if not OfflineSimulator:
            self.skipTest("OfflineSimulator not found, skipping Vector A assay")
            
        try:
            sim = OfflineSimulator()
            
            # 1. Invalid flat alpha -> Should return Sharpe 0.0 or None
            bad = sim.evaluate("rank(volumes * 0)")
            self.assertAlmostEqual(bad['sharpe'], 0.0, places=2)
            
            # 2. Functional alpha -> Should return math values
            good = sim.evaluate("rank(ts_rank(close, 10))")
            # we don't care about the absolute value for this test, just that it ran
            self.assertIsNotNone(good.get('sharpe'))
            
        except FileNotFoundError:
            self.skipTest("No offline data cache found to run the simulator tests.")

def run_tests():
    print("Running Regression Audit...")
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestAlphaFactory)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Regression Audit ensure previous features are intact
    print("\nEnsuring regression logic works...")
    if not hasattr(alpha_factory, "run_factory"):
        print("[FAIL] run_factory method missing")
        sys.exit(1)
        
    if not result.wasSuccessful():
        print("[VERIFICATION FAILED]")
        sys.exit(1)
        
    print("[VERIFICATION PASSED]")

if __name__ == "__main__":
    run_tests()
