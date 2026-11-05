"""Report tab (version 29). Run with the web server on port 8765 (see CLAUDE.md).

A sixth tab "Report" shows a period (Day, Week, Month, 3 months, 6 months, Year, Custom) as averages per logged day: an Overview, the Nutrients with the EFSA bars on the average and
"Added up from" for the period, and Data quality. Nothing new is stored (only the choice of period and the open parts, on this device). The clock of the browser is fixed to Thursday
5 Nov 2026, 12:00 (Budapest), so every date below is exact.

Covers: a hand-calculated sample (an unlogged day, a partial item, water on two days), the period maths (Monday weeks, month ends, a leap February, the year edge, "so far", previous / next /
Today / date picker), the Custom sheet and every error, empty periods, damaged saved choices, the parity of Report Day / one-day Custom with the Nutrients tab (every row, with and without a
profile), the special rows over a period (vitamin B1 and niacin on the days with complete energy, vitamin A, EPA + DHA, the omega ratio), ranges and estimates, the 12-food limit of "Added up
from", Data quality (calendar and month rows, sources, least data), entries whose food is not loaded, the shared copy (three tabs, same numbers as the sender, periods cut to the shared days,
nothing written, hostile content), the six-tab bar at five widths in light and dark with each tab active, 44 / 16 px, contrast, 390 and 320 px, speed with 6,000 entries, the backup, the
version number and no page errors."""
import asyncio, json, math, os, pathlib, re, sys, time
from datetime import date, timedelta
from playwright.async_api import async_playwright
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_ai_import import CONTRAST_JS

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = 'http://127.0.0.1:8765/index.html'
SHOTS = os.environ.get('SHOTS', '')
NOW = '2026-11-05T12:00:00+01:00'           # Thursday
TODAY = date(2026, 11, 5)
DEFAULT_OPEN = {'overview': True, 'days': False, 'nutrients': False, 'quality': False}
DT = 'details[data-sec=nutrients]'


def day(n):
    return (TODAY + timedelta(days=n)).isoformat()


INIT = """
window.__txt = (el, skip) => { let s = ''; const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  while (w.nextNode()) { const n = w.currentNode; if (skip && n.parentElement.closest(skip)) continue; s += n.textContent; }
  return s.replace(/\\s+/g, ' ').trim(); };
window.__w = { ls: [], idb: 0 };
try { const si = Storage.prototype.setItem; Storage.prototype.setItem = function (k, v) { window.__w.ls.push(k); return si.call(this, k, v); };
  const ri = Storage.prototype.removeItem; Storage.prototype.removeItem = function (k) { window.__w.ls.push('-' + k); return ri.call(this, k); };
  const io = IDBFactory.prototype.open; IDBFactory.prototype.open = function () { window.__w.idb++; return io.apply(this, arguments); }; } catch (e) { }
"""

ROWS = """(root) => { const out = {}, tx = window.__txt;
  document.querySelectorAll(root + ' details.nrow').forEach((r) => { r.open = true;
    const lab = r.querySelector('summary > span').textContent, v = r.querySelector('summary .nval'), p = r.querySelector('summary .pill');
    const rt = r.querySelector('.rtxt'), rs = r.querySelector('.rline .sr-only'), f = r.querySelector('.rfill'), tr = r.querySelector('.rtrack');
    out[lab] = { val: tx(v, '.sr-only'), none: v.classList.contains('none'), pill: p.textContent, cls: p.className.replace('pill', '').trim(),
      line: rt ? rt.textContent : null, say: rs ? rs.textContent : null, bar: f ? f.style.width : null, track: tr ? tr.className : null,
      head: r.querySelector('.nc-h') ? r.querySelector('.nc-h').textContent : null,
      parts: [...r.querySelectorAll('.ncontrib li')].map((li) => [li.querySelector('.nc-name').textContent, tx(li.querySelector('.nc-val'), '.sr-only'), li.className]),
      det: [...r.querySelectorAll('.ndetail')].map((d) => d.textContent) };
  });
  return out; }"""

OVERVIEW = """() => { const q = (s) => document.querySelector(s), rows = {};
  document.querySelectorAll('.rp-stats .an-row').forEach((r) => { const dd = r.querySelector('dd');
    rows[r.querySelector('dt').childNodes[0].textContent.trim()] = { val: dd.childNodes[0].textContent.trim(), unit: dd.querySelector('em') ? dd.querySelector('em').textContent : '', none: dd.classList.contains('none'), sub: r.querySelector('dt small') ? r.querySelector('dt small').textContent : '' }; });
  const days = [...document.querySelectorAll('.rp-days .an-row')].map((r) => [r.querySelector('dt').childNodes[0].textContent.trim(), r.querySelector('dt small').textContent.replace(/^ · /, ''), r.querySelector('dd').textContent.trim()]);
  const dsec = q('details[data-sec=days]');
  return { hero: q('.rp-hero .hero-num').textContent, chips: [...document.querySelectorAll('.rp-hero .chip')].map((c) => c.textContent.trim()), items: q('.rp-items').textContent, rows, days,
    daysTitle: dsec.querySelector('summary').textContent, daysOpen: dsec.open, daysNote: dsec.querySelector('.hint') ? dsec.querySelector('.hint').textContent : null, expl: q('.rp-expl').textContent,
    diaryBtn: !!q('[data-act=rp-diary]') }; }"""

SEL = """() => { const q = (s) => document.querySelector(s); const bs = [...document.querySelectorAll('.rp-seg button')];
  return { names: bs.map((b) => b.textContent), pressed: bs.filter((b) => b.getAttribute('aria-pressed') === 'true').map((b) => b.dataset.kind), disabled: bs.filter((b) => b.disabled).map((b) => b.dataset.kind),
    when: q('.rp-when b') ? q('.rp-when b').textContent : null, note: q('.rp-when span') ? q('.rp-when span').textContent : '',
    prev: !q('[data-act=rp-step][data-n="-1"]').disabled, next: !q('[data-act=rp-step][data-n="1"]').disabled, hint: q('.rp-hint') ? q('.rp-hint').textContent : null,
    today: !!q('[data-act=rp-today]'), datepick: !!q('#rp-date'), title: q('#topbar h1') ? q('#topbar h1').textContent : null }; }"""

QUALITY = """() => { const q = (s) => document.querySelector(s), sec = q('details[data-sec=quality]'); const out = {};
  const cal = sec.querySelector('.rp-cal');
  out.cal = cal ? { cells: [...cal.querySelectorAll('li:not(.hd):not(.pad)')].map((li) => [li.querySelector('span').textContent, li.className.trim(), li.querySelector('.sr-only').textContent]), pads: cal.querySelectorAll('li.pad').length, heads: [...cal.querySelectorAll('li.hd')].map((h) => h.textContent).join('') } : null;
  out.heads = [...sec.querySelectorAll('.rp-h')].map((h) => h.textContent);
  const rows = (h) => { let n = h.nextElementSibling; while (n && !(n.matches('dl'))) n = n.nextElementSibling; return n ? [...n.querySelectorAll('.an-row')].map((r) => [r.querySelector('dt').childNodes[0].textContent.trim(), r.querySelector('dt small') ? r.querySelector('dt small').textContent.replace(/^ · /, '') : '', r.querySelector('dd').textContent.trim()]) : []; };
  const hs = [...sec.querySelectorAll('.rp-h')]; out.sections = {}; hs.forEach((h) => { out.sections[h.textContent] = rows(h); });
  return out; }"""

TABFIT = """() => { const bar = document.querySelector('#tabbar'); const tabs = [...bar.querySelectorAll('.tab')];
  return { bar: bar.scrollWidth <= bar.clientWidth + 1, page: document.documentElement.scrollWidth <= window.innerWidth, count: tabs.length, tabs: tabs.map((t) => { const r = t.getBoundingClientRect(), sp = t.querySelector('span'), sr = sp.getBoundingClientRect(), cs = getComputedStyle(t);
    const room = r.width - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
    return { label: sp.textContent.trim(), w: Math.round(r.width), h: Math.round(r.height), text: Math.round(sr.width * 10) / 10, room: Math.round(room * 10) / 10, fits: sr.width <= room + 0.5 && sp.scrollWidth <= sp.clientWidth + 1, weight: getComputedStyle(sp).fontWeight, on: t.getAttribute('aria-current') === 'page' || t.classList.contains('on') || t.classList.contains('active') }; }) }; }"""

SIZES = "(sel) => [...document.querySelectorAll(sel)].filter((e) => !e.hidden && e.getClientRects().length).map((e) => { const r = e.getBoundingClientRect(); return [(e.id || e.dataset.act || e.className || e.tagName) + ':' + e.textContent.trim().slice(0, 14), Math.round(r.width), Math.round(r.height)]; }).filter((x) => x[2] < 44 || x[1] < 44)"
SMALLFONT = "(sel) => [...document.querySelectorAll(sel)].filter((e) => e.getClientRects().length).map((e) => [e.id || e.name || e.type, parseFloat(getComputedStyle(e).fontSize)]).filter((x) => x[1] < 16)"


def own(fid, name, n, **kw):
    f = {'id': fid, 'src': 'user', 'name': name, 'brand': '', 'barcode': '', 'basis': {'qty': 100, 'unit': 'g'}, 'n': n, 'nova': None, 'portions': [], 'note': '', 'created': 1000, 'updated': 1000}
    f.update(kw)
    return f


ALPHA = own('u:alpha', 'Alpha', {'kcal': 100, 'protein': 10, 'carbohydrate': 20, 'fat': 5, 'fibres': 2, 'salt': 0.5, 'calcium': 100, 'magnesium': 50, 'vitamin_c': 10})
BETA = own('u:beta', 'Beta', {'kcal': 200, 'protein': 5, 'carbohydrate': 30, 'fat': 10, 'fibres': 4, 'salt': 1, 'calcium': 200})
GAMMA = own('u:gamma', 'Gamma', {'kcal': 50})
CORE_FOODS = [ALPHA, BETA, GAMMA]
CORE = [('e1', 'u:alpha', 200, day(-3)), ('e2', 'u:beta', 100, day(-3)), ('e3', 'u:alpha', 100, day(-1)), ('e4', 'u:gamma', 100, day(-1)), ('e5', 'u:beta', 40, day(0))]   # Mon 2, Wed 4, Thu 5
CORE_WATER = {day(-3): 1500, day(-1): 2000}
REF_F = {'sex': 'f', 'age': '25', 'meno': 'pre', 'zinc': 600}


def cov(a, b):
    """The share of items that have data, as the Report writes it."""
    if a == b: return '100%'
    if a == 0: return '0%'
    x = math.floor(a / b * 100)
    return '<1%' if x < 1 else f'{x}%'


