"""Drinks in ml (version 18). Run with the web server on port 8765 (see CLAUDE.md).

A food can carry `ml: true` (only ever true, only on a food measured per 100 g). The data stays in grams (1 ml = 1 g, the maths does not change);
only the unit shown changes: Amount sheet (label, chips, button, toast), diary row, My foods list, entries CSV (unit column), the Edit food form
(a third radio "100 ml", portions in ml). Import: an explicit "ml" is read, and a food without it gets ml from a portion {"label": "100 ml", "grams": 100}
(that is how prompt v3.1 and the artifact give a drink per 100 ml). Update existing keeps the unit you chose by hand.
Covers: helpers, Amount sheet (new entry and edit entry), diary and list text, same numbers as a gram food, CSV, editor (radio, portions heading and placeholders,
switching back removes the flag), Paste from AI and Import foods (JSON) (explicit true, derived, explicit false, bad value, per-piece basis), Update existing,
backup / sync records carry the flag, old foods and generic foods stay in g, 16 px fields, 44 px targets, contrast, no sideways scroll."""
import asyncio, csv, io, json, os, pathlib, sys
from playwright.async_api import async_playwright
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_ai_import import CONTRAST_JS, SMALL_FONTS, SMALL_TARGETS, food as ai_food, doc as ai_doc, J

URL = 'http://127.0.0.1:8765/index.html'
HERE = pathlib.Path(__file__).resolve().parent
SHOTS = os.environ.get('SHOTS', '')


def own(fid, name, n, **kw):
    f = {'id': fid, 'src': 'user', 'name': name, 'brand': '', 'barcode': '', 'basis': {'qty': 100, 'unit': 'g'}, 'n': n, 'nova': None, 'portions': [], 'note': '', 'created': 1000, 'updated': 1000}
    f.update(kw)
    return f


