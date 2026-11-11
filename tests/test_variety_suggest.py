"""Variety suggestion tools, step L3 (version 39): tools/variety_kitchen.py (the kitchen-ingredients test) and tools/variety_suggest.py (suggestions, approved rows -> map files, the "top" list).
No browser, no web server: plain Python, run with `python3 test_variety_suggest.py` from the tests folder.

Norbert's Variety plan (step L3): a script makes a SUGGESTION file from the three built-in tables (CIQUAL group + keyword rules + aliases of the list); only rows that Norbert approves go into
vt_map_ciqual.json / vt_map_usda.json / vt_map_dmbio.json; nothing is filled in automatically. Covers: the kitchen test (the plan's five examples and more, no ingredient list = no answer), the traps
of the plan (coconut water, pumpkin flesh and seed, olive oil, black pepper, corn oil ...), other places where a name word misleads (cheese is no milk, root beer is no beer, ...), the hand-classified
yardstick (tests/fixture_variety_hand.json.txt: 2 x 50 foods drawn at random with fixed seeds; at least 95% agree, and a wrong suggestion is the thing to avoid), every suggested group exists in the list,
the real CIQUAL table end to end, apply (only approved rows, a typed final group wins, an unknown group or a flag on the wrong group is refused, existing rows stay, sorted, shape of the file),
top (the foods logged most often that have no group), the command line, and that the tools never touch the nutrient tables, the list or the shipped (empty) maps."""
import csv, hashlib, io, json, os, pathlib, shutil, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'tools'))
import variety_kitchen as K          # noqa: E402
import variety_suggest as V          # noqa: E402

problems = []


def check(name, ok, info=''):
    print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(info)[:500].replace('\n', ' | ')) if info != '' else ''))
    if not ok:
        problems.append(name)


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


GUARDED = ['ciqual.json', 'usda.json', 'dmbio.json', 'variety_units.json', 'vt_map_ciqual.json', 'vt_map_usda.json', 'vt_map_dmbio.json']
before = {f: sha(ROOT / f) for f in GUARDED}
vl = V.VList()

# =============================================================== 1. the kitchen test (plan, step L3)
C = K.kitchenIngredientsOnly
check('plan: "kukorica, olaj, só" is a kitchen list: popcorn = maize (gra.corn.corn)', C('kukorica, olaj, só') is True and K.popcornClass('kukorica, olaj, só') == 'gra.corn.corn')
check('plan: "kukorica, olaj, aroma" is not (a flavouring): popcorn is a snack (sna.corn)', C('kukorica, olaj, aroma') is False and K.popcornClass('kukorica, olaj, aroma') == 'sna.corn')
H1, H2 = 'csicseriborsó, tahini, olívaolaj, citrom, só', 'csicseriborsó, tahini, olívaolaj, citrom, só, tartósítószer'
check('plan: hummus of chickpea, tahini, olive oil, lemon, salt is the chickpea (leg.chickpea-pea.chickpea)', C(H1) is True and K.hummusClass(H1) == 'leg.chickpea-pea.chickpea')
check('plan: the same with a preservative is a mixed dish (dis.legume-veg), no unit', C(H2) is False and K.hummusClass(H2) == 'dis.legume-veg')
check('plan: no ingredient list = null, never a guess (None, an empty text, only spaces)',
      all(f(x) is None for f in (K.kitchenIngredientsOnly, K.popcornClass, K.hummusClass) for x in (None, '', '   ', '\n')), [K.popcornClass(None), K.hummusClass(''), C('  ')])
for label, ing, want in [
    ('sea salt and sunflower oil', 'pattogatott kukorica, napraforgóolaj, tengeri só', True),
    ('an E-number', 'kukorica, napraforgóolaj, só, E330', False),
    ('"natural flavouring"', 'kukorica, olaj, só, természetes aroma', False),
    ('a thickener in brackets (the hummus of dm)', 'csicseriborsó (52%), tahini, olívaolaj, citromlé, tengeri só, sűrítőanyag: guarmagliszt', False),
    ('tahini written with its seed in brackets', 'csicseriborsó, tahini (szezámmag), olívaolaj, citromlé, só', True),
    ('sugar counts as a kitchen ingredient (open question of the plan: caramel popcorn)', 'kukorica, cukor, vaj, só', True),
    ('a percent and a footnote star', 'bio kukorica*, bio napraforgóolaj*, tengeri só', True),
    ('an acid regulator', 'csicseriborsó, tahini, olívaolaj, citromsav, só', False),
    ('a yeast extract', 'kukorica, olaj, élesztőkivonat', False),
    ('an ingredient the closed list does not know is not a kitchen ingredient', 'kukorica, olaj, só, ördögszekér', False),
]:
    got = C(ing)
    check(f'kitchen test: {label} -> {want}', got is want, [ing, got, K.kitchenCheck(ing)])
fl = K.kitchenCheck('kukorica, olaj, aroma')
en = K.kitchenCheck('kukorica, olaj, só, E330')
check('a flavouring and an E-number are named as NOT kitchen ("bad"), an ingredient nobody listed is "unknown": the two reasons are kept apart',
      fl['ok'] is False and fl['bad'] == ['aroma'] and fl['unknown'] == [] and en['bad'] == ['E330'] and en['unknown'] == [], [fl, en])
chk = K.kitchenCheck('kukorica, olaj, só, ördögszekér')
check('an ingredient that is not on the closed list is reported as "unknown" (so Norbert can add it), not silently accepted', chk['ok'] is False and chk['unknown'] and not chk['bad'], chk)
out = subprocess.run([sys.executable, '-I', str(ROOT / 'tools' / 'variety_kitchen.py')], capture_output=True, text=True)
check('python3 -I tools/variety_kitchen.py prints the closed list (for Norbert to approve) and exits 0', out.returncode == 0 and len(out.stdout) > 1500 and 'KITCHEN STAPLES' in out.stdout and 'NOT KITCHEN' in out.stdout and 'só' in out.stdout.lower(), out.stderr[:200] or len(out.stdout))

