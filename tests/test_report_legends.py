"""Legends of the bars (version 32). Run with the web server on port 8765 (see CLAUDE.md).

Norbert asked (2026-11-05, after he did not know what the dashed line and the full bar mean in "Meals and weekdays"): "a jelmagyarázat mindenhol jelenjen meg".
Every place that draws such bars now has a short legend in the style of the Trend legend, and it lists only the signs that are on that card:
- Meals and weekdays: one legend under the meals, one under the weekdays, one under "Weekdays and weekend" (solid / striped / dashed / dotted, and what the length means).
- Foods: what the bar is, and the empty bar of a food that has no share ("below x" or 0).
- Food processing (NOVA), Over time: the colours that are in the bars, the dashed line (no entries) and the dotted line (no energy to split).
- Reference intake (Nutrients tab and Report > Nutrients, also in a shared copy): solid = PRI, dashed = AI, dotted = SAI, only the kinds that have a bar on the screen.
The swatches are the real bars in small (same CSS classes), so a sign cannot look different in the legend than on the bar. The clock is fixed to Thursday 5 Nov 2026, 12:00 (Budapest).

Covers: the exact legend of every card for a hand-made week, only the signs that are visible (no striped sign without a striped bar, ...), the Day period (one meals legend, no weekday or NOVA legend),
the Foods edge cases (empty bar, only empty bars, no list, water), the NOVA dotted line, the reference legend (all three kinds, one kind, no bar, no profile, empty day, Report, shared copy), the swatches
look like the bars (computed styles), aria-hidden swatches, no sideways scroll and no cut-off text at 390 and 320 px in light and dark, contrast of the text and of the signs, nothing new stored, the version."""
import asyncio, json, os, pathlib, re, sys
from datetime import date, timedelta
from playwright.async_api import async_playwright
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_ai_import import CONTRAST_JS

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = 'http://127.0.0.1:8765/index.html'
NOW = '2026-11-05T12:00:00+01:00'           # Thursday
TODAY = date(2026, 11, 5)


def day(n):
    return (TODAY + timedelta(days=n)).isoformat()


INIT = """
window.__w = { ls: [], idb: 0 };
try { const si = Storage.prototype.setItem; Storage.prototype.setItem = function (k, v) { window.__w.ls.push(k); return si.call(this, k, v); };
  const ri = Storage.prototype.removeItem; Storage.prototype.removeItem = function (k) { window.__w.ls.push('-' + k); return ri.call(this, k); };
  const io = IDBFactory.prototype.open; IDBFactory.prototype.open = function () { window.__w.idb++; return io.apply(this, arguments); }; } catch (e) { }
"""

# every legend (ul.rp-leg) inside a container: for each line the kind of the swatch, the text and whether the swatch is hidden from a screen reader
LEG_JS = """(sel) => { const kind = (sw) => sw.classList.contains('rp-swn') ? 'nova' : sw.classList.contains('rtrack') ? 'track-' + ['pri', 'ai', 'sai'].find((c) => sw.classList.contains(c))
    : 'bar-' + (sw.classList.contains('full') && !sw.firstElementChild ? 'empty' : ['full', 'part', 'none', 'nodata'].find((c) => sw.classList.contains(c)));
  return [...document.querySelectorAll(sel + ' ul.rp-leg')].map((ul) => [...ul.children].map((li) => [kind(li.firstElementChild), li.textContent.replace(/\\s+/g, ' ').trim(), li.firstElementChild.getAttribute('aria-hidden')])); }"""

