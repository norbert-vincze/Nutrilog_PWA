"""Report tab, Meals and weekdays, Foods and Food processing (NOVA) over time (version 31). Run with the web server on port 8765 (see CLAUDE.md).

Three new sections of the Report, between Nutrients and Data quality:
- "Meals and weekdays": the energy of each meal as an average per logged day and as a share (a meal with no entries on a logged day counts as 0 kcal, items without energy data never do:
  "≥" or "no energy data"), the average energy of each weekday (Monday first) with the number of logged days, and Monday-Friday against Saturday-Sunday.
- "Foods": the biggest sources (top 10 and "N more foods") of the measure that is also used by the Trend, each food as all its entries of the period added up, with the share of the sum of
  the foods that have data, the days and the entries; "No data for ..." is named, never counted as 0; water and the omega ratio have no list of foods.
- "Food processing (NOVA)": the split of the energy of the whole period (all items together, not an average of daily percents) and one bar per day, week or month with the share of NOVA 4.
The clock of the browser is fixed to Thursday 5 Nov 2026, 12:00 (Budapest), so every date below is exact; every number is worked out by hand in the comments.

Covers: the order of the sections, closed by default and remembered, a hand-calculated week (meals, weekdays, foods for Energy and Protein, NOVA and its day bars and table), the Day period
(no weekday part, no "Over time"), the measure that is shared with the Trend (also when there is no Trend), water / ratio / no data, "<x" values and estimates (~, a range, a food without a share),
an entry with an unknown meal, an entry whose food is not loaded, "<1%", week and month bars, the sums (the meals add up to the Overview, the NOVA shares to 100), the shared copy (same
numbers as the sender, nothing written), a hostile food name, 44 / 16 px, contrast of text and bars in light and dark, 390 and 320 px, speed with 6,000 entries, the backup and the version."""
import asyncio, json, os, pathlib, re, sys, time
from datetime import date, timedelta
from playwright.async_api import async_playwright
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_ai_import import CONTRAST_JS

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = 'http://127.0.0.1:8765/index.html'
SHOTS = os.environ.get('SHOTS', '')
NOW = '2026-11-05T12:00:00+01:00'           # Thursday
TODAY = date(2026, 11, 5)
ALL3 = {'overview': True, 'meals': True, 'foods': True, 'nova': True, 'novatable': True}


def day(n):
    return (TODAY + timedelta(days=n)).isoformat()


INIT = """
window.__txt = (el, skip) => { let s = ''; const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  while (w.nextNode()) { const n = w.currentNode; if (skip && n.parentElement.closest(skip)) continue; s += n.textContent; }
  return s.replace(/\\s+/g, ' ').trim(); };
window.__tx = (el) => (el ? el.textContent.replace(/\\s+/g, ' ').trim() : null);
window.__rows = (d) => [...d.querySelectorAll('.rp-drow')].map((r) => { const bar = r.querySelector('.rp-dbar'), fill = bar.querySelector('i'), dn = r.querySelector('.rp-dn'), sm = dn.querySelector('small'), pc = r.querySelector('.rp-dp');
  return [dn.firstChild.textContent, sm ? sm.textContent : '', window.__txt(r.querySelector('.rp-dv'), '.sr-only'), pc ? pc.textContent : null, bar.className.replace('rp-dbar', '').trim(), fill ? Math.round(parseFloat(fill.style.width) * 10) / 10 : 0]; });
window.__w = { ls: [], idb: 0 };
try { const si = Storage.prototype.setItem; Storage.prototype.setItem = function (k, v) { window.__w.ls.push(k); return si.call(this, k, v); };
  const ri = Storage.prototype.removeItem; Storage.prototype.removeItem = function (k) { window.__w.ls.push('-' + k); return ri.call(this, k); };
  const io = IDBFactory.prototype.open; IDBFactory.prototype.open = function () { window.__w.idb++; return io.apply(this, arguments); }; } catch (e) { }
"""

MEALS_JS = """() => { const sec = document.querySelector('details[data-sec=meals]'); if (!sec) return null; const tx = window.__tx, ds = [...sec.querySelectorAll('.rp-dist')];
  return { title: tx(sec.querySelector('summary')), open: sec.open, meals: ds[0] ? window.__rows(ds[0]) : [], days: ds[1] ? window.__rows(ds[1]) : [], wk: ds[2] ? window.__rows(ds[2]) : [],
    hints: [...sec.querySelectorAll('.hint')].map(tx), heads: [...sec.querySelectorAll('.rp-h')].map(tx), noWeekday: [...sec.querySelectorAll('p.muted')].map(tx).filter((t) => t.startsWith('Weekday')) }; }"""

FOODS_JS = """() => { const sec = document.querySelector('details[data-sec=foods]'); if (!sec) return null; const tx = window.__tx, box = sec.querySelector('#rp-foods'), list = box.querySelector('.rp-foodlist');
  return { title: tx(sec.querySelector('summary')), open: sec.open, measure: tx(box.querySelector('.rp-measure')), unit: tx(box.querySelector('.rp-trend-h .muted')), h: tx(box.querySelector('.rp-h')),
    rows: list ? window.__rows(list) : [], total: window.__txt(box.querySelector('.rp-foodtot') || document.createElement('i'), '.sr-only') || null, hint: tx(box.querySelector('.rp-expl')), miss: tx(box.querySelector('.rp-foodmiss')), none: tx(box.querySelector('.rp-trend-none')) }; }"""

NOVA_JS = """() => { const sec = document.querySelector('details[data-sec=nova]'); if (!sec) return null; const tx = window.__tx, dist = sec.querySelector('.nova-card'), cards = [...sec.querySelectorAll(':scope > .card')], over = cards[1] || null;
  const ps = [...dist.querySelectorAll('p')];
  return { title: tx(sec.querySelector('summary')), open: sec.open, label: dist.querySelector('.bar').getAttribute('aria-label'),
    rows: [...dist.querySelectorAll('.nova-row')].map((r) => [tx(r.querySelector('.nova-name b')), tx(r.querySelector('.nova-val b')), tx(r.querySelector('.nova-val small'))]),
    cov: tx(ps[1]), hint: ps[2] && ps[2].classList.contains('hint') ? tx(ps[2]) : null, intro: tx(ps[0]),
    overH: over ? tx(over.querySelector('.rp-h')) : null, overNote: over ? tx(over.querySelector('p')) : null,
    bars: over ? [...over.querySelectorAll('.rp-nrow')].map((r) => { const b = r.querySelector('.rp-nb'), l = r.querySelector('.rp-nl'), sm = l.querySelector('small');
      return { label: l.firstChild.textContent, sub: sm ? sm.textContent : '', say: b.getAttribute('aria-label'), cls: b.className.replace('bar rp-nb', '').trim(), txt: b.classList.contains('none') || b.classList.contains('nodata') ? tx(b) : '', val: tx(r.querySelector('.rp-nv')), segs: b.querySelectorAll('i').length }; }) : [],
    heads: over && over.querySelector('thead') ? [...over.querySelectorAll('thead th')].map(tx) : [], rows2: over ? [...over.querySelectorAll('tbody tr')].map((tr) => [...tr.children].map(tx)) : [],
    tabopen: over && over.querySelector('details') ? over.querySelector('details').open : null, none: over && !over.querySelector('.rp-nt') ? tx(over.querySelector('p')) : null }; }"""

