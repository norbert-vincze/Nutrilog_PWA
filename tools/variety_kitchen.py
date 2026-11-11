"""The kitchen-ingredient test of the Variety plan (version 39, step L3).

One shared, tested rule for two foods whose group depends on what is on the ingredient list:

    popcorn  with only kitchen ingredients (corn, oil, butter, salt, sugar, spices ...)   -> gra.corn.corn   (the unit "maize")
             with anything that is not a kitchen ingredient (flavouring, additive ...)    -> sna.corn        (Maize snacks)
    hummus   with only kitchen ingredients (chickpeas, tahini, olive oil, lemon, salt ...) -> leg.chickpea-pea.chickpea
             with anything that is not a kitchen ingredient                                -> dis.legume-veg

No ingredient list gives None: such a food cannot be classified by this rule and nothing is guessed.

The names are the ones of the plan (kitchenIngredientsOnly, popcornClass, hummusClass); they are written in camelCase on purpose,
so that a search for the name in the plan finds them here.

THE CLOSED LIST (Norbert approves it; the plan asks for it to be in one place and in code):
  1. KITCHEN_STAPLES below: what a home kitchen has besides the plants and animals of the variety list;
  2. every name and alias, in Hungarian and English, of every unit of variety_units.json (a unit is a kitchen ingredient by definition:
     chickpea, corn, sesame/tahini, lemon, garlic, olive oil ...).
  An ingredient that is on neither list is NOT a kitchen ingredient for this test (closed list); kitchenCheck() names it under "unknown" so that
  the list can be extended after a review, instead of the rule silently turning a food into a snack.
NOT_KITCHEN_MARKERS are checked first: an ingredient that contains one of them is not a kitchen ingredient, whatever else it contains.
Salt and sugar count as kitchen ingredients (Norbert, 2026-11-11). So plain caramel popcorn (corn, sugar, butter) comes out as gra.corn.corn;
that is the open question of the plan, the code does not decide it differently.
"""
import json
import os
import re
import unicodedata


def fold(s):
    """lower case, no accents, every run of other characters one space"""
    s = unicodedata.normalize('NFKD', str(s).lower())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


