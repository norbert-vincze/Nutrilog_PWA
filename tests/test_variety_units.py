"""Variety list, step L1 (version 37). Run with the web server on port 8765 (see CLAUDE.md); NUTRILOG_URL can point to another address.

Norbert's Variety plan (project doc nutrilog-valtozatossag-fejlesztesi-prompt.md): the app will show how many different plant and animal units he ate in a week. Step L1 is only the fixed list
(variety_units.json: 17 main groups > 75 subgroups > 164 units, plus one "other (not listed)" in every subgroup of the 11 base groups) and the loader that checks it at start. Nothing else uses it yet.
Covers: the file itself (counts, id format, no duplicate id, no orphan, "other" in every base subgroup, no name or alias that points to two units), the loader in the app (same counts, nodes, accent-free
names and aliases, the known traps: coconut water is no coconut, pumpkin seed is no pumpkin), every kind of broken list on its own (nothing is repaired or guessed), the app that still starts when the file
cannot be read (no connection, HTTP 404, invalid JSON, a newer version, a broken list, hostile text) and says why on the Data tab, the offline cache, no new key in the backup, the version number and the cache name."""
import asyncio, copy, json, os, pathlib, re, sys, unicodedata
from collections import Counter, defaultdict
from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
URL = os.environ.get('NUTRILOG_URL', 'http://127.0.0.1:8765/index.html')


def key(s):
    s = unicodedata.normalize('NFD', s.lower())
    return re.sub(r'\s+', ' ', ''.join(c for c in s if unicodedata.category(c) != 'Mn')).strip()


def find(raw, uid):   # (sub dict, unit dict or None) for an id
    for m in raw['main']:
        for s in m['subs']:
            if s['id'] == uid: return m, s, None
            for u in s.get('units', []):
                if u['id'] == uid: return m, s, u
    raise KeyError(uid)


