"""Variety plan, step L3: SUGGESTIONS for the map files (a suggestion is not a decision).

What it does
  suggest : reads the built-in food tables of the app (ciqual.json, usda.json, dmbio.json) and writes one suggestion file per table
            (CSV: code, name, source group, suggested group `vt`, flags, rule, confidence, note, approved). Nothing is written to a map.
  apply   : reads a suggestion file that a person has reviewed (column `approved` = yes) and writes ONLY those rows into the map file
            (vt_map_ciqual.json / vt_map_usda.json / vt_map_dmbio.json). Every `vt` is checked against variety_units.json; rows that
            are not approved, or whose group is not in the list, are never written. Existing map rows stay (a newer approval of the same code replaces its row).
  top     : reads a Nutrilog backup (Data tab > Export JSON) and lists the foods that are logged most often and are not classified yet
            (not in a map, no own group), with the suggestion if there is one: the review list for the next step.

Where the suggestions come from (the plan asks for: group of the table + keyword rules + aliases)
  - the group of the source table: CIQUAL group and subgroup (ciqual.json: G, g), USDA food category (only in the raw FDC CSV: --usda-csv),
    dmBio has no category (the product name and, when --dmbio-csv is given, the original ingredient list);
  - the names and aliases of the units in variety_units.json, in Hungarian and English; the plural of an English name is understood;
  - group rules for the groups that stop at the subgroup (drinks, sweets, snacks, dishes, spices ...), written below as tables.
  A suggestion is only made when ONE unit (or one subgroup) fits and the source group allows it; everything unclear gets no suggestion
  (the column stays empty), never a guess. `confidence`: high (the head of the name is the unit, the source group agrees and nothing else is in the name
  but states like raw/cooked), medium (the unit is in the name and the group agrees, or a group rule), low (a rough group rule).
  Packaged foods with an ingredient list: the kitchen-ingredient test of tools/variety_kitchen.py decides popcorn and hummus.

Run:  python3 -I tools/variety_suggest.py suggest --usda-csv <foundation_dir> <sr_legacy_dir> --dmbio-csv <products_dmbio_nutrilog_v3.csv> --out <folder>
      python3 -I tools/variety_suggest.py apply --source ciqual --reviewed <reviewed.csv>
      python3 -I tools/variety_suggest.py top --backup <nutrilog-backup.json> [--limit 50]
The FDC CSV folders and the dmBio CSV are not in the repo (like for the converters); without them USDA and dmBio get fewer suggestions.
"""
import argparse
import csv
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)   # -I leaves the script folder out; this is the repo's own tools folder
import variety_kitchen as K  # noqa: E402

fold = K.fold
MAP_FILES = {'ciqual': 'vt_map_ciqual.json', 'usda': 'vt_map_usda.json', 'dmbio': 'vt_map_dmbio.json'}
MAP_APP = 'tapnaplo-variety-map'
CONF_ORDER = {'high': 0, 'medium': 1, 'low': 2}


# ============================================================ the list
class VList:
    """variety_units.json: nodes by id, and the term index (folded name or alias -> unit id; a term that two units share is left out)"""

    def __init__(self, path=None):
        with open(path or os.path.join(ROOT, 'variety_units.json'), encoding='utf-8') as fh:
            self.raw = json.load(fh)
        self.nodes = {}
        self.flags = {f['id']: f for f in self.raw.get('flags', [])}
        raw_terms = {}
        for main in self.raw['main']:
            self.nodes[main['id']] = {'level': 'main', 'role': main['role'], 'main': main['id']}
            for sub in main['subs']:
                self.nodes[sub['id']] = {'level': 'sub', 'role': main['role'], 'main': main['id']}
                for u in sub.get('units', []):
                    self.nodes[u['id']] = {'level': 'unit', 'role': main['role'], 'main': main['id'], 'other': u['id'].endswith('.other'), 'deprecated': bool(u.get('deprecated'))}
                    if u['id'].endswith('.other') or u.get('deprecated'):
                        continue
                    for t in [u.get('hu'), u.get('en')] + list(u.get('a', [])):
                        if t:
                            raw_terms.setdefault(fold(t), set()).add(u['id'])
        # an English term also in its other number: lettuce / lettuces, cherry / cherries
        for term, ids in list(raw_terms.items()):
            if not re.fullmatch(r'[a-z ]+', term):
                continue
            for v in plural_forms(term):
                raw_terms.setdefault(v, set()).update(ids)
        for t, uid in EXTRA_UNIT_TERMS.items():   # the few words of the source tables that the list does not spell (defined below)
            if uid in self.nodes:
                raw_terms.setdefault(fold(t), set()).add(uid)
        self.terms = {t: next(iter(ids)) for t, ids in raw_terms.items() if len(ids) == 1}
        self.max_words = max(len(t.split()) for t in self.terms)

    def has(self, vt):
        return vt in self.nodes and self.nodes[vt]['level'] in ('sub', 'unit')

    def mainOf(self, vt):
        return vt.split('.')[0]


def plural_forms(term):
    out = set()
    if term.endswith('y') and len(term) > 3:
        out.add(term[:-1] + 'ies')
    elif term.endswith('ies'):
        out.add(term[:-3] + 'y')
    elif term.endswith(('s', 'x', 'ch', 'sh')):
        if term.endswith('es'):
            out.add(term[:-2])
        elif term.endswith('s'):
            out.add(term[:-1])
        out.add(term + 'es')
    else:
        out.add(term + 's')
    return {v for v in out if len(v) > 2}


# ============================================================ matching a name
STATE_WORDS = set('''raw cooked boiled fresh frozen canned drained steamed roasted grilled baked fried dried dehydrated dry whole unprepared prepared plain average
without with salt unsalted salted skin skinless peeled unpeeled flesh pulp sweetened unsweetened prepacked pre packed organic ripe mature seeds solids liquid
added sodium low high fat nonfat lean fatless trimmed all grades select choice prime separable cut retail commercial home made homemade stewed braised broiled
microwaved pan the of and in a an or by from only mixed species wild farmed fillet filet stalk leaf leaves head root bulb stem tops sprouts flower
medium large small ounce piece pieces half halves cup cups slices sliced chopped diced shredded grated ground canned heated frozen thawed no added'''.split())
# words that make the food something else than the unit itself (a juice, a sauce, a snack ...): the unit is then NOT suggested by the generic rule
PRODUCT_WORDS = set('''juice nectar sauce soup stew salad pie cake cookie cookies biscuit biscuits bar bars chips crisps crisp fries puree paste powder flour starch syrup jam jelly
marmalade pudding dessert ice cream yoghurt yogurt drink beverage smoothie cocktail wine beer liqueur vinegar oil butter spread dip dressing ketchup pickle pickles
pickled preserve sorbet candy sweets chocolate sandwich burger pizza pasta noodles bread roll buns bun cracker crackers cereal flakes muffin pancake waffle
croissant pastry tart dumpling dumplings casserole curry gravy stuffing filling extract concentrate formula infant baby babyfood tablet capsule supplement
sausage sausages frankfurter hotdog bologna salami luncheon pate loaf spam nuggets patties patty tenders strips breaded battered coated stuffed marinated
smoked cured mix blend kit imitation substitute analog analogue seasoning seasonings flavored flavoured flavor flavour'''.split())
# the words of GENERIC_UNITS are terms that stand for a product made from the plant (bread, pasta, milk); a more specific unit in the same name wins
GENERIC_TERMS = {'bread', 'kenyer', 'pasta', 'tészta', 'teszta', 'milk', 'tej', 'flour', 'liszt', 'porridge', 'tortilla', 'egg', 'eggs', 'tojas', 'chickpeas'}


