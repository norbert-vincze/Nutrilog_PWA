"""Caffeine (version 35). Run with the web server on port 8765 (see CLAUDE.md).

Norbert asked (2026-11-11) for the caffeine intake on the Nutrients tab, in the part "other ingredients" (the fold "Other components"). Caffeine was not one of the 64 nutrients, so it is the
65th and last one (mg). Where the numbers come from: USDA SR Legacy (5,215 foods have a value, 289 of them above 0), Open Food Facts (caffeine_100g, grams per 100 g), your own foods
(Create food > More values, Paste from AI key "caffeine"). CIQUAL does not report caffeine and dmBio is estimated from CIQUAL, so those foods have "no data", never 0.
Covers: the three data files (same 65 keys, every vector 65 long, CIQUAL and dmBio all empty, USDA values and zeros), the row in "Other components" (place, values, pill, "Added up from",
"No data for", estimate, range, real zero, no data), real USDA / CIQUAL / dmBio foods, the Amount and Edit entry sheet, the food editor, Open Food Facts, Paste from AI, entries and daily CSV,
the Report (Nutrients row, Measure sheet, Foods list), the shared copy, backup, the number of tracked nutrients (still 42), 390 and 320 px, the version number and the cache names."""
import asyncio, csv, io, json, os, pathlib, re, sys
from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
URL = 'http://127.0.0.1:8765/index.html'
SHOTS = os.environ.get('SHOTS', '')

INIT = """
window.__txt = (el, skip) => { let s = ''; const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  while (w.nextNode()) { const n = w.currentNode; if (n.parentElement.closest(skip)) continue; s += n.textContent; }
  return s.replace(/\\s+/g, ' ').trim(); };
"""
ROW = """() => { const g = [...document.querySelectorAll('details.group, section.group')].find((x) => { const h = x.querySelector(':scope > h3, :scope > summary'); return h && h.textContent.trim() === 'Other components'; });
  if (!g) return null;
  const closed = g.tagName === 'DETAILS' && !g.open; if (g.tagName === 'DETAILS') g.open = true;
  const rows = [...g.querySelectorAll('details.nrow')];
  const labels = rows.map((r) => r.querySelector('summary > span').textContent.trim());
  const r = rows.find((x) => x.querySelector('summary > span').textContent.trim() === 'Caffeine');
  if (!r) return { closed, labels, row: false };
  r.open = true;
  const v = r.querySelector('summary .nval'), p = r.querySelector('summary .pill');
  return { closed, labels, row: true, vis: window.__txt(v, '.sr-only').replace(/\\s/g, ''), spoken: window.__txt(v, '[aria-hidden="true"]').replace(/\\s/g, ''), none: v.classList.contains('none'),
    pill: p.textContent, cls: p.className.replace('pill', '').trim(), det: [...r.querySelectorAll(':scope > .ndetail')].map((d) => d.textContent),
    parts: [...r.querySelectorAll('.ncontrib li')].map((li) => [window.__txt(li.querySelector('.nc-name'), '.sr-only'), window.__txt(li.querySelector('.nc-val'), '.sr-only').replace(/\\s/g, '')]),
    hasLine: r.querySelectorAll('.rline').length }; }"""
AROW = """() => [...document.querySelectorAll('.sheet #prev .an-row')].map((r) => ({ label: r.querySelector('dt').textContent.trim(), val: window.__txt(r.querySelector('dd'), '.sr-only').replace(/\\s/g, '') }))"""


def own(fid, name, n, **kw):
    f = {'id': fid, 'src': 'user', 'name': name, 'brand': '', 'barcode': '', 'basis': {'qty': 100, 'unit': 'g'}, 'n': n, 'nova': None, 'portions': [], 'note': '', 'created': 1000, 'updated': 1000}
    f.update(kw)
    return f