# =============================================================== 2. the list as the tool reads it
check('the tool reads the same list as the app: 17 main groups, 75 subgroups, 164 units + 45 other', sum(1 for n in vl.nodes.values() if n['level'] == 'main') == 17 and sum(1 for n in vl.nodes.values() if n['level'] == 'sub') == 75
      and sum(1 for k, n in vl.nodes.items() if n['level'] == 'unit' and not n['other']) == 164 and sum(1 for n in vl.nodes.values() if n.get('other')) == 45)
check('a main group alone is not a group of a food; subgroups and units are', not vl.has('veg') and vl.has('veg.leaf') and vl.has('veg.leaf.spinach') and not vl.has('veg.martian') and not vl.has('') and vl.has('bev.water'))

# =============================================================== 3. traps and look-alikes
ciq = json.load(open(ROOT / 'ciqual.json', encoding='utf-8'))
cq = {x['c']: x for x in ciq['foods']}
rows_all = V.build_rows('ciqual', vl)
rows_c = {r[0]: r for r in rows_all}
sv = lambda code: rows_c[code][3]['vt']   # noqa: E731
check('trap (plan): CIQUAL 18011 "Coconut water" is a drink (bev.juice), not coconut flesh', cq['18011']['n'] == 'Coconut water' and sv('18011') == 'bev.juice' and rows_c['18011'][3]['rule'] == 'trap-coconut-water')
check('trap (plan): CIQUAL 20044 "Pumpkin, raw" is the flesh (veg.fruit.pumpkin), a coconut kernel is coconut', cq['20044']['n'] == 'Pumpkin, raw' and sv('20044') == 'veg.fruit.pumpkin' and sv('15006') == 'fru.tropical.coconut')
seeds = [(c, x['n']) for c, x in cq.items() if x.get('g') == 'nuts and seeds' and ('pumpkin' in x['n'].lower() or 'squash' in x['n'].lower())]
check('trap (plan): a pumpkin seed is an oilseed (nut.seeds.pumpkin-seed), never the pumpkin flesh (every CIQUAL food of nuts and seeds with pumpkin or squash in its name)', all(sv(c) in (None, 'nut.seeds.pumpkin-seed') for c, _ in seeds), seeds)
S = lambda src, name, cat, grp=None: V.suggest_one(src, 'x', name, grp or '', vl, cat=cat)['vt']   # noqa: E731
check('trap: pumpkin seeds of USDA are the seed', S('usda', 'Seeds, pumpkin and squash seed kernels, dried', 'Nut and Seed Products') == 'nut.seeds.pumpkin-seed')
check('trap: coconut milk or cream for cooking is made from the coconut flesh, a coconut drink is a plant-based drink',
      sv('18041') == 'fru.tropical.coconut' and S('usda', 'Beverages, almond milk, sweetened, vanilla flavor, ready-to-drink', 'Beverages') == 'bev.plant' and S('usda', 'Beverages, coconut milk, sweetened, fortified with calcium', 'Beverages') == 'bev.plant')
check('trap: olive oil is the olive-oil unit, an olive is the olive (fruit vegetable), corn oil is an oil, not maize',
      S('usda', 'Oil, olive, extra virgin', 'Fats and Oils') == 'fat.oils.olive-oil' and sv('13033') == 'veg.fruit.olive' and sv('13184') == 'veg.fruit.olive' and sv('17270') == 'fat.oils.olive-oil'
      and S('usda', 'Oil, corn', 'Fats and Oils') == 'fat.oils.other' and sv('17190') == 'fat.oils.other')
check('oils: rapeseed, canola, sunflower and coconut oil are their own units; an oil without a unit of the list is "other oil"',
      S('usda', 'Oil, canola', 'Fats and Oils') == 'fat.oils.rapeseed-oil' and S('usda', 'Oil, sunflower', 'Fats and Oils') == 'fat.oils.sunflower-oil' and S('usda', 'Oil, coconut', 'Fats and Oils') == 'fat.oils.coconut-oil' and S('usda', 'Oil, soybean', 'Fats and Oils') == 'fat.oils.other')
check('trap: black and white pepper are spices, a bell pepper is a pepper (fruit vegetable)', S('usda', 'Spices, pepper, black', 'Spices and Herbs') == 'spi.dry-spices' and S('usda', 'Peppers, bell, red, raw', 'Vegetables and Vegetable Products') == 'veg.fruit.pepper')
check('look-alike: a cheese is not a milk (CIQUAL cheese from cow\'s milk gets no suggestion or a cheese unit, never dai.milk)', not (sv('12001') or '').startswith('dai.milk'), sv('12001'))
check('look-alike: root beer is a soft drink, not beer; bottled water is water', S('usda', 'Beverages, carbonated, root beer', 'Beverages') == 'bev.sweetened' and S('usda', 'Beverages, water, bottled, non-carbonated, EVIAN', 'Beverages') == 'bev.water' and S('usda', 'Alcoholic beverage, beer, regular, BUDWEISER', 'Beverages') == 'bev.alcohol')
check('look-alike: a frozen yogurt with chocolate is a dairy dessert, chocolate syrup is not chocolate, a butter replacement is not butter, a seed of a spice is a spice',
      S('usda', 'Frozen yogurts, chocolate', 'Sweets') == 'swe.dairy-dessert' and S('usda', 'Syrups, chocolate, fudge-type', 'Sweets') != 'swe.chocolate' and S('usda', 'Butter replacement, without fat, powder', 'Fats and Oils') is None
      and S('usda', 'Spices, dill seed', 'Spices and Herbs') == 'spi.dry-spices' and S('usda', 'Spices, poppy seed', 'Spices and Herbs') == 'nut.seeds.poppy')
check('look-alike: "Corn with red and green peppers" is a mixed vegetable (no suggestion), not the pepper; "Caribbean cabbage" is no cabbage (no suggestion)',
      S('usda', 'Corn with red and green peppers, canned, solids and liquids', 'Vegetables and Vegetable Products') is None and sv('20803') is None)
