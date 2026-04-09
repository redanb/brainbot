"""
alpha_daemon.py — Autonomous 24/7 Alpha Factory God-Mode Daemon
Runs continuously, restarts itself on failure, monitors the leaderboard,
and adapts strategy based on results.

This is the MASTER CONTROLLER. It is the sole process responsible for:
1. Running the Alpha Factory loop at configurable intervals
2. Detecting and healing all failures autonomously (no human needed)
3. Monitoring WQ Brain rank after each submission
4. Persisting context to RESUME_CONTEXT.md

Usage:
    python alpha_daemon.py         # Run once and exit (for GHA)
    python alpha_daemon.py --loop  # Run continuously (for local)
    python alpha_daemon.py --sync  # Only run sync_champions graduation
"""

import os
import sys
import time
import json
import logging
import argparse
import traceback
import subprocess
from pathlib import Path
from datetime import datetime

# ─── ENCODING ─────────────────────────────────────────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore
    except Exception:
        pass

# ─── LOGGING ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [DAEMON] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger("alpha_daemon")


def get_master_dir() -> Path:
    if "ANTIGRAVITY_MASTER_DIR" in os.environ:
        return Path(os.environ["ANTIGRAVITY_MASTER_DIR"])
    if os.name == "nt":
        return Path(r"C:\Users\admin\.antigravity\master")
    return Path.home() / ".antigravity" / "master"


MASTER_DIR = get_master_dir()
SCRIPT_DIR = Path(__file__).resolve().parent


def load_env():
    """Load .env from multi-tier discovery."""
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        import env_discovery
        env_discovery.initialize_environment()
    except Exception as e:
        log.warning(f"env_discovery failed: {e}")


def check_rank() -> dict:
    """Check current WorldQuant Brain rank. Returns dict with rank info."""
    try:
        result = subprocess.run(
            [sys.executable, "check_brain_rank.py"],
            cwd=str(SCRIPT_DIR),
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="ignore"
        )
        output = result.stdout + result.stderr
        # Try to parse rank from output
        rank = None
        for line in output.splitlines():
            if "rank" in line.lower() and any(c.isdigit() for c in line):
                import re
                match = re.search(r"rank[:\s]+(\d+)", line, re.IGNORECASE)
                if match:
                    rank = int(match.group(1))
                    break
        return {"rank": rank, "output": output[:500]}
    except Exception as e:
        log.warning(f"Rank check failed: {e}")
        return {"rank": None, "output": str(e)}


def run_factory(max_calls: int = 80) -> dict:
    """Run the alpha factory. Returns dict with results."""
    log.info(f"Starting Alpha Factory with MAX_API_CALLS={max_calls}...")
    env = os.environ.copy()
    env["MAX_API_CALLS"] = str(max_calls)
    
    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, "alpha_factory.py"],
            cwd=str(SCRIPT_DIR),
            capture_output=True, text=True, timeout=7200,  # 2hr max
            encoding="utf-8", errors="ignore",
            env=env
        )
        elapsed = time.time() - start
        output = result.stdout[-3000:]  # Last 3000 chars
        stderr = result.stderr[-1000:]
        
        # Count submitted from output
        submitted = 0
        for line in output.splitlines():
            if "SUBMITTED" in line or "*** SUBMITTED" in line:
                submitted += 1
        
        log.info(f"Factory complete in {elapsed/60:.1f}m | exit={result.returncode} | ~{submitted} submitted")
        return {
            "exit_code": result.returncode,
            "elapsed_secs": elapsed,
            "submitted": submitted,
            "output_tail": output,
            "stderr_tail": stderr
        }
    except subprocess.TimeoutExpired:
        log.error("Factory timed out after 2 hours!")
        return {"exit_code": -1, "elapsed_secs": 7200, "submitted": 0, "output_tail": "TIMEOUT", "stderr_tail": ""}
    except Exception as e:
        log.error(f"Factory run error: {e}")
        return {"exit_code": -2, "elapsed_secs": 0, "submitted": 0, "output_tail": str(e), "stderr_tail": ""}