COLD = own('u:cold', 'Cold brew', {'kcal': 2, 'caffeine': 40})                  # 40 mg per 100 g
ENERGY = own('u:en', 'Energy test', {'kcal': 45, 'caffeine': 32})                # 32 mg per 100 g
PLAIN = own('u:plain', 'Plain bread', {'kcal': 250})                              # no caffeine data
ZERO = own('u:zero', 'Decaf zero', {'kcal': 5, 'caffeine': 0})                    # a real zero
ESTF = own('u:est', 'Estfood', {'kcal': 5, 'caffeine': 50}, est=['caffeine'], q='m')
LIM = own('u:lim', 'Limitfood', {'kcal': 5, 'caffeine': '<5'})
EVIL = own('u:evil', '<img src=x onerror="window.__pwn=1"><b>X</b> & "Q"', {'kcal': 10, 'caffeine': 10})
FOODS = [COLD, ENERGY, PLAIN, ZERO, ESTF, LIM, EVIL]

SR_COFFEE, SR_TEA, SR_REDBULL, SR_APPLE, SR_COLA = '171890', '173227', '173210', '171688', '174852'


async def main():
    problems = []

    def check(name, ok, info=''):
        print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(info)[:500].replace('\n', ' | ')) if info != '' else ''))
        if not ok: problems.append(name)

    # ---------------- 1. the three data files ----------------
    cq = json.load(open(ROOT / 'ciqual.json', encoding='utf-8'))
    us = json.load(open(ROOT / 'usda.json', encoding='utf-8'))
    dm = json.load(open(ROOT / 'dmbio.json', encoding='utf-8'))
    ck = [n['key'] for n in cq['nutrients']]
    check('ciqual.json has 65 nutrients and caffeine (Caffeine, mg) is the last one', len(ck) == 65 and cq['nutrients'][-1] == {'key': 'caffeine', 'label': 'Caffeine', 'unit': 'mg'} and ck.count('caffeine') == 1, cq['nutrients'][-1])
    check('usda.json and dmbio.json have the same 65 keys in the same order', us['keys'] == ck and dm['keys'] == ck)
    check('every food of the three files has 65 values (v[i] matches keys[i])', all(len(f['v']) == 65 for f in cq['foods'] + us['foods'] + dm['foods']), [len(cq['foods']), len(us['foods']), len(dm['foods'])])
    check('CIQUAL does not report caffeine: no CIQUAL food has a value (null = no data, never 0)', all(f['v'][64] is None for f in cq['foods']))
    check('dmBio has no caffeine value either (its estimates come from CIQUAL): all null', all(f['v'][64] is None for f in dm['foods']))
    sr = [f for f in us['foods'] if f['g'].startswith('SR Legacy')]
    fd = [f for f in us['foods'] if f['g'].startswith('Foundation')]
    check('USDA SR Legacy: 5,215 of 7,793 foods have a caffeine value, 289 of them above 0; Foundation Foods have none', sum(f['v'][64] is not None for f in sr) == 5215 and sum(bool(f['v'][64]) for f in sr) == 289 and len(sr) == 7793 and all(f['v'][64] is None for f in fd) and len(fd) == 436,
          [sum(f['v'][64] is not None for f in sr), sum(bool(f['v'][64]) for f in sr), len(fd)])
    by = {f['c']: f for f in us['foods']}
    check('known USDA values (mg per 100 g): brewed coffee 40, black tea 20, regular cola 9, Red Bull 29, apple 0 (a real zero), decaf coffee 1',
          [by[SR_COFFEE]['v'][64], by[SR_TEA]['v'][64], by[SR_COLA]['v'][64], by[SR_REDBULL]['v'][64], by[SR_APPLE]['v'][64], by['171889']['v'][64]] == [40, 20, 9, 29, 0, 1])
    check('no value is negative or above 10,000 mg per 100 g (the highest is instant tea)', all(0 <= f['v'][64] <= 10000 for f in us['foods'] if f['v'][64] is not None), max(f['v'][64] for f in us['foods'] if f['v'][64] is not None))
    check('the first 64 numbers of a known food did not move: brewed coffee has 1 kcal and tea has 1 kcal', by[SR_COFFEE]['v'][0] == 1 and by[SR_TEA]['v'][0] == 1)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        errs = []

        async def new_ctx(w=390, h=844):
            c = await browser.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2, is_mobile=True, has_touch=True, locale='en-GB', service_workers='block', accept_downloads=True)
            await c.add_init_script(INIT)
            await c.route('**/*openfoodfacts.org/**', lambda r: r.fulfill(status=200, headers={'access-control-allow-origin': '*', 'content-type': 'application/json'}, body='{"products":[],"status":0}'))
            return c

        def watch(pg, tag='P'):
            pg.on('pageerror', lambda e: errs.append(f'{tag} PE {e}'))
            pg.on('console', lambda m: errs.append(f'{tag} C {m.text}') if m.type == 'error' and 'Failed to load resource' not in m.text else None)

        ctx = await new_ctx()
        page = await ctx.new_page(); watch(page)
        await page.goto(URL); await page.wait_for_selector('.hero')
        T = page.evaluate
        KEYS = await T('window.__tapnaplo.KEYS')
        check('the app loaded 65 nutrients, caffeine last, 5,215 + ... USDA foods and the dmBio products', len(KEYS) == 65 and KEYS[-1] == 'caffeine' and await T('window.__tapnaplo.USDA.length') == 8229 and await T('window.__tapnaplo.DMBIO.length') == 527)

        async def seed(entries, tab='nutr', pg=page, foods=FOODS):
            await pg.evaluate("""([foods, entries, tab]) => { const t = window.__tapnaplo, S = t.S; S.log.length = 0; S.meta.ref = null;
              for (const f of foods) S.foods[f.id] = f;
              entries.forEach(([id, f, a], i) => S.log.push({ id, f, a, d: S.day, m: 'm1', t: 1000 + i, tm: '08:' + String(10 + i) }));
              S.tab = tab; t.save(); t.render(); }""", [foods, entries, tab])
            await pg.wait_for_timeout(80)

        row = lambda pg=page: pg.evaluate(ROW)

        # ---------------- 2. place of the row ----------------
        await seed([('e1', 'u:cold', 250)])
        r = await row()
        check('"Other components" is a closed fold, as before, and has the row "Caffeine" exactly once', r and r['closed'] and r['row'] and r['labels'].count('Caffeine') == 1, r and r['labels'])
        check('...Caffeine is the last row of the fold, after Organic acids (13 rows)', r['labels'][-2:] == ['Organic acids', 'Caffeine'] and len(r['labels']) == 13, r['labels'])
        check('...the rows of the other groups did not change: 65 nutrient rows plus the omega ratio row', await T("document.querySelectorAll('details.nrow').length") == 66, await T("document.querySelectorAll('details.nrow').length"))

        # ---------------- 3. values with hand-calculated numbers ----------------
        check('Cold brew 250 g (40 mg per 100 g): 100 mg, pill 1/1, "Every item has data."', r['vis'] == '100mg' and r['pill'] == '1/1' and r['cls'] == 'full' and r['det'] == ['Every item has data.'], r)
        check('...the row says where the number comes from: "Cold brew · 250 g" = 100 mg', len(r['parts']) == 1 and r['parts'][0][0].startswith('Cold brew') and '250' in r['parts'][0][0] and r['parts'][0][1] == '100mg', r['parts'])
        check('...a plain nutrient row: no reference bar (EFSA gives no caffeine value, nothing is invented)', r['hasLine'] == 0)

        await seed([('e1', 'u:cold', 250), ('e2', 'u:en', 250)])
        r = await row()
        check('Cold brew 250 g + Energy test 250 g (32 mg per 100 g): 100 + 80 = 180 mg, pill 2/2, biggest first', r['vis'] == '180mg' and r['pill'] == '2/2' and [x[1] for x in r['parts']] == ['100mg', '80mg'] and r['parts'][0][0].startswith('Cold brew'), r)

        await seed([('e1', 'u:cold', 200), ('e2', 'u:plain', 100)])
        r = await row()
        check('Cold brew 200 g + Plain bread 100 g (no data): ≥ 80 mg (a lower value), pill 1/2, the bread is named, not counted as 0', r['vis'] == '≥80mg' and r['pill'] == '1/2' and r['cls'] == 'part' and r['det'] == ['No data for: Plain bread'], r)
        check('...only the food with data is in "Added up from"', len(r['parts']) == 1 and r['parts'][0][0].startswith('Cold brew') and r['parts'][0][1] == '80mg', r['parts'])

        await seed([('e1', 'u:plain', 100)])
        r = await row()
        check('only Plain bread: "no data", grey, pill 0/1, no number, no "Added up from"', r['vis'] == 'nodata' and r['none'] and r['pill'] == '0/1' and r['cls'] == 'none' and not re.search(r'\d', r['vis']) and r['parts'] == [], r)

        await seed([('e1', 'u:zero', 100)])
        r = await row()
        check('a real zero is shown as 0 mg with pill 1/1 (not as "no data")', r['vis'] == '0mg' and r['pill'] == '1/1' and not r['none'], r)

        await seed([('e1', 'u:est', 100)])
        r = await row()
        check('an estimated value has the ~ and the estimate line (own food, confidence medium)', r['vis'] == '~50mg' and any(d.startswith('Estimate, not a label value: Estfood') and 'medium' in d for d in r['det']), r)

        await seed([('e1', 'u:lim', 100)])
        r = await row()
        check('a value known only as "<5" is a range from 0 to 5 mg, pill 1/1', r['vis'] == '0–5mg' and r['pill'] == '1/1', r)
        check('...and "Added up from" shows "<5" with the spoken word "below"', r['parts'] and r['parts'][0][1] == '<5mg', r['parts'])

        await seed([('e1', 'u:evil', 100)])
        r = await row()
        check('a hostile food name is shown as text (no HTML, nothing runs)', r['vis'] == '10mg' and '<img' in r['parts'][0][0] and await T('window.__pwn') is None, r['parts'])

        # ---------------- 4. real foods of the bundled tables ----------------
        await seed([('e1', 'usda:' + SR_COFFEE, 250)])
        r = await row()
        check('USDA "Beverages, coffee, brewed": 250 g = 100 mg, pill 1/1', r['vis'] == '100mg' and r['pill'] == '1/1' and 'coffee' in r['parts'][0][0].lower(), r)
        await seed([('e1', 'usda:' + SR_COFFEE, 250), ('e2', 'usda:' + SR_TEA, 250), ('e3', 'usda:' + SR_APPLE, 150)])
        r = await row()
        check('coffee 250 g + black tea 250 g + apple 150 g: 100 + 50 + 0 = 150 mg, pill 3/3 (the apple\'s 0 is a measured value)', r['vis'] == '150mg' and r['pill'] == '3/3', r)
        await seed([('e1', 'c:24999', 100)])
        r = await row()
        check('a CIQUAL food: "no data" (CIQUAL has no caffeine column), pill 0/1', r['vis'] == 'nodata' and r['pill'] == '0/1', r)
        await seed([('e1', await T('window.__tapnaplo.DMBIO[0].id'), 100), ('e2', 'usda:' + SR_COFFEE, 100)])
        r = await row()
        check('a dmBio product has no caffeine data: coffee 100 g + a dmBio product = ≥ 40 mg, pill 1/2', r['vis'] == '≥40mg' and r['pill'] == '1/2', r)

        # ---------------- 5. the same number everywhere ----------------
        await seed([('e1', 'usda:' + SR_COFFEE, 250), ('e2', 'u:plain', 100)], tab='log')
        await page.click(f'.entry[data-id="e1"]'); await page.wait_for_selector('#amt')
        rs = await T(AROW)
        cf = [x for x in rs if x['label'] == 'Caffeine']
        check('Edit entry (coffee, 250 g): the list "All nutrients with data for this amount" has Caffeine = 100 mg', len(cf) == 1 and cf[0]['val'] == '100mg', cf)
        check('...it is the last row, in the group "Other components"', rs[-1]['label'] == 'Caffeine' and await T("[...document.querySelectorAll('#prev .an-h')].pop().textContent.trim()") == 'Other components')
        await page.fill('#amt', '100'); await page.wait_for_timeout(120)
        cf = [x for x in await T(AROW) if x['label'] == 'Caffeine']
        check('...typing 100 g changes it to 40 mg', cf and cf[0]['val'] == '40mg', cf)
        check('the count of tracked nutrients did not change (caffeine is not one of the 42)', bool(re.search(r'of the 42 tracked', await page.inner_text('#prev'))), (await page.inner_text('#prev'))[:200])
        await page.keyboard.press('Escape'); await page.wait_for_timeout(150)
        await page.click(f'.entry[data-id="e2"]'); await page.wait_for_selector('#amt')
        rs = await T(AROW)
        nd = await T("""() => { const t = window.__tapnaplo, v = t.vecOf(t.getFood('u:plain')); let c = 0; for (let i = 0; i < t.KEYS.length; i++) if (!Number.isNaN(v.lo[i])) c++; return c; }""")
        none_txt = await T("document.querySelector('#prev .an-none').textContent")
        check('Edit entry for a food without caffeine data: no Caffeine row; it is one of the counted "No data" nutrients', not any(x['label'] == 'Caffeine' for x in rs) and none_txt.startswith(f'No data for {65 - nd} more nutrients.'), [none_txt, nd])
        await page.keyboard.press('Escape'); await page.wait_for_timeout(150)

        # ---------------- 6. the food editor ----------------
        await page.click('[data-tab=foods]'); await page.click('[data-act=new-food]'); await page.wait_for_selector('#fname')
        await page.fill('#fname', 'Guarana shot'); await page.click('details.more > summary')
        await page.click('details.fold > summary:text-is("Other components")')   # the fold "Other components" is closed while no value in it is filled
        fld = await T("""() => { const i = document.querySelector('#n_caffeine'); if (!i) return null; const fold = i.closest('details.fold');
          return { fold: fold.querySelector('summary').textContent.trim(), unit: i.closest('.nin').querySelector('.u').textContent, label: i.closest('.nin').querySelector('label').textContent, mode: i.inputMode }; }""")
        check('Create food > More values > "Other components" has the field Caffeine in mg (decimal keypad)', fld == {'fold': 'Other components', 'unit': 'mg', 'label': 'Caffeine', 'mode': 'decimal'}, fld)
        await page.fill('#n_caffeine', '32,5')
        await page.click('#fok'); await page.wait_for_timeout(250)
        saved = await T("Object.values(window.__tapnaplo.S.foods).find((f) => f.name === 'Guarana shot')")
        check('a food saved with Caffeine 32,5 keeps n.caffeine = 32.5', saved and saved['n'].get('caffeine') == 32.5, saved and saved['n'])

        # ---------------- 7. Open Food Facts and Paste from AI ----------------
        off = await T("""() => { const t = window.__tapnaplo; const mk = (nm) => t.offToFood({ code: '5449000000996', product_name: 'Energy drink', nutriments: Object.assign({ 'energy-kcal_100g': 45 }, nm) }).n;
          return [mk({ 'caffeine_100g': 0.032 }), mk({}), mk({ 'caffeine_100g': 0 }), mk({ 'caffeine_100g': -1 }), mk({ 'caffeine_100g': '' }), mk({ 'caffeine_100g': 0.0325 })]; }""")
        check('Open Food Facts: caffeine_100g 0.032 g = 32 mg; missing stays missing (no caffeine key, never 0); a real 0 stays 0; a negative or empty value is ignored; 0.0325 g = 32.5 mg',
              off[0].get('caffeine') == 32 and 'caffeine' not in off[1] and off[2].get('caffeine') == 0 and 'caffeine' not in off[3] and 'caffeine' not in off[4] and off[5].get('caffeine') == 32.5, off)
        ai = await T("""() => { const t = window.__tapnaplo; return t.parseAiImport(JSON.stringify({ app: 'tapnaplo', version: 1, foods: { 'u:x': { id: 'u:x', src: 'user', name: 'Energy shot', basis: { qty: 100, unit: 'g' }, n: { kcal: 45, caffeine: 32 } } } })); }""")
        check('Paste from AI accepts a "caffeine" value in an answer (no error, no "unknown key" warning)', ai['errors'] == [] and len(ai['foods']) == 1 and ai['foods'][0]['food']['n'].get('caffeine') == 32 and not any('nknown' in w for w in ai['foods'][0]['warnings']), ai)

        # ---------------- 8. CSV ----------------
        await seed([('e1', 'u:cold', 250), ('e2', 'u:plain', 100), ('e3', 'u:cold', 100)], tab='data')
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
        er = await csv_of('export-entries', 'tmp_caf_entries.csv')
        col = [h for h in er[0].keys() if h.startswith('caffeine')]
        check('Entries CSV has one caffeine column (named with its unit mg)', len(col) == 1 and 'mg' in col[0], col)
        vals = {r['food']: r[col[0]] for r in er if r['amount'] in ('250', '100')}
        got = [r[col[0]] for r in sorted(er, key=lambda r: r['time'])]
        check('...Cold brew 250 g = 100, Plain bread (no data) = empty, never 0, Cold brew 100 g = 40', got == ['100', '', '40'], got)
        dr = await csv_of('export-days', 'tmp_caf_days.csv')
        dcol = [h for h in dr[0].keys() if h.startswith('caffeine') and not h.endswith('__n')]
        check('Daily totals CSV: caffeine = 140 (100 + 40), the plain bread is not counted as 0, and caffeine__n = 2 of 3 entries', len(dr) == 1 and dr[0][dcol[0]] == '140' and dr[0]['caffeine__n'] == '2' and dr[0]['entries'] == '3', [dr[0][dcol[0]], dr[0].get('caffeine__n')])
        await seed([('e1', 'u:plain', 100)], tab='data')
        dr = await csv_of('export-days', 'tmp_caf_days2.csv')
        check('...a day with no caffeine data has an empty cell and caffeine__n = 0', dr[0][dcol[0]] == '' and dr[0]['caffeine__n'] == '0', [dr[0][dcol[0]], dr[0].get('caffeine__n')])

        # ---------------- 9. Report: row, Measure sheet, Foods list ----------------
        await seed([('e1', 'u:cold', 250), ('e2', 'u:en', 250), ('e3', 'u:plain', 100)], tab='report')
        await page.wait_for_selector('.rp-seg')
        rows = await T("""() => { const open = [...document.querySelectorAll('details.rp-sec')].find((d) => d.dataset.sec === 'nutrients'); if (open) open.open = true;
          const g = [...document.querySelectorAll('#rp-nutr details.group, #rp-nutr section.group, details.group, section.group')].find((x) => { const h = x.querySelector(':scope > h3, :scope > summary'); return h && h.textContent.trim() === 'Other components'; });
          if (!g) return null; if (g.tagName === 'DETAILS') g.open = true;
          const r = [...g.querySelectorAll('details.nrow')].find((x) => x.querySelector('summary > span').textContent.trim() === 'Caffeine');
          return r ? window.__txt(r.querySelector('summary'), '.sr-only').replace(/\\s/g, '') : null; }""")
        check('Report > Nutrients has the Caffeine row in "Other components": one logged day = the numbers of the Nutrients tab (≥ 180 mg; the badge is the share of items with data, 2 of 3 = 66%, rounded down as everywhere in the Report)', rows == 'Caffeine≥180mg66%', rows)
        await T("document.querySelectorAll('details.rp-sec').forEach((d) => { d.open = true; })")
        await page.wait_for_selector('[data-act=rp-measure]')
        await page.click('[data-act=rp-measure]'); await page.wait_for_selector('.rp-m')
        msr = await T("""() => { const hs = [...document.querySelectorAll('.sheet h3.rp-mh')]; const out = {}; hs.forEach((h) => { const list = []; let n = h.nextElementSibling; while (n && n.matches('.rp-m')) { list.push(n.dataset.m); n = n.nextElementSibling; } out[h.textContent.trim()] = list; }); return out; }""")
        check('the Measure sheet (Trend and Foods) lists Caffeine at the end of "Other components"', msr.get('Other components', [])[-1:] == ['caffeine'] and msr['Other components'].count('caffeine') == 1, msr.get('Other components'))
        await page.click('.rp-m[data-m=caffeine]'); await page.wait_for_timeout(250)
        foods = await T("document.querySelector('#rp-foods') ? window.__txt(document.querySelector('#rp-foods'), '.sr-only') : ''")
        check('the Foods list for the measure Caffeine: Cold brew first (100 of 180 mg), then Energy test; the bread is named under "No data for", not listed with 0',
              'Cold brew' in foods and 'Energy test' in foods and foods.index('Cold brew') < foods.index('Energy test') and 'No data for' in foods and 'Plain bread' in foods.split('No data for')[1], foods[:400])
        shares = await T("[...document.querySelectorAll('#rp-foods .rp-fr, #rp-foods li, #rp-foods .row')].map((e) => e.textContent.replace(/\\s+/g, ' ').trim()).filter((t) => /Cold brew|Energy test/.test(t))")
        check('...with shares 56% (100 of 180) and 44% (80 of 180), together 100%', any('56%' in s_ for s_ in shares) and any('44%' in s_ for s_ in shares), shares)

        # ---------------- 10. shared copy and backup ----------------
        await seed([('e1', 'u:cold', 250), ('e2', 'u:plain', 100)], tab='nutr')
        sender = await row()
        link = await T("() => { const t = window.__tapnaplo; return t.shareLink(t.S.day, t.S.day).then((r) => r.url); }")
        vctx = await new_ctx()
        vp = await vctx.new_page(); watch(vp, 'V')
        await vp.goto(link); await vp.wait_for_selector('.hero')
        await vp.click('[data-tab=nutr]'); await vp.wait_for_selector('.nrow')
        viewer = await vp.evaluate(ROW)
        check('the shared copy shows the same Caffeine row as the sender (value, pill, lines)', viewer and viewer['row'] and (viewer['vis'], viewer['pill'], viewer['det'], viewer['parts']) == (sender['vis'], sender['pill'], sender['det'], sender['parts']) and sender['vis'] == '≥100mg', [viewer and viewer.get('vis'), sender['vis']])
        await vctx.close()
        async with page.expect_download() as dd:
            await page.click('[data-tab=data]'); await page.click('[data-act=export-json]')
        dl = await dd.value
        bk = json.loads(pathlib.Path(await dl.path()).read_text(encoding='utf-8'))
        check('the backup keeps the caffeine value of your own foods (n.caffeine = 40) and has no new top-level key', bk['foods']['u:cold']['n']['caffeine'] == 40 and sorted(bk.keys()) == sorted(['app', 'version', 'exported', 'log', 'foods', 'meta', 'health', 'wlog']), sorted(bk.keys()))
        check('a food that never had caffeine has no caffeine key in the backup (missing stays missing)', 'caffeine' not in bk['foods']['u:plain']['n'])

        # ---------------- 11. narrow screen, light and dark ----------------
        ctxN = await new_ctx(320, 640)
        np_ = await ctxN.new_page(); watch(np_, 'N')
        await np_.goto(URL); await np_.wait_for_selector('.hero')
        await seed([('e1', 'u:cold', 250), ('e2', 'u:plain', 100), ('e3', 'u:evil', 100)], pg=np_)
        rn = await np_.evaluate(ROW)
        wide = await np_.evaluate("(() => { const g = [...document.querySelectorAll('details.group')].find((x) => x.querySelector(':scope > summary').textContent.trim() === 'Other components'); const r = [...g.querySelectorAll('details.nrow')].pop(); return [...r.querySelectorAll('.ndetail, summary > *, .ncontrib li')].filter((e) => e.scrollWidth > e.clientWidth + 1).map((e) => e.className + ':' + e.textContent.slice(0, 30)); })()")
        check('320 px: the Caffeine row is open, nothing is cut off and the page does not scroll sideways', rn['row'] and wide == [] and await np_.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), wide)
        for theme in ('light', 'dark'):
            await np_.evaluate(f"document.documentElement.setAttribute('data-theme', '{theme}')")
            bad = await np_.evaluate("""() => { const g = [...document.querySelectorAll('details.group')].find((x) => x.querySelector(':scope > summary').textContent.trim() === 'Other components'); const r = [...g.querySelectorAll('details.nrow')].pop();
              const lum = (c) => { const m = c.match(/[\\d.]+/g).map(Number); const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(m[0]) + 0.7152 * f(m[1]) + 0.0722 * f(m[2]); };
              const bg = (el) => { for (let e = el; e; e = e.parentElement) { const c = getComputedStyle(e).backgroundColor; if (c && !/rgba\\(.*, 0\\)|transparent/.test(c)) return c; } return 'rgb(255,255,255)'; };
              return [...r.querySelectorAll('summary > span, .nval, .pill, .ndetail, .nc-name, .nc-val')].filter((e) => e.textContent.trim()).map((e) => { const a = lum(getComputedStyle(e).color), b = lum(bg(e)); const cr = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05); return [e.className, cr]; }).filter(([, cr]) => cr < 4.5); }""")
            check(f'{theme}: every text of the Caffeine row has a contrast of at least 4.5:1', bad == [], bad)
            if SHOTS:
                await np_.evaluate("(() => { const g = [...document.querySelectorAll('details.group')].find((x) => x.querySelector(':scope > summary').textContent.trim() === 'Other components'); g.scrollIntoView({block: 'start'}); })()")
                await np_.screenshot(path=os.path.join(SHOTS, f'caffeine_{theme}.png'))
        await np_.evaluate("document.documentElement.setAttribute('data-theme', 'light')")
        await ctxN.close()

        # ---------------- 12. version and caches ----------------
        await page.click('[data-tab=data]'); await page.wait_for_timeout(300)
        txt = await page.inner_text('body')
        ver = re.search(r'(\d+) · \d+ \w+ 20\d\d', txt)
        check('the Data tab shows version 35 or newer and says "65 nutrients"', bool(ver) and int(ver.group(1)) >= 35 and '65 nutrients' in txt, [ver and ver.group(0)])
        sw = (ROOT / 'sw.js').read_text(encoding='utf-8')
        check('the service worker cache has the number of the version', bool(ver) and f"const CACHE = 'nutrilog-v{ver.group(1)}'" in sw)
        check('the food tables are in new caches (nutrilog-data-2 and nutrilog-dmbio-2), so a phone that cached the old 64-nutrient files fetches the new ones',
              "'ciqual.json': 'nutrilog-data-2'" in sw and "'usda.json': 'nutrilog-data-2'" in sw and "'dmbio.json': 'nutrilog-dmbio-2'" in sw)
        check('no page errors', errs == [], errs[:5])
        await browser.close()
    print('\nALL PASS' if not problems else f'\n{len(problems)} FAILED: {problems}')
    sys.exit(1 if problems else 0)


asyncio.run(main())
