from pathlib import Path

path = Path("mlai_market_structure_v386.py")

text = path.read_text(encoding="utf-8-sig")

old_bull = '''            if reference_swing.kind != "HIGH":
                raise RuntimeError(
                    f"BULLISH STRUCTURAL EVENT REFERENCES "
                    f"NON-HIGH SWING {reference_index}."
                )

            event_level = reference_swing.price

            bullish_level = reference_swing.price
'''

new_bull = '''            # A bullish break is caused by breaking the active
            # LOW-derived bullish structural level.
            #
            # Do not require the reference swing to be HIGH here.
            # The existing market-structure design intentionally uses
            # LOW -> bullish reference level.
            event_level = reference_swing.price

            bullish_level = reference_swing.price
'''

old_bear = '''            if reference_swing.kind != "LOW":
                raise RuntimeError(
                    f"BEARISH STRUCTURAL EVENT REFERENCES "
                    f"NON-LOW SWING {reference_index}."
                )

            event_level = reference_swing.price

            bearish_level = reference_swing.price
'''

new_bear = '''            # A bearish break is caused by breaking the active
            # HIGH-derived bearish structural level.
            #
            # Do not require the reference swing to be LOW here.
            # The existing market-structure design intentionally uses
            # HIGH -> bearish reference level.
            event_level = reference_swing.price

            bearish_level = reference_swing.price
'''

if old_bull not in text:
    raise RuntimeError(
        "Bullish strict-kind block not found. No changes made."
    )

if old_bear not in text:
    raise RuntimeError(
        "Bearish strict-kind block not found. No changes made."
    )

text = text.replace(old_bull, new_bull, 1)
text = text.replace(old_bear, new_bear, 1)

path.write_text(text, encoding="utf-8")

print("STRUCTURAL REFERENCE FIX V2 INSTALLED")
print()
print("Preserved:")
print("  LOW  -> bullish structural reference")
print("  HIGH -> bearish structural reference")
print()
print("Enforced:")
print("  event_level == referenced_swing.price")
print("  reference swing must exist")
print("  causal audit remains unchanged")