def run_graduation() -> dict:
    """Run sync_champions.py to graduate pending alphas to primary account."""
    log.info("Running graduation sync (sync_champions.py)...")
    try:
        result = subprocess.run(
            [sys.executable, "sync_champions.py"],
            cwd=str(SCRIPT_DIR),
            capture_output=True, text=True, timeout=3600,
            encoding="utf-8", errors="ignore"
        )
        output = result.stdout[-2000:]
        log.info(f"Graduation done: exit={result.returncode}")
        return {"exit_code": result.returncode, "output": output}
    except Exception as e:
        log.error(f"Graduation failed: {e}")
        return {"exit_code": -1, "output": str(e)}


def save_context(status: str, factory_result: dict, rank_info: dict, cycle: int):
    """Save current state to RESUME_CONTEXT.md for cold start recovery."""
    ctx_file = MASTER_DIR / "RESUME_CONTEXT.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M IST")
    
    content_lines = [
        f"# Alpha Daemon — Last Updated: {timestamp}",
        f"",
        f"## Execution Status",
        f"- Status: {status}",
        f"- Cycle: {cycle}",
        f"- Timestamp: {timestamp}",
        f"",
        f"## Last Factory Run",
        f"- Exit Code: {factory_result.get('exit_code', 'N/A')}",
        f"- Elapsed: {factory_result.get('elapsed_secs', 0)/60:.1f} minutes",
        f"- Submissions This Run: {factory_result.get('submitted', 0)}",
        f"",
        f"## Leaderboard",
        f"- Current Rank: {rank_info.get('rank', 'Unknown')}",
        f"- Target: #1",
        f"",
        f"## Next Actions",
        f"- [ ] Run factory again to generate more alphas",
        f"- [ ] Check graduation queue in evolution_log.json",
        f"- [ ] Monitor WQ Brain dashboard for alpha status",
        f"",
        f"## Last Factory Output (tail)",
        f"```",
        factory_result.get('output_tail', '')[-800:],
        f"```",
    ]
    
    try:
        ctx_file.write_text("\n".join(content_lines), encoding="utf-8")
        log.info(f"Context saved to {ctx_file}")
    except Exception as e:
        log.warning(f"Could not save context: {e}")


def send_telegram_report(msg: str):
    """Send status update via Telegram."""
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from sentinel_agent import send_telegram
        send_telegram(msg)
    except Exception:
        pass  # Non-critical


def run_once(max_calls: int = 80) -> int:
    """Run one full factory cycle. Returns number of submissions."""
    load_env()
    
    cycle_start = datetime.now()
    log.info("=" * 70)
    log.info(f"DAEMON CYCLE STARTING: {cycle_start.strftime('%Y-%m-%d %H:%M IST')}")
    log.info("=" * 70)
    
    # Step 1: Check current rank
    log.info("Step 1/4: Checking current leaderboard rank...")
    rank_info = check_rank()
    log.info(f"Current Rank: {rank_info.get('rank', 'Unknown')}")
    
    # Step 2: Run Alpha Factory
    log.info("Step 2/4: Running Alpha Factory...")
    factory_result = run_factory(max_calls=max_calls)
    
    # Step 3: Local Healing Protocol
    if factory_result.get("exit_code", 0) not in [0, 429]:  # Exclude success and standard rate limit
        log.warning(f"Factory exited with non-zero code: {factory_result.get('exit_code')}. Triggering God-Mode Auto-Healer locally!")
        healed = heal_factory_failure(factory_result.get("stderr_tail", ""))
        if healed:
            log.info("Healer successfully generated and applied a patch. Resuming and retrying cycle immediately.")
            return run_once(max_calls=max_calls)

    # Step 4: Run Graduation (sync_champions)
    log.info("Step 4/4: Running graduation pipeline...")
    grad_result = run_graduation()
    
    # Step 4: Save context and report
    log.info("Step 4/4: Saving context and sending report...")
    save_context("CYCLE_COMPLETE", factory_result, rank_info, cycle=1)
    
    # Summary report
    submitted = factory_result.get("submitted", 0)
    rank = rank_info.get("rank", "?")
    
    report_msg = (
        f"ALPHA DAEMON CYCLE COMPLETE\n"
        f"Time: {cycle_start.strftime('%H:%M IST')}\n"
        f"Alphas Submitted: {submitted}\n"
        f"Current Rank: {rank}\n"
        f"Factory Exit: {factory_result.get('exit_code', '?')}\n"
        f"Graduation Exit: {grad_result.get('exit_code', '?')}"
    )
    log.info(report_msg)
    send_telegram_report(report_msg)
    
    log.info("=" * 70)
    log.info(f"DAEMON CYCLE COMPLETE. Submissions: {submitted}, Rank: {rank}")
    log.info("=" * 70)
    
    return submitted


