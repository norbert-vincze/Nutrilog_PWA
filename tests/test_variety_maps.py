"""Variety maps, step L3 (version 39). Run with the web server on port 8765 (see CLAUDE.md); NUTRILOG_URL can point to another address.

Norbert's Variety plan (project doc nutrilog-valtozatossag-fejlesztesi-prompt.md, step L3): CIQUAL, USDA and dmBio foods get their variety group from three map files
(vt_map_ciqual.json, vt_map_usda.json, vt_map_dmbio.json: code -> vt, only approved rows). The maps ship EMPTY; nothing is filled in automatically. This test covers the app side:
the three shipped files, the loader (varietyMapBuild: every kind of bad row and bad file, checked against the list), the resolution order of the plan (own field > map > not classified),
the entries CSV, the Data tab sentence, the app without the list / without a file / with a hostile file, the offline cache, no new backup key, version and cache name.
The suggestion tool (tools/variety_suggest.py) has its own test: test_variety_suggest.py."""
import asyncio, csv, io, json, os, pathlib, re, sys
from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
URL = os.environ.get('NUTRILOG_URL', 'http://127.0.0.1:8765/index.html')
FILES = {'ciqual': 'vt_map_ciqual.json', 'usda': 'vt_map_usda.json', 'dmbio': 'vt_map_dmbio.json'}


def mapfile(source, rows, **kw):
    d = {'app': 'tapnaplo-variety-map', 'version': 1, 'source': source, 'updated': '2026-11-12', 'map': rows}
    d.update(kw)
    return json.dumps(d)


