"""Extra meals in the Diary (version 40). Run with the web server on port 8765 (see CLAUDE.md).

Norbert asked on 2026-11-21: after Meal 1-6 he must always be able to add a next Meal when he eats more. The Diary shows Meal 1-6 as before and, under the last meal, one button
"Add Meal N" (N = the highest meal in use + 1, at least 7). It opens the Log food flow with that meal chosen. Nothing new is stored (an entry has the meal id `m7`, `m8` ...), so backup,
Sync and the share link are unchanged. The highest meal is Meal 20 (MEAL_MAX); at that point the button is gone. The Report shows a row for Meal 7 and up only when the period has an
entry in it. The clock of the browser is fixed to Thursday 5 Nov 2026, 12:00 (Budapest).

Covers: the helpers (mealNum, mealNameOf, mealsShown), the empty day (6 meals + "Add Meal 7", 52 px, 390 / 320 px, contrast light and dark), the flow (button -> picker -> Amount sheet with
Meal 7 chosen -> entry m7, toast, section, totals line, next button "Add Meal 8"), the Meal field of the sheet (one more than the highest in use), reload, Edit entry (move back to Meal 2 and
the section and the button follow), the default meal after a Meal 7 entry, choosing Meal 8 in the sheet, the limit of 20, an entry with an unknown meal id, the day totals, the Report (rows,
averages that add up to the Overview, shares, no row without an entry, "No meal"), the entries CSV, the shared copy (Meal 7 shown, no button), Sync's record check, Restore, the version."""
import asyncio, csv, io, json, os, pathlib, re, sys
from datetime import date, timedelta
from playwright.async_api import async_playwright
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_ai_import import CONTRAST_JS

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = os.environ.get('NUTRILOG_URL', 'http://127.0.0.1:8765/index.html')
SHOTS = os.environ.get('SHOTS', '')
NOW = '2026-11-05T12:00:00+01:00'           # Thursday
TODAY = date(2026, 11, 5)


def day(n):
    return (TODAY + timedelta(days=n)).isoformat()


def own(fid, name, n, **kw):
    f = {'id': fid, 'src': 'user', 'name': name, 'brand': '', 'barcode': '', 'basis': {'qty': 100, 'unit': 'g'}, 'n': n, 'nova': None, 'portions': [], 'note': '', 'created': 1000, 'updated': 1000}
    f.update(kw)
    return f


ZETA = own('u:zeta', 'Zetafood', {'kcal': 100, 'protein': 10, 'carbohydrate': 20, 'fat': 5, 'fibres': 2, 'salt': 1})      # per 100 g

DIARY_JS = """() => ({ meals: [...document.querySelectorAll('section.meal')].map((m) => ({ name: m.querySelector('h3').textContent.trim(), kcal: m.querySelector('.mk') ? m.querySelector('.mk').textContent.trim() : null,
    rows: m.querySelectorAll('.entry').length, sum: m.querySelector('.meal-sum') ? [...m.querySelectorAll('.meal-sum .ms')].map((e) => e.textContent.replace(/\\s+/g, ' ').trim()) : null })),
  add: [...document.querySelectorAll('.add-meal')].map((b) => ({ text: b.textContent.trim(), meal: b.dataset.meal, act: b.dataset.act })),
  hero: document.querySelector('.hero-num').firstChild.textContent.trim() })"""
SELECT_JS = """() => { const s = document.querySelector('#meal'); return s ? { value: s.value, options: [...s.options].map((o) => o.value), labels: [...s.options].map((o) => o.textContent) } : null; }"""
MEAL_ROWS_JS = """() => { const sec = document.querySelector('details[data-sec=meals]'); if (!sec) return null; const d = sec.querySelector('.rp-dist'); if (!d) return null;
  return [...d.querySelectorAll('.rp-drow')].map((r) => { const dn = r.querySelector('.rp-dn'), sm = dn.querySelector('small'), dv = r.querySelector('.rp-dv');
    return [dn.firstChild.textContent.trim(), sm ? sm.textContent.trim() : '', dv ? dv.textContent.replace(/\\s+/g, ' ').trim() : '']; }); }"""


