"""Report tab, Trend (version 30). Run with the web server on port 8765 (see CLAUDE.md).

A section "Trend" in the Report shows one measure (Energy to begin with) as bars over the period: one bar per day (periods up to 31 days), per week (up to 190 days, Monday to Sunday, the
outer weeks cut at the edges of the period) or per month. The value of a bar is the average per logged day inside it, with the rules of the rest of the Report: a bar with no logged day is a gap
(dashed base, never a 0), a bar whose items have no data for the measure is a dotted stub (never a 0), a striped bar is a lower value (some items have no data, "≥"), a light cap is a range
("<x" values), "≈" is the omega ratio worked out from part of the fatty acids. A reading line under the chart tells the selected bar in words; a finger, the mouse, the arrow keys or the
Previous / Next buttons change it; "Open day / week / month" makes the bar the period of the Report; "Show as table" has every value. The measure is chosen in a sheet (Calculated: Water
intake, Omega-6 : omega-3 ratio; then the nutrient groups) and kept on this device. An EFSA line is drawn only for a measure that has a reference value on its own and only with a profile.
The clock of the browser is fixed to Thursday 5 Nov 2026, 12:00 (Budapest), so every date below is exact.

Covers: the bucket maths (31 / 32 and 190 / 191 days, Monday weeks cut at both edges, a month cut, a leap February), a hand-calculated week (Energy, Protein, Magnesium, Calcium, Sodium,
Water, the omega ratio, Vitamin A and B1 without a line), the legend, the axis, the table, the spoken label, the reading line and the selection by pointer, drag, keys and buttons, Open day /
week / month, the measure sheet and the damaged saved values, the messages (one logged day, no data), month / 3 months / year / Custom bars, a period of one day (no Trend), the shared copy
(same bars as the sender, nothing written, Open day inside the link, the reference line with a profile in the link), 44 px, contrast of text and bars in light and dark, 390 and 320 px, speed
with 6,000 entries, the backup, the version number and no page errors."""
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
OPEN_TREND = {'overview': True, 'trend': True}
MKEY = 'nutrilog.reportMeasure'

LA, AA = 'fa_18_2_9c_12c_n_6', 'fa_20_4_5c_8c_11c_14c_n_6'
ALA, EPA, DHA = 'fa_18_3_c9_c12_c15_n_3', 'fa_20_5_5c_8c_11c_14c_17c_n_3_epa', 'fa_22_6_4c_7c_10c_13c_16c_19c_n_3_dha'


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

TREND = """() => { const q = (s) => document.querySelector(s), sec = q('details[data-sec=trend]'); if (!sec) return null;
  const tx = (el) => (el ? el.textContent.replace(/\\s+/g, ' ').trim() : null), r2 = (x) => Math.round(x * 100) / 100;
  const st = (n) => { const b = sec.querySelector(`[data-act=rp-trend-step][data-n="${n}"]`); return b ? !b.disabled : null; };
  const bars = [...sec.querySelectorAll('.rp-bar')].map((b) => ({ c: [...b.classList].filter((x) => x !== 'rp-bar').sort().join(' '), h: r2(parseFloat(b.style.getPropertyValue('--h'))), t: r2(parseFloat(b.style.getPropertyValue('--t'))) }));
  const ref = sec.querySelector('.rp-ref'), pl = sec.querySelector('.rp-plot'), tb = sec.querySelector('details[data-sec=trendtable]');
  return { open: sec.open, title: tx(sec.querySelector('summary')), measure: tx(sec.querySelector('.rp-measure')), unit: tx(sec.querySelector('.rp-trend-h .muted')), none: tx(sec.querySelector('.rp-trend-none')),
    bars, ticks: [...sec.querySelectorAll('.rp-y span')].map(tx), xs: [...sec.querySelectorAll('.rp-x span')].map(tx), read: tx(sec.querySelector('#rp-rd')), prev: st(-1), next: st(1),
    openBtn: tx(sec.querySelector('[data-act=rp-open-bucket]')), leg: [...sec.querySelectorAll('.rp-leg li')].map(tx), ref: ref ? { c: [...ref.classList].filter((x) => x !== 'rp-ref').join(' '), b: r2(parseFloat(ref.style.bottom)) } : null,
    label: pl ? pl.getAttribute('aria-label') : null, heads: [...sec.querySelectorAll('.rp-table thead th')].map(tx), rows: [...sec.querySelectorAll('.rp-table tbody tr')].map((tr) => [...tr.children].map(tx)),
    chart: !!sec.querySelector('.rp-chart'), tabopen: tb ? tb.open : null }; }"""

SEL = """() => { const q = (s) => document.querySelector(s); const bs = [...document.querySelectorAll('.rp-seg button')];
  return { pressed: bs.filter((b) => b.getAttribute('aria-pressed') === 'true').map((b) => b.dataset.kind), when: q('.rp-when b') ? q('.rp-when b').textContent : null, note: q('.rp-when span') ? q('.rp-when span').textContent : '',
    trend: !!q('details[data-sec=trend]'), title: q('#topbar h1') ? q('#topbar h1').textContent : null }; }"""

SIZES = "(sel) => [...document.querySelectorAll(sel)].filter((e) => !e.hidden && e.getClientRects().length).map((e) => { const r = e.getBoundingClientRect(); return [(e.id || e.dataset.act || e.className || e.tagName) + ':' + e.textContent.trim().slice(0, 14), Math.round(r.width), Math.round(r.height)]; }).filter((x) => x[2] < 44 || x[1] < 44)"

# the colour of the bars, the dashes and the line against the card behind them (3:1 for graphics)
GFX = """() => { const parse = (c) => { let m = c.match(/rgba?\\(([^)]+)\\)/); if (m) { const p = m[1].split(/[ ,\\/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; }
    m = c.match(/color\\(srgb ([^)]+)\\)/); if (m) { const p = m[1].split(/[ \\/]+/).filter(Boolean).map(Number); return [p[0] * 255, p[1] * 255, p[2] * 255, p.length > 3 ? p[3] : 1]; } return [0, 0, 0, 1]; };
  const lum = ([r, g, b]) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const card = document.querySelector('#rp-trend'), bg = (() => { for (let e = card; e; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor); if (c[3] >= 1) return c; } return parse(getComputedStyle(document.body).backgroundColor); })();
  const tok = (name) => { const s = document.createElement('span'); s.style.color = `var(${name})`; card.appendChild(s); const c = parse(getComputedStyle(s).color); s.remove(); return c; };
  const out = {}; for (const n of ['--accent', '--muted', '--ink']) out[n] = Math.round(ratio(tok(n), bg) * 100) / 100;
  const sel = document.querySelector('#rp-trend .rp-bar.sel'); out.sel = sel ? Math.round(ratio(parse(getComputedStyle(sel).backgroundColor), bg) * 100) / 100 : null;
  return out; }"""


def own(fid, name, n, **kw):
    f = {'id': fid, 'src': 'user', 'name': name, 'brand': '', 'barcode': '', 'basis': {'qty': 100, 'unit': 'g'}, 'n': n, 'nova': None, 'portions': [], 'note': '', 'created': 1000, 'updated': 1000}
    f.update(kw)
    return f


