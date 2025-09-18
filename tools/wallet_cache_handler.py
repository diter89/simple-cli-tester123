import json
import os
from pathlib import Path

CACHE_DIR = Path(".wallet_cache")
CACHE_DIR.mkdir(exist_ok=True) 
def save_to_cache(address: str, raw_data: dict):
    cache_file = CACHE_DIR / f"{address.lower()}.json"
    try:
        with open(cache_file, 'w') as f:
            json.dump(raw_data, f, indent=2)
        print(f"[Info] Data for {address} saved to cache.")
    except Exception as e:
        print(f"[Error] Failed to save cache for {address}: {e}")

def load_from_cache(address: str) -> dict | None:
    cache_file = CACHE_DIR / f"{address.lower()}.json"
    if not cache_file.exists():
        return None
    
    try:
        with open(cache_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"[Error] Failed to load cache for {address}: {e}")
        return None
