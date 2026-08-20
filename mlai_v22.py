import os
import pickle
from datetime import datetime, timezone


# ============================================================
# MLAI v2.2
# OUTCOME CALIBRATION + SCENARIO ACCURACY LEARNING ENGINE
# ============================================================

MARKET_FILE = "market_data.bin"
EXPERIENCE_FILE = "mlai_experience.bin"
SCENARIO_FILE = "mlai_scenario_memory.bin"
CALIBRATION_FILE = "mlai_calibration_memory.bin"
STATUS_FILE = "MLAI_PROJECT_STATUS.md"

HORIZONS = [4, 8, 16]


# ============================================================
# BASIC HELPERS
# ============================================================

def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def clamp(value, low=0.0, high=100.0):
    return max(low, min(high, value))


def direction_from_change(change):
    if change > 0:
        return "bullish"
    if change < 0:
        return "bearish"
    return "neutral"


def normalize_direction(value):
    if value is None:
        return "neutral"

    text = str(value).strip().lower()

    if text in (
        "bullish",
        "bull",
        "up",
        "long",
        "buy",
        "bullish_continuation_scenario",
    ):
        return "bullish"

    if text in (
        "bearish",
        "bear",
        "down",
        "short",
        "sell",
        "bearish_reversal",
    ):
        return "bearish"

    return "neutral"


def get_close(candle):
    if isinstance(candle, dict):
        for key in ("close", "Close", "c"):
            if key in candle:
                return safe_float(candle[key])
    return safe_float(candle)


# ============================================================
# LOAD PICKLE SAFELY
# ============================================================

def load_pickle(path, default):
    if not os.path.exists(path):
        return default

    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception:
        return default


def save_pickle(path, obj):
    with open(path, "wb") as f:
        pickle.dump(obj, f)


# ============================================================
# LOAD MARKET MEMORY
# ============================================================

print("=" * 70)
print("MLAI v2.2 - LOADING MARKET MEMORY")
print("=" * 70)
print(f"File: {MARKET_FILE}")
print()

market_memory = load_pickle(MARKET_FILE, None)

if market_memory is None:
    print("ERROR: market_data.bin could not be loaded.")
    raise SystemExit(1)

print("PASS: market_data.bin loaded as MLAI memory object.")
print()

# ------------------------------------------------------------
# Extract candles from different possible memory formats
# ------------------------------------------------------------

candles = []

if isinstance(market_memory, dict):
    for key in ("candles", "data", "rows", "market_data"):
        if isinstance(market_memory.get(key), list):
            candles = market_memory[key]
            break

elif isinstance(market_memory, list):
    candles = market_memory

if not candles:
    print("ERROR: No candle data found in market_data.bin.")
    raise SystemExit(1)

print("MEMORY METADATA")
print("-" * 70)

if isinstance(market_memory, dict):
    metadata = market_memory.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    print(
        f"MLAI version : "
        f"{metadata.get('mlai_version', metadata.get('version', 'unknown'))}"
    )
    print(
        f"Created at   : "
        f"{metadata.get('created_at', 'unknown')}"
    )
    print(
        f"Source       : "
        f"{metadata.get('source', 'unknown')}"
    )
else:
    print("MLAI version : unknown")
    print("Created at   : unknown")
    print("Source       : unknown")

print()
print(f"Found {len(candles)} stored candles.")
print()

if len(candles) < 20:
    print("ERROR: Not enough candles for v2.2 calibration.")
    raise SystemExit(1)

analysis_window = min(60, len(candles))
latest = candles[-analysis_window:]

print(f"PASS: Using latest {analysis_window} candles.")
print()
print("Analysing latest candles...")
print()


# ============================================================
# BASIC MARKET CONTEXT
# ============================================================

closes = [get_close(c) for c in latest]

first_close = closes[0]
latest_close = closes[-1]

net_change = latest_close - first_close

if first_close != 0:
    net_change_pct = (net_change / first_close) * 100.0
else:
    net_change_pct = 0.0

bullish_candles = 0
bearish_candles = 0
neutral_candles = 0

