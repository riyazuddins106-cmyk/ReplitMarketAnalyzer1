"""
Download a longer immutable MLAI market-data snapshot from Yahoo Finance.

The original test generator requested only five days. This version requests
50 days of 5-minute GC=F candles so the project can run a chronological
40-day reference / 10-day holdout experiment.

The existing data/market_data.bin is never overwritten. The new snapshot is
written to data/market_data_50d.bin and must be validated before promotion.
"""

from __future__ import annotations

import json
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from urllib.request import Request, urlopen


SYMBOL = "GC=F"
INTERVAL = "5m"
RANGE = "50d"
OUTPUT_FILE = Path("data/market_data_50d.bin")
API_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/"
    f"{SYMBOL}?range={RANGE}&interval={INTERVAL}"
)


def download_response() -> Dict[str, Any]:
    print("Connecting to Yahoo Finance...")
    print(f"Symbol   : {SYMBOL}")
    print(f"Interval : {INTERVAL}")
    print(f"Range    : {RANGE}")

    request = Request(API_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    result = data.get("chart", {}).get("result")
    if not result:
        raise RuntimeError(
            "Yahoo Finance returned no chart data:\n"
            + json.dumps(data, indent=2)[:2000]
        )
    return data


def extract_candles(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    result = data["chart"]["result"][0]
    timestamps = result.get("timestamp", [])
    quote = result["indicators"]["quote"][0]
    opens = quote.get("open", [])
    highs = quote.get("high", [])
    lows = quote.get("low", [])
    closes = quote.get("close", [])
    volumes = quote.get("volume", [])

    candles: List[Dict[str, Any]] = []
    for i, timestamp in enumerate(timestamps):
        values = (
            opens[i] if i < len(opens) else None,
            highs[i] if i < len(highs) else None,
            lows[i] if i < len(lows) else None,
            closes[i] if i < len(closes) else None,
        )
        if any(value is None for value in values):
            continue

        open_price, high, low, close = map(float, values)
        if high < max(open_price, close) or low > min(open_price, close) or high < low:
            continue

        ts = int(timestamp)
        candles.append(
            {
                "datetime": datetime.fromtimestamp(
                    ts, timezone.utc
                ).isoformat(),
                "timestamp": ts,
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": (
                    float(volumes[i])
                    if i < len(volumes) and volumes[i] is not None
                    else None
                ),
            }
        )

    candles.sort(key=lambda candle: candle["timestamp"])
    if len(candles) < 1000:
        raise RuntimeError(
            f"Only {len(candles)} valid candles were returned; refusing to save "
            "a dataset too small for the planned holdout."
        )
    return candles


def main() -> None:
    raw_data = download_response()
    candles = extract_candles(raw_data)
    package = {
        "mlai_version": "0.2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "provider": "Yahoo Finance",
            "symbol": SYMBOL,
            "interval": INTERVAL,
            "range": RANGE,
        },
        "raw_api_response": raw_data,
        "candles": candles,
    }
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("wb") as file:
        pickle.dump(package, file, protocol=pickle.HIGHEST_PROTOCOL)

    print()
    print(f"Saved {len(candles)} valid candles to {OUTPUT_FILE}")
    print(f"First timestamp: {candles[0]['datetime']}")
    print(f"Last timestamp : {candles[-1]['datetime']}")
    print("Existing data/market_data.bin was not modified.")


if __name__ == "__main__":
    main()