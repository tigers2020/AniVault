import json

with open("function_violations_after_4.json", encoding="utf-8") as f:
    data = json.load(f)

# Filter and sort violations
violations = [
    v
    for v in data["violations"]
    if v["type"] in ["length", "complexity"] and v["value"] >= 10
]
sorted_violations = sorted(violations, key=lambda x: x["value"], reverse=True)

# Print top 10
print("Top 10 violations:")
for i, v in enumerate(sorted_violations[:10], 1):
    filename = v["file"].split("\\")[-1]
    print(f"{i}. {filename}:{v['function']} - {v['type']}: {v['value']}")
