
import os
import pickle
import math
import statistics
from collections import Counter
from datetime import datetime, timezone


# ============================================================
# MLAI v3.7.0
# DATA FOUNDATION / RESEARCH PIPELINE TEST
# ============================================================
#
# PURPOSE
# -------
# This is the FIRST implementation step toward the
# MLAI Market Language Brain.
#
# This version establishes a safe, read-only data foundation.
#
# It does NOT:
#
#   - modify production MLAI
#   - modify market_data.bin
#   - modify learning memory
#   - train a model
#   - discover trading rules
#   - make predictions
#   - place trades
#
# It validates whether the market-data foundation is suitable
# for future research and learning.
#
# ============================================================


VERSION = "3.7.0"

DATA_FILE = "market_data.bin"

# Expected XAUUSD data characteristics for this experiment.
# These are validation hints, NOT assumptions that alter data.
EXPECTED_SYMBOL = "XAUUSD"

# Common timeframe in the current test dataset.
EXPECTED_TIMEFRAME_SECONDS = 300

# Small numerical tolerance for floating-point comparisons.
EPSILON = 1e-10


# ============================================================
# OUTPUT HELPERS
# ============================================================

def separator(char="=", width=80):
    print(char * width)


def section(title):
    print()
    separator()
    print(title)
    separator()


def pass_check(message):
    print(f"PASS: {message}")


def warn_check(message):
    print(f"WARNING: {message}")


def fail_check(message):
    print(f"FAIL: {message}")


# ============================================================
# GENERAL HELPERS
# ============================================================

def is_finite_number(value):
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def normalize_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_timestamp(value):
    """
    Convert a timestamp into integer Unix seconds when possible.
    """
    if value is None:
        return None

    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def timestamp_text(timestamp):
    if timestamp is None:
        return "UNKNOWN"

    try:
        return datetime.fromtimestamp(
            timestamp,
            tz=timezone.utc
        ).strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return "INVALID_TIMESTAMP"


def find_value(record, names):
    """
    Find the first available key from a list of possible names.
    """
    if not isinstance(record, dict):
        return None

    lowered = {
        str(key).lower(): value
        for key, value in record.items()
    }

    for name in names:
        if name.lower() in lowered:
            return lowered[name.lower()]

    return None


# ============================================================
# CANDLE NORMALIZATION
# ============================================================

def normalize_candle(record, original_index):
    """
    Normalize common OHLCV representations into a single schema.
    """

    if not isinstance(record, dict):
        return None, "record_is_not_dict"

    timestamp = find_value(
        record,
        [
            "timestamp",
            "time",
            "datetime",
            "date",
            "ts",
        ],
    )

    open_price = find_value(
        record,
        [
            "open",
            "o",
        ],
    )

    high_price = find_value(
        record,
        [
            "high",
            "h",
        ],
    )

    low_price = find_value(
        record,
        [
            "low",
            "l",
        ],
    )

    close_price = find_value(
        record,
        [
            "close",
            "c",
        ],
    )

    volume = find_value(
        record,
        [
            "volume",
            "vol",
            "v",
        ],
    )

    timestamp = normalize_timestamp(timestamp)

    open_price = normalize_number(open_price)
    high_price = normalize_number(high_price)
    low_price = normalize_number(low_price)
    close_price = normalize_number(close_price)

    if volume is not None:
        volume = normalize_number(volume)

    if timestamp is None:
        return None, "invalid_timestamp"

    prices = [
        open_price,
        high_price,
        low_price,
        close_price,
    ]

    if not all(is_finite_number(x) for x in prices):
        return None, "invalid_ohlc"

    if high_price < low_price:
        return None, "high_less_than_low"

    if open_price < low_price or open_price > high_price:
        return None, "open_outside_range"

    if close_price < low_price or close_price > high_price:
        return None, "close_outside_range"

    if volume is not None and not is_finite_number(volume):
        return None, "invalid_volume"

    return {
        "index": original_index,
        "timestamp": timestamp,
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "close": close_price,
        "volume": volume,
    }, None


# ============================================================
# DATASET EXTRACTION
# ============================================================

