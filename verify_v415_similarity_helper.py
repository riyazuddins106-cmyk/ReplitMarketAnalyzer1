import inspect
import mlai_market_structure_v415 as m

print("=" * 100)
print("MLAI v4.1.5 - SIMILARITY HELPER FORENSIC CHECK")
print("=" * 100)

print()
print("1. REQUIRED HELPER")
print("-" * 100)
print("_mlai_fix_similarity_total exists:",
      hasattr(m, "_mlai_fix_similarity_total"))

if hasattr(m, "_mlai_fix_similarity_total"):
    print(inspect.getsource(m._mlai_fix_similarity_total))

print()
print("2. similarity_score()")
print("-" * 100)
print(inspect.getsource(m.similarity_score))

print()
print("3. ALL MODULE NAMES CONTAINING 'SIMILARITY'")
print("-" * 100)

for name in sorted(dir(m)):
    if "similarity" in name.lower():
        obj = getattr(m, name)
        print(f"{name:<45} {type(obj).__name__}")

print()
print("4. REPAIRED CLASS-EVIDENCE FUNCTION")
print("-" * 100)
print(inspect.getsource(m._mlai_fix_class_evidence))

print()
print("5. SOURCE REFERENCES TO _mlai_fix_similarity_total")
print("-" * 100)

source = inspect.getsource(m)

for line_no, line in enumerate(source.splitlines(), 1):
    if "_mlai_fix_similarity_total" in line:
        print(f"{line_no}: {line}")

print()
print("=" * 100)
print("FORENSIC CHECK COMPLETE")
print("=" * 100)
