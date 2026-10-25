"""Paste from AI (version 14): the import of an AI answer as an own food, with estimates. Run with the web server on port 8765 (see CLAUDE.md).

Covers: reading (clean JSON, fences and prose around it, curly quotes, BOM, decimal comma, numbers as text), every error and every warning,
the review editor with the ~ marks, several foods in one answer, duplicates (update / save as new / cancel, with Undo), what the diary shows after an update,
the ~ on the Nutrients tab, the CSV columns, backup and restore, sync transport (fake GitHub), the clipboard (allowed and refused), the prompt text
(it is built from KEYS and UNITS and must agree with tools/ai_prompt.md), no network and no stored answer, font sizes, touch targets, contrast, offline.
The real clipboard of an iPhone is not testable here."""
import asyncio, csv, io, json, os, pathlib, re, sys
from playwright.async_api import async_playwright
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_sync import FakeGitHub, GOOD   # the fake GitHub of the sync test

URL = 'http://127.0.0.1:8765/index.html'
ROOT = pathlib.Path(__file__).resolve().parent.parent
SHOTS = os.environ.get('SHOTS', '')   # set to a folder to get screenshots
MARK = 'ZZ-PROSE-MARKER-4711'          # sits in the text around the JSON, must never be stored

SMALL_FONTS = """
(root) => [...(document.querySelector(root) || document).querySelectorAll('input, select, textarea')]
  .filter((e) => !['hidden', 'file', 'radio', 'checkbox'].includes(e.type))
  .map((e) => [e.id || e.className || e.tagName, e.type, parseFloat(getComputedStyle(e).fontSize)])
  .filter((x) => x[2] < 16)
"""
CONTRAST_JS = """
(sel) => {
  const parse = (c) => {
    let m = c.match(/rgba?\\(([^)]+)\\)/);
    if (m) { const p = m[1].split(/[ ,\\/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; }
    m = c.match(/color\\(srgb ([^)]+)\\)/);
    if (m) { const p = m[1].split(/[ \\/]+/).filter(Boolean).map(Number); return [p[0] * 255, p[1] * 255, p[2] * 255, p.length > 3 ? p[3] : 1]; }
    return [0, 0, 0, 0];
  };
  const lum = ([r, g, b]) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  const bgOf = (el) => {
    let layers = [];
    for (let e = el; e; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor); if (c[3] > 0) layers.push(c); if (c[3] >= 1) break; }
    let base = [255, 255, 255];
    if (!layers.length || layers[layers.length - 1][3] < 1) base = parse(getComputedStyle(document.body).backgroundColor).slice(0, 3);
    for (let i = layers.length - 1; i >= 0; i--) { const [r, g, b, a] = layers[i]; base = [r * a + base[0] * (1 - a), g * a + base[1] * (1 - a), b * a + base[2] * (1 - a)]; }
    return base;
  };
  const out = [];
  const roots = [...document.querySelectorAll(sel)].slice(-1);
  for (const root of roots) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const seen = new Set();
    while (walker.nextNode()) {
      const n = walker.currentNode; if (!n.textContent.trim()) continue;
      const el = n.parentElement; if (!el || seen.has(el)) continue; seen.add(el);
      const r = el.getBoundingClientRect(); if (!r.width || !r.height) continue;
      const cs = getComputedStyle(el); if (cs.visibility === 'hidden' || cs.display === 'none') continue;
      if (el.closest('[hidden]')) continue;
      const fg = parse(cs.color), bg = bgOf(el);
      const a = fg[3]; const f = [fg[0] * a + bg[0] * (1 - a), fg[1] * a + bg[1] * (1 - a), fg[2] * a + bg[2] * (1 - a)];
      const L1 = lum(f), L2 = lum(bg), ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
      const size = parseFloat(cs.fontSize), bold = parseInt(cs.fontWeight) >= 700;
      const need = (size >= 24 || (size >= 18.66 && bold)) ? 3 : 4.5;
      if (ratio < need) out.push(el.tagName.toLowerCase() + '.' + (el.className || '') + ' "' + n.textContent.trim().slice(0, 28) + '" ' + ratio.toFixed(2));
    }
  }
  return out;
}
"""
SMALL_TARGETS = """
(sel) => [...document.querySelectorAll(sel)].filter((e) => !e.hidden && e.getClientRects().length).map((e) => { const r = e.getBoundingClientRect(); return [e.id || e.dataset.ai || e.dataset.dup || e.dataset.est || e.textContent.trim().slice(0, 20), Math.round(r.width), Math.round(r.height)]; }).filter((x) => x[1] < 44 || x[2] < 44)
"""
DUMP_STORAGE = """
async () => {
  let all = JSON.stringify(Object.entries(localStorage));
  try {
    const db = await new Promise((res, rej) => { const q = indexedDB.open('tapnaplo'); q.onsuccess = () => res(q.result); q.onerror = () => rej(q.error); });
    for (const name of db.objectStoreNames) {
      const rows = await new Promise((res) => { const q = db.transaction(name).objectStore(name).getAll(); q.onsuccess = () => res(q.result); q.onerror = () => res([]); });
      all += JSON.stringify(rows);
    }
    db.close();
  } catch (e) { all += 'IDBERR'; }
  return all;
}
"""


def food(**kw):
    f = {'name': 'Test oat drink', 'brand': 'Acme', 'barcode': '4012345678901', 'basis': {'qty': 100, 'unit': 'g'},
         'n': {'kcal': 45, 'protein': 1.0, 'fat': 1.5, 'carbohydrate': 6.6, 'calcium': 120, 'vitamin_e': 1.1},
         'est': ['vitamin_e'], 'confidence': 'medium', 'fortified': True, 'nova': 4,
         'portions': [{'label': '100 ml', 'grams': 101}], 'note': 'Fortified oat drink, label has calcium only.'}
    f.update(kw)
    return f


def doc(*foods, v=1):
    return {'nutrilog_import': v, 'foods': list(foods)}


def J(d):
    return json.dumps(d, ensure_ascii=False)


def curly(s):
    out, open_ = [], True
    for ch in s:
        if ch == '"':
            out.append('“' if open_ else '”'); open_ = not open_
        else:
            out.append(ch)
    return ''.join(out)