SIZES = "(sel) => [...document.querySelectorAll(sel)].filter((e) => !e.hidden && e.getClientRects().length).map((e) => { const r = e.getBoundingClientRect(); return [(e.id || e.dataset.act || e.className || e.tagName) + ':' + e.textContent.trim().slice(0, 14), Math.round(r.width), Math.round(r.height)]; }).filter((x) => x[2] < 44 || x[1] < 44)"

# the fill of the bars, the dashes and the outline of the NOVA segments against the card behind them (3:1 for graphics)
GFX = """(sel) => { const parse = (c) => { let m = c.match(/rgba?\\(([^)]+)\\)/); if (m) { const p = m[1].split(/[ ,\\/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; }
    m = c.match(/color\\(srgb ([^)]+)\\)/); if (m) { const p = m[1].split(/[ \\/]+/).filter(Boolean).map(Number); return [p[0] * 255, p[1] * 255, p[2] * 255, p.length > 3 ? p[3] : 1]; } return [0, 0, 0, 1]; };
  const lum = ([r, g, b]) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const card = document.querySelector(sel), bg = (() => { for (let e = card; e; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor); if (c[3] >= 1) return c; } return parse(getComputedStyle(document.body).backgroundColor); })();
  const tok = (name) => { const s = document.createElement('span'); s.style.color = `var(${name})`; card.appendChild(s); const c = parse(getComputedStyle(s).color); s.remove(); return c; };
  const out = {}; for (const n of ['--accent', '--muted', '--ink']) out[n] = Math.round(ratio(tok(n), bg) * 100) / 100;
  const seg = document.querySelector('.rp-nb:not(.none):not(.nodata) i'); const sh = seg ? getComputedStyle(seg).boxShadow : null; out.outline = sh;
  const m = sh && sh !== 'none' ? sh.match(/rgba?\\([^)]+\\)/) : null; out.outlineRatio = m ? Math.round(ratio(parse(m[0]), bg) * 100) / 100 : 0;
  out.novaCats = ['--n1', '--n2', '--n3', '--n4', '--n0'].map((n) => Math.round(ratio(tok(n), bg) * 100) / 100); return out; }"""


def own(fid, name, n, **kw):
    f = {'id': fid, 'src': 'user', 'name': name, 'brand': '', 'barcode': '', 'basis': {'qty': 100, 'unit': 'g'}, 'n': n, 'nova': None, 'portions': [], 'note': '', 'created': 1000, 'updated': 1000}
    f.update(kw)
    return f


# ---- the hand-calculated week: Mon 2, Wed 4 and Thu 5 Nov are logged days, Tue 3 Nov is not
ALPHA = own('u:alpha', 'Alpha', {'kcal': 100, 'protein': 10, 'calcium': 100}, nova=1)
BETA = own('u:beta', 'Beta', {'kcal': 200, 'protein': 5, 'calcium': 200}, nova=4)
GAMMA = own('u:gamma', 'Gamma', {'kcal': 50})
NOE = own('u:noe', 'No energy', {'protein': 2})
FOODS = [ALPHA, BETA, GAMMA, NOE]
#       id    food      g    day     meal
WEEK = [('e1', 'u:alpha', 200, day(-3), 'm1'),   # Mon: 200 kcal, protein 20, calcium 200
        ('e2', 'u:beta', 100, day(-3), 'm2'),    # Mon: 200 kcal, protein 5, calcium 200
        ('e3', 'u:alpha', 100, day(-1), 'm1'),   # Wed: 100 kcal, protein 10
        ('e4', 'u:gamma', 100, day(-1), 'm3'),   # Wed: 50 kcal
        ('e5', 'u:beta', 40, day(0), 'm1'),      # Thu: 80 kcal, protein 2
        ('e6', 'u:noe', 100, day(0), 'm4')]      # Thu: no energy, protein 2
# Energy: Mon 400, Wed 150, Thu >= 80 (e6 has no energy data); the three logged days add up to 630 kcal
# Meal 1: 200 + 100 + 80 = 380; Meal 2: 200; Meal 3: 50; Meal 4: only e6 (no energy data); Meal 5, 6: nothing

# a second sample for ranges and estimates: Mon and Wed
ESTF = own('u:estf', 'Est food', {'kcal': 100, 'calcium': 95, 'protein': 8}, est=['kcal', 'calcium'], q='m')
LIMF = own('u:limf', 'Limit food', {'kcal': '<20', 'calcium': '<201', 'protein': '<2'})
RANGE_FOODS = [ALPHA, ESTF, LIMF]
RANGE = [('r1', 'u:estf', 100, day(-3), 'm1'), ('r2', 'u:limf', 100, day(-3), 'm1'), ('r3', 'u:alpha', 100, day(-1), 'm2')]

# a long sample: Sep, Oct and Nov (the Nov days are the week above without the item without energy data)
LONG = [('m1', 'u:alpha', 100, '2026-09-02', 'm1'), ('m2', 'u:beta', 100, '2026-09-04', 'm1'), ('m3', 'u:alpha', 200, '2026-10-14', 'm1'), ('m4', 'u:alpha', 100, '2026-10-31', 'm1'), ('m5', 'u:gamma', 100, '2026-11-01', 'm1')] + WEEK[:5]