def extract_records(data):
    """
    Support several common container formats without modifying
    the original object.
    """

    if isinstance(data, list):
        return data

    if isinstance(data, tuple):
        return list(data)

    if isinstance(data, dict):

        # Common container keys.
        for key in [
            "candles",
            "data",
            "records",
            "market_data",
            "ohlcv",
            "prices",
        ]:
            value = data.get(key)

            if isinstance(value, (list, tuple)):
                return list(value)

        # A dictionary may itself represent one candle.
        if any(
            key in {
                str(k).lower()
                for k in data.keys()
            }
            for key in ["open", "high", "low", "close"]
        ):
            return [data]

    return []


def extract_metadata(data):
    metadata = {}

    if not isinstance(data, dict):
        return metadata

    for key in [
        "symbol",
        "ticker",
        "instrument",
        "pair",
        "timeframe",
        "interval",
        "source",
        "provider",
    ]:
        if key in data:
            metadata[key] = data[key]

    nested_metadata = data.get("metadata")

    if isinstance(nested_metadata, dict):
        for key, value in nested_metadata.items():
            if key not in metadata:
                metadata[key] = value

    return metadata


# ============================================================
# FILE LOADING
# ============================================================

def load_market_data(path):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Data file not found: {os.path.abspath(path)}"
        )

    # READ ONLY.
    #
    # We open the file only for reading.
    with open(path, "rb") as file:
        data = pickle.load(file)

    return data


# ============================================================
# TIMESTAMP ANALYSIS
# ============================================================

def analyze_timestamps(candles):
    result = {
        "ordered": True,
        "duplicate_count": 0,
        "negative_gap_count": 0,
        "gap_count": 0,
        "intervals": [],
        "largest_gap": None,
        "most_common_interval": None,
    }

    if len(candles) < 2:
        return result

    timestamps = [c["timestamp"] for c in candles]

    intervals = []

    for previous, current in zip(timestamps, timestamps[1:]):
        delta = current - previous
        intervals.append(delta)

        if delta == 0:
            result["duplicate_count"] += 1

        if delta < 0:
            result["negative_gap_count"] += 1
            result["ordered"] = False

    result["intervals"] = intervals

    positive_intervals = [
        value
        for value in intervals
        if value > 0
    ]

    if positive_intervals:
        counts = Counter(positive_intervals)

        result["most_common_interval"] = counts.most_common(1)[0][0]

        result["largest_gap"] = max(positive_intervals)

        expected = result["most_common_interval"]

        if expected > 0:
            for delta in positive_intervals:
                if delta > expected:
                    result["gap_count"] += 1

    return result


# ============================================================
# PRICE STATISTICS
# ============================================================

def calculate_price_statistics(candles):
    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]

    ranges = [
        c["high"] - c["low"]
        for c in candles
    ]

    bodies = [
        abs(c["close"] - c["open"])
        for c in candles
    ]

    return {
        "first_close": closes[0] if closes else None,
        "latest_close": closes[-1] if closes else None,
        "highest_high": max(highs) if highs else None,
        "lowest_low": min(lows) if lows else None,
        "average_range": (
            statistics.fmean(ranges)
            if ranges
            else None
        ),
        "median_range": (
            statistics.median(ranges)
            if ranges
            else None
        ),
        "average_body": (
            statistics.fmean(bodies)
            if bodies
            else None
        ),
    }


# ============================================================
# VOLUME ANALYSIS
# ============================================================

def analyze_volume(candles):
    volume_values = [
        c["volume"]
        for c in candles
        if c["volume"] is not None
    ]

    if not volume_values:
        return {
            "available": False,
            "count": 0,
            "average": None,
            "minimum": None,
            "maximum": None,
        }

    return {
        "available": True,
        "count": len(volume_values),
        "average": statistics.fmean(volume_values),
        "minimum": min(volume_values),
        "maximum": max(volume_values),
    }


# ============================================================
# DATA QUALITY
# ============================================================

def quality_report(candles, invalid_reasons, timestamp_analysis):
    total = len(candles) + sum(invalid_reasons.values())

    return {
        "total_records": total,
        "valid_records": len(candles),
        "invalid_records": sum(invalid_reasons.values()),
        "invalid_reasons": dict(invalid_reasons),
        "timestamp_order": timestamp_analysis["ordered"],
        "duplicates": timestamp_analysis["duplicate_count"],
        "gaps": timestamp_analysis["gap_count"],
    }


# ============================================================
# MAIN
# ============================================================

