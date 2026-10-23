#!/usr/bin/env python3
"""Builds usda.json (USDA FoodData Central: Foundation Foods + SR Legacy) in the layout of ciqual.json.

Usage:
  python3 tools/usda_to_json.py <foundation_csv_dir> <sr_legacy_csv_dir> ciqual.json usda.json

The two folders are the unzipped "CSV" downloads from https://fdc.nal.usda.gov/download-datasets
(Foundation Foods and SR Legacy). Needs pandas. The source files are not in the repo.

The values in `v` follow the same 64 nutrients, in the same order, as ciqual.json, so the app can use both
with one nutrient list. Missing = null (no data). Nothing is guessed: a CIQUAL nutrient that USDA does not
report stays empty (polyols, organic acids, chloride). Only these are derived:
  - salt (g)        = sodium (mg) x 2.5 / 1000
  - crude protein   = nitrogen (g) x 6.25 (Foundation Foods only; SR Legacy has no nitrogen)
  - vitamin D (ug)  = IU x 0.025 when only IU is given
  - energy (kcal)   = 4/4/9 from protein/carbohydrate/fat when USDA gives no energy at all (flag "e": 1)
"""
import json
import re
import sys
import warnings

import pandas as pd

warnings.filterwarnings("ignore")
foundation_dir, sr_dir, ciqual_path, out_path = sys.argv[1:5]

cat = json.load(open(ciqual_path, encoding="utf-8"))
KEYS = [n["key"] for n in cat["nutrients"]]
UNITS = {n["key"]: n["unit"] for n in cat["nutrients"]}

# CIQUAL key -> USDA nutrient numbers (nutrient.csv "nutrient_nbr"); the first one that has a value wins.
MAP = {
    "water": ["255"], "protein": ["203"], "carbohydrate": ["205", "205.2"], "fat": ["204", "298"],
    "sugars": ["269", "269.3"], "fructose": ["212"], "galactose": ["287"], "glucose": ["211"], "lactose": ["213"],
    "maltose": ["214"], "sucrose": ["210"], "starch": ["209"], "fibres": ["291", "293"], "ash": ["207"], "alcohol": ["221"],
    "fa_saturated": ["606"], "fa_mono": ["645"], "fa_poly": ["646"],
    "fa_4_0": ["607"], "fa_6_0": ["608"], "fa_8_0": ["609"], "fa_10_0": ["610"], "fa_12_0": ["611"], "fa_14_0": ["612"],
    "fa_16_0": ["613"], "fa_18_0": ["614"],
    "fa_18_1_n_9_cis": ["674"], "fa_18_2_9c_12c_n_6": ["675"], "fa_18_3_c9_c12_c15_n_3": ["851"],
    "fa_20_4_5c_8c_11c_14c_n_6": ["855"],
    "fa_20_5_5c_8c_11c_14c_17c_n_3_epa": ["629"], "fa_22_6_4c_7c_10c_13c_16c_19c_n_3_dha": ["621"],
    "cholesterol": ["601"],
    "calcium": ["301"], "copper": ["312"], "iron": ["303"], "iodine": ["314"], "magnesium": ["304"], "manganese": ["315"],
    "phosphorus": ["305"], "potassium": ["306"], "selenium": ["317"], "sodium": ["307"], "zinc": ["309"],
    "retinol": ["319"], "beta_carotene": ["321"], "vitamin_d": ["328"], "vitamin_e": ["323"],
    "vitamin_k1": ["430"], "vitamin_k2": ["428"],            # K2: USDA reports menaquinone-4 only
    "vitamin_c": ["401"], "vitamin_b1_or_thiamin": ["404"], "vitamin_b2_or_riboflavin": ["405"],
    "vitamin_b3_or_niacin": ["406"], "vitamin_b5_or_pantothenic_acid": ["410"], "vitamin_b6": ["415"],
    "vitamin_b9_or_folate": ["417"], "vitamin_b12": ["418"],
}
DERIVED = {"kcal", "salt", "protein_crude_n_x_6_25", "polyols", "organic_acids", "chloride"}
assert set(KEYS) == set(MAP) | DERIVED, (set(KEYS) ^ (set(MAP) | DERIVED))
UNIT_OF = {"G": "g", "MG": "mg", "UG": "µg", "KCAL": "kcal"}


def rnd(x):
    if x is None:
        return None
    x = float(f"{x:.4g}")
    return int(x) if x == int(x) else x


def num_str(a):
    a = float(a)
    return str(int(a)) if a == int(a) else str(a)


def portion_label(amount, unit, desc, modifier):
    """'1 cup, sliced' | '1 egg, whole without shell' | '2 tablespoon'"""
    amount = num_str(amount) if amount not in ("", None) else "1"
    parts = []
    if unit and unit != "undetermined":
        parts.append(f"{amount} {unit}")
        parts += [p for p in (desc, modifier) if p]
        return ", ".join(parts)
    # SR Legacy: the unit is inside the modifier ("cup, sliced", "roll medium submarine, hoagie")
    first = (modifier or desc or "").strip()
    return f"{amount} {first}".strip()