check('§3.3: pasta, bread and flour are the culinary species (durum / wheat); tofu is soybean; peanut butter is peanut; tahini is sesame',
      S('usda', 'Pasta, fresh-refrigerated, plain, cooked', 'Cereal Grains and Pasta') == 'gra.wheat.durum' and S('usda', 'Bread, naan, plain, commercially prepared, refrigerated', 'Baked Products') == 'gra.wheat.wheat'
      and sv('38105') == 'sna.corn' and V.suggest_dmbio('1', 'Natúr tofu, 200 g', None, vl)['vt'] == 'leg.soy.soybean' and V.suggest_dmbio('2', 'Bio földimogyorókrém, 250 g', None, vl)['vt'] == 'nut.nuts.peanut'
      and V.suggest_dmbio('3', 'Bio bulgur, 500 g', None, vl)['vt'] == 'gra.wheat.durum' and V.suggest_dmbio('4', 'Bio kuszkusz, 500 g', None, vl)['vt'] == 'gra.wheat.durum')
check('§3.3: offal is an attribute (flag) on a meat unit, never a unit of its own',
      V.suggest_one('usda', 'x', 'Lamb, variety meats and by-products, kidneys, raw', '', vl, cat='Lamb, Veal, and Game Products')['flags'] == ['offal'] and V.suggest_one('usda', 'x', 'Beef, round, raw', '', vl, cat='Beef Products')['flags'] == [])
check('§3.3: composite foods the app does not decompose are dishes (dis.*), without a unit', S('usda', 'PIZZA HUT 14" Pepperoni Pizza, Pan Crust', 'Fast Foods') == 'dis.bread' and S('usda', 'Soup, tomato rice, canned, prepared with equal volume water', 'Soups, Sauces, and Gravies') == 'dis.soup')
# every trap fires only on the thing itself: a food that merely NAMES it is something else (found by listing every food that hits a trap in the three tables)
LOOK = [
    ('sardine canned in olive oil is a fish, not the oil', 'ciqual', '26040', 'European pilchard or sardine, in olive oil, canned, drained', ('fish', 'fish'), lambda v: v != 'fat.oils.olive-oil'),
    ('olive oil dressing is a sauce, not the oil', 'ciqual', '11108', 'Salad dressing, olive oil and vinegar (50-75% fat), prepacked', ('miscellaneous', 'sauces'), lambda v: v != 'fat.oils.olive-oil'),
    ('a soup with olive oil in its name is not the oil', 'ciqual', '25917', 'Soup, pistou (basil, garlic and olive oil), dehydrated and reconstituted', ('soups and broths', 'soups'), lambda v: v != 'fat.oils.olive-oil'),
    ('pie pumpkin "seeded" is the flesh, not the seed', 'usda', '2727578', 'Squash, pie pumpkin, peeled, seeded, raw', 'Vegetables and Vegetable Products', lambda v: v != 'nut.seeds.pumpkin-seed'),
    ('a sunfish called "pumpkin seed" is a fish', 'usda', '172003', 'Fish, sunfish, pumpkin seed, cooked, dry heat', 'Finfish and Shellfish Products', lambda v: v != 'nut.seeds.pumpkin-seed'),
    ('a coconut cream pudding is a dessert, not coconut', 'usda', '168828', 'Puddings, coconut cream, dry mix, regular', 'Sweets', lambda v: v != 'fru.tropical.coconut'),
    ('a coconut cream pie is a dessert, not coconut', 'usda', '175017', 'Pie, coconut cream, prepared from mix, no-bake type', 'Baked Products', lambda v: v != 'fru.tropical.coconut'),
    ('a peanut sauce made from coconut and water is a sauce, not coconut water', 'usda', '171575', 'Sauce, peanut, made from coconut, water, sugar, peanuts', 'Soups, Sauces, and Gravies', lambda v: v != 'bev.juice'),
    ('a peppercorn dressing is a dressing, not the spice', 'usda', '168093', 'Salad dressing, peppercorn dressing, commercial, regular', 'Fats and Oils', lambda v: v != 'spi.dry-spices'),
    ('a peppercorn-flavoured pork tenderloin is meat, not the spice', 'usda', '168317', 'HORMEL ALWAYS TENDER, Pork Tenderloin, Peppercorn-Flavored', 'Pork Products', lambda v: v != 'spi.dry-spices'),
    ('mayonnaise with olive oil is a sauce, not the oil', 'usda', '171443', 'Mayonnaise, reduced fat, with olive oil', 'Fats and Oils', lambda v: v != 'fat.oils.olive-oil'),
    ('canned anchovies in olive oil are a fish, not the oil', 'usda', '2747652', 'Anchovies, canned in olive oil, with salt, drained', 'Finfish and Shellfish Products', lambda v: v != 'fat.oils.olive-oil'),
]
badlook = []
for label, src, code, name, cat, ok in LOOK:
    v = V.suggest_one(src, code, name, '', vl, cat=cat)['vt']
    if not ok(v):
        badlook.append((label, v))
check('traps fire only on the thing itself, not on a food that only names it (%d look-alikes from the real tables)' % len(LOOK), badlook == [], badlook)
check('the same for dmBio: olive oil is the oil, bread with olive oil and a snack with pumpkin seeds are not; coconut water and pumpkin seeds still are',
      V.suggest_dmbio('1', 'Bio olívaolaj, extra szűz, 750 ml', None, vl)['vt'] == 'fat.oils.olive-oil' and V.suggest_dmbio('2', 'Bio ropogós kenyér magvakkal és extraszűz olívaolajjal, 200 g', None, vl)['vt'] != 'fat.oils.olive-oil'
      and V.suggest_dmbio('3', 'Bio sajtos ropogós snack tökmaggal, 200 g', None, vl)['vt'] != 'nut.seeds.pumpkin-seed' and V.suggest_dmbio('4', 'Bio tökmag, 225 g', None, vl)['vt'] == 'nut.seeds.pumpkin-seed'
      and V.suggest_dmbio('5', 'Bio natúr kókuszvíz, 1 l', None, vl)['vt'] == 'bev.juice')
