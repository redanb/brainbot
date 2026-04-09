import time
import sys
from alpha_factory import BrainAPI

print("--- 🧬 ALPHA MUTATOR v2.0 ---")

try:
    import env_discovery
    env_discovery.initialize_environment()
except:
    pass

api = BrainAPI()

mutations = [
    # 1. Mutating wp1ZL312 (Sharpe 1.46) to boost Fitness (from 0.79 -> 1.0+)
    "group_neutralize(ts_decay_linear(rank(-1 * ts_delta(close, 5)), 3), subindustry)",
    
    # 2. Mutating 6X1AkKgp (Sharpe 1.85) to drop Turnover (<0.7) and boost Fitness (Target: group_neutralize + decay)
    "group_neutralize(ts_decay_linear(rank(open - close), 3), subindustry)",
    
    # Additional aggressive variants for maximum graduation potential
    "group_neutralize(ts_decay_linear(rank(-1 * ts_delta(close, 5)), 5), subindustry)",
    "ts_decay_linear(rank(open - close), 5)"
]

print(f"Loaded {len(mutations)} Mutated Candidates. Simulating directly on TOP3000...")

for m_expr in mutations:
    print(f"\n> Launching Simulation: {m_expr[:60]}...")
    metrics = api.simulate(m_expr, universe="TOP3000")
    
    if "error" in metrics and metrics.get("sharpe", 0.0) == 0.0:
        print(f"  [FAIL] Simulation Error: {metrics['error']}")
        continue

    sharpe = metrics.get('sharpe', 0.0)
    fitness = metrics.get('fitness', 0.0)
    turnover = metrics.get('turnover', 1.0)
    alpha_id = metrics.get('id', 'NO_ID')

    print(f"  [RESULT] Sharpe={sharpe:.3f} | Fitness={fitness:.3f} | Turnover={turnover:.3f} | ID={alpha_id}")
    
    if sharpe >= 1.25 and fitness >= 1.0 and turnover <= 0.70:
        print(f"  [🏆 CROWNED] Passes strict WQ IQC Rules! Submitting...")
        ok, err = api.submit(alpha_id)
        if ok:
            print(f"    -> [SUCCESS] Alpha {alpha_id} Submitted.")
        else:
            print(f"    -> [BLOCKED] {err}")
    else:
        print("  [DISCARDED] Failed strict criteria (Requires: Sharpe>=1.25, Fitness>=1.0, Turnover<=0.70).")
        
print("\n--- 🧬 MUTATION CYCLE COMPLETE ---")