async def main():
    problems = []

    def check(name, ok, info=''):
        print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(info)[:600].replace('\n', ' | ')) if info != '' else ''))
        if not ok: problems.append(name)

    # ---------------- 1. the file itself (counted in Python, independent of the app) ----------------
    raw = json.load(open(ROOT / 'variety_units.json', encoding='utf-8'))
    mains = raw['main']
    base = [m for m in mains if m['role'] == 'base']; sep = [m for m in mains if m['role'] == 'separate']
    subs = [s for m in mains for s in m['subs']]
    units = [u for m in base for s in m['subs'] for u in s['units']]
    others = [u for u in units if u['id'].endswith('.other')]
    check('the file is a Nutrilog variety list, version 1', raw['app'] == 'tapnaplo-variety' and raw['version'] == 1, [raw['app'], raw['version']])
    check('17 main groups: 11 base (veg fru gra tub leg nut mea fis egg dai fat) and 6 separate (bev spi swe sna dis sup)',
          len(mains) == 17 and [m['id'] for m in base] == 'veg fru gra tub leg nut mea fis egg dai fat'.split() and [m['id'] for m in sep] == 'bev spi swe sna dis sup'.split(), [m['id'] for m in mains])
    check('75 subgroups (45 in the base groups, 30 in the separate ones)', len(subs) == 75 and sum(len(m['subs']) for m in base) == 45 and sum(len(m['subs']) for m in sep) == 30,
          [len(subs), sum(len(m['subs']) for m in base), sum(len(m['subs']) for m in sep)])
    check('164 units, plus 45 "other (not listed)" items (209 in all)', len(units) - len(others) == 164 and len(others) == 45 and len(units) == 209, [len(units), len(others)])
    ids = [m['id'] for m in mains] + [s['id'] for s in subs] + [u['id'] for u in units]
    check('every id is used once', len(ids) == len(set(ids)) == 17 + 75 + 209, [k for k, v in Counter(ids).items() if v > 1])
    check('the id format: main = 3 letters, then dot-separated lower-case parts (letters, digits, hyphens)',
          all(re.fullmatch(r'[a-z]{3}', m['id']) for m in mains) and all(re.fullmatch(r'[a-z]{3}\.[a-z0-9]+(-[a-z0-9]+)*', s['id']) for s in subs) and all(re.fullmatch(r'[a-z]{3}\.[a-z0-9]+(-[a-z0-9]+)*\.[a-z0-9]+(-[a-z0-9]+)*', u['id']) for u in units))
    check('no orphan: every subgroup id starts with its main id and every unit id with its subgroup id',
          all(s['id'].startswith(m['id'] + '.') for m in mains for s in m['subs']) and all(u['id'].startswith(s['id'] + '.') for m in base for s in m['subs'] for u in s['units']))
    check('every base subgroup has its "other" unit (<subgroup>.other)', all(any(u['id'] == s['id'] + '.other' for u in s['units']) for m in base for s in m['subs']),
          [s['id'] for m in base for s in m['subs'] if not any(u['id'] == s['id'] + '.other' for u in s['units'])])
    check('separate groups go down to the subgroup only (no units), with examples (ex) in Hungarian and English', all('units' not in s and s['ex']['hu'] and s['ex']['en'] for m in sep for s in m['subs']))
    check('every node has a Hungarian and an English name', all(n.get('hu') and n.get('en') for n in mains + subs + units))
    names = defaultdict(set)
    for u in units:
        if u['id'].endswith('.other'): continue
        for t in [u['hu'], u['en'], *u.get('a', [])]: names[key(t)].add(u['id'])
    check('no name or alias (accent-free, case-free) points to two units', all(len(v) == 1 for v in names.values()), {k: v for k, v in names.items() if len(v) > 1})
    check('the "other" items have no aliases and nothing is deprecated yet', all('a' not in u for u in others) and not any(u.get('deprecated') for u in units))
    check('the fixed decisions of 2026-11-11 are in the list: two onions, coconut as a fruit, coconut oil, olive, olive oil, plant drinks, coconut water under 100% juice',
          all(find(raw, i) for i in ['veg.allium.onion', 'veg.allium.red-onion', 'fru.tropical.coconut', 'fat.oils.coconut-oil', 'veg.fruit.olive', 'fat.oils.olive-oil', 'bev.plant', 'bev.juice'])
          and 'kókuszvíz' in find(raw, 'bev.juice')[1]['ex']['hu'] and 'kókusztej-ital' in find(raw, 'bev.plant')[1]['ex']['hu'])
    check('the offal flag is defined for the meat group only', raw['flags'] == [{'id': 'offal', 'hu': 'belsőség', 'en': 'offal', 'applies': ['mea']}], raw['flags'])

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        errs = []

        async def new_ctx(**kw):
            o = dict(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True, locale='en-GB', service_workers='block')
            o.update(kw)
            c = await browser.new_context(**o)
            await c.route('**/*openfoodfacts.org/**', lambda r: r.fulfill(status=200, headers={'access-control-allow-origin': '*', 'content-type': 'application/json'}, body='{"products":[],"status":0}'))
            return c

        def watch(pg, tag='P'):
            pg.on('pageerror', lambda e: errs.append(f'{tag} PE {e}'))
            pg.on('console', lambda m: errs.append(f'{tag} C {m.text}') if m.type == 'error' and 'Failed to load resource' not in m.text else None)

        ctx = await new_ctx()
        page = await ctx.new_page(); watch(page)
        reqs = []
        page.on('request', lambda r: reqs.append(r.url) if r.url.split('?')[0].endswith('/variety_units.json') else None)
        await page.goto(URL); await page.wait_for_selector('.hero')
        T = page.evaluate

        # ---------------- 2. the loader in the app ----------------
        v = await T("(() => { const V = window.__tapnaplo.VARIETY; return V && { counts: V.counts, version: V.version, updated: V.updated, n: [V.mains.length, V.subs.length, V.units.length], err: window.__tapnaplo.VARIETY_ERR }; })()")
        check('the app loaded the list: 17 groups (11 base, 6 separate), 75 subgroups, 164 units, 45 "other", nothing deprecated',
              v and v['counts'] == {'main': 17, 'base': 11, 'separate': 6, 'sub': 75, 'unit': 164, 'other': 45, 'deprecated': 0} and v['n'] == [17, 75, 209] and v['err'] == '', v)
        check('the version and the date of the file are kept', v and v['version'] == 1 and v['updated'] == raw['updated'], v)
        node = "(id) => { const n = window.__tapnaplo.varietyNode(id); return n && { id: n.id, level: n.level, role: n.role, main: n.main, sub: n.sub, hu: n.hu, en: n.en, other: !!n.other }; }"
        n1 = await T(node, 'veg.leaf.spinach'); n2 = await T(node, 'bev.sweetened'); n3 = await T(node, 'veg'); n4 = await T(node, 'veg.leaf.other')
        check('a unit knows its subgroup and main group, a separate subgroup is a node of its own, a main group too',
              n1 == {'id': 'veg.leaf.spinach', 'level': 'unit', 'role': 'base', 'main': 'veg', 'sub': 'veg.leaf', 'hu': 'spenót', 'en': 'spinach', 'other': False}
              and n2 and n2['level'] == 'sub' and n2['role'] == 'separate' and n2['main'] == 'bev' and n2['hu'] == 'Cukros vagy édesített ital'
              and n3 and n3['level'] == 'main' and n3['en'] == 'Vegetables', [n1, n2, n3])
        check('the "other (not listed)" item is marked', n4 and n4['other'] is True and n4['level'] == 'unit', n4)
        bad_nodes = await T("['nope', '', null, undefined, 5, {}, '__proto__', 'constructor', 'toString', 'veg.leaf.'].map((x) => window.__tapnaplo.varietyNode(x))")
        check('an unknown id (or a name like __proto__ or constructor) is no node', all(x is None for x in bad_nodes), bad_nodes)
        al = "(t) => window.__tapnaplo.VARIETY.alias.get(window.__tapnaplo.varietyKey(t)) || null"
        got = {t: await T(al, t) for t in ['Tahini', 'bulgur', 'KÓKUSZZSÍR', 'kokuszzsir', 'olívaolaj', 'olivaolaj', 'hummus', 'pasta', 'tök', 'tökmag', 'pumpkin seed', 'pumpkin flesh', 'peanut butter', 'mogyoróvaj', 'Spenót', 'SPENOT']}
        check('names and aliases are found accent-free and case-free (tahini = sesame, bulgur and pasta = durum, coconut fat = coconut oil, peanut butter = peanut)',
              got['Tahini'] == 'nut.seeds.sesame' and got['bulgur'] == 'gra.wheat.durum' and got['pasta'] == 'gra.wheat.durum' and got['KÓKUSZZSÍR'] == got['kokuszzsir'] == 'fat.oils.coconut-oil'
              and got['olívaolaj'] == got['olivaolaj'] == 'fat.oils.olive-oil' and got['peanut butter'] == got['mogyoróvaj'] == 'nut.nuts.peanut' and got['Spenót'] == got['SPENOT'] == 'veg.leaf.spinach', got)
        check('the known traps: pumpkin seed is no pumpkin, hummus is the chickpea', got['tök'] == 'veg.fruit.pumpkin' and got['tökmag'] == got['pumpkin seed'] == 'nut.seeds.pumpkin-seed' and got['pumpkin flesh'] == 'veg.fruit.pumpkin' and got['hummus'] == 'leg.chickpea-pea.chickpea', got)
        none = {t: await T(al, t) for t in ['coconut water', 'kókuszvíz', 'kókuszvíz', 'cocoa butter', 'water', 'víz', 'other (not listed)', 'egyéb (nincs a listán)']}
        check('the trap "coconut water is no coconut" holds: coconut water, cocoa butter, water and the "other" texts are no alias of any unit', all(x is None for x in none.values()), none)
        check('no alias or name points to an "other" item', await T("[...window.__tapnaplo.VARIETY.alias.values()].every((id) => !id.endsWith('.other'))"))
        check('the flag list is loaded: offal applies to meat', await T("(() => { const f = window.__tapnaplo.VARIETY.flags.get('offal'); return !!f && f.applies.join() === 'mea' && f.en === 'offal'; })()"))
        check('the app made no page error and asked for the list once', errs == [] and len(reqs) == 1, [errs, reqs])

        # ---------------- 3. the Data tab line ----------------
        await page.click('[data-tab=data]'); await page.wait_for_timeout(300)
        txt = await page.inner_text('#view')
        check('the Data tab says "Variety list: 164 units in 17 groups." next to the other database numbers (and still the 65 nutrients)', 'Variety list: 164 units in 17 groups.' in txt and '65 nutrients.' in txt and 'could not be loaded' not in txt, re.findall(r'Database:[^\n]*', txt))
        ver = re.search(r'(\d+) · \d+ \w+ 20\d\d', txt)
        sw = (ROOT / 'sw.js').read_text(encoding='utf-8')
        check('the Data tab shows version 37 or newer and the service worker cache has the same number', bool(ver) and int(ver.group(1)) >= 37 and f"const CACHE = 'nutrilog-v{ver.group(1)}'" in sw, ver and ver.group(0))
        check('variety_units.json is in the service worker file list (works offline from the first install)', "'variety_units.json'" in re.search(r'const SHELL = \[[^\]]*\]', sw).group(0))
        check('the food tables keep their own caches (the list does not touch them)', "'ciqual.json': 'nutrilog-data-2'" in sw and "'usda.json': 'nutrilog-data-2'" in sw and "'dmbio.json': 'nutrilog-dmbio-2'" in sw and 'variety_units.json' not in re.search(r'const DATA = \{[^}]*\}', sw).group(0))

        # ---------------- 4. backup: no new key ----------------
        async with page.expect_download() as dd:
            await page.click('[data-act=export-json]')
        bk = json.loads(pathlib.Path(await (await dd.value).path()).read_text(encoding='utf-8'))
        check('the backup file has no new top-level key (the list is not user data)', sorted(bk.keys()) == sorted(['app', 'version', 'exported', 'log', 'foods', 'meta', 'health', 'wlog']), sorted(bk.keys()))
        await ctx.close()

        # ---------------- 5. every kind of broken list on its own (nothing is repaired or guessed) ----------------
        ctx = await new_ctx(); page = await ctx.new_page(); watch(page, 'B')
        await page.goto(URL); await page.wait_for_selector('.hero')
        BUILD = "(r) => { const o = window.__tapnaplo.varietyBuild(r); return { ok: !!o.data, errors: o.errors, newer: !!o.newer, counts: o.data && o.data.counts }; }"

        async def build(mut):
            r = copy.deepcopy(raw); mut(r)
            return await page.evaluate(BUILD, r)

        def has(o, *parts): return (not o['ok']) and any(all(x in e for x in parts) for e in o['errors'])

        good = await page.evaluate(BUILD, raw)
        check('the real list builds with no error', good['ok'] and good['errors'] == [] and good['counts']['unit'] == 164, good)

        def m_dup(r): r['main'][0]['subs'][0]['units'].append(copy.deepcopy(r['main'][0]['subs'][0]['units'][1]))
        check('a duplicate id is refused ("is used twice")', has(await build(m_dup), 'veg.leaf.spinach', 'used twice'))

        def m_dup_sub(r): r['main'][0]['subs'].append(copy.deepcopy(r['main'][0]['subs'][1]))
        check('a subgroup that appears twice is refused', has(await build(m_dup_sub), 'used twice'))

        def m_orphan_unit(r): r['main'][0]['subs'][0]['units'].insert(0, {'id': 'veg.root.pear', 'hu': 'körte', 'en': 'pear'})
        check('an orphan unit (its id belongs under another subgroup) is refused', has(await build(m_orphan_unit), 'veg.root.pear', 'does not belong under veg.leaf'))

        def m_orphan_sub(r): r['main'][0]['subs'][0]['id'] = 'fru.leaf'
        check('an orphan subgroup (its id belongs under another main group) is refused', has(await build(m_orphan_sub), 'fru.leaf', 'does not belong under veg'))

        def m_nodot(r): r['main'][0]['subs'][0]['units'].append({'id': 'spinach2', 'hu': 'x', 'en': 'y'})
        check('a unit id without its parents is refused', has(await build(m_nodot), 'spinach2', 'does not belong'))

        def m_noother(r): r['main'][0]['subs'][0]['units'] = [u for u in r['main'][0]['subs'][0]['units'] if not u['id'].endswith('.other')]
        check('a base subgroup without its "other" unit is refused', has(await build(m_noother), 'veg.leaf', '"other (not listed)"', 'veg.leaf.other'))

        def m_nounits(r): r['main'][0]['subs'][0]['units'] = []
        check('a base subgroup with no units is refused', has(await build(m_nounits), 'veg.leaf', 'has no units'))

        def m_sepunits(r): r['main'][11]['subs'][0]['units'] = [{'id': 'bev.water.tap', 'hu': 'csapvíz', 'en': 'tap water'}]
        check('a separate group with units is refused', has(await build(m_sepunits), 'bev.water', 'separate group'))

        def m_role(r): r['main'][0]['role'] = 'maybe'
        check('an unknown role is refused', has(await build(m_role), 'veg', 'role'))

        def m_mainid(r): r['main'][0]['id'] = 'VEG'
        check('an invalid main id is refused', has(await build(m_mainid), 'no valid id'))

        def m_hu(r): del r['main'][0]['subs'][0]['units'][1]['hu']
        def m_en(r): r['main'][0]['subs'][0]['units'][1]['en'] = '  '
        check('a missing Hungarian or English name is refused', has(await build(m_hu), 'veg.leaf.spinach', 'Hungarian') and has(await build(m_en), 'veg.leaf.spinach', 'English'))

        def m_alias(r): find(r, 'veg.leaf.lettuce')[2]['a'].append('spenót')
        def m_alias_acc(r): find(r, 'veg.leaf.lettuce')[2]['a'].append('SPENOT')
        def m_name(r): find(r, 'veg.leaf.kale')[2]['en'] = 'Spinach'
        o = await build(m_alias)
        check('an alias that points to two units is refused, and the message names both', has(o, '"spenot"', 'veg.leaf.lettuce and veg.leaf.spinach'), o['errors'])
        check('the same clash with other capitals or accents (SPENOT) is found too', has(await build(m_alias_acc), 'veg.leaf.lettuce and veg.leaf.spinach'))
        check('a name that is another unit\'s name (English "Spinach" on kale) is refused', has(await build(m_name), 'veg.leaf.kale and veg.leaf.spinach'))

        def m_same(r): find(r, 'veg.leaf.spinach')[2]['a'] = ['spenót', 'SPINACH']
        check('the same unit repeating its own name as an alias is no clash', (await build(m_same))['ok'])

        def m_alias_type(r): find(r, 'veg.leaf.spinach')[2]['a'] = 'spenót'
        check('an alias list that is not a list is refused', has(await build(m_alias_type), 'veg.leaf.spinach', 'alias list'))

        def m_dep(r): find(r, 'veg.leaf.kale')[2]['deprecated'] = True
        def m_dep_ok(r): u = find(r, 'veg.leaf.kale')[2]; u['deprecated'] = True; u['replacedBy'] = 'veg.leaf.spinach'
        def m_dep_bad(r): u = find(r, 'veg.leaf.kale')[2]; u['deprecated'] = True; u['replacedBy'] = 'veg.leaf.nowhere'
        def m_dep_sub(r): u = find(r, 'veg.leaf.kale')[2]; u['deprecated'] = True; u['replacedBy'] = 'veg.leaf'
        def m_rep(r): find(r, 'veg.leaf.kale')[2]['replacedBy'] = 'veg.leaf.spinach'
        check('deprecated without replacedBy, with an unknown id or with a subgroup id is refused', has(await build(m_dep), 'veg.leaf.kale', 'deprecated') and has(await build(m_dep_bad), 'veg.leaf.kale', 'deprecated') and has(await build(m_dep_sub), 'veg.leaf.kale', 'deprecated'))
        od = await build(m_dep_ok)
        check('deprecated with a valid replacedBy is accepted (a node is never deleted) and is counted apart: 163 active units, 1 deprecated', od['ok'] and od['counts']['unit'] == 163 and od['counts']['deprecated'] == 1, od)
        check('replacedBy on a unit that is not deprecated is refused', has(await build(m_rep), 'replacedBy', 'not deprecated'))

        def m_flag_unit(r): find(r, 'veg.leaf.spinach')[2]['flags'] = ['offal']
        def m_flag_unk(r): find(r, 'mea.poultry.chicken')[2]['flags'] = ['spicy']
        def m_flag_ok(r): find(r, 'mea.poultry.chicken')[2]['flags'] = ['offal']
        def m_flag_main(r): r['flags'][0]['applies'] = ['xyz']
        def m_flag_dup(r): r['flags'].append(copy.deepcopy(r['flags'][0]))
        check('a flag on a unit where it does not apply, an unknown flag, a flag for a main group that does not exist and a duplicate flag are refused',
              has(await build(m_flag_unit), 'veg.leaf.spinach', 'does not apply') and has(await build(m_flag_unk), 'unknown flag') and has(await build(m_flag_main), 'offal', 'does not exist') and has(await build(m_flag_dup), 'flag'))
        check('the offal flag on a meat unit is fine', (await build(m_flag_ok))['ok'])

        def m_app(r): r['app'] = 'something'
        def m_ver(r): r['version'] = 2
        def m_ver_s(r): r['version'] = '1'
        def m_ver0(r): r['version'] = 0
        def m_nomain(r): r['main'] = []
        def m_main_t(r): r['main'] = {'veg': 1}
        check('another file, a missing or a text version number, an empty list of groups and a list of groups that is not a list are refused',
              has(await build(m_app), 'not a Nutrilog variety list') and has(await build(m_ver_s), 'version number') and has(await build(m_ver0), 'version number')
              and has(await build(m_nomain), 'main groups') and has(await build(m_main_t), 'main groups'))
        o = await build(m_ver)
        check('a list with a higher version says "needs a newer version of the app" (never guessed)', o['newer'] and o['errors'] == ['it needs a newer version of the app'] and not o['ok'], o)
        odd = await page.evaluate("[null, [], 'x', 5, true].map((r) => { const o = window.__tapnaplo.varietyBuild(r); return [!!o.data, o.errors.length]; })")
        check('something that is not a list at all is refused without a page error', odd == [[False, 1]] * 5, odd)
        def m_many(r):
            for i in range(80): r['main'][0]['subs'][0]['units'].append({'id': f'veg.leaf.x{i}', 'hu': '', 'en': ''})
        o = await build(m_many)
        check('the list of problems is capped (at most 50 are kept)', (not o['ok']) and 40 <= len(o['errors']) <= 50, len(o['errors']))
        def m_proto(r): find(r, 'veg.leaf.spinach')[2]['a'] = ['__proto__', 'constructor', 'toString']
        o = await build(m_proto)
        check('names like __proto__, constructor and toString are only names (no clash, nothing polluted)', o['ok'] and await page.evaluate("({}).polluted === undefined && Object.prototype.hasOwnProperty.call(Object.prototype, 'polluted') === false"), o)
        await ctx.close()

        # ---------------- 6. the app starts without a usable list and says why ----------------
        async def start_with(label, route, expect, hostile=False):
            c = await new_ctx(); pg = await c.new_page(); local = []
            pg.on('pageerror', lambda e: local.append(f'PE {e}'))
            await c.route('**/variety_units.json', route)
            await pg.goto(URL); await pg.wait_for_selector('.hero')
            st = await pg.evaluate("({ v: window.__tapnaplo.VARIETY, e: window.__tapnaplo.VARIETY_ERR })")
            await pg.click('[data-tab=data]'); await pg.wait_for_timeout(250)
            t = await pg.inner_text('#view')
            ok = st['v'] is None and expect in st['e'] and f'The variety list could not be loaded ({st["e"]}).' in t and 'Variety list: 164' not in t and local == []
            check(f'without a usable list ({label}) the app still starts, says why on the Data tab, and makes no page error', ok, [st, local])
            await pg.click('[data-tab=log]'); await pg.wait_for_timeout(150)
            check(f'... and the Diary still works ({label})', await pg.locator('.hero').count() == 1 and await pg.locator('.act.primary').count() >= 1)
            extra = None
            if hostile: extra = await pg.evaluate("({ pwn: window.__pwn === 1, img: document.querySelectorAll('#view img').length })")
            await c.close()
            return extra

        await start_with('no connection', lambda r: r.abort(), 'no connection')
        await start_with('HTTP 404', lambda r: r.fulfill(status=404, body='nope'), 'HTTP 404')
        await start_with('invalid JSON', lambda r: r.fulfill(status=200, content_type='application/json', body='{"app": "tapnaplo-variety", "main": ['), 'not valid JSON')
        newer = copy.deepcopy(raw); newer['version'] = 2
        await start_with('a newer version', lambda r: r.fulfill(status=200, content_type='application/json', body=json.dumps(newer)), 'needs a newer version of the app')
        dup = copy.deepcopy(raw); dup['main'][0]['subs'][0]['units'].append(copy.deepcopy(dup['main'][0]['subs'][0]['units'][1]))
        await start_with('a duplicate id', lambda r: r.fulfill(status=200, content_type='application/json', body=json.dumps(dup)), 'the id veg.leaf.spinach is used twice')
        two = copy.deepcopy(dup); del two['main'][1]['subs'][0]['units'][-1]
        await start_with('two problems', lambda r: r.fulfill(status=200, content_type='application/json', body=json.dumps(two)), '(and 1 more)')
        evil = copy.deepcopy(raw); evil['main'][0]['subs'][0]['id'] = '<img src=x onerror="window.__pwn=1">'
        ex = await start_with('a hostile text in the file', lambda r: r.fulfill(status=200, content_type='application/json', body=json.dumps(evil)), 'does not belong under veg', hostile=True)
        check('a hostile id in a broken list is shown as text only (no script, no image on the Data tab)', ex == {'pwn': False, 'img': 0}, ex)

        # ---------------- 7. offline ----------------
        ctx = await new_ctx(service_workers='allow'); page = await ctx.new_page(); watch(page, 'O')
        await page.goto(URL); await page.wait_for_selector('.hero')
        cache = 'nutrilog-v' + re.search(r"CACHE = 'nutrilog-v(\d+)'", sw).group(1)
        got = None
        for _ in range(40):
            got = await page.evaluate("(c) => caches.open(c).then((x) => x.match('variety_units.json')).then((r) => !!r).catch(() => false)", cache)
            if got: break
            await page.wait_for_timeout(250)
        check('after the first visit the list is in the app cache (offline use)', got is True, cache)
        keys = await page.evaluate("caches.keys().then(async ks => { const o = {}; for (const k of ks) o[k] = (await (await caches.open(k)).keys()).map((r) => new URL(r.url).pathname.split('/').pop()); return o; })")
        check('the list is in the app cache only, not in a table cache', 'variety_units.json' in keys.get(cache, []) and not any('variety_units.json' in v for k, v in keys.items() if k != cache), {k: len(v) for k, v in keys.items()})
        await ctx.set_offline(True)
        await page.reload(); await page.wait_for_selector('.hero', timeout=10000)
        offl = await page.evaluate("(() => { const V = window.__tapnaplo.VARIETY; return V ? V.counts.unit : null; })()")
        check('offline reload: the list is loaded from the cache (164 units)', offl == 164, offl)
        await ctx.set_offline(False)
        await ctx.close()

        check('no page errors in the whole test', errs == [], errs[:5])
        await browser.close()
    print('\nALL PASS' if not problems else f'\n{len(problems)} FAILED: {problems}')
    sys.exit(1 if problems else 0)


asyncio.run(main())
