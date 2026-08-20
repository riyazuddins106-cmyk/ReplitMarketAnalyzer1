from pathlib import Path

p = Path("audit_mlai_v415_full_capability.py")
s = p.read_text(encoding="utf-8")

old = '''    spec = importlib.util.spec_from_file_location(
        "mlai_v415_target",
        TARGET.resolve(),
    )

    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)
'''

new = '''    module_name = "mlai_v415_target"

    spec = importlib.util.spec_from_file_location(
        module_name,
        TARGET.resolve(),
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Unable to create import specification for {TARGET}"
        )

    module = importlib.util.module_from_spec(spec)

    # IMPORTANT:
    # Register the module BEFORE executing it.
    # Python dataclasses and other runtime mechanisms may
    # resolve the currently executing module through sys.modules.
    sys.modules[module_name] = module

    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
'''

if old not in s:
    raise SystemExit(
        "PATCH NOT APPLIED: exact import block was not found."
    )

s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")

print("=" * 70)
print("AUDITOR IMPORT PATCH APPLIED")
print("=" * 70)
print("Modified: audit_mlai_v415_full_capability.py")
print("NOT modified: mlai_market_structure_v415.py")
print("NOT modified: market_data.bin")
print("NOT created: v4.1.6")
print("=" * 70)
