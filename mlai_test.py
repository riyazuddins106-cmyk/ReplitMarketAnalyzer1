import json
import pickle
import requests
from datetime import datetime, timezone


# ============================================================
# MLAI SMALL MARKET DATA TEST
# Internet -> Yahoo Finance -> Gold -> Candle Reader -> .bin
# ============================================================

SYMBOL = "GC=F"
INTERVAL = "5m"
RANGE = "5d"

API_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/"
    f"{SYMBOL}?range={RANGE}&interval={INTERVAL}"
)

OUTPUT_FILE = "market_data.bin"


# ------------------------------------------------------------
# 1. Download market data
# ------------------------------------------------------------

def download_candles():

    print("Connecting to Yahoo Finance...")
    print(f"Symbol   : {SYMBOL}")
    print(f"Interval : {INTERVAL}")
    print(f"Range    : {RANGE}")
    print()

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(
        API_URL,
        headers=headers,
        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    if "chart" not in data:
        raise RuntimeError(
            "Yahoo Finance response does not contain chart data:\n"
            + json.dumps(data, indent=2)
        )

    result = data["chart"]["result"]

    if not result:
        raise RuntimeError(
            "Yahoo Finance returned no market data."
        )

    return data


# ------------------------------------------------------------
# 2. Convert Yahoo response into candles
# ------------------------------------------------------------

def extract_candles(data):

    result = data["chart"]["result"][0]

    timestamps = result["timestamp"]

    quote = result["indicators"]["quote"][0]

    opens = quote["open"]
    highs = quote["high"]
    lows = quote["low"]
    closes = quote["close"]
    volumes = quote.get("volume", [])

    candles = []

    for i in range(len(timestamps)):

        if (
            opens[i] is None
            or highs[i] is None
            or lows[i] is None
            or closes[i] is None
        ):
            continue

        timestamp = int(timestamps[i])

        candle = {
            "datetime": datetime.fromtimestamp(
                timestamp,
                timezone.utc
            ).isoformat(),

            "timestamp": timestamp,

            "open": float(opens[i]),
            "high": float(highs[i]),
            "low": float(lows[i]),
            "close": float(closes[i]),

            "volume": (
                float(volumes[i])
                if i < len(volumes)
                and volumes[i] is not None
                else None
            )
        }

        candles.append(candle)

    # Oldest -> newest
    candles.sort(
        key=lambda candle: candle["timestamp"]
    )

    return candles


# ------------------------------------------------------------
# 3. Convert one OHLC candle into market-language features
# ------------------------------------------------------------

def analyse_candle(candle):

    open_price = candle["open"]
    high = candle["high"]
    low = candle["low"]
    close = candle["close"]

    total_range = high - low

    body = abs(close - open_price)

    upper_wick = high - max(
        open_price,
        close
    )

    lower_wick = min(
        open_price,
        close
    ) - low

    if total_range > 0:

        body_ratio = body / total_range

        upper_wick_ratio = (
            upper_wick / total_range
        )

        lower_wick_ratio = (
            lower_wick / total_range
        )

    else:

        body_ratio = 0

        upper_wick_ratio = 0

        lower_wick_ratio = 0

    # Candle direction

    if close > open_price:

        direction = "bullish"

    elif close < open_price:

        direction = "bearish"

    else:

        direction = "neutral"

    # Basic candle interpretation

    if body_ratio < 0.10:

        candle_type = "doji_like"

    elif body_ratio > 0.70:

        candle_type = "strong_body"

    elif lower_wick_ratio > 0.50:

        candle_type = "lower_rejection"

    elif upper_wick_ratio > 0.50:

        candle_type = "upper_rejection"

    else:

        candle_type = "normal"

    return {

        "timestamp": candle["timestamp"],

        "datetime": candle["datetime"],

        "open": open_price,
        "high": high,
        "low": low,
        "close": close,

        "volume": candle["volume"],

        "direction": direction,

        "candle_type": candle_type,

        "range": total_range,

        "body": body,

        "upper_wick": upper_wick,

        "lower_wick": lower_wick,

        "body_to_range": body_ratio,

        "upper_wick_to_range": upper_wick_ratio,

        "lower_wick_to_range": lower_wick_ratio
    }


# ------------------------------------------------------------
# 4. Analyse all candles
# ------------------------------------------------------------

def analyse_market(candles):

    analysed = []

    for candle in candles:

        analysed.append(
            analyse_candle(candle)
        )

    return analysed


# ------------------------------------------------------------
# 5. Save binary MLAI dataset
# ------------------------------------------------------------

def save_binary(
    raw_data,
    analysed
):

    binary_package = {

        "mlai_version": "0.1",

        "created_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "source": {

            "provider":
                "Yahoo Finance",

            "symbol":
                SYMBOL,

            "interval":
                INTERVAL,

            "range":
                RANGE
        },

        "raw_api_response":
            raw_data,

        "candles":
            analysed
    }

    with open(
        OUTPUT_FILE,
        "wb"
    ) as file:

        pickle.dump(
            binary_package,
            file,
            protocol=pickle.HIGHEST_PROTOCOL
        )

    return binary_package