def tokens(name):
    return fold(name).split()


def find_terms(toks, vl):
    """every term of the list found in the tokens (longest first, no overlaps) -> [(start, end, term, unit id)]"""
    found, i = [], 0
    while i < len(toks):
        hit = None
        for n in range(min(vl.max_words, len(toks) - i), 0, -1):
            t = ' '.join(toks[i:i + n])
            if t in vl.terms:
                hit = (i, i + n, t, vl.terms[t])
                break
        if hit:
            found.append(hit)
            i = hit[1]
        else:
            i += 1
    return found


def reorder_views(name):
    """USDA and CIQUAL write 'Beans, kidney, ...' and 'Chard, swiss, raw': also look at 'kidney beans' and 'swiss chard' (descriptor + head noun)"""
    parts = [fold(p) for p in str(name).split(',')][:4]
    views = []
    if len(parts) >= 2 and parts[0]:
        for p in parts[1:]:
            if p and len(p.split()) <= 2:
                views.append(p + ' ' + parts[0])
    return views


def allowed_unit(uid, allowed):
    """allowed = prefixes: 'veg' is every unit of the main group veg, 'dai.aged-cheese' only that subgroup, 'gra.corn' only the maize units"""
    return any(uid.startswith(a + '.') for a in allowed)


def unit_candidates(name, allowed_mains, vl):
    """-> {'units': {unit id: {'pos': first position, 'generic': bool}}, 'toks': tokens, 'extra': unknown words in the head part}"""
    toks = tokens(name)
    found = {}
    for (s, e, term, uid) in find_terms(toks, vl):
        if allowed_unit(uid, allowed_mains):
            cur = found.get(uid)
            if cur is None or s < cur['pos']:
                found[uid] = {'pos': s, 'generic': term in GENERIC_TERMS, 'term': term}
    for view in reorder_views(name):
        for (s, e, term, uid) in find_terms(view.split(), vl):
            if allowed_unit(uid, allowed_mains) and uid not in found:
                found[uid] = {'pos': 0, 'generic': term in GENERIC_TERMS, 'term': term, 'reordered': True}
    return found, toks


def head_part_words(name):
    return fold(str(name).split(',')[0]).split()


def pick_unit(name, allowed_mains, vl):
    """the one unit that fits, with a confidence and a note, or (None, None, reason)"""
    found, toks = unit_candidates(name, allowed_mains, vl)
    if not found:
        return None, None, 'no unit term'
    ids = list(found)
    if len(ids) > 1:   # a specific species beats a generic product word (rye bread: rye, not wheat)
        specific = [u for u in ids if not found[u]['generic']]
        if len(specific) == 1:
            ids = specific
        else:
            return None, None, 'ambiguous: ' + ', '.join(sorted(ids))
    uid = ids[0]
    words = set(toks)
    blockers = sorted(w for w in words if w in PRODUCT_WORDS and w not in K.fold(uid).split('.'))
    # the term itself may be the product word (peanut butter, olive oil, sweet corn): then the term is fine
    term_words = set(found[uid]['term'].split())
    blockers = [w for w in blockers if w not in term_words]
    if blockers:
        return None, None, 'product word: ' + ', '.join(blockers)
    head = head_part_words(name)
    head_ok = all(w in STATE_WORDS or w in term_words for w in head) or found[uid].get('reordered')
    f = fold(name)
    if not head_ok and re.search(r'\bwith\b', ADDIN_STATE_RE.sub(' ', f)):
        return None, None, 'composite: a word before "with" is not the unit'   # 'Corn with red and green peppers' is not pepper
    conf = 'high' if head_ok and found[uid]['pos'] == 0 or found[uid].get('reordered') else 'medium'
    if conf == 'high' and ADDIN_RE.search(ADDIN_STATE_RE.sub(' ', f)):
        conf = 'medium'   # 'yogurt with cereals', 'milk, chocolate': the unit is there, but something is added
    return uid, conf, ''


ADDIN_STATE_RE = re.compile(r'\b(with|without)\s+(skin|salt|added|bone|fat|seeds?|peel|liquid|solids|sodium|vitamin|calcium)\b')
ADDIN_RE = re.compile(r'\b(with|flavou?red|fruits?|cereals?|chocolate|sweetened|fortified|vanilla|honey|sugar|cocoa)\b')


# ============================================================ the offal flag, special words, traps
OFFAL_RE = re.compile(r'\b(liver|livers|kidney|kidneys|heart|hearts|tongue|brain|brains|tripe|giblets|gizzard|gizzards|sweetbread|sweetbreads|spleen|lung|lungs|variety meats|offal|chitterling|marrow bone)\b')
HUMMUS_RE = re.compile(r'\b(hummus|humusz|hummusz|houmous)\b')
POPCORN_RE = re.compile(r'\b(popcorn|pop corn|pattogatott kukorica)\b')
# traps of the plan (3.3/5) and other places where a unit word is in the name but the food is something else: decided before the unit rule
TRAPS = [
    (r'caribbean cabbage', None, 'high', 'trap-caribbean-cabbage', 'a tuber of the Caribbean (malanga), not a cabbage: no suggestion'),
    (r'^(nuts |beverages )?coconut water\b|kokuszviz', 'bev.juice', 'high', 'trap-coconut-water', 'coconut water is a drink, not coconut flesh (plan 2)'),
    (r'coconut (milk|cream) (drink|beverage)|kokusz(dio)? ital|kokuszital|^beverages (coconut|almond|oat|rice)', 'bev.plant', 'medium', 'trap-coconut-drink', 'a coconut drink is a plant-based drink (plan 2)'),
    (r'^(nuts )?coconut (milk|cream)\b|^kokusz(tej|krem|tejszin)', 'fru.tropical.coconut', 'medium', 'trap-coconut-milk', 'coconut milk or cream for cooking is made from the coconut flesh; a ready-to-drink coconut drink is bev.plant (plan 2)'),
    (r'^seeds? (pumpkin|squash)|^(roasted |raw |dried )?pumpkin seeds?\b|\bpepitas\b|^(bio )?(morzsolt |hejas )?tokmag\b', 'nut.seeds.pumpkin-seed', 'medium', 'trap-pumpkin-seed', 'pumpkin seeds are an oilseed, not pumpkin flesh'),
    (r'^(extra virgin )?olive oil\b|^(bio )?(extra ?szuz )?olivaolaj\b', 'fat.oils.olive-oil', 'high', 'trap-olive-oil', 'olive oil is its own unit (plan 2)'),
    (r'^(spices )?pepper (black|white)\b|^(black|white|ground) pepper\b|^peppercorns?\b|^(bio )?(fekete|feher) bors\b', 'spi.dry-spices', 'high', 'trap-black-pepper', 'black pepper is a spice, not bell pepper'),
    (r'\bcorn oil\b|maize oil|kukoricaolaj', 'fat.oils.other', 'medium', 'trap-corn-oil', 'corn oil is an oil, not maize'),
    (r'^peanut oil\b', 'fat.oils.other', 'medium', 'trap-peanut-oil', 'peanut oil is an oil'),
    (r'\bsoy(a)? ?(milk|drink|beverage)|soymilk|szojaital', 'bev.plant', 'medium', 'trap-soy-drink', 'a soy drink is a plant-based drink, not soybean'),
    (r'\b(almond|oat|rice|hazelnut|cashew) (milk|drink|beverage)|(oat|rice|almond)[- ]based drink|mandulaital|zabital|rizsital', 'bev.plant', 'medium', 'trap-plant-drink', 'a plant-based drink'),
]
EXTRA_UNIT_TERMS = {   # words of the source tables that the list does not spell; each one is one unit and nothing else
    'corn flour': 'gra.corn.corn', 'corn meal': 'gra.corn.corn', 'corn grits': 'gra.corn.corn', 'grits': 'gra.corn.corn',
    'canola oil': 'fat.oils.rapeseed-oil',   # canola is a rapeseed cultivar: USDA writes 'Oil, canola'
}


