import json
import re
import sys
import warnings

import pandas as pd

warnings.filterwarnings("ignore")

src, dst = sys.argv[1], sys.argv[2]
df = pd.read_excel(src, engine="xlrd", dtype=str)

META = ["alim_grp_code", "alim_ssgrp_code", "alim_ssssgrp_code", "alim_grp_nom_eng",
        "alim_ssgrp_nom_eng", "alim_ssssgrp_nom_eng", "alim_code", "alim_nom_eng", "alim_nom_sci"]
value_cols = [c for c in df.columns if c not in META]

kcal_cols = [c for c in value_cols if c.startswith("Energy") and "kcal" in c]
kj_cols = [c for c in value_cols if c.startswith("Energy") and "kJ" in c]
energy_cols = set(kcal_cols + kj_cols)

# nutrient catalogue (everything except the 4 energy columns, which are merged below)
nutrients = [{"key": "kcal", "label": "Energy", "unit": "kcal"}]
col_for = []
for c in value_cols:
    if c in energy_cols:
        continue
    m = re.search(r"\(([^/()]+)/100g\)\s*$", c)
    unit = m.group(1) if m else "?"
    label = re.sub(r"\s*\([^()]*/100g\)\s*$", "", c).strip()
    label = re.sub(r"\s*\.\.\.$", "", label)
    key = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")[:40]
    nutrients.append({"key": key, "label": label, "unit": unit})
    col_for.append(c)
keys = [n["key"] for n in nutrients]
assert len(set(keys)) == len(keys), [k for k in keys if keys.count(k) > 1]


def parse(v):
    """number | None (missing) | '<x' (below limit) | 't' (traces)"""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip()
    if s in ("-", "", "nan"):
        return None
    if s.lower().startswith("trace"):
        return "t"
    if s.startswith("<"):
        return "<" + s[1:].strip().replace(",", ".")
    return float(s.replace(",", "."))


P, C, F = "Protein (g/100g)", "Carbohydrate (g/100g)", "Fat (g/100g)"
foods = []
est = 0
for _, r in df.iterrows():
    kcal = None
    for c in kcal_cols:
        x = parse(r[c])
        if isinstance(x, float):
            kcal = x
            break
    kcal_est = False
    if kcal is None:
        p, c_, f = parse(r[P]), parse(r[C]), parse(r[F])
        ok = all(isinstance(t, float) or t in ("t",) or (isinstance(t, str) and t.startswith("<")) for t in (p, c_, f))
        num = lambda t: t if isinstance(t, float) else 0.0
        if ok:
            kcal = round(num(p) * 4 + num(c_) * 4 + num(f) * 9, 1)
            kcal_est = True
            est += 1
    vals = [kcal] + [parse(r[c]) for c in col_for]
    item = {"c": str(r["alim_code"]).strip(), "n": r["alim_nom_eng"], "v": vals}
    for k, col in (("g", "alim_ssgrp_nom_eng"), ("G", "alim_grp_nom_eng")):
        if isinstance(r[col], str) and r[col].strip() not in ("-", "", "nan"):
            item[k] = r[col].strip()
    if kcal_est:
        item["e"] = 1  # energy estimated with Atwater factors from protein/carbohydrate/fat
    foods.append(item)

out = {
    "source": "Anses. 2020. Ciqual French food composition table (CC BY 4.0). https://doi.org/10.5281/zenodo.4770202",
    "per": "100 g edible portion",
    "encoding": "v[i] matches nutrients[i]: number | null = no data | '<x' = below limit | 't' = traces. foods[].e = 1: energy estimated from P/C/F.",
    "nutrients": nutrients,
    "foods": foods,
}
with open(dst, "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
print("foods:", len(foods), "nutrients:", len(nutrients), "energy estimated for:", est)