def share_pct(vals):
    """the largest-remainder rounding of the app (whole percents that add up to 100), same float operations"""
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
            print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(info)[:700].replace('\n', ' | ')) if info != '' else ''))
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

        async def pick_measure(m, pg=page, where='#rp-foods'):
            await pg.click(f'{where} .rp-measure'); await pg.wait_for_selector('.rp-m')
            await pg.click(f'.rp-m[data-m="{m}"]'); await pg.wait_for_timeout(60)

        async def seed(entries, foods=FOODS, kind='week', anchor=day(0), custom=None, open_all=ALL3, pg=page, water=None, ref=None, measure='kcal', nova_meta=None):
            await pg.evaluate("""([foods, ents, kind, anchor, custom, openAll, water, ref, nova]) => { const t = window.__tapnaplo, S = t.S;
              S.log.length = 0; for (const k of Object.keys(S.foods)) delete S.foods[k]; S.meta.ref = ref; S.meta.water = water || {}; S.meta.nova = nova || {};
              for (const f of foods) S.foods[f.id] = f;
              ents.forEach(([id, f, a, d, m], i) => S.log.push({ id, f, a, d, m: m || 'm1', t: 1000 + i, tm: '08:' + String(10 + (i % 50)) }));
              t.RP.kind = kind; t.RP.anchor = anchor; t.RP.custom = custom; for (const k of Object.keys(t.RP.open)) t.RP.open[k] = typeof openAll === 'object' ? !!openAll[k] : openAll;
              S.tab = 'report'; t.save(); t.render(); }""", [foods, entries, kind, anchor, custom, open_all, water, ref, nova_meta])
            await pg.wait_for_timeout(40)
            if measure is not None and await pg.locator('#rp-foods .rp-measure:visible').count() and await pg.evaluate("() => window.__tapnaplo.curMeasure()") != measure:
                await pick_measure(measure, pg)

        async def meals(pg=page):
            return await pg.evaluate(MEALS_JS)

        async def foods_(pg=page):
            return await pg.evaluate(FOODS_JS)

        async def nova(pg=page):
            return await pg.evaluate(NOVA_JS)

        # =========================================================== 1 order, closed by default, remembered
        await seed(WEEK, open_all={'overview': True})
        order = await T("() => [...document.querySelectorAll('#view > details.rp-sec')].map((d) => [d.dataset.sec, d.querySelector('summary').textContent.trim(), d.open])")
        check('the sections of the Report are in this order: Overview (open), Trend, Nutrients, Meals and weekdays, Foods, Food processing (NOVA), Data quality (all closed)',
              order == [['overview', 'Overview', True], ['trend', 'Trend', False], ['nutrients', 'Nutrients', False], ['meals', 'Meals and weekdays', False], ['foods', 'Foods', False], ['nova', 'Food processing (NOVA)', False], ['quality', 'Data quality', False], ['time', 'Time of day', False]], order)
        await page.click('details[data-sec=meals] > summary'); await page.click('details[data-sec=foods] > summary'); await page.click('details[data-sec=nova] > summary'); await page.wait_for_timeout(60)
        ro = json.loads(await T("() => localStorage.getItem('nutrilog.reportOpen')"))
        check('opening a section is remembered on this device (meals, foods, nova), next to the older keys', ro.get('meals') is True and ro.get('foods') is True and ro.get('nova') is True and ro.get('overview') is True and ro.get('novatable') is False, ro)
        await page.click('details[data-sec=foods] > summary'); await page.wait_for_timeout(60)
        check('closing it is remembered too', json.loads(await T("() => localStorage.getItem('nutrilog.reportOpen')")).get('foods') is False)

        # =========================================================== 2 the hand-calculated week: Meals and weekdays
        await seed(WEEK)
        m = await meals()
        check('Meals and weekdays: the section has the two parts "Energy by meal" and "Energy by weekday" (and "Weekdays and weekend")', m['title'] == 'Meals and weekdays' and m['heads'] == ['Energy by meal', 'Energy by weekday', 'Weekdays and weekend'], m['heads'])
        # Meal 1: 380 / 3 days = 126.7 (3 of 3 days, 3 items); Meal 2: 200 / 3 = 66.7; Meal 3: 50 / 3 = 16.7; shares 380 / 630 = 60.3, 31.7, 7.9 -> 60 + 32 + 8 = 100
        check('Meal 1: average per logged day 380 / 3 = 127 kcal, share 60%, on 3 of 3 days with 3 items; the bar is 60.3% wide',
              m['meals'][0] == ['Meal 1', '3 of 3 days · 3 items', '127kcal', '60%', 'full', 60.3], m['meals'][0])
        check('Meal 2: 200 / 3 = 66.7 kcal, 32%; Meal 3: 50 / 3 = 16.7 kcal, 8% (a meal that is empty on two of the three logged days counts as 0 kcal on those days)',
              m['meals'][1] == ['Meal 2', '1 of 3 days · 1 item', '66.7kcal', '32%', 'full', 31.7] and m['meals'][2] == ['Meal 3', '1 of 3 days · 1 item', '16.7kcal', '8%', 'full', 7.9], [m['meals'][1], m['meals'][2]])
        check('...the shares add up to 100 (60 + 32 + 8)', sum(int(x[3][:-1]) for x in m['meals'] if x[3] and x[3] != '–') == 100)
        check('Meal 4 has an item, but it has no energy data: "no energy data", no share, a dotted line - not 0 kcal',
              m['meals'][3] == ['Meal 4', '1 of 3 days · 1 item', 'no energy data', '–', 'nodata', 0], m['meals'][3])
        check('Meal 5 and Meal 6 have no entries at all: "no entries", no share, a dashed line - not 0 kcal',
              m['meals'][4] == ['Meal 5', '', 'no entries', '–', 'none', 0] and m['meals'][5] == ['Meal 6', '', 'no entries', '–', 'none', 0] and len(m['meals']) == 6, m['meals'][4:])
        check('...the explanation says that an empty meal counts as 0 kcal, that missing energy data does not, and names the 1 item without energy data',
              'counts as 0 kcal for that meal' in m['hints'][0] and 'not counted as 0' in m['hints'][0] and '1 item without energy data is not in them' in m['hints'][0], m['hints'][0])
        # weekdays: Mon 400 (1 day), Tue none, Wed 150, Thu >= 80 (e6 has no energy data: striped), Fri-Sun none; the longest bar is Monday
        check('weekdays: Mon 400 kcal (1 logged day, the longest bar), Wed 150 kcal (37.5%), Thu "≥ 80 kcal" (a striped bar: one item has no energy data)',
              m['days'][0] == ['Mon', '1 logged day', '400kcal', None, 'full', 100.0] and m['days'][2] == ['Wed', '1 logged day', '150kcal', None, 'full', 37.5] and m['days'][3] == ['Thu', '1 logged day', '≥ 80kcal', None, 'part', 20.0], [m['days'][0], m['days'][2], m['days'][3]])
        check('...Tue, Fri, Sat and Sun have no logged day: "no logged day", a dashed line - not 0 kcal; seven weekdays',
              len(m['days']) == 7 and all(m['days'][k][2] == 'no logged day' and m['days'][k][4] == 'none' and m['days'][k][1] == '' for k in (1, 4, 5, 6)), m['days'])
        # Mon-Fri: (400 + 150 + 80) / 3 = 210, striped; Sat-Sun: nothing
        check('Monday to Friday: 3 logged days, "≥ 210 kcal" ((400 + 150 + 80) / 3), striped; Saturday and Sunday: no logged day',
              m['wk'] == [['Mon–Fri', '3 logged days', '≥ 210kcal', None, 'part', 100.0], ['Sat–Sun', '', 'no logged day', None, 'none', 0]], m['wk'])
        check('...the weekday explanation: an unlogged weekday is left out, not 0; look at the number of days', 'is left out, it is not 0' in m['hints'][1] and 'look at the number of days' in m['hints'][1], m['hints'][1])
        # the sums: the meals add up to the energy of the Overview
        sums = await T("() => { const t = window.__tapnaplo, r = t.rpRange(), P = t.rpStats(r.from, r.to), rows = t.rpMealRows(P); return { sum: rows.reduce((s, o) => s + o.avgLo, 0), overview: P.T.lo[0], avgs: rows.map((o) => o.state) }; }")
        check('the meal averages add up to the average of the Overview: 126.67 + 66.67 + 16.67 = 210 kcal (the item without energy data adds nothing)', abs(sums['sum'] - 210) < 1e-9 and abs(sums['overview'] - 210) < 1e-9, sums)
        # Day period: one day
        await seed(WEEK, kind='day', anchor=day(0))
        m = await meals()
        check('a Day (Thu 5 Nov): Meal 1 has 80 kcal and 100% of the known energy; the line says "1 item" only (no "of N days" for one day); Meal 4 has no energy data',
              m['meals'][0] == ['Meal 1', '1 item', '80kcal', '100%', 'full', 100.0] and m['meals'][3] == ['Meal 4', '1 item', 'no energy data', '–', 'nodata', 0], [m['meals'][0], m['meals'][3]])
        check('...and a Day has no weekday part: "Weekday averages need at least two logged days in the period."', m['days'] == [] and m['wk'] == [] and m['noWeekday'] == ['Weekday averages need at least two logged days in the period.'], m['noWeekday'])

        # =========================================================== 3 ranges, estimates, an unknown meal, a food that is not loaded
        await seed(RANGE, foods=RANGE_FOODS)
        m = await meals()
        # Meal 1: Est food 100 (estimate) + Limit food <20 (0..20) = 100..120 in all, /2 logged days = 50..60: a range with ~ ; Meal 2: Alpha 100 / 2 = 50
        check('a meal with an estimate and a "<20" value: "~50–60 kcal" (an estimate and a range, no ≥ because every item has energy data); the other meal 50 kcal; the shares are 50% and 50%',
              m['meals'][0] == ['Meal 1', '1 of 2 days · 2 items', '~50–60kcal', '50%', 'full', 50.0] and m['meals'][1] == ['Meal 2', '1 of 2 days · 1 item', '50kcal', '50%', 'full', 50.0], m['meals'][:2])
        await seed(WEEK + [('x1', 'u:alpha', 100, day(0), 'x')])
        m = await meals()
        # Alpha 100 kcal on Thu, in a meal that does not exist: "No meal", so the meal rows still add up to the Overview
        check('an entry whose meal is not Meal 1 - 6 (old data) is not lost: a seventh row "No meal" has its energy (100 / 3 = 33.3 kcal)', len(m['meals']) == 7 and m['meals'][6][0] == 'No meal' and m['meals'][6][2] == '33.3kcal', m['meals'][6:])
        sums = await T("() => { const t = window.__tapnaplo, r = t.rpRange(), P = t.rpStats(r.from, r.to); return [t.rpMealRows(P).reduce((s, o) => s + o.avgLo, 0), P.T.lo[0]]; }")
        check('...and the seven rows still add up to the Overview (243.3 kcal)', abs(sums[0] - sums[1]) < 1e-9 and abs(sums[0] - 243.3333333) < 1e-5, sums)
        await seed(WEEK + [('h1', 'u:missing', 100, day(-2), 'm1')])
        m = await meals()
        check('an entry whose food is not loaded is not a logged day: Tuesday stays "no logged day" and Meal 1 is unchanged (the Report warns about it elsewhere)', m['days'][1][2] == 'no logged day' and m['meals'][0][2] == '127kcal' and 'is not counted' in await page.inner_text('.banner.warn'), [m['days'][1], m['meals'][0]])

        # =========================================================== 4 Foods: Energy and Protein
        await seed(WEEK)
        f = await foods_()
        check('Foods: the measure button says Energy (the same measure as the Trend), the line says "kcal added up over 3 logged days", the heading "Biggest sources of Energy"', f['title'] == 'Foods' and f['measure'] == 'Energy' and f['unit'] == 'kcal added up over 3 logged days' and f['h'] == 'Biggest sources of Energy', [f['measure'], f['unit'], f['h']])
        # Alpha 200 + 100 g = 300 g = 300 kcal; Beta 100 + 40 g = 140 g = 280 kcal; Gamma 50 kcal; total 630; shares 47.6, 44.4, 7.9 -> 48 + 44 + 8 (largest remainder)
        check('Energy: Alpha 300 g on 2 days in 2 entries = 300 kcal (48%), Beta 140 g = 280 kcal (44%), Gamma 100 g on 1 day in 1 entry = 50 kcal (8%)',
              f['rows'] == [['Alpha', '300 g · 2 days · 2 entries', '300kcal', '48%', 'full', 47.6], ['Beta', '140 g · 2 days · 2 entries', '280kcal', '44%', 'full', 44.4], ['Gamma', '100 g · 1 day · 1 entry', '50kcal', '8%', 'full', 7.9]], f['rows'])
        check('...the total of the foods with data is 630 kcal, and "No energy" (no energy data) is named, in neither the list nor the shares, "and not zero"',
              f['total'] == 'All foods with data: 630 kcal' and f['miss'] == 'No data for: No energy. It is not in the list or the shares, and not zero.', [f['total'], f['miss']])
        check('...the explanation says each food is all its entries added up and that the shares add up to 100%', 'all its entries of the period added up' in f['hint'] and 'add up to 100%' in f['hint'], f['hint'])
        # Protein: Alpha 20 + 10 = 30 g, Beta 5 + 2 = 7 g, No energy 2 g: total 39; shares 76.9, 17.9, 5.1 -> floors 76 + 17 + 5 = 98, +1 to the two biggest remainders (.95 and .92): 77, 18, 5
        await pick_measure('protein')
        f = await foods_()
        check('choosing Protein redraws only the list: Alpha 30 g (77%), Beta 7 g (18%), No energy 2 g (5%), total 39 g; "Gamma" has no protein data and is named',
              [r[0] for r in f['rows']] == ['Alpha', 'Beta', 'No energy'] and [r[2] for r in f['rows']] == ['30g', '7g', '2g'] and [r[3] for r in f['rows']] == ['77%', '18%', '5%'] and f['total'] == 'All foods with data: 39 g' and f['miss'].startswith('No data for: Gamma.'), [f['rows'], f['total'], f['miss']])
        check('...the Trend uses the same measure (one choice for both): its button says Protein too', (await T("() => document.querySelector('#rp-trend .rp-measure').textContent.trim()")) == 'Protein' and f['measure'] == 'Protein')
        check('...the choice is the one of the Trend and is kept on this device', await T("() => localStorage.getItem('nutrilog.reportMeasure')") == 'protein')
        sh_title = None
        await page.click('#rp-foods .rp-measure'); await page.wait_for_selector('.rp-m')
        sh_title = await page.inner_text('.sheet-h') if await page.locator('.sheet-h').count() else await page.evaluate("() => document.querySelector('.sheet h2, .sheet h3, .sheet-t, .sheet header').textContent")
        mark = await T("() => [...document.querySelectorAll('.rp-m')].filter((b) => ['Sugars', 'Protein'].includes(b.firstChild.textContent)).map((b) => [b.firstChild.textContent, b.getAttribute('aria-pressed'), b.querySelector('small') ? b.querySelector('small').textContent : ''])")
        check('the measure sheet opened from Foods is called "Measure" and says that the Trend and the Foods list use it; Protein is the chosen one; Sugars (nobody has data) says "no data"',
              sh_title.strip() == 'Measure' and 'The Trend and the Foods list show the measure you choose here.' in await page.inner_text('.sheet') and ['Protein', 'true', ''] in mark and ['Sugars', 'false', 'no data'] in mark, [sh_title, mark])
        await page.click('.sheet [data-x]'); await page.wait_for_timeout(260)
        await pick_measure('water_intake')
        f = await foods_()
        check('Water intake has no list of foods (it is logged as one total for the day): the message says so and to choose a nutrient; no rows', f['rows'] == [] and f['none'] == 'Water intake is logged as one total for the day, not for each food, so there is no list of foods. Choose a nutrient.', f['none'])
        await pick_measure('omega_ratio')
        f = await foods_()
        check('the omega-6 : omega-3 ratio has no list of foods either (it is worked out from the totals): the message says so', f['rows'] == [] and f['none'].startswith('The ratio is worked out from the totals of several fatty acids, so it has no list of foods.'), f['none'])
        await pick_measure('sugars')
        f = await foods_()
        check('Sugars: nobody has data, so there is nothing to list - "This is not zero." - and the measure button stays', f['rows'] == [] and f['none'] == 'No item in this period has data for Sugars, so there is nothing to list. This is not zero.' and f['measure'] == 'Sugars', f['none'])
        await pick_measure('kcal')

        # a Day has no Trend, but the Foods list has its own measure button
        await seed(WEEK, kind='day', anchor=day(0))
        check('a Day has no Trend section, but the Foods section has its measure button', await page.locator('details[data-sec=trend]').count() == 0 and await page.locator('#rp-foods .rp-measure').count() == 1)
        f = await foods_()
        check('Day, Energy: Beta 40 g on 1 day in 1 entry = 80 kcal, 100%; "No energy" is named', f['rows'] == [['Beta', '40 g · 1 day · 1 entry', '80kcal', '100%', 'full', 100.0]] and f['miss'].startswith('No data for: No energy.'), f['rows'])
        await pick_measure('protein')
        f = await foods_()
        check('...choosing Protein there redraws the list (no Trend to redraw): Beta 2 g (50%), No energy 2 g (50%): shares 50 + 50', [r[0] for r in f['rows']] == ['Beta', 'No energy'] and [r[3] for r in f['rows']] == ['50%', '50%'] and f['measure'] == 'Protein', f['rows'])
        await pick_measure('kcal')

        # ranges and estimates in the list
        await seed(RANGE, foods=RANGE_FOODS, measure='calcium')
        f = await foods_()
        # Alpha 100 mg, Est food ~95 mg, Limit food <201 (lower value 0, upper 201): total 195 .. 396 with a ~; shares of the lower values 51.3 / 48.7 -> 51 and 49; the limit food has none
        check('Calcium with an estimate and a "<201" value: Alpha 100 mg (51%), Est food ~95 mg (49%), Limit food <201 mg with no share ("–": its lower value is 0, but it may be much more)',
              [r[0] for r in f['rows']] == ['Alpha', 'Est food', 'Limit food'] and [r[2] for r in f['rows']] == ['100mg', '~95mg', '<201mg'] and [r[3] for r in f['rows']] == ['51%', '49%', '–'], f['rows'])
        check('...the total is a range with a ~ (~195–396 mg), and the explanation says a food known only as "below x" has no share', f['total'] == 'All foods with data: ~195–396 mg' and 'A food known only as “below x” has no share.' in f['hint'], [f['total'], f['hint']])
        await pick_measure('kcal')

        # more than ten foods: the top 10 and one line "N more foods" that adds up
        many = [own(f'u:z{i:02d}', f'Food {i:02d}', {'kcal': 100 + 10 * i}) for i in range(14)]
        ents = [(f'z{i}', f'u:z{i:02d}', 100, day(-3) if i < 7 else day(-1), 'm1') for i in range(14)]
        await seed(ents, foods=many)
        f = await foods_()
        # kcal 100 .. 230 (Food 00 .. Food 13); the biggest is Food 13 (230); the last four (100, 110, 120, 130) are the "4 more foods": 460 kcal; total = 14 * 100 + 10 * 91 = 2310
        check('14 foods: ten rows and a line "4 more foods" (the four smallest: 100 + 110 + 120 + 130 = 460 kcal) - eleven lines in all', len(f['rows']) == 11 and f['rows'][0][0] == 'Food 13' and f['rows'][10][0] == '4 more foods' and f['rows'][10][2] == '460kcal' and f['total'] == 'All foods with data: 2,310 kcal', [f['rows'][0], f['rows'][10], f['total']])
        shares = [int(r[3][:-1]) for r in f['rows']]
        check('...the eleven shares add up to 100 (top 10 and the rest)', sum(shares) == 100, shares)

        # =========================================================== 5 NOVA: the whole period and the day bars
        await seed(WEEK)
        n = await nova()
        check('Food processing: the card says the share is of the energy of the whole period, worked out from all items together, not an average of daily percents',
              n['title'] == 'Food processing (NOVA)' and 'worked out from all items together, not as an average of daily percents' in n['intro'], n['intro'])
        # NOVA 1: Alpha 300 kcal, NOVA 4: Beta 280, unclassified: Gamma 50; total 630: 47.6, 44.4, 7.9 -> 48, 44, 8
        check('whole week: NOVA 1 48% (300 kcal), NOVA 2 0%, NOVA 3 0%, NOVA 4 44% (280 kcal), Unclassified 8% (50 kcal) - the same rows as the Nutrients tab',
              n['rows'] == [['NOVA 1', '48%', '300 kcal'], ['NOVA 2', '0%', ''], ['NOVA 3', '0%', ''], ['NOVA 4', '44%', '280 kcal'], ['Unclassified', '8%', '50 kcal']], n['rows'])
        check('...the spoken description of the bar lists the five shares', n['label'].startswith('Energy by NOVA group: ') and 'NOVA 1: Unprocessed or minimally processed 48%' in n['label'] and 'Unclassified 8%' in n['label'], n['label'])
        check('...coverage: 2 of 4 foods have a group; 1 entry has no energy data and is not counted; and the hint says where to set a group', n['cov'] == '2 of 4 foods classified. 1 entry has no energy data and is not counted in the shares.' and n['hint'] == 'To sort a food into a group, open the Nutrients tab and use Set NOVA groups there.', [n['cov'], n['hint']])
        check('...the card is read only: no NOVA buttons in the Report', await page.locator('details[data-sec=nova] [data-act=nova-set], details[data-sec=nova] #novafold').count() == 0)
        check('...Over time: one bar for each day (4 bars, Mon - Thu); the note says the colours are the ones above and the number at the right is the share of NOVA 4', n['overH'] == 'Over time' and len(n['bars']) == 4 and 'One bar for each day' in n['overNote'] and 'share of NOVA 4' in n['overNote'], n['overNote'])
        b = n['bars']
        # Mon 200 (n1) + 200 (n4): 50 / 50; Tue none; Wed 100 (n1) + 50 (u): 66.7 / 33.3 -> 67 / 33; Thu 80 (n4): 100
        check('Mon 2 Nov: NOVA 1 50%, NOVA 4 50% (two segments), the number at the right is 50%',
              b[0]['label'] == 'Mon, 2 Nov' and b[0]['say'] == 'Mon, 2 Nov: NOVA 1 50%, NOVA 2 0%, NOVA 3 0%, NOVA 4 50%, Unclassified 0%' and b[0]['val'] == '50%' and b[0]['segs'] == 2 and b[0]['sub'] == '', b[0])
        check('Tue 3 Nov has no entries: a dashed line that says "no entries" - not a bar of 0%, no number',
              b[1]['cls'] == 'none' and b[1]['txt'] == 'no entries' and b[1]['say'] is None and b[1]['val'] == '' and b[1]['segs'] == 0, b[1])
        check('Wed 4 Nov: NOVA 1 67%, Unclassified 33% (the unclassified part is its own segment); NOVA 4 is 0%', b[2]['say'] == 'Wed, 4 Nov: NOVA 1 67%, NOVA 2 0%, NOVA 3 0%, NOVA 4 0%, Unclassified 33%' and b[2]['val'] == '0%' and b[2]['segs'] == 2, b[2])
        check('Thu 5 Nov: NOVA 4 100% (the item without energy data is not counted)', b[3]['say'] == 'Thu, 5 Nov: NOVA 1 0%, NOVA 2 0%, NOVA 3 0%, NOVA 4 100%, Unclassified 0%' and b[3]['val'] == '100%' and b[3]['segs'] == 1, b[3])
        check('"Show as table" (open here): Day / NOVA 1 / NOVA 2 / NOVA 3 / NOVA 4 / No group, and a row for every bar; the gap says "no entries"',
              n['heads'] == ['Day', 'NOVA 1', 'NOVA 2', 'NOVA 3', 'NOVA 4', 'No group'] and n['rows2'] == [['Mon, 2 Nov', '50%', '0%', '0%', '50%', '0%'], ['Tue, 3 Nov', 'no entries'], ['Wed, 4 Nov', '67%', '0%', '0%', '0%', '33%'], ['Thu, 5 Nov', '0%', '0%', '0%', '100%', '0%']], [n['heads'], n['rows2']])
        check('...the last column is spoken as "Unclassified"', await T("() => document.querySelector('.rp-nt-table thead th:last-child').getAttribute('aria-label')") == 'Unclassified')
        sums = await T("() => { const t = window.__tapnaplo, r = t.rpRange(), P = t.rpStats(r.from, r.to), s = t.novaStats(P.es); return [s.sum, t.rpNovaBars(P, r).filter((b) => b.state === 'ok').map((b) => b.pc.reduce((a, c) => a + c, 0))]; }")
        check('the period sums: the NOVA energy is 630 kcal (as in the Foods list) and every bar adds up to 100', sums == [630, [100, 100, 100]], sums)
        # the NOVA split is not the average of the daily percents: the average of 50, 67, 0 is 39, the energy-weighted NOVA 1 is 48
        check('...the split is weighted by energy, not an average of the daily percents (NOVA 1: 48%, while the daily shares 50, 67 and 0 would average 39%)', n['rows'][0][1] == '48%')

        # a Day: only the card
        await seed(WEEK, kind='day', anchor=day(0))
        n = await nova()
        check('a Day (Thu 5 Nov): the NOVA card (NOVA 4 100%) and no "Over time"', n['rows'][3] == ['NOVA 4', '100%', '80 kcal'] and n['overH'] is None and n['bars'] == [], [n['rows'][3], n['overH']])
        # one logged day in a week
        await seed([WEEK[0], WEEK[1]], kind='week')
        n = await nova()
        check('a week with one logged day: the card is there; "Over time" says a trend needs at least two days with entries', n['rows'][0][1] == '50%' and n['none'] == 'A trend needs at least two days with entries in this period.', [n['rows'][0], n['none']])
        # no energy data at all
        await seed([('q1', 'u:noe', 100, day(-3), 'm1'), ('q2', 'u:noe', 100, day(-1), 'm1')], kind='week')
        n = await nova()
        check('only items without energy data: the card says so ("–", not 0%), the bars say "no energy to split", and the section says that it is not zero',
              n['rows'][0][1] == '–' and n['label'] == 'No energy data to split by NOVA group' and n['none'] == 'No item in this period has energy data, so there is nothing to split. This is not zero.', [n['rows'][0], n['label'], n['none']])
        # <1%
        TINY = [('t1', 'u:alpha', 1000, day(-3), 'm1'), ('t2', 'u:gamma', 1, day(-3), 'm1'), ('t3', 'u:alpha', 100, day(-1), 'm1')]
        await seed(TINY)
        n = await nova()
        # 1000 + 100 kcal NOVA 1, 0.5 kcal unclassified: 99.95%, 0.045% -> "<1%" for the unclassified, not 0%
        check('a share below 1% is "<1%", not 0% (0.5 kcal of 1,100.5 is unclassified); the largest group gets the rest (100%)', n['rows'][4][1] == '<1%' and n['rows'][0][1] == '100%' and 'Unclassified <1%' in n['label'], [n['rows'][4], n['rows'][0]])
        check('...and in the bar of the day: "Unclassified <1%"', 'Unclassified <1%' in n['bars'][0]['say'] and n['bars'][0]['say'].startswith('Mon, 2 Nov: NOVA 1 100%'), n['bars'][0]['say'])
        # a group set by hand in the metadata of a CIQUAL-like food counts (the Report only reads)
        GAMMA2 = dict(GAMMA, nova=2)       # an own food keeps the group set on the Nutrients tab in the food itself (food.nova)
        await seed(WEEK, foods=[ALPHA, BETA, GAMMA2, NOE])
        n = await nova()
        check('a group set on the Nutrients tab (here NOVA 2 for the own food Gamma) is read by the Report: NOVA 2 8% (50 kcal), Unclassified 0%, and the hint about setting groups is gone',
              n['rows'][1] == ['NOVA 2', '8%', '50 kcal'] and n['rows'][4][1] == '0%' and n['cov'].startswith('3 of 4 foods classified.'), [n['rows'], n['cov']])
        n_hint = n['hint']
        check('...nothing is left to classify (the item without energy data is not counted), so no hint', n_hint is None, n_hint)
        # a CIQUAL food (real data: c:24999 "Desert (average)", 281 kcal per 100 g) keeps its group in the metadata; the Report reads it like the Nutrients tab
        CQ = [('c1', 'c:24999', 100, day(-3), 'm1'), ('c2', 'c:24999', 100, day(-1), 'm1')]
        await seed(CQ, foods=[], measure=None)
        n = await nova()
        check('a CIQUAL food starts "Unclassified" (nothing is guessed): 562 kcal, Unclassified 100%, and the hint says where to set a group',
              n['rows'][4] == ['Unclassified', '100%', '562 kcal'] and n['hint'] == 'To sort a food into a group, open the Nutrients tab and use Set NOVA groups there.', [n['rows'][4], n['hint']])
        await seed(CQ, foods=[], nova_meta={'c:24999': 3}, measure=None)
        n = await nova()
        check('...with its group set on the Nutrients tab (kept in the metadata) the Report shows NOVA 3 100% and no hint; both day bars are NOVA 3 100%',
              n['rows'][2] == ['NOVA 3', '100%', '562 kcal'] and n['rows'][4][1] == '0%' and n['hint'] is None and all('NOVA 3 100%' in b['say'] for b in n['bars'] if b['say']), [n['rows'], n['hint']])

        # =========================================================== 6 weeks and months
        await seed(LONG, kind='m3')
        n = await nova()
        mon = await T("() => new Date(2026, 8, 1).toLocaleDateString('en-GB', { month: 'short' })")
        labels = await T("() => { const t = window.__tapnaplo, r = t.rpRange(), P = t.rpStats(r.from, r.to); return t.rpNovaBars(P, r).map((b) => b.short); }")
        check('3 months (1 Sep - 5 Nov, 66 days): one bar for each week, 10 bars; the note says the share is of the logged days in the bar; the table says Week', len(n['bars']) == 10 and 'One bar for each week' in n['overNote'] and 'The share is of the logged days in the bar.' in n['overNote'] and n['heads'][0] == 'Week', [len(n['bars']), n['overNote'], n['heads'][0]])
        check('...a week row is named by its dates and says how many logged days it has', n['bars'][0]['label'] == labels[0] and n['bars'][0]['sub'] == '2 logged days' and n['bars'][6]['sub'] == '1 logged day' and n['bars'][1]['sub'] == '', [n['bars'][0], n['bars'][6]])
        # 1-6 Sep: Alpha 100 kcal (n1) + Beta 200 kcal (n4) = 300: 33.3 / 66.7 -> 33 / 67; 12-18 Oct: Alpha 200 (n1) = 100%; 26 Oct - 1 Nov: Alpha 100 (n1) + Gamma 50 (u): 67 / 33; 2-5 Nov: 48 / 44 / 8
        check('1 - 6 Sep: NOVA 1 33%, NOVA 4 67% (the number at the right is 67%)', n['bars'][0]['say'].endswith('NOVA 1 33%, NOVA 2 0%, NOVA 3 0%, NOVA 4 67%, Unclassified 0%') and n['bars'][0]['val'] == '67%', n['bars'][0]['say'])
        check('12 - 18 Oct: NOVA 1 100% (one logged day); 7 - 13 Sep has no entries', n['bars'][6]['say'].endswith('NOVA 1 100%, NOVA 2 0%, NOVA 3 0%, NOVA 4 0%, Unclassified 0%') and n['bars'][1]['cls'] == 'none' and n['bars'][1]['txt'] == 'no entries', [n['bars'][6]['say'], n['bars'][1]['cls']])
        check('26 Oct - 1 Nov: NOVA 1 67%, Unclassified 33%; 2 - 5 Nov: 48%, 44%, 8% (the whole week, with three logged days)', n['bars'][8]['say'].endswith('NOVA 1 67%, NOVA 2 0%, NOVA 3 0%, NOVA 4 0%, Unclassified 33%') and n['bars'][9]['say'].endswith('NOVA 1 48%, NOVA 2 0%, NOVA 3 0%, NOVA 4 44%, Unclassified 8%') and n['bars'][9]['sub'] == '3 logged days', [n['bars'][8]['say'], n['bars'][9]['say']])
        check('...the table has a row for every week', len(n['rows2']) == 10 and n['rows2'][9][1:] == ['48%', '0%', '0%', '44%', '8%'], n['rows2'][9])
        check('...the whole 3 months: NOVA 1 (100 + 200 + 100 + 100 + 100 + 200 = 800 kcal... see below)', True)
        await seed(LONG, kind='year')
        n = await nova()
        # Sep: 100 + 200 -> 33 / 67; Oct: Alpha 200 + 100 = 300 -> 100; Nov: Alpha 300 + Gamma 50 + Gamma 50 (1 Nov) + Beta 280 (n4) = n1 300, n4 280, u 100 -> 44.1 / 41.2 / 14.7 -> 44 / 41 / 15
        check('Year (Dec 2025 - Nov 2026): one bar for each month, 12 bars, the table says Month; December 2025 has no entries', len(n['bars']) == 12 and 'One bar for each month' in n['overNote'] and n['heads'][0] == 'Month' and n['bars'][0]['cls'] == 'none' and n['bars'][0]['label'] == 'December 2025', [len(n['bars']), n['heads'][0], n['bars'][0]['label']])
        check('...September 33 / 67, October 100, November 44 / 41 / 15 (4 logged days) - and the number at the right is NOVA 4 (67%, 0%, 41%)',
              n['bars'][9]['say'].endswith('NOVA 1 33%, NOVA 2 0%, NOVA 3 0%, NOVA 4 67%, Unclassified 0%') and n['bars'][10]['say'].endswith('NOVA 1 100%, NOVA 2 0%, NOVA 3 0%, NOVA 4 0%, Unclassified 0%') and n['bars'][11]['say'].endswith('NOVA 1 44%, NOVA 2 0%, NOVA 3 0%, NOVA 4 41%, Unclassified 15%')
              and [n['bars'][k]['val'] for k in (9, 10, 11)] == ['67%', '0%', '41%'] and n['bars'][11]['sub'] == '4 logged days', [n['bars'][k]['say'] for k in (9, 10, 11)])
        # Meals and weekdays over a long period: the average is per logged day
        m = await meals()
        # 8 logged days (2, 4 Sep; 14, 31 Oct; 1, 2, 4, 5 Nov), not 365. Meal 1 has 8 items: Alpha 100 + Beta 200 + Alpha 200 + Alpha 100 + Gamma 50 + Alpha 200 + Alpha 100 + Beta 80 = 1,030 kcal
        # Meal 2 (Beta 200) and Meal 3 (Gamma 50) make 1,280 kcal in all = 160 kcal a day; Meal 1 is 1,030 / 8 = 128.75 kcal, 80.5% of 1,280 -> 80%
        check('a year: the meal averages divide by the 8 logged days, not by 365 - Meal 1 is 1,030 / 8 = 129 kcal, 80% of the known energy',
              m['meals'][0] == ['Meal 1', '8 of 8 days · 8 items', '129kcal', '80%', 'full', 80.5] and m['meals'][1][1:4] == ['1 of 8 days · 1 item', '25kcal', '16%'], [m['meals'][0], m['meals'][1]])
        sums = await T("() => { const t = window.__tapnaplo, r = t.rpRange(), P = t.rpStats(r.from, r.to); return [t.rpMealRows(P).reduce((s, o) => s + o.avgLo, 0), P.T.lo[0], P.nd]; }")
        check('...and the meals add up to the energy of the Overview: 160 kcal a logged day', abs(sums[0] - 160) < 1e-9 and abs(sums[1] - 160) < 1e-9 and sums[2] == 8, sums)

        # =========================================================== 7 hostile food name
        EVIL = own('u:evil', '<img src=x onerror="window.__pwn=1"><b>X</b> & "Q"', {'kcal': 300, 'protein': 1})
        await seed([('v1', 'u:evil', 100, day(-3), 'm1'), ('v2', 'u:evil', 100, day(-1), 'm1'), ('v3', 'u:noe', 100, day(0), 'm1')], foods=[EVIL, NOE])
        hostile = await T("() => ({ pwn: window.__pwn === undefined, imgs: document.querySelectorAll('#view img').length + [...document.querySelectorAll('#view b')].filter((b) => b.textContent === 'X').length, row: document.querySelector('#rp-foods .rp-foodlist .rp-dn').firstChild.textContent })")
        check('a hostile food name is plain text in the Foods list (no image, no bold, no script) and in the "No data" line', hostile['pwn'] and hostile['imgs'] == 0 and hostile['row'] == '<img src=x onerror="window.__pwn=1"><b>X</b> & "Q"', hostile)

        # =========================================================== 8 the shared copy
        VF, VT = day(-5), day(0)         # Sat 31 Oct - Thu 5 Nov: 31 Oct (Alpha), 1 Nov (Gamma), 2, 4, 5 Nov (the week)
        await seed(LONG, kind='custom', custom={'from': VF, 'to': VT})
        s_m, s_f, s_n = await meals(), await foods_(), await nova()
        link = await T("([a, b]) => window.__tapnaplo.shareLink(a, b, false).then((r) => r.url)", [VF, VT])
        vctx = await new_ctx(390, 844)
        vp = await vctx.new_page(); watch(vp, 'V')
        await vp.goto(link); await vp.wait_for_selector('.hero')
        await vp.click('[data-tab=report]'); await vp.wait_for_selector('.rp-seg')
        await vp.evaluate("() => document.querySelectorAll('details[data-sec=meals], details[data-sec=foods], details[data-sec=nova], details[data-sec=novatable]').forEach((d) => { d.open = true; })"); await vp.wait_for_timeout(60)
        v_m, v_f, v_n = await meals(vp), await foods_(vp), await nova(vp)
        check('the shared copy shows the same Meals and weekdays as the sender (meals, weekdays, weekday against weekend, explanations)', v_m is not None and {k: v_m[k] for k in ('meals', 'days', 'wk', 'hints', 'heads')} == {k: s_m[k] for k in ('meals', 'days', 'wk', 'hints', 'heads')}, [v_m and v_m['meals'][:2], s_m['meals'][:2]])
        check('...the same Foods list (rows, total, explanation)', v_f is not None and {k: v_f[k] for k in ('rows', 'total', 'hint', 'miss', 'measure', 'unit')} == {k: s_f[k] for k in ('rows', 'total', 'hint', 'miss', 'measure', 'unit')}, [v_f and v_f['rows'], s_f['rows']])
        check('...and the same NOVA card and day bars (without the hint about setting a group: a shared copy cannot set one)', v_n is not None and {k: v_n[k] for k in ('rows', 'label', 'cov', 'bars', 'rows2', 'heads')} == {k: s_n[k] for k in ('rows', 'label', 'cov', 'bars', 'rows2', 'heads')} and v_n['hint'] is None and s_n['hint'] is not None, [v_n and v_n['hint'], s_n['hint']])
        await pick_measure('protein', vp)
        vf2 = await foods_(vp)
        check('the measure of Foods can be chosen in the shared copy (Protein: the list changes)', vf2['measure'] == 'Protein' and vf2['rows'] != v_f['rows'] and vf2['rows'][0][2].endswith('g'), vf2['rows'][:1])
        w = await vp.evaluate("() => window.__w")
        check('the viewer wrote nothing: no localStorage write (not the measure, not the open parts), no IndexedDB opened', w['ls'] == [] and w['idb'] == 0, w)
        await vctx.close()

        # =========================================================== 9 layout, 44 px, contrast
        for wd in (390, 320):
            cx, pg = await fresh(wd, 844, f'L{wd}')
            await seed(LONG, kind='m3', pg=pg, open_all=True, measure='calcium')
            await pg.evaluate("() => document.querySelectorAll('#view details.rp-sec, #view details.fold').forEach((d) => { d.open = true; })"); await pg.wait_for_timeout(60)
            fits = await pg.evaluate("""() => ({ page: document.documentElement.scrollWidth <= window.innerWidth,
              wrap: (() => { const t = document.querySelector('details[data-sec=nova] .rp-tablewrap'); return t ? t.scrollWidth <= t.clientWidth + 1 : null; })(),
              cut: [...document.querySelectorAll('details[data-sec=meals] .rp-dh > *, details[data-sec=foods] .rp-dh > *, details[data-sec=nova] .rp-nrow > *, #rp-foods .rp-trend-h > *')].filter((e) => e.scrollWidth > e.clientWidth + 1).map((e) => e.className + ':' + e.textContent.slice(0, 20)) })""")
            check(f'{wd} px: the three sections do not scroll sideways and no label is cut off (the NOVA table fits too: {fits["wrap"]})', fits['page'] and fits['cut'] == [] and fits['wrap'], fits)
            small = await pg.evaluate(SIZES, '#rp-foods button, details[data-sec=meals] > summary, details[data-sec=foods] > summary, details[data-sec=nova] > summary, details[data-sec=novatable] > summary')
            check(f'{wd} px: the Foods measure button and the headers of the three sections (and "Show as table") are at least 44 px', small == [], small)
            for theme in ('light', 'dark'):
                await pg.evaluate("(t) => document.documentElement.setAttribute('data-theme', t)", theme)
                bad = [x for sel in ('details[data-sec=meals]', 'details[data-sec=foods]', 'details[data-sec=nova]') for x in await pg.evaluate(CONTRAST_JS, sel)]
                g1, g2 = await pg.evaluate(GFX, '#rp-foods'), await pg.evaluate(GFX, 'details[data-sec=nova] .card:nth-child(2)')
                check(f'{wd} px, {theme}: the text of the three sections has at least 4.5:1; the bars of Meals / Foods, the dashes and the outline of every NOVA segment have at least 3:1 against the card (the NOVA colours themselves are categories, some are about 2:1 on a light card: the outline keeps each shape visible)',
                      bad == [] and g1['--accent'] >= 3 and g1['--muted'] >= 3 and g2['--muted'] >= 3 and g2['outlineRatio'] >= 3, (bad[:3], g1['--accent'], g1['--muted'], g2['outline'], g2['outlineRatio'], g2['novaCats']))
            if SHOTS:
                for sec in ('meals', 'foods', 'nova'):
                    await pg.evaluate("(s) => document.querySelector(`details[data-sec=${s}]`).scrollIntoView()", sec)
                    await pg.screenshot(path=os.path.join(SHOTS, f'{sec}_{wd}.png'))
            await cx.close()

        # =========================================================== 10 speed with 6,000 entries
        cx, pg = await fresh(390, 844, 'S')
        foods12 = [own(f'u:k{i:02d}', f'Bulk food {i:02d}', {k: (i + 1) * (j + 1) / 7 for j, k in enumerate(['kcal', 'protein', 'carbohydrate', 'fat', 'fibres', 'salt', 'calcium', 'magnesium', 'iron', 'zinc', 'vitamin_c', 'vitamin_d', 'potassium', 'sodium', 'selenium', 'iodine'])}, nova=(i % 4) + 1 if i % 5 else None) for i in range(12)]
        bulk = []
        for k in range(365):
            d_ = (TODAY - timedelta(days=k)).isoformat()
            for j in range(16):
                bulk.append((f'k{k}_{j}', f'u:k{(k + j) % 12:02d}', 50 + j * 10, d_, f'm{1 + j % 6}'))
        await seed(bulk, foods=foods12, kind='year', pg=pg, open_all=True)
        t0 = time.perf_counter(); await pg.evaluate("() => window.__tapnaplo.render()"); dt = time.perf_counter() - t0
        m = await meals(pg); n = await nova(pg); f = await foods_(pg)
        check(f'6,000 entries over a year: the Report with the new sections renders in {dt:.2f} s (less than 3 s); six meals, ten foods and a line for the rest, twelve month bars', dt < 3 and len(m['meals']) == 6 and len(f['rows']) == 11 and len(n['bars']) == 12, [round(dt, 2), len(m['meals']), len(f['rows']), len(n['bars'])])
        shares = [int(r[3][:-1]) for r in f['rows']]
        check('...the shares of the foods add up to 100 and the meals to 100', sum(shares) == 100 and sum(int(x[3][:-1]) for x in m['meals']) == 100, [sum(shares), [x[3] for x in m['meals']]])
        t0 = time.perf_counter(); await pick_measure('calcium', pg); dt = time.perf_counter() - t0
        check(f'...changing the measure redraws the Trend and the Foods list in {dt:.2f} s (less than 1 s)', dt < 1 and (await foods_(pg))['measure'] == 'Calcium', round(dt, 2))
        await cx.close()

        # =========================================================== 11 the backup and the version
        cx, pg = await fresh(390, 844, 'B')
        await seed(WEEK, pg=pg)
        await pg.click('[data-tab=data]'); await pg.wait_for_selector('[data-act=export-json]')
        async with pg.expect_download() as dd:
            await pg.click('[data-act=export-json]')
        dl = await dd.value
        backup = json.loads(pathlib.Path(await dl.path()).read_text(encoding='utf-8'))
        check('the backup has exactly the keys it had before (nothing new is stored)', sorted(backup.keys()) == sorted(['app', 'version', 'exported', 'log', 'foods', 'meta', 'health', 'wlog']) and 'meals' not in json.dumps(backup['meta']), sorted(backup.keys()))
        ver = re.search(r'(\d+) · \d+ \w+ 20\d\d', await pg.evaluate('document.body.innerText'))
        check('the Data tab shows version 31 or newer', bool(ver) and int(ver.group(1)) >= 31, ver and ver.group(0))
        sw = open(ROOT / 'sw.js', encoding='utf-8').read()
        check('the service worker cache has the number of the version', bool(ver) and f"const CACHE = 'nutrilog-v{ver.group(1)}'" in sw)
        await cx.close()
        check('no page errors', errs == [], errs[:6])
        await browser.close()
        print('\nALL PASSED' if not problems else f'\n{len(problems)} FAILED: {problems}')
        sys.exit(1 if problems else 0)


asyncio.run(main())