for i in range(len(latest)):
    if isinstance(latest[i], dict):
        open_price = safe_float(
            latest[i].get(
                "open",
                latest[i].get("Open", latest[i].get("o", closes[i]))
            )
        )
    else:
        open_price = closes[i]

    close_price = closes[i]

    if close_price > open_price:
        bullish_candles += 1
    elif close_price < open_price:
        bearish_candles += 1
    else:
        neutral_candles += 1


if bullish_candles > bearish_candles:
    direct_direction = "bullish"
elif bearish_candles > bullish_candles:
    direct_direction = "bearish"
else:
    direct_direction = "neutral"


# ============================================================
# LOAD SCENARIO MEMORY
# ============================================================

print("PASS: Loading MLAI scenario memory...")

scenario_memory = load_pickle(SCENARIO_FILE, {})

if not isinstance(scenario_memory, dict):
    scenario_memory = {}

print("PASS: Scenario memory loaded.")


# ============================================================
# EXTRACT CURRENT SCENARIO
# ============================================================

current_scenario = {}

if isinstance(scenario_memory.get("current_scenario"), dict):
    current_scenario = scenario_memory["current_scenario"]

elif isinstance(scenario_memory.get("scenario"), dict):
    current_scenario = scenario_memory["scenario"]

elif isinstance(scenario_memory.get("latest"), dict):
    current_scenario = scenario_memory["latest"]


def find_percentage(keys, default=0.0):
    containers = [
        current_scenario,
        scenario_memory,
    ]

    for container in containers:
        if not isinstance(container, dict):
            continue

        for key in keys:
            if key in container:
                return safe_float(container[key], default)

    return default


bullish_scenario = find_percentage(
    [
        "bullish_continuation",
        "bullish_continuation_pct",
        "bullish_percentage",
        "bullish",
    ]
)

bearish_scenario = find_percentage(
    [
        "bearish_reversal",
        "bearish_reversal_pct",
        "bearish_percentage",
        "bearish",
    ]
)

neutral_scenario = find_percentage(
    [
        "neutral_range",
        "neutral_range_pct",
        "neutral_percentage",
        "neutral",
    ]
)


# ------------------------------------------------------------
# Try horizon-specific scenario values
# ------------------------------------------------------------

def horizon_scenario(horizon):
    source = None

    for key in (
        f"{horizon}_candle_scenario",
        f"horizon_{horizon}",
        f"{horizon}_candle",
        str(horizon),
    ):
        value = current_scenario.get(key)

        if isinstance(value, dict):
            source = value
            break

        value = scenario_memory.get(key)

        if isinstance(value, dict):
            source = value
            break

    if source is None:
        return {
            "bullish": bullish_scenario,
            "bearish": bearish_scenario,
            "neutral": neutral_scenario,
        }

    return {
        "bullish": safe_float(
            source.get(
                "bullish",
                source.get(
                    "bullish_continuation",
                    source.get("bullish_percentage", 0.0),
                ),
            )
        ),
        "bearish": safe_float(
            source.get(
                "bearish",
                source.get(
                    "bearish_reversal",
                    source.get("bearish_percentage", 0.0),
                ),
            )
        ),
        "neutral": safe_float(
            source.get(
                "neutral",
                source.get(
                    "neutral_range",
                    source.get("neutral_percentage", 0.0),
                ),
            )
        ),
    }


scenario_by_horizon = {
    horizon: horizon_scenario(horizon)
    for horizon in HORIZONS
}


# ============================================================
# DETERMINE PRIMARY SCENARIO
# ============================================================

primary_scenario = current_scenario.get(
    "primary_scenario",
    scenario_memory.get(
        "primary_scenario",
        None,
    ),
)

if primary_scenario:
    primary_direction = normalize_direction(primary_scenario)
else:
    scores = {
        "bullish": bullish_scenario,
        "bearish": bearish_scenario,
        "neutral": neutral_scenario,
    }

    primary_direction = max(scores, key=scores.get)


# ============================================================
# CALIBRATION MEMORY
# ============================================================

print("PASS: Loading calibration memory...")

calibration_memory = load_pickle(
    CALIBRATION_FILE,
    None,
)