# a trap must not catch more than the foods it is meant for: list what every trap hits in the three tables (the audit that found the faults above)
import re as _re
hits = {}
for fn in ('ciqual.json', 'usda.json', 'dmbio.json'):
    for x in json.load(open(ROOT / fn, encoding='utf-8'))['foods']:
        f = K.fold(x['n'])
        for rx, vt, conf, rid, why in V.TRAPS:
            if _re.search(rx, f):
                hits.setdefault(rid, []).append((fn[:2], x['c'], x['n']))
                break
EXPECT = {'trap-olive-oil': {'17270', '1459848'}, 'trap-black-pepper': {'11015', '11019', '170931', '170933'},
          'trap-pumpkin-seed': {'2515380', '168601', '169415', '170188', '170556', '170557', '1468881', '3060022'},
          'trap-coconut-water': {'18011', '170174', '174831', '1691431', '1454206'}, 'trap-peanut-oil': {'17040'}, 'trap-corn-oil': {'17190'}, 'trap-caribbean-cabbage': {'20803'},
          'trap-coconut-milk': {'18041', '169409', '170171', '170172', '170173', '170580'}}
off = {rid: sorted({h[1] for h in hits.get(rid, [])} ^ codes) for rid, codes in EXPECT.items() if {h[1] for h in hits.get(rid, [])} != codes}
check('the traps for oils, pepper, pumpkin seed, coconut and the two single foods hit exactly the foods meant (all three tables, 11,000+ names)', off == {}, off)
check('the drink traps (soy, almond, oat, rice, coconut drink) hit only drinks: every hit is a milk or a drink or a beverage',
      all(_re.search(r'milk|drink|beverage|ital|soymilk', K.fold(h[2])) for rid in ('trap-soy-drink', 'trap-plant-drink', 'trap-coconut-drink') for h in hits.get(rid, [])), [h for rid in ('trap-soy-drink', 'trap-plant-drink', 'trap-coconut-drink') for h in hits.get(rid, []) if not _re.search(r'milk|drink|beverage|ital|soymilk', K.fold(h[2]))][:3])
# faults found when the suggestions of whole categories were read through (each one is a wrong suggestion that a random sample of 100 foods did not show)
U = lambda name, cat: V.suggest_one('usda', 'x', name, '', vl, cat=cat)['vt']   # noqa: E731
C2 = lambda name, g: V.suggest_one('ciqual', 'x', name, '', vl, cat=g)['vt']   # noqa: E731
AUD = [
    ('non-alcoholic wine is no alcoholic drink', U('Beverages, Wine, non-alcoholic', 'Beverages') is None),
    ('rice pudding is a dessert, not a rice dish', U('Restaurant, Latino, arroz con leche (rice pudding)', 'Restaurant Foods') is None and U('OLIVE GARDEN, spaghetti with meat sauce', 'Restaurant Foods') == 'dis.pasta-grain'),
    ('"Oil, olive, salad or cooking" is olive oil ("salad" is no product word here)', U('Oil, olive, salad or cooking', 'Fats and Oils') == 'fat.oils.olive-oil' and U('Oil, olive, extra light', 'Fats and Oils') == 'fat.oils.olive-oil'),
    ('a blend of oils is no single unit (corn, peanut and olive; corn and canola)', U('Oil, corn, peanut, and olive', 'Fats and Oils') is None and U('Oil, corn and canola', 'Fats and Oils') is None),
    ('canola oil is rapeseed oil, also with qualifiers ("industrial", "for salads, woks and light frying")', U('Oil, canola', 'Fats and Oils') == 'fat.oils.rapeseed-oil' and U('Oil, industrial, canola for salads, woks and light frying', 'Fats and Oils') == 'fat.oils.rapeseed-oil'),
    ('sunflower and coconut oil are found also when "industrial" or "mid-oleic" comes first', U('Oil, industrial, mid-oleic, sunflower', 'Fats and Oils') == 'fat.oils.sunflower-oil' and U('Oil, industrial, coconut, principal uses candy coatings', 'Fats and Oils') == 'fat.oils.coconut-oil'),
    ('an oil of the list keeps its unit, any other oil is "other oil", a seal or whale oil is an animal fat', U('Oil, sesame, salad or cooking', 'Fats and Oils') == 'fat.oils.other' and U('Oil, walrus (Alaska Native)', 'Fats and Oils') == 'fat.animal.other'),
    ('a coffee drink made with milk is a milk-based drink, not a sweetened drink', U('Beverages, coffee, ready to drink, vanilla, light, milk based', 'Beverages') == 'bev.milk-based'),
    ('rennin (a milk dessert mix) is a dairy dessert, not chocolate', U('Rennin, chocolate, dry mix, prepared with whole milk', 'Sweets') == 'swe.dairy-dessert'),
    ('sweet potato chips, snack bars and soy crisps are not "potato", "seed" or "grain" snacks: no suggestion', U('Snacks, sweet potato chips, unsalted', 'Snacks') is None and U('Snacks, granola bar, GENERAL MILLS, NATURE VALLEY, CHEWY TRAIL MIX', 'Snacks') is None and U('Snacks, soy chips or crisps, salted', 'Snacks') is None and U('Snacks, potato chips, plain', 'Snacks') == 'sna.potato'),
    ('CIQUAL "Coconut fat or oil" is coconut oil, not "other oil"', C2('Coconut fat or oil', ('fats and oils', 'vegetable oils')) == 'fat.oils.coconut-oil' and C2('Wheat germ oil', ('fats and oils', 'vegetable oils')) == 'fat.oils.other'),
    ('CIQUAL "Poppy, seed" is the poppy seed (nut.seeds.poppy), other spice seeds are spices', C2('Poppy, seed', ('miscellaneous', 'spices')) == 'nut.seeds.poppy' and C2('Coriander, seed', ('miscellaneous', 'spices')) == 'spi.dry-spices'),
    ('an artificial sweetener is no sugar; a cocoa or malted powder for a drink is no sweetened drink', C2('Aspartame, in powder', ('sugar and confectionery', 'sugars and honey')) is None and C2('Syrup, maple', ('sugar and confectionery', 'sugars and honey')) == 'swe.sugar-honey'
     and C2('Malted cocoa or chocolate powder for beverage, with sugar', ('beverages', 'non-alcoholic beverages')) is None),
    ('dmBio: a bread spread with curry or fruit and energy balls get no suggestion, a vegetable spread is a vegetable dish', V.suggest_dmbio('1', 'Bio krémes kenyérfeltét mangó-papaya-curry, 180 g', None, vl)['vt'] is None and V.suggest_dmbio('2', 'Bio energiagolyók Spekulatiuskeksz-fűszerekkel, 60 g', None, vl)['vt'] is None
     and V.suggest_dmbio('3', 'Bio krémes kenyérfeltét padlizsánnal, 180 g', None, vl)['vt'] == 'dis.legume-veg'),
]
for label, ok in AUD:
    check('audit fix: ' + label, bool(ok))
