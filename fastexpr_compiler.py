import re
import numpy as np
import pandas as pd

class FastExprCompiler:
    """
    Compiles and evaluates WorldQuant FASTEXPR alpha strings
    by transpiling them to native pandas/numpy matrix operations.
    Assumes data is provided as 2D pandas DataFrames: shape (Dates, Assets).
    """
    def __init__(self, data_matrices: dict):
        """
        data_matrices should contain DataFrames for:
        close, open, high, low, volume, vwap, returns, subindustry, etc.
        """
        self.data = data_matrices
        
        # Subindustry mapping (static Series of length Assets)
        # We assume data_matrices['subindustry'] has constant rows, so we take iloc[0].
        if 'subindustry' in self.data:
            self.subinds = self.data['subindustry'].iloc[0]
        else:
            self.subinds = None

    def execute(self, expression: str):
        """Evaluates the FASTEXPR string and returns the resulting 2D DataFrame"""
        
        # Clean up whitespace and line breaks
        expression = expression.replace('\n', '').strip()
        
        # 1. Operators -> Functions translation
        # To avoid regex hell with nested brackets, we define Python functions 
        # in the `eval` namespace that mimic WQ FASTEXPR.
        
        def rank(x):
            return x.rank(axis=1, pct=True)

        def group_neutralize(x, g):
            # g must be evaluated to a Series if static, but usually wq passes 'subindustry'
            # 'subindustry' in our namespace will be the 2D matrix or we use self.subinds
            # To handle pandas groupby with series on columns:
            if isinstance(g, pd.DataFrame):
                g = g.iloc[0] # take first row assumption
            return x.sub(x.groupby(g, axis=1).transform('mean'))

        def ts_delay(x, d):
            return x.shift(int(d), axis=0)

        def ts_delta(x, d):
            return x - x.shift(int(d), axis=0)

        def ts_mean(x, d):
            return x.rolling(window=int(d), min_periods=1, axis=0).mean()

        def ts_std_dev(x, d):
            return x.rolling(window=int(d), min_periods=1, axis=0).std()

        def ts_zscore(x, d):
            mean = ts_mean(x, d)
            std = ts_std_dev(x, d) + 0.000001
            return (x - mean) / std

        def ts_rank(x, d):
            # Optimised rolling rank via pandas rolling apply
            return x.rolling(int(d), axis=0).apply(lambda s: s.rank(pct=True).iloc[-1], raw=False)
            
        def ts_decay_linear(x, d):
            # linear weighted moving average
            d = int(d)
            weights = np.arange(1, d + 1)
            weights = weights / weights.sum()
            def wma(s):
                if len(s) < d: return np.nan
                return np.dot(s, weights)
            return x.rolling(window=d, axis=0).apply(wma, raw=True)

        def ts_corr(x, y, d):
            return x.rolling(window=int(d), min_periods=1, axis=0).corr(y)

        def signed_power(x, e):
            # Ensure safe execution
            if isinstance(e, pd.DataFrame): e = e.values
            return np.sign(x) * (np.abs(x) ** e)

        def log(x):
            return np.log(x.replace(0, np.nan))

        def sqrt(x):
            return np.sqrt(x)

        # 2. Namespace building
        namespace = {
            # Operators
            'rank': rank,
            'group_neutralize': group_neutralize,
            'ts_delay': ts_delay,
            'ts_delta': ts_delta,
            'ts_mean': ts_mean,
            'ts_std_dev': ts_std_dev,
            'ts_zscore': ts_zscore,
            'ts_rank': ts_rank,
            'ts_decay_linear': ts_decay_linear,
            'ts_corr': ts_corr,
            'signed_power': signed_power,
            'log': log,
            'np': np,
            'pd': pd
        }
        
        # Insert variables
        for k, v in self.data.items():
            namespace[k] = v
            namespace[k.lower()] = v
            namespace[k.upper()] = v
            
        # Hardcode subindustry string for group neutralize if used
        if self.subinds is not None:
            namespace['subindustry'] = self.subinds
            namespace['SUBINDUSTRY'] = self.subinds

        import random 
        
        # 3. Simple transformations for python syntax compatibility
        # FASTEXPR uses && and || which python doesn't support inside eval without transpiling.
        # But most alpha expressions use standard math (+, -, *, /) and nested function calls.
        clean_expr = expression
        
        # Convert any unhandled custom operators if necessary
        clean_expr = clean_expr.replace("returns", "returns_df") # returns is a reserved kw in some scopes
        if "returns_df" not in namespace and "returns" in namespace:
            namespace["returns_df"] = namespace["returns"]

        try:
            result = eval(clean_expr, {"__builtins__": None}, namespace)
            return result
        except Exception as e:
            raise ValueError(f"Failed to evaluate: {e}")
