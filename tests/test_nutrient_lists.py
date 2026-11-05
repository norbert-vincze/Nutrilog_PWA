"""All nutrients in the Amount sheet and "Added up from" in the Nutrients rows (version 27). Run with the web server on port 8765 (see CLAUDE.md).

1. The Amount / Edit entry sheet lists every nutrient the food has data for, for the amount in the Amount field, inside the kcal card:
   grouped like the Nutrients tab, same units, "~" for an estimate, "<x" for a value below the detection limit, a real zero as 0, and a missing
   value never as 0 (it is only counted: "No data for N more nutrients ..."). The list follows the field while typing.
2. Every row of the Nutrients tab, when opened, first lists the foods that have data for it and their share of the total (merged per food,
   biggest first), then the old lines ("No data for: ...", "Every item has data.", "Estimate, not a label value: ...") and the EFSA text.
Covers: new entry and edit entry, scaling and live update, ml and per-piece foods, ranges, estimates, zero, missing, grouping and order,
one-nutrient singular, no list for a bad amount, the sticky buttons, folds below the list, the sums of the parts equal the row total,
same food twice, other days, the shared (read-only) view, hostile names, 390 and 320 px, contrast light/dark, 16 px, version number, no page errors."""
import asyncio, json, os, pathlib, re, sys
from playwright.async_api import async_playwright
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_ai_import import CONTRAST_JS, SMALL_FONTS

URL = 'http://127.0.0.1:8765/index.html'
SHOTS = os.environ.get('SHOTS', '')

INIT = """
window.__txt = (el, skip) => { let s = ''; const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  while (w.nextNode()) { const n = w.currentNode; if (n.parentElement.closest(skip)) continue; s += n.textContent; }
  return s.replace(/\\s+/g, ' ').trim(); };
"""
# rows of the list in the Amount sheet: label, what the eye sees (no hidden text), what a screen reader hears (no aria-hidden)
ROWS = """() => [...document.querySelectorAll('.sheet #prev .an-row')].map((r) => ({ label: r.querySelector('dt').textContent.trim(),
  vis: window.__txt(r.querySelector('dd'), '.sr-only'), spoken: window.__txt(r.querySelector('dd'), '[aria-hidden="true"]') }))"""
# parts of an opened Nutrients row (element argument)
PARTS = """(row) => [...row.querySelectorAll('.ncontrib li')].map((li) => ({ name: li.querySelector('.nc-name').textContent.replace(/\\s+/g, ' ').trim(),
  vis: window.__txt(li.querySelector('.nc-val'), '.sr-only'), spoken: window.__txt(li.querySelector('.nc-val'), '[aria-hidden="true"]') }))"""


def own(fid, name, n, **kw):
    f = {'id': fid, 'src': 'user', 'name': name, 'brand': '', 'barcode': '', 'basis': {'qty': 100, 'unit': 'g'}, 'n': n, 'nova': None, 'portions': [], 'note': '', 'created': 1000, 'updated': 1000}
    f.update(kw)
    return f


def num(s):
    """'1,234.5mg' -> 1234.5 (the first number; thousands separators removed)"""
    m = re.search(r'\d[\d,]*\.?\d*', s)
    return float(m.group(0).replace(',', '')) if m else None


