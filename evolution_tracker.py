"""
evolution_tracker.py
Maintains a persistent log of all Brain (WorldQuant) and Numerai submissions.
Provides evolution summaries for daily email reports.
RULE-079: Complete audit trail of all algorithmic submissions.
"""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
import urllib.request
import urllib.parse
import subprocess

def get_master_dir():
    if "ANTIGRAVITY_MASTER_DIR" in os.environ:
        return Path(os.environ["ANTIGRAVITY_MASTER_DIR"])
    if os.name == 'nt':
        return Path(r"C:\Users\admin\.antigravity\master")
    return Path.home() / ".antigravity" / "master"

TRACKER_FILE = get_master_dir() / "evolution_log.json"

def _auto_commit_log(msg: str):
    """Auto-commits the evolution log to track the Singularity audit trail."""
    try:
        from thinking_engine import ThinkingEngine
        te = ThinkingEngine()
        research = te.get_latest_research()
        if research and "offline" not in research.lower():
            msg += f"\n\nResearch Synthesis: {research[:150]}..."
    except Exception:
        pass
        
    try:
        subprocess.run(["git", "add", "evolution_log.json"], cwd=str(TRACKER_FILE.parent), check=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0)
        subprocess.run(["git", "commit", "-m", msg], cwd=str(TRACKER_FILE.parent), check=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0)
    except Exception:
        pass # Silent failure if git not available or nothing to commit

def _load_log() -> dict:
    if TRACKER_FILE.exists():
        try:
            return json.loads(TRACKER_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"brain": [], "numerai": []}

def _save_log(data: dict):
    with open(TRACKER_FILE, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, indent=2, default=str))
        f.flush()
        try:
            os.fsync(f.fileno())
        except Exception:
            pass

def log_brain_submission(alpha_id: str, expression: str, sharpe: float, 
                          fitness: float, turnover: float, returns: float = 0.0, 
                          margin: float = 0.0, regime: str = "UNKNOWN", 
                          status: str = "SUBMITTED", reason: str = "N/A"):
    """Log a WorldQuant Brain alpha submission."""
    data = _load_log()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M IST"),
        "alpha_id": str(alpha_id),
        "expression": str(expression)[:1024],
        "sharpe": round(float(sharpe), 4),
        "fitness": round(float(fitness), 4),
        "turnover": round(float(turnover), 4),
        "returns": round(float(returns), 4),
        "margin": round(float(margin), 4),
        "regime": regime,
        "status": status,
        "reason": reason
    }
    data["brain"].append(entry)
    # Keep last 60 entries
    data["brain"] = data["brain"][-60:]
    _save_log(data)
    
    # Singularity: Auto-commit champions and milestones
    if status in ["SUBMITTED", "CHAMPION_PENDING"]:
        _auto_commit_log(f"[skip ci] Autonomous Brain Submission | Alpha {alpha_id} | Sharpe: {sharpe:.2f} | Regime: {regime}")

def log_numerai_submission(model: str, round_num: int, status: str, 
                            correlation: Optional[float] = None, 
                            mmc: Optional[float] = None):
    """Log a Numerai prediction submission."""
    data = _load_log()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M IST"),
        "model": model,
        "round": round_num,
        "status": status,
        "correlation": correlation,
        "mmc": mmc
    }
    data["numerai"].append(entry)
    # Keep last 100 entries
    data["numerai"] = data["numerai"][-100:]
    _save_log(data)

def get_brain_summary(last_n: int = 5) -> str:
    """Returns a text summary of the last N Brain submissions."""
    data = _load_log()
    entries = data.get("brain", [])
    if not entries:
        return "No Brain submissions recorded yet."
    
    recent = entries[-last_n:]
    lines = [f"WorldQuant Brain -- Last {min(last_n, len(recent))} Sessions:"]
    for e in reversed(recent):
        lines.append(
            f"  [DATE] {e.get('date','?')} | Alpha: {e.get('alpha_id','?')} | "
            f"Sharpe: {e.get('sharpe','?')} | Ret%: {e.get('returns','?')} | "
            f"Regime: {e.get('regime','?')} | Status: {e.get('status','?')}"
        )
    
    # Champion count
    champions = [e for e in entries if e.get("status") == "SUBMITTED"]
    lines.append(f"  [BEST] Total Champions Submitted: {len(champions)}")
    return "\n".join(lines)

