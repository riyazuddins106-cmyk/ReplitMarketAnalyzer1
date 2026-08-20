from pathlib import Path

path = Path("mlai_market_structure_v386.py")

text = path.read_text(encoding="utf-8-sig")

old = '''    for event in structure_events:

        if event.reference_swing_index is None:
            event_reference_pass = False
            break

        swing = swing_by_index.get(
            event.reference_swing_index
        )

        if swing is None:
            event_reference_pass = False
            break

        if swing.confirmed_at > event.index:
            event_reference_pass = False
            break

        if abs(
            swing.price - event.level
        ) > PRICE_EPSILON:

            event_reference_pass = False
            break
'''

new = '''    for event in structure_events:

        if event.reference_swing_index is None:

            print()
            print("EVENT REFERENCE FAILURE")
            print(f"  Event index        : {event.index}")
            print(f"  Event              : {event.event}")
            print(f"  Direction          : {event.direction}")
            print(f"  Event level        : {event.level}")
            print(f"  Reference index    : None")

            event_reference_pass = False
            break

        swing = swing_by_index.get(
            event.reference_swing_index
        )

        if swing is None:

            print()
            print("EVENT REFERENCE FAILURE")
            print(f"  Event index        : {event.index}")
            print(f"  Event              : {event.event}")
            print(f"  Direction          : {event.direction}")
            print(f"  Event level        : {event.level}")
            print(
                f"  Reference index    : "
                f"{event.reference_swing_index}"
            )
            print("  Referenced swing   : NOT FOUND")

            event_reference_pass = False
            break

        if swing.confirmed_at > event.index:

            print()
            print("EVENT REFERENCE FAILURE")
            print(f"  Event index        : {event.index}")
            print(f"  Event              : {event.event}")
            print(f"  Direction          : {event.direction}")
            print(f"  Event level        : {event.level}")
            print(
                f"  Reference index    : "
                f"{event.reference_swing_index}"
            )
            print(
                f"  Swing confirmed at : "
                f"{swing.confirmed_at}"
            )
            print(
                "  ERROR: swing was not confirmed "
                "when event occurred."
            )

            event_reference_pass = False
            break

        price_difference = abs(
            swing.price - event.level
        )

        if price_difference > PRICE_EPSILON:

            print()
            print("EVENT REFERENCE FAILURE")
            print(f"  Event index        : {event.index}")
            print(f"  Event              : {event.event}")
            print(f"  Direction          : {event.direction}")
            print(f"  Event level        : {event.level}")
            print(
                f"  Reference index    : "
                f"{event.reference_swing_index}"
            )
            print(
                f"  Swing price        : "
                f"{swing.price}"
            )
            print(
                f"  Price difference   : "
                f"{price_difference}"
            )
            print(
                f"  PRICE_EPSILON      : "
                f"{PRICE_EPSILON}"
            )
            print(
                "  ERROR: event level does not "
                "match referenced swing."
            )

            event_reference_pass = False
            break
'''

if old not in text:
    raise RuntimeError(
        "Target event-reference audit block was not found."
    )

text = text.replace(old, new, 1)

path.write_text(
    text,
    encoding="utf-8",
)

print("EVENT REFERENCE DIAGNOSTIC INSTALLED")