# popcorn and hummus need the ingredient list: without one there is no suggestion, in every source
check('popcorn and hummus without an ingredient list: no suggestion (CIQUAL pop-corn rows, USDA popcorn, dmBio without the list)',
      all(rows_c[c][3]['vt'] is None for c in rows_c if 'pop-corn' in cq[c]['n'].lower() or 'popcorn' in cq[c]['n'].lower())
      and S('usda', 'Snacks, popcorn, air-popped', 'Snacks') is None and V.suggest_dmbio('1', 'Bio natúr hummusz, 180 g', None, vl)['vt'] is None and V.suggest_dmbio('2', 'Bio pattogatott kukorica fahéjjal, 13 g', None, vl)['vt'] is None)
lab_hum = 'Pontos termékmegnevezés:  Bio natúr hummusz  csicseriborsó, tahini (szezámmag), olívaolaj, citromlé, tengeri só  *Bio'
lab_hum2 = 'Pontos termékmegnevezés:  Bio natúr hummusz  csicseriborsó (52%), tahini, olívaolaj, citromlé, tengeri só, sűrítőanyag: guarmagliszt  *Bio'
lab_pop = 'Pontos termékmegnevezés:  Bio pattogatott kukorica  pattogatott kukorica, napraforgóolaj, tengeri só  *Bio'
check('with the ingredient list of dm: kitchen hummus = chickpea, hummus with a thickener = mixed dish; kitchen popcorn = maize',
      V.suggest_dmbio('1', 'Bio natúr hummusz, 180 g', lab_hum, vl)['vt'] == 'leg.chickpea-pea.chickpea' and V.suggest_dmbio('2', 'Bio natúr hummusz, 180 g', lab_hum2, vl)['vt'] == 'dis.legume-veg'
      and V.suggest_dmbio('3', 'Bio pattogatott kukorica, 90 g', lab_pop, vl)['vt'] == 'gra.corn.corn', [V.suggest_dmbio('1', 'Bio natúr hummusz, 180 g', lab_hum, vl), V.suggest_dmbio('3', 'Bio pattogatott kukorica, 90 g', lab_pop, vl)])
sugar_pop = V.suggest_dmbio('4', 'Bio pattogatott kukorica fahéjjal, 13 g', 'Pontos termékmegnevezés:  Bio pattogatott kukorica fahéjjal  pattogatott kukorica, cukor, napraforgóolaj, fahéj  *Bio', vl)
check('caramel / sugar popcorn: kept at LOW confidence with a note (the open question of the plan is Norbert\'s to decide), so it is never taken as an approved row by mistake', sugar_pop['vt'] == 'gra.corn.corn' and sugar_pop['confidence'] == 'low' and 'open question' in sugar_pop['note'], sugar_pop)
check('baby food, mixes, flavourings and in-between products get no suggestion (dmBio)', all(V.suggest_dmbio('x', n, None, vl)['vt'] is None for n in ['Bio zöldségleves ételízesítő kocka, 66 g', 'Palacsintapor fűszeres sütőtök ízesítéssel, 135 g', 'Bio extrudált kenyérszeletek rozzsal és tönköllyel, 250 g', 'Bio puffasztott sós csicseriborsó-szelet, 100 g']))
check('dmBio: dried fruit slices are the fruit, salty puffed corn slices are a maize snack, chocolate bars are chocolate, jam is jam',
      V.suggest_dmbio('1', 'Bio aszalt mangószeletek, 100 g', None, vl)['vt'] == 'fru.tropical.mango' and V.suggest_dmbio('2', 'Bio puffasztott sós kukoricaszelet, 110 g', None, vl)['vt'] == 'sna.corn'
      and V.suggest_dmbio('3', 'Bio tejcsokoládé-szelet, kekszes, 37,5 g', None, vl)['vt'] == 'swe.chocolate' and V.suggest_dmbio('4', 'Bio extradzsem 55% málnával, 340 g', None, vl)['vt'] == 'swe.fruit-sweets'
      and V.suggest_dmbio('5', 'Bio bourbon vaníliás cukor, 32 g', None, vl)['vt'] == 'swe.sugar-honey' and V.suggest_dmbio('6', 'Bio zöldségleves ételízesítő por, utántöltő, 290 g', None, vl)['vt'] is None)

# =============================================================== 4. the hand-classified yardstick
fx = json.load(open(HERE / 'fixture_variety_hand.json.txt', encoding='utf-8'))


def run_item(it):
    if it['source'] == 'ciqual':
        G, g = it['group']
        return V.suggest_one('ciqual', it['code'], it['name'], ' › '.join(x for x in (G, g) if x), vl, cat=(G, g))
    if it['source'] == 'usda':
        return V.suggest_one('usda', it['code'], it['name'], it['group'] or '', vl, cat=it['group'])
    return V.suggest_dmbio(it['code'], it['name'], it.get('ingredients'), vl)