ALPHA = own('u:alpha', 'Alpha', {'kcal': 100, 'protein': 10, 'carbohydrate': 20, 'fat': 5, 'fibres': 2, 'salt': 0.5, 'calcium': 100, 'magnesium': 50, 'vitamin_c': 10})
BETA = own('u:beta', 'Beta', {'kcal': 200, 'protein': 5, 'carbohydrate': 30, 'fat': 10, 'fibres': 4, 'salt': 1, 'calcium': 200})
GAMMA = own('u:gamma', 'Gamma', {'kcal': 50})
CORE_FOODS = [ALPHA, BETA, GAMMA]
CORE = [('e1', 'u:alpha', 200, day(-3)), ('e2', 'u:beta', 100, day(-3)), ('e3', 'u:alpha', 100, day(-1)), ('e4', 'u:gamma', 100, day(-1)), ('e5', 'u:beta', 40, day(0))]   # Mon 2, Wed 4, Thu 5 Nov
CORE_WATER = {day(-3): 1500, day(-1): 2000}
REF_F = {'sex': 'f', 'age': '25', 'meno': 'pre', 'zinc': 600}

FISH = own('u:fish', 'Salmon', {'kcal': 200, LA: 0.5, AA: 0.1, ALA: 0.3, EPA: 1.0, DHA: 1.5})       # all five fatty acids: 0.6 / 2.8
OIL = own('u:oil', 'Rapeseed oil', {'kcal': 880, LA: 20, ALA: 9})                                       # only two of the five: 20 / 9
NOFA = own('u:nofa', 'No fatty acid data', {'kcal': 50})
OMEGA_FOODS = [FISH, OIL, NOFA]
OMEGA_ENT = [('o1', 'u:fish', 100, day(-3)), ('o2', 'u:oil', 100, day(-1)), ('o3', 'u:nofa', 100, day(0))]

SALTY = own('u:salty', 'Salty', {'kcal': 10, 'sodium': 800})
VITA = own('u:vita', 'Vitamins', {'kcal': 100, 'retinol': 100, 'vitamin_b1_or_thiamin': 1})

# a long sample: Sep, Oct and Nov (the Nov days are the CORE days)
MULTI = [('m1', 'u:alpha', 100, '2026-09-02'), ('m2', 'u:beta', 100, '2026-09-04'), ('m3', 'u:alpha', 200, '2026-10-14'), ('m4', 'u:alpha', 100, '2026-10-31'), ('m5', 'u:gamma', 100, '2026-11-01')] + CORE


