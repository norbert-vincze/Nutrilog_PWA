#!/usr/bin/env python3
"""Builds dmbio.json (dmBio products sold by dm Hungary) in the layout of ciqual.json / usda.json.

Usage:
  python3 -I tools/dmbio_to_json.py <products_dmbio_nutrilog_vN.json> <products_dmbio_nutrilog_vN.csv> ciqual.json dmbio.json

The two inputs come from the dmBio estimation project (method note: dmbio_becsles_v3_modszer_es_valtozasok.md):
the JSON is a Nutrilog backup file that only holds foods (ids "u:dm<article id>"), the CSV has the same products
with the extra columns (confidence, fortified, basis, label keys, ...). They are joined on the dm article id.
The source files are not in the repo.

What is in `v` (64 values, same nutrients and order as ciqual.json; null = no data):
  - the dm label values (energy, fat, saturated fat, carbohydrate, sugars, fibre, protein, salt, sodium, plus the
    label extras the CSV lists in "Címkéből átvett kulcsok") = measured. Their indexes are in `l`.
  - every other value is an ESTIMATE from the ingredient list (CIQUAL 2020 raw ingredients). `q` is its confidence.
  - products without a dm table (rule R6, R6e) have no label values at all (R3: only energy).
Nothing is guessed here: this script only re-arranges the file, it adds the portion sizes that the method note
gives (millilitres and prepared amounts), and checks the data.
"""
import csv
import json
import re
import sys

json_path, csv_path, ciqual_path, out_path = sys.argv[1:5]

cat = json.load(open(ciqual_path, encoding="utf-8"))
KEYS = [n["key"] for n in cat["nutrients"]]
IDX = {k: i for i, k in enumerate(KEYS)}

src = json.load(open(json_path, encoding="utf-8"))
foods = src["foods"]
rows = {r["Azonosító"]: r for r in csv.DictReader(open(csv_path, encoding="utf-8-sig"), delimiter=";")}
assert {"u:dm" + i for i in rows} == set(foods), "JSON and CSV do not hold the same products"

LABEL_MACRO = ["kcal", "fat", "fa_saturated", "carbohydrate", "sugars", "fibres", "protein", "salt", "sodium"]
CONF = {"magas": "h", "közepes": "m", "alacsony": "l", "nagyon alacsony": "v", "nincs becslés": "n"}
num = lambda s: float(s.replace(",", "."))   # the note writes 1.087 and 1,087


def portions(note, basis):
    """Portion sizes in grams that follow from the method note (nothing else is invented)."""
    m = re.search(r"átszámítva 100 g száraz termékre ×([0-9]+(?:[.,][0-9]+)?)", note)
    if m:                                    # R7: the dm values were for the prepared soup / drink
        f = num(m.group(1))
        out = [["100 ml prepared", round(100 / f, 1)]]
        if f >= 40:                          # soup powder and stock cube: the dm instructions are per 0.5 l
            out.append(["0.5 l prepared", round(500 / f, 1)])
        return out
    m = re.search(r"átszámítva 100 g-ra ×([0-9]+(?:[.,][0-9]+)?)", note)
    if m and "ml" in basis:                  # R8: values converted from 100 ml to 100 g; 100 ml weighs 100 / factor grams
        g = 100 / num(m.group(1))
        return [["100 ml", round(g, 1)], ["1 tbsp (15 ml)", round(g * 0.15, 1)], ["1 tsp (5 ml)", round(g * 0.05, 1)]]
    if basis.strip() == "100 ml":            # dm gives 100 ml, density within 5% of 1: kept as 100 g, 100 ml still gets its weight
        m = re.search(r"sűrűség ([0-9]+(?:[.,][0-9]+)?) g/ml", note)
        if m:
            return [["100 ml", round(100 * num(m.group(1)), 1)]]
    return []


out_foods = []
for fid, f in foods.items():
    i = fid[4:]
    r = rows[i]
    assert f["basis"] == {"qty": 100, "unit": "g"} and f["src"] == "user" and not f["portions"]
    n = f["n"]
    unknown = [k for k in n if k not in IDX]
    assert not unknown, (fid, unknown)
    v = [None] * len(KEYS)
    for k, x in n.items():
        ok = (isinstance(x, (int, float)) and x >= 0) or (isinstance(x, str) and re.fullmatch(r"<[0-9.]+", x))
        assert ok, (fid, k, x)
        v[IDX[k]] = x

    codes = set(re.findall(r"\bR\d+e?\b", r["dm makró-javítás"]))
    if "R6" in codes or "R6e" in codes:
        label = []                           # no dm table: the macros are not label values
    elif "R3" in codes:
        label = ["kcal"]                     # macadamia: only the energy is the dm value
    else:
        label = [k for k in LABEL_MACRO if k in n]
    extras = [k.strip() for k in r["Címkéből átvett kulcsok"].split(",") if k.strip()]
    assert all(k in IDX for k in extras), (fid, extras)
    label += [k for k in extras if k not in label]
    if "protein" in label and n.get("protein_crude_n_x_6_25") == n.get("protein"):
        label.append("protein_crude_n_x_6_25")   # a copy of the label protein
    label = sorted(IDX[k] for k in label if k in n)

    note = f["note"]
    note = re.sub(r"^dm\.hu termék, azonosító \d+\.\s*", "", note)
    note = re.sub(r"\s*Forrás: https://www\.dm\.hu/p/d/\S+\s*$", "", note)
    url = r["Forrás URL"].replace("https://www.dm.hu/p/d/", "")
    assert url.startswith(i), (fid, url)
    p = portions(f["note"], r["Tápérték alapja"])
    food = {"c": i, "n": f["name"], "b": f["barcode"], "v": v, "l": label, "q": CONF[r["Becslés megbízhatósága"]], "u": url, "x": note}
    if r["Dúsított lehet"] == "igen":
        food["f"] = 1
    if p:
        food["p"] = p
    out_foods.append(food)

assert len(out_foods) == 527 and len({f["b"] for f in out_foods}) == 527

out = {
    "source": "dmBio products of dm-drogerie markt Hungary (dm.hu). Energy and macronutrients: dm nutrition tables (corrected, see foods[].x). "
              "All other values: estimates from the ingredient list with CIQUAL 2020 (dmBio estimate v3, 2026-10-24) unless listed in foods[].l.",
    "per": "100 g (liquids converted from 100 ml; powders: dry product)",
    "encoding": "v[i] matches keys[i] (the same nutrients and order as ciqual.json): number | \"<x\" | null = no data. "
                "foods[].l = indexes of the values that are dm label values; every other non-null value is an estimate. "
                "q = confidence of the estimate: h high, m medium, l low, v very low, n none. f = 1: may be fortified. "
                "p = portions [label, grams]. b = barcode, c = dm article id, u = dm.hu path, x = note (Hungarian).",
    "keys": KEYS,
    "foods": out_foods,
}
json.dump(out, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
est = sum(1 for f in out_foods for i, x in enumerate(f["v"]) if x is not None and i not in f["l"])
print(f"{len(out_foods)} foods, {est} estimated values, {sum(len(f['l']) for f in out_foods)} label values, "
      f"{sum(1 for f in out_foods if f.get('p'))} with portions, {sum(1 for f in out_foods if f.get('f'))} fortified")
