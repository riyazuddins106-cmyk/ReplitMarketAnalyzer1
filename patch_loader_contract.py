from pathlib import Path

p = Path("audit_mlai_v415_full_capability.py")
lines = p.read_text(encoding="utf-8").splitlines()

# ------------------------------------------------------------
# Find the actual loader call by content, not by a large block.
# ------------------------------------------------------------

call_index = None

for i, line in enumerate(lines):
    if "safe_call(loader)" in line:
        call_index = i
        break

if call_index is None:
    raise SystemExit(
        "PATCH NOT APPLIED: safe_call(loader) was not found."
    )

print(
    f"Found loader call at auditor line {call_index + 1}"
)

# Replace only the actual loader invocation.
indent = lines[call_index][
    :len(lines[call_index]) - len(lines[call_index].lstrip())
]

lines[call_index] = (
    indent
    + "ok, loader_result, detail = safe_call("
)

lines.insert(
    call_index + 1,
    indent + "    loader,"
)

lines.insert(
    call_index + 2,
    indent + "    str(DATA_FILE),"
)

lines.insert(
    call_index + 3,
    indent + ")"
)

# ------------------------------------------------------------
# Find the loader failure exit.
# We need to unpack the verified v4.1.5 return contract:
#
# load_market_data(path) -> (candles, invalid_count)
# ------------------------------------------------------------

failure_index = None

for i in range(call_index + 1, min(len(lines), call_index + 30)):
    if 'raise SystemExit(' in lines[i]:
        # Make sure this is the loader failure block.
        nearby = "\n".join(lines[call_index:i + 4])

        if "Target loader failed." in nearby:
            failure_index = i
            break

if failure_index is None:
    raise SystemExit(
        "PATCH NOT APPLIED: loader failure exit was not found."
    )

# Find the closing ')' of raise SystemExit("Target loader failed.")
closing_index = None

for i in range(failure_index, min(len(lines), failure_index + 8)):
    if lines[i].strip() == ")":
        closing_index = i
        break

if closing_index is None:
    raise SystemExit(
        "PATCH NOT APPLIED: loader failure block structure unexpected."
    )

# ------------------------------------------------------------
# Insert verified return-contract validation.
# ------------------------------------------------------------

insert_at = closing_index + 1

validation = [
    "",
    indent + "# Verified v4.1.5 loader contract:",
    indent + "# load_market_data(path) -> (candles, invalid_count)",
    "",
    indent + "if not isinstance(loader_result, tuple):",
    indent + "    result(",
    indent + '        "TARGET_LOADER",',
    indent + '        "FAIL",',
    indent + '        (',
    indent + '            "Loader returned "',
    indent + '            f"{type(loader_result).__name__}; expected tuple "', 
    indent + '            "(candles, invalid_count).",',
    indent + "        ),",
    indent + "    )",
    "",
    indent + '    raise SystemExit(',
    indent + '        "Target loader returned unexpected structure."',
    indent + "    )",
    "",
    indent + "if len(loader_result) != 2:",
    indent + "    result(",
    indent + '        "TARGET_LOADER",',
    indent + '        "FAIL",',
    indent + '        f"Loader returned tuple of length {len(loader_result)}; expected 2.",',
    indent + "    )",
    "",
    indent + "    raise SystemExit(",
    indent + '        "Target loader returned unexpected tuple length."',
    indent + "    )",
    "",
    indent + "candles, invalid_count = loader_result",
    "",
    indent + "if not isinstance(candles, (list, tuple)):",
    indent + "    result(",
    indent + '        "TARGET_LOADER",',
    indent + '        "FAIL",',
    indent + '        f"Loader returned invalid candle collection: {type(candles).__name__}.",',
    indent + "    )",
    "",
    indent + "    raise SystemExit(",
    indent + '        "Invalid candle collection returned by loader."',
    indent + "    )",
    "",
    indent + "if not isinstance(invalid_count, int):",
    indent + "    result(",
    indent + '        "TARGET_LOADER",',
    indent + '        "FAIL",',
    indent + '        f"Loader returned invalid count of type {type(invalid_count).__name__}.",',
    indent + "    )",
    "",
    indent + "    raise SystemExit(",
    indent + '        "Invalid invalid-count returned by loader."',
    indent + "    )",
    "",
    indent + "result(",
    indent + '    "TARGET_LOADER",',
    indent + '    "PASS",',
    indent + "    (",
    indent + '        f"Target loader returned {len(candles)} candles "',
    indent + '        f"and invalid_count={invalid_count}."',
    indent + "    ),",
    indent + ")",
]

lines[insert_at:insert_at] = validation

p.write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8",
)

print("=" * 80)
print("AUDITOR LOADER PATCH APPLIED")
print("=" * 80)
print("Modified : audit_mlai_v415_full_capability.py")
print("Engine   : NOT modified")
print("Data     : NOT modified")
print("v4.1.6   : NOT created")
print("=" * 80)