def days_in(a, b):
    return (date.fromisoformat(b) - date.fromisoformat(a)).days + 1


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

        async def seed(entries, water=None, ref=None, foods=CORE_FOODS, kind='week', anchor=day(0), custom=None, open_all=OPEN_TREND, pg=page, tab='report', measure='kcal'):
            await pg.evaluate("""([foods, ents, water, ref, kind, anchor, custom, openAll, tab, measure]) => { const t = window.__tapnaplo, S = t.S;
              S.log.length = 0; for (const k of Object.keys(S.foods)) delete S.foods[k]; S.meta.ref = ref; S.meta.water = water || {}; S.meta.nova = {};
              for (const f of foods) S.foods[f.id] = f;
              ents.forEach(([id, f, a, d], i) => S.log.push({ id, f, a, d, m: 'm1', t: 1000 + i, tm: '08:' + String(10 + (i % 50)) }));
              if (measure === null) localStorage.removeItem('nutrilog.reportMeasure');
              t.RP.kind = kind; t.RP.anchor = anchor; t.RP.custom = custom; for (const k of Object.keys(t.RP.open)) t.RP.open[k] = typeof openAll === 'object' ? !!openAll[k] : openAll;
              S.tab = tab; t.save(); t.render(); }""", [foods, entries, water, ref, kind, anchor, custom, open_all, tab, measure])
            await pg.wait_for_timeout(40)
            if measure is not None and await pg.locator('#rp-trend .rp-measure:visible').count() and await pg.evaluate("() => window.__tapnaplo.curMeasure()") != measure:   # the measure of a running page is kept in memory: choose it like a person does
                await pick_measure(measure, pg)

        async def tr(pg=page):
            return await pg.evaluate(TREND)

        async def sel(pg=page):
            return await pg.evaluate(SEL)

        async def pick_measure(m, pg=page):
            await pg.click('#rp-trend .rp-measure'); await pg.wait_for_selector('.rp-m')
            await pg.click(f'.rp-m[data-m="{m}"]'); await pg.wait_for_timeout(40)

        async def pick(k, n, pg=page):
            await pg.locator('#rp-plot').scroll_into_view_if_needed()
            bb = await pg.locator('#rp-plot').bounding_box()
            await pg.mouse.click(bb['x'] + (k + 0.5) / n * bb['width'], bb['y'] + bb['height'] / 2)

        # =========================================================== 1 the bucket maths (pure)
        B = "(r) => window.__tapnaplo.rpBuckets(r)"

        async def buckets(a, b):
            return await T(B, {'from': a, 'to': b, 'days': days_in(a, b)})

        b31 = await buckets('2026-10-05', '2026-11-04')
        check('31 days: one bar per day (31 bars), the first is 5 Oct, the last 4 Nov', len(b31) == 31 and {x['unit'] for x in b31} == {'day'} and b31[0]['from'] == b31[0]['to'] == '2026-10-05' and b31[-1]['from'] == '2026-11-04', [len(b31), b31[0], b31[-1]])
        b32 = await buckets('2026-10-05', '2026-11-05')
        check('32 days: one bar per week: 5 Oct is a Monday, so 5 weeks, the last one cut at today (2 - 5 Nov)', len(b32) == 5 and {x['unit'] for x in b32} == {'week'} and [x['from'] for x in b32] == ['2026-10-05', '2026-10-12', '2026-10-19', '2026-10-26', '2026-11-02'] and b32[-1]['to'] == '2026-11-05' and b32[0]['to'] == '2026-10-11', b32)
        b190 = await buckets('2026-04-30', '2026-11-05')
        b191 = await buckets('2026-04-29', '2026-11-05')
        check('190 days: still weeks; 191 days: months', days_in('2026-04-30', '2026-11-05') == 190 and days_in('2026-04-29', '2026-11-05') == 191 and {x['unit'] for x in b190} == {'week'} and {x['unit'] for x in b191} == {'month'}, [len(b190), len(b191)])
        check('191 days from 29 Apr: 8 month bars, April is cut at the start (29 - 30 Apr) and November at the end (1 - 5 Nov)', len(b191) == 8 and b191[0]['from'] == '2026-04-29' and b191[0]['to'] == '2026-04-30' and b191[-1]['from'] == '2026-11-01' and b191[-1]['to'] == '2026-11-05' and b191[1]['from'] == '2026-05-01' and b191[1]['to'] == '2026-05-31', b191)
        bw = await buckets('2026-09-30', '2026-11-05')
        check('weeks are cut at the start too: Wed 30 Sep - Sun 4 Oct is the first bar, then whole Monday weeks, the last 2 - 5 Nov (6 bars)', len(bw) == 6 and (bw[0]['from'], bw[0]['to']) == ('2026-09-30', '2026-10-04') and (bw[1]['from'], bw[1]['to']) == ('2026-10-05', '2026-10-11') and (bw[-1]['from'], bw[-1]['to']) == ('2026-11-02', '2026-11-05'), bw)
        check('...the bars cover every day once: no gap and no overlap', all(days_in(bw[i]['to'], bw[i + 1]['from']) == 2 for i in range(len(bw) - 1)) and sum(days_in(x['from'], x['to']) for x in bw) == days_in('2026-09-30', '2026-11-05'))
        bl = await T(B, {'from': '2028-01-15', 'to': '2028-08-01', 'days': 200})
        feb = [x for x in bl if x['from'].startswith('2028-02')]
        check('a leap year: February 2028 is one month bar of 1 - 29 Feb; 200 days = months (Jan 15 - 31 first, 1 Aug last)', len(feb) == 1 and feb[0]['from'] == '2028-02-01' and feb[0]['to'] == '2028-02-29' and bl[0]['from'] == '2028-01-15' and bl[0]['to'] == '2028-01-31' and bl[-1]['from'] == '2028-08-01' and bl[-1]['to'] == '2028-08-01' and len(bl) == 8, [len(bl), feb])
        check('two days make two bars; a bar can be one day of a cut week', len(await buckets('2026-11-04', '2026-11-05')) == 2 and (await buckets('2026-10-04', '2026-10-12'))[0] == {'unit': 'day', 'from': '2026-10-04', 'to': '2026-10-04'})
        check('rpNiceMax: 0 and negative give 1; 420 gives 500; 105 gives 200; 997.5 gives 1000; 2.333 gives 2.5; 0.021 gives 0.025; 26.25 gives 50',
              await T("() => [0, -3, 420, 105, 997.5, 2.333, 0.021, 26.25, 1, 5, 10.5].map((x) => window.__tapnaplo.rpNiceMax(x))") == [1, 1, 500, 200, 1000, 2.5, 0.025, 50, 1, 5, 20])

        # =========================================================== 2 the week, Energy
        await seed(CORE, CORE_WATER, REF_F, open_all={'overview': True})
        t = await tr()
        check('the Trend section is there, called "Trend", and closed by default (only Overview is open)', t is not None and t['title'] == 'Trend' and t['open'] is False)
        await seed(CORE, CORE_WATER, REF_F)
        t = await tr()
        check('Energy is the measure to begin with; the line under the button says kcal a day, one bar = one day', t['measure'] == 'Energy' and t['unit'] == 'kcal a day · one bar = one day', [t['measure'], t['unit']])
        check('the week 2 - 5 Nov (so far) has 4 bars, one per day', len(t['bars']) == 4)
        check('...Mon 400 kcal (80% of 500), Tue no entries (a gap, dashed base), Wed 150 (30%), Thu 80 (16%); Thursday is selected', [(b['c'], b['h']) for b in t['bars']] == [('full', 80.0), ('none', 0.0), ('full', 30.0), ('full sel', 16.0)], t['bars'])
        check('...the axis: 500, 250, 0 (a "nice" top above 400 x 1.05), the x labels 2 Nov, 3 Nov, 5 Nov', t['ticks'] == ['500', '250', '0'] and t['xs'] == ['2 Nov', '3 Nov', '5 Nov'], [t['ticks'], t['xs']])
        check('...the reading line tells the selected bar in words: day, value with unit, items', t['read'] == 'Thu, 5 Nov · 80 kcal · 1 item', t['read'])
        check('...Previous bar is on, Next bar is off (Thursday is the last bar); the button says "Open day"', t['prev'] is True and t['next'] is False and t['openBtn'] == 'Open day', [t['prev'], t['next'], t['openBtn']])
        check('...the legend explains only what is on the chart: solid bars and the dashed gap (no stripes, no dotted stub, no cap, no line: Energy has no EFSA value)',
              t['leg'] == ['Solid bar: every item has data', 'Dashed base: no entries (not a 0)'] and t['ref'] is None, [t['leg'], t['ref']])
        check('...the chart is a focusable group with a spoken description: bars, range, highest, lowest, keys', 'Bar chart of Energy, 4 bars, one per day, from 2 Nov to 5 Nov. 3 of them have a value. Highest: 400 kcal on Mon, 2 Nov. Lowest: 80 kcal on Thu, 5 Nov.' in t['label'] and 'arrow keys' in t['label'] and 'The table below has all values.' in t['label']
              and await T("() => { const p = document.querySelector('#rp-plot'); return p.tabIndex === 0 && p.getAttribute('role') === 'group'; }"), t['label'])
        check('"Show as table" is closed; opened it has Day / Energy / Items and one row per bar, a gap says "no entries" with 0 items',
              t['tabopen'] is False and t['heads'] == ['Day', 'Energy', 'Items'] and t['rows'] == [['Mon, 2 Nov', '400 kcal', '2'], ['Tue, 3 Nov', 'no entries', '0'], ['Wed, 4 Nov', '150 kcal', '2'], ['Thu, 5 Nov', '80 kcal', '1']], [t['heads'], t['rows']])
        await page.click('details[data-sec=trendtable] > summary'); await page.wait_for_timeout(40)
        check('...the table fold opens and is remembered with the open parts', (await tr())['tabopen'] is True and json.loads(await T("() => localStorage.getItem('nutrilog.reportOpen')")).get('trendtable') is True)
        await page.click('details[data-sec=trendtable] > summary'); await page.wait_for_timeout(80)
        ro = json.loads(await T("() => localStorage.getItem('nutrilog.reportOpen')"))
        check('the open state of Trend is kept in the same saved choice as the other parts', ro.get('trend') is True and ro.get('trendtable') is False and ro.get('overview') is True, ro)

        # ---- selection: pointer, drag, keys, buttons
        await page.evaluate("() => { window.__plot = document.querySelector('#rp-plot'); }")
        await pick(0, 4)
        t = await tr()
        check('a tap on the first bar selects it: only that bar is marked, the reading line follows, Previous is off and Next is on',
              [b['c'] for b in t['bars']] == ['full sel', 'none', 'full', 'full'] and t['read'] == 'Mon, 2 Nov · 400 kcal · 2 items' and t['prev'] is False and t['next'] is True, [t['read'], t['prev'], t['next']])
        await pick(1, 4)
        t = await tr()
        check('a tap on the gap (Tuesday) selects it and the line says "no entries" - not 0 kcal', t['read'] == 'Tue, 3 Nov · no entries' and t['bars'][1]['c'] == 'none sel', t['read'])
        bb = await page.locator('#rp-plot').bounding_box()
        await page.mouse.move(bb['x'] + 0.125 * bb['width'], bb['y'] + 90); await page.mouse.down()
        await page.mouse.move(bb['x'] + 0.4 * bb['width'], bb['y'] + 90, steps=4); await page.mouse.move(bb['x'] + 0.63 * bb['width'], bb['y'] + 90, steps=4)
        mid = (await tr())['read']
        await page.mouse.up()
        t = await tr()
        check('dragging across the chart follows the finger: after the drag the third bar (Wed) is selected', mid == 'Wed, 4 Nov · 150 kcal · 2 items' and t['read'] == mid, [mid, t['read']])
        check('...the chart was not drawn again during the drag (the same element)', await T("() => document.querySelector('#rp-plot') === window.__plot"))
        await page.mouse.move(bb['x'] + 0.9 * bb['width'], bb['y'] + 90)      # moving with the button up changes nothing
        check('...moving the mouse without a pressed button does not change the selection', (await tr())['read'] == 'Wed, 4 Nov · 150 kcal · 2 items')
        await page.focus('#rp-plot')
        await page.keyboard.press('Home'); r1 = (await tr())['read']
        await page.keyboard.press('ArrowLeft'); r2 = (await tr())['read']
        await page.keyboard.press('ArrowRight'); await page.keyboard.press('ArrowRight'); r3 = (await tr())['read']
        await page.keyboard.press('End'); await page.keyboard.press('ArrowRight'); r4 = (await tr())['read']
        check('keys: Home goes to the first bar, ArrowLeft stays there, ArrowRight x2 gives Wed, End goes to the last, ArrowRight stays there',
              [r1, r2, r3, r4] == ['Mon, 2 Nov · 400 kcal · 2 items', 'Mon, 2 Nov · 400 kcal · 2 items', 'Wed, 4 Nov · 150 kcal · 2 items', 'Thu, 5 Nov · 80 kcal · 1 item'], [r1, r2, r3, r4])
        await page.click('[data-act=rp-trend-step][data-n="-1"]'); await page.click('[data-act=rp-trend-step][data-n="-1"]')
        t = await tr()
        check('the Previous bar button steps back (Thu - Wed - Tue) and the spoken reading line is a live region', t['read'] == 'Tue, 3 Nov · no entries' and await T("() => document.querySelector('#rp-rd').getAttribute('aria-live')") == 'polite', t['read'])

        # ---- Open day
        await pick(2, 4)
        await page.click('[data-act=rp-open-bucket]'); await page.wait_for_timeout(60)
        s = await sel()
        check('"Open day" on Wednesday makes 4 Nov the period of the Report (Day) and the Trend is gone for a single day', s['pressed'] == ['day'] and s['when'] is not None and '4 Nov' in s['when'] and s['trend'] is False, s)
        check('...the choice of period is saved like any other (Day)', json.loads(await T("() => localStorage.getItem('nutrilog.period')"))['kind'] == 'day')
        await page.click('[data-act=rp-kind][data-kind=week]'); await page.wait_for_timeout(40)
        s = await sel()
        check('back to Week: the week of 4 Nov (2 - 5 Nov, so far) has its Trend again', s['pressed'] == ['week'] and s['trend'] is True and s['when'] == '2–8 Nov 2026', s)

        # =========================================================== 3 other measures, same week
        await seed(CORE, CORE_WATER, REF_F)
        await pick_measure('protein')
        t = await tr()
        check('Protein: Mon 25 g (all items have data), Tue gap, Wed ≥ 10 g (Gamma has no data: a striped bar), Thu 2 g; the axis goes to 50',
              t['measure'] == 'Protein' and [(b['c'], b['h']) for b in t['bars']] == [('full', 50.0), ('none', 0.0), ('part', 20.0), ('full sel', 4.0)] and t['ticks'] == ['50', '25', '0'], [t['measure'], t['bars'], t['ticks']])
        check('...the legend now also explains the stripes; Protein has no EFSA line', t['leg'] == ['Solid bar: every item has data', 'Striped bar: a lower value (≥), some items have no data', 'Dashed base: no entries (not a 0)'] and t['ref'] is None, t['leg'])
        await pick(2, 4)
        t = await tr()
        check('...the reading line for the striped bar has "≥": "Wed, 4 Nov · ≥ 10 g · 2 items"; the table too', t['read'] == 'Wed, 4 Nov · ≥ 10 g · 2 items' and t['rows'][2] == ['Wed, 4 Nov', '≥ 10 g', '2'] and t['heads'] == ['Day', 'Protein', 'Items'], [t['read'], t['rows']])
        check('...the choice is kept on this device', await T("(k) => localStorage.getItem(k)", MKEY) == 'protein')

        await pick_measure('magnesium')
        t = await tr()
        check('Magnesium: Mon ≥ 100 mg, Wed ≥ 50 mg (only Alpha has data: striped), Thu: Beta has no data, so a dotted stub - not a 0; the selected last bar says "no data for Magnesium"',
              [(b['c'], b['h']) for b in t['bars']] == [('part', 20.0), ('none', 0.0), ('part', 10.0), ('nodata sel', 0.0)] and t['read'] == 'Thu, 5 Nov · no data for Magnesium · 1 item', [t['bars'], t['read']])
        check('...EFSA, female 25+: the AI of 300 mg is a dashed line at 60% of the axis (0 - 500), and the legend says what it is', t['ref'] == {'c': 'ai', 'b': 60.0} and t['ticks'] == ['500', '250', '0']
              and t['leg'][-1] == 'Line: reference intake 300 mg (AI). A bar below it is not a deficiency.' and 'Dotted stub: logged, but no data for this measure (not a 0)' in t['leg'], [t['ref'], t['leg']])
        check('...the table says "no data" for Thursday', t['rows'][3] == ['Thu, 5 Nov', 'no data', '1'], t['rows'])

        await pick_measure('calcium')
        t = await tr()
        check('Calcium: Mon 400 mg, Wed ≥ 100 mg, Thu 80 mg; the reference (PRI 950 mg for 25+) is a solid line at 95% of an axis that goes to 1,000 although the bars are lower',
              [(b['c'], b['h']) for b in t['bars']] == [('full', 40.0), ('none', 0.0), ('part', 10.0), ('full sel', 8.0)] and t['ref'] == {'c': 'pri', 'b': 95.0} and t['ticks'] == ['1,000', '500', '0'], [t['bars'], t['ref'], t['ticks']])
        check('...the legend: "Line: reference intake 950 mg (PRI). A bar below it is not a deficiency."', 'Line: reference intake 950 mg (PRI). A bar below it is not a deficiency.' in t['leg'], t['leg'])
        await seed(CORE, CORE_WATER, None, measure='calcium')
        t = await tr()
        check('without a profile there is no line and no legend line for it, and the axis fits the bars (0 - 500)', t['ref'] is None and not any(x.startswith('Line') for x in t['leg']) and t['ticks'] == ['500', '250', '0'], [t['ref'], t['ticks']])

        await seed([('s1', 'u:salty', 100, day(-3)), ('s2', 'u:salty', 200, day(-1)), ('s3', 'u:salty', 100, day(0))], None, REF_F, foods=[SALTY], measure='sodium')
        t = await tr()
        check('Sodium: 800, 1,600, 800 mg; the EFSA value is a SAI (safe and adequate intake), so a dotted line at 80% of 2,500 and "not a target" in the legend',
              [b['h'] for b in t['bars']] == [32.0, 0.0, 64.0, 32.0] and t['ref'] == {'c': 'sai', 'b': 80.0} and t['ticks'] == ['2,500', '1,250', '0']
              and 'Line: reference intake 2,000 mg (SAI, not a target). A bar below it is not a deficiency.' in t['leg'], [t['bars'], t['ref'], t['leg']])

        await seed([('v1', 'u:vita', 100, day(-3)), ('v2', 'u:vita', 100, day(-1)), ('v3', 'u:vita', 100, day(0))], None, REF_F, foods=[VITA], measure='retinol')
        t = await tr()
        check('Vitamin A (retinol) and Vitamin B1 have an EFSA row in other units (RE with beta-carotene; per MJ of energy), so the Trend draws no line for them',
              t['measure'] == 'Vitamin A (retinol)' and t['ref'] is None and not any(x.startswith('Line') for x in t['leg']), [t['measure'], t['ref'], t['leg']])
        await pick_measure('vitamin_b1_or_thiamin')
        t = await tr()
        check('...Vitamin B1: no line either, the bars are the plain amounts (1 mg on each logged day)', t['ref'] is None and [b['c'] for b in t['bars']] == ['full', 'none', 'full', 'full sel'] and t['read'] == 'Thu, 5 Nov · 1 mg · 1 item', [t['ref'], t['read']])

        await seed(CORE, CORE_WATER, REF_F, measure='sugars')
        t = await tr()
        check('Sugars: nobody has data, so there is nothing to draw and the card says so - and that this is not zero (the measure button stays)',
              t['chart'] is False and t['none'] == 'No item in this period has data for Sugars, so there is nothing to draw. This is not zero.' and t['measure'] == 'Sugars', [t['chart'], t['none']])

        await seed(CORE, CORE_WATER, REF_F, measure='water_intake')
        t = await tr()
        check('Water intake: 1,500 mL on Mon, 2,000 mL on Wed, the days without water are gaps (Thursday has food but no water: "no water logged"); the axis goes to 2,500; the line says it is the average of the days with water logged',
              t['measure'] == 'Water intake' and [(b['c'], b['h']) for b in t['bars']] == [('full', 60.0), ('none', 0.0), ('full sel', 80.0), ('none', 0.0)] and t['ticks'] == ['2,500', '1,250', '0']
              and t['unit'] == 'mL a day, average of the days with water logged · one bar = one day', [t['bars'], t['ticks'], t['unit']])
        check('...the last bar with water (Wed) is selected: "Wed, 4 Nov · 2,000 mL" (no item count for water); legend and table use "no water logged"',
              t['read'] == 'Wed, 4 Nov · 2,000 mL' and t['leg'] == ['Average of the days with water logged', 'Dashed base: no water logged (not a 0)'] and t['rows'] == [['Mon, 2 Nov', '1,500 mL', ''], ['Tue, 3 Nov', 'no water logged', ''], ['Wed, 4 Nov', '2,000 mL', ''], ['Thu, 5 Nov', 'no water logged', '']] and t['ref'] is None, [t['read'], t['leg'], t['rows']])
        await seed(CORE, {day(-1): 2000}, REF_F, measure='water_intake')
        t = await tr()
        check('Water on one day only: "A trend needs at least two days with water logged in this period."', t['chart'] is False and t['none'] == 'A trend needs at least two days with water logged in this period.', t['none'])

        # ---- the omega ratio
        await seed(OMEGA_ENT, None, REF_F, foods=OMEGA_FOODS, measure='omega_ratio')
        t = await tr()
        check('Omega-6 : omega-3 ratio: Mon 0.6 / 2.8 = 0.21 (all five fatty acids: solid), Wed 20 / 9 = 2.22 (only two of the five: striped, "≈"), Thu: no data (dotted stub)',
              t['measure'] == 'Omega-6 : omega-3 ratio' and [(b['c'], b['h']) for b in t['bars']] == [('full', 8.57), ('none', 0.0), ('part', 88.89), ('nodata sel', 0.0)] and t['ticks'] == ['2.5', '1.25', '0'], [t['measure'], t['bars'], t['ticks']])
        check('...the unit line says "ratio of the totals"; the reading lines: "no data for ..." on Thu, "≈ 2.22 : 1" on Wed, "0.21 : 1" on Mon',
              t['unit'] == 'ratio of the totals · one bar = one day' and t['read'] == 'Thu, 5 Nov · no data for Omega-6 : omega-3 ratio · 1 item', [t['unit'], t['read']])
        await pick(2, 4); r_wed = (await tr())['read']
        await pick(0, 4); r_mon = (await tr())['read']
        check('...Wed: "Wed, 4 Nov · ≈ 2.22 : 1 · 1 item", Mon: "Mon, 2 Nov · 0.21 : 1 · 1 item"', r_wed == 'Wed, 4 Nov · ≈ 2.22 : 1 · 1 item' and r_mon == 'Mon, 2 Nov · 0.21 : 1 · 1 item', [r_wed, r_mon])
        check('...the legend explains "≈ Striped bar: worked out from the values that exist"; no EFSA line for the ratio', t['leg'] == ['Solid bar: every item has data', '≈ Striped bar: worked out from the values that exist', 'Dashed base: no entries (not a 0)', 'Dotted stub: logged, but no data for this measure (not a 0)'] and t['ref'] is None, t['leg'])
        check('...the table: 0.21 : 1, no entries, ≈ 2.22 : 1, no data', t['rows'] == [['Mon, 2 Nov', '0.21 : 1', '1'], ['Tue, 3 Nov', 'no entries', '0'], ['Wed, 4 Nov', '≈ 2.22 : 1', '1'], ['Thu, 5 Nov', 'no data', '1']], t['rows'])

        # =========================================================== 4 the measure sheet and the saved choice
        await seed(CORE, CORE_WATER, REF_F, measure='kcal')
        await T("() => localStorage.removeItem('nutrilog.reportMeasure')")
        await page.click('#rp-trend .rp-measure'); await page.wait_for_selector('.rp-m')
        sh = await page.evaluate("""() => { const s = document.querySelector('.sheet'); const hs = [...s.querySelectorAll('.rp-mh')].map((h) => h.textContent);
          const bs = [...s.querySelectorAll('.rp-m')].map((b) => [b.dataset.m, b.childNodes[0].textContent, b.getAttribute('aria-pressed'), b.querySelector('small') ? b.querySelector('small').textContent : '']);
          return { title: s.querySelector('h2, .sheet-h, header') ? (s.querySelector('h2, .sheet-h, header').textContent || '') : s.textContent.slice(0, 40), hs, bs, n: window.__tapnaplo.KEYS.length, close: !!s.querySelector('.sheet-actions [data-x]'), actions: !!s.querySelector('.sheet-actions') }; }""")
        check('the measure sheet: first the group "Calculated" with Water intake and Omega-6 : omega-3 ratio, then the nutrient groups of the Nutrients tab; one button per nutrient',
              sh['hs'][0] == 'Calculated' and [x[0] for x in sh['bs'][:2]] == ['water_intake', 'omega_ratio'] and len(sh['bs']) == 2 + sh['n'] and 'Energy & macronutrients' in sh['hs'] and len(sh['hs']) >= 5, [sh['hs'], len(sh['bs']), sh['n']])
        check('...Energy is the chosen one (aria-pressed); a nutrient nobody has data for in this period says "no data" (Sugars), one with data does not (Calcium)',
              [x[2] for x in sh['bs'] if x[0] == 'kcal'] == ['true'] and sum(1 for x in sh['bs'] if x[2] == 'true') == 1 and [x[3] for x in sh['bs'] if x[0] == 'sugars'] == ['no data'] and [x[3] for x in sh['bs'] if x[0] == 'calcium'] == [''], [x for x in sh['bs'] if x[0] in ('kcal', 'sugars', 'calcium')])
        check('...the sheet has its Close button in the sticky action bar', sh['close'] and sh['actions'])
        await page.click('.sheet-actions [data-x]'); await page.wait_for_timeout(260)
        check('Close leaves the measure as it was and writes nothing', (await tr())['measure'] == 'Energy' and await T("() => localStorage.getItem('nutrilog.reportMeasure')") is None)
        await pick_measure('calcium')
        check('choosing Calcium closes the sheet, redraws only the Trend card and names the measure', (await tr())['measure'] == 'Calcium' and await T("() => !document.querySelector('.sheet')") and await T("(k) => localStorage.getItem(k)", MKEY) == 'calcium')
        await page.wait_for_timeout(200)
        await T("() => localStorage.setItem('nutrilog.tab', 'report')")
        await page.reload(); await page.wait_for_selector('.rp-seg'); await page.wait_for_selector('#rp-trend .rp-measure')
        t = await tr()
        check('after a reload the Report tab opens with the measure Calcium and the Trend (still open)', t is not None and t['measure'] == 'Calcium' and t['open'] is True, [t and t['measure']])

        async def with_measure(value, expect, label):
            await page.evaluate("(v) => { localStorage.setItem('nutrilog.reportMeasure', v); }", value)
            await page.reload(); await page.wait_for_selector('.rp-seg'); await page.wait_for_selector('#rp-trend .rp-measure')
            m = await T("() => window.__tapnaplo.curMeasure()")
            t_ = await tr()
            check(f'damaged saved measure ({label}): {expect} and the Trend card is drawn without an error', m == expect and t_ is not None and (t_['bars'] != [] or t_['none'] is not None), m)
        await with_measure('constructor', 'kcal', '"constructor"')
        await with_measure('__proto__', 'kcal', '"__proto__"')
        await with_measure('nonsense', 'kcal', 'an unknown key')
        await with_measure('', 'kcal', 'an empty text')
        await with_measure('water_intake', 'water_intake', 'a valid key: Water intake')
        await with_measure('omega_ratio', 'omega_ratio', 'a valid key: the ratio')
        await with_measure('vitamin_b12', 'vitamin_b12', 'a valid nutrient')
        await T("() => localStorage.removeItem('nutrilog.reportMeasure')")

        # =========================================================== 5 messages
        await seed([('a1', 'u:alpha', 100, day(-1))], None, REF_F)
        t = await tr()
        check('one logged day in a week: "A trend needs at least two days with entries in this period." - no chart, the measure button stays', t['chart'] is False and t['none'] == 'A trend needs at least two days with entries in this period.' and t['measure'] == 'Energy', [t['chart'], t['none']])
        await seed(CORE, CORE_WATER, REF_F, kind='day')
        check('a single day (Day) has no Trend section at all', (await sel())['trend'] is False and await T("() => !document.querySelector('#rp-trend')"))
        await seed(CORE, CORE_WATER, REF_F, kind='custom', custom={'from': day(0), 'to': day(0)})
        check('...nor a Custom range of one day', (await sel())['trend'] is False)
        await seed(CORE, CORE_WATER, REF_F, kind='custom', custom={'from': day(-1), 'to': day(0)})
        t = await tr()
        check('a Custom range of two days has two bars: Wed 150 kcal, Thu 80 kcal (selected, the last)', len(t['bars']) == 2 and t['read'] == 'Thu, 5 Nov · 80 kcal · 1 item' and [b['c'] for b in t['bars']] == ['full', 'full sel'] and t['xs'] == ['4 Nov', '', '5 Nov'], [t['bars'], t['xs'], t['read']])
        await seed([], None, REF_F)
        check('an empty period shows the empty card and no Trend', await T("() => !document.querySelector('#rp-trend') && !!document.querySelector('[data-act=tab][data-tab=log]')"))

        # =========================================================== 6 month, 3 months, year, Custom
        SEP = await T("() => new Date(2026, 8, 1).toLocaleDateString('en-GB', { month: 'short' })")      # "Sept" or "Sep", whatever the browser's ICU writes
        await seed(MULTI, None, None, kind='month', anchor='2026-10-26')
        t = await tr()
        s = await sel()
        check('Month (October): 31 bars, one per day; 3 of them logged (1, 14 and 31 Oct), the rest are gaps; the middle label is 16 Oct',
              s['when'] == 'October 2026' and len(t['bars']) == 31 and [i for i, b in enumerate(t['bars']) if b['c'].startswith('full')] == [13, 30] and t['xs'] == ['1 Oct', '16 Oct', '31 Oct'], [s['when'], len(t['bars']), t['xs'], [i for i, b in enumerate(t['bars']) if b['c'].startswith('full')]])
        check('...Oct 14 is 200 kcal and Oct 31 is 100 kcal (the last logged day is selected); no bar for 1 Oct (no entries on that day)', t['rows'][13] == ['Wed, 14 Oct', '200 kcal', '1'] and t['read'] == 'Sat, 31 Oct · 100 kcal · 1 item' and t['rows'][0] == ['Thu, 1 Oct', 'no entries', '0'], [t['rows'][13], t['read']])

        await seed(MULTI, None, REF_F, kind='m3')
        t = await tr()
        s = await sel()
        check('3 months (Sep - 5 Nov, 66 days): one bar per week, 10 bars; the first week is cut to Tue 1 - Sun 6 Sep, the last to 2 - 5 Nov', s['when'] is not None and len(t['bars']) == 10 and t['rows'][0][0] == f'1–6 {SEP}' and t['rows'][9][0] == '2–5 Nov' and t['rows'][4][0] == f'28 {SEP} – 4 Oct', [s['when'], len(t['bars']), [r[0] for r in t['rows']]])
        check('...a week bar is the average per logged day: 1 - 6 Sep (100 and 200 kcal) = 150; 12 - 18 Oct = 200; 26 Oct - 1 Nov (100 and 50) = 75; 2 - 5 Nov (400, 150, 80) = 210',
              [t['rows'][i][1] for i in (0, 6, 8, 9)] == ['150 kcal', '200 kcal', '75 kcal', '210 kcal'], [t['rows'][i] for i in (0, 6, 8, 9)])
        check('...with the number of logged days and items in the table (Logged days, Items); the headings say Week / Energy / Logged days / Items; a week row is named by its dates only (the column says Week)',
              t['heads'] == ['Week', 'Energy', 'Logged days', 'Items'] and t['rows'][0][2:] == ['2', '2'] and t['rows'][9][2:] == ['3', '5'] and t['rows'][1] == [f'7–13 {SEP}', 'no entries', '0', '0'], [t['heads'], t['rows'][0], t['rows'][9], t['rows'][1]])
        check('...the bars are heights of 60%, 80%, 30%, 84% of an axis that goes to 250; the unit line says "average of the logged days, one bar = one week"',
              [t['bars'][i]['h'] for i in (0, 6, 8, 9)] == [60.0, 80.0, 30.0, 84.0] and t['ticks'] == ['250', '125', '0'] and t['unit'] == 'kcal a day, average of the logged days · one bar = one week', [t['ticks'], t['unit']])
        check('...the selected (last) bar says "Week of 2–5 Nov · 210 kcal · 3 logged days · 5 items" and the button says "Open week"', t['read'] == 'Week of 2–5 Nov · 210 kcal · 3 logged days · 5 items' and t['openBtn'] == 'Open week', [t['read'], t['openBtn']])
        await pick(6, 10)
        t = await tr()
        check('a bar with one logged day says "1 logged day"', t['read'] == 'Week of 12–18 Oct · 200 kcal · 1 logged day · 1 item', t['read'])
        await page.click('[data-act=rp-open-bucket]'); await page.wait_for_timeout(60)
        s = await sel(); t = await tr()
        check('"Open week" on 12 - 18 Oct: that week is the period (over, no "so far"), but it has one logged day only, so the card says a trend needs two', s['pressed'] == ['week'] and s['when'] == '12–18 Oct 2026' and s['note'] == '' and t['chart'] is False and t['none'] == 'A trend needs at least two days with entries in this period.', [s, t['none']])
        await seed(MULTI, None, REF_F, kind='m3')
        await pick(0, 10)
        await page.click('[data-act=rp-open-bucket]'); await page.wait_for_timeout(60)
        s = await sel(); t = await tr()
        check('"Open week" on the first (cut) week of September makes the whole Monday week 31 Aug - 6 Sept the period; its Trend has 7 day bars, 2 and 4 Sept are logged (100 and 200 kcal)',
              s['pressed'] == ['week'] and s['when'].startswith('31 Aug') and len(t['bars']) == 7 and t['rows'][2] == ['Wed, 2 ' + SEP, '100 kcal', '1'] and t['rows'][4] == ['Fri, 4 ' + SEP, '200 kcal', '1'] and t['read'] == 'Fri, 4 ' + SEP + ' · 200 kcal · 1 item', [s, len(t['bars']), t['rows'][2:5]])

        await seed(MULTI, None, REF_F, kind='year')
        t = await tr()
        check('Year (Dec 2025 - 5 Nov 2026): 12 month bars, December 2025 first, November 2026 (cut at today) last; Sep and Oct 150 kcal, Nov 170 kcal (50, 400, 150, 80 over 4 logged days)',
              len(t['bars']) == 12 and t['rows'][0][0] == 'December 2025' and t['rows'][11][0] == 'November 2026' and [t['rows'][i][1] for i in (9, 10, 11)] == ['150 kcal', '150 kcal', '170 kcal'] and t['heads'] == ['Month', 'Energy', 'Logged days', 'Items'], [len(t['bars']), t['rows'][0], t['rows'][9:], t['heads']])
        check('...heights 75%, 75%, 85% of an axis that goes to 200; x labels Dec 2025, (the middle), Nov 2026; the button says "Open month"',
              [t['bars'][i]['h'] for i in (9, 10, 11)] == [75.0, 75.0, 85.0] and t['ticks'] == ['200', '100', '0'] and t['xs'][0] == 'Dec 2025' and t['xs'][2] == 'Nov 2026' and t['openBtn'] == 'Open month', [t['ticks'], t['xs'], t['openBtn']])
        check('...the selected last bar: "November 2026 · 170 kcal · 4 logged days · 6 items"', t['read'] == 'November 2026 · 170 kcal · 4 logged days · 6 items', t['read'])
        await pick(9, 12)
        await page.click('[data-act=rp-open-bucket]'); await page.wait_for_timeout(60)
        s = await sel(); t = await tr()
        check('"Open month" on September makes September 2026 the period (Month, 30 days) and the Trend shows 30 days', s['pressed'] == ['month'] and s['when'] == 'September 2026' and len(t['bars']) == 30 and t['rows'][1] == ['Wed, 2 ' + SEP, '100 kcal', '1'], [s, len(t['bars'])])

        await seed(MULTI, None, REF_F, kind='custom', custom={'from': '2026-10-05', 'to': '2026-11-04'})
        check('Custom, 31 days: day bars; 32 days: week bars (5 Oct - 5 Nov)', len((await tr())['bars']) == 31 and (await tr())['heads'][0] == 'Day')
        await seed(MULTI, None, REF_F, kind='custom', custom={'from': '2026-10-05', 'to': '2026-11-05'})
        t = await tr()
        check('...32 days', len(t['bars']) == 5 and t['heads'][0] == 'Week' and t['rows'][4][0] == '2–5 Nov', [len(t['bars']), t['heads']])
        await seed(MULTI, None, REF_F, kind='custom', custom={'from': '2026-04-29', 'to': '2026-11-05'})
        t = await tr()
        check('...191 days: month bars (8), April cut to 29 - 30 Apr', len(t['bars']) == 8 and t['heads'][0] == 'Month' and t['rows'][0][0] == 'April 2026', [len(t['bars']), t['rows'][0]])

        # one more thing about weeks: a logged day whose food is not in the tables is not counted
        await seed(CORE + [('h1', 'u:missing', 100, day(-2))], CORE_WATER, REF_F)
        t = await tr()
        check('an entry whose food cannot be loaded is not a logged day: Tuesday stays a gap (and the Report warns about the hidden entry)', t['bars'][1]['c'] == 'none' and 'is not counted' in await page.inner_text('.banner.warn'), t['bars'][1])

        # =========================================================== 7 the shared copy
        VF, VT = day(-5), day(0)         # Sat 31 Oct - Thu 5 Nov
        await seed(CORE, CORE_WATER, REF_F, kind='custom', custom={'from': VF, 'to': VT})
        link = await T("([a, b]) => window.__tapnaplo.shareLink(a, b, true).then((r) => r.url)", [VF, VT])
        snap_kcal_sender = await tr()
        await pick_measure('calcium')
        snap_ca_sender = await tr()
        vctx = await new_ctx(390, 844)
        vp = await vctx.new_page(); watch(vp, 'V')
        await vp.goto(link); await vp.wait_for_selector('.hero')
        await vp.click('[data-tab=report]'); await vp.wait_for_selector('.rp-seg'); await vp.wait_for_selector('#rp-trend', state='attached')
        await vp.evaluate("() => { const s = document.querySelector('details[data-sec=trend]'); s.open = true; }"); await vp.wait_for_timeout(40)
        tv = await tr(vp)
        check('the shared copy shows the same Trend as the sender (Energy): bars, axis, reading line, legend, table', tv is not None and {k: tv[k] for k in ('bars', 'ticks', 'xs', 'read', 'leg', 'rows', 'heads', 'unit', 'measure', 'label')} == {k: snap_kcal_sender[k] for k in ('bars', 'ticks', 'xs', 'read', 'leg', 'rows', 'heads', 'unit', 'measure', 'label')},
              [tv and tv['read'], snap_kcal_sender['read']])
        check('...6 day bars (31 Oct - 5 Nov), the viewer starts with Custom = the whole shared range', len(tv['bars']) == 6 and (await sel(vp))['pressed'] == ['custom'], len(tv['bars']))
        await pick_measure('calcium', vp)
        tvc = await tr(vp)
        check('...Calcium with the profile that is in the link: the same bars and the same PRI line as the sender', {k: tvc[k] for k in ('bars', 'ticks', 'ref', 'leg', 'rows', 'read')} == {k: snap_ca_sender[k] for k in ('bars', 'ticks', 'ref', 'leg', 'rows', 'read')} and tvc['ref'] == {'c': 'pri', 'b': 95.0}, [tvc['ref'], tvc['read'], snap_ca_sender['read']])
        await vp.click('[data-act=rp-trend-step][data-n="-1"]')
        await vp.click('[data-act=rp-open-bucket]'); await vp.wait_for_timeout(60)
        sv = await sel(vp)
        check('"Open day" in the shared copy works inside the link: Wed 4 Nov becomes the period (Day), the Trend is gone', sv['pressed'] == ['day'] and '4 Nov' in sv['when'] and sv['trend'] is False, sv)
        w = await vp.evaluate("() => window.__w")
        check('the viewer wrote nothing: no localStorage write (neither the measure nor the period nor the open parts), no IndexedDB opened', w['ls'] == [] and w['idb'] == 0, w)
        await vp.click('[data-act=rp-kind][data-kind=custom]'); await vp.wait_for_selector('#rc-apply')
        await vp.click('.sheet [data-x]'); await vp.wait_for_timeout(260)
        check('...and the measure of the viewer\'s own diary on this address is untouched', await vp.evaluate("() => localStorage.getItem('nutrilog.reportMeasure')") is None)
        await vctx.close()

        # a link without a profile has no line
        await seed(CORE, CORE_WATER, REF_F, kind='custom', custom={'from': VF, 'to': VT}, measure='calcium')
        link2 = await T("([a, b]) => window.__tapnaplo.shareLink(a, b, false).then((r) => r.url)", [VF, VT])
        vctx = await new_ctx(390, 844)
        vp = await vctx.new_page(); watch(vp, 'V2')
        await vp.goto(link2); await vp.wait_for_selector('.hero')
        await vp.click('[data-tab=report]'); await vp.wait_for_selector('#rp-trend', state='attached')
        await vp.evaluate("() => { const s = document.querySelector('details[data-sec=trend]'); s.open = true; }")
        await pick_measure('calcium', vp)
        tv2 = await tr(vp)
        check('a link made without the reference intake settings draws no line (the viewer has no profile)', tv2['ref'] is None and not any(x.startswith('Line') for x in tv2['leg']), [tv2['ref'], tv2['leg']])
        await vctx.close()

        # =========================================================== 8 layout, 44 px, contrast
        for w in (390, 320):
            cx, pg = await fresh(w, 844, f'L{w}')
            await seed(MULTI, CORE_WATER, REF_F, kind='m3', open_all=True, pg=pg, measure='calcium')
            await pg.evaluate("() => document.querySelectorAll('#view details').forEach((d) => { d.open = true; })"); await pg.wait_for_timeout(60)
            fits = await pg.evaluate("""() => ({ page: document.documentElement.scrollWidth <= window.innerWidth, tab: (() => { const t = document.querySelector('#rp-trend .rp-tablewrap'); return t ? t.scrollWidth <= t.clientWidth + 1 : null; })(),
              cut: [...document.querySelectorAll('#rp-trend .rp-trend-h > *, #rp-trend .rp-read > *, #rp-trend .rp-leg li, #rp-trend .rp-x span')].filter((e) => e.scrollWidth > e.clientWidth + 1).map((e) => e.className + ':' + e.textContent.slice(0, 20)) })""")
            check(f'{w} px: the Trend with the legend and the table open does not scroll sideways, and no label is cut off', fits['page'] and fits['tab'] and fits['cut'] == [], fits)
            small = await pg.evaluate(SIZES, '#rp-trend button, #rp-trend summary, #rp-trend [data-act]')
            check(f'{w} px: the measure button, Previous / Next bar, Open week and "Show as table" are at least 44 px', small == [], small)
            plot = await pg.evaluate("() => { const r = document.querySelector('#rp-plot').getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; }")
            check(f'{w} px: the plot is 180 px high and wide enough for 10 bars of 12 px or more', plot[1] == 180 and plot[0] / 10 >= 12, plot)
            for theme in ('light', 'dark'):
                await pg.evaluate("(t) => document.documentElement.setAttribute('data-theme', t)", theme)
                bad = await pg.evaluate(CONTRAST_JS, '#rp-trend')
                g = await pg.evaluate(GFX)
                check(f'{w} px, {theme}: the text of the Trend has at least 4.5:1; the bars, the dashes and the line have at least 3:1 against the card', bad == [] and g['--accent'] >= 3 and g['--muted'] >= 3 and g['--ink'] >= 3, (bad[:3], g))
            if SHOTS:
                await pg.evaluate("() => document.querySelector('#rp-trend').scrollIntoView()")
                await pg.screenshot(path=os.path.join(SHOTS, f'trend_{w}.png'))
            await pg.click('#rp-trend .rp-measure'); await pg.wait_for_selector('.rp-m'); await pg.wait_for_timeout(250)
            ms = [await pg.evaluate(SIZES, '.sheet button'), await pg.evaluate("() => { const s = document.querySelector('.sheet-b'); return s.scrollWidth <= s.clientWidth + 1; }")]
            check(f'{w} px: the measure sheet has buttons of 44 px or more and does not scroll sideways', ms[0] == [] and ms[1], ms)
            for theme in ('light', 'dark'):
                await pg.evaluate("(t) => document.documentElement.setAttribute('data-theme', t)", theme)
                check(f'{w} px, {theme}: the measure sheet has enough contrast', await pg.evaluate(CONTRAST_JS, '.sheet') == [])
            await cx.close()

        # =========================================================== 9 speed with 6,000 entries
        cx, pg = await fresh(390, 844, 'S')
        foods12 = [own(f'u:k{i:02d}', f'Bulk food {i:02d}', {k: (i + 1) * (j + 1) / 7 for j, k in enumerate(['kcal', 'protein', 'carbohydrate', 'fat', 'fibres', 'salt', 'calcium', 'magnesium', 'iron', 'zinc', 'vitamin_c', 'vitamin_d', 'potassium', 'sodium', 'selenium', 'iodine'])}) for i in range(12)]
        bulk = []
        for k in range(365):
            d_ = (TODAY - timedelta(days=k)).isoformat()
            for j in range(16):
                bulk.append((f'k{k}_{j}', f'u:k{(k + j) % 12:02d}', 50 + j * 10, d_))
        await seed(bulk, None, REF_F, foods=foods12, kind='year', pg=pg, open_all=True)
        t0 = time.perf_counter(); await pg.evaluate("() => window.__tapnaplo.render()"); dt = time.perf_counter() - t0
        t = await tr(pg)
        check(f'6,000 entries over a year: the Report with the Trend renders in {dt:.2f} s (less than 3 s); 12 month bars, all with a value', dt < 3 and len(t['bars']) == 12 and all(b['c'].startswith('full') for b in t['bars']), [round(dt, 2), t['bars'][:2]])
        t0 = time.perf_counter(); await pick_measure('calcium', pg); dt = time.perf_counter() - t0
        check(f'...changing the measure redraws the Trend in {dt:.2f} s (less than 1 s)', dt < 1 and (await tr(pg))['measure'] == 'Calcium', round(dt, 2))
        await pg.evaluate("() => { const t = window.__tapnaplo; t.RP.kind = 'custom'; t.RP.custom = { from: '2026-05-10', to: '2026-11-05' }; }")
        t0 = time.perf_counter(); await pg.evaluate("() => window.__tapnaplo.render()"); dt = time.perf_counter() - t0
        t = await tr(pg)
        check(f'...a Custom range of 180 days: 26 or 27 week bars, rendered in {dt:.2f} s (less than 3 s)', dt < 3 and len(t['bars']) in (26, 27), [round(dt, 2), len(t['bars'])])
        await cx.close()

        # =========================================================== 10 the backup and the version
        cx, pg = await fresh(390, 844, 'B')
        await seed(CORE, CORE_WATER, REF_F, kind='month', pg=pg, measure='calcium')
        await pg.click('[data-tab=data]'); await pg.wait_for_selector('[data-act=export-json]')
        async with pg.expect_download() as dd:
            await pg.click('[data-act=export-json]')
        dl = await dd.value
        backup = json.loads(pathlib.Path(await dl.path()).read_text(encoding='utf-8'))
        check('the backup has exactly the keys it had before the Trend (the measure is a setting of this device, not in the backup)', sorted(backup.keys()) == sorted(['app', 'version', 'exported', 'log', 'foods', 'meta', 'health', 'wlog']) and 'reportMeasure' not in json.dumps(backup) and 'calcium' not in json.dumps(backup['meta']), sorted(backup.keys()))
        ver = re.search(r'(\d+) · \d+ \w+ 20\d\d', await pg.evaluate('document.body.innerText'))
        check('the Data tab shows version 30 or newer', bool(ver) and int(ver.group(1)) >= 30, ver and ver.group(0))
        sw = open(ROOT / 'sw.js', encoding='utf-8').read()
        check('the service worker cache has the number of the version', bool(ver) and f"const CACHE = 'nutrilog-v{ver.group(1)}'" in sw)
        await cx.close()
        check('no page errors', errs == [], errs[:6])
        await browser.close()
        print('\nALL PASSED' if not problems else f'\n{len(problems)} FAILED: {problems}')
        sys.exit(1 if problems else 0)


asyncio.run(main())