for sname, smp in fx['samples'].items():
    items = smp['items']
    res = [(it, run_item(it)) for it in items]
    agree = [it for it, r in res if r['vt'] == it['hand']]
    wrong = [(it['source'], it['code'], it['name'][:40], it['hand'], r['vt']) for it, r in res if r['vt'] is not None and r['vt'] != it['hand']]
    silent = [(it['source'], it['code'], it['name'][:40], it['hand']) for it, r in res if r['vt'] is None]
    check(f'yardstick "{sname}" (seed {smp["seed"]}): 50 foods, every hand label is a subgroup or unit of the list', len(items) == 50 and all(vl.has(it['hand']) for it in items), [it['hand'] for it in items if not vl.has(it['hand'])])
    check(f'yardstick "{sname}": at least 95% of the 50 foods get exactly the hand-classified group ({len(agree)} of 50)', len(agree) >= 48, [wrong, silent])
    check(f'yardstick "{sname}": a WRONG suggestion is the thing to avoid: none ({len(wrong)} wrong, {len(silent)} without a suggestion)', wrong == [], wrong)
    for src in ('ciqual', 'usda', 'dmbio'):
        part = [(it, r) for it, r in res if it['source'] == src]
        ok = sum(1 for it, r in part if r['vt'] == it['hand'])
        check(f'yardstick "{sname}", {src}: {ok} of {len(part)} agree (at least 90%)', len(part) > 0 and ok / len(part) >= 0.9, [(it['name'][:30], it['hand'], r['vt']) for it, r in part if r['vt'] != it['hand']])
check('the fixture says whose classification it is (not an approval by Norbert) and lists the debatable labels', 'NOT an approval by Norbert' in fx['about'] and len(fx['debatable']) >= 2)
check('the two samples do not share a food', not ({(i['source'], i['code']) for i in fx['samples']['dev']['items']} & {(i['source'], i['code']) for i in fx['samples']['heldout']['items']}))

# =============================================================== 5. the real CIQUAL table end to end (CIQUAL has its groups in the repository)
sugg = [r[3] for r in rows_all]
by = {k: sum(1 for s in sugg if s['vt'] and s['confidence'] == k) for k in ('high', 'medium', 'low')}
check('CIQUAL: every one of the 3186 foods of the table has a row; more than 1700 get a suggestion (high / medium / low), the rest none', len(rows_all) == 3186 and sum(by.values()) > 1700 and all(v > 0 for v in by.values()), [len(rows_all), by])
dup = [r for r in rows_all if r[0] == '9621']
check('CIQUAL: the code 9621 (Wheat bran) is in ciqual.json twice, in two groups: both rows get the same suggestion, so a map row for the code is unambiguous', len(rows_all) - len(rows_c) == 1 and len(dup) == 2 and dup[0][3]['vt'] == dup[1][3]['vt'], [(r[2], r[3]['vt']) for r in dup])
check('CIQUAL: every suggested group exists in the list (no orphan id), every flag fits its group, every suggestion has a rule and a confidence',
      all(vl.has(s['vt']) and s['rule'] and s['confidence'] in ('high', 'medium', 'low') and all(f in vl.flags and vl.mainOf(s['vt']) in vl.flags[f]['applies'] for f in s['flags']) for s in sugg if s['vt']), [s for s in sugg if s['vt'] and not vl.has(s['vt'])][:3])
check('CIQUAL: no row has a confidence without a group (and no group without one)', all(bool(s['vt']) == bool(s['confidence']) for s in sugg if s['rule'] not in ('trap-caribbean-cabbage',)), [s for s in sugg if bool(s['vt']) != bool(s['confidence'])][:3])
alc = [c for c, r in rows_c.items() if cq[c].get('g') == 'alcoholic beverages' and r[3]['vt'] not in (None, 'bev.alcohol')]
check('CIQUAL: an alcoholic beverage is never anything but bev.alcohol', alc == [], alc[:3])
usda_rows = V.build_rows('usda', vl)
dm_rows = V.build_rows('dmbio', vl)
check('USDA without the FDC category file: 8229 rows; only the name-based traps (soy / plant drinks, pumpkin seed, coconut ...) make a suggestion, every other row says that the category is missing',
      len(usda_rows) == 8229 and 0 < sum(1 for r in usda_rows if r[3]['vt']) < 100 and all(r[3]['rule'].startswith('trap-') for r in usda_rows if r[3]['vt'])
      and all('no USDA category' in r[3]['note'] for r in usda_rows if not r[3]['vt'] and not r[3]['note'].startswith(('popcorn', 'hummus'))), sum(1 for r in usda_rows if r[3]['vt']))
check('dmBio without the ingredient lists: 527 rows; popcorn and hummus have no suggestion; every suggested group exists in the list',
      len(dm_rows) == 527 and all(r[3]['vt'] is None for r in dm_rows if 'hummus' in r[1].lower() or 'popcorn' in r[1].lower() or 'pattogatott' in r[1].lower()) and all(vl.has(r[3]['vt']) for r in dm_rows if r[3]['vt']))

