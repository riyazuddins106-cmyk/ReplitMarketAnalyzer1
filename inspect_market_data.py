import pickle

DATA_FILE = "market_data.bin"

print("=" * 70)
print("MLAI MARKET MEMORY INSPECTOR")
print("=" * 70)

with open(DATA_FILE, "rb") as f:
    data = pickle.load(f)

print()
print("Stored object type:")
print(type(data))

print()

if isinstance(data, dict):
    print("Dictionary keys:")
    for key in data.keys():
        print(f"  - {key}")

elif isinstance(data, (list, tuple)):
    print(f"Sequence length: {len(data)}")

    if len(data) > 0:
        print()
        print("First item type:")
        print(type(data[0]))

        print()
        print("First item:")
        print(data[0])

else:
    print("Stored object:")
    print(data)

print()
print("=" * 70)
print("INSPECTION COMPLETE")
print("=" * 70)