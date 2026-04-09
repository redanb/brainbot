import os
import logging
from alpha_factory import BrainAPI, load_env

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger("PARITY_CHECKER")

def verify_parity(expression: str):
    load_env()
    
    # 1. Setup Accounts
    primary_email = os.getenv("BRAIN_EMAIL")
    primary_pass = os.getenv("BRAIN_PASSWORD")
    scout_email = "satisfactionbus@gmail.com" # Hardcoded based on user strategy
    scout_pass = os.getenv("BRAIN_PASSWORD") # Assuming same pass for now or find in env
    
    log.info(f"Checking parity for: {expression[:50]}...")
    
    try:
        log.info("--- Primary Account Sim ---")
        p_api = BrainAPI(primary_email, primary_pass, is_primary=True)
        p_metrics = p_api.simulate(expression, universe="TOP3000")
        p_sharpe = p_metrics.get('sharpe', 0)
        
        log.info("--- Scout Account Sim ---")
        s_api = BrainAPI(scout_email, scout_pass, is_primary=False)
        s_metrics = s_api.simulate(expression, universe="TOP3000")
        s_sharpe = s_metrics.get('sharpe', 0)
        
        delta = abs(p_sharpe - s_sharpe)
        log.info(f"RESULT: Primary={p_sharpe:.3f} | Scout={s_sharpe:.3f} | Delta={delta:.3f}")
        
        if delta > 0.05:
            log.error("!!! PARITY BREACH DETECTED !!! Check universe/truncation defaults.")
        else:
            log.info("Parity confirmed (<0.05 delta).")
            
    except Exception as e:
        log.error(f"Parity Check Failed: {e}")

if __name__ == "__main__":
    # Test with a simple reversal
    test_expr = "group_neutralize(rank(open - close), subindustry)"
    verify_parity(test_expr)
