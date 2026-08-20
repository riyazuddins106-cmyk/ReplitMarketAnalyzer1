from pathlib import Path

path = Path("mlai_market_structure_v386.py")

text = path.read_text(encoding="utf-8-sig")

old = '''        if bullish_break:

            if trend in (
                "BEARISH",
                "NEUTRAL",
            ):

                event = "CHoCH_BULLISH"

            else:

                event = "BOS_BULLISH"

            event_direction = "BULLISH"

            event_level = bullish_level
            reference_index = bullish_reference_index

            bullish_consumed = True
            consumed = True

            trend = "BULLISH"
            persistence = 0

        elif bearish_break:

            if trend in (
                "BULLISH",
                "NEUTRAL",
            ):

                event = "CHoCH_BEARISH"

            else:

                event = "BOS_BEARISH"

            event_direction = "BEARISH"

            event_level = bearish_level
            reference_index = bearish_reference_index

            bearish_consumed = True
            consumed = True

            trend = "BEARISH"
            persistence = 0
'''

new = '''        if bullish_break:

            if trend in (
                "BEARISH",
                "NEUTRAL",
            ):

                event = "CHoCH_BULLISH"

            else:

                event = "BOS_BULLISH"

            event_direction = "BULLISH"

            # ------------------------------------------------------------------
            # STRICT STRUCTURAL REFERENCE INVARIANT
            #
            # The event level MUST come from the exact swing identified by
            # reference_index. Never allow the event level and reference swing
            # to become detached.
            # ------------------------------------------------------------------

            reference_index = bullish_reference_index

            if reference_index is None:
                raise RuntimeError(
                    "BULLISH STRUCTURAL EVENT HAS NO REFERENCE SWING."
                )

            reference_swing = next(
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

            if reference_swing.kind != "HIGH":
                raise RuntimeError(
                    f"BULLISH STRUCTURAL EVENT REFERENCES "
                    f"NON-HIGH SWING {reference_index}."
                )

            event_level = reference_swing.price

            bullish_level = reference_swing.price

            bullish_consumed = True
            consumed = True

            trend = "BULLISH"
            persistence = 0

        elif bearish_break:

            if trend in (
                "BULLISH",
                "NEUTRAL",
            ):

                event = "CHoCH_BEARISH"

            else:

                event = "BOS_BEARISH"

            event_direction = "BEARISH"

            # ------------------------------------------------------------------
            # STRICT STRUCTURAL REFERENCE INVARIANT
            #
            # The event level MUST come from the exact swing identified by
            # reference_index. Never allow the event level and reference swing
            # to become detached.
            # ------------------------------------------------------------------

            reference_index = bearish_reference_index

            if reference_index is None:
                raise RuntimeError(
                    "BEARISH STRUCTURAL EVENT HAS NO REFERENCE SWING."
                )

            reference_swing = next(
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

            if reference_swing.kind != "LOW":
                raise RuntimeError(
                    f"BEARISH STRUCTURAL EVENT REFERENCES "
                    f"NON-LOW SWING {reference_index}."
                )

            event_level = reference_swing.price

            bearish_level = reference_swing.price

            bearish_consumed = True
            consumed = True

            trend = "BEARISH"
            persistence = 0
'''

if old not in text:
    raise RuntimeError(
        "TARGET STRUCTURAL EVENT BLOCK NOT FOUND. "
        "No changes were made."
    )

text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")

print("STRUCTURAL REFERENCE FIX INSTALLED")
print()
print("Changed:")
print("  - bullish event level is now taken from exact referenced HIGH swing")
print("  - bearish event level is now taken from exact referenced LOW swing")
print("  - missing/invalid references now fail immediately")
print("  - audit remains strict")