def kitchen_blocked(name):
    """popcorn and hummus: the group depends on the ingredient list (kitchen test); without a list there is no suggestion"""
    f = fold(name)
    if HUMMUS_RE.search(f):
        return 'hummus: needs the ingredient list (kitchen test)'
    if POPCORN_RE.search(f):
        return 'popcorn: needs the ingredient list (kitchen test)'
    return None


# ============================================================ group rules (regex on the folded name, vt, confidence, rule id)
R = lambda rx, vt, conf, rid: (re.compile(rx), vt, conf, rid)   # noqa: E731

CIQUAL_RULES = {
    ('beverages', 'water'): [R(r'.', 'bev.water', 'high', 'ciqual-water')],
    ('beverages', 'alcoholic beverages'): [R(r'alcohol free|non alcoholic|without alcohol', None, 'high', 'skip-alcohol-free'), R(r'.', 'bev.alcohol', 'high', 'ciqual-alcohol')],
    ('beverages', 'non-alcoholic beverages'): [
        R(r'(cocoa|chocolate) powder|malted', None, 'high', 'skip-cocoa-powder'),
        R(r'rice based|oat based|soy based|almond based|plant based|soya', 'bev.plant', 'high', 'ciqual-plant-drink'),
        R(r'nectar|cocktail|lemonade|cola|soda|tonic|energy drink|soft drink|iced tea|syrup|sweetened|flavoured|sports', 'bev.sweetened', 'medium', 'ciqual-sweetened'),
        R(r'\bjuice\b', 'bev.juice', 'medium', 'ciqual-juice'),
        R(r'\b(tea|coffee|infusion|chicory|herbal)\b', 'bev.unsweetened', 'medium', 'ciqual-tea-coffee'),
        R(r'\bmilk\b|cocoa drink|chocolate drink', 'bev.milk-based', 'low', 'ciqual-milk-drink'),
    ],
    ('miscellaneous', 'sauces'): [R(r'.', 'spi.sauces', 'medium', 'ciqual-sauce')],
    ('miscellaneous', 'herbs'): [R(r'.', 'spi.herbs', 'high', 'ciqual-herb')],
    ('miscellaneous', 'spices'): [R(r'^poppy', 'nut.seeds.poppy', 'medium', 'ciqual-poppy-seed'), R(r'.', 'spi.dry-spices', 'high', 'ciqual-spice')],
    ('miscellaneous', 'salts'): [R(r'.', 'spi.dry-spices', 'high', 'ciqual-salt')],
    ('miscellaneous', 'condiments'): [R(r'^olive', 'veg.fruit.olive', 'medium', 'ciqual-olive'), R(r'mustard|ketchup|mayonnaise', 'spi.sauces', 'medium', 'ciqual-condiment')],
    ('miscellaneous', 'seaweed'): [R(r'.', 'fis.algae.other', 'low', 'ciqual-seaweed')],
    ('sugar and confectionery', 'chocolate and chocolate products'): [R(r'.', 'swe.chocolate', 'high', 'ciqual-chocolate')],
    ('sugar and confectionery', 'cakes and pastry'): [R(r'.', 'swe.pastry', 'high', 'ciqual-pastry')],
    ('sugar and confectionery', 'sweet biscuits'): [R(r'.', 'swe.pastry', 'high', 'ciqual-biscuit')],
    ('sugar and confectionery', 'Viennese pastries'): [R(r'.', 'swe.pastry', 'medium', 'ciqual-viennese')],
    ('sugar and confectionery', 'jam'): [R(r'.', 'swe.fruit-sweets', 'high', 'ciqual-jam')],
    ('sugar and confectionery', 'sugars and honey'): [R(r'aspartame|sweetener|stevia|saccharin|sucralose|xylitol|sorbitol|polyol|erythritol', None, 'high', 'skip-sweetener'), R(r'.', 'swe.sugar-honey', 'high', 'ciqual-sugar')],
    ('sugar and confectionery', 'breakfast cereals'): [R(r'.', 'dis.breakfast', 'medium', 'ciqual-breakfast')],
    ('sugar and confectionery', 'non-chocolate confectionery'): [
        R(r'chewing gum', None, 'high', 'skip-gum'),
        R(r'candied|iced chestnut|fruit paste', 'swe.fruit-sweets', 'medium', 'ciqual-candied'),
        R(r'candy|candies|lollipop|jelly|liquorice|licorice|marshmallow|caramel|toffee|nougat', 'swe.candy', 'medium', 'ciqual-candy'),
    ],
    ('ice cream and sorbet', 'ice cream'): [R(r'.', 'swe.dairy-dessert', 'medium', 'ciqual-icecream')],
    ('ice cream and sorbet', 'frozen desserts'): [R(r'ice cream|cream', 'swe.dairy-dessert', 'low', 'ciqual-frozen-dessert')],
    ('starters and dishes', 'soups'): [R(r'.', 'dis.soup', 'high', 'ciqual-soup')],
    ('starters and dishes', 'sandwiches'): [R(r'.', 'dis.bread', 'high', 'ciqual-sandwich')],
    ('starters and dishes', 'pizzas, crepe and pies'): [R(r'pizza', 'dis.bread', 'high', 'ciqual-pizza'), R(r'.', 'dis.bread', 'low', 'ciqual-crepe-pie')],
    ('starters and dishes', 'dishes'): [R(r'^(tempeh|tofu)\b', 'leg.soy.soybean', 'high', 'ciqual-soy-product')],
    ('cereal products', 'savoury biscuits'): [
        R(r'potato', 'sna.potato', 'medium', 'ciqual-potato-snack'),
        R(r'maize|corn chips|tortilla chips|\bcorn\b', 'sna.corn', 'medium', 'ciqual-corn-snack'),
        R(r'peanuts|\bnuts\b', 'sna.seed', 'medium', 'ciqual-nut-snack'),
        R(r'.', 'sna.other-grain', 'medium', 'ciqual-savoury-biscuit'),
    ],
    ('fats and oils', 'butters'): [R(r'^butter', 'fat.animal.butter', 'high', 'ciqual-butter')],
    ('fats and oils', 'margarines'): [R(r'.', 'fat.spread.margarine', 'high', 'ciqual-margarine')],
    ('fats and oils', 'vegetable oils'): [R(r'solid vegetable fat|shortening', None, 'high', 'skip-solid-fat'), R(r'^coconut', 'fat.oils.coconut-oil', 'medium', 'ciqual-coconut-oil')],
    ('fats and oils', 'other fats'): [R(r'paraffin', None, 'high', 'skip-paraffin'), R(r'chicken fat|goose fat|turkey fat', 'fat.animal.other', 'medium', 'ciqual-animal-fat')],
}
# the groups where the units of the list are looked for: allowed main groups
CIQUAL_UNITS = {
    ('fruits, vegetables, legumes and nuts', 'fruits'): ['fru'], ('fruits, vegetables, legumes and nuts', 'vegetables'): ['veg'],
    ('fruits, vegetables, legumes and nuts', 'legumes'): ['leg'], ('fruits, vegetables, legumes and nuts', 'nuts and seeds'): ['nut', 'fru'],
    ('fruits, vegetables, legumes and nuts', 'potatoes and other tubers'): ['tub'],
    ('cereal products', 'breads and similar'): ['gra'], ('cereal products', 'pasta, rice and grains'): ['gra'],
    ('meat, egg and fish', 'raw meat'): ['mea'], ('meat, egg and fish', 'cooked meat'): ['mea'], ('meat, egg and fish', 'delicatessen meat and similar'): ['mea'],
    ('meat, egg and fish', 'eggs'): ['egg'], ('meat, egg and fish', 'fish, raw'): ['fis'], ('meat, egg and fish', 'fish, cooked'): ['fis'],
    ('meat, egg and fish', 'seafood, raw'): ['fis'], ('meat, egg and fish', 'seafood, cooked'): ['fis'], ('meat, egg and fish', 'fish products'): ['fis'],
    ('milk and milk products', 'milk'): ['dai.milk'], ('milk and milk products', 'cheese and similar'): ['dai.fresh-cheese', 'dai.aged-cheese'],
    ('milk and milk products', 'cream and similar'): ['dai.cream'], ('milk and milk products', 'dairy products and similar'): ['dai.fermented', 'dai.milk'],
    ('fats and oils', 'vegetable oils'): ['fat'], ('fats and oils', 'other fats'): ['fat'], ('fats and oils', 'butters'): ['fat'],
    ('miscellaneous', 'seaweed'): ['fis'],
}

