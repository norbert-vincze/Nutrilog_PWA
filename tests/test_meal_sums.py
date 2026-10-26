"""Meal totals in the Diary (version 19). Run with the web server on port 8765 (see CLAUDE.md).

Under the header of every meal that has entries there is one line with the totals of that meal, in grams: P protein, C carbohydrate, F fat,
Fib fibre, Salt. Same rules as the Nutrients tab: "≥" when an item of the meal has no data for it (a lower value), "~" when part of the
value is an estimate, "–" when no item has data; missing data is never counted as zero. A meal without entries has no line. A screen reader
gets the full words (hidden text). The numbers follow edits and other days do not leak in.
Covers: complete data, partial data (≥), nothing known (–), estimates (~, also ≥~), empty meal, other meals unaffected, other day, edit follows,
delete follows, the spoken text, no sideways scroll at 390 px in the worst case, contrast in light and dark, the version number (19 or newer, same as the service worker cache), no page errors."""
import asyncio, os, pathlib, re, sys
from playwright.async_api import async_playwright
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_ai_import import CONTRAST_JS

URL = 'http://127.0.0.1:8765/index.html'
SHOTS = os.environ.get('SHOTS', '')


def own(fid, name, n, **kw):
    f = {'id': fid, 'src': 'user', 'name': name, 'brand': '', 'barcode': '', 'basis': {'qty': 100, 'unit': 'g'}, 'n': n, 'nova': None, 'portions': [], 'note': '', 'created': 1000, 'updated': 1000}
    f.update(kw)
    return f


FULL = {'kcal': 165, 'protein': 10, 'carbohydrate': 20, 'fat': 5, 'fibres': 2, 'salt': 1}           # per 100 g
ONLY_P = {'kcal': 40, 'protein': 8}                                                                     # no carbohydrate, fat, fibre, salt
EST_P = {'kcal': 120, 'protein': 10, 'carbohydrate': 5, 'fat': 4, 'fibres': 1, 'salt': 0.5}
BIG = {'kcal': 900, 'protein': 123, 'carbohydrate': 345, 'fat': 67.8, 'fibres': 12, 'salt': 12.3}