# =============================================================== 6. apply: only approved rows go into a map
tmp = pathlib.Path(tempfile.mkdtemp(prefix='vsugg_'))
try:
    rev = tmp / 'reviewed.csv'
    with open(rev, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(V.COLUMNS)
        w.writerow(['15038', 'Sesame seed', '', 'nut.seeds.sesame', '', 'unit-name', 'high', '', 'yes', ''])             # approved as suggested
        w.writerow(['20035', 'Onion, cooked', '', 'veg.allium.onion', '', 'unit-name', 'high', '', '', ''])               # NOT approved (empty)
        w.writerow(['20036', 'Onion, other', '', 'veg.allium.onion', '', 'unit-name', 'high', '', 'no', ''])              # not approved (no)
        w.writerow(['40118', 'Liver, turkey, cooked', '', 'mea.poultry.turkey', 'offal', 'unit-name', 'high', '', 'igen', ''])   # approved with a flag
        w.writerow(['20044', 'Pumpkin, raw', '', 'veg.fruit.pumpkin', '', 'unit-name', 'high', '', 'x', 'veg.fruit.other'])      # approved, Norbert typed another group: it wins
        w.writerow(['111', 'Orphan', '', 'veg.leaf.martian', '', 'rule', 'low', '', 'yes', ''])                           # approved but not in the list: refused
        w.writerow(['112', 'Main group only', '', 'veg', '', 'rule', 'low', '', 'yes', ''])                               # a main group alone: refused
        w.writerow(['113', 'Offal under vegetables', '', 'veg.leaf.spinach', 'offal', 'rule', 'low', '', 'yes', ''])      # flag on the wrong group: refused
        w.writerow(['114', 'Unknown flag', '', 'mea.red.beef', 'bogus', 'rule', 'low', '', 'yes', ''])                    # unknown flag: refused
        w.writerow(['', 'No code', '', 'veg.leaf.spinach', '', 'rule', 'low', '', 'yes', ''])                             # no code: refused
        w.writerow(['115', 'No group', '', '', '', 'rule', 'low', '', 'yes', ''])                                         # approved but there is no group: refused
    mp = tmp / 'vt_map_ciqual.json'
    wr, sk = V.apply_reviewed('ciqual', str(rev), vl, map_path=str(mp), updated='2026-11-12')
    got = json.loads(mp.read_text(encoding='utf-8'))
    check('apply: only approved rows are written (yes, igen, x ...; empty and "no" are not), a typed final group wins over the suggested one, a flag is kept as {vt, vf}',
          got['map'] == {'15038': 'nut.seeds.sesame', '20044': 'veg.fruit.other', '40118': {'vt': 'mea.poultry.turkey', 'vf': ['offal']}}, [wr, got['map']])
    check('apply: 3 approved rows written, the 6 refused rows say why (unknown group, main group alone, flag on the wrong group, unknown flag, no code, no group)',
          wr == 3 and len(sk) == 6 and any('not a subgroup or unit' in why for _, why in sk) and any('flag' in why for _, why in sk) and sum(1 for _, why in sk if why == 'no group') == 2, [wr, sk])
    check('apply: the file has the shape of a map (app, version 1, source, updated) and the rows are sorted', got['app'] == 'tapnaplo-variety-map' and got['version'] == 1 and got['source'] == 'ciqual' and got['updated'] == '2026-11-12' and list(got['map']) == sorted(got['map'], key=lambda c: (len(c), c)), got)
    check('apply: an unapproved or refused row never reaches the file (20035, 20036, 111, 112, 113, 114)', not ({'20035', '20036', '111', '112', '113', '114', '115', ''} & set(got['map'])))
    # a second review adds rows and keeps the first ones, a later approval of the same code replaces it
    rev2 = tmp / 'reviewed2.csv'
    with open(rev2, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(V.COLUMNS)
        w.writerow(['20035', 'Onion, cooked', '', 'veg.allium.onion', '', 'unit-name', 'high', '', 'yes', ''])
        w.writerow(['15038', 'Sesame seed', '', 'nut.seeds.sesame', '', 'unit-name', 'high', '', 'yes', 'nut.seeds.other'])
    wr2, _ = V.apply_reviewed('ciqual', str(rev2), vl, map_path=str(mp))
    got2 = json.loads(mp.read_text(encoding='utf-8'))
    check('apply: a second review keeps the rows of the first, adds the new one and a repeated code takes the new group', wr2 == 2 and set(got2['map']) == {'15038', '20044', '40118', '20035'} and got2['map']['15038'] == 'nut.seeds.other' and got2['map']['40118'] == {'vt': 'mea.poultry.turkey', 'vf': ['offal']}, got2['map'])
    empty = tmp / 'empty.csv'
    empty.write_text(','.join(V.COLUMNS) + '\n', encoding='utf-8-sig')
    mp2 = tmp / 'vt_map_usda.json'
    wr3, sk3 = V.apply_reviewed('usda', str(empty), vl, map_path=str(mp2))
    g3 = json.loads(mp2.read_text(encoding='utf-8'))
    check('apply: a review with no approved row gives a valid EMPTY map of that table (nothing is filled in automatically)', wr3 == 0 and sk3 == [] and g3['map'] == {} and g3['source'] == 'usda' and g3['app'] == 'tapnaplo-variety-map', g3)

    # ---------------------------------------------------------- 7. top: the foods logged most often that have no group
    root = tmp / 'root'
    root.mkdir()
    for f in ('ciqual.json', 'usda.json', 'dmbio.json', 'variety_units.json'):
        os.symlink(ROOT / f, root / f)
    (root / 'vt_map_ciqual.json').write_text(json.dumps({'app': 'tapnaplo-variety-map', 'version': 1, 'source': 'ciqual', 'updated': '', 'map': {'15038': 'nut.seeds.sesame'}}), encoding='utf-8')
    (root / 'vt_map_usda.json').write_text(json.dumps({'app': 'tapnaplo-variety-map', 'version': 1, 'source': 'usda', 'updated': '', 'map': {}}), encoding='utf-8')
    log = [{'f': 'c:15038'}] * 9 + [{'f': 'c:20044'}] * 7 + [{'f': 'c:18011'}] * 3 + [{'f': 'dm:1490004'}] * 5 + [{'f': 'usda:170929'}] * 2 + [{'f': 'u:own1'}] * 4 + [{'f': 'u:own2'}] * 6 + [{'f': 'c:99999999'}]
    bk = {'app': 'tapnaplo', 'log': log, 'foods': {'u:own1': {'id': 'u:own1', 'name': 'Own without group'}, 'u:own2': {'id': 'u:own2', 'name': 'Own with group', 'vt': 'veg.leaf.spinach'}}}
    bkp = tmp / 'backup.json'
    bkp.write_text(json.dumps(bk), encoding='utf-8')
    top = V.top_unclassified(str(bkp), vl, str(root), 50)
    ids = [t[0] for t in top['top']]
    check('top: totals and classified entries are counted (CIQUAL sesame in the map = 9, own food with a group = 6)', top['total_entries'] == 37 and top['classified_entries'] == 15 and top['distinct_foods'] == 8 and top['unclassified_foods'] == 6, {k: v for k, v in top.items() if k != 'top'})
    check('top: the unclassified foods come most-logged first; mapped and own-classified foods are not in it', ids == ['c:20044', 'dm:1490004', 'u:own1', 'c:18011', 'usda:170929', 'c:99999999'] and [t[1] for t in top['top']] == [7, 5, 4, 3, 2, 1], [(t[0], t[1]) for t in top['top']])
    t0 = {t[0]: t for t in top['top']}
    check('top: each row has the name of the food and the suggestion (or the reason for none): pumpkin = veg.fruit.pumpkin, coconut water = bev.juice, a food that is not in the table says so, an own food says where to set it',
          t0['c:20044'][2] == 'Pumpkin, raw' and t0['c:20044'][3]['vt'] == 'veg.fruit.pumpkin' and t0['c:18011'][3]['vt'] == 'bev.juice' and t0['c:99999999'][2] == '(not in the table)' and t0['u:own1'][2] == 'Own without group' and 'own or saved food' in t0['u:own1'][3]['note'], t0['u:own1'])
    check('top: the limit cuts the list', len(V.top_unclassified(str(bkp), vl, str(root), 2)['top']) == 2)
    cp = subprocess.run([sys.executable, '-I', str(ROOT / 'tools' / 'variety_suggest.py'), 'top', '--backup', str(bkp), '--root', str(root), '--limit', '3'], capture_output=True, text=True)
    check('command line: top prints the share of classified entries and the list', cp.returncode == 0 and '15 of 37 entries are classified' in cp.stdout and 'c:20044' in cp.stdout and len(cp.stdout.strip().splitlines()) == 4, cp.stdout + cp.stderr)
    # the command line for suggest and apply
    outd = tmp / 'out'
    cp = subprocess.run([sys.executable, '-I', str(ROOT / 'tools' / 'variety_suggest.py'), 'suggest', '--out', str(outd)], capture_output=True, text=True)
    files = sorted(p.name for p in outd.glob('*.csv')) if outd.exists() else []
    check('command line: suggest writes one CSV per table', cp.returncode == 0 and files == ['variety_suggestions_ciqual.csv', 'variety_suggestions_dmbio.csv', 'variety_suggestions_usda.csv'], [cp.stderr[-300:], files])
    rc = list(csv.DictReader(open(outd / 'variety_suggestions_ciqual.csv', encoding='utf-8-sig')))
    check('suggest: the CSV has the columns of the review (code, name, source_group, suggested_vt, flags, rule, confidence, note, approved, final_vt) and the last two are EMPTY in every row (Norbert fills them)',
          list(rc[0].keys()) == V.COLUMNS and len(rc) == 3186 and all(r['approved'] == '' and r['final_vt'] == '' for r in rc), list(rc[0].keys()))
    # round trip: approve in the CSV, apply with the command line, the app-side rules accept the file
    for r in rc:
        pass
    rows = list(csv.reader(open(outd / 'variety_suggestions_ciqual.csv', encoding='utf-8-sig')))
    hdr = rows[0]
    ia = hdr.index('approved')
    for r in rows[1:]:
        if r[0] in ('15038', '20044'):
            r[ia] = 'yes'
    with open(tmp / 'review_cli.csv', 'w', encoding='utf-8-sig', newline='') as fh:
        csv.writer(fh).writerows(rows)
    mp3 = tmp / 'cli_map.json'
    cp = subprocess.run([sys.executable, '-I', str(ROOT / 'tools' / 'variety_suggest.py'), 'apply', '--source', 'ciqual', '--reviewed', str(tmp / 'review_cli.csv'), '--map', str(mp3)], capture_output=True, text=True)
    g = json.loads(mp3.read_text(encoding='utf-8')) if mp3.exists() else {}
    check('command line: apply writes only the two approved rows into the map given with --map (not into the repository)', cp.returncode == 0 and g.get('map') == {'15038': 'nut.seeds.sesame', '20044': 'veg.fruit.pumpkin'} and sha(ROOT / 'vt_map_ciqual.json') == before['vt_map_ciqual.json'], [cp.stdout, cp.stderr[-200:], g])
    (tmp / 'for_the_app').mkdir()
    shutil.copy(mp3, HERE / 'tmp_cli_map_ciqual.json')   # the browser test reads this file name if it exists; removed below
    (HERE / 'tmp_cli_map_ciqual.json').unlink()
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# =============================================================== 8. the shipped maps and the tables
after = {f: sha(ROOT / f) for f in GUARDED}
check('the tools changed nothing in the nutrient tables (ciqual.json, usda.json, dmbio.json), the variety list or the shipped maps', after == before, [f for f in GUARDED if after[f] != before[f]])
for src, fn in V.MAP_FILES.items():
    raw = json.load(open(ROOT / fn, encoding='utf-8'))
    table = {'ciqual': 'ciqual.json', 'usda': 'usda.json', 'dmbio': 'dmbio.json'}[src]
    codes = {x['c'] for x in json.load(open(ROOT / table, encoding='utf-8'))['foods']}
    m = raw['map']
    bad = [c for c, v in m.items() if c not in codes or not vl.has(v if isinstance(v, str) else v['vt'])]
    check(f'{fn}: a map of its own table, every row is a food of that table with a subgroup or unit of the list (no orphan id), nothing that was not approved ({len(m)} rows)', raw['app'] == 'tapnaplo-variety-map' and raw['source'] == src and raw['version'] == 1 and bad == [], bad[:3])
nutrients = json.load(open(ROOT / 'ciqual.json', encoding='utf-8'))['nutrients']
check('the 65 nutrient keys are untouched (the Variety work does not change the nutrient tables)', len(nutrients) == 65 and nutrients[0]['key'] == 'kcal' and nutrients[-1]['key'] == 'caffeine')

print('\n%d problem(s)' % len(problems))
for x in problems:
    print(' -', x)
sys.exit(1 if problems else 0)