FALLBACK_RULES = {   # used only when the unit rule found nothing: 'Oil, rapeseed' is rapeseed oil, 'Oil, sesame' (no unit of the list) is another oil
    ('ciqual', ('fats and oils', 'vegetable oils')): [R(r'\boil\b', 'fat.oils.other', 'medium', 'ciqual-oil-other')],
    ('usda', 'Fats and Oils'): [R(r'^oil,|^oil ', 'fat.oils.other', 'medium', 'usda-oil-other')],
}

OIL_HEAD = r'^oil (?:(?:industrial|vegetable|cooking and salad|natreon|mid oleic|high oleic) )*'
USDA_RULES = {
    'Beverages': [
        R(r'^water\b|^beverages water|^beverages (tap|bottled) water', 'bev.water', 'high', 'usda-water'),
        R(r'non alcoholic|alcohol free|dealcoholized|without alcohol', None, 'high', 'skip-alcohol-free'),
        R(r'^alcoholic beverage|\b(?<!root )(beer|wine|liqueur|whiskey|rum|vodka|gin|brandy|cocktail mix)\b', 'bev.alcohol', 'high', 'usda-alcohol'),
        R(r'milk based|milk beverage', 'bev.milk-based', 'low', 'usda-milk-drink'),
        R(r'\b(carbonated|cola|soda|lemonade|energy drink|fruit punch|flavor|flavored|sweetened|sports|tonic|ginger ale|root beer|cocktail)\b', 'bev.sweetened', 'medium', 'usda-sweetened'),
        R(r'^beverages (coffee|tea)|^(coffee|tea)\b|\b(brewed|infusion)\b', 'bev.unsweetened', 'medium', 'usda-tea-coffee'),
        R(r'almond milk|soymilk|soy milk|rice milk|oat milk|coconut milk', 'bev.plant', 'medium', 'usda-plant-drink'),
    ],
    'Fruits and Fruit Juices': [R(r'\bjuice\b', 'bev.juice', 'medium', 'usda-juice'), R(r'\bnectar\b', 'bev.sweetened', 'low', 'usda-nectar')],
    'Soups, Sauces, and Gravies': [
        R(r'^soup|\bsoup\b', 'dis.soup', 'high', 'usda-soup'),
        R(r'sauce|gravy|ketchup|mustard|dressing|mayonnaise|salsa|pesto|marinade', 'spi.sauces', 'medium', 'usda-sauce'),
    ],
    'Spices and Herbs': [
        R(r'^spices salt|\bsalt\b', 'spi.dry-spices', 'high', 'usda-salt'),
        R(r'poppy', 'nut.seeds.poppy', 'medium', 'usda-poppy-seed'),
        R(r'\bseeds?\b', 'spi.dry-spices', 'medium', 'usda-spice-seed'),
        R(r'\b(basil|parsley|oregano|thyme|rosemary|sage|dill|mint|marjoram|tarragon|chives|savory|bay leaf|coriander leaf|chervil|lemon grass|fenugreek leaves)\b', 'spi.herbs', 'high', 'usda-herb'),
        R(r'^spices', 'spi.dry-spices', 'medium', 'usda-spice'),
    ],
    'Sweets': [
        R(r'^(puddings|pudding|frozen yogurts|ice cream|custard)', 'swe.dairy-dessert', 'medium', 'usda-dessert'),
        R(r'^syrups chocolate', 'swe.sugar-honey', 'low', 'usda-chocolate-syrup'),
        R(r'^rennin', 'swe.dairy-dessert', 'low', 'usda-rennin'),
        R(r'chocolate|cocoa|candies, milk chocolate|candies, dark chocolate', 'swe.chocolate', 'medium', 'usda-chocolate'),
        R(r'^(sugars|sugar|honey|syrups|molasses)\b|^syrup', 'swe.sugar-honey', 'high', 'usda-sugar'),
        R(r'^(jams|jelly|jellies|preserves|marmalade)', 'swe.fruit-sweets', 'high', 'usda-jam'),
        R(r'chewing gum|^gum\b', None, 'high', 'skip-gum'),
        R(r'^candies|^candy|^gum|^marshmallow|^gelatin dessert', 'swe.candy', 'medium', 'usda-candy'),
    ],
    'Baked Products': [
        R(r'\b(tortillas?)\b.*\bflour\b|\bflour\b.*\btortillas?\b', None, 'high', 'skip-flour-tortilla'),
        R(r'cake|cookie|cookies|brownie|muffin|\bpie\b|pies|pastry|pastries|croissant|danish|doughnut|donut|waffle|pancake|cobbler|tart|strudel|sweet roll|cinnamon roll', 'swe.pastry', 'medium', 'usda-pastry'),
        R(r'cracker|crackers|pretzel|breadsticks|melba|crispbread', 'sna.other-grain', 'medium', 'usda-cracker'),
    ],
    'Breakfast Cereals': [R(r'\boats?\b|oatmeal|grits|farina|cream of', None, 'high', 'skip-hot-cereal'), R(r'.', 'dis.breakfast', 'medium', 'usda-breakfast')],
    'Snacks': [
        R(r'popcorn', None, 'high', 'skip-popcorn'),
        R(r'sweet potato', None, 'high', 'skip-sweet-potato-snack'),
        R(r'\bbars?\b|soy chips|soy crisps', None, 'high', 'skip-snack-bar'),
        R(r'potato chips|potato sticks|potato crisps', 'sna.potato', 'high', 'usda-potato-chips'),
        R(r'tortilla chips|corn chips|corn-based|corn based|cheese puffs|cheese curls|cheese flavored', 'sna.corn', 'medium', 'usda-corn-snack'),
        R(r'pretzel|crackers|rice cakes|party mix|snack mix|crisps|puffs', 'sna.other-grain', 'low', 'usda-grain-snack'),
        R(r'\b(nuts|seeds|trail mix)\b', 'sna.seed', 'low', 'usda-seed-snack'),
    ],
    'Fats and Oils': [
        R(r'salad dressing|mayonnaise|dressing', 'spi.sauces', 'medium', 'usda-dressing'),
        # 'Oil, X, qualifiers': the FIRST species decides (qualifiers like 'salad or cooking' or 'industrial' say nothing about the species); a blend of oils is no single unit
        R(r'^oil (industrial |vegetable )?(corn|soy|soybean|cottonseed|peanut|palm|canola|sunflower|olive|coconut|safflower)\b.*\band (corn|soy|soybean|cottonseed|peanut|palm|canola|sunflower|olive|coconut|safflower)\b', None, 'high', 'skip-oil-blend'),
        R(r'\balaska native\b|^oil (whale|seal|walrus|beluga)', 'fat.animal.other', 'low', 'usda-animal-oil'),
        R(OIL_HEAD + r'canola\b', 'fat.oils.rapeseed-oil', 'medium', 'usda-oil-canola'),
        R(OIL_HEAD + r'olive\b', 'fat.oils.olive-oil', 'high', 'usda-oil-olive'),
        R(OIL_HEAD + r'sunflower\b', 'fat.oils.sunflower-oil', 'high', 'usda-oil-sunflower'),
        R(OIL_HEAD + r'coconut\b', 'fat.oils.coconut-oil', 'medium', 'usda-oil-coconut'),
        R(r'^margarine|margarine-like|^spread|spreads', 'fat.spread.margarine', 'medium', 'usda-margarine'),
        R(r'^butter (replacement|substitute|buds|spray)|^butter,? (replacement|substitute)', None, 'high', 'skip-butter-replacement'),
        R(r'^butter\b', 'fat.animal.butter', 'high', 'usda-butter'),
        R(r'^fat (beef|chicken|duck|goose|turkey|mutton)|tallow|^fat ', 'fat.animal.other', 'low', 'usda-animal-fat'),
    ],
    'Poultry Products': [R(r'^(quail|pheasant|guinea hen|ostrich|emu|squab|cornish game hen|dove|pigeon)\b', 'mea.poultry.other', 'medium', 'usda-poultry-other')],
    'Lamb, Veal, and Game Products': [R(r'^game meat (bison|buffalo|elk|rabbit|boar|caribou|antelope|beaver|bear|moose|squirrel|opossum|horse|ostrich|emu)', 'mea.game.other', 'medium', 'usda-game-other')],
    'Legumes and Legume Products': [R(r'soymilk|soy milk', 'bev.plant', 'medium', 'usda-soy-drink')],
    'Fast Foods': [], 'Restaurant Foods': [], 'Meals, Entrees, and Side Dishes': [],
}
USDA_UNITS = {
    'Beef Products': ['mea'], 'Pork Products': ['mea'], 'Poultry Products': ['mea'], 'Lamb, Veal, and Game Products': ['mea'],
    'Finfish and Shellfish Products': ['fis'], 'Dairy and Egg Products': ['dai', 'egg'], 'Vegetables and Vegetable Products': ['veg', 'tub', 'leg'],
    'Fruits and Fruit Juices': ['fru'], 'Legumes and Legume Products': ['leg', 'nut'], 'Nut and Seed Products': ['nut', 'fru'],
    'Cereal Grains and Pasta': ['gra'], 'Baked Products': ['gra'], 'Fats and Oils': ['fat'],
}
# fast food, restaurant food and meals are dishes: keywords decide the subgroup (when two kinds of words are in the name there is no suggestion)
DISH_KEYWORDS = [
    ('dis.bread', r'\b(pizza|sandwich|burger|hamburger|cheeseburger|taco|burrito|hot dog|hotdog|bagel|wrap|biscuit|sub|gyro|quesadilla|nachos)\b'),
    ('dis.soup', r'\b(soup|chowder|broth)\b'),
    ('dis.pasta-grain', r'\b(pasta|spaghetti|macaroni|lasagna|lasagne|noodles?|rice|risotto|fried rice|pilaf|paella)\b'),
    ('dis.meat-fish', r'\b(chicken|beef|pork|fish|steak|nuggets|turkey|ham|ribs|shrimp|lamb|meatballs?|sausage|bacon|tenders|wings)\b'),
    ('dis.legume-veg', r'\b(beans?|lentils?|vegetables?|salad|coleslaw|potatoes|hash browns|french fries|onion rings|stew|curry)\b'),
]
DISH_CATS = {'Fast Foods', 'Restaurant Foods', 'Meals, Entrees, and Side Dishes'}
CIQUAL_DISH_GROUPS = {('starters and dishes', 'dishes'), ('starters and dishes', 'mixed salads'), ('starters and dishes', 'savoury pastries and other starters')}