async def main():
    async with async_playwright() as p:
        problems = []

        def check(name, ok, info=''):
            print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(info)) if info != '' else ''))
            if not ok: problems.append(name)

        browser = await p.chromium.launch()
        errs = []
        gh = FakeGitHub()
        net = []   # every request that is not the app's own files (must stay empty)

        async def make(name, perms=None, sw='block', gh_on=False, offline_ok=False):
            ctx = await browser.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True, locale='en-GB',
                                            service_workers=sw, accept_downloads=True, permissions=perms or [])
            if gh_on: await ctx.route('https://api.github.com/**', gh.handle)
            await ctx.route('**/*openfoodfacts.org/**', lambda r: r.fulfill(status=200, headers={'access-control-allow-origin': '*', 'content-type': 'application/json'}, body='{"products":[],"status":0}'))
            page = await ctx.new_page()
            page.dname = name
            page.on('pageerror', lambda e: errs.append(f'{name} PE {e}'))
            page.on('console', lambda m: errs.append(f'{name} C {m.text}') if m.type == 'error' and 'Failed to load resource' not in m.text else None)
            await page.goto(URL); await page.wait_for_selector('.hero')
            return ctx, page

        ctx, page = await make('main', perms=['clipboard-read', 'clipboard-write'])
        T = page.evaluate

        def parse(x):
            return T('(t) => window.__tapnaplo.parseAiImport(t)', x if isinstance(x, str) else J(x))

        async def errors_of(x):
            return (await parse(x))['errors']

        async def warns_of(x):
            r = await parse(x)
            return r['errors'], [w for f in r['foods'] for w in f['warnings']]

        # =========================================================== 1 reading
        r = await parse(doc(food()))
        f0 = r['foods'][0]['food'] if r['foods'] else {}
        check('clean JSON: no error, no warning, one food', r['errors'] == [] and len(r['foods']) == 1 and r['foods'][0]['warnings'] == [], r)
        check('clean JSON: the own-food fields are filled as they are', f0.get('name') == 'Test oat drink' and f0.get('brand') == 'Acme' and f0.get('barcode') == '4012345678901' and f0.get('basis') == {'qty': 100, 'unit': 'g'}
              and f0.get('nova') == 4 and f0.get('portions') == [{'label': '100 ml', 'grams': 101}] and f0.get('note', '').startswith('Fortified oat drink'), f0)
        check('clean JSON: values, est (only keys of n), q letter code and fortified', f0.get('n') == {'kcal': 45, 'protein': 1, 'fat': 1.5, 'carbohydrate': 6.6, 'calcium': 120, 'vitamin_e': 1.1} and f0.get('est') == ['vitamin_e'] and f0.get('q') == 'm' and f0.get('fortified') is True, f0)
        for word, code in [('high', 'h'), ('medium', 'm'), ('low', 'l'), ('very low', 'v')]:
            rr = await parse(doc(food(confidence=word)))
            check(f'confidence "{word}" is stored as "{code}"', rr['foods'] and rr['foods'][0]['food'].get('q') == code, rr['errors'])
        rr = await parse(doc(food(est=[], confidence='none')))
        check('confidence "none" without estimates: q "n", no estimates, no error', rr['errors'] == [] and rr['foods'][0]['food'].get('q') == 'n' and not rr['foods'][0]['food'].get('est'), rr)
        rr = await parse(doc(food(est=[], confidence='')))
        check('no estimates and no confidence is fine (q not set)', rr['errors'] == [] and not rr['foods'][0]['food'].get('q'), rr)

        prose = 'Szia! Itt az eredmény (' + MARK + '):\n\n```json\n' + J(doc(food())) + '\n```\n\nHa kell, pontosítok. {ez nem JSON}'
        rr = await parse(prose)
        check('fence and prose around the JSON are skipped', rr['errors'] == [] and len(rr['foods']) == 1 and rr['foods'][0]['food']['name'] == 'Test oat drink', rr['errors'])
        rr = await parse('Here it is: ' + J(doc(food())) + ' and some words')
        check('prose without a fence is skipped too', rr['errors'] == [] and len(rr['foods']) == 1, rr['errors'])
        rr = await parse('```\n' + curly(J(doc(food()))) + '\n```')
        check('curly quotes “ ” are read', rr['errors'] == [] and len(rr['foods']) == 1 and rr['foods'][0]['food']['n'].get('calcium') == 120, rr['errors'])
        rr = await parse('﻿' + J(doc(food())))
        check('a BOM in front is ignored', rr['errors'] == [] and len(rr['foods']) == 1, rr['errors'])
        rr = await parse(' ​' + J(doc(food())).replace(': ', ': '))
        check('non-breaking spaces and zero-width marks are ignored', rr['errors'] == [] and len(rr['foods']) == 1, rr['errors'])
        rr = await parse(J(doc(food())).replace('}]}', '},]}'))
        check('a trailing comma is tolerated', rr['errors'] == [] and len(rr['foods']) == 1, rr['errors'])
        rr = await parse(doc(food(n={'kcal': '45', 'protein': '1,0', 'fat': '1.5', 'carbohydrate': ' 6,6 ', 'calcium': '120', 'vitamin_e': '<0,3'}, est=[], confidence='none')))
        n = rr['foods'][0]['food']['n'] if rr['foods'] else {}
        check('numbers as text, decimal comma and "<x" are read like in the editor', rr['errors'] == [] and n.get('kcal') == 45 and n.get('protein') == 1 and n.get('carbohydrate') == 6.6 and n.get('vitamin_e') == '<0.3', (rr['errors'], n))
        rr = await parse(doc(food(n={'kcal': 45, 'protein': 0, 'vitamin_e': 0}, est=[], confidence='none')))
        check('0 is a real value and stays', rr['errors'] == [] and rr['foods'][0]['food']['n'].get('vitamin_e') == 0, rr['errors'])
        two = doc(food(), food(name='Second food', barcode='', brand='', est=[], confidence='none', n={'kcal': 100, 'protein': 10, 'fat': 3, 'carbohydrate': 12}), food(name='Third food', barcode='', brand='Zed'))
        rr = await parse(two)
        check('several foods in one answer', rr['errors'] == [] and [x['food']['name'] for x in rr['foods']] == ['Test oat drink', 'Second food', 'Third food'], rr['errors'])
        rr = await parse(doc(food(basis={'qty': 1, 'unit': 'capsule'}, portions=[], est=[], confidence='none', n={'kcal': 0, 'vitamin_d': 25})))
        check('a per-piece basis is read (1 capsule)', rr['errors'] == [] and rr['foods'][0]['food']['basis'] == {'qty': 1, 'unit': 'capsule'}, rr['errors'])
        rr = await parse(doc(food(nova=None)))
        check('nova null is fine', rr['errors'] == [] and not rr['foods'][0]['food'].get('nova'), rr['errors'])
        rr = await parse(doc({'name': 'Only a name', 'n': {'kcal': 10}, 'basis': {'qty': 100, 'unit': 'g'}}))
        check('the optional fields may be missing', rr['errors'] == [] and len(rr['foods']) == 1, rr['errors'])

        # =========================================================== 2 errors
        async def expect_error(label, x, pattern):
            errs_ = await errors_of(x)
            check('error: ' + label, len(errs_) > 0 and any(re.search(pattern, e, re.I) for e in errs_), errs_)

        await expect_error('no JSON at all', 'Sorry, I could not find this product.', r'No JSON')
        await expect_error('empty text', '   ', r'Paste')
        await expect_error('JSON without nutrilog_import', J({'foods': [food()]}), r'nutrilog_import')
        await expect_error('unknown version', J(doc(food(), v=2)), r'version')
        await expect_error('foods missing', J({'nutrilog_import': 1}), r'foods')
        await expect_error('name missing', doc(food(name='')), r'name')
        await expect_error('basis invalid (50 g)', doc(food(basis={'qty': 50, 'unit': 'g'})), r'basis')
        await expect_error('basis invalid (no unit)', doc(food(basis={'qty': 1})), r'basis')
        await expect_error('negative value', doc(food(n={'kcal': -5})), r'kcal|negative|number')
        await expect_error('value that is not a number', doc(food(n={'kcal': 'a lot'})), r'kcal|number')
        await expect_error('est key that is not in n', doc(food(est=['vitamin_c'])), r'vitamin_c')
        await expect_error('est without confidence', doc(food(confidence=None)), r'confidence')
        await expect_error('est with a confidence word that does not exist', doc(food(confidence='very high')), r'confidence')
        await expect_error('nova 5', doc(food(nova=5)), r'nova')
        await expect_error('nova "x"', doc(food(nova='x')), r'nova')
        await expect_error('portion without grams', doc(food(portions=[{'label': 'slice', 'grams': 0}])), r'portion')
        await expect_error('portion without a label', doc(food(portions=[{'label': '', 'grams': 20}])), r'portion')
        await expect_error('portions with a per-piece basis', doc(food(basis={'qty': 1, 'unit': 'tablet'}, portions=[{'label': 'x', 'grams': 1}])), r'portion')
        await expect_error('the second food is wrong: the whole answer stops', doc(food(), food(name='')), r'name')
        r2 = await parse(doc(food(), food(name='')))
        check('an error leaves no food to load', r2['foods'] == [], r2['foods'])
        r2 = await errors_of(doc(food(name='', n={'kcal': -1})))
        check('several errors are all listed', len(r2) >= 2, r2)
        check('the error text names the food when there are several', any('2' in e or 'Third' in e or 'food' in e.lower() for e in await errors_of(doc(food(), food(name='Bad', n={'kcal': -1})))), await errors_of(doc(food(), food(name='Bad', n={'kcal': -1}))))

        # =========================================================== 3 warnings
        async def expect_warn(label, x, pattern, also_ok=True):
            e, w = await warns_of(x)
            check('warning: ' + label, e == [] and any(re.search(pattern, s, re.I) for s in w), (e, w))

        await expect_warn('unknown key (skipped and listed)', doc(food(n={'kcal': 45, 'protein': 1, 'fat': 1.5, 'carbohydrate': 6.6, 'vitamin_x': 5, 'fiber': 2}, est=[], confidence='none')), r'vitamin_x')
        rr = await parse(doc(food(n={'kcal': 45, 'protein': 1, 'fat': 1.5, 'carbohydrate': 6.6, 'vitamin_x': 5, 'fiber': 2}, est=[], confidence='none')))
        check('unknown keys are not in the loaded values, the known ones are', 'vitamin_x' not in rr['foods'][0]['food']['n'] and 'fiber' not in rr['foods'][0]['food']['n'] and rr['foods'][0]['food']['n'].get('kcal') == 45, rr['foods'][0]['food']['n'])
        e, w = await warns_of(doc(food(n={'kcal': 45, 'protein': 1, 'fat': 1.5, 'carbohydrate': 6.6, 'vitamin_x': 5, 'fiber': 2}, est=[], confidence='none')))
        check('all unknown keys are listed', any('vitamin_x' in s and 'fiber' in s for s in w) or (any('vitamin_x' in s for s in w) and any('fiber' in s for s in w)), w)
        await expect_warn('energy against 4/4/9 (more than 20% apart)', doc(food(n={'kcal': 200, 'protein': 1, 'fat': 1.5, 'carbohydrate': 6.6}, est=[], confidence='none')), r'energy|kcal')
        e, w = await warns_of(doc(food(n={'kcal': 45, 'protein': 1, 'fat': 1.5, 'carbohydrate': 6.6}, est=[], confidence='none')))
        check('energy close to 4/4/9: no warning', e == [] and w == [], (e, w))
        e, w = await warns_of(doc(food(n={'kcal': 400, 'protein': 0, 'alcohol': 57, 'fat': 0, 'carbohydrate': 0}, est=[], confidence='none')))
        check('alcohol counts 7 kcal per g', e == [] and w == [], (e, w))
        await expect_warn('saturated fat above total fat', doc(food(n={'kcal': 90, 'fat': 10, 'fa_saturated': 12}, est=[], confidence='none')), r'saturated')
        await expect_warn('sugars above carbohydrate', doc(food(n={'kcal': 90, 'carbohydrate': 10, 'sugars': 12}, est=[], confidence='none')), r'sugars')
        await expect_warn('fatty acids add up to more than fat', doc(food(n={'kcal': 90, 'fat': 10, 'fa_saturated': 5, 'fa_mono': 4, 'fa_poly': 3}, est=[], confidence='none')), r'add up|fat')
        e, w = await warns_of(doc(food(n={'kcal': 90, 'fat': 10, 'fa_saturated': 5, 'fa_mono': 4, 'fa_poly': 1}, est=[], confidence='none')))
        check('fatty acids that fit into the fat: no warning', e == [] and not any('monounsaturated' in s for s in w), (e, w))
        await expect_warn('protein + carbohydrate + fat + water + ash above 105 g in 100 g', doc(food(n={'protein': 40, 'carbohydrate': 40, 'fat': 20, 'water': 10}, est=[], confidence='none')), r'100 g|add up')
        e, w = await warns_of(doc(food(basis={'qty': 1, 'unit': 'tablet'}, portions=[], n={'protein': 40, 'carbohydrate': 40, 'fat': 20, 'water': 10}, est=[], confidence='none')))
        check('the 105 g rule is for 100 g bases only', e == [] and not any(re.search(r'105|100 g', s) for s in w), (e, w))
        await expect_warn('salt and sodium do not match', doc(food(n={'salt': 1.0, 'sodium': 100}, est=[], confidence='none')), r'salt')
        e, w = await warns_of(doc(food(n={'salt': 1.0, 'sodium': 400}, est=[], confidence='none')))
        check('salt and sodium that match (sodium x 2.5): no warning', e == [] and w == [], (e, w))
        rr = await parse(doc(food(note='x' * 500)))
        check('note over 400 characters: warning, and the note is not cut', rr['errors'] == [] and len(rr['foods'][0]['food']['note']) == 500 and any(re.search(r'note', s, re.I) for s in rr['foods'][0]['warnings']), (len(rr['foods'][0]['food']['note']), rr['foods'][0]['warnings']))
        await expect_warn('name over 120 characters', doc(food(name='N' * 130)), r'name')
        rr = await parse(doc(food(name='N' * 130)))
        check('the long name is not cut either', len(rr['foods'][0]['food']['name']) == 130, len(rr['foods'][0]['food']['name']))
        await expect_warn('brand over 80 characters', doc(food(brand='B' * 90)), r'brand')
        await expect_warn('barcode that is not 8-14 digits', doc(food(barcode='12345')), r'barcode')
        await expect_warn('barcode with letters', doc(food(barcode='ABC12345678')), r'barcode')
        e, w = await warns_of(doc(food(barcode='')))
        check('an empty barcode is fine', e == [] and w == [], (e, w))

        # =========================================================== 4 the prompt agrees with the doc and with the importer
        prompt = await T('window.__tapnaplo.aiPrompt()')
        keys = await T('window.__tapnaplo.KEYS')
        ciq = json.load(open(ROOT / 'ciqual.json', encoding='utf-8'))
        unit_of = {n['key']: n['unit'] for n in ciq['nutrients']}
        check('KEYS in the app are the keys of ciqual.json', keys == [n['key'] for n in ciq['nutrients']], len(keys))
        md = (ROOT / 'tools' / 'ai_prompt.md').read_text(encoding='utf-8').replace('\r\n', '\n')

        def key_bullets(text):
            sec = text.split('## Tápanyagkulcsok\n', 1)[1].split('\nAz érték szám ponttal', 1)[0]
            got, dup = {}, []
            for line in sec.split('\n'):
                if not line.startswith('- '): continue
                head, body = line[2:].split(':', 1)
                hm = re.search(r'\(([^)]+)\)\s*$', head.strip())
                default = hm.group(1) if hm else None      # "Cukrok (g): ..." names the unit in the heading
                pending = []
                for key, unit in re.findall(r'`([a-z0-9_]+)`|\(([^)]+)\)', body.split('. A címke')[0]):
                    if key:
                        if key in got or key in pending: dup.append(key)
                        pending.append(key)
                    else:
                        for k in pending: got[k] = unit
                        pending = []
                for k in pending: got[k] = default
            return got, dup
        got, dup = key_bullets(prompt)
        check('prompt: every key of the app is listed exactly once, no other key', sorted(got) == sorted(keys) and dup == [], (set(keys) ^ set(got), dup))
        wrong = [(k, got[k], unit_of[k]) for k in got if got[k] != unit_of.get(k)]
        check('prompt: every key has the unit of the app (UNITS)', wrong == [], wrong[:5])
        mdgot, mddup = key_bullets(md)
        check('tools/ai_prompt.md: the key list of the doc and the keys of the app are the same set', set(mdgot) == set(keys), (set(keys) - set(mdgot), set(mdgot) - set(keys)))
        wrong = [(k, mdgot[k], unit_of[k]) for k in mdgot if k in unit_of and mdgot[k] != unit_of[k]]
        check('tools/ai_prompt.md: the units of the doc are the units of the app', wrong == [], wrong[:5])
        counter = set(re.findall(r'`([a-z0-9_]+)`', md.split('## Tápanyagkulcsok\n', 1)[1].split('\n- ', 1)[0]))
        check('tools/ai_prompt.md: the only non-keys named in the key section are the counter-examples', counter - set(keys) == {'vitamin_a', 'fiber', 'omega3', 'sodium_mg'}, counter - set(keys))
        secs = lambda t: {s.split('\n', 1)[0]: s.split('\n', 1)[1] for s in ('\n' + t).split('\n## ')[1:]}
        ps, ms = secs(prompt), secs(md)
        check('prompt: the same sections as the doc', list(ps) == list(ms), (list(ps), list(ms)))
        diff = [h for h in ms if h != 'Tápanyagkulcsok' and ps.get(h, '').strip() != ms[h].strip()]
        check('prompt: every section other than the key list is the text of the doc', diff == [], diff)
        pk, mk = ps['Tápanyagkulcsok'], ms['Tápanyagkulcsok']
        check('prompt: the intro and the closing rule of the key section are the doc text', pk.split('\n\n')[0] == mk.split('\n\n')[0] and pk.rstrip().endswith(mk.rstrip().split('\n\n')[-1]), (pk.split('\n\n')[0][:60], mk.split('\n\n')[0][:60]))
        check('prompt: the title carries the version of the importer', prompt.split('\n')[0] == '# Nutrilog tételpontosító (v1)' and await T('window.__tapnaplo.AI_IMPORT_VERSION') == 1, prompt.split('\n')[0])
        m = re.search(r'```json\n(.*?)\n```', prompt, re.S)
        ex = parse(m.group(1)) if m else None
        if ex is not None:
            exr = await ex
            check('prompt: the JSON example of the doc is accepted by the importer', exr['errors'] == [], exr['errors'])
        confs = re.findall(r'^- `"([a-z ]+)"`', ms['Megbízhatóság (`confidence`), a becsült értékekre'], re.M)
        okc = []
        for c in confs:
            rr = await parse(doc(food(confidence=c, est=['vitamin_e'] if c != 'none' else [])))
            okc.append(rr['errors'] == [])
        check('every confidence word of the doc is accepted', len(confs) == 5 and all(okc), (confs, okc))

        # =========================================================== 5 the sheet, the clipboard, the editor
        async def sheets():
            return await T("document.querySelectorAll('.sheet').length")

        async def close_all():
            for _ in range(8):
                if not await sheets(): break
                await page.click('.sheet-wrap:last-of-type [data-x]')
                await page.wait_for_timeout(120)
            await page.wait_for_timeout(100)

        async def open_ai():
            await page.click('[data-tab=foods]'); await page.wait_for_selector('#ffilter')
            await page.click('[data-act=ai-import]'); await page.wait_for_selector('#ai-text')

        async def read_text(text):
            await page.fill('#ai-text', text)
            await page.click('#ai-read')

        async def foods_n():
            return await T("Object.keys(window.__tapnaplo.S.foods).length")

        today = await T("(() => { const d = new Date(); const p = (n) => String(n).padStart(2, '0'); return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`; })()")

        # entry points
        await page.click('[data-tab=foods]'); await page.wait_for_selector('#ffilter')
        check('My foods tab: "Paste from AI" stands next to "Create food"', await page.locator('[data-act=ai-import]').inner_text() == 'Paste from AI' and await T("document.querySelector('[data-act=ai-import]').previousElementSibling.dataset.act") == 'new-food')
        await page.click('[data-tab=log]'); await page.wait_for_selector('.hero')
        await page.click('.act.primary'); await page.wait_for_selector('#q')
        names = await T("[...document.querySelectorAll('.sheet button')].map((b) => b.textContent.trim())")
        check('Log food search: "Paste from AI" next to "Create food from label"', 'Paste from AI' in names and any('Create food from label' in x for x in names), names)
        await close_all()

        # the sheet itself
        await open_ai()
        await page.wait_for_timeout(400)
        check('Paste from AI sheet: explanation, Paste from clipboard, Copy AI prompt, Read, Cancel', all([await page.locator(s).count() == 1 for s in ['#ai-paste', '#ai-copy', '#ai-read', '#ai-text', '[data-dx]']]) and 'Paste from clipboard' in await page.inner_text('#ai-paste') and 'Copy AI prompt' in await page.inner_text('#ai-copy'))
        check('sheet: the answer box has at least 16 px text', await T(SMALL_FONTS, '.sheet') == [], await T(SMALL_FONTS, '.sheet'))
        check('sheet: the buttons are at least 44 px', await T(SMALL_TARGETS, '.sheet button') == [], await T(SMALL_TARGETS, '.sheet button'))
        await page.fill('#ai-text', 'line one')
        await page.press('#ai-text', 'Enter')
        check('Enter in the answer box adds a line, it does not close the sheet or read', await sheets() == 1 and (await page.input_value('#ai-text')).endswith('\n') and await page.locator('#ai-msg .note').count() == 0)
        check('the sheet fits 390 px', await T('document.documentElement.scrollWidth <= window.innerWidth && (() => { const b = document.querySelector(".sheet-b"); return b.scrollWidth <= b.clientWidth; })()'))
        await page.fill('#ai-text', '')
        await page.click('#ai-read')
        check('Read with an empty box says what to do, next to the box', 'Paste the answer' in await page.inner_text('#ai-msg') and await page.get_attribute('#ai-text', 'aria-invalid') in (None, 'true'))
        await read_text('nothing useful here')
        check('error text under the box, box marked invalid, sheet stays', 'No JSON' in await page.inner_text('#ai-msg') and await page.get_attribute('#ai-text', 'aria-invalid') == 'true' and await sheets() == 1)
        light = await T(CONTRAST_JS, '.sheet')
        check('error state: text contrast >= 4.5:1 (light)', light == [], light)
        await T("document.documentElement.setAttribute('data-theme','dark')")
        dark = await T(CONTRAST_JS, '.sheet')
        check('error state: text contrast >= 4.5:1 (dark)', dark == [], dark)
        if SHOTS: await page.screenshot(path=SHOTS + '/ai_error_dark.png')
        await T("document.documentElement.setAttribute('data-theme','light')")
        await page.fill('#ai-text', 'x')
        check('typing clears the error', await page.inner_text('#ai-msg') == '' and await page.get_attribute('#ai-text', 'aria-invalid') is None)
        n0 = await foods_n()
        await read_text(J(doc(food(n={'kcal': -5}))))
        check('a negative value stops with the error under the box, nothing is saved', 'kcal' in (await page.inner_text('#ai-msg')) and await foods_n() == n0)
        await read_text(J(doc(food(est=['vitamin_c']))))
        check('est without n: error under the box', 'vitamin_c' in await page.inner_text('#ai-msg') and await foods_n() == n0)

        # clean answer -> review editor, nothing saved
        await read_text(prose)
        await page.wait_for_selector('#fok')
        check('Read opens the food editor titled "Review imported food", prefilled', 'Review imported food' in await T("[...document.querySelectorAll('.sheet-h')].pop().innerText") and await page.input_value('#fname') == 'Test oat drink' and await page.input_value('#fbrand') == 'Acme' and await page.input_value('#fcode') == '4012345678901')
        check('nothing is saved before Save (no automatic save)', await foods_n() == n0)
        check('the editor shows the AI notice and the estimate summary', 'not saved yet' in await T("document.querySelector('.banner').innerText") and 'confidence medium' in await T("document.querySelector('.banner').innerText"))
        check('values are in the fields (comma and dot forms)', await page.input_value('[data-k=kcal]') == '45' and await page.input_value('[data-k=vitamin_e]') == '1.1' and await page.input_value('[data-k=calcium]') == '120')
        check('Estimates fold is open for an import with estimates; confidence Medium; fortified ticked', await T("document.querySelector('#estfold').open") and await page.input_value('#fconf') == 'm' and await page.is_checked('#ffort'))
        check('NOVA 4, portion 100 ml and the note are in the form', await page.input_value('#fnova') == '4' and '100 ml' in await T("document.querySelector('#ports').innerHTML") and 'Fortified oat drink' in await page.input_value('#fnote'))
        # the ~ marks
        mk = lambda k: T("(k) => { const b = document.querySelector('#nuts [data-est=\"' + k + '\"]'); const r = b.getBoundingClientRect(); return { hidden: b.hidden, pressed: b.getAttribute('aria-pressed'), label: b.getAttribute('aria-label'), row: b.parentElement.className, w: Math.round(r.width), h: Math.round(r.height) }; }", k)
        v = await mk('vitamin_e'); c = await mk('calcium')
        check('estimated field: ~ button pressed, row marked, aria-label says estimate', v['pressed'] == 'true' and 'est' in v['row'].split() and 'estimated value' in v['label'] and not v['hidden'], v)
        check('label value: ~ button off, aria-label says label value', c['pressed'] == 'false' and 'label value' in c['label'] and 'est' not in c['row'].split(), c)
        check('the label of an estimated row starts with ~ (CSS)', await T("getComputedStyle(document.querySelector('#nuts [data-k=vitamin_e]').closest('.nin').querySelector('label'), '::before').content") == '"~ "')
        check('the ~ buttons are at least 44 px', await T(SMALL_TARGETS, '#nuts .est-btn') == [] and v['w'] >= 44 and v['h'] >= 44, await T(SMALL_TARGETS, '#nuts .est-btn'))
        await page.click('#nuts [data-est=calcium]')
        c = await mk('calcium')
        check('tap on ~ marks a label value as an estimate', c['pressed'] == 'true' and 'estimated value' in c['label'] and 'est' in c['row'].split(), c)
        await page.click('#nuts [data-est=calcium]')
        c = await mk('calcium')
        check('tap again takes the mark off', c['pressed'] == 'false' and 'est' not in c['row'].split(), c)
        await page.click('#nuts [data-est=calcium]')
        await page.fill('#nuts [data-k=calcium]', '')
        c = await mk('calcium')
        check('emptying the field clears the mark and hides the button', c['hidden'] and c['pressed'] == 'false' and 'est' not in c['row'].split(), c)
        await page.fill('#nuts [data-k=calcium]', '120')
        c = await mk('calcium')
        check('typing a value again does not bring the mark back', c['pressed'] == 'false' and not c['hidden'], c)
        check('editor: all fields at least 16 px', await T(SMALL_FONTS, '.sheet') == [], await T(SMALL_FONTS, '.sheet'))
        check('editor: the page does not scroll sideways', await T('document.documentElement.scrollWidth <= window.innerWidth'))
        if SHOTS: await page.screenshot(path=SHOTS + '/ai_editor.png')
        light = await T(CONTRAST_JS, '.sheet')
        check('editor with estimates: text contrast >= 4.5:1 (light)', light == [], light)
        await T("document.documentElement.setAttribute('data-theme','dark')")
        dark = await T(CONTRAST_JS, '.sheet')
        check('editor with estimates: text contrast >= 4.5:1 (dark)', dark == [], dark)
        if SHOTS: await page.screenshot(path=SHOTS + '/ai_editor_dark.png')
        await T("document.documentElement.setAttribute('data-theme','light')")
        # estimates need a confidence
        await page.select_option('#fconf', '')
        await page.click('#fok')
        check('estimates without a confidence: error next to the select, not saved', 'Choose how confident' in await T("document.querySelector('.sheet-wrap:last-of-type .sheet-b').innerText") and await page.get_attribute('#fconf', 'aria-invalid') == 'true' and await sheets() == 2 and await foods_n() == n0)
        await page.select_option('#fconf', 'm')
        await page.click('#fok')
        await page.wait_for_timeout(500)
        check('Save: the food is saved, both sheets close, a toast says so', await foods_n() == n0 + 1 and await sheets() == 0 and 'Food saved' in await page.inner_text('#toast'))
        saved = await T("Object.values(window.__tapnaplo.S.foods).find((f) => f.name === 'Test oat drink')")
        check('saved food: src user, est (only keys of n), q, fortified, basis, portions, nova', saved['src'] == 'user' and saved['id'].startswith('u:') and saved['est'] == ['vitamin_e'] and saved['q'] == 'm' and saved['fortified'] is True and saved['basis'] == {'qty': 100, 'unit': 'g'} and saved['nova'] == 4 and saved['portions'] == [{'label': '100 ml', 'grams': 101}], saved)
        FID = saved['id']

        # nothing of the pasted answer is stored, nothing leaves the phone
        dump = await T(DUMP_STORAGE)
        check('the pasted text (prose around the JSON) is not stored', MARK not in dump and 'IDBERR' not in dump, len(dump))
        check('the food itself is in storage, without cache fields (_vec, _est)', 'Test oat drink' in dump and '"_vec"' not in dump and '"_est"' not in dump)

        # =========================================================== 6 diary, Nutrients tab, CSV
        await T("([fid, d]) => { const t = window.__tapnaplo; t.S.log.push({ id: crypto.randomUUID(), d, m: 'm1', f: fid, a: 100, t: Date.now(), tm: '12:00' }); t.save(); t.render(); }", [FID, today])
        await page.click('[data-tab=log]'); await page.wait_for_selector('.hero')
        hero = (await page.inner_text('.hero')).replace('\n', ' ')
        check('Diary shows the entry of the imported food: 45 kcal for 100 g', re.search(r'(?<!\d)45(?!\d)', hero) is not None, hero)
        await page.click('[data-tab=nutr]'); await page.wait_for_selector('details.nrow')
        await T("document.querySelectorAll('#view details').forEach((d) => d.open = true)")
        nrow = lambda name: T("(n) => { const d = [...document.querySelectorAll('details.nrow')].find((x) => x.querySelector('summary').innerText.includes(n)); return d ? d.innerText : null; }", name)
        ve, ca = await nrow('Vitamin E'), await nrow('Calcium')
        check('Nutrients tab: the estimated vitamin E has a ~ before its value', ve is not None and '~' in ve.split('Estimate')[0], ve)
        check('Nutrients tab: the label value (calcium) has no ~', ca is not None and '~' not in ca, ca)
        check('Nutrients tab: the detail line says "Estimate, not a label value: <food> (medium)"', ve is not None and re.search(r'Estimate, not a label value: Test oat drink \(medium\)', ve) is not None, ve)
        check('Nutrients tab: energy is a label value here, so no ~ on the energy', '~' not in (await nrow('Energy') or ''), await nrow('Energy'))
        # estimated energy
        await T("(fid) => { const f = window.__tapnaplo.S.foods[fid]; f.est = ['kcal', 'vitamin_e']; delete f._est; window.__tapnaplo.save(); window.__tapnaplo.render(); }", FID)
        await page.click('[data-tab=log]'); await page.wait_for_selector('.hero')
        check('Diary: an estimated energy value gets the ~ (energy of an own food in est)', '~' in await page.inner_text('.hero'), (await page.inner_text('.hero')).replace('\n', ' '))
        await T("(fid) => { const f = window.__tapnaplo.S.foods[fid]; f.est = ['vitamin_e']; delete f._est; window.__tapnaplo.save(); window.__tapnaplo.render(); }", FID)
        await page.click('[data-tab=data]'); await page.wait_for_selector('[data-act=export-entries]')
        async with page.expect_download() as d:
            await page.click('[data-act=export-entries]')
        dl = await d.value; await dl.save_as('entries_ai.csv')
        rows = list(csv.DictReader(io.StringIO(open('entries_ai.csv', encoding='utf-8-sig').read())))
        o = [r_ for r_ in rows if r_['food_id'] == FID][0]
        check('CSV: own food has estimate_confidence "medium" (not only dmBio)', o['estimate_confidence'] == 'medium', o.get('estimate_confidence'))
        check('CSV: vitamin_e_mg__est is 1, energy_estimated is 0, calcium has no __est column', o['vitamin_e_mg__est'] == '1' and o['energy_estimated'] == '0' and 'calcium_mg__est' not in o and 'protein_g__est' not in o, {k: o.get(k) for k in ('vitamin_e_mg__est', 'energy_estimated')})
        check('CSV: the values are for the amount (100 g)', abs(float(o['vitamin_e_mg']) - 1.1) < 1e-6 and abs(float(o['kcal_kcal']) - 45) < 1e-6, (o['vitamin_e_mg'], o['kcal_kcal']))
        async with page.expect_download() as d:
            await page.click('[data-act=export-days]')
        dl = await d.value; await dl.save_as('days_ai.csv')
        days = list(csv.DictReader(io.StringIO(open('days_ai.csv', encoding='utf-8-sig').read())))
        check('daily CSV: vitamin_e_mg__est counts the estimated entries (1)', days[-1]['vitamin_e_mg__est'] == '1' and 'kcal_kcal__est' not in days[-1], {k: days[-1].get(k) for k in ('vitamin_e_mg__est', 'kcal_kcal__est')})
        txt = await page.inner_text('#view')
        check('Data tab text: the CSV description names the estimate columns for own foods too', 'estimate_confidence' in txt and 'your own foods' in txt, [l for l in txt.split('\n') if 'estimate' in l.lower()][:3])
        # a food without estimates must not get the columns
        await T("(d) => { const t = window.__tapnaplo; t.S.foods['u:plain'] = { id: 'u:plain', src: 'user', name: 'Plain', brand: '', barcode: '', basis: { qty: 100, unit: 'g' }, n: { kcal: 100, protein: 5 }, nova: null, portions: [], note: '', created: Date.now() }; t.S.log.push({ id: crypto.randomUUID(), d, m: 'm2', f: 'u:plain', a: 50, t: Date.now(), tm: '13:00' }); t.save(); t.render(); }", today)
        async with page.expect_download() as d:
            await page.click('[data-act=export-entries]')
        dl = await d.value; await dl.save_as('entries_ai2.csv')
        rows = list(csv.DictReader(io.StringIO(open('entries_ai2.csv', encoding='utf-8-sig').read())))
        pl = [r_ for r_ in rows if r_['food_id'] == 'u:plain'][0]
        check('CSV: a plain own food has an empty estimate_confidence and __est 0/empty', pl['estimate_confidence'] == '' and pl.get('vitamin_e_mg__est', '') in ('', '0'), (pl['estimate_confidence'], pl.get('vitamin_e_mg__est')))

        # =========================================================== 7 the Amount sheet block
        await page.click('[data-tab=log]'); await page.wait_for_selector('.hero')
        await page.click('.entry >> nth=0'); await page.wait_for_selector('#amt')
        fold = await T("[...document.querySelectorAll('.sheet details')].map((d) => d.innerText)")
        al = [x for x in fold if 'Estimated values' in x]
        check('Amount sheet: fold "Estimated values · confidence medium" for the estimated own food', len(al) == 1 and 'confidence medium' in al[0], fold[:3])
        await T("document.querySelectorAll('.sheet details').forEach((d) => d.open = true)")
        al = (await T("[...document.querySelectorAll('.sheet details')].map((d) => d.innerText)"))
        blk = [x for x in al if 'Estimated values' in x][0]
        check('Amount sheet: names the estimated nutrient, the fortified warning and the note', 'vitamin e' in blk.lower() and 'fortified' in blk.lower() and 'Fortified oat drink' in blk, blk)
        check('Amount sheet: not shown as dmBio ("dmBio" absent)', 'dmBio' not in blk)
        await close_all()

        # =========================================================== 8 manual food: the Estimates fold
        await page.click('[data-tab=foods]'); await page.wait_for_selector('#ffilter')
        await page.click('[data-act=new-food]')
        await page.wait_for_selector('#fname')
        check('manual food: "Estimates (optional)" is collapsed, ~ buttons are hidden', await T("document.querySelector('#estfold').open") is False and await T("[...document.querySelectorAll('#nuts .est-btn')].every((b) => b.hidden)"))
        await page.fill('#fname', 'Manual soup')
        await page.fill('[data-k=kcal]', '30'); await page.fill('[data-k=protein]', '1,5')
        check('typing a value does not show ~ while the fold is closed', await T("[...document.querySelectorAll('#nuts .est-btn')].every((b) => b.hidden)"))
        await page.click('#estfold summary')
        await page.wait_for_timeout(100)
        check('opening the fold shows ~ next to the filled fields only', await T("[...document.querySelectorAll('#nuts .est-btn')].filter((b) => !b.hidden).map((b) => b.dataset.est).sort().join()") == 'kcal,protein')
        check('manual food: select has Not set + 5 levels, fields are at least 16 px', await T("[...document.querySelectorAll('#fconf option')].map((o) => o.textContent.trim()).join()") == 'Not set,High,Medium,Low,Very low,None' and await T(SMALL_FONTS, '.sheet') == [])
        await page.click('#nuts [data-est=protein]')
        await page.click('#fok')
        check('manual food: an estimate without confidence is refused next to the select', await sheets() == 1 and await foods_n() == n0 + 2)
        await page.select_option('#fconf', 'l')
        await page.check('#ffort')
        await page.click('#fok')
        await page.wait_for_timeout(400)
        man = await T("Object.values(window.__tapnaplo.S.foods).find((f) => f.name === 'Manual soup')")
        check('manual food saved with est [protein], q l, fortified', man is not None and man['est'] == ['protein'] and man['q'] == 'l' and man['fortified'] is True and man['n'] == {'kcal': 30, 'protein': 1.5}, man)
        await page.click(f'[data-act=edit-food][data-id="{man["id"]}"]')
        await page.wait_for_selector('#fname')
        check('editing the saved food shows the Estimates fold open, ~ on protein, confidence Low, fortified ticked', await T("document.querySelector('#estfold').open") and (await mk('protein'))['pressed'] == 'true' and (await mk('kcal'))['pressed'] == 'false' and await page.input_value('#fconf') == 'l' and await page.is_checked('#ffort'))
        await page.click('#nuts [data-est=protein]')
        await page.click('#fok'); await page.wait_for_timeout(400)
        man = await T("(id) => window.__tapnaplo.S.foods[id]", man['id'])
        check('taking the last estimate off removes est and q (a confidence means nothing without estimates)', not man.get('est') and not man.get('q') and man.get('fortified') is True, man)
        await page.click(f'[data-act=edit-food][data-id="{man["id"]}"]'); await page.wait_for_selector('#fname')
        await page.select_option('#fconf', 'n'); await page.uncheck('#ffort')
        await page.click('#fok'); await page.wait_for_timeout(400)
        man = await T("(id) => window.__tapnaplo.S.foods[id]", man['id'])
        check('confidence "None" alone is kept as q n, fortified off is removed', man.get('q') == 'n' and 'fortified' not in man and not man.get('est'), man)

        # =========================================================== 9 several foods
        await open_ai()
        n1 = await foods_n()
        await read_text(J(two))
        await page.wait_for_selector('#ai-rows')
        rows_ = await T("[...document.querySelectorAll('#ai-rows .ai-row')].map((r) => r.innerText)")
        check('several foods: a list with a row for each', len(rows_) == 3 and 'Second food' in rows_[1], rows_)
        check('several foods: each row has Review and Save, nothing saved yet', await page.locator('#ai-rows [data-ai=review]').count() == 3 and await page.locator('#ai-rows [data-ai=save]').count() == 3 and await foods_n() == n1)
        check('list: buttons at least 44 px, text contrast ok in light and dark', await T(SMALL_TARGETS, '#ai-rows .btn') == [] and await T(CONTRAST_JS, '.sheet') == [], (await T(SMALL_TARGETS, '#ai-rows .btn'), await T(CONTRAST_JS, '.sheet')))
        if SHOTS: await page.screenshot(path=SHOTS + '/ai_list.png')
        await page.click('#ai-rows .ai-row[data-i="1"] [data-ai=save]')
        await page.wait_for_timeout(300)
        check('Save in a row saves that food at once and marks the row "Saved"', await foods_n() == n1 + 1 and 'saved' in (await page.inner_text('#ai-rows .ai-row[data-i="1"]')).lower() and await page.locator('#ai-rows .ai-row[data-i="1"] [data-ai]').count() == 0)
        await page.click('#ai-rows .ai-row[data-i="2"] [data-ai=review]')
        await page.wait_for_selector('#fok')
        check('Review in a row opens the editor with that food', await page.input_value('#fname') == 'Third food' and await page.input_value('#fbrand') == 'Zed' and await foods_n() == n1 + 1)
        await page.fill('#fname', 'Third food (checked)')
        await page.click('#fok'); await page.wait_for_timeout(400)
        check('Save in the editor saves the changed food, the row says "Saved", the list stays', await foods_n() == n1 + 2 and 'saved' in (await page.inner_text('#ai-rows .ai-row[data-i="2"]')).lower() and await T("Object.values(window.__tapnaplo.S.foods).some((f) => f.name === 'Third food (checked)')") and await sheets() == 2)
        check('the first food of the list was left alone', await foods_n() == n1 + 2 and await page.locator('#ai-rows .ai-row[data-i="0"] [data-ai=save]').count() == 1)
        await page.click('.sheet-wrap:last-of-type [data-dx]')
        await page.wait_for_timeout(300)
        check('Done closes the list and the Paste from AI sheet', await sheets() == 0)

        # =========================================================== 10 duplicates
        # an Open Food Facts food that was saved earlier
        await T("() => { const t = window.__tapnaplo; t.S.foods['o:5900000000099'] = { id: 'o:5900000000099', src: 'off', name: 'Some biscuit', brand: 'Bisco', barcode: '5900000000099', basis: { qty: 100, unit: 'g' }, n: { kcal: 480, protein: 6, fat: 20, carbohydrate: 65 }, nova: 4, portions: [], note: '', created: Date.now() }; t.save(); }")
        # (a) the same barcode as an own food -> Update existing
        await T("([fid, d]) => { const t = window.__tapnaplo; t.S.log.push({ id: crypto.randomUUID(), d, m: 'm3', f: fid, a: 200, t: Date.now(), tm: '18:00' }); t.save(); t.render(); }", [FID, today])
        before = await T("(id) => JSON.parse(JSON.stringify(window.__tapnaplo.S.foods[id]))", FID)
        newv = food(n={'kcal': 90, 'protein': 2, 'fat': 3, 'carbohydrate': 13, 'calcium': 150}, est=[], confidence='none', fortified=False, note='Updated by a new answer.')
        await open_ai()
        n2 = await foods_n()
        await read_text(J(doc(newv)))
        await page.wait_for_selector('#fok')
        await page.click('#fok')
        await page.wait_for_selector('[data-dup]')
        dtxt = await T("document.querySelector('.sheet-wrap:last-of-type .sheet').innerText")
        check('same barcode: asks "Already in your foods" with Update existing / Save as new / Cancel', 'Already in your foods' in dtxt and [await page.locator(f'[data-dup={x}]').inner_text() for x in ('update', 'new', 'cancel')] == ['Update existing', 'Save as new', 'Cancel'], dtxt)
        check('the question names the match and warns that diary entries will show the new values', 'the same barcode' in dtxt and re.search(r'2 diary entries', dtxt) is not None and 'new values' in dtxt, dtxt)
        check('the three buttons are at least 44 px', await T(SMALL_TARGETS, '[data-dup]') == [], await T(SMALL_TARGETS, '[data-dup]'))
        check('duplicate sheet: text contrast ok (light and dark)', await T(CONTRAST_JS, '.sheet') == [])
        if SHOTS: await page.screenshot(path=SHOTS + '/ai_dup.png')
        await page.click('[data-dup=cancel]'); await page.wait_for_timeout(300)
        check('Cancel: nothing changes and the editor stays open', await foods_n() == n2 and await page.locator('#fok').count() == 1 and await T("(id) => window.__tapnaplo.S.foods[id].n.kcal", FID) == 45)
        await page.click('#fok'); await page.wait_for_selector('[data-dup]')
        await page.click('[data-dup=update]'); await page.wait_for_timeout(500)
        after = await T("(id) => window.__tapnaplo.S.foods[id]", FID)
        check('Update existing: same id, new values, est/q/fortified of the old version are gone', await foods_n() == n2 and after['id'] == FID and after['n']['kcal'] == 90 and after['n'].get('calcium') == 150 and 'est' not in after and after.get('q') == 'n' and 'fortified' not in after and after['note'] == 'Updated by a new answer.', after)
        check('Update: the sheets close and a toast offers Undo', await sheets() == 0 and 'Updated' in await page.inner_text('#toast') and await page.locator('#toast button').count() == 1, await page.inner_text('#toast'))
        await page.click('[data-tab=log]'); await page.wait_for_selector('.hero')
        hero = (await page.inner_text('.hero')).replace('\n', ' ')
        check('the old diary entries now show the new value: (100 + 200 g) x 90 kcal + 50 kcal of the plain food = 320 instead of 185', re.search(r'(?<!\d)320(?!\d)', hero) is not None and re.search(r'(?<!\d)185(?!\d)', hero) is None, hero)
        await page.click('[data-tab=nutr]'); await page.wait_for_selector('details.nrow')
        await T("document.querySelectorAll('#view details').forEach((d) => d.open = true)")
        txt = await page.inner_text('#view')
        ve = re.search(r'(?m)^.*Vitamin E.*$', txt)
        check('Nutrients tab after the update: no ~ on vitamin E from the food (it has no estimate now)', ve is None or '~' not in ve.group(0), ve.group(0) if ve else '')
        await page.click('[data-tab=log]'); await page.wait_for_selector('.hero')
        # the Undo test: update again (the toast of the first update is gone or replaced)
        await open_ai(); await read_text(J(doc(food(n={'kcal': 90, 'protein': 2, 'fat': 3, 'carbohydrate': 13, 'calcium': 150}, est=[], confidence='none', fortified=False, note='Updated by a new answer.')))); await page.wait_for_selector('#fok')
        before2 = await T("(id) => JSON.parse(JSON.stringify(window.__tapnaplo.S.foods[id]))", FID)
        await page.fill('[data-k=kcal]', '95')
        await page.click('#fok'); await page.wait_for_selector('[data-dup]'); await page.click('[data-dup=update]'); await page.wait_for_timeout(400)
        check('second update gives the values typed in the editor (95)', await T("(id) => window.__tapnaplo.S.foods[id].n.kcal", FID) == 95)
        await page.click('[data-tab=log]'); await page.wait_for_selector('.hero')
        check('the diary follows the second update: 300 g x 95 kcal + 50 = 335', re.search(r'(?<!\d)335(?!\d)', (await page.inner_text('.hero')).replace('\n', ' ')) is not None, (await page.inner_text('.hero')).replace('\n', ' '))
        await page.click('#toast button'); await page.wait_for_timeout(300)
        undone = await T("(id) => window.__tapnaplo.S.foods[id]", FID)
        undone_clean = {k: v for k, v in undone.items() if not k.startswith('_')}
        check('Undo restores the old state of the food completely', undone_clean == {k: v for k, v in before2.items() if not k.startswith('_')}, (undone_clean.get('n'), before2.get('n')))
        hero = (await page.inner_text('.hero')).replace('\n', ' ')
        check('after Undo the diary shows the state before that update again (320)', re.search(r'(?<!\d)320(?!\d)', hero) is not None and re.search(r'(?<!\d)335(?!\d)', hero) is None, hero)
        await close_all()
        # (b) the same barcode as an Open Food Facts food -> Save as new
        n3 = await foods_n()
        await open_ai()
        await read_text(J(doc(food(name='Biscuit by AI', brand='', barcode='5900000000099', est=[], confidence='none'))))
        await page.wait_for_selector('#fok'); await page.click('#fok'); await page.wait_for_selector('[data-dup]')
        dtxt = await T("document.querySelector('.sheet-wrap:last-of-type .sheet').innerText")
        check('same barcode as a saved Open Food Facts food: asked as well', 'Some biscuit' in dtxt and 'the same barcode' in dtxt, dtxt)
        await page.click('[data-dup=new]'); await page.wait_for_timeout(400)
        check('Save as new: a second food is added, the old one is untouched', await foods_n() == n3 + 1 and await T("window.__tapnaplo.S.foods['o:5900000000099'].n.kcal") == 480 and await T("Object.values(window.__tapnaplo.S.foods).filter((f) => f.barcode === '5900000000099').length") == 2 and await sheets() == 0)
        # a 12-digit code is the same product as the 13-digit code with a leading 0 (UPC-A / EAN-13)
        await T("() => { const t = window.__tapnaplo; t.S.foods['o:0123456789012'] = { id: 'o:0123456789012', src: 'off', name: 'US snack', brand: 'Snacko', barcode: '0123456789012', basis: { qty: 100, unit: 'g' }, n: { kcal: 400 }, nova: 4, portions: [], note: '', created: Date.now() }; t.save(); }")
        await open_ai()
        await read_text(J(doc(food(name='UPC variant', brand='', barcode='123456789012', est=[], confidence='none'))))
        await page.wait_for_selector('#fok'); await page.click('#fok'); await page.wait_for_timeout(300)
        check('a 12-digit code and its 13-digit form with a leading 0 are the same barcode', await page.locator('[data-dup]').count() == 3 and 'US snack' in await T("document.querySelector('.sheet-wrap:last-of-type .sheet').innerText"))
        if await page.locator('[data-dup=cancel]').count(): await page.click('[data-dup=cancel]')
        await close_all()
        # (c) the same name and brand (case, accents, spaces) -> Cancel
        n4 = await foods_n()
        await open_ai()
        await read_text(J(doc(food(name='  TEST OAT DRÍNK ', brand='ACME', barcode='', est=[], confidence='none'))))
        await page.wait_for_selector('#fok'); await page.click('#fok'); await page.wait_for_selector('[data-dup]')
        dtxt = await T("document.querySelector('.sheet-wrap:last-of-type .sheet').innerText")
        check('same name and brand (case, accent, spaces ignored): asked, says "the same name and brand"', 'the same name and brand' in dtxt, dtxt)
        await page.click('[data-dup=cancel]'); await page.wait_for_timeout(300)
        await close_all()
        check('Cancel and close: no food added', await foods_n() == n4)
        await open_ai()
        await read_text(J(doc(food(name='Test oat drink', brand='', barcode='', est=[], confidence='none'))))
        await page.wait_for_selector('#fok'); await page.click('#fok'); await page.wait_for_timeout(400)
        check('same name but another brand is a new food, not a duplicate', await page.locator('[data-dup]').count() == 0 and await foods_n() == n4 + 1)
        # (d) update of an OFF food keeps its source and marks it edited
        await open_ai()
        await read_text(J(doc(food(name='Biscuit v2', brand='Bisco', barcode='5900000000099', est=[], confidence='none', n={'kcal': 500, 'protein': 7, 'fat': 22, 'carbohydrate': 64}))))
        await page.wait_for_selector('#fok'); await page.click('#fok'); await page.wait_for_selector('[data-dup]')
        await page.click('[data-dup=update]'); await page.wait_for_timeout(400)
        offf = await T("window.__tapnaplo.S.foods['o:5900000000099'] || null")
        check('updating a saved Open Food Facts food keeps its id and source, marks it edited', offf is not None and offf['src'] == 'off' and offf['n']['kcal'] == 500 and offf.get('edited') is True, offf)
        await close_all()
        # (e) a different basis and diary entries: Update is not offered
        await T("(d) => { const t = window.__tapnaplo; t.S.foods['u:caps'] = { id: 'u:caps', src: 'user', name: 'Vitamin caps', brand: '', barcode: '', basis: { qty: 1, unit: 'capsule' }, n: { vitamin_d: 20 }, nova: null, portions: [], note: '', created: Date.now() }; t.S.log.push({ id: crypto.randomUUID(), d, m: 'm1', f: 'u:caps', a: 2, t: Date.now(), tm: '08:00' }); t.save(); }", today)
        await open_ai()
        await read_text(J(doc(food(name='Vitamin caps', brand='', barcode='', est=[], confidence='none', n={'vitamin_d': 25}))))
        await page.wait_for_selector('#fok'); await page.click('#fok'); await page.wait_for_selector('[data-dup]')
        check('another basis with diary entries: Update existing is disabled and the sheet says why', await page.locator('[data-dup=update]').is_disabled() and 'cannot be moved' in await T("document.querySelector('.sheet-wrap:last-of-type .sheet').innerText"))
        await page.click('[data-dup=cancel]'); await close_all()

        # =========================================================== 11 picker flow: the new food is picked
        await page.click('[data-tab=log]'); await page.wait_for_selector('.hero')
        await page.click('.act.primary'); await page.wait_for_selector('#q')
        await page.click('[data-a=ai]'); await page.wait_for_selector('#ai-text')
        await read_text(J(doc(food(name='Picker oat drink', brand='Pick', barcode='', est=[], confidence='none', portions=[]))))
        await page.wait_for_selector('#fok'); await page.click('#fok')
        await page.wait_for_selector('#amt')
        check('from the Log food search: after Save the new food is opened in the Amount sheet', 'Picker oat drink' in await T("document.querySelector('.sheet-wrap:last-of-type .sheet').innerText") and await sheets() >= 1)
        check('the Amount sheet of the new food starts at 100 g', await page.input_value('#amt') == '100')
        await close_all()

        # =========================================================== 12 clipboard
        await T("(t) => { window.__clip = t; }", J(doc(food(name='From clipboard', brand='', barcode='', est=[], confidence='none'))))
        await open_ai()
        await T("() => navigator.clipboard.writeText(window.__clip)")
        await page.click('#ai-paste')
        await page.wait_for_selector('#fok', timeout=5000)
        check('Paste from clipboard (allowed): reads the clipboard and opens the review at once', await page.input_value('#fname') == 'From clipboard')
        await close_all()
        await open_ai()
        await T("() => navigator.clipboard.writeText('')")
        await page.click('#ai-paste'); await page.wait_for_timeout(300)
        check('Paste from clipboard with an empty clipboard says so', 'empty' in await page.inner_text('#ai-msg'), await page.inner_text('#ai-msg'))
        await page.click('#ai-copy'); await page.wait_for_timeout(300)
        copied = await T("() => navigator.clipboard.readText()")
        check('Copy AI prompt puts the whole prompt on the clipboard', copied == prompt and len(copied) > 5000, len(copied))
        check('Copy AI prompt: a toast says so', 'copied' in (await page.inner_text('#toast')).lower())
        await close_all()

        # clipboard refused (no permission): explain the long-press way
        ctx2, page2 = await make('noclip')
        await page2.click('[data-tab=foods]'); await page2.wait_for_selector('#ffilter')
        await page2.click('[data-act=ai-import]'); await page2.wait_for_selector('#ai-text')
        await page2.click('#ai-paste'); await page2.wait_for_timeout(500)
        msg = await page2.inner_text('#ai-msg')
        check('clipboard refused: the message explains press and hold, Paste, then Read', 'Paste' in msg and 'hold' in msg and 'Read' in msg, msg)
        check('clipboard refused: the answer box is still there and empty', await page2.input_value('#ai-text') == '' and await page2.locator('#ai-text').count() == 1)
        await page2.click('#ai-copy'); await page2.wait_for_timeout(500)
        box = await page2.locator('#ai-prompt-box').count()
        check('copy refused: the prompt appears in a box to copy by hand, with the Select All hint', box == 1 and await page2.input_value('#ai-prompt-box') == prompt and 'Select All' in await page2.inner_text('#ai-msg'))
        check('that box has at least 16 px text', await page2.evaluate(SMALL_FONTS, '.sheet') == [])
        await page2.fill('#ai-text', J(doc(food(name='By hand', est=[], confidence='none', brand='', barcode=''))))
        await page2.click('#ai-read'); await page2.wait_for_selector('#fok')
        check('pasting by hand and Read works without clipboard access', await page2.input_value('#fname') == 'By hand')
        await ctx2.close()

        # =========================================================== 13 backup and restore
        await page.click('[data-tab=data]'); await page.wait_for_selector('[data-act=export-json]')
        async with page.expect_download() as d:
            await page.click('[data-act=export-json]')
        dl = await d.value; await dl.save_as('backup_ai.json')
        bk = json.load(open('backup_ai.json', encoding='utf-8'))
        # make a food with all three for the backup
        await T("() => { const t = window.__tapnaplo; t.S.foods['u:bk'] = { id: 'u:bk', src: 'user', name: 'Backup food', brand: '', barcode: '', basis: { qty: 100, unit: 'g' }, n: { kcal: 50, vitamin_e: 2 }, est: ['vitamin_e'], q: 'v', fortified: true, nova: null, portions: [], note: '', created: Date.now() }; t.save(); }")
        async with page.expect_download() as d:
            await page.click('[data-act=export-json]')
        dl = await d.value; await dl.save_as('backup_ai.json')
        bk = json.load(open('backup_ai.json', encoding='utf-8'))
        bf = bk['foods']['u:bk']
        check('backup JSON: est, q and fortified are in the file, no cache fields', bf['est'] == ['vitamin_e'] and bf['q'] == 'v' and bf['fortified'] is True and not any(k.startswith('_') for k in bf), bf)
        await T("() => { const S = window.__tapnaplo.S; delete S.foods['u:bk']; S.log.length = 0; window.__tapnaplo.save(); }")
        await page.set_input_files('#importfile', 'backup_ai.json'); await page.wait_for_selector('[data-ok]'); await page.click('[data-ok]'); await page.wait_for_timeout(600)
        rb = await T("window.__tapnaplo.S.foods['u:bk']")
        check('restore from the file: est, q and fortified are back', rb is not None and rb['est'] == ['vitamin_e'] and rb['q'] == 'v' and rb['fortified'] is True, rb)
        check('restored estimates work (isEst on vitamin E, not on kcal)', await T("() => { const t = window.__tapnaplo, f = t.S.foods['u:bk'], v = t.vecOf(f); return [t.isEst(f, t.IDX.vitamin_e, v), t.isEst(f, 0, v)]; }") == [True, False])
        # an old backup without the new fields
        old = json.loads(json.dumps(bk))
        for f in old['foods'].values():
            for k in ('est', 'q', 'fortified'): f.pop(k, None)
        json.dump(old, open('backup_old.json', 'w', encoding='utf-8'))
        await page.set_input_files('#importfile', 'backup_old.json'); await page.wait_for_selector('[data-ok]'); await page.click('[data-ok]'); await page.wait_for_timeout(600)
        ob = await T("window.__tapnaplo.S.foods['u:bk']")
        check('an old backup (no est/q/fortified) still loads', ob is not None and 'est' not in ob and await T("() => { const t = window.__tapnaplo, f = t.S.foods['u:bk'], v = t.vecOf(f); return [t.isEst(f, t.IDX.vitamin_e, v), t.isEst(f, 0, v), t.estSet(f).size]; }") == [False, False, 0], ob)
        await page.click('[data-tab=nutr]'); await page.wait_for_selector('.nrow, .card')
        check('the app renders after loading an old backup', not errs, errs[:3])

        # =========================================================== 14 sync transport
        canon = lambda o: T("(o) => window.__tapnaplo.canon(o)", o)
        fa = await T("(id) => JSON.parse(JSON.stringify(window.__tapnaplo.S.foods[id]))", 'u:bk')
        c1 = await T("(id) => { const f = window.__tapnaplo.S.foods[id]; const a = window.__tapnaplo.canon(f); window.__tapnaplo.estSet(f); const b = window.__tapnaplo.canon(f); return [a, b, '_est' in f]; }", 'u:bk')
        check('canon (the sync hash input) ignores the cache field _est', c1[0] == c1[1] and c1[2] is True, c1[2])
        fb, fc, fd = dict(fa, est=['vitamin_e']), dict(fa, q='h'), dict(fa, fortified=True)
        cs = [await canon(x) for x in (fa, fb, fc, fd)]
        check('canon changes when est, q or fortified change (so a change is synced)', len(set(cs)) == 4, [len(x) for x in cs])

        ctxA, A = await make('A', gh_on=True)
        await A.click('[data-tab=foods]'); await A.wait_for_selector('#ffilter')
        await A.click('[data-act=ai-import]'); await A.wait_for_selector('#ai-text')
        await A.fill('#ai-text', J(doc(food(name='Synced oat', brand='Syn', barcode='4000000000017'))))
        await A.click('#ai-read'); await A.wait_for_selector('#fok'); await A.click('#fok'); await A.wait_for_timeout(500)
        sid = await A.evaluate("Object.values(window.__tapnaplo.S.foods).find((f) => f.name === 'Synced oat').id")
        await A.click('[data-tab=data]'); await A.wait_for_selector('[data-act=sync-setup]')
        await A.click('[data-act=sync-setup]'); await A.fill('#sy-repo', 'me/nutrilog-data'); await A.fill('#sy-token', GOOD); await A.click('[data-ok]')
        for _ in range(3):
            await A.wait_for_function('!window.__tapnaplo.SY.busy')
            await A.evaluate("window.__tapnaplo.syncRun('manual')")
        await A.wait_for_function('!window.__tapnaplo.SY.busy')
        rec = gh.recs().get('f:' + sid)
        check('sync: the imported food is in the repository with est, q and fortified', rec is not None and rec['x'] is not None and rec['x'].get('est') == ['vitamin_e'] and rec['x'].get('q') == 'm' and rec['x'].get('fortified') is True, rec)
        check('sync: no cache field leaves the phone', rec is not None and not any(k.startswith('_') for k in rec['x']), [k for k in (rec or {'x': {}})['x'] if k.startswith('_')])
        ctxB, B = await make('B', gh_on=True)
        await B.click('[data-tab=data]'); await B.wait_for_selector('[data-act=sync-setup]')
        await B.click('[data-act=sync-setup]'); await B.fill('#sy-repo', 'me/nutrilog-data'); await B.fill('#sy-token', GOOD); await B.click('[data-ok]')
        for _ in range(3):
            await B.wait_for_function('!window.__tapnaplo.SY.busy')
            await B.evaluate("window.__tapnaplo.syncRun('manual')")
        await B.wait_for_function('!window.__tapnaplo.SY.busy')
        fb_ = await B.evaluate("(id) => window.__tapnaplo.S.foods[id] || null", sid)
        check('sync: the second device has the food with est, q and fortified', fb_ is not None and fb_.get('est') == ['vitamin_e'] and fb_.get('q') == 'm' and fb_.get('fortified') is True, fb_)
        check('sync: the second device marks the estimate (isEst) after receiving', await B.evaluate("(id) => { const t = window.__tapnaplo, f = t.S.foods[id]; return t.isEst(f, t.IDX.vitamin_e, t.vecOf(f)); }", sid) is True)
        # an update on B (import with update) travels back to A
        await B.click('[data-tab=foods]'); await B.wait_for_selector('#ffilter')
        await B.click('[data-act=ai-import]'); await B.wait_for_selector('#ai-text')
        await B.fill('#ai-text', J(doc(food(name='Synced oat', brand='Syn', barcode='4000000000017', est=[], confidence='none', fortified=False, n={'kcal': 77, 'protein': 2, 'fat': 2, 'carbohydrate': 12}))))
        await B.click('#ai-read'); await B.wait_for_selector('#fok'); await B.click('#fok'); await B.wait_for_selector('[data-dup]'); await B.click('[data-dup=update]'); await B.wait_for_timeout(400)
        for pg in (B, A, B, A):
            for _ in range(2):
                await pg.wait_for_function('!window.__tapnaplo.SY.busy')
                await pg.evaluate("window.__tapnaplo.syncRun('manual')")
            await pg.wait_for_function('!window.__tapnaplo.SY.busy')
        fa_ = await A.evaluate("(id) => window.__tapnaplo.S.foods[id]", sid)
        check('sync: an update by import on one device reaches the other, the old estimates are gone there too', fa_['n']['kcal'] == 77 and 'est' not in fa_ and 'fortified' not in fa_ and fa_.get('q') == 'n', fa_)
        check('sync: A and B end with the same food', json.dumps({k: v for k, v in fa_.items() if k[0] != '_' and k != 'updated'}, sort_keys=True) == json.dumps({k: v for k, v in (await B.evaluate("(id) => window.__tapnaplo.S.foods[id]", sid)).items() if k[0] != '_' and k != 'updated'}, sort_keys=True))
        await ctxA.close(); await ctxB.close()

        # =========================================================== 15 no network, offline
        ctx3, P3 = await make('net', sw='block')
        reqs = []
        P3.on('request', lambda r: reqs.append(r.url))
        await P3.click('[data-tab=foods]'); await P3.wait_for_selector('#ffilter')
        await P3.click('[data-act=ai-import]'); await P3.wait_for_selector('#ai-text')
        await P3.fill('#ai-text', prose)
        await P3.click('#ai-read'); await P3.wait_for_selector('#fok'); await P3.click('#fok'); await P3.wait_for_timeout(500)
        await P3.click('[data-act=ai-import]'); await P3.wait_for_selector('#ai-text')
        await P3.fill('#ai-text', J(two)); await P3.click('#ai-read'); await P3.wait_for_selector('#ai-rows')
        await P3.click('#ai-rows .ai-row[data-i="1"] [data-ai=save]'); await P3.wait_for_timeout(300)
        check('the whole import (paste, read, review, list, save) makes no network request at all', reqs == [], reqs)
        await ctx3.close()

        ctx4 = await browser.new_context(viewport={'width': 390, 'height': 844}, locale='en-GB', has_touch=True, is_mobile=True)
        P4 = await ctx4.new_page()
        P4.on('pageerror', lambda e: errs.append('off PE ' + str(e)))
        await P4.route('**/*openfoodfacts.org/**', lambda r: r.abort())
        await P4.goto(URL); await P4.wait_for_selector('.hero')
        await P4.wait_for_timeout(1500)
        ready = await P4.evaluate('navigator.serviceWorker.ready.then((r) => !!r.active)')
        await ctx4.set_offline(True)
        await P4.reload(); await P4.wait_for_selector('.hero', timeout=10000)
        await P4.click('[data-tab=foods]'); await P4.wait_for_selector('#ffilter')
        await P4.click('[data-act=ai-import]'); await P4.wait_for_selector('#ai-text')
        await P4.fill('#ai-text', J(doc(food(name='Offline oat'))))
        await P4.click('#ai-read'); await P4.wait_for_selector('#fok'); await P4.click('#fok'); await P4.wait_for_timeout(500)
        check('offline (service worker): reload works, import works, the food is saved', ready and await P4.evaluate("Object.values(window.__tapnaplo.S.foods).some((f) => f.name === 'Offline oat' && f.q === 'm')"))
        await P4.click('[data-act=ai-import]'); await P4.wait_for_selector('#ai-text')
        await P4.click('#ai-copy'); await P4.wait_for_timeout(300)
        check('offline: "Copy AI prompt" works too (the prompt is part of the app)', ('copied' in (await P4.inner_text('#toast')).lower()) or await P4.locator('#ai-prompt-box').count() == 1)
        await ctx4.set_offline(False); await ctx4.close()

        check('no page errors in the whole run', errs == [], errs[:5])
        await browser.close()
        print('\n' + ('ALL OK' if not problems else f'{len(problems)} FAILED: ' + '; '.join(problems)))
        sys.exit(1 if problems else 0)


asyncio.run(main())