def heal_factory_failure(stderr_text: str) -> bool:
    """Invokes the LLM to autonomously patch the codebase based on the traceback during runtime."""
    if not stderr_text or len(stderr_text.strip()) < 10:
        return False
        
    log.info("Initializing autonomous local healing protocol...")
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from auto_fixer import ContinuousFeedbackFixer
        fixer = ContinuousFeedbackFixer()
        
        # We dummy the GHA run data since we are running locally
        run_data = {
            "id": f"LOCAL_CRASH_{int(time.time())}",
            "head_branch": "master",
            "head_commit": {"message": "Runtime local crash"}
        }
        summary = "Alpha Factory crashed with the following traceback/error:\n" + stderr_text[-3000:]
        
        # analyze_and_fix generates a fix prompt, executes emergency_fix.py, and tries to commit
        fixer.analyze_and_fix(run_data, summary)
        return True
    except Exception as e:
        log.error(f"Local God-Mode healer failed: {e}")
        return False


def run_loop(interval_hours: float = 4.0, max_calls: int = 80):
    """Run daemon loop continuously with interval between cycles."""
    cycle = 0
    consecutive_failures = 0
    
    log.info(f"DAEMON LOOP: Running every {interval_hours}h. Press Ctrl+C to stop.")
    
    while True:
        cycle += 1
        try:
            submitted = run_once(max_calls=max_calls)
            consecutive_failures = 0
            
            if submitted > 0:
                log.info(f"Cycle {cycle}: {submitted} new submissions!")
        except KeyboardInterrupt:
            log.info("Daemon interrupted by user. Exiting.")
            break
        except Exception as e:
            consecutive_failures += 1
            log.error(f"Cycle {cycle} failed: {e}\n{traceback.format_exc()}")
            
            if consecutive_failures >= 3:
                log.error("3 consecutive failures. Sleeping 30 minutes before retry.")
                time.sleep(1800)
            
        sleep_secs = interval_hours * 3600
        log.info(f"Cycle {cycle} done. Sleeping {interval_hours}h until next run...")
        
        try:
            time.sleep(sleep_secs)
        except KeyboardInterrupt:
            log.info("Daemon interrupted during sleep. Exiting.")
            break


def main():
    parser = argparse.ArgumentParser(description="Alpha Factory God-Mode Daemon")
    parser.add_argument("--loop", action="store_true", help="Run in loop mode (continuous)")
    parser.add_argument("--sync", action="store_true", help="Only run graduation sync")
    parser.add_argument("--interval", type=float, default=4.0, help="Loop interval in hours (default: 4)")
    parser.add_argument("--max-calls", type=int, default=80, help="Max API calls per cycle (default: 80)")
    args = parser.parse_args()
    
    if args.sync:
        load_env()
        run_graduation()
    elif args.loop:
        run_loop(interval_hours=args.interval, max_calls=args.max_calls)
    else:
        # Single run (for GHA)
        submitted = run_once(max_calls=args.max_calls)
        sys.exit(0 if submitted >= 0 else 1)


if __name__ == "__main__":
    main()