DESSERT_RE = re.compile(r'\b(pudding|puddings|dessert|ice cream|cake|cakes|pie|cookie|cookies|brownie|candy|candies|chocolate|cobbler|custard|flan)\b')


def dish_subgroup(f):
    if DESSERT_RE.search(f):   # 'arroz con leche (rice pudding)' is a dessert, not a rice dish: no suggestion
        return None
    hits = [vt for vt, rx in DISH_KEYWORDS if re.search(rx, f)]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:   # a sandwich with chicken is bread-based (the vessel decides); otherwise two kinds of words: no suggestion
        if 'dis.bread' in hits:
            return 'dis.bread'
        if 'dis.soup' in hits:
            return 'dis.soup'
        return None
    return None


# ============================================================ one food -> one suggestion (or none)
def suggest_one(source, code, name, group, vl, cat=None):
    """-> dict(vt, flags, rule, confidence, note) with vt None when there is no suggestion (the note says why, when it is useful)"""
    f = fold(name)
    out = {'vt': None, 'flags': [], 'rule': '', 'confidence': '', 'note': ''}
    block = kitchen_blocked(name)
    if block:
        out['note'] = block
        return out
    for rx, vt, conf, rid, why in TRAPS:
        if re.search(rx, f):
            out.update(vt=vt, rule=rid, confidence=conf, note=why)
            return out
    rules, units = [], []
    if source == 'ciqual':
        key = (cat[0], cat[1])
        rules, units = CIQUAL_RULES.get(key, []), CIQUAL_UNITS.get(key, [])
        is_dish = key in CIQUAL_DISH_GROUPS
    elif source == 'usda':
        rules, units = USDA_RULES.get(cat, []), USDA_UNITS.get(cat, [])
        is_dish = cat in DISH_CATS
    else:
        is_dish = False
    for rx, vt, conf, rid in rules:
        if rx.search(f):
            if vt is None:
                out['note'] = rid
                return out
            out.update(vt=vt, rule=rid, confidence=conf)
            return out
    if is_dish:
        vt = dish_subgroup(f)
        if vt:
            out.update(vt=vt, rule='dish-keywords', confidence='low', note='dish: no unit')
        else:
            out['note'] = 'dish: no clear subgroup'
        return out
    if units:
        uid, conf, why = pick_unit(name, units, vl)
        if uid is None:
            for rx, vt, conf2, rid in FALLBACK_RULES.get((source, cat if source == 'usda' else (cat[0], cat[1])), []):
                if rx.search(f):
                    out.update(vt=vt, rule=rid, confidence=conf2)
                    return out
            out['note'] = why
            return out
        flags = []
        if vl.nodes[uid]['main'] == 'mea' and OFFAL_RE.search(f):
            flags = ['offal']
        out.update(vt=uid, flags=flags, rule='unit-name', confidence=conf)
        return out
    out['note'] = 'no rule for this group'
    return out