def main():

    section(
        f"MLAI v{VERSION} DATA FOUNDATION / RESEARCH PIPELINE TEST"
    )

    print(
        """
PURPOSE
-------

This experiment establishes the first safe foundation for
the MLAI Market Language Brain.

It validates the market-data layer before implementing
advanced learning, historical experience, probability,
and reasoning.

The test checks:

    OHLC
    Volume
    Timestamps
    Data ordering
    Duplicate candles
    Time gaps
    Price integrity
    Candle integrity
    Basic statistics
    Dataset metadata

This is a diagnostic experiment only.

market_data.bin        = READ ONLY
Production MLAI        = NOT MODIFIED
Learning memory        = NOT MODIFIED
Training               = NOT PERFORMED
Trading                = NOT PERFORMED
Predictions            = NOT PERFORMED
"""
    )

    # --------------------------------------------------------
    # PROTECTION
    # --------------------------------------------------------

    section("PROTECTION CHECK")

    print("market_data.bin : READ ONLY")
    print("production MLAI : NOT MODIFIED")
    print("learning memory : NOT MODIFIED")
    print("training        : DISABLED")
    print("trading         : DISABLED")
    print("predictions     : DISABLED")

    if not os.path.exists(DATA_FILE):
        fail_check(
            f"{DATA_FILE} does not exist."
        )
        return

    original_size = os.path.getsize(DATA_FILE)

    print(
        f"Data file: {os.path.abspath(DATA_FILE)}"
    )
    print(
        f"Data file size: {original_size:,} bytes"
    )

    # --------------------------------------------------------
    # LOAD
    # --------------------------------------------------------

    section("DATA LOADING")

    try:
        raw_data = load_market_data(DATA_FILE)
    except Exception as exc:
        fail_check(
            f"Could not load {DATA_FILE}: {exc}"
        )
        return

    print(
        f"Data type: {type(raw_data).__name__}"
    )

    metadata = extract_metadata(raw_data)

    records = extract_records(raw_data)

    print(
        f"Raw records detected: {len(records)}"
    )

    if not records:
        fail_check(
            "No candle records were detected."
        )
        return

    pass_check(
        f"{DATA_FILE} loaded successfully."
    )

    # --------------------------------------------------------
    # METADATA
    # --------------------------------------------------------

    section("MARKET DATA METADATA")

    if metadata:
        for key, value in metadata.items():
            print(
                f"{key:15}: {value}"
            )
    else:
        warn_check(
            "No explicit dataset metadata found."
        )

    # --------------------------------------------------------
    # NORMALIZATION
    # --------------------------------------------------------

    section("OHLCV NORMALIZATION")

    normalized = []
    invalid_reasons = Counter()

    for index, record in enumerate(records):

        candle, error = normalize_candle(
            record,
            index
        )

        if candle is None:
            invalid_reasons[error] += 1
        else:
            normalized.append(candle)

    print(
        f"Valid candles  : {len(normalized)}"
    )

    print(
        f"Invalid candles: {sum(invalid_reasons.values())}"
    )

    if invalid_reasons:
        print()
        print("Invalid reasons:")

        for reason, count in invalid_reasons.items():
            print(
                f"    {reason:25} : {count}"
            )

        fail_check(
            "One or more invalid records were detected."
        )
    else:
        pass_check(
            "All detected records passed OHLC normalization."
        )

    if not normalized:
        fail_check(
            "No valid candles remain after normalization."
        )
        return

    # --------------------------------------------------------
    # TIMESTAMPS
    # --------------------------------------------------------

    section("TIMESTAMP ANALYSIS")

    timestamp_analysis = analyze_timestamps(
        normalized
    )

    first_timestamp = normalized[0]["timestamp"]
    last_timestamp = normalized[-1]["timestamp"]

    print(
        f"First timestamp : {first_timestamp}"
    )

    print(
        f"First UTC       : {timestamp_text(first_timestamp)}"
    )

    print(
        f"Last timestamp  : {last_timestamp}"
    )

    print(
        f"Last UTC        : {timestamp_text(last_timestamp)}"
    )

    print(
        f"Timestamp order : "
        f"{'PASS' if timestamp_analysis['ordered'] else 'FAIL'}"
    )

    print(
        f"Duplicate gaps  : "
        f"{timestamp_analysis['duplicate_count']}"
    )

    print(
        f"Time gaps       : "
        f"{timestamp_analysis['gap_count']}"
    )

    print(
        f"Common interval : "
        f"{timestamp_analysis['most_common_interval']} seconds"
    )

    print(
        f"Largest interval: "
        f"{timestamp_analysis['largest_gap']} seconds"
    )

    if timestamp_analysis["ordered"]:
        pass_check(
            "Timestamps are in chronological order."
        )
    else:
        fail_check(
            "Timestamp ordering is invalid."
        )

    if timestamp_analysis["duplicate_count"] == 0:
        pass_check(
            "No duplicate timestamps detected."
        )
    else:
        warn_check(
            "Duplicate timestamps detected."
        )

    # --------------------------------------------------------
    # TIMEFRAME
    # --------------------------------------------------------

    section("TIMEFRAME ANALYSIS")

    interval = timestamp_analysis["most_common_interval"]

    if interval:

        print(
            f"Detected dominant interval: "
            f"{interval} seconds"
        )

        minutes = interval / 60

        print(
            f"Detected dominant interval: "
            f"{minutes:g} minutes"
        )

        if interval == EXPECTED_TIMEFRAME_SECONDS:
            pass_check(
                "Dataset interval matches the expected "
                "5-minute test data."
            )
        else:
            warn_check(
                "Dataset interval differs from the expected "
                "5-minute test interval."
            )

    else:
        warn_check(
            "Could not determine a dominant timeframe."
        )

    # --------------------------------------------------------
    # PRICE INTEGRITY
    # --------------------------------------------------------

    section("PRICE INTEGRITY")

    price_errors = 0

    for candle in normalized:

        if candle["high"] < candle["low"]:
            price_errors += 1

        if not (
            candle["low"]
            <= candle["open"]
            <= candle["high"]
        ):
            price_errors += 1

        if not (
            candle["low"]
            <= candle["close"]
            <= candle["high"]
        ):
            price_errors += 1

    print(
        f"Price integrity errors: {price_errors}"
    )

    if price_errors == 0:
        pass_check(
            "All normalized candles satisfy OHLC price constraints."
        )
    else:
        fail_check(
            "OHLC price integrity errors detected."
        )

    # --------------------------------------------------------
    # BASIC MARKET STATISTICS
    # --------------------------------------------------------

    section("BASIC MARKET STATISTICS")

    stats = calculate_price_statistics(
        normalized
    )

    print(
        f"First close       : {stats['first_close']:.5f}"
    )

    print(
        f"Latest close      : {stats['latest_close']:.5f}"
    )

    print(
        f"Highest high      : {stats['highest_high']:.5f}"
    )

    print(
        f"Lowest low        : {stats['lowest_low']:.5f}"
    )

    print(
        f"Average range     : {stats['average_range']:.5f}"
    )

    print(
        f"Median range      : {stats['median_range']:.5f}"
    )

    print(
        f"Average candle body: {stats['average_body']:.5f}"
    )

    # --------------------------------------------------------
    # VOLUME
    # --------------------------------------------------------

    section("VOLUME DATA")

    volume_stats = analyze_volume(
        normalized
    )

    if volume_stats["available"]:

        print("Volume available : YES")

        print(
            f"Volume candles   : {volume_stats['count']}"
        )

        print(
            f"Average volume   : "
            f"{volume_stats['average']:.5f}"
        )

        print(
            f"Minimum volume   : "
            f"{volume_stats['minimum']:.5f}"
        )

        print(
            f"Maximum volume   : "
            f"{volume_stats['maximum']:.5f}"
        )

        pass_check(
            "Volume data is available."
        )

    else:

        print("Volume available : NO")

        warn_check(
            "No volume data is available."
        )

        print(
            "Future MLAI modules must NOT fabricate volume."
        )

    # --------------------------------------------------------
    # DATASET COVERAGE
    # --------------------------------------------------------

    section("DATASET COVERAGE")

    duration_seconds = (
        last_timestamp - first_timestamp
    )

    duration_days = duration_seconds / 86400

    print(
        f"Total candles : {len(normalized)}"
    )

    print(
        f"Duration      : {duration_seconds:,} seconds"
    )

    print(
        f"Duration      : {duration_days:.4f} days"
    )

    if duration_seconds > 0:

        expected_candle_count = None

        if interval and interval > 0:
            expected_candle_count = (
                duration_seconds / interval
            ) + 1

        if expected_candle_count:
            print(
                f"Expected candles over span: "
                f"{expected_candle_count:.2f}"
            )

            coverage_ratio = (
                len(normalized)
                / expected_candle_count
            )

            print(
                f"Approximate temporal coverage: "
                f"{coverage_ratio * 100:.2f}%"
            )

    # --------------------------------------------------------
    # SAMPLE DATA
    # --------------------------------------------------------

    section("FIRST / LAST CANDLE CHECK")

    first = normalized[0]
    last = normalized[-1]

    print("FIRST CANDLE")

    print(
        f"  Time  : {timestamp_text(first['timestamp'])}"
    )

    print(
        f"  Open  : {first['open']:.5f}"
    )

    print(
        f"  High  : {first['high']:.5f}"
    )

    print(
        f"  Low   : {first['low']:.5f}"
    )

    print(
        f"  Close : {first['close']:.5f}"
    )

    print()

    print("LATEST CANDLE")

    print(
        f"  Time  : {timestamp_text(last['timestamp'])}"
    )

    print(
        f"  Open  : {last['open']:.5f}"
    )

    print(
        f"  High  : {last['high']:.5f}"
    )

    print(
        f"  Low   : {last['low']:.5f}"
    )

    print(
        f"  Close : {last['close']:.5f}"
    )

    # --------------------------------------------------------
    # PROTECTION VERIFICATION
    # --------------------------------------------------------

    section("READ-ONLY PROTECTION VERIFICATION")

    final_size = os.path.getsize(DATA_FILE)

    print(
        f"Original file size: {original_size:,} bytes"
    )

    print(
        f"Final file size   : {final_size:,} bytes"
    )

    if original_size == final_size:
        pass_check(
            "market_data.bin size unchanged."
        )
    else:
        fail_check(
            "market_data.bin size changed."
        )

    # --------------------------------------------------------
    # FOUNDATION VERDICT
    # --------------------------------------------------------

    section("DATA FOUNDATION VERDICT")

    total_invalid = sum(
        invalid_reasons.values()
    )

    foundation_pass = (
        len(normalized) > 0
        and total_invalid == 0
        and timestamp_analysis["ordered"]
        and price_errors == 0
        and original_size == final_size
    )

    if foundation_pass:

        print(
            "FOUNDATION STATUS: PASS"
        )

        print()
        print(
            "The current dataset passed the basic data-foundation"
        )
        print(
            "checks required before the next MLAI research layer."
        )

        print()
        print(
            "This does NOT mean the data is sufficient for learning."
        )

        print(
            "It means the basic data layer is structurally usable."
        )

    else:

        print(
            "FOUNDATION STATUS: NOT READY"
        )

        print()
        print(
            "The dataset requires data-quality investigation"
        )

        print(
            "before advanced learning experiments should continue."
        )

    # --------------------------------------------------------
    # WHAT THIS TEST DOES NOT PROVE
    # --------------------------------------------------------

    section("IMPORTANT LIMITATIONS")

    print(
        """
This test does NOT prove:

    - Market understanding
    - Predictive ability
    - Trading accuracy
    - Statistical edge
    - Generalization
    - Historical learning
    - Probability calibration
    - Sequence understanding
    - Market-language understanding

Those capabilities will be tested in later phases.

NEXT STEP IF THIS PASSES:

    P0-2
    Unified Market Representation

That layer will transform raw validated market data into
machine-readable descriptions of:

    Candle anatomy
    Candle behaviour
    Relative movement
    Candle sequences
    Volatility context
    Momentum context
    Volume context
    Price location

No production MLAI changes should be made until that
representation has been independently tested.
"""
    )

    # --------------------------------------------------------
    # FINAL PROTECTION
    # --------------------------------------------------------

    section("FINAL PROTECTION CHECK")

    print("market_data.bin : READ ONLY")
    print("Production MLAI : NOT MODIFIED")
    print("Learning memory : NOT MODIFIED")
    print("Training        : DISABLED")
    print("Trading         : DISABLED")
    print("Predictions     : DISABLED")

    separator()

    print(
        f"MLAI v{VERSION} DATA FOUNDATION TEST COMPLETE"
    )

    separator()


if __name__ == "__main__":
    main()
