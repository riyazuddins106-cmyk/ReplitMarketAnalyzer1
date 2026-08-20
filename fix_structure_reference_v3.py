from pathlib import Path

TARGET = Path("mlai_market_structure_v386.py")

text = TARGET.read_text(encoding="utf-8-sig")

old_bullish = '''            reference_swing = next(
                (
                    s
                    for s in swings
                    if s.index == reference_index
                ),
                None,
            )

            if reference_swing is None:
                raise RuntimeError(
                    f"BULLISH STRUCTURAL EVENT REFERENCES "
                    f"UNKNOWN SWING INDEX {reference_index}."
                )

            # A bullish break is caused by breaking the active
            # LOW-derived bullish structural level.
            #
            # Do not require the reference swing to be HIGH here.
            # The existing market-structure design intentionally uses
            # LOW -> bullish reference level.
            event_level = reference_swing.price

            bullish_level = reference_swing.price
'''

new_bullish = '''            reference_swing = next(
                (
                    s
                    for s in swings
                    if s.index == reference_index
                ),
                None,
            )

            if reference_swing is None:
                raise RuntimeError(
                    f"BULLISH STRUCTURAL EVENT REFERENCES "
                    f"UNKNOWN SWING INDEX {reference_index}."
                )

            if reference_swing.kind != "LOW":
                raise RuntimeError(
                    f"BULLISH STRUCTURAL EVENT REFERENCES "
                    f"NON-LOW SWING {reference_index}."
                )

            # The reference swing is the single source of truth.
            #
            # Never copy a previously stored structural level here.
            # The event level is derived directly from the exact
            # referenced LOW swing at event creation time.
            event_level = reference_swing.price
            bullish_level = reference_swing.price
'''

old_bearish = '''            reference_swing = next(
                (
                    s
                    for s in swings
                    if s.index == reference_index
                ),
                None,
            )

            if reference_swing is None:
                raise RuntimeError(
                    f"BEARISH STRUCTURAL EVENT REFERENCES "
                    f"UNKNOWN SWING INDEX {reference_index}."
                )

            # A bearish break is caused by breaking the active
            # HIGH-derived bearish structural level.
            #
            # Do not require the reference swing to be LOW here.
            # The existing market-structure design intentionally uses
            # HIGH -> bearish reference level.
            event_level = reference_swing.price

            bearish_level = reference_swing.price
'''

new_bearish = '''            reference_swing = next(
                (
                    s
                    for s in swings
                    if s.index == reference_index
                ),
                None,
            )

            if reference_swing is None:
                raise RuntimeError(
                    f"BEARISH STRUCTURAL EVENT REFERENCES "
                    f"UNKNOWN SWING INDEX {reference_index}."
                )

            if reference_swing.kind != "HIGH":
                raise RuntimeError(
                    f"BEARISH STRUCTURAL EVENT REFERENCES "
                    f"NON-HIGH SWING {reference_index}."
                )

            # The reference swing is the single source of truth.
            #
            # Never copy a previously stored structural level here.
            # The event level is derived directly from the exact
            # referenced HIGH swing at event creation time.
            event_level = reference_swing.price
            bearish_level = reference_swing.price
'''

if old_bullish not in text:
    raise RuntimeError(
        "Could not find bullish structural reference block."
    )

if old_bearish not in text:
    raise RuntimeError(
        "Could not find bearish structural reference block."
    )

text = text.replace(
    old_bullish,
    new_bullish,
    1,
)

text = text.replace(
    old_bearish,
    new_bearish,
    1,
)

TARGET.write_text(
    text,
    encoding="utf-8",
)

print("STRUCTURAL REFERENCE FIX V3 INSTALLED")
print()
print("Changed:")
print("  - LOW is the only valid bullish reference")
print("  - HIGH is the only valid bearish reference")
print("  - event level comes directly from referenced swing")
print("  - structural reference is validated at event creation")
print("  - causal audit remains strict")