# ============================================================ dmBio (Hungarian product names + the original ingredient list)
DM_BABY = re.compile(r'honapos|tapszer|anyatej|\bbebi|bebimenu|bebidesszert|junior|gyermekmenu|csecsemo|eves kortol|gyerekeknek|gyermekeknek|tejpep|gabonapep')
DM_NEUTRAL = set('''bio natur natur extra szuz finomitatlan gluténmentes glutenmentes teljes kiorlesu nagyszemu aproszemu hantolt magozott szaritott aszalt pirított pirított
egesz darabolt morzsolt liofilizalt sos sozott hidegen sajtolt tisztitott reszelt orolt kiszereles barna feher piros fekete zold vegyes szemes ecetes szeletelt'''.split())
DM_NEUTRAL = {fold(w) for w in DM_NEUTRAL}
DM_UNITWORDS = re.compile(r'^(\d+([.,]\d+)?|g|kg|ml|l|db|filter|tasak)$')
DM_SUFFIX_SAME = ('liszt', 'pehely', 'krem', 'dara', 'buzadara', 'szeletek', 'szelet')   # almond cream = almond, buckwheat flour = buckwheat: the same species
DM_SUFFIX_ONLY = {'krem': 'nut', 'szeletek': 'fru', 'szelet': 'fru'}   # cream only for nuts, 'dried mango slices' only for fruit
# products that are mixes, flavourings or in-between things: no suggestion (a note says why); decided first
DM_BLOCK = re.compile(r'etelizesito|leveskocka|alaple|sutokeverek|tesztakeverek|teszta keverek|palacsintapor|cookie dough|izu (krem|kenyerfeltet)|kenyerszelet|puffasztott[^,]*(csicseri|lencse|borso)|kenyerfeltet[^,]*(curry|mango|papaya|gyumolcs)|energiagolyo')
DM_RULES = [
    R(r'kokuszviz', 'bev.juice', 'high', 'dm-coconut-water'),
    R(r'\bzabital|szojaital|rizsital|mandulaital|kokuszital|\bital\b', 'bev.plant', 'medium', 'dm-plant-drink'),
    R(r'(direktle|gyumolcsle|narancsle|grapefruitle|almale|zoldsegle|vegyesgyumolcsle)\b', 'bev.juice', 'medium', 'dm-juice'),
    R(r'jeges tea|ice tea|iced tea', 'bev.sweetened', 'medium', 'dm-iced-tea'),
    R(r'caffe latte|cappuccino', 'bev.milk-based', 'low', 'dm-milk-coffee'),
    R(r'(tea\b|(?<!s)teak|\bfilter)', 'bev.unsweetened', 'medium', 'dm-tea'),
    R(r'\bkave\b|kavé|espresso|malatakave|tonkolykave|kaveval', 'bev.unsweetened', 'medium', 'dm-coffee'),
    R(r'\bdzsem|extradzsem|lekvar', 'swe.fruit-sweets', 'high', 'dm-jam'),
    R(r'vanilias cukor|vaniliascukor|vanilia cukor', 'swe.sugar-honey', 'medium', 'dm-vanilla-sugar'),
    R(r'agavészirup|agavesirup|agavesz|juharszirup|viragmez|^mez\b|nadcukor|porcukor|^cukor|datolyaszirup|datolya edesito', 'swe.sugar-honey', 'high', 'dm-sugar'),
    R(r'^(etcsokolade|tejcsokolade|nugatos tejcsokolade|csokolade|feher csokolade)\b', 'swe.chocolate', 'medium', 'dm-chocolate'),
    R(r'csokolad[^,]*[- ]?szelet|csokoladeszelet|csokolad.*bevon|csokoladeban|bevon.*csokolad', 'swe.chocolate', 'low', 'dm-chocolate-coated'),
    R(r'csokolad.*perec|perec.*csokolad', 'sna.other-grain', 'low', 'dm-cracker-chocolate'),
    R(r'puffasztott[^,]*kukoricaszelet', 'sna.corn', 'medium', 'dm-puffed-corn'),
    R(r'puffasztott[^,]*rizsszelet', 'sna.other-grain', 'low', 'dm-puffed-rice'),
    R(r'\bperec|kreker|kekszersult', 'sna.other-grain', 'medium', 'dm-cracker'),
    R(r'gyumolcsszelet', 'swe.fruit-sweets', 'low', 'dm-fruit-bar'),
    R(r'puding', 'swe.dairy-dessert', 'low', 'dm-pudding'),
    R(r'keksz|puszedli|cantuccini|kifli|csillag|ostya|susemeny|kosarka', 'swe.pastry', 'low', 'dm-pastry'),
    R(r'muzli|müzli|crunchy|gabonapehely mix|ropogos tonkolypehely', 'dis.breakfast', 'medium', 'dm-breakfast'),
    R(r'bolognai|curry', 'spi.sauces', 'low', 'dm-sauce-cooking'),
    R(r'ketchup|\bszosz|pesto|mustar|dressing|majonez|teriyaki|shoyu|sriracha', 'spi.sauces', 'medium', 'dm-sauce'),
    R(r'fuszersó|fuszerso|fuszerkeverek|bourbon vanilia|vaniliaru|vaniliarud|orolt vanilia', 'spi.dry-spices', 'medium', 'dm-spice'),
]
DM_DISH_KEYWORDS = [
    ('dis.soup', r'leves'),
    ('dis.pasta-grain', r'teszta|rizs|tortellini|ravioli|gnocchi|kuszkusz|bulgur|penne|spagetti|fusilli|farfalle'),
    ('dis.meat-fish', r'hus|csirke|marha|sertes|\bhal\b|lazac|szalonna'),
    ('dis.legume-veg', r'bab|lencse|csicseri|zoldseg|ratatouille|padlizsan|sutotok|burgonya|spenot'),
]