# the look of a swatch against the look of the real thing
LOOK_JS = """() => { const cs = (e, props) => { const s = getComputedStyle(e); return props.map((p) => s[p]); };
  const BAR = ['height', 'borderBottomStyle', 'borderBottomWidth', 'backgroundColor', 'borderRadius'], FILL = ['backgroundImage', 'backgroundColor', 'boxShadow', 'borderRadius'];
  const TRK = ['height', 'borderTopStyle', 'borderTopWidth', 'borderTopColor', 'backgroundColor', 'borderRadius'], TF = ['backgroundImage', 'backgroundColor', 'borderRadius'];
  const out = {};
  for (const k of ['full', 'part', 'none', 'nodata']) {
    const real = document.querySelector(`.rp-drow .rp-dbar.${k}`), sw = document.querySelector(`ul.rp-leg .rp-dbar.rp-swt.${k}`);
    const edge = (e) => (parseFloat(getComputedStyle(e).borderBottomWidth) > 0 ? getComputedStyle(e).borderBottomColor : '');   // the colour of an absent border is the text colour, which differs
    out[k] = real && sw ? { bar: JSON.stringify(cs(real, BAR).concat(edge(real))) === JSON.stringify(cs(sw, BAR).concat(edge(sw))), fill: !real.querySelector('i') || JSON.stringify(cs(real.querySelector('i'), FILL)) === JSON.stringify(cs(sw.querySelector('i'), FILL)) } : null;
  }
  for (const k of ['pri', 'ai', 'sai']) {
    const real = document.querySelector(`.rline .rtrack.${k}`), sw = document.querySelector(`ul.rp-leg .rtrack.rp-swt.${k}`);
    out[k] = real && sw ? { bar: JSON.stringify(cs(real, TRK)) === JSON.stringify(cs(sw, TRK)), fill: JSON.stringify(cs(real.querySelector('i'), TF)) === JSON.stringify(cs(sw.querySelector('i'), TF)) } : null;
  }
  return out; }"""

# the signs against the card behind them (3:1 for graphics), and the outline of the NOVA squares
GFX = """(sel) => { const parse = (c) => { let m = c.match(/rgba?\\(([^)]+)\\)/); if (m) { const p = m[1].split(/[ ,\\/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; }
    m = c.match(/color\\(srgb ([^)]+)\\)/); if (m) { const p = m[1].split(/[ \\/]+/).filter(Boolean).map(Number); return [p[0] * 255, p[1] * 255, p[2] * 255, p.length > 3 ? p[3] : 1]; } return [0, 0, 0, 1]; };
  const lum = ([r, g, b]) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const card = document.querySelector(sel), bg = (() => { for (let e = card; e; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor); if (c[3] >= 1) return c; } return parse(getComputedStyle(document.body).backgroundColor); })();
  const tok = (name) => { const s = document.createElement('span'); s.style.color = `var(${name})`; card.appendChild(s); const c = parse(getComputedStyle(s).color); s.remove(); return c; };
  const out = {}; for (const n of ['--accent', '--muted']) out[n] = Math.round(ratio(tok(n), bg) * 100) / 100;
  const sq = document.querySelector('ul.rp-leg .rp-swn'); const sh = sq ? getComputedStyle(sq).boxShadow : null; const m = sh && sh !== 'none' ? sh.match(/rgba?\\([^)]+\\)/) : null;
  out.outlineRatio = m ? Math.round(ratio(parse(m[0]), bg) * 100) / 100 : null; return out; }"""

# each line of each legend: the swatch has a size and does not overlap the text, the text is not cut off, no legend is wider than the screen
FIT_JS = """() => { const bad = [];
  for (const ul of document.querySelectorAll('ul.rp-leg-h')) { if (!ul.getClientRects().length) continue; const ur = ul.getBoundingClientRect(); if (ur.right > window.innerWidth + 0.5 || ul.scrollWidth > ul.clientWidth + 1) bad.push('wide:' + ul.textContent.slice(0, 20));
    for (const li of ul.children) { const sw = li.firstElementChild, tx = li.lastElementChild, a = sw.getBoundingClientRect(), b = tx.getBoundingClientRect();
      if (a.width < 8) bad.push('swatch:' + li.textContent.slice(0, 20)); if (a.right > b.left + 0.5 && a.bottom > b.top + 0.5 && a.top < b.bottom - 0.5) bad.push('overlap:' + li.textContent.slice(0, 20));
      if (tx.scrollWidth > tx.clientWidth + 1 || b.right > window.innerWidth + 0.5) bad.push('cut:' + li.textContent.slice(0, 20)); } }
  return { page: document.documentElement.scrollWidth <= window.innerWidth, bad, n: document.querySelectorAll('ul.rp-leg-h').length }; }"""