# ------------------------------------------------------------
# 6. Display market-language summary
# ------------------------------------------------------------

def print_summary(candles):

    print()

    print("=" * 80)
    print("MLAI MARKET DATA TEST")
    print("=" * 80)

    print(
        f"Total candles: {len(candles)}"
    )

    if not candles:
        return

    first = candles[0]

    last = candles[-1]

    print()
    print("FIRST CANDLE")
    print("-" * 80)
    print(first)

    print()
    print("LATEST CANDLE")
    print("-" * 80)
    print(last)

    print()
    print("LATEST MARKET OBSERVATION")
    print("-" * 80)

    if last["direction"] == "bullish":

        print(
            "Direction : BULLISH"
        )

        print(
            "Price closed above the candle open."
        )

    elif last["direction"] == "bearish":

        print(
            "Direction : BEARISH"
        )

        print(
            "Price closed below the candle open."
        )

    else:

        print(
            "Direction : NEUTRAL"
        )

    print(
        f"Candle type : "
        f"{last['candle_type']}"
    )

    print(
        f"Range       : "
        f"{last['range']:.2f}"
    )

    print(
        f"Body        : "
        f"{last['body']:.2f}"
    )

    print(
        f"Upper wick  : "
        f"{last['upper_wick']:.2f}"
    )

    print(
        f"Lower wick  : "
        f"{last['lower_wick']:.2f}"
    )

    if (
        last["lower_wick"]
        >
        last["upper_wick"]
    ):

        print(
            "Observation: Greater lower-price rejection."
        )

    elif (
        last["upper_wick"]
        >
        last["lower_wick"]
    ):

        print(
            "Observation: Greater upper-price rejection."
        )

    else:

        print(
            "Observation: Upper and lower rejection are approximately balanced."
        )

    print()
    print("Binary file created:")
    print(OUTPUT_FILE)


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():

    try:

        # ----------------------------------------------------
        # INTERNET
        # ----------------------------------------------------

        raw_data = download_candles()

        print(
            "Internet/API connection: SUCCESS"
        )

        # ----------------------------------------------------
        # CANDLE EXTRACTION
        # ----------------------------------------------------

        candles = extract_candles(
            raw_data
        )

        print(
            f"Candles received: "
            f"{len(candles)}"
        )

        if not candles:

            raise RuntimeError(
                "No valid candles received."
            )

        # ----------------------------------------------------
        # MLAI ANALYSIS
        # ----------------------------------------------------

        analysed = analyse_market(
            candles
        )

        print(
            f"Candles analysed: "
            f"{len(analysed)}"
        )

        # ----------------------------------------------------
        # BINARY STORAGE
        # ----------------------------------------------------

        save_binary(
            raw_data,
            analysed
        )

        print_summary(
            analysed
        )

        print()

        print("=" * 80)
        print("TEST SUCCESSFUL")
        print("=" * 80)

        print()
        print("MLAI PIPELINE:")
        print()
        print("Internet")
        print("   ↓")
        print("Yahoo Finance")
        print("   ↓")
        print("GC=F Gold")
        print("   ↓")
        print("5-minute OHLC candles")
        print("   ↓")
        print("MLAI candle analysis")
        print("   ↓")
        print("market_data.bin")
        print("   ↓")
        print("Binary market-language dataset")

    except requests.RequestException as error:

        print()
        print("NETWORK/API ERROR:")
        print(error)

    except Exception as error:

        print()
        print("ERROR:")
        print(error)


if __name__ == "__main__":

    main()