async def main():
    async with async_playwright() as p:
        problems = []

        def check(name, ok, info=''):
            print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(info)[:500].replace('\n', ' | ')) if info != '' else ''))
            if not ok: problems.append(name)

        browser = await p.chromium.launch()
        errs = []

        async def new_ctx(maps=None, nolist=False, sw='block'):
            """maps: {source: body string | (status, body) | 'abort'}; a source that is not given is the shipped file"""
            ctx = await browser.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True, locale='en-GB', service_workers=sw, accept_downloads=True)
            for src, what in (maps or {}).items():
                def mk(what):
                    async def h(route):
                        if what == 'abort': return await route.abort()
                        if isinstance(what, tuple): return await route.fulfill(status=what[0], body=what[1])
                        return await route.fulfill(status=200, content_type='application/json', body=what)
                    return h
                await ctx.route('**/' + FILES[src], mk(what))
            if nolist: await ctx.route('**/variety_units.json', lambda r: r.fulfill(status=404, body='not found'))
            await ctx.route('**/*openfoodfacts.org/**', lambda r: r.fulfill(status=200, headers={'access-control-allow-origin': '*', 'content-type': 'application/json'}, body='{"products":[],"status":0}'))
            return ctx

        async def new_page(ctx, name):
            pg = await ctx.new_page()
            pg.dname = name; pg.reqs = []
            pg.on('request', lambda r: pg.reqs.append(r.url.split('?')[0].rsplit('/', 1)[-1]))
            pg.on('pageerror', lambda e: errs.append(f'{name} PE {e}'))
            pg.on('console', lambda m: errs.append(f'{name} C {m.text}') if m.type == 'error' and 'Failed to load resource' not in m.text else None)
            await pg.goto(URL); await pg.wait_for_selector('.hero')
            return pg

        async def data_text(pg):
            await pg.click('[data-tab=data]'); await pg.wait_for_timeout(250)
            t = await pg.inner_text('#view')
            await pg.click('[data-tab=log]'); await pg.wait_for_timeout(100)
            return t

        # real codes of the built-in tables (checked against the files below)
        CQ_SESAME, CQ_ONION, CQ_LIVER, CQ_COFFEE = '15038', '20035', '40118', '18154'
        US_MUSTARD, DM_LENTIL = '170929', '1490004'
        ciq = json.load(open(ROOT / 'ciqual.json', encoding='utf-8'))
        usda = json.load(open(ROOT / 'usda.json', encoding='utf-8'))
        dm = json.load(open(ROOT / 'dmbio.json', encoding='utf-8'))
        check('the codes used by this test exist in the three tables (so a typo cannot make a test pass by accident)',
              all(any(x['c'] == c for x in ciq['foods']) for c in (CQ_SESAME, CQ_ONION, CQ_LIVER, CQ_COFFEE)) and any(x['c'] == US_MUSTARD for x in usda['foods']) and any(x['c'] == DM_LENTIL for x in dm['foods']))

        # =========================================================== 1. the shipped files and the app with them
        for src, fn in FILES.items():
            raw = json.load(open(ROOT / fn, encoding='utf-8'))
            check(f'{fn} is shipped, is a map of its own table, and is EMPTY (no row is filled in automatically; Norbert approves the rows)',
                  raw.get('app') == 'tapnaplo-variety-map' and raw.get('version') == 1 and raw.get('source') == src and raw.get('map') == {}, list(raw.keys()))
        ctx = await new_ctx(); page = await new_page(ctx, 'main')
        T = lambda js, arg=None: page.evaluate(js, arg)
        st = await T("({ c: window.__tapnaplo.VMAPS.ciqual.size, u: window.__tapnaplo.VMAPS.usda.size, d: window.__tapnaplo.VMAPS.dmbio.size, e: window.__tapnaplo.VMAP_ERR, v: window.__tapnaplo.VARIETY_MAP_V })")
        check('the app loads the three shipped maps: 0 rows each, no problem', st == {'c': 0, 'u': 0, 'd': 0, 'e': '', 'v': 1}, st)
        check('each map file is requested once at start', all(page.reqs.count(fn) == 1 for fn in FILES.values()), [page.reqs.count(fn) for fn in FILES.values()])
        r0 = await T("""() => { const t = window.__tapnaplo; return ['c:' + '%s', 'usda:' + '%s', 'dm:' + '%s'].map((id) => { const f = t.getFood(id), r = t.varietyOf(f); return [!!f, r.state, r.id, r.source, r.flags]; }); }""" % (CQ_SESAME, US_MUSTARD, DM_LENTIL))
        check('with empty maps a CIQUAL, a USDA and a dmBio food are NOT classified (never a guess)', r0 == [[True, 'none', None, None, []]] * 3, r0)
        tx = await data_text(page)
        check('the Data tab says: Variety maps: 0 CIQUAL, 0 USDA, 0 dmBio foods have a group.', 'Variety maps: 0 CIQUAL, 0 USDA, 0 dmBio foods have a group.' in tx and 'could not be used' not in tx, tx[-400:])
        await ctx.close()

        # =========================================================== 2. a good map: the group comes from the map, in the right table
        good_c = {CQ_SESAME: 'nut.seeds.sesame', CQ_ONION: 'veg.allium.onion', CQ_LIVER: {'vt': 'mea.poultry.turkey', 'vf': ['offal']}, '9999999': 'veg.leaf'}
        good_u = {US_MUSTARD: 'spi.dry-spices'}
        good_d = {DM_LENTIL: 'leg.lentils.red-lentil'}
        ctx = await new_ctx({'ciqual': mapfile('ciqual', good_c), 'usda': mapfile('usda', good_u), 'dmbio': mapfile('dmbio', good_d)})
        page = await new_page(ctx, 'good'); T = lambda js, arg=None: page.evaluate(js, arg)
        o = await T("""() => { const t = window.__tapnaplo, g = (id) => { const f = t.getFood(id), r = t.varietyOf(f); return f ? { state: r.state, id: r.id, level: r.node && r.node.level, source: r.source, flags: r.flags, name: r.node && r.node.en } : null; };
          return { sesame: g('c:%s'), onion: g('c:%s'), liver: g('c:%s'), coffee: g('c:%s'), mustard: g('usda:%s'), lentil: g('dm:%s'), orphan: t.varietyOf({ id: 'c:9999999' }), sizes: [t.VMAPS.ciqual.size, t.VMAPS.usda.size, t.VMAPS.dmbio.size], err: t.VMAP_ERR }; }"""
                    % (CQ_SESAME, CQ_ONION, CQ_LIVER, CQ_COFFEE, US_MUSTARD, DM_LENTIL))
        check('a CIQUAL food in the map has its group, the source is "map" and the node is the unit of the list', o['sesame'] == {'state': 'ok', 'id': 'nut.seeds.sesame', 'level': 'unit', 'source': 'map', 'flags': [], 'name': 'sesame'}, o['sesame'])
        check('a row with a flag gives the flag (offal under mea.*)', o['liver']['state'] == 'ok' and o['liver']['id'] == 'mea.poultry.turkey' and o['liver']['flags'] == ['offal'] and o['liver']['source'] == 'map', o['liver'])
        check('a CIQUAL food that is not in the map is not classified, also when its neighbours are', o['coffee']['state'] == 'none' and o['coffee']['id'] is None, o['coffee'])
        check('a USDA food and a dmBio food get their group from their own map', o['mustard']['id'] == 'spi.dry-spices' and o['mustard']['level'] == 'sub' and o['lentil']['id'] == 'leg.lentils.red-lentil' and o['lentil']['source'] == 'map', [o['mustard'], o['lentil']])
        check('a subgroup is a valid group of a food too; a code that is in the map but not in the table is simply never looked up', o['orphan']['state'] == 'ok' and o['orphan']['id'] == 'veg.leaf' and o['sizes'] == [4, 1, 1] and o['err'] == '', o)
        same = await T("""() => { const t = window.__tapnaplo; return [t.varietyMapOf({ id: 'usda:%s' }), t.varietyMapOf({ id: 'dm:%s' }), t.varietyMapOf({ id: 'usda:%s' }), t.varietyMapOf({ id: 'u:%s' }), t.varietyMapOf({ id: 'o:%s' }), t.varietyMapOf(null), t.varietyMapOf({})].map((x) => x && x.vt); }""" % (CQ_SESAME, CQ_SESAME, DM_LENTIL, CQ_SESAME, CQ_SESAME))
        check('the same code in another table is another food: a CIQUAL code is not looked up in the USDA or dmBio map, and foods you made or saved never read a map', same == [None, None, None, None, None, None, None], same)

        # resolution order: the own field of a food you made wins, a map is never looked at for it
        r = await T("""() => { const t = window.__tapnaplo, S = t.S; S.log.length = 0; for (const k of Object.keys(S.foods)) delete S.foods[k];
          const mk = (id, name, extra) => Object.assign({ id, src: 'user', name, brand: '', barcode: '', basis: { qty: 100, unit: 'g' }, n: { kcal: 40 }, nova: null, portions: [], note: '' }, extra);
          S.foods['u:%s'] = mk('u:%s', 'Own with the code of a mapped food', {});
          S.foods['u:m2'] = mk('u:m2', 'Own with a group', { vt: 'veg.leaf.spinach', vts: 'manual' });
          S.foods['o:%s'] = Object.assign(mk('o:%s', 'Saved product', {}), { src: 'off' });
          const out = ['u:%s', 'u:m2', 'o:%s'].map((id) => { const r = t.varietyOf(S.foods[id]); return [r.state, r.id, r.source]; });
          [['c:%s', '08:10'], ['c:%s', '08:20'], ['u:m2', '08:30'], ['usda:%s', '08:40'], ['dm:%s', '08:50'], ['c:%s', '09:00']].forEach(([f, tm], i) => S.log.push({ id: 'e' + i, f, a: 100, d: S.day, m: 'm1', t: 1000 + i, tm }));
          S.tab = 'data'; t.save(); t.render(); return out; }""" % (CQ_SESAME, CQ_SESAME, CQ_SESAME, CQ_SESAME, CQ_SESAME, CQ_SESAME, CQ_SESAME, CQ_COFFEE, US_MUSTARD, DM_LENTIL, CQ_LIVER))
        check('order of the plan: a food you made keeps its own field; a food you made or saved with a code that is also in a map stays not classified (the own field is the only source)',
              r == [['none', None, None], ['ok', 'veg.leaf.spinach', 'manual'], ['none', None, None]], r)
        await page.wait_for_selector('[data-act=export-entries]')

        async def csv_of(act, name):
            async with page.expect_download() as d:
                await page.click(f'[data-act={act}]')
            dl = await d.value
            path = HERE / name
            await dl.save_as(str(path))
            try:
                return list(csv.DictReader(io.StringIO(path.read_text(encoding='utf-8-sig'))))
            finally:
                path.unlink()
        er = await csv_of('export-entries', 'tmp_vmap_entries.csv')
        cells = [(x['food'], x['variety_unit'], x['variety_source'], x['variety_flags']) for x in er]
        names = {c: next(x['n'] for x in ciq['foods'] if x['c'] == c) for c in (CQ_SESAME, CQ_COFFEE, CQ_LIVER)}
        byname = {}
        for f, u, s, fl in cells: byname.setdefault(f, []).append((u, s, fl))
        check('Entries CSV: foods of the tables show the group of their map row (source "map", flags joined by ;), a food not in the map has empty cells',
              byname[names[CQ_SESAME]] == [('nut.seeds.sesame', 'map', ''), ('nut.seeds.sesame', 'map', '')][:len(byname[names[CQ_SESAME]])] and byname[names[CQ_LIVER]] == [('mea.poultry.turkey', 'map', 'offal')]
              and byname[names[CQ_COFFEE]] == [('', '', '')] and ('Own with a group' in byname and byname['Own with a group'] == [('veg.leaf.spinach', 'manual', '')]), byname)
        dr = await csv_of('export-days', 'tmp_vmap_days.csv')
        check('Daily totals CSV is unchanged (no variety column)', not any('variety' in h for h in dr[0].keys()))
        async with page.expect_download() as d:
            await page.click('[data-act=export-json]')
        dl = await d.value; path = HERE / 'tmp_vmap_backup.json'
        await dl.save_as(str(path)); bk = json.loads(path.read_text(encoding='utf-8')); path.unlink()
        check('the backup file has no new top-level key and does not contain the maps (the maps are not user data)',
              sorted(bk.keys()) == sorted(['app', 'version', 'exported', 'log', 'foods', 'meta', 'health', 'wlog']) and 'nut.seeds.sesame' not in json.dumps(bk), sorted(bk.keys()))
        await ctx.close()

        # =========================================================== 3. rows: every kind of bad row is left out and counted, the good ones stay
        ctx = await new_ctx(); page = await new_page(ctx, 'rows'); T = lambda js, arg=None: page.evaluate(js, arg)
        B = """([raw, src]) => { const t = window.__tapnaplo, o = t.varietyMapBuild(raw, src, t.VARIETY); return { rows: [...o.map].map(([k, v]) => [k, v.vt, v.vf]), dropped: o.dropped, problems: o.problems, newer: o.newer }; }"""
        BJ = """([text, src]) => { const t = window.__tapnaplo, o = t.varietyMapBuild(JSON.parse(text), src, t.VARIETY); return { rows: [...o.map].map(([k, v]) => [k, v.vt, v.vf]), dropped: o.dropped, problems: o.problems, newer: o.newer }; }"""

        async def one(row, code='1000'):
            o = await T(B, [{'app': 'tapnaplo-variety-map', 'version': 1, 'source': 'ciqual', 'map': {code: row}}, 'ciqual'])
            return o
        for label, row, code, why in [
            ('a number', 5, '1000', 'wrong shape'), ('null', None, '1000', 'wrong shape'), ('a list', ['veg.leaf'], '1000', 'wrong shape'), ('an empty text', '', '1000', 'wrong shape'),
            ('a main group alone', 'veg', '1000', 'wrong shape'), ('upper case', 'Veg.Leaf', '1000', 'wrong shape'), ('a long text', 'veg.' + 'a' * 100, '1000', 'wrong shape'),
            ('a unit that is not in the list', 'veg.leaf.martian', '1000', 'is not a subgroup or unit of the list'), ('a subgroup that is not in the list', 'veg.martian', '1000', 'is not a subgroup or unit of the list'),
            ('a main group written like a subgroup', 'bev.alcohol.beer', '1000', 'is not a subgroup or unit of the list'),
            ('an unknown flag', {'vt': 'mea.red.beef', 'vf': ['bogus']}, '1000', 'is not known or does not fit'), ('offal under vegetables', {'vt': 'veg.leaf.spinach', 'vf': ['offal']}, '1000', 'is not known or does not fit'),
            ('vf that is not a list', {'vt': 'mea.red.beef', 'vf': 'offal'}, '1000', '"vf" is not a short list'), ('eleven flags', {'vt': 'mea.red.beef', 'vf': ['offal'] * 11}, '1000', '"vf" is not a short list'),
            ('a flag that is not text', {'vt': 'mea.red.beef', 'vf': [5]}, '1000', 'is not known or does not fit'),
            ('an extra key', {'vt': 'mea.red.beef', 'x': 1}, '1000', 'wrong shape'), ('an object without vt', {'vf': ['offal']}, '1000', 'wrong shape'),
            ('a code with a space', 'veg.leaf', 'a b', 'the code has a wrong shape'), ('a code of 33 characters', 'veg.leaf', 'a' * 33, 'the code has a wrong shape'), ('an empty code', 'veg.leaf', '', 'the code has a wrong shape'),
            ('a code with a dot', 'veg.leaf', '1.5', 'the code has a wrong shape'),
        ]:
            o = await one(row, code)
            check(f'bad row ({label}): left out and said ({why})', o['rows'] == [] and len(o['dropped']) == 1 and why in o['dropped'][0] and o['problems'] == [], o)
        o = await T(BJ, ['{"app":"tapnaplo-variety-map","version":1,"source":"ciqual","map":{"1":"veg.leaf.spinach","2":{"vt":"mea.red.beef","vf":["offal","offal"]},"3":"nope","4":"veg.leaf","__proto__":"veg.leaf.spinach","constructor":"veg.leaf","toString":"fru.pome"}}', 'ciqual'])
        check('good rows stay when a bad one is in the same file; a repeated flag is kept once; names like __proto__ and constructor are only codes',
              sorted(o['rows'], key=lambda x: x[0]) == sorted([['1', 'veg.leaf.spinach', []], ['2', 'mea.red.beef', ['offal']], ['4', 'veg.leaf', []], ['__proto__', 'veg.leaf.spinach', []], ['constructor', 'veg.leaf', []], ['toString', 'fru.pome', []]], key=lambda x: x[0]) and len(o['dropped']) == 1 and o['dropped'][0].startswith('3: '), o)
        check('nothing was polluted', await T("({}).polluted === undefined && Object.getPrototypeOf({}) === Object.prototype && window.__tapnaplo.VMAPS.ciqual.get('toString') === undefined"))
        o = await T(B, [{'app': 'tapnaplo-variety-map', 'version': 1, 'source': 'ciqual', 'map': {'1': 'veg.leaf.other', '2': 'bev.water', '3': 'swe.chocolate'}}, 'ciqual'])
        check('the "other (not listed)" unit and the subgroups of the separate groups (drinks, sweets) are valid groups', [r[1] for r in o['rows']] == ['veg.leaf.other', 'bev.water', 'swe.chocolate'] and o['dropped'] == [], o)
        # whole files
        for label, raw, src, why in [
            ('a list', [], 'ciqual', 'it is not a variety map'), ('null', None, 'ciqual', 'it is not a variety map'), ('a text', 'x', 'ciqual', 'it is not a variety map'), ('another app', {'app': 'tapnaplo', 'version': 1, 'source': 'ciqual', 'map': {}}, 'ciqual', 'it is not a variety map'),
            ('no version', {'app': 'tapnaplo-variety-map', 'source': 'ciqual', 'map': {}}, 'ciqual', 'positive whole number'), ('version 0', {'app': 'tapnaplo-variety-map', 'version': 0, 'source': 'ciqual', 'map': {}}, 'ciqual', 'positive whole number'),
            ('version 1.5', {'app': 'tapnaplo-variety-map', 'version': 1.5, 'source': 'ciqual', 'map': {}}, 'ciqual', 'positive whole number'), ('version "1"', {'app': 'tapnaplo-variety-map', 'version': '1', 'source': 'ciqual', 'map': {}}, 'ciqual', 'positive whole number'),
            ('a newer version', {'app': 'tapnaplo-variety-map', 'version': 2, 'source': 'ciqual', 'map': {}}, 'ciqual', 'needs a newer version'),
            ('the map of another table', {'app': 'tapnaplo-variety-map', 'version': 1, 'source': 'usda', 'map': {}}, 'ciqual', 'it is the map of usda, not of ciqual'),
            ('no source', {'app': 'tapnaplo-variety-map', 'version': 1, 'map': {}}, 'ciqual', 'not of ciqual'),
            ('no map', {'app': 'tapnaplo-variety-map', 'version': 1, 'source': 'ciqual'}, 'ciqual', '"map" is not an object'), ('a map that is a list', {'app': 'tapnaplo-variety-map', 'version': 1, 'source': 'ciqual', 'map': ['veg.leaf']}, 'ciqual', '"map" is not an object'),
        ]:
            o = await T(B, [raw, src])
            check(f'bad file ({label}): not used at all, one problem that says why', o['rows'] == [] and len(o['problems']) == 1 and why in o['problems'][0], o)
        o = await T(B, [{'app': 'tapnaplo-variety-map', 'version': 2, 'source': 'ciqual', 'map': {}}, 'ciqual'])
        check('a newer version is marked as newer (nothing is guessed)', o['newer'] is True, o)
        await ctx.close()

        # =========================================================== 4. the app with a bad file or without a file: it starts, the other maps work, the Data tab says why
        async def start_with(label, maps, expect, others_ok=True, nolist=False):
            c = await new_ctx(maps, nolist=nolist); pg = await c.new_page(); local = []
            pg.on('pageerror', lambda e: local.append(f'PE {e}'))
            pg.reqs = []
            pg.on('request', lambda r: pg.reqs.append(r.url.split('?')[0].rsplit('/', 1)[-1]))
            await pg.goto(URL); await pg.wait_for_selector('.hero')
            st = await pg.evaluate("({ e: window.__tapnaplo.VMAP_ERR, s: [window.__tapnaplo.VMAPS.ciqual.size, window.__tapnaplo.VMAPS.usda.size, window.__tapnaplo.VMAPS.dmbio.size] })")
            t = await data_text(pg)
            ok = (expect in st['e'] and f'The variety maps could not be used completely ({st["e"]}).' in t) if expect else (st['e'] == '' and 'could not be used' not in t)
            check(f'{label}: the app starts, the Data tab says why, no page error', ok and local == [], [st, local])
            await pg.click('[data-tab=log]'); await pg.wait_for_timeout(150)
            check(f'  ... and the Diary still works ({label})', await pg.locator('.hero').count() == 1 and await pg.locator('.act.primary').count() >= 1)
            await c.close()
            return st, pg

        st, _ = await start_with('the CIQUAL map answers HTTP 404', {'ciqual': (404, 'nope'), 'usda': mapfile('usda', good_u)}, 'vt_map_ciqual.json: HTTP 404')
        check('  ... the USDA map still works, the CIQUAL map is empty', st['s'] == [0, 1, 0], st)
        st, _ = await start_with('the USDA map has no connection', {'usda': 'abort', 'dmbio': mapfile('dmbio', good_d)}, 'vt_map_usda.json: no connection')
        check('  ... the dmBio map still works', st['s'] == [0, 0, 1], st)
        await start_with('the dmBio map is not valid JSON', {'dmbio': '{"app": "tapnaplo-variety-map", "map": ['}, 'vt_map_dmbio.json: the file is not valid JSON')
        await start_with('a newer map version', {'ciqual': mapfile('ciqual', good_c, version=2)}, 'needs a newer version of the app')
        st, _ = await start_with('the USDA file is the map of dmBio', {'usda': mapfile('dmbio', good_d)}, 'vt_map_usda.json: it is the map of dmbio, not of usda')
        check('  ... nothing of it was used', st['s'] == [0, 0, 0], st)
        st, _ = await start_with('two rows are not valid', {'ciqual': mapfile('ciqual', {CQ_SESAME: 'nut.seeds.sesame', '1': 'veg.leaf.martian', '2': 'veg'})}, 'vt_map_ciqual.json: 2 rows were left out, 1: veg.leaf.martian is not a subgroup or unit of the list')
        check('  ... the good row is used', st['s'] == [1, 0, 0], st)
        st, _ = await start_with('one row is not valid, another file is missing', {'ciqual': mapfile('ciqual', {'1': 'veg.leaf.martian'}), 'usda': (404, 'x')}, '(and 1 more)')
        st, pg = await start_with('everything is fine', {}, '')

        # hostile text in a map (a code with markup) is shown as text only
        c = await new_ctx({'ciqual': mapfile('ciqual', {'<img src=x onerror="window.__pwn=1">': 'veg.leaf', CQ_SESAME: 'nut.seeds.sesame'})})
        pg = await new_page(c, 'evil')
        t = await data_text(pg)
        await pg.click('[data-tab=data]'); await pg.wait_for_timeout(250)
        ex = await pg.evaluate("({ pwn: window.__pwn === 1, img: document.querySelectorAll('#view img').length })")
        check('a hostile code in a map file is dropped and shown as text only (no script, no image on the Data tab)', ex == {'pwn': False, 'img': 0} and 'the code has a wrong shape' in t and '<img src=x' in t, [ex, t[-300:]])
        await c.close()

        # =========================================================== 5. without the list the maps are not even requested (nothing to check them against)
        c = await new_ctx({'ciqual': mapfile('ciqual', good_c)}, nolist=True); pg = await new_page(c, 'nolist')
        n = await pg.evaluate("({ list: window.__tapnaplo.VARIETY === null, sizes: [window.__tapnaplo.VMAPS.ciqual.size, window.__tapnaplo.VMAPS.usda.size, window.__tapnaplo.VMAPS.dmbio.size], err: window.__tapnaplo.VMAP_ERR, r: window.__tapnaplo.varietyOf(window.__tapnaplo.getFood('c:%s')).state })" % CQ_SESAME)
        t = await data_text(pg)
        check('without the list the maps are not requested, are empty, and a mapped food is not classified; the Data tab speaks about the list only',
              n == {'list': True, 'sizes': [0, 0, 0], 'err': '', 'r': 'none'} and not any(f in pg.reqs for f in FILES.values()) and 'The variety list could not be loaded' in t and 'Variety maps' not in t, [n, [f for f in pg.reqs if f in FILES.values()]])
        await c.close()

        # =========================================================== 6. offline: the three files are in the app cache
        sw = (ROOT / 'sw.js').read_text(encoding='utf-8')
        cache = 'nutrilog-v' + re.search(r"CACHE = 'nutrilog-v(\d+)'", sw).group(1)
        ctx = await new_ctx(sw='allow'); page = await new_page(ctx, 'offline')
        got = {}
        for _ in range(40):
            got = await page.evaluate("(c) => caches.open(c).then(async (x) => { const o = {}; for (const f of ['vt_map_ciqual.json', 'vt_map_usda.json', 'vt_map_dmbio.json']) o[f] = !!(await x.match(f)); return o; }).catch(() => ({}))", cache)
            if got and all(got.values()) and len(got) == 3: break
            await page.wait_for_timeout(250)
        check('after the first visit the three maps are in the app cache (offline use)', got == {f: True for f in FILES.values()}, got)
        keys = await page.evaluate("caches.keys().then(async ks => { const o = {}; for (const k of ks) o[k] = (await (await caches.open(k)).keys()).map((r) => new URL(r.url).pathname.split('/').pop()); return o; })")
        check('the maps are in the app cache only, not in a table cache', not any('vt_map' in x for k, v in keys.items() if k != cache for x in v), {k: len(v) for k, v in keys.items()})
        await ctx.set_offline(True)
        await page.reload(); await page.wait_for_selector('.hero', timeout=10000)
        off = await page.evaluate("({ e: window.__tapnaplo.VMAP_ERR, v: !!window.__tapnaplo.VARIETY, s: [window.__tapnaplo.VMAPS.ciqual.size, window.__tapnaplo.VMAPS.usda.size, window.__tapnaplo.VMAPS.dmbio.size] })")
        check('offline reload: list and maps load from the cache without a problem', off == {'e': '', 'v': True, 's': [0, 0, 0]}, off)
        await ctx.set_offline(False)
        await ctx.close()

        # =========================================================== 6b. the maps written by tools/variety_suggest.py are read by the app (tool and app agree)
        import subprocess, tempfile
        tdir = pathlib.Path(tempfile.mkdtemp(prefix='vmap_tool_'))
        try:
            sys.path.insert(0, str(ROOT / 'tools'))
            import variety_suggest as VS
            made = {}
            for src, code, vt, flag in (('ciqual', CQ_SESAME, 'nut.seeds.sesame', ''), ('ciqual', CQ_LIVER, 'mea.poultry.turkey', 'offal'), ('usda', US_MUSTARD, 'spi.dry-spices', ''), ('dmbio', DM_LENTIL, 'leg.lentils.red-lentil', '')):
                made.setdefault(src, []).append([code, 'x', '', vt, flag, 'unit-name', 'high', '', 'yes', ''])
            texts = {}
            for src, rows in made.items():
                rev = tdir / f'review_{src}.csv'
                with open(rev, 'w', encoding='utf-8-sig', newline='') as fh:
                    w = csv.writer(fh); w.writerow(VS.COLUMNS); w.writerows(rows)
                outp = tdir / FILES[src]
                cp = subprocess.run([sys.executable, '-I', str(ROOT / 'tools' / 'variety_suggest.py'), 'apply', '--source', src, '--reviewed', str(rev), '--map', str(outp)], capture_output=True, text=True)
                texts[src] = outp.read_text(encoding='utf-8') if cp.returncode == 0 and outp.exists() else ''
            check('the command line (apply --map) wrote the three map files', all(texts.get(k) for k in FILES), list(texts))
            ctx = await new_ctx({k: texts[k] for k in FILES}); page = await new_page(ctx, 'tool'); T = lambda js, arg=None: page.evaluate(js, arg)
            o = await T("""() => { const t = window.__tapnaplo, g = (id) => { const r = t.varietyOf(t.getFood(id)); return [r.state, r.id, r.source, r.flags]; };
              return { s: g('c:%s'), l: g('c:%s'), u: g('usda:%s'), d: g('dm:%s'), sizes: [t.VMAPS.ciqual.size, t.VMAPS.usda.size, t.VMAPS.dmbio.size], err: t.VMAP_ERR }; }""" % (CQ_SESAME, CQ_LIVER, US_MUSTARD, DM_LENTIL))
            check('the app reads the files the tool wrote: no problem, the four approved rows resolve with source "map" and the offal flag', o['err'] == '' and o['sizes'] == [2, 1, 1]
                  and o['s'] == ['ok', 'nut.seeds.sesame', 'map', []] and o['l'] == ['ok', 'mea.poultry.turkey', 'map', ['offal']] and o['u'] == ['ok', 'spi.dry-spices', 'map', []] and o['d'] == ['ok', 'leg.lentils.red-lentil', 'map', []], o)
            await ctx.close()
        finally:
            import shutil
            shutil.rmtree(tdir, ignore_errors=True)

        # =========================================================== 7. files, version, cache
        shell = sw.split('const SHELL')[1].split(']')[0]
        data = sw.split('const DATA')[1].split('}')[0]
        check('sw.js lists the three maps among the app files (network first, a newly approved row reaches the phone with the next version) and not among the data caches',
              all(f"'{f}'" in shell for f in FILES.values()) and not any('vt_map' in data for _ in [0]), shell[-200:])
        ctx = await new_ctx(); page = await new_page(ctx, 'v')
        tx = await data_text(page)
        await page.click('[data-tab=data]'); await page.wait_for_timeout(250)
        txt = await page.inner_text('body')
        ver = re.search(r'(\d+) · \d+ \w+ 20\d\d', txt)
        cv = re.search(r"CACHE = 'nutrilog-v(\d+)'", sw)
        check('the Data tab shows version 39 or newer and sw.js has the same cache number', bool(ver) and int(ver.group(1)) >= 39 and bool(cv) and cv.group(1) == ver.group(1), [ver and ver.group(0), cv and cv.group(0)])
        await ctx.close()
        check('no page error and no console error in any of the pages', errs == [], errs[:5])
        await browser.close()
        print('\n%d problem(s)' % len(problems))
        for x in problems: print(' -', x)
        sys.exit(1 if problems else 0)

asyncio.run(main())