def dm_ingredients(label):
    """the ingredient list out of the original label text of the dmBio CSV: 'Pontos termékmegnevezés:  <title>  <ingredients>  *<footnote>'; None when there is none"""
    if not label:
        return None
    t = re.sub(r'^\s*Pontos term[ée]kmegnevez[ée]s:\s*', '', str(label))
    parts = [p.strip() for p in re.split(r'\s{2,}', t) if p.strip()]
    if len(parts) < 2:
        return None
    block = parts[1]
    if block.startswith('*') or block.lower().startswith(('nyomokban', 'kérjük', 'kerjuk')):
        return None
    block = re.split(r'\s\*[^\s,]', block)[0]
    return block.strip() or None


def dm_head_unit(name, vl):
    """'Bio kesudió, 150 g' -> the unit when the name is that unit and nothing else (neutral words and the weight are left out); 'mandulakrém' -> the almond"""
    first = fold(str(name).split(',')[0]).split()
    rest = [w for w in first if w not in DM_NEUTRAL and not DM_UNITWORDS.match(w)]
    if not rest:
        return None
    term = ' '.join(rest)
    if term in vl.terms:
        return vl.terms[term]
    if len(rest) == 1:
        w = rest[0]
        for suf in DM_SUFFIX_SAME:
            if w.endswith(suf) and len(w) > len(suf) + 2 and w[:-len(suf)] in vl.terms:
                uid = vl.terms[w[:-len(suf)]]
                return uid if (suf not in DM_SUFFIX_ONLY or vl.nodes[uid]['main'] == DM_SUFFIX_ONLY[suf]) else None
    return None


def suggest_dmbio(code, name, ingredients, vl):
    f = fold(name)
    out = {'vt': None, 'flags': [], 'rule': '', 'confidence': '', 'note': ''}
    ing = dm_ingredients(ingredients)
    is_pop, is_hum = bool(POPCORN_RE.search(f)), bool(HUMMUS_RE.search(f))
    if is_pop or is_hum:
        if ing is None:
            out['note'] = 'popcorn/hummus: no ingredient list (kitchen test)'
            return out
        chk = K.kitchenCheck(ing)
        vt = K.popcornClass(ing) if is_pop else K.hummusClass(ing)
        out.update(vt=vt, rule='kitchen-popcorn' if is_pop else 'kitchen-hummus', confidence='medium')
        bits = []
        if chk['bad']:
            bits.append('not kitchen: ' + ', '.join(chk['bad']))
        if chk['unknown']:
            bits.append('not on the closed list: ' + ', '.join(chk['unknown']))
        if not bits and 'cukor' in fold(ing):
            bits.append('contains sugar: counts as a kitchen ingredient (open question of the plan)')
            out['confidence'] = 'low'   # Norbert has not decided yet whether sugar keeps popcorn a plain maize food
        out['note'] = '; '.join(bits)
        return out
    if DM_BABY.search(f):
        out['note'] = 'baby food'
        return out
    if DM_BLOCK.search(f):
        out['note'] = 'mix, flavouring or in-between product: no suggestion'
        return out
    f = re.sub(r'^(bio|dmbio)\s+', '', f)   # the rules that start with ^ look at the product word, not at 'Bio'
    for rx, vt, conf, rid in DM_RULES:
        if rx.search(f):
            out.update(vt=vt, rule=rid, confidence=conf)
            return out
    uid = dm_head_unit(name, vl)
    if uid:
        out.update(vt=uid, rule='dm-head-unit', confidence='high' if len(fold(name).split(',')[0].split()) <= 2 else 'medium')
        return out
    if re.search(r'egytalelet|tortellini|ravioli|gnocchi|ratatouille|pastetom|kenyerfeltet', f):
        hits = [vt for vt, rx in DM_DISH_KEYWORDS if re.search(rx, f)]
        if len(hits) == 1:
            out.update(vt=hits[0], rule='dm-dish-keywords', confidence='low')
        else:
            out['note'] = 'dish: no clear subgroup'
        return out
    out['note'] = 'no rule'
    return out


# ============================================================ tables -> suggestion rows
def load_usda_categories(dirs):
    """fdc_id -> category text, from the food.csv and food_category.csv of the FDC downloads (the CSV folders are not in the repo)"""
    cat = {}
    for d in dirs:
        names = {r['id']: r['description'] for r in csv.DictReader(open(os.path.join(d, 'food_category.csv'), encoding='utf-8-sig'))}
        for r in csv.DictReader(open(os.path.join(d, 'food.csv'), encoding='utf-8-sig')):
            if r['food_category_id'] in names:
                cat.setdefault(r['fdc_id'], names[r['food_category_id']])
    return cat


def load_dm_ingredients(path):
    out = {}
    for r in csv.DictReader(open(path, encoding='utf-8-sig'), delimiter=';'):
        out[r['Azonosító']] = r['Összetevők (eredeti)']
    return out


def build_rows(source, vl, root=ROOT, usda_cat=None, dm_ing=None):
    rows = []
    if source == 'ciqual':
        for x in json.load(open(os.path.join(root, 'ciqual.json'), encoding='utf-8'))['foods']:
            G, g = x.get('G'), x.get('g')
            s = suggest_one('ciqual', x['c'], x['n'], ' › '.join(v for v in (G, g) if v), vl, cat=(G, g))
            rows.append((x['c'], x['n'], ' › '.join(v for v in (G, g) if v), s))
    elif source == 'usda':
        for x in json.load(open(os.path.join(root, 'usda.json'), encoding='utf-8'))['foods']:
            cat = (usda_cat or {}).get(x['c'])
            s = suggest_one('usda', x['c'], x['n'], cat or '', vl, cat=cat)
            if cat is None and not s['vt'] and not s['note'].startswith(('popcorn', 'hummus')):
                s['note'] = 'no USDA category (give --usda-csv)'   # the traps work on the name alone, every other rule needs the category
            rows.append((x['c'], x['n'], cat or '', s))
    elif source == 'dmbio':
        for x in json.load(open(os.path.join(root, 'dmbio.json'), encoding='utf-8'))['foods']:
            s = suggest_dmbio(x['c'], x['n'], (dm_ing or {}).get(x['c']), vl)
            rows.append((x['c'], x['n'], '', s))
    return rows