# ---------------------------------------------------------------------------------------------------------------------------------
# 1. the staples (head nouns; an ingredient that ENDS with one of them is that kitchen ingredient: répacukor, olívaolaj, csicseriborsóliszt)
KITCHEN_STAPLES = {
    'water': ['víz', 'water'],
    'salt': ['só', 'salt'],
    'sugar, honey, maple syrup': ['cukor', 'sugar', 'méz', 'honey', 'juharszirup', 'maple syrup'],
    'oils and fats': ['olaj', 'oil', 'vaj', 'butter', 'zsír', 'lard', 'ghee', 'margarin', 'margarine'],
    'eggs and dairy': ['tojás', 'egg', 'tej', 'milk', 'tejszín', 'cream', 'tejföl', 'sour cream', 'joghurt', 'yoghurt', 'yogurt', 'sajt', 'cheese', 'túró', 'quark', 'író', 'buttermilk'],
    'flour, starch, flakes': ['liszt', 'flour', 'keményítő', 'starch', 'dara', 'semolina', 'pehely', 'flakes'],
    'acids': ['ecet', 'vinegar', 'citromlé', 'lemon juice', 'limelé', 'lime juice'],
    'yeast': ['élesztő', 'yeast'],
    'plain foods whose English name the variety list spells differently': ['corn', 'popping corn'],   # the unit is called "maize" there
    'spices and herbs': [
        'bors', 'pepper', 'fahéj', 'cinnamon', 'kömény', 'cumin', 'koriander', 'coriander', 'kapor', 'dill', 'petrezselyem', 'parsley', 'bazsalikom', 'basil',
        'oregánó', 'oregano', 'rozmaring', 'rosemary', 'kakukkfű', 'thyme', 'majoránna', 'marjoram', 'zsálya', 'sage', 'menta', 'mint', 'szerecsendió', 'nutmeg',
        'szegfűszeg', 'clove', 'gyömbér', 'ginger', 'kurkuma', 'turmeric', 'kardamom', 'cardamom', 'ánizs', 'anise', 'csillagánizs', 'star anise',
        'édeskömény', 'fennel seed', 'édesgyökér', 'liquorice', 'vanília', 'vanilla', 'babérlevél', 'bay leaf', 'chili', 'chilli', 'cayenne', 'fűszerpaprika',
        'paprika', 'curry', 'sáfrány', 'saffron', 'mustár', 'mustard', 'lestyán', 'lovage', 'oregánó',
    ],
}
# ---------------------------------------------------------------------------------------------------------------------------------
# 2. NOT kitchen ingredients: a part of the ingredient (after folding) that makes it an additive, a flavouring or an industrial product
NOT_KITCHEN_MARKERS = [
    'aroma', 'aromak', 'flavour', 'flavor', 'izfokozo', 'flavour enhancer', 'izesito', 'izesitopor', 'szinezek', 'szinezo', 'colour', 'color', 'festek',
    'tartositoszer', 'tartosito', 'preservative', 'suritoanyag', 'suritoszer', 'suritett', 'thickener', 'stabilizator', 'stabilizalo', 'stabiliser', 'stabilizer',
    'emulgealoszer', 'emulgator', 'emulsifier', 'savanyusagot szabalyozo', 'savtartalom szabalyozo', 'acidity regulator', 'antioxidans', 'antioxidant',
    'zselesitoszer', 'gelling', 'edesitoszer', 'edesito', 'sweetener', 'csomosodasgatlo', 'anti caking', 'kenesgatlo', 'habzasgatlo', 'maltodextrin',
    'modositott kemenyito', 'modified starch', 'glukoz', 'glucose', 'fruktoz', 'fructose', 'izolatum', 'isolate', 'elesztokivonat', 'yeast extract',
    'citromsav', 'citric acid', 'aszkorbinsav', 'ascorbic acid', 'szorbat', 'sorbate', 'benzoat', 'benzoate', 'nitrit', 'nitrite', 'glutamat', 'glutamate',
    'izesitoporkeverek', 'por keverek',
]
NOT_KITCHEN_RE = re.compile(r'(?:^| )e ?\d{3,4}[a-z]?(?: |$)')   # an E-number: E 330, E330, E 150d
# words that only describe the form of an ingredient and are left out before the list is looked at
FORM_WORDS = {   # folded
    'bio', 'natur', 'natural', 'organic', 'extra', 'szuz', 'virgin', 'finomitatlan', 'unrefined', 'finomitott', 'refined', 'koncentratum', 'concentrate',
    'szaritott', 'dried', 'orolt', 'ground', 'friss', 'fresh', 'porkolt', 'roasted', 'hamozott', 'peeled', 'daralt', 'minced',
    'teljes', 'erteku', 'kiorlesu', 'whole', 'tengeri', 'sea',
}

_HERE = os.path.dirname(os.path.abspath(__file__))
_UNIT_TERMS = None


def _unitTerms():
    """folded names and aliases (hu and en) of every active unit and subgroup example of variety_units.json"""
    global _UNIT_TERMS
    if _UNIT_TERMS is None:
        with open(os.path.join(_HERE, '..', 'variety_units.json'), encoding='utf-8') as fh:
            data = json.load(fh)
        terms = set()
        for main in data['main']:
            if main['role'] != 'base':
                continue
            for sub in main['subs']:
                for u in sub.get('units', []):
                    if u['id'].endswith('.other') or u.get('deprecated'):
                        continue
                    for t in [u.get('hu'), u.get('en')] + list(u.get('a', [])):
                        if t:
                            terms.add(fold(t))
        _UNIT_TERMS = terms
    return _UNIT_TERMS


def _staples():
    out = set()
    for words in KITCHEN_STAPLES.values():
        out.update(fold(w) for w in words)
    return out


def _endsWithTerm(phrase, terms):
    """True when the folded phrase ends with a term. A term of 3 letters or fewer must be a whole word (so is "so" not the end of "kakaso"); a longer one may end a compound (répacukor)."""
    for t in terms:
        if not t:
            continue
        if len(t) <= 3:
            if phrase == t or phrase.endswith(' ' + t):
                return True
        elif phrase.endswith(t):
            return True
    return False


