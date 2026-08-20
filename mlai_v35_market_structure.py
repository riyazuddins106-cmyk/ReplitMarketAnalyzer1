# ============================================================
# MLAI v3.5 — MARKET STRUCTURE FEATURE ENGINE
# ============================================================
#
# Adds:
#
# 1. Swing structure
#    - Higher High (HH)
#    - Higher Low (HL)
#    - Lower High (LH)
#    - Lower Low (LL)
#
# 2. Break of Structure (BOS)
#
# 3. Change of Character (CHoCH)
#
# 4. Distance to recent swing high / low
#
# 5. Liquidity sweeps
#
# 6. Candle displacement
#
# 7. Multi-horizon trend alignment
#
# 8. Consecutive directional candles / exhaustion
#
# 9. ATR-normalized distance
#
# 10. Support / resistance interaction
#
# IMPORTANT:
# All features are causal.
# No future candle is used to create the feature.
# ============================================================

import numpy as np
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

MS_SWING_LOOKBACK = 3

MS_SHORT_TREND = 10
MS_MEDIUM_TREND = 20
MS_LONG_TREND = 50

MS_ATR_PERIOD = 14

MS_SR_LOOKBACK = 20

MS_DISPLACEMENT_ATR = 1.5

MS_EXHAUSTION_STREAK = 5

MS_SR_ATR_DISTANCE = 0.50


# ============================================================
# MAIN FUNCTION
# ============================================================

