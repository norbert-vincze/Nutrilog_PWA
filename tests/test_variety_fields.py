"""Variety fields of a food, step L2 (version 38). Run with the web server on port 8765 (see CLAUDE.md); NUTRILOG_URL can point to another address.

Norbert's Variety plan (project doc nutrilog-valtozatossag-fejlesztesi-prompt.md, step L2): a food you made (or a saved Open Food Facts food) may carry three optional fields:
  vt   the id of a subgroup or a unit of the variety list (variety_units.json), missing = not classified
  vts  where it came from: map | manual | ai
  vf   attributes, a list of flag ids ("offal", only under mea.*), only with a vt
Nothing in the UI sets them yet (that is step L4); they come in through Paste from AI and Import foods (JSON), and they are kept by Edit food, Update existing, backup, Restore, Sync, the share link
and the entries CSV. Covers: the three pure functions (varietyClean, varietyFix, varietyOf) for every shape, the closed vocabulary of the import door (aiFood: unknown or malformed vt = left out + a
warning, never an error), Paste from AI end to end, Edit food and Update existing keep the group, Import foods (JSON), save and reload, damaged and unknown values in the store, backup and Restore
(with and without the fields, damaged), Sync with the fake GitHub (two devices, a damaged remote record), the share link (sender, hostile link, viewer writes nothing), the entries CSV columns, no new
required field when a food is made, the app without a variety list, the Data tab sentence, no new backup key, version and cache name."""
import asyncio, base64, csv, io, json, os, pathlib, re, sys
from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from test_sync import FakeGitHub, GOOD   # the fake GitHub of the sync test

URL = os.environ.get('NUTRILOG_URL', 'http://127.0.0.1:8765/index.html')
WATCH = """(() => {
  window.__w = { idbOpen: 0, idbWrite: 0, lsWrite: 0 };
  const o = indexedDB.open.bind(indexedDB); indexedDB.open = function () { window.__w.idbOpen++; return o.apply(this, arguments); };
  for (const m of ['put', 'add', 'delete', 'clear']) { const f = IDBObjectStore.prototype[m]; IDBObjectStore.prototype[m] = function () { window.__w.idbWrite++; return f.apply(this, arguments); }; }
  for (const m of ['setItem', 'removeItem', 'clear']) { const f = Storage.prototype[m]; Storage.prototype[m] = function () { window.__w.lsWrite++; return f.apply(this, arguments); }; }
})();"""


def own(fid, name='Test food', **kw):
    d = {'id': fid, 'src': 'user', 'name': name, 'brand': '', 'barcode': '', 'basis': {'qty': 100, 'unit': 'g'}, 'n': {'kcal': 50, 'protein': 2, 'carbohydrate': 8, 'fat': 1},
         'nova': None, 'portions': [], 'note': '', 'created': 1761750000000, 'updated': 1761750000000}
    d.update(kw)
    return d


def b64u(b):
    return base64.urlsafe_b64encode(b).decode().rstrip('=')