async def main():
    async with async_playwright() as p:
        problems, made = [], []

        def check(name, ok, info=''):
            print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(info)) if info != '' else ''))
            if not ok: problems.append(name)

        browser = await p.chromium.launch()
        errs = []
        ctx = await browser.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True, locale='en-GB', service_workers='block', accept_downloads=True)
        await ctx.route('**/*openfoodfacts.org/**', lambda r: r.fulfill(status=200, headers={'access-control-allow-origin': '*', 'content-type': 'application/json'}, body='{"products":[],"status":0}'))
        page = await ctx.new_page()
        page.on('pageerror', lambda e: errs.append(f'PE {e}'))
        page.on('console', lambda m: errs.append(f'C {m.text}') if m.type == 'error' and 'Failed to load resource' not in m.text else None)
        await page.goto(URL); await page.wait_for_selector('.hero')
        T = page.evaluate

        async def sheets():
            return await T("document.querySelectorAll('.sheet').length")

        async def close_all():
            for _ in range(8):
                if not await sheets(): break
                await page.click('.sheet-wrap:last-of-type [data-x]')
                await page.wait_for_timeout(150)

        async def csv_of(act, name):
            async with page.expect_download() as d:
                await page.click(f'[data-act={act}]')
            dl = await d.value
            path = HERE / name
            await dl.save_as(str(path)); made.append(path)
            return list(csv.DictReader(io.StringIO(path.read_text(encoding='utf-8-sig'))))

        foods_n = lambda: T("Object.keys(window.__tapnaplo.S.foods).length")
        today = await T("(() => { const d = new Date(); const p = (n) => String(n).padStart(2, '0'); return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`; })()")

        # ---- foods: a drink in ml (ml flag), the same drink in g, a capsule with a stray ml flag, an old food without the flag
        N = {'kcal': 40, 'protein': 1, 'carbohydrate': 6, 'fat': 1.5}
        M = own('u:ml', 'Oat drink ml', N, ml=True, portions=[{'label': '1 glass', 'grams': 250}, {'label': '100 ml', 'grams': 100}])
        G = own('u:g', 'Oat drink gram', N)
        C = own('u:cap', 'Fish oil capsule', {'kcal': 9, 'fat': 1}, basis={'qty': 1, 'unit': 'capsule'}, ml=True)
        await T("""([foods, d]) => { const t = window.__tapnaplo; for (const f of foods) t.S.foods[f.id] = f;
            t.S.log.push({ id: 'e1', d, m: 'm1', f: 'u:ml', a: 250, t: Date.now(), tm: '08:00' }, { id: 'e2', d, m: 'm1', f: 'u:g', a: 250, t: Date.now(), tm: '09:00' }, { id: 'e3', d, m: 'm2', f: 'u:cap', a: 2, t: Date.now(), tm: '10:00' });
            t.save(); t.render(); }""", [[M, G, C], today])

        # =========================================================== 1 helpers
        h = await T("""(() => { const t = window.__tapnaplo, S = t.S; return {
            ml: t.isMl(S.foods['u:ml']), g: t.isMl(S.foods['u:g']), cap: t.isMl(S.foods['u:cap']),
            uml: t.unitOf(S.foods['u:ml']), ug: t.unitOf(S.foods['u:g']), ucap: t.unitOf(S.foods['u:cap']),
            generic: t.unitOf(t.getFood(Object.keys(S.foods).length ? 'c:9436' : 'c:9436')) }; })()""")
        check('helpers: a food with ml is shown in ml', h['ml'] is True and h['uml'] == 'ml', h)
        check('helpers: a food without it stays in g', h['g'] is False and h['ug'] == 'g', h)
        check('helpers: a capsule with a stray ml flag is not ml, its unit is the capsule', h['cap'] is False and h['ucap'] == 'capsule', h)
        check('helpers: a CIQUAL food stays in g', h['generic'] == 'g', h)

        # =========================================================== 2 diary and lists
        sub = lambda name: T("(n) => { const e = [...document.querySelectorAll('.entry')].find((x) => x.innerText.includes(n)); return e ? e.innerText : null; }", name)
        s1, s2, s3 = await sub('Oat drink ml'), await sub('Oat drink gram'), await sub('Fish oil')
        check('diary row: the ml food shows "250 ml"', s1 is not None and '250 ml' in s1 and '250 g' not in s1, s1)
        check('diary row: the gram food shows "250 g"', s2 is not None and '250 g' in s2 and 'ml' not in s2.replace('Oat drink gram', ''), s2)
        check('diary row: the capsule shows its own unit', s3 is not None and '2 capsule' in s3, s3)
        k1 = await T("(() => { const t = window.__tapnaplo; return [t.totalsFor(t.S.log.filter((e) => e.f === 'u:ml')).lo[0], t.totalsFor(t.S.log.filter((e) => e.f === 'u:g')).lo[0]]; })()")
        check('the maths is the same for ml and g (250 ml of 40 kcal/100 = 100 kcal)', abs(k1[0] - 100) < 1e-9 and abs(k1[1] - 100) < 1e-9, k1)

        await page.click('[data-tab=foods]'); await page.wait_for_selector('#ffilter')
        rows = await T("[...document.querySelectorAll('#flist .item')].map((x) => x.innerText)")
        rm = next((r for r in rows if 'Oat drink ml' in r), ''); rg = next((r for r in rows if 'Oat drink gram' in r), '')
        check('My foods: the ml food says "per 100 ml", the gram food "per 100 g"', 'per 100 ml' in rm and 'per 100 g' not in rm and 'per 100 g' in rg and 'ml' not in rg.replace('Oat drink gram', ''), [rm, rg])
        await page.click('[data-tab=log]'); await page.wait_for_selector('.hero')

        # =========================================================== 3 Amount sheet: edit entry
        await page.click('.entry:has-text("Oat drink ml")'); await page.wait_for_selector('#amt')
        lab = await T("document.querySelector('#amt').closest('label').innerText")
        chips = await T("[...document.querySelectorAll('#chips button')].map((b) => b.innerText)")
        check('Amount sheet: the label above the field says ml', lab.startswith('Amount (ml)'), lab)
        check('Amount sheet: the standard buttons are in ml', all(x in chips for x in ['10 ml', '30 ml', '50 ml', '100 ml', '200 ml']) and not any(c.endswith(' g') for c in chips), chips)
        check('Amount sheet: the saved portions are there ("1 glass")', '1 glass' in chips, chips)
        check('Amount sheet: the button says what it saves ("Save 250 ml")', (await page.inner_text('#ok')).strip() == 'Save 250 ml', await page.inner_text('#ok'))
        await page.fill('#amt', '300')
        check('Amount sheet: typing updates the button ("Save 300 ml")', (await page.inner_text('#ok')).strip() == 'Save 300 ml')
        pv = await page.inner_text('#prev')
        check('Amount sheet: 300 ml of 40 kcal/100 g shows 120 kcal', '120 kcal' in pv, pv)
        await page.click('#chips button:has-text("1 glass")')
        check('Amount sheet: a portion button enters its amount (250)', await page.input_value('#amt') == '250')
        check('Amount sheet: fields are at least 16 px, the main buttons at least 44 px', await T(SMALL_FONTS, '.sheet') == [] and await T(SMALL_TARGETS, '.sheet #ok, .sheet #editfood, .sheet #del') == [], [await T(SMALL_FONTS, '.sheet'), await T(SMALL_TARGETS, '.sheet #ok, .sheet #editfood, .sheet #del')])
        await page.fill('#amt', '300'); await page.click('#ok'); await page.wait_for_timeout(300)
        t = await page.inner_text('#toast')
        check('toast after the change says ml', '300 ml' in t, t)
        check('the entry now holds 300 and the diary row says "300 ml"', await T("window.__tapnaplo.S.log.find((e) => e.id === 'e1').a") == 300 and '300 ml' in (await sub('Oat drink ml')))

        # gram food and capsule keep their old sheet
        await page.click('.entry:has-text("Oat drink gram")'); await page.wait_for_selector('#amt')
        lab = await T("document.querySelector('#amt').closest('label').innerText"); chips = await T("[...document.querySelectorAll('#chips button')].map((b) => b.innerText)")
        check('gram food: label "Amount (g)", chips in g, button "Save 250 g"', lab.startswith('Amount (g)') and '30 g' in chips and not any(c.endswith(' ml') for c in chips) and (await page.inner_text('#ok')).strip() == 'Save 250 g', [lab, chips])
        await close_all()
        await page.click('.entry:has-text("Fish oil")'); await page.wait_for_selector('#amt')
        lab = await T("document.querySelector('#amt').closest('label').innerText")
        check('capsule: label "Amount (capsule)"', lab.startswith('Amount (capsule)'), lab)
        await close_all()

        # =========================================================== 4 Amount sheet: new entry from the Log food search
        await page.click('[data-act=add][data-meal=m1]'); await page.wait_for_selector('#q')
        await page.fill('#q', 'oat drink ml'); await page.wait_for_timeout(500)
        await page.click('.item:has-text("Oat drink ml")'); await page.wait_for_selector('#amt')
        check('new entry: starts at the last used amount (300 from before) in ml', await page.input_value('#amt') == '300' and (await page.inner_text('#ok')).strip() == 'Add 300 ml', [await page.input_value('#amt'), await page.inner_text('#ok')])
        await page.fill('#amt', '200'); await page.click('#ok'); await page.wait_for_timeout(300)
        t = await page.inner_text('#toast')
        check('new entry: toast "Added: Oat drink ml, 200 ml to Meal 1"', 'Added' in t and '200 ml' in t and 'Meal' in t, t)
        await close_all()

        # =========================================================== 5 entries CSV
        await page.click('[data-tab=data]'); await page.wait_for_selector('[data-act=export-entries]')
        rows = await csv_of('export-entries', 'ml_entries.csv')
        um = {r['food']: r['unit'] for r in rows}
        check('entries CSV: unit column is ml for the ml food, g for the gram food, capsule for the capsule', um.get('Oat drink ml') == 'ml' and um.get('Oat drink gram') == 'g' and um.get('Fish oil capsule') == 'capsule', um)
        check('entries CSV: the amount stays a plain number', {r['amount'] for r in rows if r['food'] == 'Oat drink ml'} == {'300', '200'}, [r['amount'] for r in rows])

        # =========================================================== 6 Edit food: radios, portions, switching back
        await page.click('[data-tab=foods]'); await page.wait_for_selector('#ffilter')
        await page.click('#flist .item:has-text("Oat drink gram")'); await page.wait_for_selector('#fok')
        radios = await T("[...document.querySelectorAll('input[name=basis]')].map((r) => [r.value, r.checked, r.closest('label').innerText.trim()])")
        check('editor: three choices, 100 g is selected for a gram food', [r[0] for r in radios] == ['g', 'ml', 'u'] and [r[1] for r in radios] == [True, False, False], radios)
        check('editor: the labels say 100 g / 100 ml (counted as 100 g) / 1 unit', radios[0][2] == '100 g' and radios[1][2] == '100 ml (counted as 100 g)' and radios[2][2].startswith('1 unit'), radios)
        check('editor: portions heading and placeholders start in grams', await page.text_content('#porth') == 'Portions (in grams)', await page.text_content('#porth'))
        await page.click('#addport')
        check('editor: a new portion row asks for grams', await T("document.querySelector('#ports .pg').placeholder") == 'g' and await T("document.querySelector('#ports .pg').getAttribute('aria-label')") == 'Portion in grams')
        await page.check('input[name=basis][value=ml]')
        check('editor: choosing 100 ml changes the heading, placeholder and aria-label of the rows to ml', await page.text_content('#porth') == 'Portions (in ml)' and await T("document.querySelector('#ports .pg').placeholder") == 'ml' and await T("document.querySelector('#ports .pg').getAttribute('aria-label')") == 'Portion in ml')
        check('editor: the unit-name box stays hidden and the portions stay visible', await T("document.querySelector('#funit').hidden") and not await T("document.querySelector('#portwrap').hidden"))
        await page.click('#addport')
        check('editor: a row added after the switch also asks for ml', await T("document.querySelectorAll('#ports .pg')[1].placeholder") == 'ml')
        await page.fill('#ports .ing:nth-child(1) .pl', '1 glass'); await page.fill('#ports .ing:nth-child(1) .pg', '250')
        check('editor: fonts at least 16 px, the three choices fit the screen', await T(SMALL_FONTS, '.sheet') == [] and await T('document.documentElement.scrollWidth <= window.innerWidth'))
        if SHOTS: await page.screenshot(path=SHOTS + '/ml_editor.png')
        light = await T(CONTRAST_JS, '.sheet')
        await T("document.documentElement.setAttribute('data-theme','dark')")
        dark = await T(CONTRAST_JS, '.sheet')
        await T("document.documentElement.setAttribute('data-theme','light')")
        check('editor with the ml choice: contrast >= 4.5:1 (light and dark)', light == [] and dark == [], [light[:2], dark[:2]])
        await page.click('#fok'); await page.wait_for_timeout(400)
        sv = await T("(() => { const f = window.__tapnaplo.S.foods['u:g']; return { ml: f.ml, basis: f.basis, portions: f.portions }; })()")
        check('Save: the food now has ml:true, basis stays 100 g, the portion is kept', sv['ml'] is True and sv['basis'] == {'qty': 100, 'unit': 'g'} and sv['portions'] == [{'label': '1 glass', 'grams': 250}], sv)
        check('diary rows of that food now say ml (the old entry of 250)', '250 ml' in (await sub('Oat drink gram') or '') if await page.locator('.entry').count() else True)
        # back to 100 g removes the flag (the key is gone, not false)
        await page.click('#flist .item:has-text("Oat drink gram")'); await page.wait_for_selector('#fok')
        radios = await T("[...document.querySelectorAll('input[name=basis]')].map((r) => [r.value, r.checked])")
        check('editor of an ml food: the 100 ml choice is selected and the heading says ml', radios == [['g', False], ['ml', True], ['u', False]] and await page.text_content('#porth') == 'Portions (in ml)', radios)
        await page.check('input[name=basis][value=g]'); await page.click('#fok'); await page.wait_for_timeout(400)
        sv = await T("(() => { const f = window.__tapnaplo.S.foods['u:g']; return 'ml' in f; })()")
        check('switching back to 100 g removes the ml key', sv is False)
        # a capsule: choosing the piece unit never leaves an ml flag behind
        await page.click('#flist .item:has-text("Oat drink ml")'); await page.wait_for_selector('#fok')
        await page.check('input[name=basis][value=u]'); await page.fill('#funit', 'bottle'); await page.click('#fok'); await page.wait_for_timeout(400)
        sv = await T("(() => { const f = window.__tapnaplo.S.foods['u:ml']; return { has: 'ml' in f, unit: f.basis.unit, ml: window.__tapnaplo.isMl(f) }; })()")
        check('changing an ml food to a piece unit removes the flag; it is a "bottle" food', sv == {'has': False, 'unit': 'bottle', 'ml': False}, sv)
        await close_all()

        # =========================================================== 7 Paste from AI
        async def paste(obj):
            await page.click('[data-tab=foods]'); await page.wait_for_selector('#ffilter')
            await page.click('[data-act=ai-import]'); await page.wait_for_selector('#ai-text')
            await page.fill('#ai-text', obj if isinstance(obj, str) else J(obj)); await page.click('#ai-read')
            await page.wait_for_selector('#fok, #ai-msg:not(:empty)')

        ml_radio = lambda: T("document.querySelector('input[name=basis]:checked').value")
        await paste(ai_doc(ai_food(name='Almond drink', barcode='', portions=[{'label': '100 ml', 'grams': 100}], est=[], confidence=None, fortified=False)))
        check('Paste from AI: a drink with the portion "100 ml" = 100 g opens with the 100 ml choice selected (prompt v3.1 shape)', await ml_radio() == 'ml', await ml_radio())
        await page.click('#fok'); await page.wait_for_timeout(400)
        a = await T("Object.values(window.__tapnaplo.S.foods).find((f) => f.name === 'Almond drink')")
        check('saved from the review: ml:true, basis 100 g, no changes to the numbers', a['ml'] is True and a['basis'] == {'qty': 100, 'unit': 'g'} and a['n']['kcal'] == 45, a)
        await close_all()
        r = await T("""(() => { const t = window.__tapnaplo; const o = (x) => t.parseAiImport(JSON.stringify({ nutrilog_import: 1, foods: [x] }));
            const base = { name: 'X', basis: { qty: 100, unit: 'g' }, n: { kcal: 40, protein: 1, carbohydrate: 6, fat: 1.5 } };
            const w = (x) => { const r = o(x); return { errors: r.errors, ml: r.foods[0] && r.foods[0].food.ml, warnings: r.foods[0] ? r.foods[0].warnings : null }; };
            return { explicit: w({ ...base, ml: true }), strtrue: w({ ...base, ml: 'true' }), derived: w({ ...base, portions: [{ label: '100 ml', grams: 100 }] }), derived2: w({ ...base, portions: [{ label: '100ML', grams: 100 }] }),
              off: w({ ...base, ml: false, portions: [{ label: '100 ml', grams: 100 }] }), plain: w(base), other: w({ ...base, portions: [{ label: '250 ml kész', grams: 20 }] }), grams101: w({ ...base, portions: [{ label: '100 ml', grams: 101 }] }),
              bad: w({ ...base, ml: 'maybe' }), piece: w({ name: 'Y', basis: { qty: 1, unit: 'capsule' }, n: { kcal: 9, fat: 1 }, ml: true }) }; })()""")
        check('parse: explicit ml:true and "true" are read', r['explicit']['ml'] is True and r['strtrue']['ml'] is True and r['explicit']['warnings'] == [], r)
        check('parse: the 100 ml portion (also written 100ML) gives ml', r['derived']['ml'] is True and r['derived2']['ml'] is True and r['derived']['warnings'] == [], [r['derived'], r['derived2']])
        check('parse: an explicit ml:false wins over the portion', r['off']['ml'] is None, r['off'])
        check('parse: no ml and no 100 ml portion stays in g; a "250 ml kész" portion (dry powder) and 100 ml = 101 g do not make ml', r['plain']['ml'] is None and r['other']['ml'] is None and r['grams101']['ml'] is None, [r['plain'], r['other'], r['grams101']])
        check('parse: a bad value is ignored with a warning', r['bad']['ml'] is None and any('"ml" should be true or false' in x for x in r['bad']['warnings']), r['bad'])
        check('parse: ml on a per-piece food is ignored with a warning and is not an error', r['piece']['errors'] == [] and r['piece']['ml'] is None and any('only for foods measured per 100 g' in x for x in r['piece']['warnings']), r['piece'])

        # =========================================================== 8 Update existing keeps the unit chosen by hand
        await T("""() => { const t = window.__tapnaplo; t.S.foods['u:keep'] = { id: 'u:keep', src: 'user', name: 'Kept drink', brand: 'Acme', barcode: '', basis: { qty: 100, unit: 'g' }, ml: true, n: { kcal: 30 }, nova: null, portions: [], note: '', created: 1000, updated: 1000 };
            t.S.log.push({ id: 'e9', d: '""" + today + """', m: 'm1', f: 'u:keep', a: 100, t: Date.now(), tm: '11:00' }); t.save(); t.render(); }""")
        await paste(ai_doc(ai_food(name='Kept drink', brand='Acme', barcode='', portions=[], est=[], confidence=None, fortified=False, nova=None)))
        check('Paste from AI: an answer with no 100 ml portion opens as 100 g (the editor shows what the import says)', await ml_radio() == 'g', await ml_radio())
        await page.click('#fok'); await page.wait_for_selector('[data-dup=update]')
        await page.click('[data-dup=update]'); await page.wait_for_timeout(400)
        k = await T("(() => { const f = window.__tapnaplo.S.foods['u:keep']; return { ml: f.ml, kcal: f.n.kcal }; })()")
        check('Update existing: the numbers are replaced, the ml unit you chose stays', k['kcal'] == 45 and k['ml'] is True, k)
        await close_all()
        # and an update whose answer says ml also gives ml to a gram food
        await T("""() => { const t = window.__tapnaplo; t.S.foods['u:gram2'] = { id: 'u:gram2', src: 'user', name: 'Gram drink', brand: 'Acme', barcode: '', basis: { qty: 100, unit: 'g' }, n: { kcal: 30 }, nova: null, portions: [], note: '', created: 1000, updated: 1000 }; t.save(); }""")
        await paste(ai_doc(ai_food(name='Gram drink', brand='Acme', barcode='', portions=[{'label': '100 ml', 'grams': 100}], est=[], confidence=None, fortified=False)))
        await page.click('#fok'); await page.wait_for_selector('[data-dup=update]'); await page.click('[data-dup=update]'); await page.wait_for_timeout(400)
        check('Update existing: an answer with the 100 ml portion turns a gram food into an ml food', await T("window.__tapnaplo.S.foods['u:gram2'].ml") is True)
        await close_all()

        # =========================================================== 9 Import foods (JSON)
        ff = {'app': 'tapnaplo', 'version': 1, 'foods': {
            'u:f1': {'id': 'u:f1', 'src': 'user', 'name': 'File drink', 'brand': '', 'barcode': '', 'basis': {'qty': 100, 'unit': 'g'}, 'n': {'kcal': 20, 'protein': 0.5}, 'ml': True, 'portions': [{'label': '1 glass', 'grams': 200}], 'created': 5, 'updated': 5},
            'u:f2': {'id': 'u:f2', 'src': 'user', 'name': 'File drink two', 'brand': '', 'barcode': '', 'basis': {'qty': 100, 'unit': 'g'}, 'n': {'kcal': 25}, 'portions': [{'label': '100 ml', 'grams': 100}], 'created': 5, 'updated': 5},
            'u:f3': {'id': 'u:f3', 'src': 'user', 'name': 'File food', 'brand': '', 'barcode': '', 'basis': {'qty': 100, 'unit': 'g'}, 'n': {'kcal': 250}, 'portions': [], 'created': 5, 'updated': 5}}}
        path = HERE / 'ml_foods.json'; path.write_text(json.dumps(ff), encoding='utf-8'); made.append(path)
        await page.click('[data-tab=data]'); await page.wait_for_selector('#importfoods', state='attached')
        await page.set_input_files('#importfoods', str(path)); await page.wait_for_timeout(600)
        if await sheets(): await page.click('.sheet button.primary'); await page.wait_for_timeout(400)
        fl = await T("(() => { const S = window.__tapnaplo.S.foods; return ['u:f1', 'u:f2', 'u:f3'].map((i) => S[i] && S[i].ml); })()")
        check('Import foods (JSON): explicit ml and the 100 ml portion give ml, a plain food does not', fl == [True, True, None], fl)
        await close_all()

        # =========================================================== 10 backup, sync records, old data
        bk = await T("""(() => { const t = window.__tapnaplo; const j = JSON.parse(JSON.stringify({ foods: t.S.foods })); return { saved: j.foods['u:keep'].ml, canon: t.canon(t.S.foods['u:keep']).includes('"ml":true'), sync: !!(t.syncRecords().get('f:u:keep') && t.syncRecords().get('f:u:keep').v.ml === true) }; })()""")
        check('backup JSON, sync canon and sync records carry the flag', bk['saved'] is True and bk['canon'] is True and bk['sync'] is True, bk)
        # restore a backup made before version 18 (no ml anywhere) and one with the flag
        old = {'app': 'tapnaplo', 'version': 1, 'exported': 1, 'foods': {'u:old': own('u:old', 'Old drink', N, portions=[{'label': '100 ml', 'grams': 100}])}, 'log': [{'id': 'o1', 'd': today, 'm': 'm1', 'f': 'u:old', 'a': 100, 't': 1, 'tm': '07:00'}], 'meta': {}}
        opath = HERE / 'ml_old_backup.json'; opath.write_text(json.dumps(old), encoding='utf-8'); made.append(opath)
        await page.click('[data-tab=data]'); await page.wait_for_selector('#importfile', state='attached')
        await page.set_input_files('#importfile', str(opath)); await page.wait_for_selector('.sheet button.danger'); await page.click('.sheet button.danger'); await page.wait_for_timeout(500)
        of = await T("(() => { const t = window.__tapnaplo; const f = t.S.foods['u:old']; return { ml: t.isMl(f), unit: t.unitOf(f) }; })()")
        check('an old backup restores unchanged: a drink with a 100 ml portion but no flag stays in g (no silent migration)', of == {'ml': False, 'unit': 'g'}, of)
        await page.click('[data-tab=log]'); await page.wait_for_selector('.hero')
        so = await sub('Old drink')
        check('old data: the diary row still says g', so is not None and '100 g' in so, so)
        await page.click('.entry:has-text("Old drink")'); await page.wait_for_selector('#amt')
        check('old data: the Amount sheet still says g', (await T("document.querySelector('#amt').closest('label').innerText")).startswith('Amount (g)'))
        await close_all()

        # =========================================================== 11 generic foods stay in g
        await page.click('[data-act=add][data-meal=m1]'); await page.wait_for_selector('#q')
        await page.fill('#q', 'milk'); await page.wait_for_timeout(600)
        await page.click('.item >> nth=0'); await page.wait_for_selector('#amt')
        check('a CIQUAL / USDA / dmBio food keeps "Amount (g)"', (await T("document.querySelector('#amt').closest('label').innerText")).startswith('Amount (g)'))
        await close_all()

        check('no page errors', errs == [], errs[:5])
        await browser.close()
        for pth in made:
            try: pth.unlink()
            except OSError: pass
        print('\nALL PASS' if not problems else f'\n{len(problems)} FAILED: {problems}')
        sys.exit(1 if problems else 0)


asyncio.run(main())
