"""Download and validate the real XAU/USD 5-minute corpus used by MLAI."""

from __future__ import annotations

import csv
import io
import pickle
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


URL = (
    "https://raw.githubusercontent.com/getdata-finance/"
    "xauusd-5m-ohlcv-metals-historical-data/main/XAUUSD_5m.csv"
)
OUTPUT = Path("data/market_data_50d.bin")


def main() -> None:
    request = Request(URL, headers={"User-Agent": "MLAI-XAUUSD-Data-Generator/1.0"})
    with urlopen(request, timeout=60) as response:
        text = response.read().decode("utf-8-sig")
    candles = []
    for row_number, row in enumerate(csv.DictReader(io.StringIO(text)), 2):
        try:
            instant = datetime.fromisoformat(
                row["datetime"].strip().replace("Z", "+00:00")
            ).astimezone(timezone.utc)
            candle = {
                "instrument": "XAU/USD",
                "symbol": "XAUUSD",
                "timestamp": int(instant.timestamp()),
                "datetime": instant.isoformat(),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
            }
        except (KeyError, TypeError, ValueError) as error:
            raise RuntimeError(f"Invalid CSV row {row_number}: {error}") from error
        if min(candle["open"], candle["close"]) < candle["low"]:
            raise RuntimeError(f"Invalid OHLC at row {row_number}")
        if max(candle["open"], candle["close"]) > candle["high"]:
            raise RuntimeError(f"Invalid OHLC at row {row_number}")
        candles.append(candle)
    if not candles or any(
        b["timestamp"] <= a["timestamp"] for a, b in zip(candles, candles[1:])
    ):
        raise RuntimeError("Empty or non-chronological source data")
    package = {
        "mlai_version": "XAUUSD-1.0",
        "dataset_type": "XAU/USD_SPOT",
        "instrument": "XAU/USD",
        "symbol": "XAUUSD",
        "timeframe": "5m",
        "source": {
            "provider": "Public XAUUSD historical dataset",
            "provider_symbol": "XAUUSD",
            "instrument": "XAU/USD SPOT",
            "is_gc_f": False,
            "is_synthetic": False,
            "is_fabricated": False,
            "timeframe": "5m",
            "url": URL,
        },
        "validation": {"ohlc": "PASS", "duplicates": "PASS", "chronology": "PASS"},
        "candles": candles,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(pickle.dumps(package, protocol=pickle.HIGHEST_PROTOCOL))
    print(f"Saved {len(candles):,} candles to {OUTPUT}")


if __name__ == "__main__":
    main()