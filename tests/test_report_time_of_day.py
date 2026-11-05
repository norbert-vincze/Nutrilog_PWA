"""Report, Time of day (version 33). Run with the web server on port 8765 (see CLAUDE.md).

Norbert asked for the Report on 2026-11-05 and said to go on in the order of the concept document; Time of day is the first item of Phase 3. The section "Time of day" is the last one of the Report
(after Data quality) and has two cards:
- "When you eat": the average first entry, the average last entry and the average window between them (over the logged days), the earliest first entry and the latest last entry. One logged day: first, last, window.
- "Energy by hour": 24 bars, one per hour (00:00-23:59), each the average energy of the logged days in that hour. An hour with no entries on a logged day counts as 0 kcal for that day ("no entries" is a fact);
  an item without energy data is never 0 (striped bar and a ≥, or a dotted stub when the hour has only such items). So the 24 bars add up to the average energy of the Overview.
The time of an entry is `timeOf`: the time set in the Amount sheet or, when it was never changed, the moment the entry was logged. An entry without any usable time is left out and the card says so.
The clock is fixed to Thursday 5 Nov 2026, 12:00 (Budapest).

Hand-calculated sample (three own foods, 100 kcal / 200 kcal / 50 kcal per 100 g, one with no energy), logged days Mon 2, Wed 4 and Thu 5 Nov, Tue 3 Nov is not logged:
  Mon 2:  07:30 Alpha 200 g = 200 kcal, 12:45 Beta 100 g = 200 kcal, 19:10 Gamma 100 g = 50 kcal              first 450 min, last 1150 min
  Wed 4:  08:15 Alpha 100 g = 100 kcal, 12:05 Beta 50 g = 100 kcal                                              first 495 min, last 725 min
  Thu 5:  09:00 Beta 40 g = 80 kcal, 12:30 No energy 100 g (no energy data), 21:45 Gamma 200 g = 100 kcal     first 540 min, last 1305 min
  average first = (450 + 495 + 540) / 3 = 495 = 08:15, average last = (1150 + 725 + 1305) / 3 = 1060 = 17:40, window = 565 min = 9 h 25 min; earliest first 07:30 (Mon), latest last 21:45 (Thu)
  hours (kcal / 3 logged days): 07 = 200 -> 66.67, 08 = 100 -> 33.33, 09 = 80 -> 26.67, 12 = 200 + 100 (+ an item without data) = 300 -> 100 and a lower value (≥), 19 = 50 -> 16.67, 21 = 100 -> 33.33; sum = 830 / 3 = 276.67 = the Overview.

Covers: the section and its place, remembered open state, the numbers above, one logged day, an entry without a time (uses the time it was logged), an entry with no usable time (left out, said), the bars with their states
(solid, striped, dashed, dotted stub, outlined top for a "below x" value, estimate), the reading line, the default selection (the highest hour), Previous / Next, pointer, drag and keys, the table, the legends (only the visible signs),
the sentences, a period that has no entries, the shared copy (same numbers, nothing written), 44 / 16 px, 390 and 320 px, contrast of text and bars in light and dark, 6,000 entries, nothing new stored, the version."""
import asyncio, json, os, pathlib, re, sys, time
from datetime import date, datetime, timedelta, timezone
from playwright.async_api import async_playwright
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_ai_import import CONTRAST_JS

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = 'http://127.0.0.1:8765/index.html'
NOW = '2026-11-05T12:00:00+01:00'           # Thursday
TODAY = date(2026, 11, 5)
SHOTS = os.environ.get('SHOTS')


def day(n):
    return (TODAY + timedelta(days=n)).isoformat()


INIT = """
window.__w = { ls: [], idb: 0 };
try { const si = Storage.prototype.setItem; Storage.prototype.setItem = function (k, v) { window.__w.ls.push(k); return si.call(this, k, v); };
  const ri = Storage.prototype.removeItem; Storage.prototype.removeItem = function (k) { window.__w.ls.push('-' + k); return ri.call(this, k); };
  const io = IDBFactory.prototype.open; IDBFactory.prototype.open = function () { window.__w.idb++; return io.apply(this, arguments); }; } catch (e) { }
"""

# the whole section as the person sees it: the "When you eat" rows, the chart (bars with their classes and heights), the reading line, the legend, the table
TOD = """() => { const sec = document.querySelector('details[data-sec=time]'); if (!sec) return null;
  const txt = (e) => (e ? e.textContent.replace(/\\s+/g, ' ').trim() : null);
  const rows = [...sec.querySelectorAll('.an-row')].map((r) => [txt(r.querySelector('dt')), txt(r.querySelector('dd'))]);
  const bars = [...sec.querySelectorAll('#rp-hours .rp-bar')].map((b) => ({ k: Number(b.dataset.k), c: b.className.replace('rp-bar ', '').replace(' sel', ''), sel: b.classList.contains('sel'), h: parseFloat(b.style.getPropertyValue('--h')), t: parseFloat(b.style.getPropertyValue('--t')) }));
  const tbl = [...sec.querySelectorAll('#rp-hours table tbody tr')].map((r) => [...r.children].map((c) => txt(c)));
  const heads = [...sec.querySelectorAll('#rp-hours table thead th')].map((c) => txt(c));
  return { open: sec.open, rows, bars, read: txt(sec.querySelector('#rp-hrd')), leg: [...sec.querySelectorAll('#rp-hours ul.rp-leg li')].map((li) => txt(li)), ticks: [...sec.querySelectorAll('#rp-hours .rp-y span')].map((s) => txt(s)),
    xs: [...sec.querySelectorAll('#rp-hours .rp-hx span')].map((s) => txt(s)), tbl, heads, label: sec.querySelector('#rp-hplot') ? sec.querySelector('#rp-hplot').getAttribute('aria-label') : null,
    hints: [...sec.querySelectorAll('.hint, .small.muted')].map((e) => txt(e)), prevDis: !!sec.querySelector('[data-act=rp-hour-step][data-n="-1"]:disabled'), nextDis: !!sec.querySelector('[data-act=rp-hour-step][data-n="1"]:disabled'),
    chart: !!sec.querySelector('#rp-hplot'), tableOpen: !!(sec.querySelector('details[data-sec=timetable]') || {}).open }; }"""

