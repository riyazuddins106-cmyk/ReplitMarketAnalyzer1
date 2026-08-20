from pathlib import Path

p = Path("audit_mlai_v415_full_capability.py")
s = p.read_text(encoding="utf-8")

old = '''ok, candles, detail = safe_call(
    loader_fn,
)
'''

new = '''ok, candles, detail = safe_call(
    loader_fn,
    DATA_FILE,
)
'''

if old not in s:
    raise SystemExit(
        "PATCH NOT APPLIED: loader call block not found."
    )

s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")

print("=" * 70)
print("AUDITOR LOADER-CALL PATCH APPLIED")
print("=" * 70)
print("Modified: audit_mlai_v415_full_capability.py")
print("NOT modified: mlai_market_structure_v415.py")
print("NOT modified: market_data.bin")
print("NOT created: v4.1.6")
print("=" * 70)
