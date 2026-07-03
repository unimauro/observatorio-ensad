import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "presupuesto-ensad.json")
raw = json.load(open(os.path.join(HERE, "ca_ensad_raw.json")))
doc = json.load(open(DATA))

existing = {r["year"]: r for r in doc["serie"]}  # tiene 2025, 2026
for ystr, rec in raw.items():
    y = int(ystr)
    if y in (2025, 2026):
        continue  # NO tocar
    existing[y] = rec

doc["serie"] = [existing[y] for y in sorted(existing)]
years = sorted(existing)
doc["_meta"]["nota"] = (f"Serie {years[0]}-{years[-1]}. ENSAD como UE 123 del pliego 010 MINEDU "
                        f"existe desde 2016 (creada por RM 400-2015-MINEDU); 2012-2015 sin UE propia. "
                        f"2025 cerrado; 2026 en ejecución parcial.")

json.dump(doc, open(DATA, "w"), ensure_ascii=False, separators=(",", ":"))
print("Años en serie:", [r["year"] for r in doc["serie"]])
print("2025:", existing[2025]["pim"], "| 2026:", existing[2026]["pim"])