async def main():
    async with async_playwright() as p:
        problems = []

        def check(name, ok, info=''):
            print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(info)) if info != '' else ''))
            if not ok: problems.append(name)

        browser = await p.chromium.launch()
        errs = []
        ctx = await browser.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True, locale='en-GB', service_workers='block')
        await ctx.route('**/*openfoodfacts.org/**', lambda r: r.fulfill(status=200, headers={'access-control-allow-origin': '*', 'content-type': 'application/json'}, body='{"products":[],"status":0}'))
        page = await ctx.new_page()
        page.on('pageerror', lambda e: errs.append(f'PE {e}'))
        page.on('console', lambda m: errs.append(f'C {m.text}') if m.type == 'error' and 'Failed to load resource' not in m.text else None)
        await page.goto(URL); await page.wait_for_selector('.hero')
        T = page.evaluate

        async def seed(foods, entries):
            await T("""([foods, entries]) => { const S = window.__tapnaplo.S; S.log.length = 0;
              for (const f of foods) S.foods[f.id] = f;
              entries.forEach(([id, f, a, m], i) => S.log.push({ id, f, a, d: S.day, m, t: 1000 + i, tm: '08:' + String(10 + i) }));
              window.__tapnaplo.invalidate && window.__tapnaplo.invalidate(); window.__tapnaplo.save(); window.__tapnaplo.render(); }""", [foods, entries])

        async def sums(meal_idx):
            """['P 15g', 'C 30g', ...] of one meal (0-based position in the Diary), or None when it has no line."""
            return await T("""(i) => { const m = document.querySelectorAll('.meal')[i]; const s = m && m.querySelector('.meal-sum');
              return s ? [...s.querySelectorAll('.ms')].map((e) => e.textContent.replace(/\\s+/g, ' ').trim()) : null; }""", meal_idx)

        foods = [own('u:t1', 'Full food', FULL), own('u:t2', 'Only protein', ONLY_P), own('u:t3', 'Estimated protein', EST_P, est=['protein'], q='l'),
                 own('u:t4', 'Big food', BIG)]

        # ---- complete data: 150 g of Full food ----
        await seed(foods, [('e1', 'u:t1', 150, 'm1')])
        check('a meal with one complete entry shows P C F Fib Salt in grams', await sums(0) == ['P 15g', 'C 30g', 'F 7.5g', 'Fib 3g', 'Salt 1.5g'], await sums(0))
        check('the meal energy in the header is still there', await T("document.querySelectorAll('.meal')[0].querySelector('.mk').textContent") == '248 kcal')
        check('a meal without entries has no totals line', await sums(1) is None and await T("document.querySelectorAll('.meal-sum').length") == 1)
        check('the line sits between the header and the rows', await T("(() => { const m = document.querySelectorAll('.meal')[0]; return m.children[0].className === 'meal-h' && m.children[1].className === 'meal-sum' && m.children[2].className === 'rows'; })()"))

        # ---- partial data: a second entry that knows only protein ----
        await seed(foods, [('e1', 'u:t1', 150, 'm1'), ('e2', 'u:t2', 100, 'm1'), ('e3', 'u:t2', 50, 'm2')])
        check('an item without data makes the others lower values (≥), protein is complete', await sums(0) == ['P 23g', 'C ≥30g', 'F ≥7.5g', 'Fib ≥3g', 'Salt ≥1.5g'], await sums(0))
        check('a meal where nothing is known shows – and not 0', await sums(1) == ['P 4g', 'C –', 'F –', 'Fib –', 'Salt –'], await sums(1))
        check('each meal is counted on its own (meal 1 does not include meal 2)', (await sums(0))[0] == 'P 23g')

        # ---- estimates ----
        await seed(foods, [('e1', 'u:t3', 100, 'm1'), ('e2', 'u:t3', 100, 'm2'), ('e3', 'u:t2', 100, 'm2')])
        check('a value that is an estimate gets ~ (only protein is marked)', await sums(0) == ['P ~10g', 'C 5g', 'F 4g', 'Fib 1g', 'Salt 0.5g'], await sums(0))
        check('an estimate with complete data gets ~, a lower value without estimate gets ≥ (the ≥~ mix is in the worst case below)', (await sums(1))[0] == 'P ~18g' and (await sums(1))[1] == 'C ≥5g', await sums(1))

        # ---- the spoken text ----
        spoken = await T("document.querySelectorAll('.meal')[1].querySelector('.sr-only').textContent")
        check('screen readers get the full words', spoken.startswith('Meal 2 totals.') and 'Protein: about 18 g' in spoken and 'Carbohydrate: at least 5 g' in spoken, spoken)
        check('the short form is hidden from screen readers, the full text is not', await T("(() => { const s = document.querySelector('.meal-sum'); return s.querySelector('.ms-row').getAttribute('aria-hidden') === 'true' && !s.querySelector('.sr-only').closest('[aria-hidden]'); })()"))
        await seed(foods, [('e1', 'u:t2', 100, 'm1')])
        spoken = await T("document.querySelector('.sr-only').textContent")
        check('no data is said as no data', 'Fat: no data' in spoken and 'Salt: no data' in spoken, spoken)

        # ---- edits and deletes follow ----
        await seed(foods, [('e1', 'u:t1', 100, 'm1'), ('e2', 'u:t1', 100, 'm1')])
        check('two entries add up', (await sums(0))[:2] == ['P 20g', 'C 40g'], await sums(0))
        await T("() => { const S = window.__tapnaplo.S; S.log.find((e) => e.id === 'e2').a = 50; window.__tapnaplo.save(); window.__tapnaplo.render(); }")
        check('a changed amount changes the line', (await sums(0))[:2] == ['P 15g', 'C 30g'], await sums(0))
        await T("() => { const S = window.__tapnaplo.S; S.log.find((e) => e.id === 'e2').m = 'm2'; window.__tapnaplo.save(); window.__tapnaplo.render(); }")
        check('moving an entry to another meal moves its numbers', (await sums(0))[:2] == ['P 10g', 'C 20g'] and (await sums(1))[:2] == ['P 5g', 'C 10g'], [await sums(0), await sums(1)])
        await T("() => { const S = window.__tapnaplo.S; S.log.splice(S.log.findIndex((e) => e.id === 'e2'), 1); window.__tapnaplo.save(); window.__tapnaplo.render(); }")
        check('a deleted entry leaves the meal and its line disappears when the meal is empty', await sums(1) is None and (await sums(0))[0] == 'P 10g')

        # ---- the real edit sheet changes the line too ----
        await page.click('[data-act=edit-entry]'); await page.wait_for_selector('.sheet')
        await page.fill('#amt', '300'); await page.click('.sheet-actions .btn.primary, .sheet-actions button.primary'); await page.wait_for_timeout(500)
        check('saving the edit sheet updates the line', (await sums(0))[:2] == ['P 30g', 'C 60g'], await sums(0))

        # ---- another day ----
        await page.click('[data-act=day][data-n="-1"]'); await page.wait_for_timeout(300)
        check('another day shows no totals lines (nothing leaks over)', await T("document.querySelectorAll('.meal-sum').length") == 0)
        await page.click('[data-act=day][data-n="1"]'); await page.wait_for_timeout(300)
        check('and back on the first day the line is there again', await T("document.querySelectorAll('.meal-sum').length") == 1)

        # ---- worst case at 390 px: every value a lower value and an estimate, 3 digits ----
        bigfoods = [own('u:t5', 'Big estimated', BIG, est=['protein', 'carbohydrate', 'fat', 'fibres', 'salt'], q='l'), own('u:t6', 'Nothing', {'kcal': 10})]
        await seed(bigfoods, [('e1', 'u:t5', 100, 'm1'), ('e2', 'u:t6', 100, 'm1')])
        line = await sums(0)
        check('worst case text', line == ['P ≥~123g', 'C ≥~345g', 'F ≥~67.8g', 'Fib ≥~12g', 'Salt ≥~12.3g'], line)
        geo = await T("""() => { const s = document.querySelector('.meal-sum'); const r = s.getBoundingClientRect(); const items = [...s.querySelectorAll('.ms')].map((e) => e.getBoundingClientRect());
          return { page: document.documentElement.scrollWidth <= window.innerWidth, inside: items.every((b) => b.left >= 0 && b.right <= window.innerWidth), lines: new Set(items.map((b) => Math.round(b.top))).size, h: Math.round(r.height) }; }""")
        check('no sideways scroll, every item inside the screen', geo['page'] and geo['inside'], geo)
        check('the line wraps to at most two rows', geo['lines'] <= 2, geo)
        if SHOTS:
            await page.screenshot(path=os.path.join(SHOTS, 'meal_sums_worst.png'))

        # ---- contrast in light and dark ----
        await seed(foods, [('e1', 'u:t1', 150, 'm1'), ('e2', 'u:t2', 100, 'm1')])
        for theme in ('light', 'dark'):
            await T("(t) => { document.documentElement.dataset.theme = t; }", theme)
            bad = await T(CONTRAST_JS, '.meal-sum')
            check(f'text contrast of the totals line is at least 4.5:1 ({theme})', bad == [], bad)
            if SHOTS:
                await page.screenshot(path=os.path.join(SHOTS, f'meal_sums_{theme}.png'))
        await T("() => { document.documentElement.dataset.theme = 'light'; }")

        # ---- version ----
        await page.click('[data-tab=data]'); await page.wait_for_timeout(300)
        ver = re.search(r'(\d+) · \d+ \w+ 20\d\d', await T("document.body.innerText"))
        check('the Data tab shows version 19 or newer', bool(ver) and int(ver.group(1)) >= 19, ver and ver.group(0))
        sw = open(pathlib.Path(__file__).resolve().parent.parent / 'sw.js', encoding='utf-8').read()
        check('the service worker cache has the number of the version', bool(ver) and f"const CACHE = 'nutrilog-v{ver.group(1)}'" in sw)

        check('no page errors', errs == [], errs[:5])
        await browser.close()
        print('\nALL PASS' if not problems else f'\n{len(problems)} FAILED: {problems}')
        sys.exit(1 if problems else 0)


asyncio.run(main())