def get_numerai_summary(last_n: int = 5) -> str:
    """Returns a text summary of the last N Numerai submissions."""
    data = _load_log()
    entries = data.get("numerai", [])
    if not entries:
        return "No Numerai submissions recorded yet."
    
    recent = entries[-last_n:]
    lines = [f"Numerai -- Last {min(last_n, len(recent))} Submissions:"]
    for e in reversed(recent):
        corr_str = f" | Corr: {e['correlation']:.4f}" if e.get("correlation") else ""
        mmc_str  = f" | MMC: {e['mmc']:.4f}" if e.get("mmc") else ""
        lines.append(
            f"  [DATE] {e.get('date','?')} | {e.get('model','?')} Round {e.get('round','?')} | "
            f"Status: {e.get('status','?')}{corr_str}{mmc_str}"
        )
    return "\n".join(lines)

def get_evolution_report() -> str:
    """Full evolution report for the daily digest."""
    data = _load_log()
    brain_entries = data.get("brain", [])
    numerai_entries = data.get("numerai", [])
    
    lines = ["=" * 50, "📊 EVOLUTION TRACKER — FULL AUDIT", "=" * 50]
    
    # --- Brain ---
    lines.append(get_brain_summary(last_n=5))
    
    # Brain stats
    if brain_entries:
        total_simulated = len(brain_entries)
        total_submitted = len([e for e in brain_entries if e.get("status") == "SUBMITTED"])
        best = max(brain_entries, key=lambda e: e.get("sharpe", 0))
        avg_sharpe = sum(e.get("sharpe", 0) for e in brain_entries[-10:]) / min(10, len(brain_entries))
        lines.append(f"  📈 Total Simulated: {total_simulated} | Submitted: {total_submitted}")
        lines.append(f"  🥇 Best Alpha: Sharpe {best.get('sharpe')} ({best.get('date')})")
        lines.append(f"  📉 Avg Sharpe (Last 10): {avg_sharpe:.4f}")
    
    lines.append("")
    
    # --- Numerai ---
    lines.append(get_numerai_summary(last_n=5))
    
    # Numerai stats
    if numerai_entries:
        models = set(e["model"] for e in numerai_entries)
        for m in models:
            m_entries = [e for e in numerai_entries if e["model"] == m]
            corrs = [e["correlation"] for e in m_entries if e.get("correlation")]
            if corrs:
                lines.append(f"  📊 {m}: Avg Correlation {sum(corrs)/len(corrs):.4f} over {len(corrs)} rounds")
    
    lines.append("=" * 50)
    return "\n".join(lines)

def audit_alpha_decay(alpha_id: str) -> float:
    """
    Calculates the 'Decay Rate' of an alpha by comparing recent Sharpe to historical.
    Return: percentage decline (e.g., 0.10 for 10% drop).
    """
    data = _load_log()
    history = [e for e in data.get("brain", []) if e.get("alpha_id") == alpha_id]
    
    if len(history) < 2:
        return 0.0
    
    # Sort by date
    history.sort(key=lambda x: x.get("date", ""))
    initial_sharpe = history[0].get("sharpe", 1.0)
    current_sharpe = history[-1].get("sharpe", initial_sharpe)
    
    decay = (initial_sharpe - current_sharpe) / max(initial_sharpe, 0.001)
    return round(decay, 4) if decay > 0 else 0.0

def notify_submission(alpha_id: str, expression: str, sharpe: float, fitness: float):
    """Send a real-time notification via Sentinel Agent."""
    try:
        from sentinel_agent import send_telegram
        msg = (
            f"🚀 **New Alpha Submitted**\n\n"
            f"🆔 ID: `{alpha_id}`\n"
            f"📊 Sharpe: `{float(sharpe):.4f}`\n"
            f"📈 Fitness: `{float(fitness):.4f}`\n"
            f"📝 Expr: `{str(expression)[:100]}...`"
        )
        send_telegram(msg)
    except Exception:
        pass # Silent failure to avoid breaking the core loop

if __name__ == "__main__":

    print(get_evolution_report())