async def main():
    async with async_playwright() as p:
        problems = []

        def check(name, ok, info=''):
            print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(info)[:400].replace('\n', ' | ')) if info != '' else ''))
            if not ok: problems.append(name)

        browser = await p.chromium.launch()
        errs = []

        async def new_ctx(w=390, h=844):
            c = await browser.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2, is_mobile=True, has_touch=True, locale='en-GB', service_workers='block')
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

        LF = own('u:lf', 'List full', {'kcal': 200, 'protein': 10, 'carbohydrate': 20, 'fat': 8, 'fibres': 4, 'salt': 0.5, 'calcium': 100, 'iron': '<2', 'vitamin_c': 30, 'zinc': 2}, est=['vitamin_c'], q='m', fortified=True)
        CAP = own('u:cap', 'Capsule', {'kcal': 5, 'calcium': 120, 'vitamin_d': 10}, basis={'qty': 1, 'unit': 'capsule'})
        DRK = own('u:drk', 'Oat drink', {'kcal': 40, 'protein': 3, 'calcium': '<12'}, ml=True)
        KCL = own('u:kcl', 'Only energy', {'kcal': 50})
        ZER = own('u:zer', 'Zero protein', {'kcal': 10, 'protein': 0, 'fat': 't'})
        ALL = own('u:all', 'Everything', {k: 1 for k in KEYS})
        ALB = own('u:alb', 'Almost everything', {k: 1 for k in KEYS if k != 'alcohol'})
        EVIL = own('u:evil', '<img src=x onerror="window.__pwn=1"><b>X</b> & "Q"', {'kcal': 10, 'calcium': 7})
        LONG = own('u:long', 'Verylongfoodnamewithoutanyspacesatalltoseeifthesheetwrapsitorbreaksthelayoutonanarrowphone', {'kcal': 10, 'calcium': 7})
        FOODS = [LF, CAP, DRK, KCL, ZER, ALL, ALB, EVIL, LONG]

        async def seed(entries, foods=FOODS):
            await T("""([foods, entries]) => { const t = window.__tapnaplo, S = t.S; S.log.length = 0;
              for (const f of foods) S.foods[f.id] = f;
              entries.forEach(([id, f, a, m], i) => S.log.push({ id, f, a, d: S.day, m, t: 1000 + i, tm: '08:' + String(10 + i) }));
              t.save(); t.render(); }""", [foods, entries])

        async def sheets(): return await T("document.querySelectorAll('.sheet-wrap').length")

        async def close_all():
            for _ in range(4):
                if not await sheets(): break
                await page.locator('.sheet-wrap [aria-label=Close]').last.click()
                await page.wait_for_timeout(120)

        async def new_amount(name, amount=None):
            await close_all()
            await page.click('#tabbar .tab >> nth=0'); await page.wait_for_selector('.hero')
            await page.click('[data-act=add][data-meal=m1]'); await page.wait_for_selector('#q')
            await page.fill('#q', name); await page.wait_for_timeout(500)
            await page.locator('.sheet button', has_text=name).first.click(); await page.wait_for_selector('#amt')
            if amount is not None:
                await page.fill('#amt', str(amount)); await page.wait_for_timeout(120)

        async def edit_amount(entry_id, amount=None):
            await close_all()
            await page.click('#tabbar .tab >> nth=0'); await page.wait_for_selector('.hero')
            await page.click(f'.entry[data-id="{entry_id}"]'); await page.wait_for_selector('#amt')
            if amount is not None:
                await page.fill('#amt', str(amount)); await page.wait_for_timeout(120)

        rows = lambda: T(ROWS)
        byl = lambda rs: {r['label']: r for r in rs}

        # =========================================================== 1  Amount sheet, new entry
        await seed([])
        await new_amount('List full', 150)
        top = "[...document.querySelectorAll('.sheet-wrap')].pop().innerText.slice(0, 40)"
        check('the sheet is the Amount sheet (new entry)', (await T(top)).startswith('Amount'), await T(top))
        check('the list sits inside the kcal card (#prev)', await T("!!document.querySelector('.sheet #prev .allnut')"))
        title = await T("document.querySelector('#prev .an-t').textContent")
        rs = await rows()
        check('the title says how many nutrients have data and the number is right', title == f'All nutrients with data for this amount ({len(rs)})' and len(rs) == 10, [title, len(rs)])
        b = byl(rs)
        check('150 g of 10 g protein per 100 g: Protein 15 g', b['Protein']['vis'] == '15g', b.get('Protein'))
        check('Energy 300 kcal, Carbohydrate 30 g, Fat 12 g, Fibre 6 g, Salt 0.75 g', [b['Energy']['vis'], b['Carbohydrate']['vis'], b['Fat']['vis'], b['Fibre']['vis'], b['Salt']['vis']] == ['300kcal', '30g', '12g', '6g', '0.75g'], [b['Energy']['vis'], b['Carbohydrate']['vis'], b['Fat']['vis'], b['Fibre']['vis'], b['Salt']['vis']])
        check('Calcium 150 mg, Zinc 3 mg', [b['Calcium']['vis'], b['Zinc']['vis']] == ['150mg', '3mg'], [b['Calcium']['vis'], b['Zinc']['vis']])
        check('an estimated value has a ~ (Vitamin C ~45 mg), a label value has none', b['Vitamin C']['vis'] == '~45mg' and not b['Calcium']['vis'].startswith('~'), b['Vitamin C'])
        check('...and a screen reader hears "estimated", not the tilde', b['Vitamin C']['spoken'] == 'estimated 45mg', b['Vitamin C']['spoken'])
        check('a value below the detection limit is shown as <3 mg (3 = 2 per 100 g x 1.5)', b['Iron']['vis'] == '<3mg' and b['Iron']['spoken'] == 'below 3mg', b['Iron'])
        check('the units are the ones of the Nutrients tab', await T("[...document.querySelectorAll('#prev .an-row dd em')].map((e) => e.textContent)") == ['kcal', 'g', 'g', 'g', 'g', 'g', 'mg', 'mg', 'mg', 'mg'], await T("[...document.querySelectorAll('#prev .an-row dd em')].map((e) => e.textContent)"))
        heads = await T("[...document.querySelectorAll('#prev .an-h')].map((h) => h.textContent)")
        check('grouped like the Nutrients tab, only groups that have rows get a heading', heads == ['Energy & macronutrients', 'Minerals', 'Vitamins'] or heads[:1] == ['Energy & macronutrients'] and 'Minerals' in heads and 'Vitamins' in heads and 'Fatty acids & cholesterol' not in heads, heads)
        order = [r['label'] for r in rs]
        check('rows follow the order of the Nutrients tab (Energy, Protein, Carbohydrate, Fat, Fibre, Salt, then minerals)', order[:6] == ['Energy', 'Protein', 'Carbohydrate', 'Fat', 'Fibre', 'Salt'], order)
        none_txt = await T("document.querySelector('#prev .an-none').textContent")
        check('the missing ones are counted, not listed, and called not zero', none_txt == 'No data for 54 more nutrients. They are not shown, and they are not zero.', none_txt)
        check('no row for a nutrient the food has no data for (Vitamin B12, Protein is there)', 'Vitamin B12' not in b and 'Protein' in b)
        check('the old summary line and the "Data for N of 42" line are still there', 'protein 15 g' in await page.inner_text('#prev') and 'tracked nutrients' in await page.inner_text('#prev'))
        check('a food with estimates still has its fold below the list', await T("(() => { const p = document.querySelector('#prev'); const d = p.nextElementSibling; return !!d && d.tagName === 'DETAILS' && /Estimated values/.test(d.textContent); })()"))

        # live update
        await page.fill('#amt', '50'); await page.wait_for_timeout(100)
        b = byl(await rows())
        check('typing a new amount updates the list at once (50 g: Protein 5 g, Calcium 50 mg, Vitamin C ~15 mg, Iron <1 mg)', [b['Protein']['vis'], b['Calcium']['vis'], b['Vitamin C']['vis'], b['Iron']['vis']] == ['5g', '50mg', '~15mg', '<1mg'], [b['Protein']['vis'], b['Calcium']['vis'], b['Vitamin C']['vis'], b['Iron']['vis']])
        await page.fill('#amt', '1234'); await page.wait_for_timeout(100)
        b = byl(await rows())
        check('a big amount uses the thousands separator like everywhere else (Calcium 1,234 mg)', b['Calcium']['vis'] == '1,234mg' and b['Energy']['vis'] == '2,468kcal', [b['Calcium']['vis'], b['Energy']['vis']])
        await page.fill('#amt', '12,5'); await page.wait_for_timeout(100)
        b = byl(await rows())
        check('a decimal comma works (12,5 g: Protein 1.25 g)', b['Protein']['vis'] == '1.25g', b['Protein'])
        await page.click('#chips button:has-text("30 g")'); await page.wait_for_timeout(100)
        check('a chip button updates the list too (30 g: Protein 3 g)', byl(await rows())['Protein']['vis'] == '3g')
        for bad in ('', '0', 'abc', '-5'):
            await page.fill('#amt', bad); await page.wait_for_timeout(100)
            check(f'amount "{bad}": no list, the old hint instead, nothing shown as 0', await T("document.querySelectorAll('#prev .allnut').length") == 0 and 'Enter a positive number.' in await page.inner_text('#prev'))
        await page.fill('#amt', '150'); await page.wait_for_timeout(100)
        check('a valid amount again brings the list back', len(await rows()) == 10)

        # the buttons stay in view while the list is long
        await close_all()
        await new_amount('Everything', 100)
        sb = await T("(() => { const s = [...document.querySelectorAll('.sheet-b')].pop(); return [s.scrollHeight, s.clientHeight]; })()")
        check('a food with data for every nutrient makes a long sheet that scrolls inside', sb[0] > sb[1] + 400, sb)
        await T("(() => { const s = [...document.querySelectorAll('.sheet-b')].pop(); s.scrollTop = s.scrollHeight; })()"); await page.wait_for_timeout(150)
        ok = await T("(() => { const r = document.querySelector('#ok').getBoundingClientRect(); return [r.top, r.bottom, window.innerHeight]; })()")
        check('...and the Add button is still in view at the end of the list (sticky bar)', ok[0] >= 0 and ok[1] <= ok[2] + 1, ok)
        rs = await rows()
        check('all 64 rows are there, and there is no "No data" line when nothing is missing', len(rs) == 64 and await T("document.querySelectorAll('#prev .an-none').length") == 0 and 'with data for this amount (64)' in await T("document.querySelector('#prev .an-t').textContent"), len(rs))
        check('every nutrient is in exactly one group (6 headings)', await T("document.querySelectorAll('#prev .an-h').length") == 6)
        await close_all()
        await new_amount('Almost everything', 100)
        check('one nutrient missing: singular wording', await T("document.querySelector('#prev .an-none').textContent") == 'No data for 1 more nutrient. It is not shown, and it is not zero.', await T("document.querySelector('#prev .an-none').textContent"))
        check('...and Alcohol is not in the list', 'Alcohol' not in byl(await rows()))

        # nothing but energy; zero and trace
        await close_all()
        await new_amount('Only energy', 100)
        rs = await rows()
        check('a food that only knows its energy lists one row and counts the other 63', [r['label'] for r in rs] == ['Energy'] and 'No data for 63 more nutrients.' in await T("document.querySelector('#prev .an-none').textContent"), [r['label'] for r in rs])
        check('...no Minerals/Vitamins heading for it', await T("[...document.querySelectorAll('#prev .an-h')].map((h) => h.textContent)") == ['Energy & macronutrients'])
        await close_all()
        await new_amount('Zero protein', 100)
        b = byl(await rows())
        check('a real zero (0) and a trace (t) are shown as 0, and the rest is still missing', b['Protein']['vis'] == '0g' and b['Fat']['vis'] == '0g' and 'Carbohydrate' not in b, [b.get('Protein'), b.get('Fat')])

        # ml drink and a food counted per piece
        await close_all()
        await new_amount('Oat drink', 250)
        b = byl(await rows())
        check('a drink in ml: 250 ml of 3 g protein per 100 ml = 7.5 g, Calcium <30 mg', b['Protein']['vis'] == '7.5g' and b['Calcium']['vis'] == '<30mg' and 'Amount (ml)' in await T("document.querySelector('#amt').closest('label').innerText"), [b['Protein'], b['Calcium']])
        await close_all()
        await new_amount('Capsule', 2)
        b = byl(await rows())
        check('a food counted per piece: 2 capsules of 120 mg calcium = 240 mg, vitamin D 20 µg', b['Calcium']['vis'] == '240mg' and b['Vitamin D']['vis'] == '20µg', [b['Calcium'], b['Vitamin D']])
        await page.fill('#amt', '0.5'); await page.wait_for_timeout(100)
        check('half a capsule: 60 mg', byl(await rows())['Calcium']['vis'] == '60mg')

        # generic (CIQUAL) food: the list is the vector of the food, for the amount
        await close_all()
        await new_amount('Raspberry, frozen, raw', 140)
        n_list = len(await rows())
        n_expect = await T("""() => { const t = window.__tapnaplo; const r = t.searchCiqual('raspberry'); const food = r.find((f) => f.name === 'Raspberry, frozen, raw'); const v = t.vecOf(t.getFood(food.id)); return Array.from(v.lo).filter((x) => !Number.isNaN(x)).length; }""")
        check('a CIQUAL food: the list has one row per nutrient that has data (same number as vecOf)', n_list == n_expect and n_list > 30, [n_list, n_expect])
        b = byl(await rows())
        check('...energy is marked as estimated (~) because it is worked out from the macros, label-free', b['Energy']['vis'].startswith('~') or b['Energy']['vis'].endswith('kcal'), b['Energy'])

        # long names and a hostile name
        await close_all()
        await T("document.documentElement.setAttribute('data-theme', 'light')")
        await new_amount('Verylongfoodname', 100)
        check('a very long food name does not make the sheet wider than the screen', await T("document.documentElement.scrollWidth <= window.innerWidth && (() => { const b = [...document.querySelectorAll('.sheet-b')].pop(); return b.scrollWidth <= b.clientWidth; })()"))

        # =========================================================== 2  Edit entry
        await seed([('e1', 'u:lf', 150, 'm1'), ('e2', 'u:cap', 2, 'm1')])
        await edit_amount('e1')
        check('Edit entry: the title is "Edit entry" and the list is for the amount of the entry (150 g: Protein 15 g)', (await T(top)).startswith('Edit entry') and byl(await rows())['Protein']['vis'] == '15g')
        await page.fill('#amt', '300'); await page.wait_for_timeout(100)
        check('changing the amount in Edit entry updates the list (300 g: Protein 30 g)', byl(await rows())['Protein']['vis'] == '30g')
        check('...but the saved entry is untouched until Save', await T("window.__tapnaplo.S.log.find((e) => e.id === 'e1').a") == 150)
        await page.click('#ok'); await page.wait_for_timeout(300)
        check('Save writes the amount', await T("window.__tapnaplo.S.log.find((e) => e.id === 'e1').a") == 300)
        await page.click('.entry[data-id="e1"]'); await page.wait_for_selector('#amt')
        check('opening it again shows the list for 300 g', byl(await rows())['Protein']['vis'] == '30g' and await page.input_value('#amt') == '300')
        await edit_amount('e2')
        check('Edit entry for a per-piece food (2 capsules): Calcium 240 mg', byl(await rows())['Calcium']['vis'] == '240mg')
        check('Edit entry: Delete, Edit food and Save are still there', await T("['#del', '#editfood', '#ok'].every((s) => !!document.querySelector(s))"))
        await close_all()

        # =========================================================== 3  Nutrients rows
        # day: List full 150 + 50 g (same food twice), Only energy 100 g, Oat drink 250 ml, Capsule 2
        await seed([('e1', 'u:lf', 150, 'm1'), ('e2', 'u:lf', 50, 'm2'), ('e3', 'u:kcl', 100, 'm2'), ('e4', 'u:drk', 250, 'm3'), ('e5', 'u:cap', 2, 'm3')])
        await page.click('[data-tab=nutr]'); await page.wait_for_selector('.nrow')

        async def row(label):
            idx = await T("(l) => [...document.querySelectorAll('details.nrow')].findIndex((r) => r.querySelector('summary > span').textContent === l)", label)
            assert idx >= 0, label
            loc = page.locator('details.nrow').nth(idx)
            await loc.evaluate('(r) => { r.open = true; }')
            return loc

        ca = await row('Calcium')
        parts = await ca.evaluate(PARTS)
        check('Calcium: the foods with data are listed, biggest first (Capsule 240, List full 200, Oat drink <30)', [p['name'].split(' · ')[0] for p in parts] == ['Capsule', 'List full', 'Oat drink'], parts)
        check('...with the amount that was eaten, one line per food, the same food twice merged ("200 g · 2 entries")', [p['name'] for p in parts] == ['Capsule · 2 capsule', 'List full · 200 g · 2 entries', 'Oat drink · 250 ml'], [p['name'] for p in parts])
        check('...and their values (240 mg, 200 mg, <30 mg), the range with the "below" for a screen reader', [p['vis'] for p in parts] == ['240mg', '200mg', '<30mg'] and parts[2]['spoken'] == 'below 30mg', parts)
        check('...the food that has no calcium data is not in the list', not any('Only energy' in p['name'] for p in parts))
        summ = await ca.evaluate("(r) => ({ val: r.querySelector('.nval').textContent.replace(/\\s+/g, ''), pill: r.querySelector('.pill').textContent })")
        check('the row total is unchanged: ≥ 440 mg (a 30 mg range is under 10%, so no range shown), 4 of 5 items', summ == {'val': '≥440mg', 'pill': '4/5'}, summ)
        check('"Added up from" comes first, then the old lines (No data for ..., not Every item)', await ca.evaluate("""(r) => { const k = [...r.children].map((c) => c.className); return k.indexOf('ncontrib') === 1 && k.indexOf('ndetail') > k.indexOf('ncontrib'); }"""))
        nd = await ca.evaluate("(r) => [...r.querySelectorAll('.ndetail')].map((d) => d.textContent)")
        check('the old line still says who has no data', nd and nd[0] == 'No data for: Only energy', nd)
        check('the heading says "Added up from"', await ca.evaluate("(r) => r.querySelector('.nc-h').textContent") == 'Added up from')

        vc = await row('Vitamin C')
        parts = await vc.evaluate(PARTS)
        check('Vitamin C: only List full has data, its value is an estimate (~60 mg for 200 g)', [(p['name'], p['vis'], p['spoken']) for p in parts] == [('List full · 200 g · 2 entries', '~60mg', 'estimated 60mg')], parts)
        nd = await vc.evaluate("(r) => [...r.querySelectorAll('.ndetail')].map((d) => d.textContent)")
        check('...and the old "Estimate, not a label value" line is still there', any(x.startswith('Estimate, not a label value: List full') for x in nd), nd)

        fib = await row('Fibre')
        parts = await fib.evaluate(PARTS)
        check('Fibre: one food, 200 g x 4 = 8 g', [(p['name'], p['vis']) for p in parts] == [('List full · 200 g · 2 entries', '8g')], parts)

        k2 = await row('Vitamin K2')
        check('a row nobody has data for has no list and says no data', await k2.evaluate("(r) => r.querySelectorAll('.ncontrib').length") == 0 and await k2.evaluate("(r) => r.querySelector('.nval').textContent") == 'no data')

        # the parts add up to the total, for every row that has a list
        sums = await T("""() => { const num = (s) => { const m = s.replace(/[~≥]/g, '').match(/\\d[\\d,]*\\.?\\d*/); return m ? parseFloat(m[0].replace(/,/g, '')) : null; };
          const out = [];
          for (const r of document.querySelectorAll('details.nrow')) {
            const lis = [...r.querySelectorAll('.ncontrib li')]; if (!lis.length) continue;
            const total = r.querySelector('.nval').textContent, ranged = /–/.test(total);
            const lo = (li) => { const v = window.__txt(li.querySelector('.nc-val'), '.sr-only'); return /^</.test(v) ? 0 : num(v); };
            const sum = lis.reduce((a, li) => a + lo(li), 0);
            out.push([r.querySelector('summary > span').textContent, num(total), Math.round(sum * 1000) / 1000, lis.length]);
          }
          return out; }""")
        bad = [x for x in sums if abs(x[1] - x[2]) > max(0.011, x[1] * 0.012)]
        check('for every row with a list, the lower values of the parts add up to the lower value of the row', len(sums) >= 8 and bad == [], [len(sums), bad])

        # every row with data has a list, and a list has no more lines than the row has items with data
        cnts = await T("""() => [...document.querySelectorAll('details.nrow:not(.ratio-row)')].map((r) => [r.querySelector('summary > span').textContent, +r.querySelector('.pill').textContent.split('/')[0], r.querySelectorAll('.ncontrib li').length])""")
        bad = [c for c in cnts if (c[1] == 0) != (c[2] == 0) or c[2] > c[1]]
        check('a row with data has a list, a row without data has none, and no list has more lines than items with data', bad == [], bad)

        # a real tap opens the row and the list is visible
        await T("document.querySelectorAll('details.nrow').forEach((r) => { r.open = false; })")
        await page.locator('details.nrow summary', has_text='Zinc').first.click(); await page.wait_for_timeout(150)
        check('a tap on the row opens it and shows "Added up from"', await T("(() => { const r = [...document.querySelectorAll('details.nrow')].find((x) => x.querySelector('summary > span').textContent === 'Zinc'); return r.open && !!r.querySelector('.ncontrib') && r.querySelector('.ncontrib').getBoundingClientRect().height > 20; })()"))
        await T("document.querySelectorAll('details.nrow').forEach((r) => { r.open = true; })")

        # reference intake text is still there under the list
        await T("(() => { const t = window.__tapnaplo; t.S.meta.ref = { sex: 'f', age: '25', meno: 'pre', zinc: 600 }; t.save(); t.render(); })()")
        await page.wait_for_selector('.nrow')
        ca = await row('Calcium')
        check('with a reference profile the row still has its bar and its text, and the list sits before them', await ca.evaluate("""(r) => { const k = [...r.children].map((c) => c.className); const ref = [...r.children].findIndex((c) => /^Reference intake:/.test(c.textContent)); return !!r.querySelector('summary .rline') && k.indexOf('ncontrib') >= 0 && ref > k.indexOf('ncontrib'); }"""))
        await T("(() => { const t = window.__tapnaplo; t.S.meta.ref = null; t.save(); t.render(); })()")
        await page.wait_for_selector('.nrow')

        # other day: not mixed in
        await T("(() => { const t = window.__tapnaplo, S = t.S; const d = new Date(S.day + 'T12:00:00'); d.setDate(d.getDate() - 1); const y = d.toISOString().slice(0, 10); S.log.push({ id: 'y1', d: y, m: 'm1', f: 'u:all', a: 100, t: 5000, tm: '07:00' }); t.save(); })()")
        parts_today = await (await row('Calcium')).evaluate(PARTS)
        check('an entry of another day does not show up in today\'s list', not any('Everything' in p['name'] for p in parts_today))
        await page.click('[data-act=day][data-n="-1"]'); await page.wait_for_timeout(300)
        parts_y = await (await row('Calcium')).evaluate(PARTS)
        check('...and yesterday has its own list (Everything 100 g, 1 mg)', [p['name'] for p in parts_y] == ['Everything · 100 g'] and parts_y[0]['vis'] == '1mg', parts_y)
        await page.click('[data-act=day][data-n="1"]'); await page.wait_for_timeout(300)

        # hostile name: text only
        await seed([('h1', 'u:evil', 100, 'm1'), ('h2', 'u:lf', 100, 'm1')])
        await page.click('[data-tab=nutr]'); await page.wait_for_selector('.nrow')
        parts = await (await row('Calcium')).evaluate(PARTS)
        check('a food name with HTML in it is shown as text in the list', any(p['name'].startswith('<img src=x onerror="window.__pwn=1"><b>X</b> & "Q"') for p in parts) and await T("document.querySelectorAll('.ncontrib img, .ncontrib b').length") == 0 and await T('window.__pwn') is None, parts)
        await new_amount('Capsule', 1)
        check('...and the same name in the Amount sheet is not a problem either (no script ran)', await T('window.__pwn') is None)
        await close_all()

        # =========================================================== 4  the shared (read-only) view
        await seed([('e1', 'u:lf', 150, 'm1'), ('e2', 'u:lf', 50, 'm2'), ('e3', 'u:kcl', 100, 'm2'), ('e4', 'u:drk', 250, 'm3'), ('e5', 'u:cap', 2, 'm3')])
        day = await T('window.__tapnaplo.S.day')
        link = await T('async (d) => (await window.__tapnaplo.shareLink(d, d)).url', day)
        await page.click('[data-tab=nutr]'); await page.wait_for_selector('.nrow')
        sender = {}
        for lab in ('Calcium', 'Vitamin C', 'Fibre'):
            sender[lab] = await (await row(lab)).evaluate(PARTS)
        ctxV = await new_ctx()
        vp = await ctxV.new_page(); watch(vp, 'V')
        await vp.goto(link); await vp.wait_for_selector('.hero')
        await vp.click('#tabbar .tab >> nth=1'); await vp.wait_for_selector('.nrow')
        viewer = {}
        for lab in ('Calcium', 'Vitamin C', 'Fibre'):
            idx = await vp.evaluate("(l) => [...document.querySelectorAll('details.nrow')].findIndex((r) => r.querySelector('summary > span').textContent === l)", lab)
            loc = vp.locator('details.nrow').nth(idx)
            await loc.evaluate('(r) => { r.open = true; }')
            viewer[lab] = await loc.evaluate(PARTS)
        check('the shared view shows the same "Added up from" lists as the sender', viewer == sender and len(viewer['Calcium']) == 3, [viewer['Calcium'], sender['Calcium']])
        await ctxV.close()

        # =========================================================== 5  narrow phone, contrast, fields
        await seed([('e1', 'u:lf', 150, 'm1'), ('e2', 'u:long', 100, 'm1'), ('e3', 'u:cap', 2, 'm3')])
        ctxN = await new_ctx(320, 640)
        np_ = await ctxN.new_page(); watch(np_, 'N')
        await np_.goto(URL); await np_.wait_for_selector('.hero')
        await np_.evaluate("""([foods, entries]) => { const t = window.__tapnaplo, S = t.S; for (const f of foods) S.foods[f.id] = f;
          entries.forEach(([id, f, a, m], i) => S.log.push({ id, f, a, d: S.day, m, t: 1000 + i, tm: '08:' + String(10 + i) })); t.save(); t.render(); }""", [FOODS, [('e1', 'u:lf', 150, 'm1'), ('e2', 'u:long', 100, 'm1'), ('e3', 'u:cap', 2, 'm3')]])
        await np_.click('.entry[data-id="e2"]'); await np_.wait_for_selector('#amt')
        fits = await np_.evaluate("document.documentElement.scrollWidth <= window.innerWidth && (() => { const b = document.querySelector('.sheet-b'); return b.scrollWidth <= b.clientWidth; })()")
        check('320 px: the Amount sheet with a very long food name has no sideways scroll', fits)
        await np_.locator('.sheet-wrap [aria-label=Close]').last.click(); await np_.wait_for_timeout(150)
        await np_.click('.entry[data-id="e1"]'); await np_.wait_for_selector('#amt')
        check('320 px: the Amount sheet with the full list has no sideways scroll', await np_.evaluate("document.documentElement.scrollWidth <= window.innerWidth && (() => { const b = document.querySelector('.sheet-b'); return b.scrollWidth <= b.clientWidth; })()"))
        if SHOTS: await np_.screenshot(path=os.path.join(SHOTS, 'lists_amount_320.png'))
        await np_.locator('.sheet-wrap [aria-label=Close]').last.click(); await np_.wait_for_timeout(150)
        await np_.click('[data-tab=nutr]'); await np_.wait_for_selector('.nrow')
        await np_.evaluate("document.querySelectorAll('details.nrow').forEach((r) => { r.open = true; })")
        check('320 px: the Nutrients tab with every row open has no sideways scroll', await np_.evaluate("document.documentElement.scrollWidth <= window.innerWidth"))
        wide = await np_.evaluate("[...document.querySelectorAll('.ncontrib li')].filter((li) => li.scrollWidth > li.clientWidth + 1).map((li) => li.textContent.slice(0, 40))")
        check('320 px: no line of "Added up from" is cut off (long name wraps, the value stays whole)', wide == [], wide)
        if SHOTS: await np_.screenshot(path=os.path.join(SHOTS, 'lists_nutrients_320.png'))
        await ctxN.close()

        await seed([('e1', 'u:lf', 150, 'm1'), ('e2', 'u:cap', 2, 'm3')])
        for theme in ('light', 'dark'):
            await T(f"document.documentElement.setAttribute('data-theme', '{theme}')")
            await edit_amount('e1')
            bad = await T(CONTRAST_JS, '.sheet')
            check(f'Amount sheet with the list: text contrast at least 4.5:1 ({theme})', bad == [], bad)
            check(f'Amount sheet: every field has at least 16 px text ({theme})', await T(SMALL_FONTS, '.sheet') == [])
            if SHOTS: await page.screenshot(path=os.path.join(SHOTS, f'lists_amount_{theme}.png'))
            await close_all()
            await page.click('[data-tab=nutr]'); await page.wait_for_selector('.nrow')
            await T("document.querySelectorAll('details.nrow').forEach((r) => { r.open = true; })")
            bad = await T(CONTRAST_JS, '#view')
            check(f'Nutrients tab with every row open: text contrast at least 4.5:1 ({theme})', bad == [], bad)
            if SHOTS: await page.screenshot(path=os.path.join(SHOTS, f'lists_nutrients_{theme}.png'))
        await T("document.documentElement.setAttribute('data-theme', 'light')")

        # =========================================================== 6  version
        await page.click('[data-tab=data]'); await page.wait_for_timeout(300)
        ver = re.search(r'(\d+) · \d+ \w+ 20\d\d', await T('document.body.innerText'))
        check('the Data tab shows version 27 or newer', bool(ver) and int(ver.group(1)) >= 27, ver and ver.group(0))
        sw = open(pathlib.Path(__file__).resolve().parent.parent / 'sw.js', encoding='utf-8').read()
        check('the service worker cache has the number of the version', bool(ver) and f"const CACHE = 'nutrilog-v{ver.group(1)}'" in sw)
        check('no page errors', errs == [], errs[:5])
        await browser.close()
        print('\nALL PASS' if not problems else f'\n{len(problems)} FAILED: {problems}')
        sys.exit(1 if problems else 0)


asyncio.run(main())