def share_pct(vals):
    """the largest-remainder rounding of the app (whole percents that add up to 100)"""
    tot = sum(vals)
    raw = [v / tot * 100 if tot > 0 else 0 for v in vals]
    out = [int(r) for r in raw]
    rest = 100 - sum(out)
    for r, i in sorted(((raw[i] - out[i], i) for i in range(len(vals))), key=lambda t: -t[0]):
        if rest > 0 and raw[i] > 0:
            out[i] += 1; rest -= 1
    return out


async def main():
    async with async_playwright() as p:
        problems = []

        def check(name, ok, info=''):
            print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(info)[:600].replace('\n', ' | ')) if info != '' else ''))
            if not ok: problems.append(name)

        browser = await p.chromium.launch()
        errs = []

        async def new_ctx(w=390, h=844, **kw):
            c = await browser.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2, is_mobile=True, has_touch=True, locale='en-GB', timezone_id='Europe/Budapest', service_workers='block', accept_downloads=True, **kw)
            await c.clock.set_fixed_time(NOW)
            await c.route('**/*openfoodfacts.org/**', lambda r: r.fulfill(status=200, headers={'access-control-allow-origin': '*', 'content-type': 'application/json'}, body='{"products":[],"status":0}'))
            return c

        def watch(pg, tag='P'):
            pg.on('pageerror', lambda e: errs.append(f'{tag} PE {e}'))
            pg.on('console', lambda m: errs.append(f'{tag} C {m.text}') if m.type == 'error' and 'Failed to load resource' not in m.text else None)

        ctx = await new_ctx()
        page = await ctx.new_page(); watch(page)
        await page.goto(URL); await page.wait_for_selector('.hero')
        T = page.evaluate

        async def seed(entries, tab='log', foods=None):
            await T("""([foods, ents, tab]) => { const t = window.__tapnaplo, S = t.S; S.log.length = 0;
              for (const k of Object.keys(S.foods)) delete S.foods[k]; for (const f of foods) S.foods[f.id] = f;
              ents.forEach(([id, f, a, m, d], i) => S.log.push({ id, f, a, d: d || S.day, m, t: 1000 + i, tm: '08:' + String(10 + i) }));
              S.tab = tab; t.save(); t.render(); }""", [foods or [ZETA], entries, tab])
            await page.wait_for_timeout(60)

        async def diary():
            return await T(DIARY_JS)

        async def add_via(selector, amount='100', meal=None, query='zeta'):
            """the real flow: the button, the search, the first result, the Amount sheet"""
            await page.click(selector); await page.fill('#q', query)
            await page.tap('[data-pick] >> nth=0'); await page.wait_for_selector('#amt')
            if meal: await page.select_option('#meal', meal)
            await page.fill('#amt', amount); await page.tap('#ok'); await page.wait_for_timeout(250)

        async def close_sheets():
            for _ in range(5):
                if not await page.locator('#sheets .sheet-wrap').count(): break
                await page.keyboard.press('Escape'); await page.wait_for_timeout(200)

        names6 = [f'Meal {i}' for i in range(1, 7)]

        # ---- the helpers ----
        check('MEAL_COUNT is 6 and MEAL_MAX is 20', await T("[__tapnaplo.MEAL_COUNT, __tapnaplo.MEAL_MAX]") == [6, 20])
        r = await T("""() => { const t = window.__tapnaplo; return [t.mealNum('m1'), t.mealNum('m6'), t.mealNum('m7'), t.mealNum('m20'), t.mealNum('m21'), t.mealNum('m99'), t.mealNum('m0'), t.mealNum('m07'), t.mealNum('m'),
          t.mealNum('M7'), t.mealNum('x'), t.mealNum(''), t.mealNum(null), t.mealNum(undefined), t.mealNum(7), t.mealNum(['m7']), t.mealNum({}), t.mealNum('m7 '), t.mealNum('m1e1')]; }""")
        check('mealNum reads only m1 … m20 (m0, m07, m21, text, numbers, lists are 0)', r == [1, 6, 7, 20, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], r)
        r = await T("""() => { const t = window.__tapnaplo; return [t.mealNameOf('m1'), t.mealNameOf('m12'), t.mealNameOf('x'), t.mealNameOf('m21'), t.mealNameOf(null)]; }""")
        check('mealNameOf gives "Meal N", and an empty text for an unknown id', r == ['Meal 1', 'Meal 12', '', '', ''], r)
        r = await T("""() => { const t = window.__tapnaplo; return [t.mealsShown([]), t.mealsShown([{ m: 'm3' }]), t.mealsShown([{ m: 'm6' }]), t.mealsShown([{ m: 'm7' }, { m: 'm2' }]), t.mealsShown([{ m: 'm9' }]),
          t.mealsShown([{ m: 'm20' }]), t.mealsShown([{ m: 'm21' }, { m: 'x' }, { m: undefined }])]; }""")
        check('mealsShown is 6 at least and the highest valid meal in use', r == [6, 6, 6, 7, 9, 20, 6], r)

        # ---- an empty day ----
        await seed([])
        d = await diary()
        check('an empty day shows Meal 1 … Meal 6', [m['name'] for m in d['meals']] == names6, [m['name'] for m in d['meals']])
        check('and one button "Add Meal 7" that logs into m7', d['add'] == [{'text': 'Add Meal 7', 'meal': 'm7', 'act': 'add'}], d['add'])
        check('the button is a real button under the last meal', await T("""() => { const b = document.querySelector('.add-meal'), ms = document.querySelectorAll('section.meal');
          return b.tagName === 'BUTTON' && b.previousElementSibling === ms[ms.length - 1]; }"""))
        box = await T("""() => { const r = document.querySelector('.add-meal').getBoundingClientRect(), c = document.querySelector('.card').getBoundingClientRect();
          return [Math.round(r.width), Math.round(r.height), Math.round(r.left), Math.round(c.width), Math.round(c.left)]; }""")
        check('it is at least 44 px high and exactly as wide as the cards above it', box[1] >= 44 and box[0] == box[3] and box[2] == box[4], box)
        check('no sideways scroll at 390 px', await T("document.documentElement.scrollWidth <= window.innerWidth"))
        await page.set_viewport_size({'width': 320, 'height': 700}); await page.wait_for_timeout(80)
        check('no sideways scroll at 320 px and the button stays inside the screen', await T("""() => { const r = document.querySelector('.add-meal').getBoundingClientRect();
          return document.documentElement.scrollWidth <= window.innerWidth && r.left >= 0 && r.right <= window.innerWidth; }"""))
        await page.set_viewport_size({'width': 390, 'height': 844}); await page.wait_for_timeout(80)
        for theme in ('light', 'dark'):
            await T("(t) => { document.documentElement.dataset.theme = t; }", theme)
            bad = await T(CONTRAST_JS, '.add-meal')
            check(f'text contrast of the button is at least 4.5:1 ({theme})', bad == [], bad)
            if SHOTS:
                await page.evaluate("document.querySelector('.add-meal').scrollIntoView({block: 'center'})")
                await page.screenshot(path=os.path.join(SHOTS, f'add_meal_{theme}.png'))
        await T("() => { document.documentElement.dataset.theme = 'light'; }")

        # ---- the Meal field of the top Log food button on an empty day: Meal 1 chosen, one more than shown (Meal 7) is offered ----
        await page.click('.act.primary'); await page.fill('#q', 'zeta')
        await page.tap('[data-pick] >> nth=0'); await page.wait_for_selector('#amt')
        s = await T(SELECT_JS)
        check('Log food on an empty day: Meal 1 is chosen and the field offers Meal 1 … Meal 7', s['value'] == 'm1' and s['options'] == [f'm{i}' for i in range(1, 8)] and s['labels'][6] == 'Meal 7', s)
        await close_sheets()

        # ---- the flow: Add Meal 7 -> picker -> Amount sheet ----
        await page.click('.add-meal'); await page.wait_for_selector('#q')
        check('the button opens the Log food search', await page.is_visible('#q'))
        await page.fill('#q', 'zeta'); await page.tap('[data-pick] >> nth=0'); await page.wait_for_selector('#amt')
        s = await T(SELECT_JS)
        check('the Amount sheet has Meal 7 chosen (and Meal 8 as the next one)', s['value'] == 'm7' and s['options'] == [f'm{i}' for i in range(1, 9)] and s['labels'][6] == 'Meal 7', s)
        await page.fill('#amt', '100'); await page.tap('#ok'); await page.wait_for_timeout(250)
        toast = await T("document.querySelector('#toast').textContent")
        check('the toast says the food went to Meal 7', 'to Meal 7' in toast and 'Zetafood' in toast, toast)
        check('the entry is stored with the meal id m7', await T("__tapnaplo.S.log.map((e) => e.m)") == ['m7'])
        d = await diary()
        check('the Diary now has 7 meals, Meal 7 holds the entry with its energy and its totals line', [m['name'] for m in d['meals']] == names6 + ['Meal 7'] and d['meals'][6]['rows'] == 1 and d['meals'][6]['kcal'] == '100 kcal'
              and d['meals'][6]['sum'] == ['P 10g', 'C 20g', 'F 5g', 'Fib 2g', 'Salt 1g'] and all(m['rows'] == 0 for m in d['meals'][:6]), d['meals'][6])
        check('the day total counts the entry and the button is now "Add Meal 8"', d['hero'] == '100' and d['add'] == [{'text': 'Add Meal 8', 'meal': 'm8', 'act': 'add'}], [d['hero'], d['add']])
        check('the other meals have no totals line', all(m['sum'] is None for m in d['meals'][:6]))
        await page.wait_for_timeout(400)

        # ---- reload ----
        await page.reload(); await page.wait_for_selector('.hero'); await page.wait_for_timeout(300)
        d = await diary()
        check('after a reload Meal 7 and "Add Meal 8" are still there', len(d['meals']) == 7 and d['meals'][6]['rows'] == 1 and d['add'][0]['text'] == 'Add Meal 8', d['add'])

        # ---- the default meal follows the latest entry, one more than the highest in use is offered ----
        await page.click('.act.primary'); await page.fill('#q', 'zeta')
        await page.tap('[data-pick] >> nth=0'); await page.wait_for_selector('#amt')
        s = await T(SELECT_JS)
        check('Log food after a Meal 7 entry: Meal 7 is the default and the field offers up to Meal 8', s['value'] == 'm7' and s['options'][-1] == 'm8' and len(s['options']) == 8, s)
        # choosing the next meal in the sheet creates it
        await page.select_option('#meal', 'm8'); await page.fill('#amt', '50'); await page.tap('#ok'); await page.wait_for_timeout(250)
        d = await diary()
        check('choosing Meal 8 in the sheet makes Meal 8 (the empty Meal 7 stays shown) and the next button is "Add Meal 9"', len(d['meals']) == 8 and d['meals'][7]['name'] == 'Meal 8' and d['meals'][7]['rows'] == 1
              and d['meals'][6]['rows'] == 1 and d['add'][0]['text'] == 'Add Meal 9', [m['name'] for m in d['meals']])
        # an empty slot between two used meals is shown as an ordinary empty meal
        await seed([('a', 'u:zeta', 100, 'm9')])
        d = await diary()
        check('one entry in Meal 9: Meal 1 … Meal 9 are shown, 8 of them empty, the button is "Add Meal 10"', len(d['meals']) == 9 and d['meals'][8]['rows'] == 1 and sum(m['rows'] for m in d['meals']) == 1 and d['add'][0]['text'] == 'Add Meal 10', d['add'])
        # the small + of a meal header still logs into its own meal
        await page.locator('section.meal').nth(7).locator('[data-act=add]').click(); await page.fill('#q', 'zeta')
        await page.tap('[data-pick] >> nth=0'); await page.wait_for_selector('#amt')
        s = await T(SELECT_JS)
        check('the + of the Meal 8 header opens the sheet with Meal 8 chosen', s['value'] == 'm8', s)
        await close_sheets()

        # ---- Edit entry ----
        await seed([('a', 'u:zeta', 100, 'm7'), ('b', 'u:zeta', 50, 'm1')])
        await page.tap('.entry[data-id=a]'); await page.wait_for_selector('#amt')
        s = await T(SELECT_JS)
        check('Edit entry of a Meal 7 entry: Meal 7 is chosen, the field offers up to Meal 8', s['value'] == 'm7' and s['options'][-1] == 'm8' and len(s['options']) == 8, s)
        await page.select_option('#meal', 'm2'); await page.tap('#ok'); await page.wait_for_timeout(250)
        d = await diary()
        check('moving the entry to Meal 2 takes Meal 7 away again and the button goes back to "Add Meal 7"', [m['name'] for m in d['meals']] == names6 and d['meals'][1]['rows'] == 1 and d['add'][0]['text'] == 'Add Meal 7', d['add'])
        await page.tap('.entry[data-id=a]'); await page.wait_for_selector('#amt')
        s = await T(SELECT_JS)
        check('Edit entry of a Meal 2 entry (nothing above Meal 6 in use): the field offers Meal 1 … Meal 7', s['value'] == 'm2' and len(s['options']) == 7, s)
        await page.select_option('#meal', 'm7'); await page.tap('#ok'); await page.wait_for_timeout(250)
        d = await diary()
        check('moving it up to Meal 7 makes Meal 7', len(d['meals']) == 7 and d['meals'][6]['rows'] == 1 and d['add'][0]['text'] == 'Add Meal 8')
        # delete: the last entry of Meal 7 goes, the section goes with it
        await page.tap('.entry[data-id=a]'); await page.wait_for_selector('#del'); await page.tap('#del'); await page.wait_for_timeout(250)
        d = await diary()
        check('deleting the only Meal 7 entry takes Meal 7 and its button away', len(d['meals']) == 6 and d['add'][0]['text'] == 'Add Meal 7', d['add'])

        # ---- day totals and the nutrient numbers count the extra meals ----
        await seed([('a', 'u:zeta', 100, 'm1'), ('b', 'u:zeta', 200, 'm7'), ('c', 'u:zeta', 50, 'm12')])
        d = await diary()
        check('the hero energy adds up Meal 1, Meal 7 and Meal 12 (100 + 200 + 50 g of 100 kcal / 100 g = 350)', d['hero'] == '350', d['hero'])
        check('Meal 12 is the last section, with the 5 sections between Meal 7 and Meal 12 empty, and the button is "Add Meal 13"', len(d['meals']) == 12 and d['meals'][11]['kcal'] == '50 kcal' and d['add'][0]['text'] == 'Add Meal 13', d['add'])
        await page.click('[data-tab=nutr]'); await page.wait_for_timeout(200)
        check('the Nutrients tab counts all three entries', 'Protein' in await T("document.body.innerText") and await T("""() => { const t = window.__tapnaplo; return Math.round(t.totalsFor(t.S.log).lo[t.IDX.protein] * 100) / 100; }""") == 35)
        await page.click('[data-tab=log]'); await page.wait_for_timeout(200)

        # ---- the limit: Meal 20 ----
        await seed([('a', 'u:zeta', 100, 'm19')])
        d = await diary()
        check('with Meal 19 in use the button is "Add Meal 20"', len(d['meals']) == 19 and d['add'] == [{'text': 'Add Meal 20', 'meal': 'm20', 'act': 'add'}], d['add'])
        await page.click('.add-meal'); await page.fill('#q', 'zeta'); await page.tap('[data-pick] >> nth=0'); await page.wait_for_selector('#amt')
        s = await T(SELECT_JS)
        check('Add Meal 20 opens the sheet with Meal 20 chosen and no Meal 21', s['value'] == 'm20' and s['options'][-1] == 'm20' and len(s['options']) == 20, s)
        await page.fill('#amt', '100'); await page.tap('#ok'); await page.wait_for_timeout(250)
        d = await diary()
        check('with Meal 20 in use there are 20 meals and no "Add Meal" button any more', len(d['meals']) == 20 and d['meals'][19]['name'] == 'Meal 20' and d['add'] == [], [len(d['meals']), d['add']])
        await page.tap('.entry >> nth=1'); await page.wait_for_selector('#amt')
        s = await T(SELECT_JS)
        check('Edit entry at the limit: the field offers Meal 1 … Meal 20 only', len(s['options']) == 20 and s['options'][-1] == 'm20', s)
        await close_sheets()
        await page.click('.act.primary'); await page.fill('#q', 'zeta'); await page.tap('[data-pick] >> nth=0'); await page.wait_for_selector('#amt')
        s = await T(SELECT_JS)
        check('Log food at the limit: Meal 20 is the default and the list ends at Meal 20', s['value'] == 'm20' and len(s['options']) == 20, s)
        await close_sheets()
        check('no sideways scroll with 20 meals at 390 px', await T("document.documentElement.scrollWidth <= window.innerWidth"))

        # ---- an entry with an unknown meal id (damaged or very old data) ----
        await seed([('a', 'u:zeta', 100, 'm1'), ('b', 'u:zeta', 100, 'x'), ('c', 'u:zeta', 100, 'm21'), ('d', 'u:zeta', 100, 'm07')])
        d = await diary()
        check('unknown meal ids add no section and no button for them (the Diary has Meal 1 … Meal 6 and "Add Meal 7")', [m['name'] for m in d['meals']] == names6 and d['add'][0]['text'] == 'Add Meal 7', d['add'])
        await T("""() => { const S = window.__tapnaplo.S; S.log.push({ id: 'z', d: S.day, m: 'x', f: 'u:zeta', a: 1, t: 999999, tm: '09:00' }); }""")   # the latest entry has an unknown meal
        await page.click('.act.primary'); await page.fill('#q', 'zeta'); await page.tap('[data-pick] >> nth=0'); await page.wait_for_selector('#amt')
        check('Log food with such an entry as the latest one defaults to Meal 1', (await T(SELECT_JS))['value'] == 'm1')
        await close_sheets()

        # ---- the Report: the Meals and weekdays rows ----
        # logged days: Mon 2 Nov and Thu 5 Nov. Alpha = Zetafood: 100 kcal per 100 g.
        # Mon: Meal 1 100 g (100 kcal), Meal 7 200 g (200 kcal); Thu: Meal 1 100 g (100 kcal), Meal 8 50 g (50 kcal)
        # sums: Meal 1 200, Meal 7 200, Meal 8 50 (450 kcal); averages per logged day (2 days): 100, 100, 25 = 225 kcal = the Overview
        week = [('r1', 'u:zeta', 100, 'm1', day(-3)), ('r2', 'u:zeta', 200, 'm7', day(-3)), ('r3', 'u:zeta', 100, 'm1', day(0)), ('r4', 'u:zeta', 50, 'm8', day(0))]
        await T("""() => { const t = window.__tapnaplo; t.RP.kind = 'week'; t.RP.anchor = '2026-11-05'; t.RP.custom = null; for (const k of Object.keys(t.RP.open)) t.RP.open[k] = true; }""")
        await seed(week, tab='report')
        rows = await T(MEAL_ROWS_JS)
        check('the Report lists Meal 1 … Meal 6, then Meal 7 and Meal 8 (the meals that have entries) and nothing else', rows is not None and [r[0] for r in rows] == names6 + ['Meal 7', 'Meal 8'], rows and [r[0] for r in rows])
        by = {r[0]: r for r in rows}
        check('Meal 2 … Meal 6 say "no entries"', all('no entries' in by[f'Meal {i}'][2] for i in range(2, 7)), [by[f'Meal {i}'][2] for i in range(2, 7)])
        check('Meal 7: 100 kcal on average, "1 of 2 days · 1 item"', by['Meal 7'][1] == '1 of 2 days · 1 item' and by['Meal 7'][2].startswith('100'), by['Meal 7'])
        check('Meal 8: 25 kcal on average, "1 of 2 days · 1 item"', by['Meal 8'][1] == '1 of 2 days · 1 item' and by['Meal 8'][2].startswith('25'), by['Meal 8'])
        check('Meal 1: 100 kcal on average, "2 of 2 days · 2 items"', by['Meal 1'][1] == '2 of 2 days · 2 items' and by['Meal 1'][2].startswith('100'), by['Meal 1'])
        r = await T("""() => { const t = window.__tapnaplo, P = t.RP_NOW.P, rows = t.rpMealRows(P); return { rows: rows.map((o) => [o.name, Math.round(o.avgLo * 100) / 100, o.state, o.shareTxt]), overview: Math.round(P.T.lo[0] * 100) / 100, nd: P.nd, sum: Math.round(rows.reduce((s, o) => s + o.avgLo, 0) * 100) / 100 }; }""")
        check('the meal averages add up to the Overview energy (225 kcal, 2 logged days)', r['nd'] == 2 and r['overview'] == 225 and r['sum'] == 225, r)
        pc = share_pct([200, 0, 0, 0, 0, 0, 200, 50])           # Meal 1 … Meal 6, Meal 7, Meal 8
        check('the shares are whole percents that add up to 100 (Meal 1, Meal 7, Meal 8: 45 / 45 / 10 by the largest remainder)', [o[3] for o in r['rows'] if o[2] == 'ok'] == [f'{pc[0]}%', f'{pc[6]}%', f'{pc[7]}%'] and sum(pc) == 100, [r['rows'], pc])
        check('the Overview average in the page is the same number', '225' in await T("document.querySelector('.rp-sec[data-sec=overview]') ? document.querySelector('.rp-sec[data-sec=overview]').innerText : document.body.innerText"))
        # no entry above Meal 6 in the period: exactly the six rows
        await seed([('r1', 'u:zeta', 100, 'm1', day(-3)), ('r3', 'u:zeta', 100, 'm5', day(0))], tab='report')
        rows = await T(MEAL_ROWS_JS)
        check('a period without entries in Meal 7 and up has exactly the six rows (as before)', [r[0] for r in rows] == names6, [r[0] for r in rows])
        # an entry of another period does not add a row to this one
        await seed([('r1', 'u:zeta', 100, 'm1', day(-3)), ('o1', 'u:zeta', 100, 'm9', '2026-09-10')], tab='report')
        rows = await T(MEAL_ROWS_JS)
        check('Meal 9 in September gives no row in the week of 2 Nov', [r[0] for r in rows] == names6, [r[0] for r in rows])
        # unknown ids go to "No meal", never to a Meal row
        await seed([('r1', 'u:zeta', 100, 'm1', day(-3)), ('r2', 'u:zeta', 100, 'x', day(-3)), ('r3', 'u:zeta', 100, 'm21', day(0)), ('r4', 'u:zeta', 100, 'm10', day(0))], tab='report')
        rows = await T(MEAL_ROWS_JS)
        by = {r[0]: r for r in rows}
        check('unknown ids (x, m21) are "No meal" (2 items), m10 is its own row, the order is Meal 1-6, Meal 10, No meal', [r[0] for r in rows] == names6 + ['Meal 10', 'No meal'] and 'Meal 21' not in by and by['No meal'][1].endswith('2 items'), [r[0] for r in rows])
        check('the sums still add up with the extra rows and "No meal"', await T("""() => { const t = window.__tapnaplo, P = t.RP_NOW.P; return Math.abs(t.rpMealRows(P).reduce((s, o) => s + o.avgLo, 0) - P.T.lo[0]) < 1e-9; }"""))
        # the Day period
        await T("() => { const t = window.__tapnaplo; t.RP.kind = 'day'; t.RP.anchor = '2026-11-05'; }")
        await seed([('r1', 'u:zeta', 100, 'm1', day(0)), ('r2', 'u:zeta', 200, 'm7', day(0))], tab='report')
        rows = await T(MEAL_ROWS_JS)
        check('a Day period shows Meal 7 too (200 kcal, "1 item")', rows is not None and rows[-1][0] == 'Meal 7' and rows[-1][1] == '1 item' and rows[-1][2].startswith('200'), rows and rows[-1])
        await T("() => { const t = window.__tapnaplo; t.RP.kind = 'week'; }")

        # ---- the entries CSV ----
        await seed([('a', 'u:zeta', 100, 'm1', day(0)), ('b', 'u:zeta', 200, 'm7', day(0)), ('c', 'u:zeta', 50, 'm12', day(0)), ('d', 'u:zeta', 10, 'x', day(0))], tab='data')
        await page.wait_for_selector('[data-act=export-entries]')
        async with page.expect_download() as dl_:
            await page.click('[data-act=export-entries]')
        dl = await dl_.value
        path = str(pathlib.Path(__file__).resolve().parent / 'entries_extra_meals.csv')
        await dl.save_as(path)
        rows = list(csv.reader(io.StringIO(open(path, encoding='utf-8-sig').read())))
        meal_col = rows[0].index('meal')
        check('the entries CSV writes "Meal 7" and "Meal 12", and an empty text for an unknown id', sorted(r[meal_col] for r in rows[1:]) == ['', 'Meal 1', 'Meal 12', 'Meal 7'], [r[meal_col] for r in rows[1:]])
        os.remove(path)
        await page.click('[data-tab=log]'); await page.wait_for_timeout(200)

        # ---- the shared copy: Meal 7 is shown, there is no button ----
        await seed([('a', 'u:zeta', 100, 'm1'), ('b', 'u:zeta', 200, 'm7')])
        link = await T("""async () => { const t = window.__tapnaplo; const r = await t.shareLink(t.S.day, t.S.day); return r.url; }""")
        check('a link with a Meal 7 entry can be made', link.startswith(URL + '#share='), link[:80])
        ctxB = await new_ctx()
        v = await ctxB.new_page(); watch(v, 'V')
        await v.goto(link); await v.wait_for_selector('.hero')
        d = await v.evaluate(DIARY_JS)
        check('the viewer shows Meal 1 … Meal 7 with the Meal 7 entry', [m['name'] for m in d['meals']] == names6 + ['Meal 7'] and d['meals'][6]['rows'] == 1 and d['meals'][0]['rows'] == 1 and d['hero'] == '300', [[m['name'], m['rows']] for m in d['meals']])
        check('and has no "Add Meal" button and no + in any meal', d['add'] == [] and await v.evaluate("document.querySelectorAll('[data-act=add], .add-meal').length") == 0)
        await v.close()
        # a meal that is only in the link, never in the sender's own app (a hand-made link with Meal 14)
        snap = json.loads(await T("""() => { const t = window.__tapnaplo; return t.shareSnapshot(t.S.day, t.S.day).json; }"""))
        k = next(iter(snap['days'])); snap['days'][k][1][0] = 'm14'
        import base64, zlib
        link14 = URL + '#share=z.' + base64.urlsafe_b64encode(zlib.compress(json.dumps(snap).encode())).decode().rstrip('=')
        v = await ctxB.new_page(); watch(v, 'V')
        await v.goto(link14); await v.wait_for_selector('.hero')
        d = await v.evaluate(DIARY_JS)
        check('a link with a Meal 14 entry shows 14 meals', len(d['meals']) == 14 and d['meals'][13]['rows'] == 1 and d['add'] == [], [len(d['meals']), d['add']])
        await v.close()
        await ctxB.close()

        # ---- Sync: a received entry with Meal 7 is a valid record ----
        r = await T("""() => { const t = window.__tapnaplo; const ok = (m) => !!t.validRec('e:q1', { id: 'q1', d: '2026-11-05', f: 'u:zeta', a: 100, m, t: 1 }); return [ok('m7'), ok('m12'), ok('m1')]; }""")
        check('Sync accepts entries with Meal 7, Meal 12 and Meal 1', r == [True, True, True], r)

        # ---- Restore from a backup file with a Meal 7 entry ----
        backup = {'app': 'tapnaplo', 'version': 1, 'exported': 1762340000000, 'foods': {ZETA['id']: ZETA}, 'log': [{'id': 'b1', 'd': '2026-11-05', 'm': 'm7', 'f': 'u:zeta', 'a': 150, 't': 5000, 'tm': '19:30'}], 'meta': {}}
        bpath = pathlib.Path(__file__).resolve().parent / 'backup_extra_meals.json'
        bpath.write_text(json.dumps(backup), encoding='utf-8')
        await page.click('[data-tab=data]'); await page.wait_for_timeout(200)
        await page.set_input_files('#importfile', str(bpath)); await page.wait_for_selector('[data-ok]'); await page.click('[data-ok]'); await page.wait_for_timeout(600)
        bpath.unlink()
        await page.click('[data-tab=log]'); await page.wait_for_timeout(300)
        d = await diary()
        check('Restore keeps a Meal 7 entry and the Diary shows it with "Add Meal 8"', len(d['meals']) == 7 and d['meals'][6]['rows'] == 1 and d['meals'][6]['kcal'] == '150 kcal' and d['add'][0]['text'] == 'Add Meal 8', [d['meals'][6], d['add']])

        # ---- version ----
        await page.click('[data-tab=data]'); await page.wait_for_timeout(300)
        ver = re.search(r'(\d+) · \d+ \w+ 20\d\d', await T("document.body.innerText"))
        check('the Data tab shows version 40 or newer', bool(ver) and int(ver.group(1)) >= 40, ver and ver.group(0))
        sw = (ROOT / 'sw.js').read_text(encoding='utf-8')
        check('the service worker cache has the number of the version', bool(ver) and f"const CACHE = 'nutrilog-v{ver.group(1)}'" in sw)

        check('no page errors', errs == [], errs[:5])
        await browser.close()
        print('\nALL PASS' if not problems else f'\n{len(problems)} FAILED: {problems}')
        sys.exit(1 if problems else 0)


asyncio.run(main())