SIZES = """(sel) => [...document.querySelectorAll(sel)].filter((e) => e.getClientRects().length).map((e) => { const r = e.getBoundingClientRect(); return [e.className || e.tagName, Math.round(r.width), Math.round(r.height)]; }).filter((x) => x[1] < 43.5 || x[2] < 43.5)"""

# the lines and the bars against the card behind them (3:1 for graphics)
GFX = """() => { const parse = (c) => { let m = c.match(/rgba?\\(([^)]+)\\)/); if (m) { const p = m[1].split(/[ ,\\/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; }
    m = c.match(/color\\(srgb ([^)]+)\\)/); if (m) { const p = m[1].split(/[ \\/]+/).filter(Boolean).map(Number); return [p[0] * 255, p[1] * 255, p[2] * 255, p.length > 3 ? p[3] : 1]; } return [0, 0, 0, 1]; };
  const lum = ([r, g, b]) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const card = document.querySelector('#rp-hours'), bg = (() => { for (let e = card; e; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor); if (c[3] >= 1) return c; } return parse(getComputedStyle(document.body).backgroundColor); })();
  const tok = (name) => { const s = document.createElement('span'); s.style.color = `var(${name})`; card.appendChild(s); const c = parse(getComputedStyle(s).color); s.remove(); return c; };
  const out = {}; for (const n of ['--accent', '--muted', '--ink']) out[n] = Math.round(ratio(tok(n), bg) * 100) / 100; return out; }"""


def own(fid, name, n, **kw):
    f = {'id': fid, 'src': 'user', 'name': name, 'brand': '', 'barcode': '', 'basis': {'qty': 100, 'unit': 'g'}, 'n': n, 'nova': None, 'portions': [], 'note': '', 'created': 1000, 'updated': 1000}
    f.update(kw)
    return f


ALPHA = own('u:alpha', 'Alpha', {'kcal': 100, 'protein': 10})
BETA = own('u:beta', 'Beta', {'kcal': 200, 'protein': 5})
GAMMA = own('u:gamma', 'Gamma', {'kcal': 50})
NOE = own('u:noe', 'No energy', {'protein': 2})
LIMF = own('u:limf', 'Limit food', {'kcal': '<20'})
EST = own('u:est', 'Estimated food', {'kcal': 100}, est=['kcal'], q='m')
FOODS = [ALPHA, BETA, GAMMA, NOE, LIMF, EST]

# (id, food, grams, day, meal, time)
SAMPLE = [('a1', 'u:alpha', 200, day(-3), 'm1', '07:30'), ('a2', 'u:beta', 100, day(-3), 'm2', '12:45'), ('a3', 'u:gamma', 100, day(-3), 'm3', '19:10'),
          ('b1', 'u:alpha', 100, day(-1), 'm1', '08:15'), ('b2', 'u:beta', 50, day(-1), 'm2', '12:05'),
          ('c1', 'u:beta', 40, day(0), 'm1', '09:00'), ('c2', 'u:noe', 100, day(0), 'm2', '12:30'), ('c3', 'u:gamma', 200, day(0), 'm3', '21:45')]
HOUR_KCAL = {7: 200, 8: 100, 9: 80, 12: 300, 19: 50, 21: 100}      # the sums of the lower values of the sample, before the division by 3 logged days

L_FULL = 'Solid bar: every item has energy data'
L_PART = 'Striped bar: a lower value (≥), some items have no energy data'
L_CAP = 'Outlined top: a range, from values given as “below x”'
L_NONE = 'Dashed base: no entries in this hour (not a 0)'
L_NODATA = 'Dotted stub: logged, but no energy data (not a 0)'