if not isinstance(calibration_memory, dict):
    calibration_memory = {
        "version": "2.2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "observations": [],
    }

if "observations" not in calibration_memory:
    calibration_memory["observations"] = []

print("PASS: Calibration memory loaded.")
print()


# ============================================================
# EXPERIENCE MEMORY
# ============================================================

experience_memory = load_pickle(
    EXPERIENCE_FILE,
    {}
)

if not isinstance(experience_memory, dict):
    experience_memory = {}

experience_observations = experience_memory.get(
    "observations",
    []
)

if not isinstance(experience_observations, list):
    experience_observations = []


# ============================================================
# OUTCOME CALCULATION
# ============================================================

def calculate_outcome(start_index, horizon):
    end_index = start_index + horizon

    if end_index >= len(candles):
        return None

    start_price = get_close(candles[start_index])
    end_price = get_close(candles[end_index])

    if start_price == 0:
        return None

    change = end_price - start_price
    change_pct = (change / start_price) * 100.0

    # Small movement is treated as neutral.
    neutral_threshold = 0.01

    if change_pct > neutral_threshold:
        direction = "bullish"
    elif change_pct < -neutral_threshold:
        direction = "bearish"
    else:
        direction = "neutral"

    return {
        "direction": direction,
        "start_price": start_price,
        "end_price": end_price,
        "change": change,
        "change_pct": change_pct,
        "horizon": horizon,
        "resolved_at_candle": end_index,
    }


# ============================================================
# CALIBRATION RECORD HELPERS
# ============================================================

def make_calibration_record(
    candle_index,
    horizon,
    scenario,
):
    return {
        "id": (
            f"cal_{candle_index}_"
            f"{horizon}"
        ),
        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "candle_index": candle_index,
        "horizon": horizon,

        "scenario": {
            "bullish": safe_float(
                scenario.get("bullish", 0.0)
            ),
            "bearish": safe_float(
                scenario.get("bearish", 0.0)
            ),
            "neutral": safe_float(
                scenario.get("neutral", 0.0)
            ),
        },

        "primary_direction": primary_direction,

        "status": "pending",
        "actual_outcome": None,

        "calibration_error": None,
        "correct": None,
    }


# ============================================================
# CURRENT OBSERVATION
# ============================================================

current_candle_index = len(candles) - 1

existing_ids = {
    item.get("id")
    for item in calibration_memory["observations"]
    if isinstance(item, dict)
}


# ============================================================
# IMPORTANT:
# We only create a calibration observation if the scenario
# memory represents the current market observation.
# ============================================================

for horizon in HORIZONS:

    scenario = scenario_by_horizon[horizon]

    record_id = (
        f"cal_{current_candle_index}_"
        f"{horizon}"
    )

    if record_id not in existing_ids:

        record = make_calibration_record(
            current_candle_index,
            horizon,
            scenario,
        )

        calibration_memory["observations"].append(
            record
        )


# ============================================================
# RESOLVE PENDING CALIBRATION OBSERVATIONS
# ============================================================

newly_resolved = []

for record in calibration_memory["observations"]:

    if not isinstance(record, dict):
        continue

    if record.get("status") != "pending":
        continue

    candle_index = record.get("candle_index")
    horizon = record.get("horizon")

    if candle_index is None or horizon is None:
        continue

    try:
        candle_index = int(candle_index)
        horizon = int(horizon)
    except Exception:
        continue

    outcome = calculate_outcome(
        candle_index,
        horizon,
    )

    if outcome is None:
        continue

    actual_direction = outcome["direction"]

    scenario = record.get(
        "scenario",
        {},
    )

    predicted_direction = normalize_direction(
        record.get("primary_direction")
    )

    probabilities = {
        "bullish": safe_float(
            scenario.get("bullish", 0.0)
        ),
        "bearish": safe_float(
            scenario.get("bearish", 0.0)
        ),
        "neutral": safe_float(
            scenario.get("neutral", 0.0)
        ),
    }

    predicted_probability = probabilities.get(
        predicted_direction,
        0.0,
    )

    actual_probability = probabilities.get(
        actual_direction,
        0.0,
    )

    # Brier-like single-outcome calibration error.
    target = {
        "bullish": 0.0,
        "bearish": 0.0,
        "neutral": 0.0,
    }

    target[actual_direction] = 1.0

    probability_vector = {
        key: probabilities[key] / 100.0
        for key in probabilities
    }

    squared_error = 0.0

    for key in (
        "bullish",
        "bearish",
        "neutral",
    ):
        squared_error += (
            probability_vector[key]
            - target[key]
        ) ** 2
        

    squared_error /= 3.0

    correct = (
        predicted_direction
        == actual_direction
    )

    record["status"] = "resolved"

    record["actual_outcome"] = outcome

    record["correct"] = bool(correct)

    record["predicted_probability"] = (
        predicted_probability
    )

    record["actual_probability"] = (
        actual_probability
    )

    record["calibration_error"] = (
        squared_error
    )

    newly_resolved.append(record)