def load(folder, data_type, dataset_name):
    food = pd.read_csv(folder + "/food.csv", dtype=str).fillna("")
    food = food[food.data_type == data_type]
    ids = set(food.fdc_id)
    nut = pd.read_csv(folder + "/nutrient.csv", dtype=str).fillna("")
    id_of = {}
    for _, r in nut.iterrows():
        if r.nutrient_nbr:
            assert r.nutrient_nbr not in id_of, ("duplicate nutrient number", r.nutrient_nbr)
            id_of[r.nutrient_nbr] = r.id
    unit_of_id = dict(zip(nut.id, nut.unit_name))
    # the units USDA reports must be the units the app uses
    for key, nbrs in MAP.items():
        for nb in nbrs:
            assert nb in id_of, ("nutrient number missing in nutrient.csv", key, nb, folder)
            assert UNIT_OF[unit_of_id[id_of[nb]]] == UNITS[key], ("unit mismatch", key, nb, unit_of_id[id_of[nb]], UNITS[key])
    fn = pd.read_csv(folder + "/food_nutrient.csv", dtype=str, usecols=["fdc_id", "nutrient_id", "amount"])
    fn = fn[fn.fdc_id.isin(ids)].dropna(subset=["amount"])
    vals = {}
    for fid, nid, amt in zip(fn.fdc_id, fn.nutrient_id, fn.amount):
        vals.setdefault(fid, {})[nid] = float(amt)      # a repeated pair (rare) keeps the last row
    units = pd.read_csv(folder + "/measure_unit.csv", dtype=str).set_index("id").name.to_dict()
    por = pd.read_csv(folder + "/food_portion.csv", dtype=str).fillna("")
    por = por[por.fdc_id.isin(ids)]
    portions = {}
    for _, r in por.iterrows():
        try:
            g = float(r.gram_weight)
        except ValueError:
            continue
        if g <= 0:
            continue
        label = portion_label(r.amount, units.get(r.measure_unit_id, ""), r.portion_description.strip(), r.modifier.strip())
        low = label.lower()
        if len(label) > 44 or low.split(" ", 1)[-1] in ("oz", "lb", "g", "kg"):
            continue                                   # weights are not household measures; very long texts do not fit a button
        lst = portions.setdefault(r.fdc_id, [])
        if all(l != label for l, _ in lst):
            lst.append([label, rnd(g)])
    out = []
    skipped = 0
    for _, r in food.iterrows():
        v = vals.get(r.fdc_id, {})

        def get(nbrs):
            for nb in nbrs:
                if nb in id_of and id_of[nb] in v:
                    return v[id_of[nb]]
            return None

        row = {}
        for key, nbrs in MAP.items():
            row[key] = get(nbrs)
        if row["vitamin_d"] is None and get(["324"]) is not None:          # IU only
            row["vitamin_d"] = get(["324"]) * 0.025
        kcal = get(["208", "958", "957"])
        if kcal is None and get(["268"]) is not None:                       # kJ only
            kcal = get(["268"]) / 4.184
        est = False
        if kcal is None and all(row[k] is not None for k in ("protein", "carbohydrate", "fat")):
            kcal = row["protein"] * 4 + row["carbohydrate"] * 4 + row["fat"] * 9
            est = True
        row["kcal"] = kcal
        row["salt"] = row["sodium"] * 2.5 / 1000 if row["sodium"] is not None else None
        nitrogen = get(["202"])
        row["protein_crude_n_x_6_25"] = nitrogen * 6.25 if nitrogen is not None else None
        row["polyols"] = row["organic_acids"] = row["chloride"] = None
        if kcal is None and row["protein"] is None and row["fat"] is None and row["carbohydrate"] is None:
            skipped += 1
            continue
        name = re.sub(r"\s*\(Includes foods for USDA's Food Distribution Program\)", "", r.description)
        name = re.sub(r"\s+", " ", name.replace("\u00a0", " ")).strip()      # some names contain no-break spaces
        # the FDC id is shown in the app: several Foundation foods share one name, and the id lets you look the food up on fdc.nal.usda.gov
        item = {"c": r.fdc_id, "n": name, "v": [rnd(row[k]) for k in KEYS], "g": f"{dataset_name} · FDC {r.fdc_id}"}
        if est:
            item["e"] = 1
        if r.fdc_id in portions:
            item["p"] = portions[r.fdc_id][:8]
        out.append(item)
    print(f"{dataset_name}: {len(out)} foods ({skipped} skipped without energy and macros), "
          f"{sum(1 for f in out if 'p' in f)} with household measures, energy estimated for {sum(1 for f in out if 'e' in f)}")
    return out


foods = load(foundation_dir, "foundation_food", "Foundation Foods") + load(sr_dir, "sr_legacy_food", "SR Legacy")
assert len({f["c"] for f in foods}) == len(foods)
out = {
    "source": "U.S. Department of Agriculture, Agricultural Research Service. FoodData Central: Foundation Foods (April 2026) and "
              "SR Legacy (April 2018). https://fdc.nal.usda.gov (U.S. public domain).",
    "per": "100 g edible portion",
    "encoding": "v[i] matches keys[i] (the same nutrients and order as ciqual.json): number | null = no data. "
                "foods[].e = 1: energy estimated from P/C/F. foods[].p = household measures [label, grams].",
    "keys": KEYS,
    "foods": foods,
}
with open(out_path, "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
print("foods:", len(foods), "nutrients:", len(KEYS))