async def main():
    async with async_playwright() as p:
        problems = []

        def check(name, ok, info=''):
            print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(info)[:900].replace('\n', ' | ')) if info != '' else ''))
            if not ok: problems.append(name)

        browser = await p.chromium.launch()
        errs = []

        async def new_ctx(w=390, h=844):
            c = await browser.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2, is_mobile=True, has_touch=True, locale='en-GB', timezone_id='Europe/Budapest', service_workers='block', accept_downloads=True)
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

        async def seed(entries, foods=FOODS, kind='week', anchor=day(0), custom=None, tab='report', pg=page, open_all=True, ref=None):
            """entries: (id, food, grams, day, meal, 'HH:MM' | None, t_ms | None); a missing time leaves the entry without `tm`"""
            await pg.evaluate("""([foods, ents, kind, anchor, custom, tab, openAll, ref]) => { const t = window.__tapnaplo, S = t.S;
              S.log.length = 0; for (const k of Object.keys(S.foods)) delete S.foods[k]; S.meta.ref = ref; S.meta.water = {}; S.meta.nova = {};
              for (const f of foods) S.foods[f.id] = f;
              ents.forEach(([id, f, a, d, m, tm, tms], i) => { const e = { id, f, a, d, m: m || 'm1', t: tms === undefined || tms === null ? 1000 + i : tms }; if (tm) e.tm = tm; if (tms === false) delete e.t; S.log.push(e); });
              t.RP.kind = kind; t.RP.anchor = anchor; t.RP.custom = custom; for (const k of Object.keys(t.RP.open)) t.RP.open[k] = openAll;
              S.tab = tab; S.day = anchor; t.save(); t.render(); }""", [foods, entries, kind, anchor, custom, tab, open_all, ref])
            await pg.wait_for_timeout(40)

        async def tod(pg=page):
            return await pg.evaluate(TOD)

        def row(t, label):
            for r in t['rows']:
                if r[0].startswith(label): return r
            return None

        # day labels as the browser writes them
        lab = await T("""() => { const f = (d) => new Date(d + 'T12:00:00').toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' }); return [f('2026-11-02'), f('2026-11-05')]; }""")
        MON, THU = lab

        # =========================================================== 1 the section and its place
        dflt = await T("() => ({ time: window.__tapnaplo.RP.open.time, timetable: window.__tapnaplo.RP.open.timetable })")
        check('by default the section and its table are closed', dflt == {'time': False, 'timetable': False}, dflt)
        await seed(SAMPLE)
        t = await tod()
        order = await T("() => [...document.querySelectorAll('#view > details.rp-sec')].map((d) => [d.dataset.sec, d.querySelector('summary').textContent.trim()])")
        check('"Time of day" is the last section of the Report, after Data quality', t is not None and [o[0] for o in order] == ['overview', 'trend', 'nutrients', 'meals', 'foods', 'nova', 'quality', 'time'] and order[-1][1] == 'Time of day', order)
        await seed(SAMPLE, open_all=False)
        t = await tod()
        check('...and a saved "closed" state keeps it closed', t['open'] is False)
        await page.evaluate("() => { const s = document.querySelector('details[data-sec=time]'); s.open = true; s.dispatchEvent(new Event('toggle')); }"); await page.wait_for_timeout(60)
        saved = await T("() => JSON.parse(localStorage.getItem('nutrilog.reportOpen') || '{}')")
        check('opening it is remembered on this device (key "time"), as the other sections', saved.get('time') is True, saved)
        await seed(SAMPLE)

        # =========================================================== 2 When you eat (hand-calculated)
        t = await tod()
        check('the period is the week Mon 2 - Thu 5 Nov with three logged days', await T("() => window.__tapnaplo.rpStats(window.__tapnaplo.rpRange().from, window.__tapnaplo.rpRange().to).nd") == 3)
        check('"Average first entry" is 08:15 over 3 logged days: (07:30 + 08:15 + 09:00) / 3', row(t, 'Average first entry') == [f'Average first entry · 3 logged days', '08:15'], t['rows'])
        check('"Average last entry" is 17:40: (19:10 + 12:05 + 21:45) / 3', row(t, 'Average last entry') == ['Average last entry', '17:40'], t['rows'])
        check('"Average window" is 9 h 25 min (17:40 minus 08:15)', row(t, 'Average window') == ['Average window · first to last entry', '9 h 25 min'], t['rows'])
        check(f'"Earliest first entry" is 07:30 on {MON} and "Latest last entry" is 21:45 on {THU}', row(t, 'Earliest first entry') == [f'Earliest first entry · {MON}', '07:30'] and row(t, 'Latest last entry') == [f'Latest last entry · {THU}', '21:45'], t['rows'])
        check('the card explains where the time comes from and that an entry belongs to the day it was logged on',
              any('The time of an entry is the time you set for it' in h and 'logged the entry' in h and 'belongs to the day it was logged on' in h for h in t['hints']), t['hints'])

        # one logged day: first, last, window
        await seed(SAMPLE, kind='day', anchor=day(-3))
        t = await tod()
        check('one logged day (Mon 2 Nov): First entry 07:30, Last entry 19:10, Window 11 h 40 min; no averages and no earliest / latest',
              [r[1] for r in t['rows']] == ['07:30', '19:10', '11 h 40 min'] and [r[0].split(' · ')[0] for r in t['rows']] == ['First entry', 'Last entry', 'Window'], t['rows'])
        # a day with a single entry: the window is 0 min
        await seed([('s1', 'u:alpha', 100, day(0), 'm1', '10:00')], kind='day')
        t = await tod()
        check('one entry on a day: the window is 0 min (first and last are the same time)', [r[1] for r in t['rows']] == ['10:00', '10:00', '0 min'], t['rows'])
        await seed([('s1', 'u:alpha', 100, day(0), 'm1', '10:00'), ('s2', 'u:alpha', 100, day(0), 'm1', '10:45')], kind='day')
        t = await tod()
        check('45 minutes are written as "45 min" (under an hour) and an exact hour as "1 h"', t['rows'][2][1] == '45 min', t['rows'])
        await seed([('s1', 'u:alpha', 100, day(0), 'm1', '10:00'), ('s2', 'u:alpha', 100, day(0), 'm1', '11:00')], kind='day')
        t = await tod()
        check('...and 60 minutes as "1 h"', t['rows'][2][1] == '1 h', t['rows'])

        # =========================================================== 3 Energy by hour: bars and numbers
        await seed(SAMPLE)
        t = await tod()
        check('24 bars, one per hour; the axis has 00:00, 06:00, 12:00 and 18:00 under it', len(t['bars']) == 24 and [b['k'] for b in t['bars']] == list(range(24)) and t['xs'] == ['00:00', '06:00', '12:00', '18:00'], [len(t['bars']), t['xs']])
        states = {b['k']: b['c'] for b in t['bars']}
        exp = {h: ('part' if h == 12 else 'full') for h in HOUR_KCAL}
        check('the hours with entries are solid, except 12:00-12:59 (an item without energy data: striped); all the other hours are a dashed base', all(states[h] == exp.get(h, 'none') for h in range(24)), states)
        # the height of each bar follows the value: the highest hour (12, 100 kcal) is the tallest; ticks 0 / 50 / 100 or the nice maximum of 105 -> 120? read the axis from the page
        ymax = float(t['ticks'][0].replace(',', ''))
        check('the axis starts at 0 and its top is a round number above the highest bar (100 kcal x 1.05 -> 200)', t['ticks'][2] == '0' and ymax >= 105, t['ticks'])
        heights = {b['k']: b['h'] for b in t['bars']}
        want = {h: v / 3 / ymax * 100 for h, v in HOUR_KCAL.items()}
        check('every bar is as high as its value over the top of the axis (value = the lower sum over the 3 logged days)', all(abs(heights[h] - want[h]) < 0.02 for h in HOUR_KCAL) and all(heights[h] == 0 for h in range(24) if h not in HOUR_KCAL), {h: (heights[h], round(want[h], 2)) for h in HOUR_KCAL})
        hs = await T("() => ({ hours: window.__tapnaplo.rpTimeStats(window.__tapnaplo.rpStats(window.__tapnaplo.rpRange().from, window.__tapnaplo.rpRange().to)).bars.map((b) => [b.k, b.state, b.lo, b.hi, b.items, b.dayN, b.partial]), kcal: window.__tapnaplo.rpStats(window.__tapnaplo.rpRange().from, window.__tapnaplo.rpRange().to).T.lo[0] })")
        got = {b[0]: b[2] for b in hs['hours'] if b[1] == 'ok'}
        check('the values (hand-calculated): 07 = 66.67, 08 = 33.33, 09 = 26.67, 12 = 100, 19 = 16.67, 21 = 33.33 kcal a logged day', all(abs(got[h] - v / 3) < 1e-9 for h, v in HOUR_KCAL.items()) and len(got) == len(HOUR_KCAL), got)
        check('the 24 hours add up to the average energy of the logged days in the Overview (830 / 3 = 276.67 kcal)', abs(sum(b[2] for b in hs['hours']) - hs['kcal']) < 1e-9 and abs(hs['kcal'] - 830 / 3) < 1e-9, [sum(b[2] for b in hs['hours']), hs['kcal']])
        hour12 = [b for b in hs['hours'] if b[0] == 12][0]
        check('12:00-12:59 has 3 items on 3 days and is a lower value (the item with no energy data is not counted as 0); the empty hours have no items', hour12[4] == 3 and hour12[5] == 3 and hour12[6] is True and all(b[4] == 0 for b in hs['hours'] if b[0] not in HOUR_KCAL), hour12)
        # the reading line: the highest hour at the start
        check('the reading line starts on the highest hour and says it in words: "12:00–12:59 · ≥ 100 kcal · 3 of 3 days · 3 items"', t['read'] == '12:00–12:59 · ≥ 100 kcal · 3 of 3 days · 3 items' and [b['k'] for b in t['bars'] if b['sel']] == [12], t['read'])
        check('the chart has a spoken description with the number of bars with a value, the highest hour and how to use the keys', 'Bar chart of the energy in each hour of the day, 24 bars' in t['label'] and '6 of them have a value' in t['label'] and 'Highest: ≥ 100 kcal at 12:00–12:59' in t['label'] and 'left and right arrow keys' in t['label'], t['label'])
        check('the explanation says an hour with no entries on a logged day counts as 0 kcal, and that items without energy data are not 0', any('counts as 0 kcal for that hour' in h and 'not counted as 0' in h and 'logged days' in h for h in t['hints']), t['hints'])

        # =========================================================== 4 selecting an hour: buttons, keys, pointer, drag
        tr0 = await T("() => { const t = window.__tapnaplo.RP_TREND; return t ? t.sel : null; }")
        await page.locator('#rp-hplot').scroll_into_view_if_needed()
        await page.click('[data-act=rp-hour-step][data-n="1"]'); t = await tod()
        check('Next hour moves to 13:00-13:59 and reads "no entries" (a dashed hour is a fact, not a 0)', t['read'] == '13:00–13:59 · no entries' and [b['k'] for b in t['bars'] if b['sel']] == [13], t['read'])
        for _ in range(13): await page.click('[data-act=rp-hour-step][data-n="-1"]')
        t = await tod()
        check('Previous hour x13 reaches 00:00 and the button is then disabled (Previous), Next is enabled', t['read'] == '00:00–00:59 · no entries' and t['prevDis'] is True and t['nextDis'] is False, [t['read'], t['prevDis'], t['nextDis']])
        await page.focus('#rp-hplot')
        await page.keyboard.press('End'); t = await tod()
        check('the End key goes to 23:00 and then Next is disabled', t['read'] == '23:00–23:59 · no entries' and t['nextDis'] is True and t['prevDis'] is False, [t['read'], t['nextDis']])
        await page.keyboard.press('Home'); await page.keyboard.press('ArrowRight'); await page.keyboard.press('ArrowRight'); t = await tod()
        check('Home and the arrow keys work on the focused chart (Home, then right x2 = 02:00)', t['read'].startswith('02:00–02:59'), t['read'])
        await page.keyboard.press('ArrowLeft'); await page.keyboard.press('ArrowLeft'); await page.keyboard.press('ArrowLeft'); t = await tod()
        check('...and the left arrow stops at the first hour', t['read'].startswith('00:00–00:59'), t['read'])
        bb = await page.locator('#rp-hplot').bounding_box()
        await page.mouse.click(bb['x'] + (7 + 0.5) / 24 * bb['width'], bb['y'] + bb['height'] / 2); t = await tod()
        check('a tap on the 07:00 bar selects it: "07:00–07:59 · 66.7 kcal · 1 of 3 days · 1 item" (Alpha 200 g on Mon 2 Nov, over 3 logged days)', t['read'] == '07:00–07:59 · 66.7 kcal · 1 of 3 days · 1 item', t['read'])
        await page.mouse.move(bb['x'] + 8.5 / 24 * bb['width'], bb['y'] + 90); await page.mouse.down()
        await page.mouse.move(bb['x'] + 10.5 / 24 * bb['width'], bb['y'] + 90, steps=4); await page.mouse.move(bb['x'] + 12.5 / 24 * bb['width'], bb['y'] + 90, steps=4)
        t = await tod()
        check('dragging a finger or the mouse along the chart follows the bars and does not draw the chart again (12:00 is selected while the button is down)', t['read'].startswith('12:00–12:59') and [b['k'] for b in t['bars'] if b['sel']] == [12], t['read'])
        await page.mouse.up()
        await page.mouse.move(bb['x'] + 20.5 / 24 * bb['width'], bb['y'] + 90); t = await tod()
        check('...moving the mouse without a pressed button changes nothing', t['read'].startswith('12:00–12:59'), t['read'])
        # the Trend and the hour chart do not share their selection: the Trend keeps its own bar
        tr1 = await T("() => { const t = window.__tapnaplo.RP_TREND; return t ? t.sel : null; }")
        check('the hour chart does not touch the Trend selection (two charts, two states)', tr0 is not None and tr0 == tr1, [tr0, tr1])

        # =========================================================== 5 the table
        t = await tod()
        check('"Show as table" lists 24 hours with Energy, Days and Items; columns Hour / Energy / Days / Items', t['heads'] == ['Hour', 'Energy', 'Days', 'Items'] and len(t['tbl']) == 24, t['heads'])
        check('...00:00–00:59 is "no entries"; 12:00–12:59 is "≥ 100 kcal", 3 days, 3 items; 07:00–07:59 is "66.7 kcal", 1 day, 1 item',
              t['tbl'][0] == ['00:00–00:59', 'no entries', '0', '0'] and t['tbl'][12] == ['12:00–12:59', '≥ 100 kcal', '3', '3'] and t['tbl'][7] == ['07:00–07:59', '66.7 kcal', '1', '1'], [t['tbl'][0], t['tbl'][7], t['tbl'][12]])
        await seed(SAMPLE, open_all=False)
        await page.evaluate("() => localStorage.removeItem('nutrilog.reportOpen')")
        await page.click('details[data-sec=time] > summary'); await page.click('details[data-sec=timetable] > summary'); await page.wait_for_timeout(60)
        saved = await T("() => JSON.parse(localStorage.getItem('nutrilog.reportOpen') || '{}')")
        check('opening "Show as table" with a tap is remembered too (key "timetable"), together with the section', saved.get('timetable') is True and saved.get('time') is True and saved.get('quality') is False, saved)
        check('...and the table is open on the screen', (await tod())['tableOpen'] is True)

        # =========================================================== 6 the legend: only the signs that are visible
        await seed(SAMPLE)
        t = await tod()
        check('the legend of the sample: solid, striped and dashed - no dotted stub and no outlined top, because no hour has only items without energy data and no value is a range', t['leg'] == [L_FULL, L_PART, L_NONE], t['leg'])
        # an hour with only an item without energy data: the dotted stub; a "below x" value: the outlined top; an estimate: ~
        await seed([('x1', 'u:noe', 100, day(0), 'm1', '10:05'), ('x2', 'u:limf', 100, day(0), 'm2', '14:20'), ('x3', 'u:est', 100, day(0), 'm3', '18:00')], kind='day')
        t = await tod()
        bars = {b['k']: b['c'] for b in t['bars']}
        check('a "<20 kcal" food, an item with no energy data and an estimate: one dotted stub (10:00), one bar with an outlined top (14:00), a solid estimate bar (18:00)', bars[10] == 'nodata' and bars[14] == 'full cap' and bars[18] == 'full' and bars[9] == 'none', bars)
        check('the legend now has all five signs, in the order solid, outlined top, dashed, dotted', t['leg'] == [L_FULL, L_CAP, L_NONE, L_NODATA], t['leg'])
        await page.focus('#rp-hplot')
        await page.keyboard.press('Home')
        for _ in range(10): await page.keyboard.press('ArrowRight')
        t = await tod()
        check('the reading line of the item without energy data says "no energy data" (not 0): "10:00–10:59 · no energy data · 1 item"', t['read'] == '10:00–10:59 · no energy data · 1 item', t['read'])
        for _ in range(4): await page.keyboard.press('ArrowRight')
        t = await tod()
        check('the reading line of the "<20 kcal" hour is a range: "14:00–14:59 · 0–20 kcal · 1 item" (lower value 0, upper value 20)', t['read'] == '14:00–14:59 · 0–20 kcal · 1 item', t['read'])
        for _ in range(4): await page.keyboard.press('ArrowRight')
        t = await tod()
        check('the estimate has a ~ before the value: "18:00–18:59 · ~100 kcal · 1 item"', t['read'] == '18:00–18:59 · ~100 kcal · 1 item', t['read'])
        check('a day (not a period) has no "Days" column and no "N of M days" in the reading line', t['heads'] == ['Hour', 'Energy', 'Items'] and 'of 1 day' not in t['read'], t['heads'])
        check('the table says "no energy data" for the dotted hour and "0–20 kcal" for the range', [r for r in t['tbl'] if r[0].startswith('10:00')][0][1] == 'no energy data' and [r for r in t['tbl'] if r[0].startswith('14:00')][0][1] == '0–20 kcal', [t['tbl'][10], t['tbl'][14]])
        check('the head line says "kcal in that day" for one day', 'kcal in that day' in await page.inner_text('#rp-hours'))

        # =========================================================== 7 entries without a usable time
        t_wed = int(datetime(2026, 11, 4, 14, 20, tzinfo=timezone(timedelta(hours=1))).timestamp() * 1000)
        await seed([('n1', 'u:alpha', 100, day(-1), 'm1', None, t_wed)], kind='day', anchor=day(-1))
        t = await tod()
        check('an entry without a time of its own (made before version 6) uses the time it was logged: 14:20 -> first and last 14:20, the bar at 14:00', [r[1] for r in t['rows']] == ['14:20', '14:20', '0 min'] and [b['k'] for b in t['bars'] if b['c'] != 'none'] == [14], [t['rows'], [b['k'] for b in t['bars'] if b['c'] != 'none']])
        await seed([('n1', 'u:alpha', 100, day(-1), 'm1', '09:00'), ('n2', 'u:beta', 100, day(-1), 'm2', None, False)], kind='day', anchor=day(-1))
        t = await tod()
        check('an entry with no time at all is left out of this section, and the card says so: "1 entry has no time and is not in this section."', any(h == '1 entry has no time and is not in this section.' for h in t['hints']) and [r[1] for r in t['rows']][:2] == ['09:00', '09:00'], t['hints'])
        await seed([('n1', 'u:alpha', 100, day(-1), 'm1', '09:00'), ('n2', 'u:beta', 100, day(-1), 'm2', None, False), ('n3', 'u:beta', 100, day(-1), 'm2', None, False)], kind='day', anchor=day(-1))
        t = await tod()
        check('...2 entries: "2 entries have no time and are not in this section."', any(h == '2 entries have no time and are not in this section.' for h in t['hints']), t['hints'])
        await seed([('n2', 'u:beta', 100, day(-1), 'm2', None, False)], kind='day', anchor=day(-1))
        t = await tod()
        check('only entries with no time: "No entry in this period has a time." on both cards, no chart', t['chart'] is False and sum(1 for h in t['hints'] if h == 'No entry in this period has a time.') >= 1 and t['rows'] == [], t['hints'])
        # a time like 25:99 is not a time; the entry falls back to the time it was logged
        await seed([('n4', 'u:alpha', 100, day(-1), 'm1', '25:99', t_wed)], kind='day', anchor=day(-1))
        t = await tod()
        check('a damaged time ("25:99") is not used; the entry falls back to the time it was logged (14:20)', [r[1] for r in t['rows']][:2] == ['14:20', '14:20'], t['rows'])

        # =========================================================== 8 an entry after midnight stays on the day it was logged
        await seed([('m1', 'u:alpha', 100, day(-1), 'm1', '23:50'), ('m2', 'u:alpha', 100, day(-1), 'm1', '00:20')], kind='day', anchor=day(-1))
        t = await tod()
        check('00:20 on Wed 4 Nov is the first entry of Wed, 23:50 the last: the window is 23 h 30 min (an entry belongs to the day it was logged on, not to the night before)', [r[1] for r in t['rows']] == ['00:20', '23:50', '23 h 30 min'], t['rows'])

        # =========================================================== 9 only no-data items / empty period / hidden entries
        await seed([('z1', 'u:noe', 100, day(0), 'm1', '10:00')], kind='day')
        t = await tod()
        check('every item without energy data: the card says "No item in this period has energy data, so there is nothing to draw. This is not zero." and draws no chart; the times are still shown', t['chart'] is False and any('No item in this period has energy data, so there is nothing to draw. This is not zero.' in h for h in await T("() => [...document.querySelectorAll('details[data-sec=time] .small.muted')].map((e) => e.textContent)")) and [r[1] for r in t['rows']][:2] == ['10:00', '10:00'], [t['rows'], t['hints']])
        await seed(SAMPLE, kind='day', anchor=day(-2))        # Tue 3 Nov: no entries
        sec = await T("() => { const s = document.querySelector('details[data-sec=time]'); return s ? s.textContent.replace(/\\s+/g, ' ').trim() : null; }")
        check('a period with no entries: the Report shows its empty card and no Time of day numbers (nothing is 0)', sec is None or ('Average' not in sec and 'First entry' not in sec), sec)
        await seed(SAMPLE + [('h1', 'u:missing', 100, day(0), 'm4', '11:11')])
        t = await tod()
        check('an entry whose food cannot be loaded is not counted (the Report warns about it elsewhere): the numbers of the sample do not change', row(t, 'Average first entry')[1] == '08:15' and row(t, 'Latest last entry')[1] == '21:45', t['rows'])

        # =========================================================== 10 the other periods: month, Custom
        await seed(SAMPLE, kind='month')
        t = await tod()
        check('Month (Nov 2026 so far) gives the same numbers as the week (the same three logged days)', row(t, 'Average first entry')[1] == '08:15' and row(t, 'Average last entry')[1] == '17:40' and t['bars'][12]['c'] == 'part', [t['rows'][:2]])
        await seed(SAMPLE, kind='custom', custom={'from': day(-3), 'to': day(-3)})
        t = await tod()
        check('a Custom range of one day behaves as a Day (First entry, Last entry, Window)', [r[0].split(' · ')[0] for r in t['rows']] == ['First entry', 'Last entry', 'Window'], t['rows'])

        # =========================================================== 11 nothing new is stored
        await seed(SAMPLE)
        keys = await T("() => ({ ls: Object.keys(localStorage).sort(), meta: Object.keys(window.__tapnaplo.S.meta).sort() })")
        check('nothing new is stored: the localStorage keys are only the known ones, and S.meta has no new key', all(k.startswith('nutrilog.') for k in keys['ls']) and 'time' not in ' '.join(keys['meta']), keys)
        bk = await T("() => { const j = JSON.parse(JSON.stringify({ meta: window.__tapnaplo.S.meta, log: window.__tapnaplo.S.log })); return Object.keys(j.meta).sort(); }")
        check('the backup keys (S.meta) are unchanged by this section', 'hours' not in bk and 'window' not in bk and 'tod' not in bk, bk)

        # =========================================================== 12 the shared copy: same numbers, nothing written
        VF, VT = day(-5), day(0)
        await seed(SAMPLE, kind='custom', custom={'from': VF, 'to': VT})
        own_t = await tod()
        link = await T("([a, b]) => window.__tapnaplo.shareLink(a, b, false).then((r) => r.url)", [VF, VT])
        vctx = await new_ctx(390, 844)
        vp = await vctx.new_page(); watch(vp, 'V')
        await vp.goto(link); await vp.wait_for_selector('.hero')
        await vp.click('[data-tab=report]'); await vp.wait_for_selector('.rp-seg'); await vp.wait_for_selector('details[data-sec=time]', state='attached')
        await vp.evaluate("() => { document.querySelector('details[data-sec=time]').open = true; document.querySelector('details[data-sec=timetable]').open = true; }"); await vp.wait_for_timeout(60)
        vt = await tod(vp)
        keys_cmp = ('rows', 'bars', 'ticks', 'xs', 'tbl', 'heads', 'leg')
        check('the shared copy shows the same Time of day as the sender: the rows, the 24 bars, the axis, the legend and the table', vt is not None and all(vt[k] == own_t[k] for k in keys_cmp), [vt and vt['rows'], own_t['rows']])
        check('...and the same reading line for the highest hour', vt['read'] == own_t['read'] == '12:00–12:59 · ≥ 100 kcal · 3 of 3 days · 3 items', [vt['read'], own_t['read']])
        await vp.focus('#rp-hplot'); await vp.keyboard.press('Home'); await vp.keyboard.press('ArrowRight')
        vt2 = await tod(vp)
        check('...the viewer can read the bars (keys) and the buttons work in the shared copy', vt2['read'].startswith('01:00–01:59'), vt2['read'])
        await vp.click('[data-act=rp-hour-step][data-n="1"]'); vt3 = await tod(vp)
        check('...Next hour in the shared copy: 02:00', vt3['read'].startswith('02:00–02:59'), vt3['read'])
        w = await vp.evaluate("() => window.__w")
        check('the viewer wrote nothing: no localStorage write, no IndexedDB opened (the v23 guarantee holds)', w['ls'] == [] and w['idb'] == 0, w)
        await vctx.close()

        # =========================================================== 13 layout, 44 px, 16 px, contrast
        for w in (390, 320):
            cx, pg = await fresh(w, 844, f'L{w}')
            await seed(SAMPLE + [('x1', 'u:limf', 100, day(0), 'm5', '14:20'), ('x2', 'u:noe', 100, day(-3), 'm5', '03:10')], pg=pg, open_all=True)
            await pg.evaluate("() => document.querySelectorAll('details[data-sec=time] details').forEach((d) => { d.open = true; })"); await pg.wait_for_timeout(60)
            fits = await pg.evaluate("""() => { const sec = document.querySelector('details[data-sec=time]'); const tab = sec.querySelector('.rp-tablewrap');
              return { page: document.documentElement.scrollWidth <= window.innerWidth, tab: tab ? tab.scrollWidth <= tab.clientWidth + 1 : null,
              cut: [...sec.querySelectorAll('.an-row dt, .an-row dd, .rp-read > *, .rp-leg li, .rp-hx span, .hint')].filter((e) => e.scrollWidth > e.clientWidth + 1).map((e) => e.className + ':' + e.textContent.slice(0, 20)),
              hx: [...sec.querySelectorAll('.rp-hx span')].map((e) => { const r = e.getBoundingClientRect(), p = sec.querySelector('#rp-hplot').getBoundingClientRect(); return r.right <= window.innerWidth && r.left >= p.left - 1; }) }; }""")
            check(f'{w} px: the section with the table and legend open does not scroll sideways, no label is cut off, and the four hour labels sit inside the page', fits['page'] and fits['tab'] and fits['cut'] == [] and all(fits['hx']), fits)
            small = await pg.evaluate(SIZES, 'details[data-sec=time] > summary, details[data-sec=time] [data-act], details[data-sec=time] summary')
            check(f'{w} px: the section header, Previous hour, Next hour and "Show as table" are at least 44 px', small == [], small)
            plot = await pg.evaluate("() => { const r = document.querySelector('#rp-hplot').getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; }")
            check(f'{w} px: the chart is 180 px high and each of the 24 bars is at least 8 px wide ({plot[0] / 24:.1f} px)', plot[1] == 180 and plot[0] / 24 >= 8, plot)
            for theme in ('light', 'dark'):
                await pg.evaluate("(t) => document.documentElement.setAttribute('data-theme', t)", theme)
                bad = await pg.evaluate(CONTRAST_JS, 'details[data-sec=time]')
                g = await pg.evaluate(GFX)
                check(f'{w} px, {theme}: the text of Time of day has at least 4.5:1; the bars, dashes and dots have at least 3:1 against the card', bad == [] and g['--accent'] >= 3 and g['--muted'] >= 3, (bad[:3], g))
            small16 = await pg.evaluate("() => [...document.querySelectorAll('details[data-sec=time] input, details[data-sec=time] select, details[data-sec=time] textarea')].length")
            check(f'{w} px: the section has no field at all (so nothing can zoom the page on iOS)', small16 == 0, small16)
            if SHOTS:
                await pg.evaluate("() => document.querySelector('details[data-sec=time]').scrollIntoView()")
                await pg.screenshot(path=os.path.join(SHOTS, f'time_{w}.png'))
            await cx.close()

        # =========================================================== 14 speed with 6,000 entries
        cx, pg = await fresh(390, 844, 'S')
        foods12 = [own(f'u:k{i:02d}', f'Bulk food {i:02d}', {'kcal': (i + 1) * 30, 'protein': i}) for i in range(12)]
        bulk = []
        for k in range(365):
            d_ = (TODAY - timedelta(days=k)).isoformat()
            for j in range(16):
                bulk.append((f'k{k}_{j}', f'u:k{(k + j) % 12:02d}', 50 + j * 10, d_, 'm1', f'{6 + j}:{(k * 7 + j) % 60:02d}'.rjust(5, '0')))
        await seed(bulk, foods=foods12, kind='year', pg=pg, open_all=True)
        t0 = time.perf_counter(); await pg.evaluate("() => window.__tapnaplo.render()"); dt = time.perf_counter() - t0
        t = await tod(pg)
        check(f'6,000 entries over a year: the Report with Time of day renders in {dt:.2f} s (less than 3 s); 24 bars, 16 of them with a value (06:00-21:59)', dt < 3 and len(t['bars']) == 24 and sum(1 for b in t['bars'] if b['c'].startswith('full')) == 16, [round(dt, 2), [b['c'] for b in t['bars']]])
        await cx.close()

        # =========================================================== 15 the version
        ver = await T("() => document.querySelector('#appver, .ver, [data-version]') ? document.querySelector('#appver, .ver, [data-version]').textContent : ''")
        app = (ROOT / 'app.js').read_text(encoding='utf-8'); sw = (ROOT / 'sw.js').read_text(encoding='utf-8')
        v = int(re.search(r"const VERSION = '(\d+)", app).group(1)); c = int(re.search(r"const CACHE = 'nutrilog-v(\d+)'", sw).group(1))
        check('version 33 or later, and the service worker cache has the same number', v >= 33 and v == c, [v, c])

        check('no page errors', errs == [], errs[:5])
        await browser.close()
        print('\nALL PASSED' if not problems else f'\nFAILED: {problems}')
        sys.exit(1 if problems else 0)


asyncio.run(main())
