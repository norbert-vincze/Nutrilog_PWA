"""Checks the 18 points of the UX / accessibility audit. Run with the web server on port 8765 (see CLAUDE.md)."""
import asyncio
from playwright.async_api import async_playwright
URL = 'http://127.0.0.1:8765/index.html'

CONTRAST_JS = """
() => {
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
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const seen = new Set();
  while (walker.nextNode()) {
    const n = walker.currentNode; if (!n.textContent.trim()) continue;
    const el = n.parentElement; if (!el || seen.has(el)) continue; seen.add(el);
    const r = el.getBoundingClientRect(); if (!r.width || !r.height) continue;
    const cs = getComputedStyle(el); if (cs.visibility === 'hidden' || cs.display === 'none') continue;
    const fg = parse(cs.color), bg = bgOf(el);
    const a = fg[3]; const f = [fg[0] * a + bg[0] * (1 - a), fg[1] * a + bg[1] * (1 - a), fg[2] * a + bg[2] * (1 - a)];
    const L1 = lum(f), L2 = lum(bg), ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    const size = parseFloat(cs.fontSize), bold = parseInt(cs.fontWeight) >= 700;
    const need = (size >= 24 || (size >= 18.66 && bold)) ? 3 : 4.5;
    if (ratio < need) out.push(el.tagName.toLowerCase() + '.' + (el.className || '') + ' "' + n.textContent.trim().slice(0, 28) + '" ' + ratio.toFixed(2));
  }
  return out;
}
"""

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

        # ---- 1, 2, 7: amount shows a real value; button says what will be logged; toast says what was logged
        await page.click('.act.primary'); await page.fill('#q', 'hard-boiled egg'); await page.tap('[data-pick] >> nth=0'); await page.wait_for_selector('#amt')
        v = await page.input_value('#amt'); btn = (await page.inner_text('#ok')).strip()
        check('1 amount field holds a real value', v == '100', v)
        check('1 button says what it will add', btn == 'Add 100 g', btn)
        await page.fill('#amt', ''); await page.tap('#ok')
        check('1 empty amount is refused with a message', await page.is_visible('#amterr') and await T('__tapnaplo.S.log.length') == 0)
        await page.fill('#amt', '80,5'); await page.select_option('#meal', 'm3'); await page.tap('#ok'); await page.wait_for_timeout(200)
        toast = await page.inner_text('#toast')
        check('7 toast names amount and meal', 'Egg, hard-boiled' in toast and '80.5 g' in toast and 'Meal 3' in toast, toast)
        await page.tap('.entry >> nth=0'); await page.wait_for_selector('#amt')
        check('2 edit entry shows the stored amount', await page.input_value('#amt') == '80.5', await page.input_value('#amt'))
        check('2 edit button says Save 80.5 g', (await page.inner_text('#ok')).strip() == 'Save 80.5 g')
        await page.keyboard.press('Escape')

        # ---- 8: default meal = meal of the latest entry that day
        await page.click('.act.primary'); await page.fill('#q', 'bread'); await page.tap('[data-pick] >> nth=0'); await page.wait_for_selector('#amt')
        check('8 default meal is the last used one', await page.input_value('#meal') == 'm3', await page.input_value('#meal'))
        await page.keyboard.press('Escape'); await page.keyboard.press('Escape')
        await page.click('[data-act=day][data-n="-1"]')
        await page.click('.act.primary'); await page.fill('#q', 'bread'); await page.tap('[data-pick] >> nth=0'); await page.wait_for_selector('#amt')
        check('8 empty day starts with Meal 1', await page.input_value('#meal') == 'm1', await page.input_value('#meal'))
        await page.keyboard.press('Escape'); await page.keyboard.press('Escape')
        await page.click('[data-act=today]') if await page.locator('[data-act=today]').count() else None

        # ---- 9: Hungary checkbox sits with the Open Food Facts search, below the local results
        await page.click('.act.primary')
        check('9 no Hungary box while the search is empty', await page.locator('#huonly').count() == 0)
        await page.fill('#q', 'egg')
        order = await T("(()=>{const r=document.querySelector('#res');const h=[...r.querySelectorAll('h4')].map(x=>x.textContent);const box=r.querySelector('.offbox #huonly');return {h, inBox: !!box, label: box? box.parentElement.textContent.trim():''}})()")
        check('9 box is inside the Open Food Facts block, after CIQUAL', order['inBox'] and order['h'].index('CIQUAL (generic foods)') < len(order['h']) - 1, order)
        await page.keyboard.press('Escape')

        # ---- 10, 11: wording
        await page.wait_for_timeout(100)
        tabs = await T("[...document.querySelectorAll('#tabbar .tab span')].map(s=>s.textContent)")
        acts = await T("[...document.querySelectorAll('.act')].map(a=>a.textContent.trim())")
        check('11 tabs', tabs == ['Diary', 'Nutrients', 'My foods', 'Data'], tabs)
        check('11 actions', acts == ['Log food', 'Scan', 'Create food'], acts)
        body = await T('document.body.innerText')
        check('10 Diary says Carbohydrate, never Carbs', 'Carbohydrate' in body and 'Carbs' not in body)
        await page.click('[data-tab=nutr]'); await page.wait_for_selector('.nrow')
        check('10 Nutrients says Carbohydrate', 'Carbohydrate' in await T('document.body.innerText') and 'Carbs' not in await T('document.body.innerText'))

        # ---- 6: touch targets
        await page.click('[data-tab=log]')
        sizes = await T("[...document.querySelectorAll('.icon-btn')].map(e=>{const r=e.getBoundingClientRect();return [Math.round(r.width),Math.round(r.height)]})")
        check('6 every icon button is at least 44 x 44', all(w >= 44 and h >= 44 for w, h in sizes), sizes[:4])

        # ---- 15: empty Nutrients state has a way back
        await page.click('[data-act=day][data-n="-1"]'); await page.click('[data-tab=nutr]')
        check('15 empty Nutrients offers Go to Diary', await page.locator('button:has-text("Go to Diary")').count() == 1)
        await page.click('button:has-text("Go to Diary")')
        check('15 button leads to the Diary', await T('__tapnaplo.S.tab') == 'log')
        await page.click('[data-act=today]')

        # ---- 3, 14: Data tab
        await page.click('[data-tab=data]'); await page.wait_for_timeout(300)
        st = await page.inner_text('#persist-state')
        check('3 storage status resolves on its own', 'Checking' not in st and ('Persistent' in st or 'Not persistent' in st or 'cannot tell' in st), st)
        dtxt = await T('document.body.innerText')
        check('14 no raw "Columns ending in" jargon', 'Columns ending in' not in dtxt and 'max-value column' in dtxt)

        # ---- 16: tab survives a reload
        await page.click('[data-tab=foods]'); await page.reload(); await page.wait_for_selector('#tabbar .tab')
        check('16 reload stays on My foods', await T('__tapnaplo.S.tab') == 'foods' and 'My foods' in await page.inner_text('.title'))

        # ---- 4, 12, 13, 18: Create food form
        await page.click('[data-act=new-food]'); await page.wait_for_selector('#fname')
        vis = []
        for el in await page.query_selector_all('#nuts input[data-k]'):
            if await el.is_visible(): vis.append(await el.get_attribute('data-k'))
        check('18 only the essentials are visible first', vis == ['kcal', 'protein', 'carbohydrate', 'sugars', 'fat', 'fa_saturated', 'fibres', 'salt'], vis)
        check('18 More values exists and is closed', await T("(()=>{const d=document.querySelector('details.more');return !!d && !d.open})()"))
        check('12 unit field hidden for 100 g', not await page.is_visible('#funit'))
        await page.check('input[name=basis][value=u]')
        check('12 unit field appears for 1 unit', await page.is_visible('#funit'))
        await page.check('input[name=basis][value=g]')
        nova = await T("(()=>{const d=[...document.querySelectorAll('details.fold')].find(x=>/NOVA/.test(x.textContent));return d? d.textContent:''})()")
        check('13 NOVA explained', 'ultra-processed' in nova and 'Not set' in nova and 'unprocessed' in nova)
        await page.tap('#fok'); await page.wait_for_timeout(200)
        err = await T("(()=>{const e=document.querySelector('.field-err');const n=document.querySelector('#fname');return {txt:e?e.textContent:'', prev: e? e.previousElementSibling===n.closest('label'):false, focus: document.activeElement.id}})()")
        check('4 name error sits under the Name field and focus is there', err['txt'] == 'Give the food a name.' and err['prev'] and err['focus'] == 'fname', err)
        await page.fill('#fname', 'Test bar'); await page.click('details.more > summary'); await page.fill('#n_magnesium', 'abc'); await page.tap('#fok'); await page.wait_for_timeout(200)
        err2 = await T("(()=>{const e=document.querySelector('.field-err');return {txt:e?e.textContent:'', focus: document.activeElement.id}})()")
        check('4 number error appears at the faulty field', 'Magnesium' in err2['txt'] and err2['focus'] == 'n_magnesium', err2)
        await page.fill('#n_magnesium', '50'); await page.fill('#n_kcal', '200'); await page.tap('#fok'); await page.wait_for_timeout(300)

        # ---- 17: deleting a food needs no native dialog, and Undo works
        await page.wait_for_selector('.item')
        await page.tap('.item >> nth=0'); await page.wait_for_selector('#fdel')
        await page.tap('#fdel'); await page.wait_for_timeout(300)
        gone = await T('Object.values(__tapnaplo.S.foods).length') == 0
        check('17 food deleted without a native dialog', gone and not dialogs, dialogs)
        check('17 toast offers Undo', await page.locator('#toast button').count() == 1)
        await page.tap('#toast button'); await page.wait_for_timeout(200)
        check('17 Undo brings the food back', await T('Object.values(__tapnaplo.S.foods).length') == 1)

        # ---- 17b: save-as-portion and import use in-app dialogs
        await page.click('[data-tab=log]'); await page.click('.act.primary'); await page.fill('#q', 'bread'); await page.tap('[data-pick] >> nth=0'); await page.wait_for_selector('#saveportion')
        await page.tap('#saveportion'); await page.wait_for_selector('#ask-v'); await page.fill('#ask-v', '1 slice'); await page.tap('[data-ok]'); await page.wait_for_timeout(300)
        check('17 save-as-portion uses an in-app dialog', not dialogs and await T("Object.values(__tapnaplo.S.log).length>=0") and await page.locator('#chips button:has-text("1 slice")').count() == 1)
        await page.keyboard.press('Escape'); await page.keyboard.press('Escape')

        # ---- 5: contrast in light and dark, every tab
        for scheme in ('light', 'dark'):
            c2 = await b.new_context(viewport={'width': 390, 'height': 844}, locale='en-GB', color_scheme=scheme, reduced_motion='reduce')
            pg = await c2.new_page(); await pg.goto(URL); await pg.wait_for_selector('.hero')
            await pg.click('.act.primary'); await pg.fill('#q', 'bread'); await pg.click('[data-pick] >> nth=0'); await pg.wait_for_selector('#amt'); await pg.click('#ok'); await pg.wait_for_timeout(300)
            allbad = []
            for tab in ('log', 'nutr', 'foods', 'data'):
                await pg.click(f'[data-tab={tab}]'); await pg.wait_for_timeout(200)
                allbad += [tab + ': ' + x for x in await pg.evaluate(CONTRAST_JS)]
            await pg.click('[data-tab=log]'); await pg.click('.act.primary'); await pg.fill('#q', 'egg'); await pg.wait_for_timeout(200)
            allbad += ['picker: ' + x for x in await pg.evaluate(CONTRAST_JS)]
            await pg.keyboard.press('Escape'); await pg.click('[data-act=new-food]'); await pg.wait_for_selector('#fname'); await pg.wait_for_timeout(200)
            allbad += ['editor: ' + x for x in await pg.evaluate(CONTRAST_JS)]
            await pg.screenshot(path=f'a_editor_{scheme}.png')
            check(f'5 text contrast >= 4.5:1 ({scheme})', not allbad, allbad[:8])
            if scheme == 'light':   # sanity check: the old grey must be caught by this test
                await pg.add_style_tag(content=':root{--muted:#6f7780 !important}')
                await pg.wait_for_timeout(100)
                old = await pg.evaluate(CONTRAST_JS)
                check('5 (test sensitivity) old grey #6f7780 is detected', len(old) > 0, len(old))
            await c2.close()

        print('dialogs:', dialogs, '| page errors:', errs)
        print('PROBLEMS:', problems if problems else 'none')
        await b.close()

asyncio.run(main())