# ============================================================
# CALIBRATION STATISTICS
# ============================================================

resolved_records = [
    item
    for item in calibration_memory["observations"]
    if isinstance(item, dict)
    and item.get("status") == "resolved"
]

pending_records = [
    item
    for item in calibration_memory["observations"]
    if isinstance(item, dict)
    and item.get("status") == "pending"
]


def calculate_statistics(records):

    result = {
        "resolved": len(records),
        "correct": 0,
        "incorrect": 0,
        "accuracy": 0.0,
        "mean_calibration_error": 0.0,
        "bullish_actual": 0,
        "bearish_actual": 0,
        "neutral_actual": 0,
    }

    if not records:
        return result

    errors = []

    for record in records:

        if record.get("correct"):
            result["correct"] += 1
        else:
            result["incorrect"] += 1

        outcome = record.get(
            "actual_outcome",
            {}
        )

        direction = normalize_direction(
            outcome.get("direction")
        )

        if direction == "bullish":
            result["bullish_actual"] += 1
        elif direction == "bearish":
            result["bearish_actual"] += 1
        else:
            result["neutral_actual"] += 1

        error = record.get(
            "calibration_error"
        )

        if error is not None:
            errors.append(
                safe_float(error)
            )

    result["accuracy"] = (
        result["correct"]
        / result["resolved"]
        * 100.0
    )

    if errors:
        result["mean_calibration_error"] = (
            sum(errors) / len(errors)
        )

    return result


statistics_by_horizon = {}

for horizon in HORIZONS:

    records = [
        item
        for item in resolved_records
        if int(item.get("horizon", 0))
        == horizon
    ]

    statistics_by_horizon[horizon] = (
        calculate_statistics(records)
    )


# ============================================================
# DIRECTION ACCURACY
# ============================================================

direction_statistics = {}

for direction in (
    "bullish",
    "bearish",
    "neutral",
):

    records = [
        item
        for item in resolved_records
        if normalize_direction(
            item.get("primary_direction")
        ) == direction
    ]

    direction_statistics[direction] = (
        calculate_statistics(records)
    )


# ============================================================
# OVERALL CALIBRATION RELIABILITY
# ============================================================

if resolved_records:

    overall_accuracy = (
        sum(
            1
            for record in resolved_records
            if record.get("correct")
        )
        / len(resolved_records)
        * 100.0
    )

    errors = [
        safe_float(
            record.get(
                "calibration_error",
                0.0
            )
        )
        for record in resolved_records
        if record.get(
            "calibration_error"
        ) is not None
    ]

    mean_error = (
        sum(errors) / len(errors)
        if errors
        else 0.0
    )

else:

    overall_accuracy = 0.0
    mean_error = 0.0


# ============================================================
# SAMPLE RELIABILITY LEVEL
# ============================================================

sample_count = len(resolved_records)

if sample_count == 0:
    reliability_level = "not_available"
elif sample_count < 10:
    reliability_level = "very_limited"
elif sample_count < 30:
    reliability_level = "limited"
elif sample_count < 100:
    reliability_level = "developing"
else:
    reliability_level = "established"


# ============================================================
# SAVE CALIBRATION MEMORY
# ============================================================

calibration_memory["version"] = "2.2"

calibration_memory["updated_at"] = (
    datetime.now(timezone.utc).isoformat()
)

