from pathlib import Path
import re

path = Path("mlai_market_structure_v386.py")

text = path.read_text(encoding="utf-8-sig")

start = text.index("def check_window_boundaries(")

# Find the next function after check_window_boundaries().
match = re.search(
    r"\n(?=def\s+\w+\s*\()",
    text[start + len("def check_window_boundaries("):]
)

if not match:
    raise RuntimeError(
        "Could not find the next function after check_window_boundaries()."
    )

end = start + len("def check_window_boundaries(") + match.start()

replacement = '''def check_window_boundaries(windows, n):

    section("WALK-FORWARD BOUNDARY CHECK")

    passed = True
    previous_oos_end = None

    for window_number, window in enumerate(windows, start=1):

        train_start = window["train_start"]
        train_end = window["train_end"]
        oos_start = window["oos_start"]
        oos_end = window["oos_end"]

        print(
            f"Checking Window {window_number}: "
            f"TRAIN [{train_start}:{train_end}] | "
            f"OOS [{oos_start}:{oos_end}]"
        )

        if train_start < 0:
            print("  FAIL: train_start < 0")
            passed = False

        if train_end > n:
            print("  FAIL: train_end > dataset length")
            passed = False

        if oos_start < 0:
            print("  FAIL: oos_start < 0")
            passed = False

        if oos_end > n:
            print("  FAIL: oos_end > dataset length")
            passed = False

        if train_start >= train_end:
            print("  FAIL: invalid training range")
            passed = False

        if oos_start >= oos_end:
            print("  FAIL: invalid OOS range")
            passed = False

        if train_end != oos_start:
            print(
                f"  FAIL: TRAIN end {train_end} "
                f"!= OOS start {oos_start}"
            )
            passed = False

        if previous_oos_end is not None:

            if train_end != previous_oos_end:
                print(
                    f"  FAIL: expanding continuity: "
                    f"TRAIN end {train_end} "
                    f"!= previous OOS end {previous_oos_end}"
                )
                passed = False

        previous_oos_end = oos_end

    if windows and windows[-1]["oos_end"] != n:

        print(
            f"  FAIL: final OOS end "
            f"{windows[-1]['oos_end']} "
            f"!= dataset length {n}"
        )

        passed = False

    print()

    print(
        f"Window boundaries: "
        f"{'PASS' if passed else 'FAIL'}"
    )

    if not passed:

        raise RuntimeError(
            "Walk-forward boundary check failed."
        )

    return True


'''

path.write_text(
    text[:start] + replacement + text[end:],
    encoding="utf-8",
)

print("DEBUG BOUNDARY CHECK INSTALLED")