def own(fid, name, n, **kw):
    f = {'id': fid, 'src': 'user', 'name': name, 'brand': '', 'barcode': '', 'basis': {'qty': 100, 'unit': 'g'}, 'n': n, 'nova': None, 'portions': [], 'note': '', 'created': 1000, 'updated': 1000}
    f.update(kw)
    return f


# the same hand-made week as in test_report_meals_foods_nova.py: Mon 2, Wed 4 and Thu 5 Nov are logged days, Tue 3 Nov is not
ALPHA = own('u:alpha', 'Alpha', {'kcal': 100, 'protein': 10, 'calcium': 100}, nova=1)
BETA = own('u:beta', 'Beta', {'kcal': 200, 'protein': 5, 'calcium': 200}, nova=4)
GAMMA = own('u:gamma', 'Gamma', {'kcal': 50})
NOE = own('u:noe', 'No energy', {'protein': 2})
LIMF = own('u:limf', 'Limit food', {'kcal': '<20', 'calcium': '<201', 'protein': '<2'})
FOODS = [ALPHA, BETA, GAMMA, NOE, LIMF]
WEEK = [('e1', 'u:alpha', 200, day(-3), 'm1'), ('e2', 'u:beta', 100, day(-3), 'm2'), ('e3', 'u:alpha', 100, day(-1), 'm1'),
        ('e4', 'u:gamma', 100, day(-1), 'm3'), ('e5', 'u:beta', 40, day(0), 'm1'), ('e6', 'u:noe', 100, day(0), 'm4')]
# reference intake: calcium has a PRI, magnesium an AI, sodium a SAI
MIX = own('u:mix', 'Mixed', {'kcal': 300, 'protein': 10, 'calcium': 400, 'magnesium': 120, 'sodium': 500})
CAL = own('u:cal', 'Calcium food', {'kcal': 100, 'protein': 5, 'calcium': 300})
PLAIN = own('u:plain', 'Plain food', {'kcal': 100, 'protein': 5})
MALE = {'sex': 'm', 'age': '25', 'zinc': 600}

L_MEAL_FULL = 'Solid bar: every item has energy data. The length is the meal’s share of the known energy'
L_PART = 'Striped bar: a lower value (≥), some items have no energy data'
L_LIST_FULL = 'Solid bar: every item has energy data. The length is compared with the highest average in this list'
L_PAIR_FULL = 'Solid bar: every item has energy data. The length is compared with the higher average of the two'
L_NONE_MEAL = 'Dashed line: no entries (not a 0)'
L_NONE_DAY = 'Dashed line: no logged day (not a 0)'
L_NODATA_MEAL = 'Dotted line: logged, but none has energy data (not a 0)'
L_NODATA_DAY = 'Dotted line: logged, but no energy data (not a 0)'
L_FOOD = 'Bar: the food’s share of the total of all foods with data, worked out from lower values'
L_EMPTY = 'Empty bar: nothing to draw, the value is 0 or only “below x” is known'
L_NOVA_NONE = 'Dashed line: no entries (not a 0%)'
L_NOVA_NODATA = 'Dotted line: logged, but no energy to split (not a 0%)'
L_PRI = 'Solid bar: PRI, population reference intake'
L_AI = 'Dashed bar: AI, adequate intake. EFSA’s value rests on less evidence'
L_SAI = 'Dotted bar: SAI, safe and adequate intake. Not a target'
L_STOP = 'A bar stops at 100%. The percent next to it goes on.'


