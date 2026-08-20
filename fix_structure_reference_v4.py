from pathlib import Path

TARGET = Path("mlai_market_structure_v386.py")

text = TARGET.read_text(encoding="utf-8-sig")


# ============================================================
# 1. Add direction-aware structural swing lookup
# ============================================================

anchor = "# ================================================================================\n# CAUSALITY AUDIT"

helper = '''# ==============================================================================
# STRUCTURAL SWING IDENTITY
# ==============================================================================

def get_structural_swing(
    swings,
    index,
    kind,
):
    """
    A structural swing is uniquely identified by:

        (candle index, swing kind)

    A candle may legally contain both a HIGH and LOW swing.
    Therefore index alone is NOT a unique structural identity.
    """

    if index is None:
        return None

    for swing in swings:

        if (
            swing.index == index
            and swing.kind == kind
        ):
            return swing

    return None


'''

if "def get_structural_swing(" not in text:

    if anchor not in text:
        raise RuntimeError(
            "Could not locate CAUSALITY AUDIT section."
        )

    text = text.replace(
        anchor,
        helper + anchor,
        1,
    )


# ============================================================
# 2. Replace bullish reference lookup
# ============================================================

old = '''            reference_swing = next(
                (
                    s
                    for s in swings
                    if s.index == reference_index
                ),
                None,
            )
'''

new_bullish = '''            reference_swing = get_structural_swing(
                swings,
                reference_index,
                "LOW",
            )
'''

if old not in text:
    raise RuntimeError(
        "Bullish reference lookup was not found."
    )

text = text.replace(
    old,
    new_bullish,
    1,
)


# ============================================================
# 3. Replace bearish reference lookup
# ============================================================

if old not in text:
    raise RuntimeError(
        "Bearish reference lookup was not found."
    )

new_bearish = '''            reference_swing = get_structural_swing(
                swings,
                reference_index,
                "HIGH",
            )
'''

text = text.replace(
    old,
    new_bearish,
    1,
)


# ============================================================
# 4. Replace audit dictionary
# ============================================================

old_map = '''    swing_by_index = {
        swing.index: swing
        for swing in swings
    }
'''

new_map = '''    # IMPORTANT:
    # Candle index alone is not a unique swing identity.
    # A candle may contain both HIGH and LOW.
    swing_by_identity = {
        (swing.index, swing.kind): swing
        for swing in swings
    }
'''

if old_map not in text:
    raise RuntimeError(
        "Audit swing_by_index dictionary was not found."
    )

text = text.replace(
    old_map,
    new_map,
    1,
)


# ============================================================
# 5. Replace audit lookup
# ============================================================

old_lookup = '''        swing = swing_by_index.get(
            event.reference_swing_index
        )
'''

new_lookup = '''        expected_kind = (
            "LOW"
            if event.direction == "BULLISH"
            else "HIGH"
            if event.direction == "BEARISH"
            else None
        )

        if expected_kind is None:

            print()
            print("EVENT REFERENCE FAILURE")
            print(f"  Event index        : {event.index}")
            print(f"  Event              : {event.event}")
            print(f"  Direction          : {event.direction}")
            print("  ERROR: invalid event direction.")

            event_reference_pass = False
            break

        swing = swing_by_identity.get(
            (
                event.reference_swing_index,
                expected_kind,
            )
        )
'''

if old_lookup not in text:
    raise RuntimeError(
        "Audit event reference lookup was not found."
    )

text = text.replace(
    old_lookup,
    new_lookup,
    1,
)


# ============================================================
# 6. Fix one-break identity
# ============================================================

old_break = '''        key = (
            event.reference_swing_index,
            event.level,
        )
'''

new_break = '''        expected_kind = (
            "LOW"
            if event.direction == "BULLISH"
            else "HIGH"
        )

        # One break per actual structural swing.
        # Index alone is insufficient because HIGH and LOW
        # can occur on the same candle.
        key = (
            event.reference_swing_index,
            expected_kind,
        )
'''

if old_break not in text:
    raise RuntimeError(
        "One-break audit key was not found."
    )

text = text.replace(
    old_break,
    new_break,
    1,
)


# ============================================================
# 7. Write file
# ============================================================

TARGET.write_text(
    text,
    encoding="utf-8",
)

print("STRUCTURAL REFERENCE FIX V4 INSTALLED")
print()
print("ROOT CAUSE FIX:")
print("  - structural identity = (index, kind)")
print("  - bullish reference = LOW")
print("  - bearish reference = HIGH")
print("  - event level comes from exact referenced swing")
print("  - event audit uses typed structural identity")
print("  - one-break audit uses typed structural identity")
print("  - causal audit remains strict")