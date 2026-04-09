import sys
import numpy as np
import pandas as pd
from pathlib import Path

# Fix relative imports
sys.path.insert(0, ".")

from data_synthesizer import get_master_dir, OS_DATA_FILE
from fastexpr_compiler import FastExprCompiler

class OfflineSimulator:
    def __init__(self):
        self.data_matrices = {}
        self.returns_matrix = None
        self.is_loaded = False
        self.compiler = None

    def load_data(self):
        pkl_fallback = get_master_dir() / "data_cache" / "market_data.pkl"
        
        if OS_DATA_FILE.exists():
            df = pd.read_parquet(OS_DATA_FILE)
        elif pkl_fallback.exists():
            df = pd.read_pickle(pkl_fallback)
        else:
            raise FileNotFoundError("Offline market data not found. Run data_synthesizer.py first.")
            
        # We need 2D matrices (Dates x Assets) for each feature
        features = ['open', 'high', 'low', 'close', 'volume', 'vwap', 'subindustry', 'returns']
        
        for feat in features:
            if feat in df.columns:
                self.data_matrices[feat] = df.pivot(index='date', columns='asset', values=feat)
                
        self.returns_matrix = self.data_matrices['returns']
        self.compiler = FastExprCompiler(self.data_matrices)
        self.is_loaded = True
        
    def evaluate(self, expression: str) -> dict:
        if not self.is_loaded:
            self.load_data()
            
        try:
            # 1. Compile and Execute FASTEXPR to get Signals
            signal_df = self.compiler.execute(expression)
            
            # 2. Check for NaN saturation or empty output
            if signal_df is None or signal_df.empty:
                return {"sharpe": 0.0, "fitness": 0.0, "turnover": 1.0, "error": "Empty signal returned"}
                
            nan_ratio = signal_df.isna().sum().sum() / signal_df.size
            if nan_ratio > 0.95:
                # If 95% of the signal is NaN, it's a dead formula
                return {"sharpe": 0.0, "fitness": 0.0, "turnover": 1.0, "error": "Signal 95%+ NaN"}
                
            # 3. Simulate Portfolio Weights (WorldQuant standard market-neutral)
            # Cross-sectional rank normalization
            ranks = signal_df.rank(axis=1, pct=True)
            
            # Mean-centered (market-neutral)
            centered = ranks.sub(ranks.mean(axis=1), axis=0)
            
            # L1 Normalized weights (sum(abs(w)) = 1)
            weights = centered.div(centered.abs().sum(axis=1), axis=0)
            
            # Shift weights by 1 day (you trade on tomorrow's returns)
            # WorldQuant defaults to delay=1.
            weights_delayed = weights.shift(1, axis=0)
            
            # 4. Calculate PnL
            daily_returns = (weights_delayed * self.returns_matrix).sum(axis=1)
            
            # 5. Extract Metrics
            mean_ret = daily_returns.mean()
            std_ret = daily_returns.std()
            
            if std_ret == 0 or np.isnan(std_ret):
                return {"sharpe": 0.0, "fitness": 0.0, "turnover": 1.0, "error": "Zero or NaN standard deviation"}
                
            annualized_sharpe = (mean_ret / std_ret) * np.sqrt(252)
            
            # Turnover (approximate average absolute daily weight change)
            turnover = weights_delayed.diff(axis=0).abs().sum(axis=1).mean()
            
            # Fitness approximation (Sharpe * sqrt(Returns Penalty / Turnover Penalty))
            # Keeping it simple for offline pass: just return sharpe and high fitness if returns > 0
            # A true fitness score needs max_drawdown, but offline we just use raw sharpe as threshold.
            fitness = annualized_sharpe * 0.5 
            
            return {
                "sharpe": float(annualized_sharpe), 
                "fitness": float(fitness), 
                "turnover": float(turnover), 
                "error": ""
            }
            
        except Exception as e:
            return {"sharpe": 0.0, "fitness": 0.0, "turnover": 1.0, "error": str(e)}

if __name__ == "__main__":
    sim = OfflineSimulator()
    print("Testing valid alpha...")
    r1 = sim.evaluate("rank(-1 * ts_delta(close, 2))")
    print(r1)
    
    print("Testing garbage alpha...")
    r2 = sim.evaluate("rank(close * 0)")
    print(r2)
