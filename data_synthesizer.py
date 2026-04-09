import os
import time
from pathlib import Path
import pandas as pd
import numpy as np

# ensure master dir
def get_master_dir() -> Path:
    if "ANTIGRAVITY_MASTER_DIR" in os.environ:
        return Path(os.environ["ANTIGRAVITY_MASTER_DIR"])
    if os.name == "nt":
        return Path(r"C:\Users\admin\.antigravity\master")
    return Path.home() / ".antigravity" / "master"

CACHE_DIR = get_master_dir() / "data_cache"
OS_DATA_FILE = CACHE_DIR / "market_data.parquet"

# Top 100 highly liquid tickers
LIQUID_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "LLY", "V",
    "JNJ", "XOM", "WMT", "JPM", "MA", "PG", "UNH", "HD", "CVX", "MRK", "KO",
    "ABBV", "PEP", "COST", "AVGO", "BAC", "TMO", "MCD", "CSCO", "ABT", "CRM",
    "ACN", "CMCSA", "LIN", "DHR", "NFLX", "ADBE", "NKE", "TXN", "PM", "PFE",
    "WFC", "VZ", "HON", "COP", "RTX", "NEE", "UPS", "DIS", "BA", "INTC", "BMY",
    "QCOM", "SPGI", "LOW", "CAT", "AMD", "GS", "UNP", "INTU", "MS", "IBM", "ISRG",
    "GE", "AMAT", "NOW", "SYK", "BKNG", "PLD", "MDT", "AXP", "T", "LMT", "DE",
    "BLK", "TJX", "MDLZ", "C", "SBUX", "MMC", "GILD", "CVS", "ZTS", "PGR",
    "SCHW", "LRCX", "VRTX", "MO", "CB", "REGN", "BSX", "TMUS", "ELV", "CI",
    "BDX", "SO", "ADI", "KLAC", "SLB", "FI", "DUK"
]

def synthesize_data(force=False):
    import yfinance as yf
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    if OS_DATA_FILE.exists() and not force:
        # Check if older than 7 days
        mod_time = OS_DATA_FILE.stat().st_mtime
        if time.time() - mod_time < 7 * 86400:
            print(f"[DATA] Cache is fresh ({OS_DATA_FILE}). No download needed.")
            return pd.read_parquet(OS_DATA_FILE)
            
    print(f"[DATA] Downloading data for {len(LIQUID_TICKERS)} tickers via yfinance...")
    # Fetch 2 years of daily data
    df = yf.download(LIQUID_TICKERS, period="2y", auto_adjust=True, group_by="ticker", threads=True)
    
    df_list = []
    
    # Restructure from MultiIndex columns to flat features per ticker
    for ticker in LIQUID_TICKERS:
        try:
            if ticker in df.columns.levels[0]:
                ticker_df = df[ticker].copy()
            else:
                ticker_df = df.xs(ticker, level=1, axis=1).copy() # if older yfinance version format
                
            ticker_df = ticker_df.dropna(subset=['Close']) # remove empty dates
            if ticker_df.empty:
                continue
            ticker_df['asset'] = ticker
            
            # Simple static subindustry assignment
            sub_id = sum(ord(c) for c in ticker) % 11  # 11 broad sectors
            ticker_df['subindustry'] = sub_id
            
            ticker_df = ticker_df.reset_index()
            # Rename columns to lowercase for easier mapping
            ticker_df = ticker_df.rename(columns={
                'Date': 'date', 'Open': 'open', 'High': 'high', 'Low': 'low',
                'Close': 'close', 'Volume': 'volume'
            })
            # keep only necessary cols to avoid extra cruft
            cols = ['date', 'asset', 'open', 'high', 'low', 'close', 'volume', 'subindustry']
            df_list.append(ticker_df[[c for c in cols if c in ticker_df.columns]])
        except Exception as e:
            print(f"[DATA] Skipped {ticker}: {e}")
            
    if not df_list:
        print("[DATA] Error: No data could be processed from yfinance.")
        return pd.DataFrame()
        
    stacked = pd.concat(df_list, ignore_index=True)
    
    # Calculate basic WorldQuant structural indicators
    stacked['vwap'] = (stacked['high'] + stacked['low'] + stacked['close']) / 3
    
    # We need to sort securely
    stacked = stacked.sort_values(by=['asset', 'date']).reset_index(drop=True)
    stacked['returns'] = stacked.groupby('asset')['close'].pct_change()
    
    # Final cleanup (replace infs)
    stacked = stacked.replace([np.inf, -np.inf], np.nan)
    
    print(f"[DATA] Generated structure: {stacked.shape}")
    
    try:
        stacked.to_parquet(OS_DATA_FILE, index=False)
        print(f"[DATA] Saved properly to {OS_DATA_FILE}")
    except ImportError:
        print("Fastparquet/Pyarrow not installed. Falling back to Pickle.")
        OS_DATA_FILE_PKL = CACHE_DIR / "market_data.pkl"
        stacked.to_pickle(OS_DATA_FILE_PKL)
        print(f"[DATA] Saved to {OS_DATA_FILE_PKL}")
    except Exception as e:
        print(f"Failed to save parquet: {e}.")
        
    return stacked

if __name__ == "__main__":
    synthesize_data()