def add_market_structure_features(df):
    """
    Add MLAI market-structure features to an OHLC dataframe.

    Required columns:
        open
        high
        low
        close

    The function is strictly causal:
    the value at candle t uses only candle t and candles
    before t.
    """

    df = df.copy()

    # --------------------------------------------------------
    # Validate columns
    # --------------------------------------------------------

    required_columns = [
        "open",
        "high",
        "low",
        "close",
    ]

    missing = [
        col
        for col in required_columns
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            "Missing OHLC columns: "
            + ", ".join(missing)
        )

    # --------------------------------------------------------
    # Numeric conversion
    # --------------------------------------------------------

    for col in required_columns:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    # ========================================================
    # 1. BASIC CANDLE STRUCTURE
    # ========================================================

    df["ms_range"] = (
        df["high"] - df["low"]
    )

    df["ms_body"] = (
        df["close"] - df["open"]
    )

    df["ms_abs_body"] = (
        df["ms_body"].abs()
    )

    df["ms_upper_wick"] = (
        df["high"]
        - df[["open", "close"]].max(axis=1)
    ).clip(lower=0)

    df["ms_lower_wick"] = (
        df[["open", "close"]].min(axis=1)
        - df["low"]
    ).clip(lower=0)

    df["ms_direction"] = np.select(
        [
            df["close"] > df["open"],
            df["close"] < df["open"],
        ],
        [
            1,
            -1,
        ],
        default=0,
    )

    # ========================================================
    # 2. ATR
    # ========================================================

    previous_close = df["close"].shift(1)

    true_range = pd.concat(
        [
            df["high"] - df["low"],
            (
                df["high"] - previous_close
            ).abs(),
            (
                df["low"] - previous_close
            ).abs(),
        ],
        axis=1,
    ).max(axis=1)

    df["ms_true_range"] = true_range

    df["ms_atr"] = (
        true_range
        .rolling(
            MS_ATR_PERIOD,
            min_periods=MS_ATR_PERIOD
        )
        .mean()
    )

    # ========================================================
    # 3. CONFIRMED HISTORICAL SWING LEVELS
    # ========================================================
    #
    # IMPORTANT:
    #
    # We use SHIFT(1).
    #
    # Therefore the current candle can never define the
    # historical swing level used by the current candle.
    #
    # This prevents direct look-ahead leakage.
    #
    # ========================================================

    prior_highs = (
        df["high"]
        .shift(1)
        .rolling(
            MS_SWING_LOOKBACK,
            min_periods=MS_SWING_LOOKBACK
        )
    )

    prior_lows = (
        df["low"]
        .shift(1)
        .rolling(
            MS_SWING_LOOKBACK,
            min_periods=MS_SWING_LOOKBACK
        )
    )

    df["ms_prior_high"] = prior_highs.max()

    df["ms_prior_low"] = prior_lows.min()

    # ========================================================
    # 4. RECENT SWING HIGH / LOW
    # ========================================================

    df["recent_swing_high"] = (
        df["high"]
        .shift(1)
        .rolling(
            MS_SR_LOOKBACK,
            min_periods=5
        )
        .max()
    )

    df["recent_swing_low"] = (
        df["low"]
        .shift(1)
        .rolling(
            MS_SR_LOOKBACK,
            min_periods=5
        )
        .min()
    )

    # Longer structural levels

    df["recent_swing_high_50"] = (
        df["high"]
        .shift(1)
        .rolling(
            50,
            min_periods=10
        )
        .max()
    )

    df["recent_swing_low_50"] = (
        df["low"]
        .shift(1)
        .rolling(
            50,
            min_periods=10
        )
        .min()
    )

    # ========================================================
    # 5. SWING HIGH / LOW EVENTS
    # ========================================================
    #
    # A candle becomes a structural candidate if it creates
    # a new local extreme relative to prior candles.
    #
    # These are causal candidate events, not future-confirmed
    # pivots.
    #
    # ========================================================

    df["swing_high_event"] = (
        df["high"] >
        df["ms_prior_high"]
    ).astype(int)

    df["swing_low_event"] = (
        df["low"] <
        df["ms_prior_low"]
    ).astype(int)

    # ========================================================
    # 6. HH / LH
    # ========================================================
    #
    # Compare current high with historical structural high.
    #
    # HH = current high above previous structural high
    # LH = current high below previous structural high
    #
    # ========================================================

    previous_structural_high = (
        df["recent_swing_high_50"]
        .shift(1)
    )

    previous_structural_low = (
        df["recent_swing_low_50"]
        .shift(1)
    )

    df["higher_high"] = (
        df["high"] >
        previous_structural_high
    ).astype(int)

    df["lower_high"] = (
        df["high"] <
        previous_structural_high
    ).astype(int)

    # ========================================================
    # 7. HL / LL
    # ========================================================

    df["higher_low"] = (
        df["low"] >
        previous_structural_low
    ).astype(int)

    df["lower_low"] = (
        df["low"] <
        previous_structural_low
    ).astype(int)

    # ========================================================
    # 8. SWING STRUCTURE STATE
    # ========================================================
    #
    # 2  = bullish structure
    # 1  = partially bullish
    # 0  = neutral / transition
    # -1 = partially bearish
    # -2 = bearish structure
    #
    # ========================================================

    bullish_structure = (
        (df["higher_high"] == 1) &
        (df["higher_low"] == 1)
    )

    bearish_structure = (
        (df["lower_high"] == 1) &
        (df["lower_low"] == 1)
    )

    partial_bullish = (
        (df["higher_high"] == 1) |
        (df["higher_low"] == 1)
    )

    partial_bearish = (
        (df["lower_high"] == 1) |
        (df["lower_low"] == 1)
    )

    df["swing_structure"] = np.select(
        [
            bullish_structure,
            bearish_structure,
            partial_bullish,
            partial_bearish,
        ],
        [
            2,
            -2,
            1,
            -1,
        ],
        default=0,
    )

    # ========================================================
    # 9. STRUCTURAL DIRECTION MEMORY
    # ========================================================

    df["structure_direction"] = (
        df["swing_structure"]
        .replace(0, np.nan)
        .ffill()
        .fillna(0)
    )

    # ========================================================
    # 10. BREAK OF STRUCTURE — BOS
    # ========================================================

    df["bullish_bos"] = (
        df["close"] >
        df["recent_swing_high"]
    ).astype(int)

    df["bearish_bos"] = (
        df["close"] <
        df["recent_swing_low"]
    ).astype(int)

    df["bos_direction"] = np.select(
        [
            df["bullish_bos"] == 1,
            df["bearish_bos"] == 1,
        ],
        [
            1,
            -1,
        ],
        default=0,
    )

    # ========================================================
    # 11. CHANGE OF CHARACTER — CHoCH
    # ========================================================

    previous_structure = (
        df["structure_direction"].shift(1)
    )

    df["bullish_choch"] = (
        (previous_structure < 0) &
        (df["bullish_bos"] == 1)
    ).astype(int)

    df["bearish_choch"] = (
        (previous_structure > 0) &
        (df["bearish_bos"] == 1)
    ).astype(int)

    df["choch_direction"] = np.select(
        [
            df["bullish_choch"] == 1,
            df["bearish_choch"] == 1,
        ],
        [
            1,
            -1,
        ],
        default=0,
    )

    # ========================================================
    # 12. DISTANCE TO SWING HIGH / LOW
    # ========================================================

    df["distance_to_swing_high"] = (
        df["recent_swing_high"]
        - df["close"]
    )

    df["distance_to_swing_low"] = (
        df["close"]
        - df["recent_swing_low"]
    )

    # Percentage distance

    safe_close = (
        df["close"]
        .replace(0, np.nan)
    )

    df["distance_to_swing_high_pct"] = (
        df["distance_to_swing_high"]
        / safe_close
    )

    df["distance_to_swing_low_pct"] = (
        df["distance_to_swing_low"]
        / safe_close
    )

    # ========================================================
    # 13. LIQUIDITY SWEEP
    # ========================================================
    #
    # HIGH SWEEP:
    #
    # High takes previous high
    # AND
    # candle closes back below that level.
    #
    # LOW SWEEP:
    #
    # Low takes previous low
    # AND
    # candle closes back above that level.
    #
    # ========================================================

    df["liquidity_sweep_high"] = (
        (df["high"] > df["recent_swing_high"]) &
        (df["close"] < df["recent_swing_high"])
    ).astype(int)

    df["liquidity_sweep_low"] = (
        (df["low"] < df["recent_swing_low"]) &
        (df["close"] > df["recent_swing_low"])
    ).astype(int)

    df["liquidity_sweep_direction"] = np.select(
        [
            df["liquidity_sweep_low"] == 1,
            df["liquidity_sweep_high"] == 1,
        ],
        [
            1,
            -1,
        ],
        default=0,
    )

    # Sweep depth

    safe_atr = (
        df["ms_atr"]
        .replace(0, np.nan)
    )

    df["high_sweep_depth_atr"] = (
        (
            df["high"] -
            df["recent_swing_high"]
        )
        / safe_atr
    )

    df["low_sweep_depth_atr"] = (
        (
            df["recent_swing_low"] -
            df["low"]
        )
        / safe_atr
    )

    # ========================================================
    # 14. CANDLE DISPLACEMENT
    # ========================================================

    df["range_atr"] = (
        df["ms_range"]
        / safe_atr
    )

    df["body_atr"] = (
        df["ms_abs_body"]
        / safe_atr
    )

    df["bullish_displacement"] = (
        (df["ms_direction"] == 1) &
        (df["body_atr"] >= MS_DISPLACEMENT_ATR)
    ).astype(int)

    df["bearish_displacement"] = (
        (df["ms_direction"] == -1) &
        (df["body_atr"] >= MS_DISPLACEMENT_ATR)
    ).astype(int)

    # ========================================================
    # 15. DISPLACEMENT STRENGTH
    # ========================================================

    df["displacement_strength"] = (
        df["body_atr"]
        * df["ms_direction"]
    )

    # ========================================================
    # 16. MULTI-HORIZON TREND
    # ========================================================

    for window in [
        MS_SHORT_TREND,
        MS_MEDIUM_TREND,
        MS_LONG_TREND,
    ]:

        moving_average = (
            df["close"]
            .rolling(
                window,
                min_periods=window
            )
            .mean()
        )

        df[f"trend_{window}"] = np.select(
            [
                df["close"] > moving_average,
                df["close"] < moving_average,
            ],
            [
                1,
                -1,
            ],
            default=0,
        )

    # ========================================================
    # 17. TREND ALIGNMENT
    # ========================================================

    df["trend_alignment_score"] = (
        df[f"trend_{MS_SHORT_TREND}"] +
        df[f"trend_{MS_MEDIUM_TREND}"] +
        df[f"trend_{MS_LONG_TREND}"]
    )

    df["trend_fully_bullish"] = (
        df["trend_alignment_score"] == 3
    ).astype(int)

    df["trend_fully_bearish"] = (
        df["trend_alignment_score"] == -3
    ).astype(int)

    df["trend_mixed"] = (
        df["trend_alignment_score"].abs() < 3
    ).astype(int)

    # ========================================================
    # 18. CONSECUTIVE BULLISH / BEARISH CANDLES
    # ========================================================

    bullish = (
        df["close"] > df["open"]
    ).astype(int)

    bearish = (
        df["close"] < df["open"]
    ).astype(int)

    # Bullish streak

    bullish_group = (
        bullish.eq(0).cumsum()
    )

    df["consecutive_bullish"] = (
        bullish
        .groupby(bullish_group)
        .cumsum()
    )

    # Bearish streak

    bearish_group = (
        bearish.eq(0).cumsum()
    )

    df["consecutive_bearish"] = (
        bearish
        .groupby(bearish_group)
        .cumsum()
    )

    # ========================================================
    # 19. EXHAUSTION
    # ========================================================

    df["bullish_exhaustion"] = (
        df["consecutive_bullish"]
        >= MS_EXHAUSTION_STREAK
    ).astype(int)

    df["bearish_exhaustion"] = (
        df["consecutive_bearish"]
        >= MS_EXHAUSTION_STREAK
    ).astype(int)

    df["directional_streak"] = (
        df["consecutive_bullish"]
        -
        df["consecutive_bearish"]
    )

    # ========================================================
    # 20. ATR-NORMALIZED DISTANCE
    # ========================================================

    df["close_to_swing_high_atr"] = (
        (
            df["recent_swing_high"]
            - df["close"]
        )
        / safe_atr
    )

    df["close_to_swing_low_atr"] = (
        (
            df["close"]
            - df["recent_swing_low"]
        )
        / safe_atr
    )

    df["support_distance_atr"] = (
        (
            df["close"]
            - df["recent_swing_low"]
        )
        / safe_atr
    )

    df["resistance_distance_atr"] = (
        (
            df["recent_swing_high"]
            - df["close"]
        )
        / safe_atr
    )

    # ========================================================
    # 21. SUPPORT / RESISTANCE INTERACTION
    # ========================================================

    df["near_support"] = (
        df["support_distance_atr"].abs()
        <= MS_SR_ATR_DISTANCE
    ).astype(int)

    df["near_resistance"] = (
        df["resistance_distance_atr"].abs()
        <= MS_SR_ATR_DISTANCE
    ).astype(int)

    # Support rejection:
    # candle trades to/below support but closes above it

    df["support_rejection"] = (
        (df["low"] <= df["recent_swing_low"]) &
        (df["close"] > df["recent_swing_low"])
    ).astype(int)

    # Resistance rejection:
    # candle trades to/above resistance but closes below it

    df["resistance_rejection"] = (
        (df["high"] >= df["recent_swing_high"]) &
        (df["close"] < df["recent_swing_high"])
    ).astype(int)

    # ========================================================
    # 22. SUPPORT / RESISTANCE BREAK
    # ========================================================

    df["support_break"] = (
        df["close"] <
        df["recent_swing_low"]
    ).astype(int)

    df["resistance_break"] = (
        df["close"] >
        df["recent_swing_high"]
    ).astype(int)

    # ========================================================
    # 23. STRUCTURAL COMPOSITE STATES
    # ========================================================

    df["market_structure_bias"] = (
        df["swing_structure"]
        +
        df["bos_direction"]
        +
        df["choch_direction"]
    )

    df["liquidity_event"] = (
        df["liquidity_sweep_direction"]
    )

    df["structure_event"] = np.select(
        [
            df["bullish_choch"] == 1,
            df["bearish_choch"] == 1,
            df["bullish_bos"] == 1,
            df["bearish_bos"] == 1,
            df["liquidity_sweep_low"] == 1,
            df["liquidity_sweep_high"] == 1,
        ],
        [
            5,   # bullish CHoCH
            -5,  # bearish CHoCH
            3,   # bullish BOS
            -3,  # bearish BOS
            2,   # bullish liquidity sweep
            -2,  # bearish liquidity sweep
        ],
        default=0,
    )

    # ========================================================
    # 24. CLEAN NUMERIC VALUES
    # ========================================================

    df.replace(
        [np.inf, -np.inf],
        np.nan,
        inplace=True
    )

    return df


# ============================================================
# USAGE
# ============================================================
#
# After your OHLC dataframe has been created:
#
#     df = add_market_structure_features(df)
#
# Then continue with your existing MLAI feature/quantile
# generation and validation pipeline.
#
# ============================================================