calibration_memory["statistics"] = {
    "overall_accuracy": overall_accuracy,
    "mean_calibration_error": mean_error,
    "resolved_samples": sample_count,
    "pending_samples": len(
        pending_records
    ),
    "reliability_level": reliability_level,
}

calibration_memory["statistics_by_horizon"] = (
    statistics_by_horizon
)

calibration_memory["direction_statistics"] = (
    direction_statistics
)

save_pickle(
    CALIBRATION_FILE,
    calibration_memory
)

print(
    f"PASS: {CALIBRATION_FILE} saved."
)
print()


# ============================================================
# DISPLAY
# ============================================================

print("=" * 70)
print(
    "MLAI v2.2 OUTCOME CALIBRATION + "
    "SCENARIO ACCURACY LEARNING ENGINE"
)
print("=" * 70)
print()

print("CURRENT MARKET CONTEXT")
print("-" * 70)
print(
    f"Direction              : "
    f"{direct_direction}"
)
print(
    f"First close            : "
    f"{first_close:.4f}"
)
print(
    f"Latest close           : "
    f"{latest_close:.4f}"
)
print(
    f"Net movement           : "
    f"{net_change:.4f}"
)
print(
    f"Net change %           : "
    f"{net_change_pct:.3f}%"
)
print(
    f"Bullish candles        : "
    f"{bullish_candles}"
)
print(
    f"Bearish candles        : "
    f"{bearish_candles}"
)
print(
    f"Neutral candles        : "
    f"{neutral_candles}"
)
print()

print("CURRENT SCENARIO")
print("-" * 70)
print(
    f"Primary scenario       : "
    f"{primary_direction}"
)

for horizon in HORIZONS:

    scenario = scenario_by_horizon[
        horizon
    ]

    print(
        f"{horizon}-candle scenario     : "
        f"B={scenario['bullish']:.1f}% | "
        f"S={scenario['bearish']:.1f}% | "
        f"N={scenario['neutral']:.1f}%"
    )

print()

print("NEWLY RESOLVED CALIBRATION")
print("-" * 70)

if newly_resolved:

    print(
        f"Newly resolved windows : "
        f"{len(newly_resolved)}"
    )

    for record in newly_resolved:

        outcome = record.get(
            "actual_outcome",
            {}
        )

        print(
            f"- {record.get('horizon')} candles | "
            f"predicted="
            f"{record.get('primary_direction')} | "
            f"actual="
            f"{outcome.get('direction')} | "
            f"change="
            f"{safe_float(outcome.get('change_pct')):.3f}% | "
            f"correct="
            f"{record.get('correct')}"
        )

else:

    print(
        "No previously pending calibration "
        "window became resolvable during this run."
    )

print()

print("CALIBRATION PERFORMANCE")
print("-" * 70)

print(
    f"Resolved samples      : "
    f"{sample_count}"
)

print(
    f"Pending samples       : "
    f"{len(pending_records)}"
)

print(
    f"Overall accuracy      : "
    f"{overall_accuracy:.1f}%"
)

print(
    f"Mean calibration error: "
    f"{mean_error:.4f}"
)

print(
    f"Reliability level     : "
    f"{reliability_level}"
)

print()

print("HORIZON PERFORMANCE")
print("-" * 70)

for horizon in HORIZONS:

    stats = statistics_by_horizon[
        horizon
    ]

    print(
        f"{horizon:2d} candles -> "
        f"resolved={stats['resolved']} | "
        f"correct={stats['correct']} | "
        f"incorrect={stats['incorrect']} | "
        f"accuracy={stats['accuracy']:.1f}% | "
        f"calibration_error="
        f"{stats['mean_calibration_error']:.4f}"
    )

print()

print("DIRECTION PERFORMANCE")
print("-" * 70)

for direction in (
    "bullish",
    "bearish",
    "neutral",
):

    stats = direction_statistics[
        direction
    ]

    print(
        f"{direction:<8} -> "
        f"resolved={stats['resolved']} | "
        f"correct={stats['correct']} | "
        f"accuracy={stats['accuracy']:.1f}%"
    )

print()