COLUMNS = ['code', 'name', 'source_group', 'suggested_vt', 'flags', 'rule', 'confidence', 'note', 'approved', 'final_vt']


def write_suggestions(path, rows):
    with open(path, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(COLUMNS)
        for code, name, grp, s in rows:
            w.writerow([code, name, grp, s['vt'] or '', ';'.join(s['flags']), s['rule'], s['confidence'], s['note'], '', ''])


# ============================================================ apply: only the approved rows go into a map
YES = {'yes', 'y', 'igen', 'i', '1', 'x', 'true', 'ok'}


def apply_reviewed(source, reviewed_csv, vl, root=ROOT, map_path=None, updated=None):
    """-> (written rows, skipped rows [(code, reason)]). Never writes a row that is not approved or whose group is not in the list."""
    map_path = map_path or os.path.join(root, MAP_FILES[source])
    cur = {'app': MAP_APP, 'version': 1, 'source': source, 'updated': '', 'map': {}}
    if os.path.exists(map_path):
        cur = json.load(open(map_path, encoding='utf-8'))
    written, skipped = 0, []
    for r in csv.DictReader(open(reviewed_csv, encoding='utf-8-sig')):
        if fold(r.get('approved', '')) not in YES:
            continue
        code = (r.get('code') or '').strip()
        vt = (r.get('final_vt') or r.get('suggested_vt') or '').strip()
        flags = [x for x in (r.get('flags') or '').split(';') if x.strip()]
        if not code or not vt:
            skipped.append((code, 'no group'))
            continue
        if not vl.has(vt):
            skipped.append((code, f'{vt} is not a subgroup or unit of the list'))
            continue
        if any(fl not in vl.flags or vl.mainOf(vt) not in vl.flags[fl]['applies'] for fl in flags):
            skipped.append((code, f'flag {";".join(flags)} does not fit {vt}'))
            continue
        cur['map'][code] = {'vt': vt, 'vf': flags} if flags else vt
        written += 1
    cur.update(app=MAP_APP, version=1, source=source)
    cur['updated'] = updated or cur.get('updated') or ''
    cur['map'] = dict(sorted(cur['map'].items(), key=lambda kv: (len(kv[0]), kv[0])))
    with open(map_path, 'w', encoding='utf-8') as fh:
        json.dump(cur, fh, ensure_ascii=False, indent=0, separators=(',', ':'))
        fh.write('\n')
    return written, skipped


# ============================================================ top: the foods that are logged most often and are not classified
def top_unclassified(backup_path, vl, root=ROOT, limit=50, usda_cat=None, dm_ing=None):
    bk = json.load(open(backup_path, encoding='utf-8'))
    counts = {}
    for e in bk.get('log', []):
        counts[e.get('f')] = counts.get(e.get('f'), 0) + 1
    maps = {s: (json.load(open(os.path.join(root, fn), encoding='utf-8')).get('map', {}) if os.path.exists(os.path.join(root, fn)) else {}) for s, fn in MAP_FILES.items()}
    tables = {}
    pref = {'c:': 'ciqual', 'usda:': 'usda', 'dm:': 'dmbio'}
    out, classified, total = [], 0, 0
    for fid, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        total += n
        src = next((s for p, s in pref.items() if str(fid).startswith(p)), None)
        if src:
            code = fid.split(':', 1)[1]
            if code in maps[src]:
                classified += n
                continue
            if src not in tables:
                tables[src] = {c: (nm, g, s) for c, nm, g, s in build_rows(src, vl, root, usda_cat, dm_ing)}
            nm, g, s = tables[src].get(code, ('(not in the table)', '', {'vt': None, 'rule': '', 'confidence': '', 'note': ''}))
            out.append((fid, n, nm, s))
        else:
            food = (bk.get('foods') or {}).get(fid)
            if food and food.get('vt'):
                classified += n
                continue
            out.append((fid, n, (food or {}).get('name', '(unknown food)'), {'vt': None, 'rule': 'own food', 'confidence': '', 'note': 'own or saved food: set it in the editor / by the AI prompt'}))
    return {'total_entries': total, 'classified_entries': classified, 'distinct_foods': len(counts), 'top': out[:limit], 'unclassified_foods': len(out)}


# ============================================================ command line
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('suggest')
    a.add_argument('--out', required=True)
    a.add_argument('--usda-csv', nargs='*', default=[])
    a.add_argument('--dmbio-csv')
    b = sub.add_parser('apply')
    b.add_argument('--source', required=True, choices=list(MAP_FILES))
    b.add_argument('--reviewed', required=True)
    b.add_argument('--map', help='the map file to write (default: the file of the source in the repository)')
    c = sub.add_parser('top')
    c.add_argument('--backup', required=True)
    c.add_argument('--limit', type=int, default=50)
    c.add_argument('--root', default=ROOT, help='the folder with the tables and maps (default: the repository)')
    c.add_argument('--usda-csv', nargs='*', default=[])
    c.add_argument('--dmbio-csv')
    args = ap.parse_args(argv)
    vl = VList()
    if args.cmd == 'suggest':
        os.makedirs(args.out, exist_ok=True)
        usda_cat = load_usda_categories(args.usda_csv) if args.usda_csv else None
        dm_ing = load_dm_ingredients(args.dmbio_csv) if args.dmbio_csv else None
        for src in ('ciqual', 'usda', 'dmbio'):
            rows = build_rows(src, vl, ROOT, usda_cat, dm_ing)
            write_suggestions(os.path.join(args.out, f'variety_suggestions_{src}.csv'), rows)
            n = len(rows)
            by = {k: sum(1 for r in rows if r[3]['confidence'] == k and r[3]['vt']) for k in ('high', 'medium', 'low')}
            print(f'{src}: {n} foods, suggestions: high {by["high"]}, medium {by["medium"]}, low {by["low"]}, none {n - sum(by.values())}')
    elif args.cmd == 'apply':
        w, sk = apply_reviewed(args.source, args.reviewed, vl, map_path=args.map)
        print(f'{w} approved rows written to {args.map or MAP_FILES[args.source]}; {len(sk)} skipped')
        for code, why in sk[:20]:
            print('  skipped', code, why)
    else:
        usda_cat = load_usda_categories(args.usda_csv) if args.usda_csv else None
        dm_ing = load_dm_ingredients(args.dmbio_csv) if args.dmbio_csv else None
        r = top_unclassified(args.backup, vl, args.root, args.limit, usda_cat, dm_ing)
        print(f'{r["classified_entries"]} of {r["total_entries"]} entries are classified; {r["unclassified_foods"]} of {r["distinct_foods"]} foods are not')
        for fid, n, nm, s in r['top']:
            print(f'{n:5d}  {fid:16s} {nm[:60]:60s} -> {s["vt"] or "-"} ({s["confidence"] or s["note"]})')


if __name__ == '__main__':
    main()