def splitIngredients(ingredients):
    """a list of texts, or one text 'a, b (c, d), 12 % e*' -> [(head, [sub items]) ...]; commas inside brackets do not split.
    Percentages, '*', footnote marks and a final dot are dropped. 'class: substance' ("sűrítőanyag: guarliszt") keeps both words in the head."""
    if ingredients is None:
        return []
    if isinstance(ingredients, (list, tuple)):
        text = ', '.join(str(x) for x in ingredients if x is not None)
    else:
        text = str(ingredients)
    text = re.sub(r'[*¹²³⁴⁵]+', '', text)
    text = re.sub(r'\d+(?:[.,]\d+)?\s*%', '', text)
    items, depth, cur = [], 0, ''
    for ch in text:
        if ch in '([':
            depth += 1
        elif ch in ')]':
            depth = max(0, depth - 1)
        if ch in ',;' and depth == 0:
            items.append(cur)
            cur = ''
        else:
            cur += ch
    items.append(cur)
    out = []
    for it in items:
        it = it.strip().strip('.').strip()
        if not it:
            continue
        m = re.match(r'^([^(]*)\((.*)\)\s*$', it)
        if m:
            out.append((m.group(1).strip(), splitIngredients(m.group(2))))
        else:
            out.append((it, []))
    return out


def _stripForm(phrase):
    words = [w for w in phrase.split() if w not in FORM_WORDS]
    return ' '.join(words)


def _judge(head, subs):
    """'ok' (a kitchen ingredient), 'bad' (an additive or flavouring) or 'unknown' (not on the closed list)"""
    f = fold(head)
    if NOT_KITCHEN_RE.search(f) or any(m in f for m in NOT_KITCHEN_MARKERS):
        return 'bad'
    if subs:   # an ingredient with its own parts (a spice mix, coconut milk with water): the parts decide
        verdicts = [_judge(h, s) for h, s in subs]
        if 'bad' in verdicts:
            return 'bad'
        return 'ok' if all(v == 'ok' for v in verdicts) else 'unknown'
    core = _stripForm(f)
    if ':' in head:   # "thickener: guar gum": the class word is the marker; it was not on the list above, so look at the substance only
        core = _stripForm(fold(head.split(':', 1)[1]))
    if not core:
        return 'unknown'
    if _endsWithTerm(core, _staples()) or _endsWithTerm(core, _unitTerms()):
        return 'ok'
    return 'unknown'


def kitchenCheck(ingredients):
    """{'ok': True | False | None, 'bad': [...], 'unknown': [...], 'items': n}; ok is None without any ingredient"""
    parts = splitIngredients(ingredients)
    if not parts:
        return {'ok': None, 'bad': [], 'unknown': [], 'items': 0}
    bad, unknown = [], []
    for head, subs in parts:
        v = _judge(head, subs)
        if v == 'bad':
            bad.append(head)
        elif v == 'unknown':
            unknown.append(head)
    return {'ok': not bad and not unknown, 'bad': bad, 'unknown': unknown, 'items': len(parts)}


def kitchenIngredientsOnly(ingredients):
    """True: only kitchen ingredients; False: at least one is not (an additive, a flavouring, or not on the closed list); None: no ingredient list"""
    return kitchenCheck(ingredients)['ok']


def popcornClass(ingredients):
    ok = kitchenIngredientsOnly(ingredients)
    return None if ok is None else ('gra.corn.corn' if ok else 'sna.corn')


def hummusClass(ingredients):
    ok = kitchenIngredientsOnly(ingredients)
    return None if ok is None else ('leg.chickpea-pea.chickpea' if ok else 'dis.legume-veg')


if __name__ == '__main__':   # python3 -I tools/variety_kitchen.py   prints the closed list for a review
    print('KITCHEN STAPLES (an ingredient that ends with one of these words is a kitchen ingredient)')
    for k, words in KITCHEN_STAPLES.items():
        print(f'  {k}: ' + ', '.join(words))
    print('\nALSO: every name and alias (Hungarian and English) of every unit of variety_units.json (%d terms)' % len(_unitTerms()))
    print('\nNOT KITCHEN (any ingredient that contains one of these, or an E-number):')
    print('  ' + ', '.join(NOT_KITCHEN_MARKERS))