print("CALIBRATION INTERPRETATION")
print("-" * 70)

if sample_count == 0:

    interpretation = (
        "No resolved scenario outcomes are "
        "available yet. Calibration cannot "
        "be measured until future candles "
        "resolve pending observations."
    )

elif sample_count < 10:

    interpretation = (
        "Calibration has started, but the "
        "sample size is very small. Accuracy "
        "statistics should not yet be treated "
        "as reliable."
    )

elif mean_error < 0.05:

    interpretation = (
        "Historical scenario weighting shows "
        "relatively low calibration error for "
        "the available sample."
    )

elif mean_error < 0.15:

    interpretation = (
        "Historical scenario weighting shows "
        "moderate calibration error. More "
        "resolved observations are required."
    )

else:

    interpretation = (
        "Historical scenario weighting shows "
        "high calibration error. The scenario "
        "engine requires additional learning."
    )

print(interpretation)
print()

print("CALIBRATION PRINCIPLES")
print("-" * 70)

principles = [
    "1. Scenario assessments are compared with actual future outcomes.",
    "2. Pending observations never contribute to accuracy.",
    "3. Four-, eight- and sixteen-candle horizons are measured separately.",
    "4. Bullish, bearish and neutral outcomes remain separate.",
    "5. Accuracy is based on resolved observations only.",
    "6. Calibration error measures how closely scenario weighting matches outcomes.",
    "7. Small samples are explicitly labelled as unreliable.",
    "8. Historical calibration does not guarantee future performance.",
    "9. Scenario percentages remain evidence-weighted until statistically calibrated.",
    "10. The engine does not create an automatic trading signal.",
]

for principle in principles:
    print(principle)

print()

print("CURRENT MARKET STORY")
print("-" * 70)

story = (
    f"The MLAI v2.2 calibration engine evaluates the "
    f"current {analysis_window}-candle market context as "
    f"{direct_direction}. The current scenario engine "
    f"classifies the primary scenario as "
    f"{primary_direction}. MLAI currently has "
    f"{sample_count} resolved calibration samples and "
    f"{len(pending_records)} pending calibration samples. "
    f"Overall historical scenario accuracy is "
    f"{overall_accuracy:.1f}% for the available resolved "
    f"sample, with a mean calibration error of "
    f"{mean_error:.4f}. The current reliability level is "
    f"{reliability_level}. These measurements describe "
    f"historical calibration only and do not guarantee "
    f"future market behaviour."
)

print(story)
print()


# ============================================================
# UPDATE PROJECT STATUS
# ============================================================

status_text = f"""# MLAI Project Status

## MLAI v2.2

**Status:** Completed

### Component

Outcome Calibration + Scenario Accuracy Learning Engine

### New Memory

`mlai_calibration_memory.bin`

### Current Calibration

- Resolved samples: {sample_count}
- Pending samples: {len(pending_records)}
- Overall accuracy: {overall_accuracy:.1f}%
- Mean calibration error: {mean_error:.4f}
- Reliability level: {reliability_level}

### Horizons

- 4 candles: {statistics_by_horizon[4]['accuracy']:.1f}% accuracy
- 8 candles: {statistics_by_horizon[8]['accuracy']:.1f}% accuracy
- 16 candles: {statistics_by_horizon[16]['accuracy']:.1f}% accuracy

### Principles

1. Actual future candles are required for calibration.
2. Pending outcomes receive zero learning influence.
3. Accuracy is measured separately by horizon.
4. Bullish, bearish and neutral outcomes remain separate.
5. Calibration error is measured independently from accuracy.
6. Small sample sizes are explicitly identified.
7. Historical calibration does not guarantee future behaviour.
8. No automatic trading signal is produced.

**Updated:** {datetime.now(timezone.utc).isoformat()}
"""

with open(
    STATUS_FILE,
    "w",
    encoding="utf-8"
) as f:
    f.write(status_text)

print(
    f"PASS: {STATUS_FILE} updated."
)
print()

print("=" * 70)
print(
    "PASS: MLAI v2.2 Outcome Calibration + "
    "Scenario Accuracy Learning Engine completed."
)
print("=" * 70)
