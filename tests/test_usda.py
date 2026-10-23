"""USDA FoodData Central as a second source of generic foods. Run with the web server on port 8765 (see CLAUDE.md)."""
import asyncio, csv, io
from playwright.async_api import async_playwright
URL = 'http://127.0.0.1:8765/index.html'


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        problems = []

        def check(name, ok, info=''):
            print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(info)) if info != '' else ''))
            if not ok: problems.append(name)

        ctx = await b.new_context(viewport={'width': 390, 'height': 844}, locale='en-GB', has_touch=True, is_mobile=True, reduced_motion='reduce', accept_downloads=True)
        page = await ctx.new_page()
        dialogs, errs = [], []
        page.on('dialog', lambda d: (dialogs.append(d.message), asyncio.ensure_future(d.dismiss())))
        page.on('pageerror', lambda e: errs.append(str(e)))
        T = page.evaluate
        await page.goto(URL); await page.wait_for_selector('.hero')

        # ---- the data
        check('8229 USDA foods are loaded', await T('__tapnaplo.USDA.length') == 8229, await T('__tapnaplo.USDA.length'))
        check('every USDA food has one value per app nutrient (64)', await T('__tapnaplo.USDA.every(f=>f._cells.length===__tapnaplo.KEYS.length)'))
        check('USDA ids do not clash with ids of your own foods', await T("__tapnaplo.USDA.every(f=>f.id.startsWith('usda:'))"))
        egg = await T("(()=>{const f=__tapnaplo.USDA.find(f=>f.name==='Egg, whole, cooked, hard-boiled');const v=__tapnaplo.vecOf(f),I=__tapnaplo.IDX;return {kcal:v.lo[I.kcal],protein:v.lo[I.protein],chol:v.lo[I.cholesterol],b12:v.lo[I.vitamin_b12],salt:v.lo[I.salt],iodine:v.lo[I.iodine],p:f.portions.map(x=>x.label)}})()")
        check('hard-boiled egg matches the USDA table (155 kcal, 12.58 g protein, 373 mg cholesterol, 1.11 ug B12)',
              egg['kcal'] == 155 and abs(egg['protein'] - 12.58) < 1e-6 and egg['chol'] == 373 and abs(egg['b12'] - 1.11) < 1e-6, egg)
        check('salt is worked out from sodium (124 mg -> 0.31 g)', abs(egg['salt'] - 0.31) < 0.005, egg['salt'])
        check('a nutrient USDA does not report stays "no data", not zero (iodine)', egg['iodine'] != egg['iodine'], egg['iodine'])
        check('household measures come with the food', '1 large' in egg['p'], egg['p'])

        # ---- search: both sources, in the search sheet
        await page.click('.act.primary'); await page.fill('#q', 'egg'); await page.wait_for_timeout(200)
        heads = await T("[...document.querySelectorAll('#res h4')].map(h=>h.textContent)")
        check('search shows CIQUAL first, then USDA, then Open Food Facts', heads[-3:] == ['CIQUAL (generic foods)', 'USDA (generic foods, US)', 'Open Food Facts (packaged products)'], heads)
        n1 = await T("document.querySelectorAll('#res [data-pick]').length")
        usda_rows = await T("[...document.querySelectorAll('#res [data-pick]')].filter(b=>b.dataset.pick.startsWith('usda:')).length")
        check('only 10 USDA rows at first', usda_rows == 10, usda_rows)
        check('rows carry the USDA tag and the FDC id', await T("[...document.querySelectorAll('#res [data-pick^=\"usda:\"]')].every(b=>b.querySelector('.tag').textContent==='USDA' && /FDC \\d+/.test(b.textContent))"))
        await page.tap('[data-a=more-usda]'); await page.wait_for_timeout(150)
        usda_rows2 = await T("[...document.querySelectorAll('#res [data-pick]')].filter(b=>b.dataset.pick.startsWith('usda:')).length")
        check('"Show more USDA results" adds rows', usda_rows2 > usda_rows, (usda_rows, usda_rows2))
        await page.fill('#q', 'egg '); await page.fill('#q', 'egg')
        check('a new search starts with 10 rows again', await T("[...document.querySelectorAll('#res [data-pick]')].filter(b=>b.dataset.pick.startsWith('usda:')).length") == 10)

        # ---- Hungarian words find USDA foods
        wants = {'kenyér': 'bread', 'csirkemell': 'chicken, breast', 'tejföl': 'sour cream', 'túró': 'cottage', 'mandulatej': 'almond milk',
                 'banán': 'banana', 'alma': 'apple', 'krumpli': 'potato', 'olívaolaj': 'oil, olive', 'lazac': 'salmon', 'spenót': 'spinach', 'rizs': 'rice'}
        bad = {}
        for hu, en in wants.items():
            names = await T("(q)=>__tapnaplo.searchUsda(q,5).map(f=>f.name.toLowerCase())", hu)
            if not any(en in n for n in names[:3]): bad[hu] = names
        check('Hungarian words find the right USDA foods (top 3)', not bad, bad)
        first = await T("__tapnaplo.searchUsda('banán',1)[0].name")
        check('plural names rank first (banán -> Bananas, not banana pepper)', first.startswith('Bananas'), first)

        # ---- log a USDA food with a household measure
        await page.fill('#q', 'hard-boiled egg'); await page.wait_for_timeout(150)
        await page.tap('[data-pick="usda:173424"]'); await page.wait_for_selector('#amt')
        check('amount starts at 100 g (not at the first household measure)', await page.input_value('#amt') == '100' and (await page.inner_text('#ok')).strip() == 'Add 100 g')
        chips = await T("[...document.querySelectorAll('#chips .chip-btn')].map(b=>b.textContent)")
        check('household measures are offered as buttons', '1 large' in chips and '1 cup, chopped' in chips, chips)
        check('USDA foods cannot be edited (no "Edit food")', await page.locator('#editfood').count() == 0)
        await page.tap('#chips .chip-btn:text-is("1 large")'); await page.wait_for_timeout(100)
        check('"1 large" sets 50 g', await page.input_value('#amt') == '50')
        await page.tap('#ok'); await page.wait_for_timeout(250)
        row = await page.inner_text('.entry')
        check('diary row says USDA', 'USDA' in row and '50 g' in row, row.replace('\n', ' | '))
        check('energy is 155 kcal x 0.5 = 77.5', abs(await T("__tapnaplo.totalsFor(__tapnaplo.S.log).lo[0]") - 77.5) < 1e-9)
        # a long household measure must not push the sheet sideways
        await page.click('.act.primary'); await page.fill('#q', 'apples, raw, with skin'); await page.tap('[data-pick^="usda:"] >> nth=0'); await page.wait_for_selector('#amt')
        check('long measure names fit the 390 px screen', await T('document.documentElement.scrollWidth <= window.innerWidth'))
        await page.keyboard.press('Escape'); await page.keyboard.press('Escape'); await page.wait_for_timeout(150)

        # ---- saved entries survive a reload and appear in the CSV
        await page.reload(); await page.wait_for_selector('.hero'); await page.wait_for_timeout(300)
        check('USDA entry survives a reload', 'USDA' in await page.inner_text('.entry'))
        await page.click('[data-tab=data]')
        body = await page.inner_text('#view')
        check('Data tab names the USDA source and counts the foods', 'FoodData Central' in body and '8229 USDA foods' in body)
        async with page.expect_download() as d:
            await page.click('[data-act=export-entries]')
        dl = await d.value; await dl.save_as('entries_usda.csv')
        rows = list(csv.DictReader(io.StringIO(open('entries_usda.csv', encoding='utf-8-sig').read())))
        check('CSV: source usda, food_id usda:173424, amount 50', rows[0]['source'] == 'usda' and rows[0]['food_id'] == 'usda:173424' and rows[0]['amount'] == '50', {k: rows[0][k] for k in ('source', 'food_id', 'amount')})
        check('CSV: iodine is empty (no data), protein is filled', rows[0]['iodine_ug'] == '' and abs(float(rows[0]['protein_g']) - 6.29) < 0.01, (rows[0]['iodine_ug'], rows[0]['protein_g']))

        # ---- offline: the food tables sit in their own cache
        await page.click('[data-tab=log]'); await page.wait_for_timeout(1500)
        keys = await T("caches.keys().then(async ks=>{const o={};for(const k of ks){o[k]=(await (await caches.open(k)).keys()).map(r=>new URL(r.url).pathname.split('/').pop())}return o})")
        check('ciqual.json and usda.json are cached together, apart from the app files', sorted(keys.get('nutrilog-data-1', [])) == ['ciqual.json', 'usda.json'] and 'usda.json' not in keys.get('nutrilog-v8', []), keys)
        await ctx.set_offline(True)
        await page.reload(); await page.wait_for_selector('.hero', timeout=10000)
        check('offline reload still shows the USDA entry', 'USDA' in await page.inner_text('.entry'))
        await ctx.set_offline(False)
        await ctx.close()

        # ---- the app starts without usda.json and says what is hidden
        ctx2 = await b.new_context(viewport={'width': 390, 'height': 844}, locale='en-GB', has_touch=True, is_mobile=True, service_workers='block', reduced_motion='reduce')
        p2 = await ctx2.new_page(); errs2 = []
        p2.on('pageerror', lambda e: errs2.append(str(e)))
        await p2.goto(URL); await p2.wait_for_selector('.hero')
        await p2.click('.act.primary'); await p2.fill('#q', 'hard-boiled egg'); await p2.tap('[data-pick="usda:173424"]'); await p2.wait_for_selector('#amt'); await p2.tap('#ok'); await p2.wait_for_timeout(250)
        await ctx2.route('**/usda.json', lambda r: r.abort())
        await p2.reload(); await p2.wait_for_selector('.hero')
        check('without usda.json the app still starts', await p2.locator('.hero').count() == 1)
        banner = await p2.inner_text('.banner')
        check('the diary says that 1 USDA entry is hidden and why', '1 entry is hidden' in banner and 'USDA food data could not be loaded' in banner, banner)
        await p2.click('.act.primary'); await p2.fill('#q', 'egg'); await p2.wait_for_timeout(150)
        heads2 = await p2.evaluate("[...document.querySelectorAll('#res h4')].map(h=>h.textContent)")
        check('CIQUAL search still works, no USDA block', 'CIQUAL (generic foods)' in heads2 and 'USDA (generic foods, US)' not in heads2, heads2)
        await p2.keyboard.press('Escape'); await p2.keyboard.press('Escape')
        await p2.click('[data-tab=data]')
        check('Data tab reports the failed USDA load', 'The USDA data could not be loaded' in await p2.inner_text('#view'))
        check('no page errors without usda.json', errs2 == [], errs2)
        await ctx2.close()

        check('no native dialogs', dialogs == [], dialogs)
        check('no page errors', errs == [], errs)
        await b.close()
        print('\nPROBLEMS:', problems if problems else 'none')
        raise SystemExit(1 if problems else 0)

asyncio.run(main())