async def main():
    async with async_playwright() as p:
        problems = []

        def check(name, ok, info=''):
            print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(info)[:700].replace('\n', ' | ')) if info != '' else ''))
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

        async def seed(entries, foods=FOODS, kind='week', anchor=day(0), custom=None, tab='report', ref=None, pg=page, measure='kcal', open_all=True):
            await pg.evaluate("""([foods, ents, kind, anchor, custom, tab, ref, openAll]) => { const t = window.__tapnaplo, S = t.S;
              S.log.length = 0; for (const k of Object.keys(S.foods)) delete S.foods[k]; S.meta.ref = ref; S.meta.water = {}; S.meta.nova = {};
              for (const f of foods) S.foods[f.id] = f;
              ents.forEach(([id, f, a, d, m], i) => S.log.push({ id, f, a, d, m: m || 'm1', t: 1000 + i, tm: '08:' + String(10 + (i % 50)) }));
              t.RP.kind = kind; t.RP.anchor = anchor; t.RP.custom = custom; for (const k of Object.keys(t.RP.open)) t.RP.open[k] = openAll;
              S.tab = tab; S.day = anchor; t.save(); t.render(); }""", [foods, entries, kind, anchor, custom, tab, ref, open_all])
            await pg.wait_for_timeout(40)
            if tab == 'report' and measure is not None and await pg.locator('#rp-foods .rp-measure:visible').count() and await pg.evaluate("() => window.__tapnaplo.curMeasure()") != measure:
                await pick_measure(measure, pg)

        async def pick_measure(m, pg=page):
            await pg.click('#rp-foods .rp-measure'); await pg.wait_for_selector('.rp-m')
            await pg.click(f'.rp-m[data-m="{m}"]'); await pg.wait_for_timeout(60)

        async def legs(sel, pg=page):
            return await pg.evaluate(LEG_JS, sel)

        # =========================================================== 1 Meals and weekdays: the three legends of the hand-made week
        await seed(WEEK)
        L = await legs('details[data-sec=meals]')
        check('Meals and weekdays has three legends: under the meals, under the weekdays, under "Weekdays and weekend"', len(L) == 3, [len(x) for x in L])
        # Meal 1-3 solid, Meal 4 has an item without energy data (dotted), Meal 5 and 6 have no entries (dashed); no striped meal
        check('the meal legend lists exactly the signs that are on the meal bars: solid, dashed, dotted - no striped sign, because no meal is a lower value',
              L[0] == [['bar-full', L_MEAL_FULL, 'true'], ['bar-none', L_NONE_MEAL, 'true'], ['bar-nodata', L_NODATA_MEAL, 'true']], L[0])
        # weekdays: Mon and Wed solid, Thu striped (e6 has no energy data), Tue/Fri/Sat/Sun no logged day
        check('the weekday legend: solid (with what the length means), striped, dashed "no logged day"; no dotted sign, because no weekday has only items without energy data',
              L[1] == [['bar-full', L_LIST_FULL, 'true'], ['bar-part', L_PART, 'true'], ['bar-none', L_NONE_DAY, 'true']], L[1])
        # Mon-Fri is striped (Thursday has an item without energy), Sat-Sun has no logged day
        check('the weekday against weekend legend: striped and dashed only (Monday to Friday is a lower value, Saturday and Sunday have no logged day)',
              L[2] == [['bar-part', L_PART, 'true'], ['bar-none', L_NONE_DAY, 'true']], L[2])
        check('every swatch is hidden from a screen reader (the words say it all)', all(x[2] == 'true' for lg in L for x in lg))
        # the legend sits right under its bars, before the explanation
        order = await T("""() => { const sec = document.querySelector('details[data-sec=meals]'); return [...sec.querySelectorAll('.rp-dist, ul.rp-leg, .rp-expl')].map((e) => e.matches('.rp-dist') ? 'bars' : e.matches('ul') ? 'legend' : 'text'); }""")
        check('...each legend is right under its bars, then the explanation (meals: bars, legend, text; weekdays: bars, legend; weekend: bars, legend, text)', order == ['bars', 'legend', 'text', 'bars', 'legend', 'bars', 'legend', 'text'], order)

        # =========================================================== 2 Foods
        F = await legs('#rp-foods')
        check('Foods (Energy) has one legend that says what the bar is; no "empty bar" sign, because every food has a share', F == [[['bar-full', L_FOOD, 'true']]], F)

        # =========================================================== 3 Food processing (NOVA): the colours in the bars, the dashed line for Tuesday
        N = await legs('details[data-sec=nova]')
        # Mon: NOVA 1 (Alpha) + NOVA 4 (Beta); Tue none; Wed: NOVA 1 + Unclassified (Gamma); Thu: NOVA 4 (Beta); NOVA 2 and 3 are in no bar
        check('NOVA Over time: only the groups that are in a bar (NOVA 1, NOVA 4, Unclassified - not NOVA 2 or 3), then the dashed line for the day without entries; no dotted line',
              N == [[['nova', 'NOVA 1', 'true'], ['nova', 'NOVA 4', 'true'], ['nova', 'Unclassified', 'true'], ['bar-none', L_NOVA_NONE, 'true']]], N)
        cols = await T("""() => { const dots = [...document.querySelectorAll('details[data-sec=nova] .nova-card .nova-row .dot')].map((d) => getComputedStyle(d).backgroundColor);
          return { sw: [...document.querySelectorAll('details[data-sec=nova] ul.rp-leg .rp-swn')].map((s) => getComputedStyle(s).backgroundColor), dots,
                   segs: [...document.querySelectorAll('details[data-sec=nova] .rp-nb:not(.none):not(.nodata) i')].map((s) => getComputedStyle(s).backgroundColor) }; }""")
        check('...the three squares have the colours of NOVA 1, NOVA 4 and Unclassified (the dots of the card above), and these colours are the ones of the segments in the bars',
              cols['sw'] == [cols['dots'][0], cols['dots'][3], cols['dots'][4]] and all(c in cols['segs'] for c in cols['sw']), cols)

        # =========================================================== 4 the Day period: Mon 2 Nov
        await seed(WEEK, kind='day', anchor=day(-3))
        L = await legs('details[data-sec=meals]')
        check('a Day: the meal legend (Meal 1 and 2 solid, the other four have no entries) and no weekday legend (the part says that it needs two logged days)',
              L == [[['bar-full', L_MEAL_FULL, 'true'], ['bar-none', L_NONE_MEAL, 'true']]], L)
        check('a Day: the Foods legend is there, and NOVA has no "Over time" and so no legend', (await legs('#rp-foods')) == [[['bar-full', L_FOOD, 'true']]] and (await legs('details[data-sec=nova]')) == [])

        # =========================================================== 5 only the signs that are visible
        await seed([('p1', 'u:alpha', 100, day(0), 'm1'), ('p2', 'u:noe', 100, day(0), 'm1')], kind='day')
        L = await legs('details[data-sec=meals]')
        check('a meal with one item that has energy and one that has not is striped: the legend has the striped sign and the dashed one, no solid and no dotted sign',
              L == [[['bar-part', L_PART, 'true'], ['bar-none', L_NONE_MEAL, 'true']]], L)
        await seed([('p1', 'u:noe', 100, day(0), 'm1')], kind='day')
        L = await legs('details[data-sec=meals]')
        check('a meal whose only item has no energy data has the dotted line: the legend has the dotted and the dashed sign, nothing else',
              L == [[['bar-none', L_NONE_MEAL, 'true'], ['bar-nodata', L_NODATA_MEAL, 'true']]], L)
        # Foods: the "below x" food has no bar
        await seed([('r1', 'u:alpha', 100, day(-3), 'm1'), ('r2', 'u:limf', 100, day(-3), 'm1'), ('r3', 'u:beta', 50, day(-1), 'm2')])
        F = await legs('#rp-foods')
        check('Foods: a food that is only known as "below x" has an empty bar, so the legend has the empty bar as well',
              F == [[['bar-full', L_FOOD, 'true'], ['bar-empty', L_EMPTY, 'true']]], F)
        await seed([('l1', 'u:limf', 100, day(0), 'm1')], kind='day')
        F = await legs('#rp-foods')
        check('Foods: when every bar is empty there is no solid sign, only the empty bar', F == [[['bar-empty', L_EMPTY, 'true']]], F)
        await seed(WEEK)
        await pick_measure('magnesium')
        check('Foods: a measure that nobody has data for shows the "nothing to list" message and no legend', (await legs('#rp-foods')) == [] and 'nothing to list' in await T("() => document.querySelector('#rp-foods').textContent"))
        await pick_measure('water_intake')
        check('Foods: water has no list of foods and no legend', (await legs('#rp-foods')) == [])
        # NOVA: a day that has items but no energy gets the dotted line
        await seed([('n1', 'u:alpha', 100, day(-3), 'm1'), ('n2', 'u:noe', 100, day(-1), 'm1')])
        N = await legs('details[data-sec=nova]')
        check('NOVA Over time: a day with items but no energy ("no energy to split") adds the dotted line to the legend, together with the dashed line for the days without entries',
              N == [[['nova', 'NOVA 1', 'true'], ['bar-none', L_NOVA_NONE, 'true'], ['bar-nodata', L_NOVA_NODATA, 'true']]], N)

        # =========================================================== 6 reference intake bars: Nutrients tab, Report > Nutrients, empty day, no profile
        await seed([('x1', 'u:mix', 100, day(0), 'm1')], foods=[MIX, CAL, PLAIN], kind='day', tab='nutr', ref=MALE)
        R = await legs('#refcard')
        stop = await T("() => { const p = document.querySelector('#refcard .rp-legend'); return p ? p.textContent.trim() : null; }")
        check('Nutrients tab with a profile: the legend of the bars is in the reference card with the three kinds that have a bar today (calcium = PRI, magnesium = AI, sodium = SAI)',
              R == [[['track-pri', L_PRI, 'true'], ['track-ai', L_AI, 'true'], ['track-sai', L_SAI, 'true']]], R)
        check('...and the sentence that the bar stops at 100% while the percent goes on', stop == L_STOP, stop)
        drawn = await T("() => ['pri', 'ai', 'sai'].filter((k) => document.querySelector(`.nrow .rtrack.${k}`))")
        check('...the kinds in the legend are exactly the kinds of the bars in the rows', drawn == ['pri', 'ai', 'sai'], drawn)
        look = await T(LOOK_JS)
        check('...the three swatches have the look of the real bars (height, border style, colours, fill)', all(look[k] and look[k]['bar'] and look[k]['fill'] for k in ('pri', 'ai', 'sai')), look)
        await seed([('x1', 'u:cal', 100, day(0), 'm1')], foods=[MIX, CAL, PLAIN], kind='day', tab='nutr', ref=MALE)
        R = await legs('#refcard')
        drawn = await T("() => ['pri', 'ai', 'sai'].filter((k) => document.querySelector(`.nrow .rtrack.${k}`))")
        check('when only calcium has data, only the solid (PRI) sign is listed - the same kinds as the bars that are drawn', R == [[['track-pri', L_PRI, 'true']]] and drawn == ['pri'], [R, drawn])
        await seed([('x1', 'u:plain', 100, day(0), 'm1')], foods=[MIX, CAL, PLAIN], kind='day', tab='nutr', ref=MALE)
        none_ = await T("() => ({ ul: document.querySelectorAll('#refcard ul.rp-leg').length, stop: document.querySelectorAll('#refcard .rp-legend').length, bars: document.querySelectorAll('.nrow .rtrack').length })")
        check('with a profile but no nutrient that has a reference value and data, there is no bar and no legend (and not the sentence about 100% either)', none_ == {'ul': 0, 'stop': 0, 'bars': 0}, none_)
        await seed([('x1', 'u:mix', 100, day(0), 'm1')], foods=[MIX, CAL, PLAIN], kind='day', tab='nutr', ref=None)
        none_ = await T("() => ({ ul: document.querySelectorAll('#refcard ul.rp-leg').length, stop: document.querySelectorAll('#refcard .rp-legend').length })")
        check('without a profile (Male / Female buttons) there is no legend', none_ == {'ul': 0, 'stop': 0})
        await seed([], foods=[MIX, CAL, PLAIN], kind='day', tab='nutr', ref=MALE)
        none_ = await T("() => ({ ul: document.querySelectorAll('#refcard ul.rp-leg').length, stop: document.querySelectorAll('#refcard .rp-legend').length })")
        check('an empty day with a profile has the card but no legend (there is no bar)', none_ == {'ul': 0, 'stop': 0})
        await seed([('x1', 'u:mix', 100, day(-1), 'm1'), ('x2', 'u:cal', 100, day(0), 'm1')], foods=[MIX, CAL, PLAIN], kind='week', tab='report', ref=MALE)
        R = await legs('details[data-sec=nutrients]')
        check('Report > Nutrients: the same legend in the reference card (the averages of the logged days have PRI, AI and SAI bars)',
              R == [[['track-pri', L_PRI, 'true'], ['track-ai', L_AI, 'true'], ['track-sai', L_SAI, 'true']]], R)
        # the other legends of the Report are not changed by a profile
        check('...and the Meals legends are the same with a profile', len(await legs('details[data-sec=meals]')) == 3)

        # =========================================================== 7 the shared copy
        VF, VT = day(-3), day(0)
        await seed([('x1', 'u:mix', 100, day(-1), 'm1'), ('x2', 'u:cal', 100, day(0), 'm1'), ('x3', 'u:noe', 100, day(0), 'm2')], foods=[MIX, CAL, NOE, PLAIN], kind='custom', custom={'from': VF, 'to': VT}, tab='report', ref=MALE)
        link = await T("([a, b]) => window.__tapnaplo.shareLink(a, b, true).then((r) => r.url)", [VF, VT])
        s_leg = {k: await legs(sel) for k, sel in (('meals', 'details[data-sec=meals]'), ('foods', '#rp-foods'), ('nova', 'details[data-sec=nova]'), ('ref', 'details[data-sec=nutrients]'))}
        vctx = await new_ctx(390, 844)
        vp = await vctx.new_page(); watch(vp, 'V')
        await vp.goto(link); await vp.wait_for_selector('.hero')
        await vp.click('[data-tab=report]'); await vp.wait_for_selector('.rp-seg')
        await vp.evaluate("() => document.querySelectorAll('#view details.rp-sec').forEach((d) => { d.open = true; })"); await vp.wait_for_timeout(60)
        v_leg = {k: await legs(sel, vp) for k, sel in (('meals', 'details[data-sec=meals]'), ('foods', '#rp-foods'), ('nova', 'details[data-sec=nova]'), ('ref', 'details[data-sec=nutrients]'))}
        check('the shared copy has the same legends as the sender (Meals, Foods, NOVA, reference intake)', v_leg == s_leg and len(v_leg['meals']) == 3 and len(v_leg['ref']) == 1 and len(v_leg['foods']) == 1, [v_leg['ref'], s_leg['ref']])
        await vp.click('[data-tab=nutr]'); await vp.wait_for_selector('#refcard'); await vp.wait_for_timeout(60)
        vref = await legs('#refcard', vp)
        vdrawn = await vp.evaluate("() => ['pri', 'ai', 'sai'].filter((k) => document.querySelector(`.nrow .rtrack.${k}`))")
        # the shared copy opens the last shared day (Thu 5 Nov: Calcium food and No energy): only calcium has a reference value and data, so only the solid (PRI) sign is on the screen
        check('...and the Nutrients tab of the shared copy shows the reference legend too (read only), with the kinds of the bars of the day it shows (Thursday: only calcium, a PRI)',
              len(vref) == 1 and [x[0] for x in vref[0]] == ['track-' + k for k in vdrawn] and vdrawn == ['pri'], [vref, vdrawn])
        w = await vp.evaluate("() => window.__w")
        check('the viewer wrote nothing (no localStorage write, no IndexedDB opened)', w['ls'] == [] and w['idb'] == 0, w)
        await vctx.close()

        # =========================================================== 8 the swatches look like the bars (Report)
        await seed([('r1', 'u:alpha', 100, day(-3), 'm1'), ('r2', 'u:noe', 100, day(-3), 'm1'), ('r3', 'u:beta', 50, day(-1), 'm2'), ('r4', 'u:noe', 100, day(0), 'm5')], kind='week')
        look = await T(LOOK_JS)
        check('the solid, striped, dashed and dotted swatches have the same height, border and fill as the real bars', all(look[k] and look[k]['bar'] and look[k]['fill'] for k in ('full', 'part', 'none', 'nodata')), look)

        # =========================================================== 9 layout and contrast, 390 and 320 px, light and dark
        EXTRA = WEEK + [('x1', 'u:mix', 100, day(-2), 'm1'), ('x2', 'u:noe', 100, day(-2), 'm5')]
        for wd in (390, 320):
            cx, pg = await fresh(wd, 844, f'L{wd}')
            await seed(EXTRA, foods=FOODS + [MIX], kind='week', pg=pg, ref=MALE)
            await pg.evaluate("() => document.querySelectorAll('#view details.rp-sec, #view details.fold').forEach((d) => { d.open = true; })"); await pg.wait_for_timeout(60)
            fit = await pg.evaluate(FIT_JS)
            check(f'{wd} px: {fit["n"]} legends in the Report, no sideways scroll, every swatch has a size and does not touch its text, no text is cut off', fit['page'] and fit['bad'] == [] and fit['n'] >= 6, fit)
            await pg.evaluate("() => window.__tapnaplo.S.tab = 'nutr'"); await pg.evaluate("() => { window.__tapnaplo.S.day = '%s'; window.__tapnaplo.render(); }" % day(-2)); await pg.wait_for_timeout(60)
            fit2 = await pg.evaluate(FIT_JS)
            check(f'{wd} px: the reference legend on the Nutrients tab fits too', fit2['page'] and fit2['bad'] == [] and fit2['n'] == 1, fit2)
            await pg.evaluate("() => { window.__tapnaplo.S.tab = 'report'; window.__tapnaplo.render(); document.querySelectorAll('#view details.rp-sec, #view details.fold').forEach((d) => { d.open = true; }); }"); await pg.wait_for_timeout(60)
            for theme in ('light', 'dark'):
                await pg.evaluate("(t) => document.documentElement.setAttribute('data-theme', t)", theme)
                bad = [x for sel in ('details[data-sec=meals]', 'details[data-sec=foods]', 'details[data-sec=nova]', 'details[data-sec=nutrients]') for x in await pg.evaluate(CONTRAST_JS, sel)]
                g = await pg.evaluate(GFX, 'details[data-sec=meals] .card')
                g2 = await pg.evaluate(GFX, 'details[data-sec=nova] .card:nth-child(2)')
                check(f'{wd} px, {theme}: the legend text has at least 4.5:1; the signs (accent, dashes) and the outline of the NOVA squares have at least 3:1 against the card',
                      bad == [] and g['--accent'] >= 3 and g['--muted'] >= 3 and (g2['outlineRatio'] or 0) >= 3, (bad[:3], g['--accent'], g['--muted'], g2['outlineRatio']))
            await cx.close()

        # =========================================================== 10 nothing new is stored, version
        cx, pg = await fresh(390, 844, 'B')
        await seed(WEEK, pg=pg)
        await pg.click('[data-tab=data]'); await pg.wait_for_selector('[data-act=export-json]')
        async with pg.expect_download() as dd:
            await pg.click('[data-act=export-json]')
        dl = await dd.value
        backup = json.loads(pathlib.Path(await dl.path()).read_text(encoding='utf-8'))
        check('the backup has exactly the keys it had before (a legend stores nothing)', sorted(backup.keys()) == sorted(['app', 'version', 'exported', 'log', 'foods', 'meta', 'health']) and 'legend' not in json.dumps(backup['meta']).lower(), sorted(backup.keys()))
        ver = re.search(r'(\d+) · \d+ \w+ 20\d\d', await pg.evaluate('document.body.innerText'))
        check('the Data tab shows version 32 or newer', bool(ver) and int(ver.group(1)) >= 32, ver and ver.group(0))
        sw = open(ROOT / 'sw.js', encoding='utf-8').read()
        check('the service worker cache has the number of the version', bool(ver) and f"const CACHE = 'nutrilog-v{ver.group(1)}'" in sw)
        await cx.close()
        check('no page errors', errs == [], errs[:6])
        await browser.close()
        print('\nALL PASSED' if not problems else f'\n{len(problems)} FAILED: {problems}')
        sys.exit(1 if problems else 0)


asyncio.run(main())
