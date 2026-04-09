
import json, sys, os
sys.stdout.reconfigure(encoding='utf-8')

print("=== LAST RUN ROOT CAUSE ANALYSIS ===")
print()

# 1. Evolution log stats
try:
    with open(r'C:\Users\admin\.antigravity\master\evolution_log.json', 'r', encoding='utf-8', errors='ignore') as f:
        raw = f.read()
    data = json.loads(raw)
    brain = data.get('brain', [])
    statuses = {}
    for e in brain:
        s = e.get('status', 'UNKNOWN')
        statuses[s] = statuses.get(s, 0) + 1
    print("EVOLUTION LOG STATUS BREAKDOWN:")
    for k, v in sorted(statuses.items()):
        print(f"  {k}: {v}")
    print(f"  TOTAL: {len(brain)}")
    print()
    print("LAST 10 ENTRIES:")
    for e in brain[-10:]:
        print(f"  [{e.get('status','?')}] sharpe={e.get('sharpe',0):.3f} fitness={e.get('fitness',0):.3f} | {str(e.get('reason',''))[:80]}")
    print()

    # Count graduated
    graduated = [e for e in brain if e.get('status') == 'GRADUATED']
    submitted = [e for e in brain if e.get('status') == 'SUBMITTED']
    submit_fail = [e for e in brain if e.get('status') == 'SUBMIT_FAIL']
    evaluating = [e for e in brain if e.get('status') == 'EVALUATING']
    print(f"GRADUATED (ready for primary): {len(graduated)}")
    print(f"SUBMITTED (IQC in-progress):   {len(submitted)}")
    print(f"SUBMIT_FAIL:                    {len(submit_fail)}")
    print(f"EVALUATING (stuck):             {len(evaluating)}")
    print()
    if submit_fail:
        print("SUBMIT FAILURE REASONS:")
        for e in submit_fail[-5:]:
            print(f"  {e.get('reason','')[:120]}")
    print()
except Exception as ex:
    print(f"ERROR reading evolution_log: {type(ex).__name__}: {ex}")

# 2. Telemetry analysis
print("=== LLM TELEMETRY (LAST 40 CALLS) ===")
try:
    with open(r'C:\Users\admin\.antigravity\master\llm_router_telemetry.jsonl', 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    last40 = lines[-40:]
    success = 0
    failed = 0
    providers_ok = {}
    providers_fail = {}
    for line in last40:
        try:
            entry = json.loads(line.strip())
            prov = entry.get('provider', 'unknown')
            if entry.get('status') == 'SUCCESS':
                success += 1
                providers_ok[prov] = providers_ok.get(prov, 0) + 1
            else:
                failed += 1
                providers_fail[prov] = providers_fail.get(prov, 0) + 1
        except:
            pass
    print(f"  SUCCESS: {success} / FAILED: {failed}")
    print(f"  Working Providers: {providers_ok}")
    print(f"  Failed Providers:  {providers_fail}")
    print()
except Exception as ex:
    print(f"ERROR reading telemetry: {ex}")

# 3. Check .env for scout account
print("=== ACCOUNT STATUS ===")
brain_accounts = os.getenv('BRAIN_ACCOUNTS', '')
if not brain_accounts:
    # Try to find from .env files
    for env_path in [
        r'C:\Users\admin\.antigravity\master\.env',
        r'C:\Users\admin\Downloads\medsumag1\brainbot\.env'
    ]:
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('BRAIN_ACCOUNTS='):
                        brain_accounts = line.split('=',1)[1].strip().strip('"').strip("'")
                        break
            if brain_accounts:
                break

if brain_accounts:
    accounts = [a.split(':')[0] for a in brain_accounts.split(',') if ':' in a]
    print(f"  Accounts configured: {accounts}")
else:
    print("  WARNING: BRAIN_ACCOUNTS not found!")

print()
print("=== DIAGNOSIS SUMMARY ===")
print("Run this script to understand why alphas are not being submitted.")