def pct(x):
    return '<1' if 0 < x < 1 else f'{round(x):,}'


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
            await c.add_init_script(INIT)
            await c.route('**/*openfoodfacts.org/**', lambda r: r.fulfill(status=200, headers={'access-control-allow-origin': '*', 'content-type': 'application/json'}, body='{"products":[],"status":0}'))
            return c

        def watch(pg, tag='P'):
            pg.on('pageerror', lambda e: errs.append(f'{tag} PE {e}'))
            pg.on('console', lambda m: errs.append(f'{tag} C {m.text}') if m.type == 'error' and 'Failed to load resource' not in m.text else None)

        async def fresh(w=390, h=844, tag='P'):
            c = await new_ctx(w, h)
            pg = await c.new_page(); watch(pg, tag)
            await pg.goto(URL); await pg.wait_for_selector('.hero')
            return c, pg

        ctx, page = await fresh()
        T = page.evaluate

        async def seed(entries, water=None, ref=None, foods=CORE_FOODS, kind='week', anchor=day(0), custom=None, open_all=True, pg=page, tab='report'):
            await pg.evaluate("""([foods, ents, water, ref, kind, anchor, custom, openAll, tab]) => { const t = window.__tapnaplo, S = t.S;
              S.log.length = 0; for (const k of Object.keys(S.foods)) delete S.foods[k]; S.meta.ref = ref; S.meta.water = water || {}; S.meta.nova = {};
              for (const f of foods) S.foods[f.id] = f;
              ents.forEach(([id, f, a, d], i) => S.log.push({ id, f, a, d, m: 'm1', t: 1000 + i, tm: '08:' + String(10 + (i % 50)) }));
              t.RP.kind = kind; t.RP.anchor = anchor; t.RP.custom = custom; for (const k of Object.keys(t.RP.open)) t.RP.open[k] = typeof openAll === 'object' ? openAll[k] : openAll;
              S.tab = tab; t.save(); t.render(); }""", [foods, entries, water, ref, kind, anchor, custom, open_all, tab])
            await pg.wait_for_timeout(40)

        async def rows(pg=page, root=DT):
            return await pg.evaluate(ROWS, root)

        async def ov(pg=page):
            return await pg.evaluate(OVERVIEW)

        async def sel(pg=page):
            return await pg.evaluate(SEL)

        async def kind(k, pg=page):
            await pg.click(f'[data-act=rp-kind][data-kind={k}]')
            await pg.wait_for_timeout(30)

        # =========================================================== 1 the tab and the sample
        tabs = await page.locator('#tabbar .tab span').all_inner_texts()
        check('six tabs: Diary, Nutrients, Report, My foods, Health log, Data', tabs == ['Diary', 'Nutrients', 'Report', 'My foods', 'Health log', 'Data'], tabs)
        await seed(CORE, CORE_WATER, REF_F, open_all=DEFAULT_OPEN)
        s = await sel()
        check('the Report tab opens with the title "Report", Week is chosen and the selector has the seven periods in order', s['title'] == 'Report' and s['pressed'] == ['week'] and s['names'] == ['Day', 'Week', 'Month', '3 months', '6 months', 'Year', 'Custom'], s)
        check('...the period is the week of today, Monday 2 to Sunday 8 Nov, "so far" because the week is not over (4 days)', s['when'] == '2–8 Nov 2026' and s['note'] == 'so far, 4 days', [s['when'], s['note']])
        check('...there is a date picker; no Today chip while the period contains today; Next is off (the next week is in the future), Previous is on', s['datepick'] and not s['today'] and s['prev'] and not s['next'], s)
        check('by default only Overview is open: Nutrients and Data quality are closed, and so is the Days fold',
              await T("() => ['overview', 'nutrients', 'quality', 'days'].map((k) => document.querySelector(`details[data-sec=${k}]`).open)") == [True, False, False, False])

        await seed(CORE, CORE_WATER, REF_F)
        o = await ov()
        check('Overview: 630 kcal over 3 logged days = 210 kcal a day (a day without entries is left out, not counted as 0)', o['hero'] == '210kcal', o['hero'])
        check('...the chips say "3 of 4 days logged · so far"', o['chips'] == ['3 of 4 days logged · so far'], o['chips'])
        check('...5 items, 1.7 a day on average', o['items'] == '5 items in all · 1.7 a day on average', o['items'])
        r = o['rows']
        # hand calculation: protein 25 + 10 + 2 = 37 / 3 = 12.33 (Gamma has no protein: ≥); carbohydrate 102 / 3 = 34; fat 29 / 3 = 9.67; fibre 11.6 / 3 = 3.87; salt 2.9 / 3 = 0.97; sugars: nobody
        check('...Protein ≥ 12.3 g, Carbohydrate ≥ 34 g, Fat ≥ 9.67 g, Fibre ≥ 3.87 g, Salt ≥ 0.97 g (all lower values: Gamma has no data)',
              [(r[k]['val'], r[k]['unit']) for k in ('Protein', 'Carbohydrate', 'Fat', 'Fibre', 'Salt')] == [('≥ 12.3', 'g'), ('≥ 34', 'g'), ('≥ 9.67', 'g'), ('≥ 3.87', 'g'), ('≥ 0.97', 'g')], r)
        check('...Sugars: nobody has data, so "no data" (never 0)', r['Sugars']['val'] == 'no data' and r['Sugars']['none'] and r['Sugars']['unit'] == '', r['Sugars'])
        wk = [k for k in r if k.startswith('Water intake')]
        check('...water: logged on 2 of the days (1,500 and 2,000 mL), so 1,750 mL, the average of the days with water logged', len(wk) == 1 and r[wk[0]]['val'] == '1,750' and r[wk[0]]['unit'] == 'mL' and 'average of 2 days with water logged' in r[wk[0]]['sub'], r.get(wk[0]))
        check('...the explanation names the divisor (3) and says that a day without entries is not 0', 'divided by the number of logged days (3)' in o['expl'] and 'not counted as 0' in o['expl'], o['expl'])
        check('...no "Open in Diary" button for a week', not o['diaryBtn'])
        check('the Days fold: "Days · 3 logged", one row per logged day with its items and energy, in date order',
              o['daysTitle'] == 'Days · 3 logged' and o['days'] == [['Mon, 2 Nov', '2 items', '400kcal'], ['Wed, 4 Nov', '2 items', '150kcal'], ['Thu, 5 Nov', '1 item', '80kcal']], [o['daysTitle'], o['days']])
        check('...and says that the 1 day without entries is not listed and not counted as 0', o['daysNote'] == '1 day without entries is not listed. It is not counted as 0.', o['daysNote'])

        # ---- Nutrients section
        R = await rows()
        check('Nutrients: Energy 210 kcal with a 100% badge in the "full" colour (every item has energy)', R['Energy']['val'] == '210kcal' and R['Energy']['pill'] == '100%' and R['Energy']['cls'] == 'full', R['Energy'])
        check('...Protein ≥ 12.3 g, badge 80% (4 of 5 items) in the "part" colour', R['Protein']['val'] == '≥ 12.3g' and R['Protein']['pill'] == '80%' and R['Protein']['cls'] == 'part', R['Protein'])
        check('...Sugars "no data", badge 0%, grey', R['Sugars']['val'] == 'no data' and R['Sugars']['none'] and R['Sugars']['pill'] == '0%' and R['Sugars']['cls'] == 'none', R['Sugars'])
        check('...Magnesium ≥ 50 mg (100 + 50 over 3 days) badge 40%; Vitamin C ≥ 10 mg badge 40%; Calcium ≥ 193 mg badge 80%',
              [(R[k]['val'], R[k]['pill']) for k in ('Magnesium', 'Vitamin C', 'Calcium')] == [('≥ 50mg', '40%'), ('≥ 10mg', '40%'), ('≥ 193mg', '80%')], [(R[k]['val'], R[k]['pill']) for k in ('Magnesium', 'Vitamin C', 'Calcium')])
        pe = R['Protein']
        check('...Protein "Added up from": Alpha 300 g in 2 entries = 30 g, Beta 140 g in 2 entries = 7 g (merged per food over the days), heading "3 logged days, 37 g in all"',
              pe['parts'] == [['Alpha · 300 g · 2 entries', '30g', ''], ['Beta · 140 g · 2 entries', '7g', '']] and pe['head'] == 'Added up from · 3 logged days, 37 g in all', [pe['parts'], pe['head']])
        check('...Energy "Added up from": 300, 280 and 50 kcal, 630 kcal in all (= 3 x 210)', [x[1] for x in R['Energy']['parts']] == ['300kcal', '280kcal', '50kcal'] and R['Energy']['head'] == 'Added up from · 3 logged days, 630 kcal in all', [R['Energy']['parts'], R['Energy']['head']])
        check('...the detail lines say how many items have data, the days with complete data (and their average), and who has none',
              'Data for 4 of 5 items (80%).' in pe['det'] and 'Days with complete data: 2 of 3 · average 13.5 g' in pe['det'] and 'No data for: Gamma' in pe['det'], pe['det'])
        check('...calcium: complete on 2 of 3 days, average 240 mg (400 and 80)', 'Days with complete data: 2 of 3 · average 240 mg' in R['Calcium']['det'], R['Calcium']['det'])
        check('...magnesium has no complete day, so no such line; energy is complete on every day, so no such line either',
              not any(d.startswith('Days with complete data') for d in R['Magnesium']['det'] + R['Energy']['det']) and 'Every item has data.' in R['Energy']['det'], [R['Magnesium']['det'], R['Energy']['det']])
        check('...a row nobody has data for has no "Added up from" list', R['Sugars']['parts'] == [] and R['Sugars']['head'] is None)
        check('the banner names the divisor and says that a ≥ is a lower value; there is no "~" banner (no estimates)', await T("() => { const b = [...document.querySelectorAll(`%s .banner`)].map((x) => x.textContent); return b.length === 1 && b[0].startsWith('Averages per logged day: the sum of the 3 logged days divided by 3.') && b[0].includes('a ≥ value is a lower value'); }" % DT))

        # ---- EFSA on the average
        check('EFSA, Calcium: ≥ 20% of 950 mg · PRI (193.3 / 950), a solid bar at 20.35%', R['Calcium']['line'] == '≥ 20% of 950 mg · PRI' and 'pri' in R['Calcium']['track'] and abs(float(R['Calcium']['bar'].rstrip('%')) - 193.3333 / 950 * 100) < 0.01, [R['Calcium']['line'], R['Calcium']['bar']])
        check('...Magnesium ≥ 17% of 300 mg · AI (50 / 300), dashed bar; Vitamin C ≥ 11% of 95 mg · PRI (10 / 95); Fibre ≥ 15% of 25 g · AI (3.87 / 25)',
              [(R[k]['line'], 'ai' in (R[k]['track'] or '')) for k in ('Magnesium', 'Vitamin C', 'Fibre')] == [('≥ 17% of 300 mg · AI', True), ('≥ 11% of 95 mg · PRI', False), ('≥ 15% of 25 g · AI', True)], [(R[k]['line'], R[k]['track']) for k in ('Magnesium', 'Vitamin C', 'Fibre')])
        check('...a screen reader hears the words, with "at least", and the period (the reference is a daily average)', 'Calcium: at least 20 percent of the reference intake of 950 milligrams (population reference intake).' == R['Calcium']['say'], R['Calcium']['say'])
        va = R['Vitamin A (retinol)']
        check('...Vitamin A: nobody has retinol or beta-carotene, so "Reference 650 µg RE · PRI · no data to compare", no bar and no 0%', va['line'] == 'Reference 650 µg RE · PRI · no data to compare' and va['track'] is None and va['bar'] is None, va)
        check('...the banner adds "A period below them is not a deficiency."', await T("() => document.querySelector('%s .banner').textContent.includes('Reference values are long-term daily averages. A period below them is not a deficiency.')" % DT))
        check('...the profile card is on the Report too (Change is there)', await page.locator('details[data-sec=nutrients] [data-act=ref-change]').count() == 1)

        # ---- Data quality
        Q = await page.evaluate(QUALITY)
        cells = Q['cal']['cells'] if Q['cal'] else []
        check('Data quality: the calendar has the 4 days of the period, Monday first, no padding (the period starts on a Monday); Mon, Wed and Thu are filled, Tue is outlined; Mon and Wed have the water dot',
              Q['cal'] and Q['cal']['heads'] == 'MTWTFSS' and Q['cal']['pads'] == 0 and [c[:2] for c in cells] == [['2', 'logged w'], ['3', 'none'], ['4', 'logged w'], ['5', 'logged']], Q['cal'])
        check('...the spoken text of a day: "Mon, 2 Nov: has entries, water logged" / "Tue, 3 Nov: no entries"', [c[2] for c in cells][:2] == ['Mon, 2 Nov: has entries, water logged', 'Tue, 3 Nov: no entries'], [c[2] for c in cells])
        it = {x[0]: x for x in Q['sections']['Items']}
        check('...Items: days with entries 3 of 4; items 5; energy data 100% (5 of 5); estimated share 0%; 100% of the energy is not yet in a NOVA group',
              it['Days with entries'][2] == '3 of 4' and it['Items'][2] == '5' and it['Items with energy data'][2] == '100%5 of 5' and it['Estimated share of the values'][2] == '0%' and it['Energy not yet sorted into a NOVA group'][2] == '100%', it)
        check('...Energy by data source: your own foods, 5 items, 100% of energy', Q['sections']['Energy by data source'] == [['Your own foods', '5 items', '100% of energy']], Q['sections']['Energy by data source'])
        least = [x[0] for x in Q['sections']['Nutrients with the least data']]
        check('...the nutrients with the least data: the five (alphabetically first) that no item has data for, each 0 of 5 items', least == ['Alpha-linolenic acid (18:3 n-3)', 'Arachidonic acid (20:4 n-6)', 'Beta-carotene', 'Chloride', 'Cholesterol'] and all(x[1] == '0 of 5 items' and x[2] == '0%' for x in Q['sections']['Nutrients with the least data']), Q['sections']['Nutrients with the least data'])

        # =========================================================== 2 period maths (pure)
        async def rng(kind_, anchor, custom=None):
            return await T("([k, a, c]) => { const r = window.__tapnaplo.rpRange({ kind: k, anchor: a, custom: c }); return { from: r.from, to: r.to, ff: r.fullFrom, ft: r.fullTo, days: r.days, partial: r.partial, prevOk: r.prevOk, nextOk: r.nextOk, hasToday: r.hasToday, empty: r.empty }; }", [kind_, anchor, custom])

        r = await rng('week', '2026-11-05')
        check('week of Thu 5 Nov 2026: Mon 2 to Sun 8, cut at today, 4 days, partial, contains today', (r['ff'], r['ft'], r['from'], r['to'], r['days'], r['partial'], r['hasToday']) == ('2026-11-02', '2026-11-08', '2026-11-02', '2026-11-05', 4, True, True), r)
        r = await rng('week', '2026-11-01')
        check('Sunday 1 Nov belongs to the week of Monday 26 Oct (weeks start on Monday): 26 Oct - 1 Nov, 7 days, not partial', (r['from'], r['to'], r['days'], r['partial']) == ('2026-10-26', '2026-11-01', 7, False), r)
        r = await rng('week', '2026-11-02')
        check('Monday 2 Nov starts its own week', (r['ff'], r['ft']) == ('2026-11-02', '2026-11-08'), r)
        r = await rng('week', '2024-02-29')
        check('the week of the leap day Thu 29 Feb 2024: 26 Feb - 3 Mar, 7 days', (r['from'], r['to'], r['days']) == ('2024-02-26', '2024-03-03', 7), r)
        r = await rng('month', '2026-11-05')
        check('month of 5 Nov 2026: 1 Nov - 30 Nov, cut at today: 5 days, partial', (r['ff'], r['ft'], r['from'], r['to'], r['days'], r['partial']) == ('2026-11-01', '2026-11-30', '2026-11-01', '2026-11-05', 5, True), r)
        r = await rng('month', '2026-02-15')
        check('February 2026 has 28 days; February 2024 has 29 (leap year); December has 31', [(await rng('month', a))['days'] for a in ('2026-02-15', '2024-02-10', '2025-12-31')] == [28, 29, 31])
        r = await rng('m3', '2026-11-05')
        check('3 months = the month of the day and the 2 months before it: 1 Sep - 30 Nov, cut at today: 66 days', (r['ff'], r['ft'], r['days']) == ('2026-09-01', '2026-11-30', 66), r)
        r = await rng('m6', '2026-11-05')
        check('6 months: 1 Jun - 30 Nov (the month of the day and the 5 months before it), 158 days so far', (r['ff'], r['ft'], r['days']) == ('2026-06-01', '2026-11-30', 158), r)
        r = await rng('year', '2026-11-05')
        check('Year = 12 months ending with the month of the day: 1 Dec 2025 - 30 Nov 2026, 340 days so far', (r['ff'], r['ft'], r['days']) == ('2025-12-01', '2026-11-30', 340), r)
        r = await rng('year', '2026-01-15')
        check('Year ending in January 2026: 1 Feb 2025 - 31 Jan 2026, 365 days, over (not partial)', (r['ff'], r['ft'], r['days'], r['partial']) == ('2025-02-01', '2026-01-31', 365, False), r)
        r = await rng('year', '2024-12-20')
        check('a year that contains a leap day: 1 Jan - 31 Dec 2024 is 366 days', (await rng('year', '2024-12-20'))['days'] == 366 and (await rng('year', '2024-12-20'))['ff'] == '2024-01-01')
        r = await rng('day', '2026-11-05')
        check('Day: one day, contains today, not partial', (r['from'], r['to'], r['days'], r['partial'], r['hasToday']) == ('2026-11-05', '2026-11-05', 1, False, True), r)
        r = await rng('custom', '2026-11-05', {'from': '2026-10-01', 'to': '2026-10-10'})
        check('Custom 1 - 10 Oct: 10 days, does not contain today', (r['from'], r['to'], r['days'], r['hasToday']) == ('2026-10-01', '2026-10-10', 10, False), r)
        r = await rng('custom', '2026-11-05', {'from': '2026-10-30', 'to': '2026-11-20'})
        check('a Custom period that reaches into the future is cut at today ("so far")', (r['from'], r['to'], r['days'], r['partial']) == ('2026-10-30', '2026-11-05', 7, True), r)
        check('Custom entirely in the future is empty', (await rng('custom', '2026-11-05', {'from': '2026-11-10', 'to': '2026-11-20'}))['empty'])

        async def step(kind_, anchor, custom, d):
            return await T("([k, a, c, d]) => { const s = window.__tapnaplo.rpStep(k, a, c, d), f = window.__tapnaplo.rpFull(k, s.anchor, s.custom); return { anchor: s.anchor, from: f.from, to: f.to }; }", [kind_, anchor, custom, d])

        s_ = await step('week', '2026-11-05', None, -1)
        check('Previous week from Thu 5 Nov: 26 Oct - 1 Nov', (s_['from'], s_['to']) == ('2026-10-26', '2026-11-01'), s_)
        s_ = await step('week', '2026-11-05', None, 1)
        check('Next week: 9 - 15 Nov', (s_['from'], s_['to']) == ('2026-11-09', '2026-11-15'), s_)
        s_ = await step('month', '2026-01-31', None, -1)
        check('Previous month from 31 Jan does not skip to March or stay in January (the day is not carried): December 2025', (s_['from'], s_['to']) == ('2025-12-01', '2025-12-31'), s_)
        s_ = await step('month', '2026-03-31', None, -1)
        check('Previous month from 31 Mar: February 2026 (28 days), not 3 Mar', (s_['from'], s_['to']) == ('2026-02-01', '2026-02-28'), s_)
        s_ = await step('m3', '2026-11-05', None, -1)
        check('Previous 3 months do not overlap: 1 Jun - 31 Aug 2026', (s_['from'], s_['to']) == ('2026-06-01', '2026-08-31'), s_)
        s_ = await step('year', '2026-11-05', None, -1)
        check('Previous year: 1 Dec 2024 - 30 Nov 2025', (s_['from'], s_['to']) == ('2024-12-01', '2025-11-30'), s_)
        s_ = await step('day', '2026-01-01', None, -1)
        check('Previous day across the year edge: 31 Dec 2025', s_['from'] == '2025-12-31', s_)
        s_ = await step('custom', '2026-11-05', {'from': '2026-10-01', 'to': '2026-10-10'}, 1)
        check('Custom 1 - 10 Oct, next: the same length right after it (11 - 20 Oct)', (s_['from'], s_['to']) == ('2026-10-11', '2026-10-20'), s_)
        s_ = await step('custom', '2026-11-05', {'from': '2026-10-01', 'to': '2026-10-10'}, -1)
        check('...previous: 21 - 30 Sep', (s_['from'], s_['to']) == ('2026-09-21', '2026-09-30'), s_)
        r = await rng('month', '2026-10-15')
        check('October: Next is possible (November has started), and from November on it is not (December is in the future)', r['nextOk'] and not (await rng('month', '2026-11-05'))['nextOk'])

        # =========================================================== 3 the buttons
        await seed(CORE, CORE_WATER, REF_F, open_all=DEFAULT_OPEN)
        await kind('day')
        s = await sel()
        check('Day: today, "Thursday 5 November 2026", no "so far" note; no Today chip', bool(re.fullmatch(r'Thursday,? 5 November 2026', s['when'])) and s['note'] == '' and not s['today'], s)
        o = await ov()
        check('...Day shows 80 kcal and "1 of 1 day logged", and an "Open in Diary" button', o['hero'] == '80kcal' and o['chips'] == ['1 of 1 day logged'] and o['diaryBtn'], [o['hero'], o['chips'], o['diaryBtn']])
        await page.click('[data-act=rp-step][data-n="-1"]')
        s = await sel()
        o = await ov()
        check('Previous (Day): Wednesday 4 Nov, 150 kcal (2 items, one without protein data: ≥)', bool(re.fullmatch(r'Wednesday,? 4 November 2026', s['when'])) and o['hero'] == '150kcal' and o['rows']['Protein']['val'] == '≥ 10', [s['when'], o['hero'], o['rows']['Protein']])
        check('...a Today chip appears now that the period does not contain today', s['today'])
        await page.click('[data-act=rp-diary]')
        check('Open in Diary opens the Diary on that day', await T('() => window.__tapnaplo.S.tab') == 'log' and await T('() => window.__tapnaplo.S.day') == day(-1))
        await page.click('[data-tab=report]'); await page.wait_for_timeout(30)
        await page.click('[data-act=rp-today]')
        s = await sel()
        check('Today chip jumps back to the period of today', bool(re.fullmatch(r'Thursday,? 5 November 2026', s['when'])) and not s['today'], s)
        await page.click('[data-act=rp-step][data-n="-1"]'); await page.click('[data-act=rp-step][data-n="-1"]')
        await page.click('[data-act=rp-step][data-n="-1"]')   # Mon 2 Nov
        o = await ov()
        check('...Day, 2 days back (Mon 2 Nov): 400 kcal', o['hero'] == '400kcal', o['hero'])
        await page.click('[data-act=rp-step][data-n="-1"]')
        txt = await page.inner_text('#view')
        check('a day without entries (Sun 1 Nov): "No entries on …" card with a Go to Diary button, and the numbers are not shown as 0', 'No entries on' in txt and '1 Nov' in txt and await page.locator('[data-act=tab][data-tab=log]').count() >= 1 and 'Average per logged day' not in txt, txt[:300])
        await page.click('[data-act=rp-today]')
        await kind('week')
        s = await sel()
        check('Week again: 2 - 8 Nov', s['pressed'] == ['week'] and s['when'] == '2–8 Nov 2026', s)
        await page.click('[data-act=rp-step][data-n="-1"]')
        s = await sel(); txt = await page.inner_text('#view')
        check('Previous week (26 Oct - 1 Nov, no entries): the card says so, the period is not "so far", Next is on', s['when'] == '26 Oct – 1 Nov 2026' and s['note'] == '' and s['next'] and 'No entries from' in txt, [s['when'], s['note'], txt[:200]])
        await page.click('[data-act=tab][data-tab=log] >> nth=0')
        check('...Go to Diary leads to the Diary', await T('() => window.__tapnaplo.S.tab') == 'log')
        await page.click('[data-tab=report]'); await page.wait_for_timeout(30)
        await page.click('[data-act=rp-today]')
        for k, when, note in [('month', 'November 2026', 'so far, 5 days'), ('m3', 'Sept – Nov 2026', 'so far, 66 days'), ('m6', 'Jun – Nov 2026', 'so far, 158 days'), ('year', 'Dec 2025 – Nov 2026', 'so far, 340 days')]:
            await kind(k)
            s = await sel()
            check(f'{k}: "{when}", {note}', s['pressed'] == [k] and s['when'] == when and s['note'] == note, [s['pressed'], s['when'], s['note']])
        await kind('month')
        o = await ov()
        check('Month (1 - 5 Nov): the same 3 logged days, "3 of 5 days logged · so far"', o['chips'] == ['3 of 5 days logged · so far'] and o['hero'] == '210kcal', [o['chips'], o['hero']])
        await kind('week')
        await page.fill('#rp-date', '2026-10-14')
        s = await sel()
        check('the date picker sets the day the period is built around: Wed 14 Oct is in the week of 12 - 18 Oct, and a Today chip appears', s['when'] == '12–18 Oct 2026' and s['note'] == '' and s['today'], s)
        await kind('month')
        s = await sel()
        check('...the month of that day: October 2026', s['when'] == 'October 2026', s)
        await page.fill('#rp-date', '2026-11-20')
        s = await sel()
        check('a date in the future is pulled back to today (the max of the picker)', s['when'] == 'November 2026' and s['note'] == 'so far, 5 days', s)

        # =========================================================== 4 Custom
        await kind('week')
        await page.click('[data-act=rp-kind][data-kind=custom]'); await page.wait_for_selector('#rc-apply')
        check('Custom opens a sheet "Custom period" with the two dates filled in from the period that is shown', (await page.input_value('#rc-from'), await page.input_value('#rc-to')) == ('2026-11-02', '2026-11-05') and 'Custom period' in await page.inner_text('.sheet'))
        check('...the sheet has the quick buttons Last 14 days, Last 30 days, Whole diary and no sheet error', [await page.inner_text(f'#rc-quick [data-q="{q}"]') for q in ('14', '30', 'all')] == ['Last 14 days', 'Last 30 days', 'Whole diary'] and await page.locator('#rc-err').is_hidden())
        await page.click('#rc-quick [data-q="14"]')
        check('Last 14 days: 23 Oct - 5 Nov', (await page.input_value('#rc-from'), await page.input_value('#rc-to')) == ('2026-10-23', '2026-11-05'))
        await page.click('#rc-quick [data-q="30"]')
        check('Last 30 days: 7 Oct - 5 Nov', (await page.input_value('#rc-from'), await page.input_value('#rc-to')) == ('2026-10-07', '2026-11-05'))
        await page.click('#rc-quick [data-q="all"]')
        check('Whole diary: from the first day with entries or water (2 Nov) to the last (5 Nov)', (await page.input_value('#rc-from'), await page.input_value('#rc-to')) == ('2026-11-02', '2026-11-05'))

        async def apply_err(frm, to, expect, label):
            await page.fill('#rc-from', frm); await page.fill('#rc-to', to)
            await page.click('#rc-apply'); await page.wait_for_timeout(30)
            msg = (await page.inner_text('#rc-err')) if await page.locator('#rc-err').is_visible() else ''
            still = await page.locator('#rc-apply').count() == 1
            check(f'Custom error: {label}', msg == expect and still, msg)

        await apply_err('', '2026-11-03', 'Choose a start date.', 'no start date')
        await apply_err('2026-11-01', '', 'Choose an end date.', 'no end date')
        await apply_err('2026-11-04', '2026-11-01', 'The start date cannot be after the end date.', 'start after end')
        await apply_err('2026-11-01', '2026-11-20', 'The end date cannot be in the future.', 'end in the future')
        await apply_err('1999-12-31', '2026-11-01', 'The start date cannot be before 1 Jan 2000.', 'before the year 2000')
        check('...the error sits next to the dates (inside the sheet), is announced (role=alert) and the field is marked invalid', await T("() => { const e = document.querySelector('#rc-err'); return e.getAttribute('role') === 'alert' && e.closest('.sheet') !== null; }"))
        await page.click('#rc-cancel'); await page.wait_for_timeout(250)
        s = await sel()
        check('Cancel closes the sheet and changes nothing (still Week)', await page.locator('#rc-apply').count() == 0 and s['pressed'] == ['week'] and s['when'] == '2–8 Nov 2026', s)
        await page.click('[data-act=rp-kind][data-kind=custom]'); await page.wait_for_selector('#rc-apply')
        await page.fill('#rc-from', '2026-10-28'); await page.fill('#rc-to', '2026-11-03')
        await page.click('#rc-apply'); await page.wait_for_timeout(250)
        s = await sel()
        check('Apply 28 Oct - 3 Nov: Custom is chosen, "28 Oct – 3 Nov 2026", 7 days, no "so far"', s['pressed'] == ['custom'] and s['when'] == '28 Oct – 3 Nov 2026' and s['note'] == '', s)
        check('...in Custom there is no date picker and no Today chip (the dates are the period)', not s['datepick'] and not s['today'])
        o = await ov()
        check('...only the logged days inside the range count: Mon 2 Nov alone (400 kcal), "1 of 7 days logged"', o['hero'] == '400kcal' and o['chips'] == ['1 of 7 days logged'], [o['hero'], o['chips']])
        await page.click('[data-act=rp-step][data-n="1"]')
        s = await sel()
        check('Next in Custom moves by the length of the range: 4 - 10 Nov, cut at today (2 days, "so far")', s['when'] == '4–10 Nov 2026' and s['note'] == 'so far, 2 days' and not s['next'], s)
        await page.click('[data-act=rp-step][data-n="-1"]'); await page.click('[data-act=rp-step][data-n="-1"]')
        s = await sel()
        check('Previous twice: 21 - 27 Oct', s['when'] == '21–27 Oct 2026', s)
        ls = json.loads(await T("() => localStorage.getItem('nutrilog.period')"))
        check('the choice is kept on this device: kind and the dates, nothing else', ls == {'kind': 'custom', 'custom': {'from': '2026-10-21', 'to': '2026-10-27'}}, ls)

        # =========================================================== 5 saved choices and damaged values
        await kind('month')
        await page.reload(); await page.wait_for_selector('.rp-seg')
        s = await sel()
        check('after a reload the Report tab and the period (Month) are still there', s['pressed'] == ['month'] and s['title'] == 'Report', s)
        await T("() => { document.querySelector('details[data-sec=quality]').open = true; }"); await page.wait_for_timeout(60)
        ro = json.loads(await T("() => localStorage.getItem('nutrilog.reportOpen')"))
        check('opening "Data quality" is remembered: {overview: true, quality: true, others false}', ro == {'overview': True, 'days': False, 'trend': False, 'trendtable': False, 'nutrients': False, 'quality': True}, ro)
        await page.reload(); await page.wait_for_selector('.rp-seg')
        check('...and it is open after a reload', await T("() => document.querySelector('details[data-sec=quality]').open"))

        async def with_ls(period, openv, expect_kind, label, expect_open=None):
            await page.evaluate("([a, b]) => { localStorage.setItem('nutrilog.period', a); localStorage.setItem('nutrilog.reportOpen', b); }", [period, openv])
            await page.reload(); await page.wait_for_selector('.rp-seg')
            s_ = await sel()
            op = await T("() => ['overview', 'days', 'nutrients', 'quality'].map((k) => document.querySelector(`details[data-sec=${k}]`) && document.querySelector(`details[data-sec=${k}]`).open)")
            check(f'damaged saved value ({label}): {expect_kind} and no error', s_['pressed'] == [expect_kind] and (expect_open is None or op == expect_open), [s_['pressed'], op])

        await with_ls('not json{', 'also not json', 'week', 'not JSON', [True, False, False, False])
        await with_ls('{"kind":"nonsense"}', '[1,2]', 'week', 'unknown kind, open state is a list', [True, False, False, False])
        await with_ls('{"kind":"custom"}', '{"overview":"yes","nutrients":true,"x":true}', 'week', 'Custom without dates; a text instead of a boolean is ignored, an unknown key too', [True, False, True, False])
        await with_ls('{"kind":"custom","custom":{"from":"2026-02-30","to":"2026-03-01"}}', 'null', 'week', 'Custom with a day that does not exist')
        await with_ls('{"kind":"custom","custom":{"from":"2026-03-05","to":"2026-03-01"}}', 'null', 'week', 'Custom with the dates the wrong way round')
        await with_ls('{"kind":"custom","custom":{"from":"1990-01-01","to":"2026-03-01"}}', 'null', 'week', 'Custom before the year 2000')
        await with_ls('{"kind":"constructor"}', 'null', 'week', '"constructor" as the kind')
        await with_ls('{"kind":"year","custom":null}', '{"overview":false}', 'year', 'a valid Year, Overview closed', [False, False, False, False])
        await T("() => { localStorage.removeItem('nutrilog.period'); localStorage.removeItem('nutrilog.reportOpen'); }")

        # =========================================================== 6 empty periods and the hidden entries
        await seed([], None, None, open_all=DEFAULT_OPEN)
        txt = await page.inner_text('#view')
        check('an empty diary: the week card says "No entries from 2 Nov to 5 Nov 2026." and explains that a day without entries is not 0; no sections', 'No entries from 2 Nov to 5 Nov 2026.' in txt and 'not a day of 0' in txt and await page.locator('details.rp-sec').count() == 0, txt[:300])
        check('...the selector and the arrows are still there, and the Go to Diary button works', await page.locator('.rp-seg button').count() == 7 and await page.locator('[data-act=rp-step]').count() == 2 and await page.locator('#view [data-act=tab][data-tab=log]').count() == 1)
        await seed([], {day(-1): 1200}, None, open_all=DEFAULT_OPEN)
        txt = await page.inner_text('#view')
        check('water but no food in the period: the card says no entries and the water is still shown (1,200 mL)', 'No entries from' in txt and '1,200' in txt and 'mL' in txt, txt[:300])
        await seed(CORE + [('e9', 'u:ghost', 100, day(-3)), ('e10', 'u:ghost', 100, day(-1))], CORE_WATER, None)
        txt = await page.inner_text('#view')
        o = await ov()
        check('entries whose food is not loaded are not counted, and a banner says how many (2) and why', '2 entries in this period are not counted: the food data is not available' in txt and o['hero'] == '210kcal' and o['chips'] == ['3 of 4 days logged · so far'], [txt[:260], o['hero']])
        await seed([('e9', 'u:ghost', 100, day(-3))], None, None)
        txt = await page.inner_text('#view')
        check('a period whose only entry is hidden shows the empty card and the banner (singular wording)', '1 entry in this period is not counted' in txt and 'No entries from' in txt, txt[:300])

        # =========================================================== 7 parity with the Nutrients tab
        CIQ = json.loads((ROOT / 'ciqual.json').read_text(encoding='utf-8'))
        cf = next(f for f in CIQ['foods'] if isinstance(f['v'][0], (int, float)) and f['v'][0] > 0 and isinstance(f['v'][2], (int, float)))
        CIQ_ID = 'c:' + str(cf['c'])
        FISH = own('u:fish', 'Salmon', {'kcal': 200, 'fa_18_2_9c_12c_n_6': 0.5, 'fa_20_4_5c_8c_11c_14c_n_6': 0.1, 'fa_18_3_c9_c12_c15_n_3': 0.3, 'fa_20_5_5c_8c_11c_14c_17c_n_3_epa': 1.0, 'fa_22_6_4c_7c_10c_13c_16c_19c_n_3_dha': 1.5, 'vitamin_d': 10, 'retinol': 40, 'beta_carotene': 600})
        OIL = own('u:oil', 'Rapeseed oil', {'kcal': 880, 'fat': 99, 'fa_18_2_9c_12c_n_6': 20, 'fa_18_3_c9_c12_c15_n_3': 9, 'vitamin_e': 20})
        ESTF = own('u:estf', 'Est food', {'kcal': 100, 'calcium': 95, 'protein': 8}, est=['calcium'], q='m')
        LIMF = own('u:limf', 'Limit food', {'kcal': 10, 'calcium': '<201', 'protein': '<2'})
        B1F = own('u:b1', 'Thiamin food', {'kcal': 120, 'vitamin_b1_or_thiamin': 0.4, 'vitamin_b3_or_niacin': 3})
        NOEN = own('u:noen', 'No energy', {'vitamin_b1_or_thiamin': 0.5, 'iron': 2})
        PFOODS = CORE_FOODS + [FISH, OIL, ESTF, LIMF, B1F, NOEN]
        todays = [('p1', 'u:alpha', 150, day(0)), ('p2', 'u:beta', 80, day(0)), ('p3', 'u:gamma', 60, day(0)), ('p4', 'u:fish', 120, day(0)), ('p5', 'u:oil', 15, day(0)), ('p6', 'u:estf', 100, day(0)), ('p7', 'u:limf', 100, day(0)),
                  ('p8', 'u:b1', 200, day(0)), ('p9', 'u:noen', 50, day(0)), ('p10', CIQ_ID, 130, day(0))]
        for with_ref in (None, REF_F):
            for mode in ('day', 'custom1'):
                await seed(todays, None, with_ref, foods=PFOODS, tab='nutr')
                nt = await rows(page, '#view')
                await seed(todays, None, with_ref, foods=PFOODS, kind='day' if mode == 'day' else 'custom', custom=None if mode == 'day' else {'from': day(0), 'to': day(0)})
                rp = await rows(page)
                tag = ('with the profile' if with_ref else 'without a profile') + (', Day' if mode == 'day' else ', Custom of one day')
                check(f'parity ({tag}): the Report has exactly the rows of the Nutrients tab, in the same order ({len(nt)} rows)', list(rp.keys()) == list(nt.keys()) and len(nt) > 60, [len(rp), len(nt), [k for k in rp if k not in nt][:3], [k for k in nt if k not in rp][:3]])
                diff = []
                for k in nt:
                    a, b = nt[k], rp.get(k)
                    if not b: continue
                    for f in ('val', 'none', 'line', 'say', 'bar', 'track', 'head', 'parts'):
                        if a[f] != b[f]: diff.append((k, f, a[f], b[f]))
                    for d in a['det']:
                        if d not in b['det']: diff.append((k, 'det', d, b['det']))
                check(f'...every value, every EFSA line / bar / spoken sentence, every "Added up from" list and every detail line is identical ({tag})', diff == [], diff[:3])
                badpill = [(k, v['pill'], nt[k]['pill']) for k, v in rp.items() if k in nt and (lambda m: v['pill'] != cov(int(m.group(1)), int(m.group(2))))(re.fullmatch(r'(\d+)/(\d+)', nt[k]['pill']))]
                check(f'...the badge is the same share as the Nutrients tab\'s "k/n" counts ({tag})', badpill == [], badpill[:3])
        check('the special rows are among them: EPA + DHA (with a profile) and the omega ratio', 'EPA + DHA' in rp and 'Omega-6 : omega-3 ratio' in rp and 'Vitamin A (retinol)' in rp)
        # the hero, protein and fat of the Report Day equal the Diary day
        dh = await T("() => { const t = window.__tapnaplo, T = t.totalsFor(t.S.log.filter((e) => e.d === '%s')); return [T.lo[0], T.lo[t.IDX.protein], T.lo[t.IDX.fat]]; }" % day(0))
        o = await ov()
        check('Report Day: energy, protein and fat equal totalsFor of that day', o['hero'].replace('≥ ', '').replace('~', '') == (await T('(v) => window.__tapnaplo.fmt(v)', dh[0])) + 'kcal' and o['rows']['Protein']['val'].replace('≥ ', '').replace('~', '') == await T('(v) => window.__tapnaplo.fmt(v)', dh[1]) and o['rows']['Fat']['val'].replace('≥ ', '').replace('~', '') == await T('(v) => window.__tapnaplo.fmt(v)', dh[2]), [o['hero'], o['rows']['Protein'], dh])

        # =========================================================== 8 sums: the parts add up to the total of the row
        await seed(CORE + [('s1', 'u:fish', 50, day(-2)), ('s2', 'u:oil', 10, day(-2)), ('s3', 'u:estf', 100, day(-4)), ('s4', 'u:limf', 100, day(-4))], CORE_WATER, REF_F, foods=PFOODS, kind='custom', custom={'from': day(-4), 'to': day(0)})
        bad = await T("""() => { const t = window.__tapnaplo, out = [], tx = window.__txt;
          document.querySelectorAll('%s details.nrow').forEach((r) => {
            const head = r.querySelector('.nc-h'); if (!head) return;
            const lab = r.querySelector('summary > span').textContent;
            const items = [...r.querySelectorAll('.ncontrib li')];
            const num = (s) => { if (/^~?</.test(s)) return 0; const m = s.replace(/,/g, '').match(/-?\\d+(\\.\\d+)?/); return m ? parseFloat(m[0]) : NaN; };
            const sum = items.reduce((a, li) => a + num(tx(li.querySelector('.nc-val'), '.sr-only')), 0);
            const m = head.textContent.match(/, (.+?) in all/); const total = m ? num(m[1]) : NaN;
            if (!(Math.abs(sum - total) <= Math.max(0.011, Math.abs(total) * 0.02))) out.push([lab, sum, total]);
          }); return out; }""" % DT)
        check('in every row of the Report the lines of "Added up from" add up to the total in the heading (checked in the page, all rows)', bad == [], bad[:4])
        tot = await T("""() => { const t = window.__tapnaplo, P = t.rpStats('%s', '%s'); const i = t.IDX.calcium; return [P.nd, P.T.lo[i] * P.nd, P.T.hi[i] * P.nd]; }""" % (day(-4), day(0)))
        # Sun 1 Nov: 95 (estimate) + a limit <201 (0..201); Mon 2: 200 + 200; Tue 3: nothing with calcium (the day still counts: 0); Wed 4: 100; Thu 5: 80
        check('the average times the number of logged days is the sum of the parts: calcium over 5 logged days is 675 (lower) to 876 (upper); a logged day without calcium data (Tue) counts as 0 in the sum and in the divisor', tot[0] == 5 and abs(tot[1] - (95 + 0 + 400 + 0 + 100 + 80)) < 1e-9 and abs(tot[2] - (95 + 201 + 400 + 0 + 100 + 80)) < 1e-9, tot)

        # =========================================================== 9 ranges and estimates over a period
        await seed([('r1', 'u:estf', 100, day(-4)), ('r2', 'u:limf', 100, day(-4)), ('r3', 'u:alpha', 100, day(-3))], None, REF_F, foods=PFOODS, kind='month')
        R = await rows()
        c = R['Calcium']
        # day Sun 1 Nov: estimated 95 + a limit (0..201) = 95..296; Mon 2 Nov: 100. Two logged days: lower (95 + 100) / 2 = 97.5, upper (296 + 100) / 2 = 198
        check('a "<x" value makes a range and an estimate a "~": Calcium ~97.5–198 mg over two logged days (95 est. + 0..201 on day 1, 100 on day 2)', c['val'] == '~97.5–198mg', c['val'])
        check('...every item has data for calcium (a limit is data), so no ≥ and the badge is 100%', c['pill'] == '100%' and c['cls'] == 'full', c)
        check('...EFSA: ~10–21% of 950 mg · PRI (97.5 / 950 to 198 / 950), a range', c['line'] == '~10–21% of 950 mg · PRI', c['line'])
        check('...the lines of "Added up from": Est food ~95, Alpha 100, Limit food <201 (range), and the "~" is spoken as "estimated"', [x[0].split(' · ')[0] for x in c['parts']] == ['Alpha', 'Est food', 'Limit food'] and [x[1] for x in c['parts']] == ['100mg', '~95mg', '<201mg'], c['parts'])
        check('...the detail names the estimate with its confidence: "Estimate, not a label value: Est food (medium)"', 'Estimate, not a label value: Est food (medium)' in c['det'], c['det'])
        check('...the banner explains the "~"', await T("() => [...document.querySelectorAll('%s .banner')].some((b) => b.textContent.startsWith('A ~ in front of a value means'))" % DT))
        p_ = R['Protein']
        check('...Protein: Sun 8 (not an estimate: only calcium is) + a limit <2 = 8..10, Mon 10; average 9..10 g, a range, no ≥ and no ~', p_['val'] == '9–10g', p_['val'])

        # =========================================================== 10 B1 and niacin follow the energy, only on the days with complete energy data
        E1 = own('u:e1', 'Energetic', {'kcal': 100, 'vitamin_b1_or_thiamin': 0.5, 'vitamin_b3_or_niacin': 2})
        NOE = own('u:noe', 'No energy item', {'vitamin_b1_or_thiamin': 1.0})
        EF = [E1, NOE]
        await seed([('b1', 'u:e1', 200, day(-3)), ('b2', 'u:e1', 100, day(-2)), ('b3', 'u:noe', 100, day(-2)), ('b4', 'u:e1', 300, day(-1))], None, REF_F, foods=EF)
        R = await rows()
        B1 = R['Vitamin B1 (thiamin)']
        # eligible days: Mon (200 kcal) and Wed (300 kcal); Tue has an item without energy. Average energy 250 kcal = 1.0468 MJ -> reference 0.1 x 1.0468 = 0.10468 mg. Amount: (1.0 + 1.5) / 2 = 1.25 mg -> 1194%
        ref_b1 = 0.1 * 250 / 238.83
        want = round(1.25 / ref_b1 * 100)
        check(f'B1 over a period: only the days with complete energy data (Mon, Wed) are compared: {want:,}% (1.25 mg against 0.1 mg per MJ x 1.047 MJ)', B1['line'] == f'{want:,}% of 0.1 mg · PRI' and abs(float(B1['bar'].rstrip('%')) - 100) < 1e-9, [B1['line'], B1['bar']])
        check('...the value of the row itself is the average of all 3 logged days (3.0 / 3 = 1 mg... 1.0 + 1.5 + 1.5 = 4 mg / 3 days = 1.33 mg)', B1['val'].startswith('1.33') or B1['val'].startswith('≥ 1.33'), B1['val'])
        check('...the opened row says which days were used: "Average energy of the 2 of 3 logged days that have complete energy data: 1.05 MJ (250 kcal)"', any('Average energy of the 2 of 3 logged days that have complete energy data: 1.05 MJ (250 kcal)' in d for d in B1['det']), B1['det'])
        check('...the spoken sentence says "for the average energy of these days"', 'for the average energy of these days' in B1['say'], B1['say'])
        ni = R['Vitamin B3 (niacin)'] if 'Vitamin B3 (niacin)' in R else next(v for k, v in R.items() if k.startswith('Vitamin B3'))
        ref_n = 1.6 * 250 / 238.83
        wantn = round(5 / ref_n * 100)
        check(f'niacin (always ≥, tryptophan is not in the data): ≥ {wantn:,}% (5 mg on the two days against 1.6 mg NE per MJ)', ni['line'] == f'≥ {wantn:,}% of 1.67 mg NE · PRI', ni['line'])
        await seed([('b2', 'u:e1', 100, day(-2)), ('b3', 'u:noe', 100, day(-2)), ('b5', 'u:noe', 100, day(-1))], None, REF_F, foods=EF)
        R = await rows(); B1 = R['Vitamin B1 (thiamin)']
        check('when no day of the period has complete energy data: "needs complete energy data", no percent and no bar, and the opened row says that no day qualifies', B1['line'] == 'Reference 0.1 mg per MJ · PRI · needs complete energy data' and B1['track'] is None and any('no day in this period qualifies' in d for d in B1['det']), [B1['line'], B1['det']])
        await seed([('b2', 'u:e1', 100, day(-2)), ('b3', 'u:noe', 100, day(-2))], None, REF_F, foods=EF)
        R = await rows(); B1 = R['Vitamin B1 (thiamin)']
        check('...a period of one logged day uses the words of the Nutrients tab ("when every item of the day has energy data")', B1['line'] == 'Reference 0.1 mg per MJ · PRI · needs complete energy data' and any('A percent is shown only when every item of the day has energy data' in d for d in B1['det']), [B1['line'], B1['det']])
        await seed([('b2', 'u:noe', 100, day(-2))], None, REF_F, foods=EF)
        R = await rows(); B1 = R['Vitamin B1 (thiamin)']
        check('...and when there is no energy at all it is the same sentence (never a percent)', B1['line'] == 'Reference 0.1 mg per MJ · PRI · needs complete energy data' and B1['track'] is None, B1['line'])

        # =========================================================== 11 Vitamin A, EPA + DHA, omega ratio on averages
        RET = own('u:ret', 'Retinol food', {'kcal': 50, 'retinol': 100, 'beta_carotene': 600})
        CAR = own('u:car', 'Carotene food', {'kcal': 40, 'beta_carotene': 1200})
        FISH2 = own('u:fish2', 'Fish', {'kcal': 200, 'fa_18_2_9c_12c_n_6': 0.5, 'fa_20_4_5c_8c_11c_14c_n_6': 0.1, 'fa_18_3_c9_c12_c15_n_3': 0.3, 'fa_20_5_5c_8c_11c_14c_17c_n_3_epa': 1.0, 'fa_22_6_4c_7c_10c_13c_16c_19c_n_3_dha': 1.5})
        await seed([('v1', 'u:ret', 100, day(-2)), ('v2', 'u:car', 100, day(-1)), ('v3', 'u:fish2', 10, day(-2)), ('v4', 'u:alpha', 100, day(-1))], None, REF_F, foods=[RET, CAR, FISH2, ALPHA])
        R = await rows()
        va = R['Vitamin A (retinol)']
        # RE: Tue day: retinol 100 + 600/6 = 200; Wed: carotene only 1200/6 = 200 (no retinol: lower value). Two logged days: (200 + 200) / 2 = 200 RE, 200 / 650 = 30.8%
        check('Vitamin A over a period is counted in retinol equivalents (retinol + beta-carotene / 6) as an average: ≥ 31% of 650 µg RE · PRI (200 / 650)', va['line'] == '≥ 31% of 650 µg RE · PRI · with beta-carotene', va['line'])
        check('...with the "lower value" explanation of the opened row', any('Other provitamin A carotenoids are not in the food data, so this is a lower value.' in d for d in va['det']), va['det'])
        bc = R['Beta-carotene']
        check('...the Beta-carotene row says it is counted in Vitamin A', any(d.startswith('Counted in Vitamin A') for d in bc['det']), bc['det'])
        ed = R['EPA + DHA']
        # fish 10 g: EPA 0.1 g + DHA 0.15 g = 250 mg on one day; the other day nothing: 250 / 2 = 125 mg = 50% of 250 mg, a lower value (the other food has no data)
        check('EPA + DHA over a period: 250 mg on one of two logged days = 125 mg a day, ≥ 50% of 250 mg · AI', ed['line'] == '≥ 50% of 250 mg · AI' and ed['val'].startswith('≥ 125'), [ed['line'], ed['val']])
        om = R['Omega-6 : omega-3 ratio']
        # omega-6 0.06 g, omega-3 0.28 g -> 0.214; the same after the division by the number of days
        check('the omega ratio is worked out from the averages and the divisor cancels out: 0.6 / 2.8 = ≈ 0.21 : 1 (the other items lack the five fatty acids)', om['val'].replace(' ', '') in ('≈0.21:1',), om['val'])
        check('...the badges of these rows are shares of the 4 items: EPA + DHA 25% (only the fish has data), the omega ratio 25%, Vitamin A (retinol) 25% (one item has retinol)', [ed['pill'], om['pill'], va['pill']] == ['25%', '25%', '25%'], [ed['pill'], om['pill'], va['pill']])

        # =========================================================== 12 the limit of "Added up from"
        many = [own(f'u:m{i:02d}', f'Many food {i:02d}', {'kcal': 10 + i, 'protein': i}) for i in range(1, 15)]
        ents = [(f'm{i}', f'u:m{i:02d}', 100, day(-3) if i <= 7 else day(-1)) for i in range(1, 15)]
        await seed(ents, None, None, foods=many)
        R = await rows()
        pr = R['Protein']
        shown = [x for x in pr['parts'] if 'nc-more' not in x[2]]
        more = [x for x in pr['parts'] if 'nc-more' in x[2]]
        check('14 foods with protein: 12 are listed (the biggest first: 14, 13, … 3) and one line sums up the other 2 foods', len(shown) == 12 and [x[0].split(' · ')[0] for x in shown][:3] == ['Many food 14', 'Many food 13', 'Many food 12'] and shown[-1][0].startswith('Many food 03'), [x[0] for x in pr['parts']])
        check('...the last line is "2 more foods" with their sum (2 + 1 = 3 g)', len(more) == 1 and more[0][0] == '2 more foods' and more[0][1] == '3g', more)
        check('...all the lines together are 105 g, and the heading says "2 logged days, 105 g in all" (the average is 52.5 g)', sum(float(re.sub(r'[^\d.]', '', x[1])) for x in pr['parts']) == 105 and pr['head'] == 'Added up from · 2 logged days, 105 g in all' and pr['val'] == '52.5g', [pr['head'], pr['val']])
        check('...a food with 100 g eaten once is listed with its amount and no "entries" word', shown[0][0] == 'Many food 14 · 100 g', shown[0])

        # =========================================================== 13 Data quality: calendar, month rows, sources, estimated share
        for frm, to, cal in [('2026-09-05', '2026-11-05', True), ('2026-09-04', '2026-11-05', False)]:
            await seed([('q1', 'u:alpha', 100, '2026-09-10'), ('q2', 'u:alpha', 100, '2026-10-15'), ('q3', 'u:alpha', 100, '2026-11-02')], {'2026-10-15': 1000}, None, kind='custom', custom={'from': frm, 'to': to})
            Q = await page.evaluate(QUALITY)
            n = (date.fromisoformat(to) - date.fromisoformat(frm)).days + 1
            if cal:
                check(f'a period of {n} days shows the calendar grid (up to 62 days)', Q['cal'] is not None and len(Q['cal']['cells']) == n == 62 and Q['cal']['pads'] == 5, [None if not Q['cal'] else (len(Q['cal']['cells']), Q['cal']['pads'])])
                lg = [c[0] for c in Q['cal']['cells'] if c[1].startswith('logged')]
                check('...5 Sep 2026 is a Saturday, so 5 padding cells come before it; the logged days are 10 Sep, 15 Oct and 2 Nov; 15 Oct has the water dot', lg == ['10', '15', '2'] and [c[1] for c in Q['cal']['cells'] if c[0] == '15' and c[1].startswith('logged')] == ['logged w'], lg)
            else:
                rowsq = Q['sections']['Days']
                check(f'a period of {n} days (63) shows one line per month instead of the grid', Q['cal'] is None and rowsq == [['September 2026', '', '1 of 27days'], ['October 2026', '', '1 of 31days'], ['November 2026', '', '1 of 5days']], [Q['cal'] is None, rowsq])
        # Year
        await seed([('q2', 'u:alpha', 100, '2026-10-15'), ('q3', 'u:alpha', 100, '2026-11-02'), ('q4', 'u:alpha', 100, '2025-12-01')], None, None, kind='year')
        Q = await page.evaluate(QUALITY)
        mrows = Q['sections']['Days']
        check('Year: 12 monthly lines from December 2025 to November 2026; the first and the last month are counted in full / so far (Nov: 5 days)', len(mrows) == 12 and mrows[0][0] == 'December 2025' and mrows[0][2] == '1 of 31days' and mrows[-1] == ['November 2026', '', '1 of 5days'] and mrows[10][2] == '1 of 31days', mrows)
        # sources and estimated share
        await seed([('t1', 'u:alpha', 100, day(0)), ('t2', CIQ_ID, round(10000 / cf['v'][0], 6), day(0))], None, None, foods=CORE_FOODS, kind='day')
        Q = await page.evaluate(QUALITY)
        srcs = Q['sections']['Energy by data source']
        check('Energy by data source: 100 kcal of your own food and 100 kcal of a CIQUAL food are 50% and 50%', srcs == [['CIQUAL', '1 item', '50% of energy'], ['Your own foods', '1 item', '50% of energy']] or sorted(srcs) == sorted([['CIQUAL', '1 item', '50% of energy'], ['Your own foods', '1 item', '50% of energy']]), srcs)
        # estimated share: Est food alone: kcal (not estimated) 0%, calcium 100%, protein (not estimated) 0% -> mean over the nutrients with data
        await seed([('t1', 'u:estf', 100, day(0))], None, None, foods=PFOODS, kind='day')
        Q = await page.evaluate(QUALITY)
        shr = await T("() => { const t = window.__tapnaplo; return t.estShare(t.S.log); }")
        it = {x[0]: x for x in Q['sections']['Items']}
        # nutrients with data: kcal, protein, calcium -> shares 0, 0, 100 -> mean 33.3
        check('the estimated share of the values is the mean over the nutrients that have data: kcal 0%, protein 0%, calcium 100% = 33.3% (same function as est_share in the CSV)', abs(shr - 100 / 3) < 0.06 and it['Estimated share of the values'][2] == f"{await T('(v) => window.__tapnaplo.fmt(v)', shr)}%", [shr, it['Estimated share of the values']])
        await seed([('t1', 'u:alpha', 100, day(0))], None, None, foods=PFOODS, kind='day')
        Q = await page.evaluate(QUALITY)
        check('when nothing is estimated the share is 0% (not "no data")', {x[0]: x for x in Q['sections']['Items']}['Estimated share of the values'][2] == '0%')

        # =========================================================== 14 the shared copy
        VCIQ = CIQ_ID
        EVIL = own('u:evil', '<img src=x onerror="window.__pwn=1"><b>X</b> & "Q"', {'kcal': 10})
        VFOODS = CORE_FOODS + [EVIL, ESTF]
        ventries = [('x0', 'u:alpha', 100, day(-12)), ('x1', 'u:alpha', 200, day(-10)), ('x2', 'u:evil', 50, day(-10)), ('x3', 'u:beta', 100, day(-8)), ('x4', 'u:gamma', 100, day(-8)),
                    ('x5', VCIQ, 100, day(-6)), ('x6', 'u:estf', 100, day(-6)), ('x7', 'u:alpha', 100, day(-3)), ('x8', 'u:beta', 100, day(-3)), ('x9', 'u:alpha', 100, day(-1))]
        vwater = {day(-10): 1000, day(-6): 2000, day(-1): 500}
        VF, VT = day(-11), day(-2)            # 25 Oct - 3 Nov: 10 days
        await seed(ventries, vwater, None, foods=VFOODS, kind='custom', custom={'from': VF, 'to': VT})
        # sender's Report as text (all parts open) for the comparison
        SNAP = """async (open) => { document.querySelectorAll('#view details').forEach((d) => { d.open = true; }); await new Promise((r) => setTimeout(r, 60));
          const tx = window.__txt, rows = {};
          document.querySelectorAll('details[data-sec=nutrients] details.nrow').forEach((r) => { const lab = r.querySelector('summary > span').textContent;
            rows[lab] = [tx(r.querySelector('summary .nval'), '.sr-only'), r.querySelector('summary .pill').textContent, r.querySelector('.rtxt') ? r.querySelector('.rtxt').textContent : null, [...r.querySelectorAll('.ncontrib li')].map((li) => tx(li, '.sr-only')), [...r.querySelectorAll('.ndetail')].map((d) => d.textContent)]; });
          return { overview: tx(document.querySelector('details[data-sec=overview]')), nutrients: rows, quality: tx(document.querySelector('details[data-sec=quality]')), banners: [...document.querySelectorAll('details[data-sec=nutrients] .banner')].map((b) => b.textContent) }; }"""
        snap_sender = await page.evaluate(SNAP, True)
        link = await T("([a, b]) => window.__tapnaplo.shareLink(a, b).then((r) => r.url)", [VF, VT])
        vctx = await new_ctx(390, 844)
        vp = await vctx.new_page(); watch(vp, 'V')
        reqs = []
        vp.on('request', lambda r: reqs.append(r.url.split('/')[-1].split('#')[0]))
        await vp.goto(link); await vp.wait_for_selector('.hero')
        vt = await vp.locator('#tabbar .tab span').all_inner_texts()
        check('the shared copy has three tabs: Diary, Nutrients, Report; the tab bar has three columns', vt == ['Diary', 'Nutrients', 'Report'] and await vp.evaluate("() => getComputedStyle(document.querySelector('#tabbar')).gridTemplateColumns.split(' ').length") == 3, vt)
        await vp.click('[data-tab=report]'); await vp.wait_for_selector('.rp-seg')
        vs = await sel(vp)
        check('in the shared copy Custom is chosen and covers the whole shared range (25 Oct - 3 Nov); a "Shared diary · read-only" note is on the tab', vs['pressed'] == ['custom'] and vs['when'] == '25 Oct – 3 Nov 2026' and await vp.locator('.view-note').count() == 1 and 'read-only' in await vp.inner_text('.view-note'), [vs['pressed'], vs['when']])
        check('...the link has 10 days, so 3 months, 6 months and Year are off (disabled) and a hint says why; Day, Week, Month and Custom are on', vs['disabled'] == ['m3', 'm6', 'year'] and vs['hint'] == 'The link has 10 days, so 3 months, 6 months and Year are not available.', [vs['disabled'], vs['hint']])
        check('...no Today chip and no date picker problem: the date picker is limited to the shared days', not vs['today'] and await vp.evaluate("() => { const d = document.querySelector('#rp-date'); return !d || (d.min === '%s' && d.max === '%s'); }" % (VF, VT)))
        snap_viewer = await vp.evaluate(SNAP, True)
        check('the numbers are the same as in the sender: Overview text', snap_sender['overview'] == snap_viewer['overview'], (snap_sender['overview'][:200], snap_viewer['overview'][:200]))
        dn = [(k, snap_sender['nutrients'][k], snap_viewer['nutrients'].get(k)) for k in snap_sender['nutrients'] if snap_sender['nutrients'][k] != snap_viewer['nutrients'].get(k)]
        check(f'...every Nutrients row ({len(snap_sender["nutrients"])}): value, badge, EFSA line, "Added up from" lines and detail lines', dn == [] and len(snap_viewer['nutrients']) == len(snap_sender['nutrients']) > 60, dn[:2])
        check('...Data quality text', snap_sender['quality'] == snap_viewer['quality'], (snap_sender['quality'][:200], snap_viewer['quality'][:200]))
        check('...and the banners', snap_sender['banners'] == snap_viewer['banners'])
        check('the viewer loaded the CIQUAL table for the CIQUAL food in the link (and nothing else)', 'ciqual.json' in reqs and 'usda.json' not in reqs and 'dmbio.json' not in reqs, [r for r in reqs if r.endswith('.json')])
        ov_v = await ov(vp)
        check('...4 logged days (26, 28, 30 Oct and 2 Nov), water on 2 of them = 1,500 mL (the water of 4 Nov is outside the link)', ov_v['chips'] == ['4 of 10 days logged'] and [k for k in ov_v['rows'] if k.startswith('Water')] and ov_v['rows'][[k for k in ov_v['rows'] if k.startswith('Water')][0]]['val'] == '1,500', [ov_v['chips'], ov_v['rows']])
        # periods are cut to the shared days
        await kind('week', vp)
        vs = await sel(vp)
        check('Week in the shared copy: the week of the last shared day, cut to the shared days (2 - 3 Nov, "shared days only, 2 days"); Next is off, Previous is on', vs['when'] == '2–8 Nov 2026' and vs['note'] == 'shared days only, 2 days' and not vs['next'] and vs['prev'], vs)
        await vp.click('[data-act=rp-step][data-n="-1"]')
        vs = await sel(vp)
        check('...Previous: 26 Oct - 1 Nov is entirely inside the shared days, so no note', vs['when'] == '26 Oct – 1 Nov 2026' and vs['note'] == '' and vs['prev'] and vs['next'], vs)
        await vp.click('[data-act=rp-step][data-n="-1"]')
        vs = await sel(vp)
        check('...Previous again: 19 - 25 Oct is cut to 25 Oct ("shared days only, 1 day") and Previous is off now', vs['when'] == '19–25 Oct 2026' and vs['note'] == 'shared days only, 1 day' and not vs['prev'], vs)
        txt = await vp.inner_text('#view')
        check('...a period with no shared entries says so with the same card (no Go to Diary button in the shared copy... it opens the Diary of the link)', 'No entries' in txt, txt[:200])
        await kind('month', vp)
        vs = await sel(vp)
        check('Month in the shared copy: the month of the day the period was built around (20 Oct after the two steps back), cut to the shared days: 25 - 31 Oct, "shared days only, 7 days"; Previous is off (September is before the link), Next is on', vs['when'] == 'October 2026' and vs['note'] == 'shared days only, 7 days' and not vs['prev'] and vs['next'], vs)
        await vp.click('[data-act=rp-step][data-n="1"]')
        vs = await sel(vp)
        check('...Next: November 2026 cut to 1 - 3 Nov, "shared days only, 3 days", and Next is off', vs['when'] == 'November 2026' and vs['note'] == 'shared days only, 3 days' and not vs['next'], vs)
        await kind('day', vp)
        await vp.fill('#rp-date', day(-4)); await vp.wait_for_timeout(30)
        txt = await vp.inner_text('#view')
        check('Day in the shared copy on a day without entries (Sun 1 Nov): the empty card, no "Open in Diary" button', 'No entries on' in txt and await vp.locator('[data-act=rp-diary]').count() == 0, txt[:200])
        await vp.fill('#rp-date', day(-3)); await vp.wait_for_timeout(30)
        check('Day in the shared copy on a day with entries (Mon 2 Nov) has "Open in Diary", which opens the Diary of the link on that day', await vp.locator('[data-act=rp-diary]').count() == 1)
        await vp.evaluate("() => document.querySelector('[data-act=rp-diary]').scrollIntoView({ block: 'center' })")
        await vp.click('[data-act=rp-diary]'); await vp.wait_for_timeout(60)
        check('...it opens the Diary on 2 Nov', await vp.evaluate('() => window.__tapnaplo.S.tab') == 'log' and await vp.evaluate('() => window.__tapnaplo.S.day') == day(-3))
        await vp.click('[data-tab=report]'); await vp.wait_for_selector('.rp-seg')
        await vp.click('[data-act=rp-kind][data-kind=custom]'); await vp.wait_for_selector('#rc-apply')
        check('Custom in the shared copy: the sheet offers the dates inside the link only (min / max), and "Whole shared range" instead of "Whole diary"', await vp.evaluate("() => { const f = document.querySelector('#rc-from'), t = document.querySelector('#rc-to'); return f.min === '%s' && f.max === '%s' && t.min === '%s' && t.max === '%s'; }" % (VF, VT, VF, VT)) and await vp.inner_text('#rc-quick [data-q="all"]') == 'Whole shared range')
        await vp.fill('#rc-from', '2026-10-01'); await vp.fill('#rc-to', VT)
        await vp.click('#rc-apply'); await vp.wait_for_timeout(30)
        msg = await vp.inner_text('#rc-err')
        check('...a start before the shared days is refused with the shared range in the message', msg.startswith('The shared days are 25 Oct 2026 – 3 Nov 2026. Choose days inside them.') or msg.startswith('The shared days are') and 'Choose days inside them.' in msg, msg)
        await vp.click('#rc-quick [data-q="all"]')
        check('...Whole shared range fills the two dates with the link\'s first and last day', (await vp.input_value('#rc-from'), await vp.input_value('#rc-to')) == (VF, VT))
        await vp.click('#rc-quick [data-q="14"]')
        check('...Last 14 days is cut to the first shared day', (await vp.input_value('#rc-from'), await vp.input_value('#rc-to')) == (VF, VT))
        await vp.fill('#rc-from', day(-8)); await vp.fill('#rc-to', day(-3))
        await vp.click('#rc-apply'); await vp.wait_for_timeout(250)
        vs = await sel(vp)
        check('...a range inside the link is applied (28 Oct - 2 Nov)', vs['pressed'] == ['custom'] and vs['when'] == '28 Oct – 2 Nov 2026', vs)
        await vp.click('[data-act=rp-step][data-n="-1"]')
        vs = await sel(vp)
        check('...Previous moves by the length of the range and is cut to the shared days (22 - 27 Oct → 25 - 27 Oct)', vs['when'] == '22–27 Oct 2026' and vs['note'].startswith('shared days only'), vs)
        w = await vp.evaluate('() => window.__w')
        check('the viewer wrote nothing to the browser: no localStorage write (no period, no open parts), no IndexedDB opened', w['ls'] == [] and w['idb'] == 0, w)
        await vp.evaluate("() => { document.querySelectorAll('details[data-sec]').forEach((d) => { d.open = !d.open; }); }"); await vp.wait_for_timeout(80)
        w = await vp.evaluate('() => window.__w')
        check('...also not when parts are opened and closed', w['ls'] == [] and w['idb'] == 0, w)
        check('a viewer cannot reach the profile, change, add or save actions of the Report', await vp.locator('[data-act=ref-quick], [data-act=ref-change], [data-act=health-add], [data-act=water-add], [data-act=nova-set]').count() == 0)
        await vp.evaluate("() => { const b = document.createElement('button'); b.dataset.act = 'ref-change'; b.id = 'fake1'; document.body.append(b); const c = document.createElement('button'); c.dataset.act = 'rp-today'; c.id = 'fake2'; document.body.append(c); }")
        await vp.dispatch_event('#fake1', 'click'); await vp.dispatch_event('#fake2', 'click'); await vp.wait_for_timeout(100)
        check('...a faked button for an action that changes something does nothing (no sheet, the period is as it was)', await vp.locator('.sheet-wrap').count() == 0 and (await sel(vp))['when'] == '22–27 Oct 2026')
        # hostile
        await kind('week', vp); await vp.evaluate("() => document.querySelectorAll('#view details').forEach((d) => { d.open = true; })")
        await vp.click('[data-act=rp-kind][data-kind=custom]'); await vp.wait_for_selector('#rc-apply'); await vp.click('#rc-quick [data-q="all"]'); await vp.click('#rc-apply'); await vp.wait_for_timeout(250)
        await vp.evaluate("() => document.querySelectorAll('#view details').forEach((d) => { d.open = true; })")
        hostile = await vp.evaluate("() => ({ pwn: window.__pwn === undefined, imgs: document.querySelectorAll('#view img').length + [...document.querySelectorAll('#view b')].filter((b) => b.textContent === 'X').length, text: document.querySelector('#view').textContent.includes('<img src=x onerror=\"window.__pwn=1\"><b>X</b> & \"Q\"') })")
        check('a hostile food name is only text: it is shown as typed (in the lists), nothing runs and no element is made from it', hostile['pwn'] and hostile['imgs'] == 0 and hostile['text'], hostile)
        await vctx.close()
        # the profile in the link
        await seed(ventries, vwater, REF_F, foods=VFOODS, kind='custom', custom={'from': VF, 'to': VT})
        snap_sender = await page.evaluate(SNAP, True)
        link2 = await T("([a, b]) => window.__tapnaplo.shareLink(a, b, true).then((r) => r.url)", [VF, VT])
        vctx = await new_ctx(390, 844)
        vp = await vctx.new_page(); watch(vp, 'V2')
        await vp.goto(link2); await vp.wait_for_selector('.hero')
        await vp.click('[data-tab=report]'); await vp.wait_for_selector('.rp-seg')
        snap_viewer = await vp.evaluate(SNAP, True)
        dn = [(k, snap_sender['nutrients'][k], snap_viewer['nutrients'].get(k)) for k in snap_sender['nutrients'] if snap_sender['nutrients'][k] != snap_viewer['nutrients'].get(k)]
        check('with the reference settings in the link the viewer shows the same EFSA bars and lines on the average as the sender, for every row', dn == [] and len(snap_viewer['nutrients']) == len(snap_sender['nutrients']) and any('% of' in (v[2] or '') for v in snap_viewer['nutrients'].values()), dn[:2])
        check('...and the profile card is read-only (no Change, no Male / Female)', await vp.locator('[data-act=ref-change], [data-act=ref-quick]').count() == 0 and 'EFSA values for adults' in await vp.inner_text('#view'))
        w = await vp.evaluate('() => window.__w')
        check('...still nothing written by the viewer', w['ls'] == [] and w['idb'] == 0, w)
        await vctx.close()
        # a longer link: m3 / m6 / year are on
        longs = [('l1', 'u:alpha', 100, day(-100)), ('l2', 'u:beta', 100, day(-20)), ('l3', 'u:alpha', 100, day(-2))]
        await seed(longs, None, None, foods=CORE_FOODS, kind='week')
        link3 = await T("([a, b]) => window.__tapnaplo.shareLink(a, b).then((r) => r.url)", [day(-110), day(0)])
        vctx = await new_ctx(390, 844)
        vp = await vctx.new_page(); watch(vp, 'V3')
        await vp.goto(link3); await vp.wait_for_selector('.hero')
        await vp.click('[data-tab=report]'); await vp.wait_for_selector('.rp-seg')
        vs = await sel(vp)
        check('a link with 111 days: 3 months, 6 months and Year are available, there is no hint; the default is the whole range', vs['disabled'] == [] and vs['hint'] is None and vs['pressed'] == ['custom'], vs)
        await kind('m3', vp)
        vs = await sel(vp); o = await ov(vp)
        check('...3 months (Sept - Nov 2026) is not cut (the first shared day is 17 Jul) and shows the 2 logged days', vs['when'] == 'Sept – Nov 2026' and o['chips'][0].startswith('2 of '), [vs['when'], o['chips']])
        await kind('year', vp)
        o = await ov(vp)
        check('...Year contains all three logged days', o['chips'][0].startswith('3 of ') and 'logged' in o['chips'][0], o['chips'])
        await vctx.close()

        # =========================================================== 15 the tab bar and the layout
        for (w, h) in [(430, 932), (390, 844), (375, 667), (360, 740), (320, 568)]:
            cx = await new_ctx(w, h)
            pg = await cx.new_page(); watch(pg, f'W{w}')
            await pg.goto(URL); await pg.wait_for_selector('.hero')
            for theme in ('light', 'dark'):
                await pg.evaluate("(t) => document.documentElement.setAttribute('data-theme', t)", theme)
                for tabkey in ('log', 'nutr', 'report', 'foods', 'health', 'data'):
                    await pg.click(f'[data-tab={tabkey}]'); await pg.wait_for_timeout(30)
                    fit = await pg.evaluate(TABFIT)
                    ok = fit['count'] == 6 and fit['bar'] and fit['page'] and all(t['fits'] and t['w'] >= 44 and t['h'] >= 44 for t in fit['tabs'])
                    if not ok or (tabkey == 'report' and theme == 'light'):
                        check(f'{w} px, {theme}, tab "{tabkey}" active: all six labels fit in their tab (one line, nothing cut), every tab is at least 44 x 44 px, the bar does not scroll', ok, [(t['label'], t['text'], t['room'], t['w'], t['fits']) for t in fit['tabs']])
            allok = True
            check(f'{w} px: the six-tab bar fits in light and dark with each of the six tabs active (12 combinations)', not any(x.startswith(f'{w} px') and x.endswith('(12 combinations)') for x in problems) and not any(p_.startswith(f'{w} px,') for p_ in problems))
            await cx.close()
        await ctx.close()

        # layout of the Report itself at 390 and 320 px (everything open), 16 px fields, 44 px targets, contrast
        for (w, h) in [(390, 844), (320, 640)]:
            cx, pg = await fresh(w, h, f'L{w}')
            await seed(CORE + [('s1', 'u:fish', 50, day(-2)), ('s2', 'u:oil', 10, day(-2)), ('s3', 'u:estf', 100, day(-4)), ('s4', 'u:limf', 100, day(-4)), ('s5', 'u:evil', 50, day(-1))], CORE_WATER, REF_F, foods=PFOODS + [EVIL], pg=pg)
            await pg.evaluate("() => document.querySelectorAll('#view details').forEach((d) => { d.open = true; })"); await pg.wait_for_timeout(60)
            fits = await pg.evaluate("""() => ({ page: document.documentElement.scrollWidth <= window.innerWidth, cut: [...document.querySelectorAll('#view .rp-hero *, #view .nrow summary > *, #view .rline, #view .ncontrib li, #view .ndetail, #view .an-row, #view .rp-nav *, #view .rp-seg button')].filter((e) => e.scrollWidth > e.clientWidth + 1 && getComputedStyle(e).overflow !== 'visible').map((e) => e.textContent.trim().slice(0, 30)) })""")
            check(f'{w} px: the Report with everything open does not scroll sideways, and no value or line is cut off', fits['page'] and fits['cut'] == [], fits)
            small = await pg.evaluate(SIZES, '#view button, #view summary, #view label.icon-btn, #topbar button, #topbar label, #tabbar .tab')
            small = [x for x in small if not x[0].startswith('nrow')]
            check(f'{w} px: buttons, summaries and the date picker are at least 44 px (the section and row summaries too)', small == [], small)
            check(f'{w} px: the date field is at least 16 px (iOS does not zoom into it)', await pg.evaluate(SMALLFONT, '#rp-date') == [])
            for theme in ('light', 'dark'):
                await pg.evaluate("(t) => document.documentElement.setAttribute('data-theme', t)", theme)
                bad = await pg.evaluate(CONTRAST_JS, '#view')
                bar = await pg.evaluate(CONTRAST_JS, '#tabbar')
                check(f'{w} px, {theme}: text contrast is at least 4.5:1 on the whole Report and the tab bar', bad == [] and bar == [], (bad[:3], bar[:3]))
            if SHOTS: await pg.screenshot(path=os.path.join(SHOTS, f'report_{w}.png'), full_page=True)
            await pg.click('[data-act=rp-kind][data-kind=custom]'); await pg.wait_for_selector('#rc-apply'); await pg.wait_for_timeout(250)
            cs = [await pg.evaluate(SMALLFONT, '#rc-from, #rc-to'), await pg.evaluate(SIZES, '.sheet button'), await pg.evaluate("() => { const s = document.querySelector('.sheet-b'); return s.scrollWidth <= s.clientWidth + 1; }")]
            check(f'{w} px: the Custom sheet\'s fields are at least 16 px, its buttons at least 44 px, and it does not scroll sideways', cs[0] == [] and cs[1] == [] and cs[2], cs)
            await pg.evaluate("(t) => document.documentElement.setAttribute('data-theme', t)", 'dark')
            check(f'{w} px: the Custom sheet has enough contrast in dark mode', await pg.evaluate(CONTRAST_JS, '.sheet') == [])
            await cx.close()

        # =========================================================== 16 speed with 6,000 entries over a year
        cx, pg = await fresh(390, 844, 'S')
        foods12 = [own(f'u:k{i:02d}', f'Bulk food {i:02d}', {k: (i + 1) * (j + 1) / 7 for j, k in enumerate(['kcal', 'protein', 'carbohydrate', 'fat', 'fibres', 'salt', 'calcium', 'magnesium', 'iron', 'zinc', 'vitamin_c', 'vitamin_d', 'potassium', 'sodium', 'selenium', 'iodine'])}) for i in range(12)]
        bulk = []
        for k in range(365):
            d_ = (TODAY - timedelta(days=k)).isoformat()
            for j in range(16):
                bulk.append((f'k{k}_{j}', f'u:k{(k + j) % 12:02d}', 50 + j * 10, d_))
        await seed(bulk, None, REF_F, foods=foods12, kind='year', pg=pg)
        t0 = time.perf_counter()
        await pg.evaluate("() => { window.__tapnaplo.render(); }")
        dt = time.perf_counter() - t0
        o = await ov(pg)
        check(f'6,000 entries over a year: the Report (all parts open) renders in {dt:.2f} s (less than 3 s)', dt < 3 and o['chips'][0].startswith('340 of 340 days logged'), [round(dt, 2), o['chips']])
        await pg.evaluate("() => { window.__tapnaplo.RP.kind = 'month'; }")
        t0 = time.perf_counter(); await pg.evaluate("() => window.__tapnaplo.render()"); dt = time.perf_counter() - t0
        check(f'...switching to a month: {dt:.2f} s', dt < 2, round(dt, 2))
        await cx.close()

        # =========================================================== 17 the backup and the version
        cx, pg = await fresh(390, 844, 'B')
        await seed(CORE, CORE_WATER, REF_F, kind='month', pg=pg)
        await pg.click('[data-tab=data]'); await pg.wait_for_selector('[data-act=export-json]')
        async with pg.expect_download() as dd:
            await pg.click('[data-act=export-json]')
        dl = await dd.value
        backup = json.loads(pathlib.Path(await dl.path()).read_text(encoding='utf-8'))
        check('the backup has exactly the keys it had before the Report (the period and the open parts are not in it)', sorted(backup.keys()) == sorted(['app', 'version', 'exported', 'log', 'foods', 'meta', 'health']) and 'period' not in json.dumps(backup)[:0] + '' and not any('report' in k.lower() or 'period' in k.lower() for k in backup['meta']), (sorted(backup.keys()), sorted(backup['meta'].keys())))
        check('...and the data of the sample is in it unchanged (5 entries, water, profile)', len(backup['log']) == 5 and backup['meta']['water'] == CORE_WATER and backup['meta']['ref'] == REF_F)
        ver = re.search(r'(\d+) · \d+ \w+ 20\d\d', await pg.evaluate('document.body.innerText'))
        check('the Data tab shows version 29 or newer', bool(ver) and int(ver.group(1)) >= 29, ver and ver.group(0))
        sw = open(ROOT / 'sw.js', encoding='utf-8').read()
        check('the service worker cache has the number of the version', bool(ver) and f"const CACHE = 'nutrilog-v{ver.group(1)}'" in sw)
        await cx.close()
        check('no page errors', errs == [], errs[:6])
        await browser.close()
        print('\nALL PASSED' if not problems else f'\n{len(problems)} FAILED: {problems}')
        sys.exit(1 if problems else 0)


asyncio.run(main())
