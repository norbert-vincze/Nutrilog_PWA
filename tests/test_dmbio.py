"""dmBio products (dm.hu) as built-in packaged foods with estimated values. Run with the web server on port 8765 (see CLAUDE.md)."""
import asyncio, csv, io, json
from playwright.async_api import async_playwright
URL = 'http://127.0.0.1:8765/index.html'

OLIVE = 'dm:1459848'    # Bio olívaolaj, extra szűz, 750 ml; barcode 4066447918687; confidence high; 100 ml = 92 g
OLIVE_CODE = '4066447918687'
SOUP = 'dm:1490261'     # Bio zöldségleves ételízesítő por; values for the dry powder; 100 ml prepared = 2 g, 0.5 l prepared = 10 g
COFFEE = 'dm:1545670'   # Bio szemes kávé: no nutrition values and no estimate (confidence none)
FORT = 'dm:1588440'     # Bio gabonapép csecsemőknek: may be fortified
CRUNCHY_CODE = '4067796000306'   # Bio tejcsokoládés crunchy, 500 g

CONTRAST_JS = """
(which) => {
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
  const root = which === 'sheet' ? [...document.querySelectorAll('.sheet-b')].pop() : document.querySelector(which);
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
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

# the row of the Nutrients tab with this label: value text, detail lines, name of the group it sits in
ROW_JS = """
(label) => {
  const d = [...document.querySelectorAll('details.nrow')].find((x) => x.querySelector('summary span').textContent.trim() === label);
  if (!d) return null;
  const g = d.closest('section.group, details.group');
  return { val: d.querySelector('.nval').textContent.trim(), detail: [...d.querySelectorAll('.ndetail')].map((x) => x.textContent.trim()), group: (g.querySelector('h3, summary') || {}).textContent, pill: d.querySelector('.pill').textContent.trim() };
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
        dialogs, errs, off_calls = [], [], []
        page.on('dialog', lambda d: (dialogs.append(d.message), asyncio.ensure_future(d.dismiss())))
        page.on('pageerror', lambda e: errs.append(str(e)))

        async def off_route(r):
            off_calls.append(r.request.url)
            await r.fulfill(status=200, headers={'access-control-allow-origin': '*', 'content-type': 'application/json'}, body='{"status":0,"products":[]}')
        await page.route('**/*openfoodfacts.org/**', off_route)
        T = page.evaluate
        await page.goto(URL); await page.wait_for_selector('.hero')

        # ---- the data
        check('527 dmBio products are loaded', await T('__tapnaplo.DMBIO.length') == 527, await T('__tapnaplo.DMBIO.length'))
        check('every product has one value per app nutrient (64) and an id with the dm: prefix', await T("__tapnaplo.DMBIO.every(f=>f._cells.length===__tapnaplo.KEYS.length && f.id.startsWith('dm:') && f.src==='dmbio')"))
        check('527 different barcodes', await T('new Set(__tapnaplo.DMBIO.map(f=>f.barcode)).size') == 527)
        check('ids do not clash with ids of your own foods, CIQUAL or USDA', await T("__tapnaplo.DMBIO.every(f=>!f.id.startsWith('u:') && !f.id.startsWith('c:') && !f.id.startsWith('usda:') && !f.id.startsWith('o:'))"))
        counts = await T("(()=>{const c={};for(const f of __tapnaplo.DMBIO) c[f.q]=(c[f.q]||0)+1;return c})()")
        check('confidence counts match the estimate file (high 165, medium 210, low 97, very low 24, none 31)', counts == {'h': 165, 'm': 210, 'l': 97, 'v': 24, 'n': 31}, counts)
        tally = await T("(()=>{let est=0,lab=0;for(const f of __tapnaplo.DMBIO) f._cells.forEach((x,i)=>{if(x!==null){if(f._lab.has(i)) lab++; else est++;}});return {est,lab}})()")
        check('18293 estimated values and 5012 label values', tally == {'est': 18293, 'lab': 5012}, tally)
        check('19 products are marked as possibly fortified', await T('__tapnaplo.DMBIO.filter(f=>f.fortified).length') == 19)
        olive = await T("(()=>{const t=__tapnaplo,f=t.getFood('dm:1459848'),v=t.vecOf(f),I=t.IDX;return {name:f.name,q:f.q,kcal:v.lo[I.kcal],kcalEst:t.isEst(f,I.kcal,v),protEst:t.isEst(f,I.protein,v),fatEst:t.isEst(f,I.fat,v),eEst:t.isEst(f,I.vitamin_e,v),e:v.lo[I.vitamin_e],water:v.lo[I.water],waterEst:t.isEst(f,I.water,v)}})()")
        check('olive oil: label energy 896 kcal, not an estimate', olive['kcal'] == 896 and olive['kcalEst'] is False, olive)
        check('olive oil: protein and fat are label values, vitamin E (22.3 mg) is an estimate', not olive['protEst'] and not olive['fatEst'] and olive['eEst'] and abs(olive['e'] - 22.3) < 1e-9, olive)
        check('olive oil: water 0 g is an estimate (real zero, not missing)', olive['water'] == 0 and olive['waterEst'] is True, olive)
        coffee = await T("(()=>{const t=__tapnaplo,f=t.getFood('dm:1545670'),v=t.vecOf(f);let known=0;for(let i=0;i<t.KEYS.length;i++) if(!Number.isNaN(v.lo[i])) known++;return {q:f.q,known}})()")
        check('coffee beans have no values at all (missing stays missing, not 0)', coffee == {'q': 'n', 'known': 0}, coffee)
        check('foods that are not dmBio never count as estimated', await T("(()=>{const t=__tapnaplo,f=t.getFood('usda:173424'),v=t.vecOf(f);return t.trackedEst(f)===0 && !t.isEst(f,t.IDX.protein,v)})()"))

        # ---- search (code)
        top = await T("(q)=>__tapnaplo.searchDm(q,5).map(f=>f.id)", 'olívaolaj')
        check('"olívaolaj" finds the olive oil in the top 2', OLIVE in top[:2], top)
        top = await T("(q)=>__tapnaplo.searchDm(q,5).map(f=>f.id)", 'olivaolaj')
        check('search ignores accents ("olivaolaj")', OLIVE in top[:2], top)
        top = await T("(q)=>__tapnaplo.searchDm(q,5).map(f=>f.id)", 'olive oil')
        check('English "olive oil" finds the olive oil in the top 3', OLIVE in top[:3], top)
        names = await T("(q)=>__tapnaplo.searchDm(q,40).map(f=>f.name.toLowerCase())", 'egg')
        check('"egg" does not match "meggy" (short words match at a word start)', not any('meggy' in n for n in names), names[:3])
        names = await T("(q)=>__tapnaplo.searchDm(q,10).map(f=>f.name.toLowerCase())", 'maple syrup')
        check('"maple syrup" finds the Hungarian juhar syrup', any('juhar' in n for n in names), names[:3])
        names = await T("(q)=>__tapnaplo.searchDm(q,10).map(f=>f.name.toLowerCase())", 'oat drink')
        check('"oat drink" finds oat drinks', any('zab' in n and 'ital' in n for n in names), names[:3])
        hit = await T("(q)=>__tapnaplo.searchDm(q,5).map(f=>f.id)", OLIVE_CODE)
        check('an exact barcode finds exactly one product', hit == [OLIVE], hit)
        check('the same search without a barcode-like text finds nothing silly', await T("__tapnaplo.searchDm('zzzzqq',5).length") == 0)

        # ---- search sheet: order and "Show more"
        await page.click('.act.primary'); await page.fill('#q', 'olívaolaj'); await page.wait_for_timeout(250)
        heads = await T("[...document.querySelectorAll('#res h4')].map(h=>h.textContent)")
        check('sheet order: dmBio, CIQUAL, USDA, Open Food Facts', heads[:1] == ['dmBio (dm.hu products)'] and heads.index('CIQUAL (generic foods)') == 1 and heads.index('USDA (generic foods, US)') == 2 and heads[-1] == 'Open Food Facts (packaged products)', heads)
        row = await page.inner_text(f'[data-pick="{OLIVE}"]')
        check('a dmBio row shows its tag, energy, data coverage and the confidence', 'dmbio' in row.lower() and '896 kcal' in row and 'data ' in row and 'micronutrient estimate: high' in row, row.replace('\n', ' | '))
        check('dmBio rows carry the dmBio tag', await T("[...document.querySelectorAll('#res [data-pick^=\"dm:\"]')].every(b=>b.querySelector('.tag').textContent==='dmBio')"))
        await page.fill('#q', 'bio'); await page.wait_for_timeout(250)
        n1 = await T("[...document.querySelectorAll('#res [data-pick]')].filter(b=>b.dataset.pick.startsWith('dm:')).length")
        check('only 10 dmBio rows at first', n1 == 10, n1)
        await page.tap('[data-a=more-dm]'); await page.wait_for_timeout(150)
        n2 = await T("[...document.querySelectorAll('#res [data-pick]')].filter(b=>b.dataset.pick.startsWith('dm:')).length")
        check('"Show more dmBio results" adds 30 rows', n2 == 40, n2)
        await page.fill('#q', 'bio '); await page.fill('#q', 'bio'); await page.wait_for_timeout(150)
        check('a new search starts with 10 rows again', await T("[...document.querySelectorAll('#res [data-pick]')].filter(b=>b.dataset.pick.startsWith('dm:')).length") == 10)

        # ---- barcode: a dmBio product is found without the internet (Open Food Facts is not asked)
        await page.fill('#q', ''); await page.wait_for_timeout(100)
        n0 = len(off_calls)
        await page.click('[data-a=scan]'); await page.wait_for_selector('#scan-manual')
        await page.fill('#scan-manual', OLIVE_CODE); await page.click('#scan-go')
        await page.wait_for_selector('#amt', timeout=4000)
        check('typing the barcode opens the dmBio product', 'olívaolaj' in (await page.inner_text('.sheet-b >> nth=-1')).lower())
        check('and no request went to Open Food Facts', len(off_calls) == n0, off_calls[n0:])

        # ---- amount sheet of a dmBio product
        check('amount starts at 100 g, button says what it logs', await page.input_value('#amt') == '100' and (await page.inner_text('#ok')).strip() == 'Add 100 g')
        check('dmBio foods cannot be edited (no "Edit food")', await page.locator('#editfood').count() == 0)
        summ = await page.inner_text('details.fold summary')
        check('the fold names the confidence', summ.strip() == 'Estimated values · confidence high', summ)
        await page.tap('details.fold summary'); await page.wait_for_timeout(100)
        fold = await page.inner_text('details.fold')
        check('the fold lists the label values and says the rest is estimated', 'From the dm.hu label:' in fold and 'energy' in fold.lower() and 'estimate' in fold, fold[:200].replace('\n', ' | '))
        href = await page.get_attribute('details.fold a', 'href')
        check('the fold links to the dm.hu product page', href.startswith('https://www.dm.hu/p/d/1459848'), href)
        check('the fold shows the Hungarian note of the estimate file', 'Note from the estimate file (Hungarian)' in fold)
        cov = await page.inner_text('.sheet-b >> nth=-1')
        check('the coverage line says how many values are estimates', 'of them estimated, not from a label' in cov, [l for l in cov.split('\n') if 'Data for' in l])
        check('water is not one of the tracked nutrients (still "of the 42 tracked nutrients")', 'of the 42 tracked nutrients' in cov, [l for l in cov.split('\n') if 'Data for' in l])
        chips = await T("[...document.querySelectorAll('#chips .chip-btn')].map(b=>b.textContent)")
        check('millilitre buttons are offered for the oil', '100 ml' in chips and '1 tbsp (15 ml)' in chips and '1 tsp (5 ml)' in chips, chips)
        await page.tap('#chips .chip-btn:text-is("1 tbsp (15 ml)")'); await page.wait_for_timeout(100)
        check('"1 tbsp (15 ml)" sets 13.8 g', await page.input_value('#amt') == '13.8', await page.input_value('#amt'))
        await page.tap('#chips .chip-btn:text-is("100 ml")'); await page.wait_for_timeout(100)
        check('"100 ml" sets 92 g (the weight of 100 ml, the values stay per 100 g)', await page.input_value('#amt') == '92', await page.input_value('#amt'))
        check('the 390 px sheet does not scroll sideways', await T('document.documentElement.scrollWidth <= window.innerWidth'))
        await page.fill('#amt', '100'); await page.tap('#ok'); await page.wait_for_timeout(250)

        # a product with a dry-powder basis
        await page.click('.act.primary'); await page.fill('#q', 'zöldségleves ételízesítő por'); await page.wait_for_timeout(150)
        await page.tap(f'[data-pick="{SOUP}"]'); await page.wait_for_selector('#amt')
        chips = await T("[...document.querySelectorAll('#chips .chip-btn')].map(b=>b.textContent)")
        check('soup powder offers the prepared amounts', '100 ml prepared' in chips and '0.5 l prepared' in chips, chips)
        await page.tap('#chips .chip-btn:text-is("0.5 l prepared")'); await page.wait_for_timeout(100)
        check('"0.5 l prepared" sets 10 g of powder', await page.input_value('#amt') == '10', await page.input_value('#amt'))
        await page.tap('#chips .chip-btn:text-is("100 ml prepared")'); await page.wait_for_timeout(100)
        check('"100 ml prepared" sets 2 g of powder', await page.input_value('#amt') == '2', await page.input_value('#amt'))
        await page.tap('details.fold summary'); await page.wait_for_timeout(100)
        check('the fold says the values are for the dry product', 'dry product' in await page.inner_text('details.fold'))
        await page.keyboard.press('Escape'); await page.keyboard.press('Escape'); await page.wait_for_timeout(150)

        # a product that may be fortified, and one without any estimate
        await page.click('.act.primary'); await page.fill('#q', 'gabonapép csecsemőknek'); await page.wait_for_timeout(150)
        await page.tap(f'[data-pick="{FORT}"]'); await page.wait_for_selector('#amt')
        await page.tap('details.fold summary'); await page.wait_for_timeout(100)
        fold = await page.inner_text('details.fold')
        check('a possibly fortified product warns that vitamin and mineral estimates can be too low', 'may be fortified' in fold and 'too low' in fold, fold[:260].replace('\n', ' | '))
        await page.keyboard.press('Escape'); await page.keyboard.press('Escape'); await page.wait_for_timeout(150)
        await page.click('.act.primary'); await page.fill('#q', 'szemes kávé caffé crema'); await page.wait_for_timeout(150)
        await page.tap(f'[data-pick="{COFFEE}"]'); await page.wait_for_selector('#amt')
        summ = await page.inner_text('details.fold summary')
        fold_open = await page.evaluate("(()=>{const d=document.querySelector('details.fold');d.open=true;return d.innerText})()")
        check('a product without an estimate says so', summ.strip() == 'No micronutrient estimate' and 'No other nutrient is estimated' in fold_open and 'no nutrition table' in fold_open, fold_open[:200].replace('\n', ' | '))
        await page.fill('#amt', '10'); await page.tap('#ok'); await page.wait_for_timeout(250)

        # a second product, found by its barcode
        await page.click('.act.primary'); await page.click('[data-a=scan]'); await page.wait_for_selector('#scan-manual')
        await page.fill('#scan-manual', CRUNCHY_CODE); await page.click('#scan-go'); await page.wait_for_selector('#amt', timeout=4000)
        await page.fill('#amt', '50'); await page.tap('#ok'); await page.wait_for_timeout(250)

        # ---- diary
        rows = await page.inner_text('#view')
        check('diary rows carry the dmBio tag', rows.lower().count('dmbio') >= 3, rows.lower().count('dmbio'))
        check('the diary says that one entry has no energy data', 'Lower estimate · 1 without energy data' in rows)
        total = await T("__tapnaplo.totalsFor(__tapnaplo.S.log).lo[0]")
        crunchy_kcal = await T("(()=>{const f=__tapnaplo.DMBIO.find(f=>f.barcode==='4067796000306');return __tapnaplo.vecOf(f).lo[0]})()")
        check('energy = olive oil 100 g + crunchy 50 g (coffee has none)', abs(total - (896 + crunchy_kcal * 0.5)) < 1e-6, (total, crunchy_kcal))
        check('the entries are saved (3 dmBio entries + the soup was not added)', await T("__tapnaplo.S.log.filter(e=>e.f.startsWith('dm:')).length") == 3)

        # ---- nutrients tab
        await page.click('[data-tab=nutr]'); await page.wait_for_selector('details.nrow')
        txt = await page.inner_text('#view')
        check('a legend explains the ~ sign', 'A ~ in front of a value means' in txt)
        w = await T(ROW_JS, 'Water')
        check('Water is listed under "Energy & macronutrients" with ~', w and w['group'] == 'Energy & macronutrients' and '~' in w['val'], w)
        check('its detail names the estimated items with their confidence', w and any('Estimate, not a label value' in d and 'olívaolaj' in d.lower() and '(high)' in d for d in w['detail']), w and w['detail'])
        e = await T(ROW_JS, 'Energy')
        check('energy comes from the labels: no ~ (and ≥ because the coffee has no data)', e and '~' not in e['val'] and e['val'].startswith('≥') and not any('Estimate' in d for d in e['detail']), e)
        pr = await T(ROW_JS, 'Protein')
        check('protein is a label value: no ~', pr and '~' not in pr['val'], pr)
        ve = await T(ROW_JS, 'Vitamin E')
        check('vitamin E is estimated: ~', ve and '~' in ve['val'] and ve['group'] == 'Vitamins', ve)
        # the same number as the diary computes: vitamin E = 22.3 mg x 1 (olive 100 g) + crunchy part
        vit_e = await T("(()=>{const t=__tapnaplo;return t.totalsFor(t.S.log).lo[t.IDX.vitamin_e]})()")
        check('vitamin E total is at least the 22.3 mg of the olive oil', vit_e >= 22.3 - 1e-9, vit_e)
        await page.screenshot(path='d_nutr.png')

        # ---- reload keeps everything
        await page.reload(); await page.wait_for_selector('[data-tab=log]'); await page.wait_for_timeout(300)
        await page.click('[data-tab=log]'); await page.wait_for_selector('.hero')
        check('dmBio entries survive a reload', (await page.inner_text('#view')).lower().count('dmbio') >= 3)

        # ---- CSV
        await page.click('[data-tab=data]')
        body = await page.inner_text('#view')
        check('Data tab names the dmBio source and counts the products', 'dmBio products of dm Hungary' in body and '527 dmBio products' in body)
        check('Data tab explains the estimate columns of the CSV', '__est' in body, [l for l in body.split('\n') if 'CSV' in l][:2])
        async with page.expect_download() as d:
            await page.click('[data-act=export-entries]')
        dl = await d.value; await dl.save_as('entries_dmbio.csv')
        rows = list(csv.DictReader(io.StringIO(open('entries_dmbio.csv', encoding='utf-8-sig').read())))
        by = {r['food_id']: r for r in rows}
        o = by[OLIVE]
        check('CSV: source dmbio, brand dmBio, confidence high, amount 100', o['source'] == 'dmbio' and o['brand'] == 'dmBio' and o['estimate_confidence'] == 'high' and o['amount'] == '100', {k: o[k] for k in ('source', 'brand', 'estimate_confidence', 'amount')})
        check('CSV: label energy is not marked as estimated', o['energy_estimated'] == '0' and 'kcal_kcal__est' not in o, (o['energy_estimated'], 'kcal_kcal__est' in o))
        check('CSV: vitamin E and water are marked as estimates; there is no __est column for label-only nutrients (protein)', o['vitamin_e_mg__est'] == '1' and o['water_g__est'] == '1' and 'protein_g__est' not in o, (o['vitamin_e_mg__est'], o['water_g__est'], 'protein_g__est' in o))
        check('CSV: vitamin E value 22.3 for 100 g', abs(float(o['vitamin_e_mg']) - 22.3) < 1e-6, o['vitamin_e_mg'])
        c = by[COFFEE]
        check('CSV: coffee has empty cells (no data), not zeros, and confidence none', c['kcal_kcal'] == '' and c['protein_g'] == '' and c['estimate_confidence'] == 'none', {k: c[k] for k in ('kcal_kcal', 'protein_g', 'estimate_confidence')})
        async with page.expect_download() as d:
            await page.click('[data-act=export-days]')
        dl = await d.value; await dl.save_as('days_dmbio.csv')
        days = list(csv.DictReader(io.StringIO(open('days_dmbio.csv', encoding='utf-8-sig').read())))
        check('daily CSV: __est columns count the estimated entries (vitamin E: 2), none for label-only energy', days[0]['vitamin_e_mg__est'] == '2' and 'kcal_kcal__est' not in days[0], {k: days[0].get(k) for k in ('vitamin_e_mg__est', 'kcal_kcal__est')})

        # ---- layout and contrast, light and dark
        await page.click('[data-tab=nutr]'); await page.wait_for_selector('details.nrow')
        await T("document.querySelectorAll('#view details').forEach(d=>d.open=true)"); await page.wait_for_timeout(100)
        check('Nutrients tab fits 390 px', await T('document.documentElement.scrollWidth <= window.innerWidth'))
        light = await T(CONTRAST_JS, '#view')
        check('text contrast >= 4.5:1 on the Nutrients tab (light)', light == [], light)
        await T("document.documentElement.setAttribute('data-theme','dark')"); await page.wait_for_timeout(100)
        dark = await T(CONTRAST_JS, '#view')
        check('text contrast >= 4.5:1 on the Nutrients tab (dark)', dark == [], dark)
        await T("document.documentElement.setAttribute('data-theme','light')")
        await page.click('[data-tab=log]'); await page.click('.act.primary'); await page.fill('#q', 'olívaolaj'); await page.wait_for_timeout(200)
        await page.tap(f'[data-pick="{OLIVE}"]'); await page.wait_for_selector('#amt')
        await T("document.querySelectorAll('.sheet-b details').forEach(d=>d.open=true)"); await page.wait_for_timeout(100)
        light = await T(CONTRAST_JS, 'sheet')
        check('text contrast >= 4.5:1 in the amount sheet with the open fold (light)', light == [], light)
        await T("document.documentElement.setAttribute('data-theme','dark')"); await page.wait_for_timeout(100)
        dark = await T(CONTRAST_JS, 'sheet')
        check('text contrast >= 4.5:1 in the amount sheet with the open fold (dark)', dark == [], dark)
        await page.screenshot(path='d_sheet_dark.png')
        await T("document.documentElement.setAttribute('data-theme','light')")
        small = await T("[...document.querySelectorAll('.sheet-b details summary')].filter(s=>s.getBoundingClientRect().height<44).length")
        check('the fold summary is at least 44 px tall', small == 0, small)
        await page.keyboard.press('Escape'); await page.keyboard.press('Escape'); await page.wait_for_timeout(150)
        # long product name in the picker
        await page.click('.act.primary'); await page.fill('#q', 'ropogós kenyér magvakkal'); await page.wait_for_timeout(200)
        check('long dmBio names wrap inside the 390 px picker', await T('document.documentElement.scrollWidth <= window.innerWidth'))
        await page.keyboard.press('Escape'); await page.keyboard.press('Escape'); await page.wait_for_timeout(150)

        # ---- offline: the product table sits in a cache of its own, barcode still works
        await page.click('[data-tab=log]'); await page.wait_for_timeout(1500)
        keys = await T("caches.keys().then(async ks=>{const o={};for(const k of ks){o[k]=(await (await caches.open(k)).keys()).map(r=>new URL(r.url).pathname.split('/').pop())}return o})")
        check('dmbio.json has its own cache, apart from the app files and the other food tables', keys.get('nutrilog-dmbio-1') == ['dmbio.json'] and not any('dmbio.json' in v for k, v in keys.items() if k != 'nutrilog-dmbio-1'), keys)
        check('ciqual.json and usda.json stay together in nutrilog-data-1', sorted(keys.get('nutrilog-data-1', [])) == ['ciqual.json', 'usda.json'], keys.get('nutrilog-data-1'))
        await ctx.set_offline(True)
        n0 = len(off_calls)
        await page.reload(); await page.wait_for_selector('.hero', timeout=10000)
        check('offline reload still shows the dmBio entries', (await page.inner_text('#view')).lower().count('dmbio') >= 3)
        await page.click('.act.primary'); await page.click('[data-a=scan]'); await page.wait_for_selector('#scan-manual')
        await page.fill('#scan-manual', '4066447707267'); await page.click('#scan-go'); await page.wait_for_selector('#amt', timeout=4000)
        check('offline: a dmBio barcode still opens its product', 'ropogós kenyér' in (await page.inner_text('.sheet-b >> nth=-1')).lower())
        check('offline: Open Food Facts was not asked', len(off_calls) == n0, off_calls[n0:])
        await page.keyboard.press('Escape'); await page.keyboard.press('Escape')
        await ctx.set_offline(False)
        await ctx.close()

        # ---- the app starts without dmbio.json and says what is hidden
        ctx2 = await b.new_context(viewport={'width': 390, 'height': 844}, locale='en-GB', has_touch=True, is_mobile=True, service_workers='block', reduced_motion='reduce')
        p2 = await ctx2.new_page(); errs2 = []
        p2.on('pageerror', lambda e: errs2.append(str(e)))
        await p2.goto(URL); await p2.wait_for_selector('.hero')
        await p2.click('.act.primary'); await p2.fill('#q', 'olívaolaj'); await p2.tap(f'[data-pick="{OLIVE}"]'); await p2.wait_for_selector('#amt'); await p2.tap('#ok'); await p2.wait_for_timeout(250)
        await ctx2.route('**/dmbio.json', lambda r: r.abort())
        await p2.reload(); await p2.wait_for_selector('.hero')
        check('without dmbio.json the app still starts', await p2.locator('.hero').count() == 1)
        banner = await p2.inner_text('.banner')
        check('the diary says that 1 dmBio entry is hidden and why', '1 entry is hidden' in banner and 'dmBio food data could not be loaded' in banner, banner)
        await p2.click('.act.primary'); await p2.fill('#q', 'olive oil'); await p2.wait_for_timeout(150)
        heads2 = await p2.evaluate("[...document.querySelectorAll('#res h4')].map(h=>h.textContent)")
        check('CIQUAL and USDA search still work, no dmBio block', 'CIQUAL (generic foods)' in heads2 and 'USDA (generic foods, US)' in heads2 and not any('dmBio' in h for h in heads2), heads2)
        await p2.keyboard.press('Escape'); await p2.keyboard.press('Escape')
        await p2.click('[data-tab=data]')
        check('Data tab reports the failed dmBio load', 'The dmBio data could not be loaded' in await p2.inner_text('#view'))
        check('no page errors without dmbio.json', errs2 == [], errs2)
        await ctx2.close()

        check('no native dialogs', dialogs == [], dialogs)
        check('no page errors', errs == [], errs)
        await b.close()
        print('\nPROBLEMS:', problems if problems else 'none')
        raise SystemExit(1 if problems else 0)

asyncio.run(main())