async def main():
    async with async_playwright() as p:
        problems = []

        def check(name, ok, info=''):
            print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(info)[:500].replace('\n', ' | ')) if info != '' else ''))
            if not ok: problems.append(name)

        browser = await p.chromium.launch()
        errs = []
        gh = FakeGitHub()

        async def new_ctx(gh_on=False, watch=False, w=390, h=844, nolist=False):
            ctx = await browser.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2, is_mobile=True, has_touch=True, locale='en-GB', service_workers='block', accept_downloads=True)
            if gh_on: await ctx.route('https://api.github.com/**', gh.handle)
            if nolist: await ctx.route('**/variety_units.json', lambda r: r.fulfill(status=404, body='not found'))
            await ctx.route('**/*openfoodfacts.org/**', lambda r: r.fulfill(status=200, headers={'access-control-allow-origin': '*', 'content-type': 'application/json'}, body='{"products":[],"status":0}'))
            if watch: await ctx.add_init_script(WATCH)
            return ctx

        async def new_page(ctx, name, goto=URL):
            pg = await ctx.new_page()
            pg.dname = name
            pg.on('pageerror', lambda e: errs.append(f'{name} PE {e}'))
            pg.on('console', lambda m: errs.append(f'{name} C {m.text}') if m.type == 'error' and 'Failed to load resource' not in m.text else None)
            await pg.goto(goto); await pg.wait_for_selector('.hero')
            return pg

        ctx = await new_ctx()
        page = await new_page(ctx, 'main')
        T = lambda js, arg=None: page.evaluate(js, arg)

        async def put_foods(foods, pg=None, day_entries=()):
            pg = pg or page
            await pg.evaluate("""([foods, entries]) => { const t = window.__tapnaplo, S = t.S; S.log.length = 0; for (const k of Object.keys(S.foods)) delete S.foods[k];
              for (const f of foods) S.foods[f.id] = f;
              entries.forEach(([id, f, a], i) => S.log.push({ id, f, a, d: S.day, m: 'm1', t: 1000 + i, tm: '08:' + String(10 + i) }));
              t.save(); t.render(); }""", [foods, list(day_entries)])
            await pg.wait_for_timeout(250)

        async def reload(pg):   # the open tab is remembered, so the Diary hero is not always there
            await pg.wait_for_timeout(300)
            await pg.reload(); await pg.wait_for_selector('#tabbar button.tab'); await pg.wait_for_timeout(400)

        async def food(fid, pg=None):
            return await (pg or page).evaluate("(id) => { const f = window.__tapnaplo.S.foods[id]; return f ? JSON.parse(JSON.stringify(f, (k, v) => (k[0] === '_' ? undefined : v))) : null; }", fid)

        async def vfields(fid, pg=None):
            f = await food(fid, pg)
            return None if f is None else {k: f[k] for k in ('vt', 'vts', 'vf') if k in f}

        # =========================================================== 1. the three pure functions
        r = await T("""() => { const t = window.__tapnaplo, c = (x) => JSON.parse(JSON.stringify(t.varietyClean(x))), o = (f) => { const r = t.varietyOf(f); return { state: r.state, id: r.id, level: r.node && r.node.level, source: r.source, flags: r.flags }; };
          const fx = (f) => { const bad = t.varietyFix(f); return [bad, JSON.parse(JSON.stringify(f))]; };
          const out = {};
          out.blank = [c({}), c({ vt: null, vts: null, vf: null }), c({ vt: '' }), c(null), c('x'), c([])];
          out.unit = c({ vt: 'veg.leaf.spinach' }); out.sub = c({ vt: 'veg.leaf' }); out.sep = c({ vt: 'bev.water' });
          out.shapes = ['veg', 'Veg.Leaf', 'veg leaf', 5, ['veg.leaf'], '<img src=x onerror=alert(1)>', '__proto__', 'a'.repeat(200), 'veg.leaf.spinach.extra', 'veg..leaf', 'veg.leaf.', ' veg.leaf', 've.leaf', 'vegetable.leaf']
            .map((v) => [typeof v === 'string' ? v.slice(0, 20) : String(v), c({ vt: v })]);
          out.src = ['map', 'manual', 'ai'].map((s) => c({ vt: 'veg.leaf.spinach', vts: s })); out.badsrc = [c({ vt: 'veg.leaf.spinach', vts: 'robot' }), c({ vt: 'veg.leaf.spinach', vts: 5 }), c({ vts: 'manual' })];
          out.offal = c({ vt: 'mea.red.beef', vf: ['offal'] }); out.offalVeg = c({ vt: 'veg.leaf.spinach', vf: ['offal'] }); out.dup = c({ vt: 'mea.red.beef', vf: ['offal', 'offal'] });
          out.vfText = c({ vt: 'mea.red.beef', vf: 'offal' }); out.vfMixed = c({ vt: 'mea.red.beef', vf: ['OFFAL!', 5, 'offal'] }); out.vfMany = c({ vt: 'mea.red.beef', vf: Array.from({ length: 11 }, (_, i) => 'f' + i) });
          out.vfUnknown = c({ vt: 'mea.red.beef', vf: ['organic'] }); out.vfEmpty = c({ vt: 'mea.red.beef', vf: [] }); out.vfOnly = c({ vf: ['offal'] });
          out.proto = c(JSON.parse('{"vt":"veg.leaf","__proto__":{"vt":"x"}}')); out.pollution = ({}).vt === undefined && Object.prototype.vt === undefined;
          const same = { vt: 'veg.leaf.spinach', vts: 'manual' }; out.fixOk = [t.varietyFix(same), same];
          const f1 = { vt: 'Bad!', vts: 'manual', vf: ['offal'], name: 'k' }; out.fixBad = fx(f1); out.fixSame = f1 === f1;
          out.fixNull = fx({ vt: null, vts: null, vf: null, name: 'k' }); out.fixSrc = fx({ vt: 'veg.leaf.spinach', vts: 'robot' }); out.fixNone = fx({ name: 'k' }); out.fixEmpty = fx({ vt: 'mea.red.beef', vf: [] });
          out.fixText = fx({ vt: '' , vts: 'ai' });
          out.of = [o({ src: 'user', vt: 'veg.leaf.spinach', vts: 'manual' }), o({ src: 'user', vt: 'veg.leaf' }), o({ src: 'off', vt: 'veg.leaf.spinach' }), o({ src: 'user', vt: 'mea.red.beef', vf: ['offal', 'organic'] }),
            o({ src: 'user', vt: 'veg.leaf.martian' }), o({ src: 'user', vt: 'xyz.abc' }), o({ src: 'user', vt: 'veg' }), o({ src: 'user', name: 'x' }), o({ src: 'ciqual', vt: 'veg.leaf.spinach' }), o({ src: 'usda', vt: 'veg.leaf.spinach' }), o(null), o(undefined), o({ src: 'user', vt: 'bev.water' })];
          return out; }""")
        none = {'v': None, 'bad': False}
        check('no group: nothing, nothing wrong (missing, null, empty text, not an object)', r['blank'] == [none] * 6, r['blank'])
        check('a unit id, a subgroup id and a subgroup of a separate group (no units there) are good groups', r['unit'] == {'v': {'vt': 'veg.leaf.spinach'}, 'bad': False} and r['sub']['v'] == {'vt': 'veg.leaf'} and r['sep']['v'] == {'vt': 'bev.water'} and not r['sep']['bad'])
        check('a malformed vt is dropped and said (main group alone, capitals, spaces, number, list, HTML, __proto__, 200 characters, too many parts, empty part, trailing dot, leading space, short or long main id)',
              all(v == {'v': None, 'bad': True} for _, v in r['shapes']) and len(r['shapes']) == 14, [(k, v) for k, v in r['shapes'] if v != {'v': None, 'bad': True}])
        check('vts: map, manual and ai are kept; another text or a number is dropped and said while the group stays; a source without a group means nothing (dropped, said)',
              [x['v'].get('vts') for x in r['src']] == ['map', 'manual', 'ai'] and all(not x['bad'] for x in r['src']) and all(x['v'] == {'vt': 'veg.leaf.spinach'} and x['bad'] for x in r['badsrc'][:2]) and r['badsrc'][2] == {'v': None, 'bad': True}, r['badsrc'])
        check('vf offal under mea.* is kept; under veg.* it is dropped and said (the group stays); the same flag twice is kept once', r['offal'] == {'v': {'vt': 'mea.red.beef', 'vf': ['offal']}, 'bad': False} and r['offalVeg'] == {'v': {'vt': 'veg.leaf.spinach'}, 'bad': True} and r['dup']['v']['vf'] == ['offal'] and not r['dup']['bad'], [r['offal'], r['offalVeg']])
        check('vf that is not a list, has a malformed flag (the good one stays) or has more than 10 flags is dropped and said; an empty list is simply no flags', r['vfText'] == {'v': {'vt': 'mea.red.beef'}, 'bad': True} and r['vfMixed'] == {'v': {'vt': 'mea.red.beef', 'vf': ['offal']}, 'bad': True} and r['vfMany'] == {'v': {'vt': 'mea.red.beef'}, 'bad': True} and r['vfEmpty'] == {'v': {'vt': 'mea.red.beef'}, 'bad': False}, [r['vfText'], r['vfMixed'], r['vfMany']])
        check('a well-formed flag this list does not know ("organic") is kept in storage (a later list may know it); a flag without a group is dropped and said', r['vfUnknown'] == {'v': {'vt': 'mea.red.beef', 'vf': ['organic']}, 'bad': False} and r['vfOnly'] == {'v': None, 'bad': True}, r['vfUnknown'])
        check('an own "__proto__" key in JSON does nothing, and nothing is added to Object.prototype', r['proto']['v'] == {'vt': 'veg.leaf'} and r['pollution'] is True)
        check('varietyFix works in place: a good group returns false and stays; a bad one returns true and all three fields are gone; the other fields stay', r['fixOk'] == [False, {'vt': 'veg.leaf.spinach', 'vts': 'manual'}] and r['fixBad'] == [True, {'name': 'k'}] and r['fixSame'], [r['fixOk'], r['fixBad']])
        check('...null and empty text are removed without a complaint; a bad vts is removed and said (vt stays); a food without the keys is left alone; an empty vf is removed',
              r['fixNull'] == [False, {'name': 'k'}] and r['fixSrc'] == [True, {'vt': 'veg.leaf.spinach'}] and r['fixNone'] == [False, {'name': 'k'}] and r['fixEmpty'] == [False, {'vt': 'mea.red.beef'}] and r['fixText'] == [True, {}], [r['fixNull'], r['fixSrc'], r['fixText']])
        o = r['of']
        check('varietyOf: a unit (manual), a subgroup, a saved Open Food Facts food, offal flag (the unknown "organic" is not shown)', o[0] == {'state': 'ok', 'id': 'veg.leaf.spinach', 'level': 'unit', 'source': 'manual', 'flags': []} and o[1]['state'] == 'ok' and o[1]['level'] == 'sub' and o[2]['state'] == 'ok' and o[3]['flags'] == ['offal'], o[:4])
        check('varietyOf: a well-formed id the list does not have is "unknown" (the id is kept, it counts as not classified); a main group alone, no field, null and undefined are "none"',
              o[4] == {'state': 'unknown', 'id': 'veg.leaf.martian', 'level': None, 'source': None, 'flags': []} and o[5]['state'] == 'unknown' and o[6]['state'] == 'none' and o[7]['state'] == 'none' and o[10]['state'] == 'none' and o[11]['state'] == 'none' and o[12]['state'] == 'ok', o[4:])
        check('varietyOf: CIQUAL and USDA foods are not read from the record (their groups come from map files in step L3)', o[8]['state'] == 'none' and o[9]['state'] == 'none', o[8:10])

        # =========================================================== 2. the import door (aiFood): closed vocabulary
        ai = await T("""() => { const t = window.__tapnaplo;
          const mk = (extra, id = 'u:x') => JSON.stringify({ app: 'tapnaplo', version: 1, foods: { [id]: Object.assign({ id, src: 'user', name: 'Imp', basis: { qty: 100, unit: 'g' }, n: { kcal: 50, protein: 2, carbohydrate: 8, fat: 1 } }, extra) } });
          const run = (extra) => { const r = t.parseAiImport(mk(extra)); const f = r.foods[0] && r.foods[0].food; return { errors: r.errors, n: r.foods.length, v: f ? ['vt', 'vts', 'vf'].filter((k) => k in f).reduce((a, k) => (a[k] = f[k], a), {}) : null, w: r.foods[0] ? r.foods[0].warnings : [] }; };
          const out = {};
          out.none = run({}); out.nulls = run({ vt: null, vts: null, vf: null }); out.unit = run({ vt: 'veg.leaf.spinach' }); out.sub = run({ vt: 'veg.leaf' }); out.sep = run({ vt: 'bev.water' }); out.manual = run({ vt: 'veg.leaf.spinach', vts: 'manual' }); out.trim = run({ vt: '  veg.leaf.spinach ' });
          out.unknown = run({ vt: 'veg.leaf.martian' }); out.main = run({ vt: 'veg' }); out.text = run({ vt: 'Spinach' }); out.caps = run({ vt: 'VEG.LEAF.SPINACH' }); out.num = run({ vt: 5 }); out.list = run({ vt: ['veg.leaf'] }); out.html = run({ vt: '<img src=x onerror=window.__pwn=1>' });
          out.robot = run({ vt: 'veg.leaf.spinach', vts: 'robot' }); out.offal = run({ vt: 'mea.red.beef', vf: ['offal'] }); out.offalVeg = run({ vt: 'veg.leaf.spinach', vf: ['offal'] }); out.flagUnknown = run({ vt: 'mea.red.beef', vf: ['organic'] });
          out.flagText = run({ vt: 'mea.red.beef', vf: 'offal' }); out.flagBad = run({ vt: 'mea.red.beef', vf: ['Offal!', 7] }); out.flagMany = run({ vt: 'mea.red.beef', vf: Array.from({ length: 11 }, (_, i) => 'f' + i) });
          out.vfOnly = run({ vf: ['offal'] }); out.vtsOnly = run({ vts: 'manual' }); out.unknownWithRest = run({ vt: 'veg.leaf.martian', vts: 'manual', vf: ['offal'] });
          const ff = t.parseFoodsFile(mk({ vt: 'veg.leaf.martian' })); out.file = { error: ff.error, n: ff.foods.length, invalid: ff.invalid.length, w: ff.foods[0].warnings, vt: 'vt' in ff.foods[0].food };
          const fg = t.parseFoodsFile(mk({ vt: 'mea.red.beef', vts: 'manual', vf: ['offal'] })); out.fileOk = { w: fg.foods[0].warnings, f: ['vt', 'vts', 'vf'].map((k) => fg.foods[0].food[k]) };
          return out; }""")
        vwarn = lambda x: [w for w in x['w'] if 'vt' in w or 'vts' in w or 'vf' in w or 'variety' in w or 'flag' in w.lower()]
        check('no variety keys in the answer: no variety keys in the food, no warning (an old answer works as before); null values are the same', ai['none']['v'] == {} and vwarn(ai['none']) == [] and ai['nulls']['v'] == {} and vwarn(ai['nulls']) == [] and ai['none']['errors'] == [])
        check('a unit, a subgroup, a separate-group subgroup: kept, vts is "ai" when the answer does not say, no warning', all(ai[k]['v'] == {'vt': vt, 'vts': 'ai'} and vwarn(ai[k]) == [] for k, vt in (('unit', 'veg.leaf.spinach'), ('sub', 'veg.leaf'), ('sep', 'bev.water'), ('trim', 'veg.leaf.spinach'))), [ai[k]['v'] for k in ('unit', 'sub', 'sep', 'trim')])
        check('vts "manual" in the answer is kept (a food exported from a backup keeps its source)', ai['manual']['v'] == {'vt': 'veg.leaf.spinach', 'vts': 'manual'} and vwarn(ai['manual']) == [])
        check('vt that is not in the list (closed vocabulary): left out with a warning, the food is still loaded, no error', ai['unknown']['v'] == {} and ai['unknown']['n'] == 1 and ai['unknown']['errors'] == [] and len(vwarn(ai['unknown'])) == 1 and 'not in the variety list' in vwarn(ai['unknown'])[0], ai['unknown']['w'])
        check('vt of a wrong shape (main group alone, plain text, capitals, number, list, HTML): left out with a warning, never an error, never repaired', all(ai[k]['v'] == {} and ai[k]['n'] == 1 and ai[k]['errors'] == [] and len(vwarn(ai[k])) == 1 and 'must be the id' in vwarn(ai[k])[0] for k in ('main', 'text', 'caps', 'num', 'list', 'html')), [ai[k]['w'] for k in ('main', 'text', 'caps')])
        check('a bad vts becomes "ai" with a warning; offal under mea.* is kept; under veg.* it is left out with a warning (the group stays)', ai['robot']['v'] == {'vt': 'veg.leaf.spinach', 'vts': 'ai'} and any('set to ai' in w for w in ai['robot']['w']) and ai['offal']['v'] == {'vt': 'mea.red.beef', 'vts': 'ai', 'vf': ['offal']} and vwarn(ai['offal']) == []
              and ai['offalVeg']['v'] == {'vt': 'veg.leaf.spinach', 'vts': 'ai'} and any('only for mea.*' in w for w in ai['offalVeg']['w']), [ai['robot']['w'], ai['offalVeg']['w']])
        check('a flag the list does not have, a vf that is not a list, a malformed flag or more than 10 flags: left out with a warning', ai['flagUnknown']['v'] == {'vt': 'mea.red.beef', 'vts': 'ai'} and any('not in the variety list' in w for w in ai['flagUnknown']['w']) and 'vf' not in ai['flagText']['v'] and any('must be a list' in w for w in ai['flagText']['w'])
              and 'vf' not in ai['flagBad']['v'] and len(vwarn(ai['flagBad'])) == 2 and 'vf' not in ai['flagMany']['v'] and any('more than 10' in w for w in ai['flagMany']['w']), [ai['flagUnknown']['w'], ai['flagBad']['w']])
        check('vts or vf without a valid vt: left out with one warning; an unknown vt takes its vts and vf with it (nothing half-classified)', ai['vfOnly']['v'] == {} and any('need a valid' in w for w in ai['vfOnly']['w']) and ai['vtsOnly']['v'] == {} and any('need a valid' in w for w in ai['vtsOnly']['w']) and ai['unknownWithRest']['v'] == {} and any('not in the variety list' in w for w in ai['unknownWithRest']['w']), [ai['vfOnly']['w'], ai['unknownWithRest']['w']])
        check('Import foods (JSON) reads the same way: an unknown vt is a warning (not invalid), a good group with vts and vf is kept', not ai['file']['error'] and ai['file']['n'] == 1 and ai['file']['invalid'] == 0 and ai['file']['vt'] is False and any('not in the variety list' in w for w in ai['file']['w']) and ai['fileOk']['f'] == ['mea.red.beef', 'manual', ['offal']] and ai['fileOk']['w'] == [], [ai['file'], ai['fileOk']])

        # =========================================================== 3. Paste from AI end to end, Edit food, Update existing
        def doc(**extra):
            f = {'id': 'u:imp', 'src': 'user', 'name': 'Wild spinach', 'brand': 'Garden', 'barcode': '4000000000024', 'basis': {'qty': 100, 'unit': 'g'}, 'n': {'kcal': 23, 'protein': 2.9, 'carbohydrate': 1.4, 'fat': 0.4}}
            f.update(extra)
            return json.dumps({'app': 'tapnaplo', 'version': 1, 'foods': {'u:imp': f}})

        async def paste(text, dup=None):
            await page.click('[data-tab=foods]'); await page.wait_for_selector('#ffilter')
            await page.click('[data-act=ai-import]'); await page.wait_for_selector('#ai-text')
            await page.fill('#ai-text', text); await page.click('#ai-read'); await page.wait_for_selector('#fok')
            await page.click('#fok')
            if dup:
                await page.wait_for_selector('[data-dup]'); await page.click(f'[data-dup={dup}]')
            await page.wait_for_timeout(400)

        async def named(name):
            return await T("(n) => { const f = Object.values(window.__tapnaplo.S.foods).find((x) => x.name === n); return f ? JSON.parse(JSON.stringify(f, (k, v) => (k[0] === '_' ? undefined : v))) : null; }", name)

        await put_foods([])
        await paste(doc(vt='veg.leaf.spinach', vts='manual'))
        f = await named('Wild spinach')
        check('Paste from AI > review editor > Save: the food is saved with vt and vts from the answer', f is not None and f.get('vt') == 'veg.leaf.spinach' and f.get('vts') == 'manual' and 'vf' not in f, f and {k: f.get(k) for k in ('vt', 'vts', 'vf')})
        fid = f['id']
        # Edit food: change the name, save: the group stays
        await page.click('[data-tab=foods]'); await page.wait_for_selector('#ffilter')
        await page.click(f'[data-act=edit-food][data-id="{fid}"]'); await page.wait_for_selector('#fname')
        edit_text = (await page.inner_text('.sheet')).lower()
        check('the Edit food sheet has no variety field yet (the screen comes in step L4)', 'variety' not in edit_text and 'vt' not in await T("[...document.querySelectorAll('.sheet input, .sheet select')].map((e) => e.id).join(' ')"), '')
        await page.fill('#fname', 'Wild spinach, renamed'); await page.click('#fok'); await page.wait_for_timeout(400)
        f2 = await food(fid)
        check('Edit food: after changing the name the group, its source and the id are unchanged', f2['name'] == 'Wild spinach, renamed' and f2.get('vt') == 'veg.leaf.spinach' and f2.get('vts') == 'manual' and f2['id'] == fid, {k: f2.get(k) for k in ('name', 'vt', 'vts')})
        await T("(id) => { const f = window.__tapnaplo.S.foods[id]; f.name = 'Wild spinach'; window.__tapnaplo.save(); }", fid)
        # Update existing, answer without vt: the old group stays
        await paste(doc(), dup='update')
        f3 = await food(fid)
        check('Update existing with an answer that has no vt: the old group and its source stay (like barcode, NOVA and note)', f3.get('vt') == 'veg.leaf.spinach' and f3.get('vts') == 'manual' and f3['id'] == fid and len([1 for x in await T("Object.values(window.__tapnaplo.S.foods)") if x['name'] == 'Wild spinach']) == 1, {k: f3.get(k) for k in ('vt', 'vts', 'vf')})
        # Update existing with a new group, and with a flag: the new group replaces vt/vts/vf
        await T("(id) => { const f = window.__tapnaplo.S.foods[id]; f.vt = 'mea.red.beef'; f.vts = 'manual'; f.vf = ['offal']; window.__tapnaplo.save(); }", fid)
        await paste(doc(vt='veg.root.carrot'), dup='update')
        f4 = await food(fid)
        check('Update existing with a new vt replaces the group, takes vts "ai" and drops the old flags (a flag of the old group does not stay on the new one)', f4.get('vt') == 'veg.root.carrot' and f4.get('vts') == 'ai' and 'vf' not in f4, {k: f4.get(k) for k in ('vt', 'vts', 'vf')})
        # an unknown vt in the answer: the sheet shows the warning, the food is saved without a group, the old group stays on Update
        await page.click('[data-tab=foods]'); await page.wait_for_selector('#ffilter')
        await page.click('[data-act=ai-import]'); await page.wait_for_selector('#ai-text')
        await page.fill('#ai-text', doc(name='Martian cress', brand='Mars', barcode='4000000000031', vt='veg.leaf.martian', vts='manual', vf=['offal'])); await page.click('#ai-read'); await page.wait_for_selector('#fok')
        notice = await page.locator('.sheet').last.inner_text()
        check('Paste from AI with an unknown vt: the review sheet shows the warning (the group is not in the list, so it is left out)', 'not in the variety list' in notice and 'left out' in notice, notice[:300])
        await page.click('#fok'); await page.wait_for_timeout(400)
        mc = await named('Martian cress')
        check('...the food can still be saved (it is only a warning): it has no vt, vts or vf of its own, so it is not classified', mc is not None and not any(k in mc for k in ('vt', 'vts', 'vf')), mc and list(mc))
        # Create food through the editor: no variety field is needed, the new food has no vt/vts/vf
        await page.click('[data-tab=foods]'); await page.wait_for_selector('#ffilter')
        await page.click('[data-act=new-food]'); await page.wait_for_selector('#fname')
        await page.fill('#fname', 'Plain new food'); await page.fill('#n_kcal', '120'); await page.click('#fok'); await page.wait_for_timeout(400)
        nf = await named('Plain new food')
        check('Create food: no variety field is asked, and the new food has no vt, vts or vf', nf is not None and not any(k in nf for k in ('vt', 'vts', 'vf')), nf and list(nf))

        # =========================================================== 4. Import foods (JSON): unknown vt = warning, the rest loads
        await put_foods([])
        file_foods = {
            'u:imp1': own('u:imp1', 'File food one', vt='mea.red.beef', vts='manual', vf=['offal']),
            'u:imp2': own('u:imp2', 'File food two', vt='veg.leaf.martian', vts='manual'),
            'u:imp3': own('u:imp3', 'File food three'),
            'u:imp4': own('u:imp4', 'File food four <img src=x onerror=window.__pwn=1>', vt='<b>x</b>'),
        }
        buf = json.dumps({'app': 'tapnaplo', 'version': 1, 'foods': file_foods}).encode()
        await page.click('[data-tab=data]'); await page.wait_for_selector('#importfoods', state='attached')
        await page.set_input_files('#importfoods', files=[{'name': 'foods.json', 'mimeType': 'application/json', 'buffer': buf}])
        await page.wait_for_selector('.sheet [data-fi=skip]', timeout=5000)
        sheet = await page.inner_text('.sheet')
        check('Import foods (JSON): the sheet opens (there are warnings), names the unknown group and the wrong shape, and offers "Import 4 foods"', 'not in the variety list' in sheet and 'must be the id' in sheet and 'Import 4 foods' in sheet, sheet[:300])
        check('...hostile text in a name or in vt is shown as text only (no element, no script)', await T("document.querySelectorAll('img[src=x], script:not([src])[data-x], #sheets script').length") == 0 and await T("window.__pwn === undefined"))
        await page.click('[data-fi=skip]'); await page.wait_for_timeout(500)
        got = {i: await vfields(i) for i in ('u:imp1', 'u:imp2', 'u:imp3', 'u:imp4')}
        check('after the import: the good group (with vts and vf) is kept, the unknown and malformed groups are not on the foods, the food without a group has none', got['u:imp1'] == {'vt': 'mea.red.beef', 'vts': 'manual', 'vf': ['offal']} and got['u:imp2'] == {} and got['u:imp3'] == {} and got['u:imp4'] == {}, got)
        check('...and all four foods were imported (a variety warning never blocks a food)', len(await T("Object.keys(window.__tapnaplo.S.foods)")) == 4)
        # a file that has only Undo-able overwrite: the group of the file replaces the old one
        await page.click('[data-tab=data]'); await page.wait_for_selector('#importfoods', state='attached')
        await T("() => { const f = window.__tapnaplo.S.foods['u:imp1']; f.vt = 'veg.leaf.spinach'; f.vts = 'manual'; window.__tapnaplo.save(); }")
        buf2 = json.dumps({'app': 'tapnaplo', 'version': 1, 'foods': {'u:imp1': own('u:imp1', 'File food one', vt='veg.root.carrot', vts='ai')}}).encode()
        await page.set_input_files('#importfoods', files=[{'name': 'foods.json', 'mimeType': 'application/json', 'buffer': buf2}])
        await page.wait_for_selector('.sheet [data-fi=over]', timeout=5000)
        await page.click('[data-fi=over]'); await page.wait_for_timeout(500)
        check('Import foods (JSON) > Overwrite: the group of the file replaces the old group (the whole food is replaced, as before)', await vfields('u:imp1') == {'vt': 'veg.root.carrot', 'vts': 'ai'}, await vfields('u:imp1'))

        # =========================================================== 5. save and reload; old saves; damaged and unknown values in the store
        await put_foods([own('u:a', 'Alpha', vt='veg.leaf.spinach', vts='manual'), own('u:b', 'Beta', vt='mea.red.beef', vts='ai', vf=['offal']), own('u:c', 'Gamma'), own('u:d', 'Delta', vt='veg.leaf', vts='map')])
        before = {i: await vfields(i) for i in ('u:a', 'u:b', 'u:c', 'u:d')}
        await reload(page)
        after = {i: await vfields(i) for i in ('u:a', 'u:b', 'u:c', 'u:d')}
        check('save and reload: the fields come back exactly (vt, vts, vf), and a food without them has none', after == before and after['u:c'] == {} and after['u:b'] == {'vt': 'mea.red.beef', 'vts': 'ai', 'vf': ['offal']}, after)
        check('...no toast about a variety group on a clean store', 'variety' not in (await T("document.querySelector('#toast span') ? document.querySelector('#toast span').textContent : ''")))
        await T("""async () => { const db = await new Promise((res) => { const r = indexedDB.open('tapnaplo', 1); r.onsuccess = () => res(r.result); });
          const mk = (id, extra) => Object.assign({ id, src: 'user', name: id, brand: '', barcode: '', basis: { qty: 100, unit: 'g' }, n: { kcal: 10 }, nova: null, portions: [], note: '' }, extra);
          await new Promise((res) => { const tx = db.transaction('kv', 'readwrite'); tx.objectStore('kv').put({
            'u:ok': mk('u:ok', { vt: 'veg.leaf.spinach', vts: 'manual' }), 'u:bad': mk('u:bad', { vt: 'Bad!', vts: 'manual', vf: ['offal'] }), 'u:unk': mk('u:unk', { vt: 'veg.leaf.martian', vts: 'ai' }),
            'u:src': mk('u:src', { vt: 'veg.leaf', vts: 'robot' }), 'u:flag': mk('u:flag', { vt: 'veg.leaf', vf: ['offal'] }), 'u:null': mk('u:null', { vt: null, vts: null, vf: null }), 'u:old': mk('u:old', {}) }, 'foods'); tx.oncomplete = res; }); }""")
        await reload(page)
        st = {i: await vfields(i) for i in ('u:ok', 'u:bad', 'u:unk', 'u:src', 'u:flag', 'u:null', 'u:old')}
        check('damaged fields in the store are dropped, never repaired (bad vt: all three gone; bad vts: vt stays; offal under veg: the flag goes; null: no keys)',
              st['u:ok'] == {'vt': 'veg.leaf.spinach', 'vts': 'manual'} and st['u:bad'] == {} and st['u:src'] == {'vt': 'veg.leaf'} and st['u:flag'] == {'vt': 'veg.leaf'} and st['u:null'] == {} and st['u:old'] == {}, st)
        check('a well-formed id this list does not know is kept in the record (nothing is lost) and counts as not classified', st['u:unk'] == {'vt': 'veg.leaf.martian', 'vts': 'ai'} and await T("window.__tapnaplo.varietyOf(window.__tapnaplo.S.foods['u:unk']).state") == 'unknown')
        toast = await T("document.querySelector('#toast') && !document.querySelector('#toast').hidden ? document.querySelector('#toast span').textContent : ''")
        check('the person is told how many foods had a damaged variety group (3: bad vt, bad vts, offal under veg) and that they are not classified', '3 foods had a variety group that could not be read' in toast and 'not classified' in toast, toast)
        await page.click('[data-tab=data]'); await page.wait_for_timeout(300)
        dt = await page.inner_text('body')
        check('the Data tab says how many of your foods have a group this version does not know (1), as "not classified"', 'Variety list: 164 units in 17 groups.' in dt and '1 food of yours has a variety group this version of the app does not know; it counts as not classified.' in dt, re.findall(r'Variety list[^\n]*', dt))
        await put_foods([own('u:a', 'Alpha', vt='veg.leaf.spinach')])
        await page.click('[data-tab=data]'); await page.wait_for_timeout(300)
        check('...and says nothing about it when every group is known', 'does not know' not in await page.inner_text('body'))

        # =========================================================== 6. backup and Restore
        await put_foods([own('u:a', 'Alpha', vt='veg.leaf.spinach', vts='manual'), own('u:b', 'Beta', vt='mea.red.beef', vts='ai', vf=['offal']), own('u:c', 'Gamma'), own('u:u', 'Unknown', vt='veg.leaf.martian', vts='ai')])
        await page.click('[data-tab=data]'); await page.wait_for_selector('[data-act=export-json]')
        async with page.expect_download() as dl:
            await page.click('[data-act=export-json]')
        bk = json.loads(pathlib.Path(await (await dl.value).path()).read_text(encoding='utf-8'))
        check('the backup keeps vt, vts and vf of your own foods, also an id this list does not know; a food without them has no such key', bk['foods']['u:a']['vt'] == 'veg.leaf.spinach' and bk['foods']['u:a']['vts'] == 'manual' and bk['foods']['u:b']['vf'] == ['offal'] and bk['foods']['u:u']['vt'] == 'veg.leaf.martian'
              and not any(k in bk['foods']['u:c'] for k in ('vt', 'vts', 'vf')), {k: bk['foods']['u:b'].get(k) for k in ('vt', 'vts', 'vf')})
        check('the backup has no new top-level key (the same keys as in version 37)', sorted(bk.keys()) == sorted(['app', 'version', 'exported', 'log', 'foods', 'meta', 'health', 'wlog']), sorted(bk.keys()))

        async def restore(obj, pg=None, confirm=True):
            pg = pg or page
            await pg.click('[data-tab=data]'); await pg.wait_for_selector('#importfile', state='attached')
            await pg.set_input_files('#importfile', files=[{'name': 'b.json', 'mimeType': 'application/json', 'buffer': json.dumps(obj).encode()}])
            await pg.wait_for_selector('.sheet, #toast', timeout=5000)
            text = None
            if confirm and await pg.locator('.sheet [data-ok]').count():
                text = await pg.inner_text('.sheet')
                await pg.click('.sheet [data-ok]'); await pg.wait_for_selector('.sheet', state='detached')
            await pg.wait_for_timeout(300)
            return text
        ctxR = await new_ctx(); R = await new_page(ctxR, 'R')
        txt = await restore(bk, R)
        rr = {i: await vfields(i, R) for i in ('u:a', 'u:b', 'u:c', 'u:u')}
        check('Restore of that backup on another device: every group, source and flag comes back; the confirm text does not mention variety (nothing is wrong)', rr['u:a'] == {'vt': 'veg.leaf.spinach', 'vts': 'manual'} and rr['u:b'] == {'vt': 'mea.red.beef', 'vts': 'ai', 'vf': ['offal']} and rr['u:c'] == {} and rr['u:u']['vt'] == 'veg.leaf.martian' and 'variety' not in (txt or '').lower(), [rr, txt])
        old = {'app': 'tapnaplo', 'version': 1, 'log': [], 'foods': {'u:o': own('u:o', 'From v37')}, 'meta': {}}
        txt = await restore(old, R)
        check('a backup from before version 38 (no variety fields) loads as it did, and the food has none', await vfields('u:o', R) == {} and 'variety' not in (txt or '').lower(), txt)
        dmg = {'app': 'tapnaplo', 'version': 1, 'log': [], 'foods': {'u:g1': own('u:g1', 'Good', vt='veg.leaf.spinach', vts='manual'), 'u:g2': own('u:g2', 'Bad one', vt='Bad!', vts='manual', vf=['offal']), 'u:g3': own('u:g3', 'Bad src', vt='veg.leaf', vts='robot')}, 'meta': {}}
        txt = await restore(dmg, R)
        check('a backup with damaged groups: the confirm text counts them (2 foods) and says they are restored as not classified', txt is not None and '2 foods in the file have a variety group that is not valid; they are restored as not classified.' in txt, txt)
        toast = await R.evaluate("document.querySelector('#toast') && !document.querySelector('#toast').hidden ? document.querySelector('#toast span').textContent : ''")
        gg = {i: await vfields(i, R) for i in ('u:g1', 'u:g2', 'u:g3')}
        check('...the foods are restored without the damaged fields (the good group stays, a bad vts goes alone) and the toast says "2 variety groups skipped: not valid"', gg['u:g1'] == {'vt': 'veg.leaf.spinach', 'vts': 'manual'} and gg['u:g2'] == {} and gg['u:g3'] == {'vt': 'veg.leaf'} and '2 variety groups skipped: not valid' in toast, [gg, toast])
        await ctxR.close()

        # =========================================================== 7. Sync with the fake GitHub: two devices
        await put_foods([own('u:sy', 'Synced beef', vt='mea.red.beef', vts='manual', vf=['offal']), own('u:sp', 'Plain synced')])

        async def connect(pg):
            await pg.click('[data-tab=data]'); await pg.wait_for_selector('[data-act=sync-setup]')
            await pg.click('[data-act=sync-setup]'); await pg.fill('#sy-repo', 'me/nutrilog-data'); await pg.fill('#sy-token', GOOD); await pg.click('[data-ok]')
            for _ in range(3):
                await pg.wait_for_function('!window.__tapnaplo.SY.busy')
                await pg.evaluate("window.__tapnaplo.syncRun('manual')")
            await pg.wait_for_function('!window.__tapnaplo.SY.busy')

        async def rounds(*pgs):
            for pg in pgs:
                for _ in range(2):
                    await pg.wait_for_function('!window.__tapnaplo.SY.busy')
                    await pg.evaluate("window.__tapnaplo.syncRun('manual')")
                await pg.wait_for_function('!window.__tapnaplo.SY.busy')
        ctxA = await new_ctx(gh_on=True); A = await new_page(ctxA, 'A')
        await put_foods([own('u:sy', 'Synced beef', vt='mea.red.beef', vts='manual', vf=['offal']), own('u:sp', 'Plain synced')], A)
        await connect(A)
        rec = gh.recs().get('f:u:sy'); rp = gh.recs().get('f:u:sp')
        check('Sync: the repository record of the food has vt, vts and vf; a food without a group has none of them', rec is not None and rec['x'].get('vt') == 'mea.red.beef' and rec['x'].get('vts') == 'manual' and rec['x'].get('vf') == ['offal'] and rp is not None and not any(k in rp['x'] for k in ('vt', 'vts', 'vf')), [rec and rec['x'], rp and rp['x']])
        ctxB = await new_ctx(gh_on=True); B = await new_page(ctxB, 'B')
        await connect(B)
        check('Sync: the second device has the food with its group, source and flag', await vfields('u:sy', B) == {'vt': 'mea.red.beef', 'vts': 'manual', 'vf': ['offal']} and await vfields('u:sp', B) == {}, await vfields('u:sy', B))
        await B.evaluate("() => { const t = window.__tapnaplo, f = t.S.foods['u:sy']; f.vt = 'veg.root.carrot'; f.vts = 'ai'; delete f.vf; t.save(); }")
        await rounds(B, A, B, A)
        check('Sync: a change of the group on B (new vt, vts, flag removed) reaches A', await vfields('u:sy', A) == {'vt': 'veg.root.carrot', 'vts': 'ai'}, await vfields('u:sy', A))
        # damaged record: A sends a food with a malformed group (set in memory after the start), B cleans it when it receives it
        await A.evaluate("() => { const t = window.__tapnaplo, f = t.S.foods['u:sp']; f.vt = 'Bad!'; f.vts = 'manual'; f.vf = ['offal']; t.save(); }")
        await rounds(A, B, A, B)
        check('Sync: a food that arrives with a malformed group is received without it (the food stays, nothing is repaired or guessed)', (await food('u:sp', B)) is not None and await vfields('u:sp', B) == {}, await vfields('u:sp', B))
        await ctxA.close(); await ctxB.close()

        # =========================================================== 8. share link
        D = '2026-11-10'
        await T("""([D]) => { const t = window.__tapnaplo, S = t.S; S.log.length = 0; for (const k of Object.keys(S.foods)) delete S.foods[k];
          const mk = (id, name, extra) => Object.assign({ id, src: 'user', name, brand: '', barcode: '', basis: { qty: 100, unit: 'g' }, n: { kcal: 40, protein: 3 }, nova: null, portions: [], note: 'private note' }, extra);
          S.foods['u:s1'] = mk('u:s1', 'Shared beef', { vt: 'mea.red.beef', vts: 'manual', vf: ['offal'] }); S.foods['u:s2'] = mk('u:s2', 'Shared plain', {}); S.foods['u:s3'] = mk('u:s3', 'Shared unknown', { vt: 'veg.leaf.martian', vts: 'ai' });
          S.foods['u:s4'] = mk('u:s4', 'Shared flag', { vt: 'veg.leaf.spinach', vf: ['offal'] });
          S.log.push({ id: 'e1', f: 'u:s1', a: 100, d: D, m: 'm1', t: 1, tm: '08:10' }, { id: 'e2', f: 'u:s2', a: 100, d: D, m: 'm1', t: 2, tm: '08:20' }, { id: 'e3', f: 'u:s3', a: 100, d: D, m: 'm1', t: 3, tm: '08:30' }, { id: 'e4', f: 'u:s4', a: 100, d: D, m: 'm1', t: 4, tm: '08:40' });
          t.save(); }""", [D])
        snap = json.loads(await T("([D]) => window.__tapnaplo.shareSnapshot(D, D).json", [D]))
        sf = {f['id']: f for f in snap['foods']}
        check('the link carries vt, vts and vf of the foods in it (also an id this list does not know); a food without them looks exactly as before; the private note is not in it', sf['u:s1'].get('vt') == 'mea.red.beef' and sf['u:s1'].get('vts') == 'manual' and sf['u:s1'].get('vf') == ['offal'] and sf['u:s3'].get('vt') == 'veg.leaf.martian'
              and not any(k in sf['u:s2'] for k in ('vt', 'vts', 'vf')) and 'private note' not in json.dumps(snap), [sf['u:s1'], sf['u:s2']])
        check('...a flag on a group it does not belong to (offal under veg) is not sent', 'vf' not in sf['u:s4'] and sf['u:s4'].get('vt') == 'veg.leaf.spinach', sf['u:s4'])
        check('the format stays v1, and the keys of the link are the same as without the fields', snap['v'] == 1 and sorted(snap.keys()) == sorted(['app', 'v', 'made', 'from', 'to', 'refs', 'foods', 'nova', 'days']), sorted(snap.keys()))
        link_ = await T("([D]) => window.__tapnaplo.shareLink(D, D).then((r) => r.url)", [D])
        ctxV = await new_ctx(watch=True); V = await new_page(ctxV, 'V', goto=link_)
        vv = {i: await vfields(i, V) for i in ('u:s1', 'u:s2', 'u:s3')}
        w = await V.evaluate("window.__w")
        check('the viewer has the same groups (read only, in memory); it writes nothing and does not even open the storage of the browser', vv['u:s1'] == {'vt': 'mea.red.beef', 'vts': 'manual', 'vf': ['offal']} and vv['u:s2'] == {} and vv['u:s3']['vt'] == 'veg.leaf.martian' and w == {'idbOpen': 0, 'idbWrite': 0, 'lsWrite': 0}, [vv, w])
        await ctxV.close()
        hostile = {'app': 'tapnaplo-share', 'v': 1, 'made': 1761750000000, 'from': D, 'to': D, 'refs': ['u:h1', 'u:h2', 'u:h3'], 'nova': {},
                   'foods': [{'id': 'u:h1', 'src': 'user', 'name': 'Hostile one', 'basis': {'qty': 100, 'unit': 'g'}, 'n': {'kcal': 10}, 'vt': '<img src=x onerror=window.__pwn=1>', 'vts': 'robot', 'vf': ['offal']},
                             {'id': 'u:h2', 'src': 'user', 'name': 'Hostile two', 'basis': {'qty': 100, 'unit': 'g'}, 'n': {'kcal': 10}, 'vt': '__proto__', 'vf': '<b>x</b>'},
                             {'id': 'u:h3', 'src': 'user', 'name': 'Fine three', 'basis': {'qty': 100, 'unit': 'g'}, 'n': {'kcal': 10}, 'vt': 'veg.leaf.spinach', 'vts': 'ai', 'vf': ['x'] * 50}],
                   'days': {D: [['m1', 0, '08:00', 100], ['m1', 1, '08:10', 100], ['m1', 2, '08:20', 100]]}}
        ctxH = await new_ctx(watch=True); H = await new_page(ctxH, 'H', goto=URL + '#share=j.' + b64u(json.dumps(hostile).encode()))
        hh = {i: await vfields(i, H) for i in ('u:h1', 'u:h2', 'u:h3')}
        check('a hostile link: the groups of a wrong shape are left out and the link still opens (no script runs); a good group with a flood of flags keeps the group only; nothing is written',
              hh['u:h1'] == {} and hh['u:h2'] == {} and hh['u:h3'] == {'vt': 'veg.leaf.spinach', 'vts': 'ai'} and await H.evaluate("window.__pwn === undefined && !document.body.innerHTML.includes('<img src=x')") and await H.evaluate("window.__w.idbWrite + window.__w.lsWrite") == 0, hh)
        await ctxH.close()

        # =========================================================== 9. entries CSV
        await T("""() => { const t = window.__tapnaplo, S = t.S; S.log.length = 0; for (const k of Object.keys(S.foods)) delete S.foods[k];
          const mk = (id, name, extra) => Object.assign({ id, src: 'user', name, brand: '', barcode: '', basis: { qty: 100, unit: 'g' }, n: { kcal: 40 }, nova: null, portions: [], note: '' }, extra);
          S.foods['u:c1'] = mk('u:c1', 'Csv beef', { vt: 'mea.red.beef', vts: 'manual', vf: ['offal'] }); S.foods['u:c2'] = mk('u:c2', 'Csv plain', {}); S.foods['u:c3'] = mk('u:c3', 'Csv unknown', { vt: 'veg.leaf.martian', vts: 'ai' });
          S.foods['u:c4'] = mk('u:c4', 'Csv sub', { vt: 'veg.leaf' });
          [['u:c1', '08:10'], ['u:c2', '08:20'], ['u:c3', '08:30'], ['u:c4', '08:40'], ['c:24999', '08:50']].forEach(([f, tm], i) => S.log.push({ id: 'e' + i, f, a: 100, d: S.day, m: 'm1', t: 1000 + i, tm }));
          S.tab = 'data'; t.save(); t.render(); }""")
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
        er = await csv_of('export-entries', 'tmp_var_entries.csv')
        heads = list(er[0].keys())
        i = heads.index('nova')
        check('Entries CSV: the columns variety_unit, variety_source and variety_flags come right after nova', heads[i + 1:i + 4] == ['variety_unit', 'variety_source', 'variety_flags'], heads[i:i + 5])
        rows = {r['food']: (r['variety_unit'], r['variety_source'], r['variety_flags']) for r in er}
        check('...a food with a group shows id, source and flag; a subgroup is its id; an id this list does not know is kept (no flags); a food without a group and a built-in (CIQUAL) food have empty cells, never a guess',
              rows['Csv beef'] == ('mea.red.beef', 'manual', 'offal') and rows['Csv sub'] == ('veg.leaf', '', '') and rows['Csv unknown'] == ('veg.leaf.martian', 'ai', '') and rows['Csv plain'] == ('', '', '') and all(v == ('', '', '') for k, v in rows.items() if k not in ('Csv beef', 'Csv sub', 'Csv unknown')), rows)
        dr = await csv_of('export-days', 'tmp_var_days.csv')
        check('Daily totals CSV is unchanged (no variety column)', not any('variety' in h for h in dr[0].keys()), [h for h in dr[0].keys() if 'variety' in h])

        # =========================================================== 10. the app without a variety list
        ctxN = await new_ctx(nolist=True); N = await new_page(ctxN, 'N')
        await put_foods([own('u:n1', 'No list food', vt='veg.leaf.spinach', vts='manual'), own('u:n2', 'No list offal', vt='veg.leaf.spinach', vf=['offal'])], N)
        await reload(N)
        nn = {i: await vfields(i, N) for i in ('u:n1', 'u:n2')}
        check('without the list (404) the app starts and keeps every well-formed group in the record (nothing is lost); they count as not classified', nn['u:n1'] == {'vt': 'veg.leaf.spinach', 'vts': 'manual'} and nn['u:n2']['vt'] == 'veg.leaf.spinach' and await N.evaluate("window.__tapnaplo.VARIETY === null && window.__tapnaplo.varietyOf(window.__tapnaplo.S.foods['u:n1']).state") == 'unknown', nn)
        nai = await N.evaluate("""() => { const t = window.__tapnaplo; const r = t.parseAiImport(JSON.stringify({ app: 'tapnaplo', version: 1, foods: { 'u:x': { id: 'u:x', src: 'user', name: 'Imp', basis: { qty: 100, unit: 'g' }, n: { kcal: 50 }, vt: 'veg.leaf.spinach' } } }));
          const bad = t.parseAiImport(JSON.stringify({ app: 'tapnaplo', version: 1, foods: { 'u:x': { id: 'u:x', src: 'user', name: 'Imp', basis: { qty: 100, unit: 'g' }, n: { kcal: 50 }, vt: 'Bad!' } } }));
          return { vt: r.foods[0].food.vt, w: r.foods[0].warnings, errors: r.errors, badVt: 'vt' in bad.foods[0].food }; }""")
        check('without the list an import keeps a well-formed vt but says it could not be checked; a malformed one is still left out', nai['vt'] == 'veg.leaf.spinach' and any('could not be loaded' in w for w in nai['w']) and nai['errors'] == [] and nai['badVt'] is False, nai)
        await N.click('[data-tab=data]'); await N.wait_for_timeout(300)
        check('...the Data tab says the list could not be loaded, and does not count unknown groups then', 'could not be loaded' in await N.inner_text('body') and 'does not know' not in await N.inner_text('body'))
        await ctxN.close()

        # =========================================================== 11. version, cache, errors
        await page.click('[data-tab=data]'); await page.wait_for_timeout(300)
        txt = await page.inner_text('body')
        ver = re.search(r'(\d+) · \d+ \w+ 20\d\d', txt)
        sw = (ROOT / 'sw.js').read_text(encoding='utf-8')
        cv = re.search(r"CACHE = 'nutrilog-v(\d+)'", sw)
        check('the Data tab shows version 38 or newer and sw.js has the same cache number', bool(ver) and int(ver.group(1)) >= 38 and bool(cv) and cv.group(1) == ver.group(1), [ver and ver.group(0), cv and cv.group(0)])
        check('variety_units.json is still in the app files of sw.js (network first) and not in the data caches', "'variety_units.json'" in sw.split('const SHELL')[1].split(']')[0] and 'variety_units' not in sw.split('const DATA')[1].split('}')[0])
        check('no page error and no console error in any of the pages', errs == [], errs[:5])
        await browser.close()
        print('\n%d problem(s)' % len(problems))
        for x in problems: print(' -', x)
        sys.exit(1 if problems else 0)

asyncio.run(main())
