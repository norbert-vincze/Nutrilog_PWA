"""Omega-6 : omega-3 ratio on the Nutrients tab (version 28). Run with the web server on port 8765 (see CLAUDE.md).

A calculated row "Omega-6 : omega-3 ratio" in "Fatty acids & cholesterol", right under DHA (and under the EPA + DHA reference row when a profile is set), above Cholesterol.
omega-6 = linoleic + arachidonic acid, omega-3 = alpha-linolenic acid + EPA + DHA, worked out from the day's totals of those rows. Only items with data count; an item with no
data for a fatty acid is left out and never counted as 0. No ratio without data on both sides ("no data"); "≈" in front when some item lacks one of the five; "~" when part of a value is
an estimate; "≥ x" when the omega-3 total is only known to be below a limit; a range from "<x" values; "not defined" when omega-3 is 0 or everything is only a limit.
Covers: every state, the numbers against a hand calculation, the detail lines, same food twice, placement (with and without a profile), the number of rows, spoken text, the shared
view, a hostile food name, contrast in light and dark, 390 and 320 px, the version number, no page errors."""
import asyncio, os, pathlib, re, sys
from playwright.async_api import async_playwright
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_ai_import import CONTRAST_JS

URL = 'http://127.0.0.1:8765/index.html'
SHOTS = os.environ.get('SHOTS', '')

LA, AA = 'fa_18_2_9c_12c_n_6', 'fa_20_4_5c_8c_11c_14c_n_6'
ALA, EPA, DHA = 'fa_18_3_c9_c12_c15_n_3', 'fa_20_5_5c_8c_11c_14c_17c_n_3_epa', 'fa_22_6_4c_7c_10c_13c_16c_19c_n_3_dha'

INIT = """
window.__txt = (el, skip) => { let s = ''; const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  while (w.nextNode()) { const n = w.currentNode; if (n.parentElement.closest(skip)) continue; s += n.textContent; }
  return s.replace(/\\s+/g, ' ').trim(); };
"""
RATIO = """() => { const r = document.querySelector('.ratio-row'); if (!r) return null; r.open = true;
  const v = r.querySelector('.nval'), p = r.querySelector('.pill'), pv = r.previousElementSibling, nx = r.nextElementSibling;
  return { vis: window.__txt(v, '.sr-only'), spoken: window.__txt(v, '[aria-hidden="true"]'), pill: p.textContent, cls: p.className.replace('pill', '').trim(),
    det: [...r.querySelectorAll('.ndetail')].map((d) => d.textContent), none: v.classList.contains('none'),
    prev: pv && pv.querySelector('summary > span').textContent, next: nx && nx.querySelector('summary > span').textContent,
    group: r.closest('section.group, details.group').querySelector('h3, summary').textContent.trim(), label: r.querySelector('summary > span').textContent,
    extra: r.querySelectorAll('.rline, .ncontrib').length, count: document.querySelectorAll('.ratio-row').length }; }"""


def own(fid, name, n, **kw):
    f = {'id': fid, 'src': 'user', 'name': name, 'brand': '', 'barcode': '', 'basis': {'qty': 100, 'unit': 'g'}, 'n': n, 'nova': None, 'portions': [], 'note': '', 'created': 1000, 'updated': 1000}
    f.update(kw)
    return f


FISH = own('u:fish', 'Salmon', {'kcal': 200, LA: 0.5, AA: 0.1, ALA: 0.3, EPA: 1.0, DHA: 1.5})        # all five
OIL = own('u:oil', 'Rapeseed oil', {'kcal': 880, LA: 20, ALA: 9})                                        # omega-6 and omega-3, no AA/EPA/DHA
ONLY6 = own('u:o6', 'Only omega six', {'kcal': 10, LA: 10})
ONLY3 = own('u:o3', 'Only omega three', {'kcal': 10, ALA: 2})
NOFA = own('u:nofa', 'No fatty acid data', {'kcal': 50})
ZERO3 = own('u:z3', 'Zero omega three', {'kcal': 10, LA: 5, ALA: 0})
LIM3 = own('u:lim3', 'Limit omega three', {'kcal': 10, LA: 10, ALA: '<2'})                              # omega-3 only known to be below 2
LIM6 = own('u:lim6', 'Limit omega six', {'kcal': 10, LA: '<4', ALA: 2})                                  # omega-6 only known to be below 4
LIMBOTH = own('u:limb', 'Limit both', {'kcal': 10, LA: '<1', ALA: '<1'})
ESTFISH = own('u:efish', 'Estfish', {'kcal': 200, LA: 0.5, AA: 0.1, ALA: 0.3, EPA: 1.0, DHA: 1.5}, est=[LA], q='m')
EVIL = own('u:evil', '<img src=x onerror="window.__pwn=1"><b>X</b> & "Q"', {'kcal': 10, LA: 3, ALA: 1})
FOODS = [FISH, OIL, ONLY6, ONLY3, NOFA, ZERO3, LIM3, LIM6, LIMBOTH, ESTFISH, EVIL]


async def main():
    async with async_playwright() as p:
        problems = []

        def check(name, ok, info=''):
            print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(info)[:500].replace('\n', ' | ')) if info != '' else ''))
            if not ok: problems.append(name)

        browser = await p.chromium.launch()
        errs = []

        async def new_ctx(w=390, h=844):
            c = await browser.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2, is_mobile=True, has_touch=True, locale='en-GB', service_workers='block')
            await c.add_init_script(INIT)
            await c.route('**/*openfoodfacts.org/**', lambda r: r.fulfill(status=200, headers={'access-control-allow-origin': '*', 'content-type': 'application/json'}, body='{"products":[],"status":0}'))
            return c

        def watch(pg, tag='P'):
            pg.on('pageerror', lambda e: errs.append(f'{tag} PE {e}'))
            pg.on('console', lambda m: errs.append(f'{tag} C {m.text}') if m.type == 'error' and 'Failed to load resource' not in m.text else None)

        ctx = await new_ctx()
        page = await ctx.new_page(); watch(page)
        await page.goto(URL); await page.wait_for_selector('.hero')
        T = page.evaluate
        KEYS = await T('window.__tapnaplo.KEYS')
        fmt = lambda v: T('(v) => window.__tapnaplo.fmt(v)', v)

        async def seed(entries, ref=None, pg=page, foods=FOODS):
            await pg.evaluate("""([foods, entries, ref]) => { const t = window.__tapnaplo, S = t.S; S.log.length = 0; S.meta.ref = ref;
              for (const f of foods) S.foods[f.id] = f;
              entries.forEach(([id, f, a], i) => S.log.push({ id, f, a, d: S.day, m: 'm1', t: 1000 + i, tm: '08:' + String(10 + i) }));
              S.tab = 'nutr'; t.save(); t.render(); }""", [foods, entries, ref])
            await pg.wait_for_timeout(60)

        async def ratio(pg=page):
            return await pg.evaluate(RATIO)

        # ---------------- an empty day and the placement of the row ----------------
        await seed([])
        check('an empty day has no ratio row (only the "Nothing logged" card)', await ratio() is None)

        await seed([('e1', 'u:fish', 100)])
        r = await ratio()
        check('the row exists exactly once, with its name, in the group "Fatty acids & cholesterol"', r and r['count'] == 1 and r['label'] == 'Omega-6 : omega-3 ratio' and r['group'] == 'Fatty acids & cholesterol', r)
        check('it sits under DHA and above Cholesterol (no profile)', r['prev'] == 'DHA (22:6 n-3)' and r['next'] == 'Cholesterol', [r['prev'], r['next']])
        check('it has no reference bar and no "Added up from" list', r['extra'] == 0)
        check('every nutrient still has its row and there is exactly one extra row', await T("document.querySelectorAll('details.nrow').length") == len(KEYS) + 1, [await T("document.querySelectorAll('details.nrow').length"), len(KEYS)])
        await seed([('e1', 'u:fish', 100)], ref={'sex': 'f', 'age': '25', 'meno': 'pre', 'zinc': 600})
        r = await ratio()
        check('with a reference profile it sits under the EPA + DHA row, above Cholesterol', r['prev'] == 'EPA + DHA' and r['next'] == 'Cholesterol', [r['prev'], r['next']])
        await seed([('e1', 'u:fish', 100)])

        # ---------------- complete data: Salmon 100 g ----------------
        exp = await fmt((0.5 + 0.1) / (0.3 + 1.0 + 1.5))
        check('Salmon 100 g: (0.5 + 0.1) / (0.3 + 1 + 1.5) = 0.21 : 1', r['vis'] == f'{exp}: 1' and exp == '0.21', [r['vis'], exp])
        check('...complete data: no ≈, pill 1/1 in the "full" colour', not r['vis'].startswith('≈') and r['pill'] == '1/1' and r['cls'] == 'full', [r['pill'], r['cls']])
        check('...the lines show omega-6 0.6 g and omega-3 2.8 g and that every item has all five', r['det'][1] == 'Omega-6: 0.6 g (Linoleic acid 0.5 g; Arachidonic acid 0.1 g)' and r['det'][2] == 'Omega-3: 2.8 g (Alpha-linolenic acid 0.3 g; EPA 1 g; DHA 1.5 g)' and r['det'][-1] == 'Every item has data for all five fatty acids.', r['det'])
        check('...the first line says what is divided and that there is no target', r['det'][0].startswith('Omega-6 divided by omega-3') and 'shows no target' in r['det'][0])
        check('...nothing is shown as ≥ or ≈ and a screen reader hears the same number', r['spoken'] == r['vis'] and '≥' not in ' '.join(r['det'][1:3]))
        # the same numbers as the rows above it
        rows = await T("""() => { const t = window.__tapnaplo, T = t.totalsFor(t.S.log.filter((e) => e.d === t.S.day)); const g = (k) => T.lo[t.IDX[k]]; return [g('%s') + g('%s'), g('%s') + g('%s') + g('%s')]; }""" % (LA, AA, ALA, EPA, DHA))
        check('the ratio is the sum of the omega-6 rows divided by the sum of the omega-3 rows (checked with the totals)', abs(rows[0] / rows[1] - 0.6 / 2.8) < 1e-9, rows)

        # ---------------- same food twice, and two foods ----------------
        await seed([('e1', 'u:fish', 100), ('e2', 'u:fish', 50)])
        r = await ratio()
        check('the same food twice (150 g) gives the same ratio and pill 2/2', r['vis'] == '0.21: 1' and r['pill'] == '2/2', [r['vis'], r['pill']])

        # ---------------- partial data ----------------
        await seed([('e1', 'u:oil', 20)])
        r = await ratio()
        exp = await fmt((20 * 0.2) / (9 * 0.2))
        check('Rapeseed oil 20 g (no arachidonic acid, EPA, DHA): ≈ 2.22 : 1', r['vis'] == f'≈ {exp}: 1' and exp == '2.22', [r['vis'], exp])
        check('...a screen reader hears "approximately", not the sign', r['spoken'] == f'approximately {exp}: 1', r['spoken'])
        check('...pill 1/1 in the "part" colour', r['pill'] == '1/1' and r['cls'] == 'part', [r['pill'], r['cls']])
        check('...the totals are lower values (≥) and the missing fatty acids are named, not zero', r['det'][1] == 'Omega-6: ≥ 4 g (Linoleic acid 4 g; Arachidonic acid: no data)' and r['det'][2] == 'Omega-3: ≥ 1.8 g (Alpha-linolenic acid 1.8 g; EPA: no data; DHA: no data)', r['det'])
        check('...the item with the gaps is named with what it lacks', 'No data for: Rapeseed oil (Arachidonic acid, EPA, DHA)' in r['det'])
        check('...and the ≈ is explained', any(d.startswith('≈ means the ratio is worked out from the values that exist') and 'not counted as 0' in d for d in r['det']))

        await seed([('e1', 'u:oil', 20), ('e2', 'u:fish', 100)])
        r = await ratio()
        exp = await fmt((4 + 0.5 + 0.1) / (1.8 + 0.3 + 1.0 + 1.5))
        check('Oil 20 g + Salmon 100 g: 4.6 / 4.6 = 1 : 1, with ≈ because the oil lacks three fatty acids', r['vis'] == f'≈ {exp}: 1' and exp == '1', [r['vis'], exp])
        check('...pill 2/2 (both items have some of the five)', r['pill'] == '2/2')
        check('...Arachidonic acid, EPA and DHA are lower values (≥) because only the salmon has them', 'Arachidonic acid ≥ 0.1 g' in r['det'][1] and 'EPA ≥ 1 g; DHA ≥ 1.5 g' in r['det'][2], r['det'][1:3])
        check('...the item without gaps (Salmon) is not in the "No data for" line', any(d.startswith('No data for: Rapeseed oil') and 'Salmon' not in d for d in r['det']))

        # ---------------- no ratio ----------------
        for name, entries in [('no fatty acid data at all', [('e1', 'u:nofa', 100)]), ('only omega-6 has data', [('e1', 'u:o6', 100)]), ('only omega-3 has data', [('e1', 'u:o3', 100)])]:
            await seed(entries)
            r = await ratio()
            check(f'{name}: "no data", no number, pill 0/1, grey', r['vis'] == 'no data' and r['none'] and r['pill'] == '0/1' and r['cls'] == 'none' and not re.search(r'\d', r['vis']), r)
            check(f'{name}: the line says what a ratio needs', 'A ratio needs data for at least one omega-6 and one omega-3 fatty acid.' in r['det'])
        await seed([('e1', 'u:o6', 100), ('e2', 'u:o3', 100)])
        r = await ratio()
        check('omega-6 from one item and omega-3 from another item: the ratio is worked out from the totals (10 / 2 = 5 : 1, with ≈)', r['vis'] == '≈ 5: 1' and r['pill'] == '2/2', r['vis'])

        # ---------------- limits (<x) and zero ----------------
        await seed([('e1', 'u:zero3' if False else 'u:z3', 100)])
        r = await ratio()
        check('omega-3 is a real 0: "not defined" with the reason, never a number', r['vis'] == 'not defined' and r['none'] and 'Omega-3 is 0 in the data, so there is no ratio.' in r['det'] and not re.search(r'\d', r['vis']), r)
        await seed([('e1', 'u:lim3', 100)])
        r = await ratio()
        check('omega-3 only known to be below 2: a lower limit "≥ 5 : 1" (10 / 2)', r['vis'] == '≈ ≥ 5: 1', r['vis'])
        await seed([('e1', 'u:lim6', 100)])
        r = await ratio()
        check('omega-6 only known to be below 4: a range "0–2 : 1" (0..4 divided by 2)', r['vis'] == '≈ 0–2: 1', r['vis'])
        await seed([('e1', 'u:limb', 100)])
        r = await ratio()
        check('both only limits: "not defined" with the reason', r['vis'] == 'not defined' and 'The values are only known to be below a limit, so no ratio can be given.' in r['det'], r)

        # ---------------- estimate ----------------
        await seed([('e1', 'u:efish', 100)])
        r = await ratio()
        check('a value that is an estimate: "~" in front, spoken as "estimated", and the old estimate line', r['vis'] == '~0.21: 1' and r['spoken'] == 'estimated 0.21: 1' and any(d.startswith('Estimate, not a label value: Estfish (medium)') for d in r['det']), [r['vis'], r['spoken'], r['det'][-1]])

        # ---------------- a food with all 64 values ----------------
        await seed([('e1', 'u:all', 100)], foods=FOODS + [own('u:all', 'Everything', {k: 1 for k in KEYS})])
        r = await ratio()
        exp = await fmt(2 / 3)
        check('a food with every value = 1: (1 + 1) / (1 + 1 + 1) = ' + exp + ' : 1, complete', r['vis'] == f'{exp}: 1', r['vis'])

        # ---------------- hostile name ----------------
        await seed([('e1', 'u:evil', 100)])
        r = await ratio()
        check('a food name with HTML is shown as text in the "No data for" line and nothing runs', any(d.startswith('No data for: <img src=x onerror="window.__pwn=1"><b>X</b> & "Q" (') for d in r['det']) and await T("document.querySelectorAll('.ratio-row img, .ratio-row b').length") == 0 and await T('window.__pwn') is None, r['det'])

        # ---------------- the shared (read-only) view ----------------
        await seed([('e1', 'u:oil', 20), ('e2', 'u:fish', 100)])
        sender = await ratio()
        day = await T('window.__tapnaplo.S.day')
        link = await T('async (d) => (await window.__tapnaplo.shareLink(d, d)).url', day)
        ctxV = await new_ctx()
        vp = await ctxV.new_page(); watch(vp, 'V')
        await vp.goto(link); await vp.wait_for_selector('.hero')
        await vp.click('#tabbar .tab >> nth=1'); await vp.wait_for_selector('.nrow')
        viewer = await ratio(vp)
        check('the shared view shows the same row with the same numbers and lines', viewer == sender and viewer['vis'] == '≈ 1: 1', [viewer, sender])
        await ctxV.close()

        # ---------------- looks: contrast, 390 and 320 px ----------------
        await seed([('e1', 'u:oil', 20), ('e2', 'u:fish', 100), ('e3', 'u:nofa', 100)])
        for theme in ('light', 'dark'):
            await T(f"document.documentElement.setAttribute('data-theme', '{theme}')")
            await ratio()
            bad = await T(CONTRAST_JS, '#view')
            check(f'the Nutrients tab with the ratio row open: text contrast at least 4.5:1 ({theme})', bad == [], bad)
            if SHOTS:
                await T("document.querySelector('.ratio-row').scrollIntoView({block: 'center'})")
                await page.screenshot(path=os.path.join(SHOTS, f'omega_ratio_{theme}.png'))
        await T("document.documentElement.setAttribute('data-theme', 'light')")
        check('390 px: no sideways scroll with the row open', await T('document.documentElement.scrollWidth <= window.innerWidth'))

        ctxN = await new_ctx(320, 640)
        np_ = await ctxN.new_page(); watch(np_, 'N')
        await np_.goto(URL); await np_.wait_for_selector('.hero')
        await seed([('e1', 'u:oil', 20), ('e2', 'u:fish', 100), ('e3', 'u:evil', 100)], pg=np_)
        rn = await ratio(np_)
        check('320 px: the row is there and nothing makes the page wider', rn is not None and await np_.evaluate('document.documentElement.scrollWidth <= window.innerWidth'))
        wide = await np_.evaluate("(() => { const r = document.querySelector('.ratio-row'); return [...r.querySelectorAll('.ndetail, summary > *')].filter((e) => e.scrollWidth > e.clientWidth + 1).map((e) => e.textContent.slice(0, 30)); })()")
        check('320 px: no line or value of the row is cut off', wide == [], wide)
        if SHOTS:
            await np_.evaluate("document.querySelector('.ratio-row').scrollIntoView({block: 'start'})")
            await np_.screenshot(path=os.path.join(SHOTS, 'omega_ratio_320.png'))
        await ctxN.close()

        # ---------------- version ----------------
        await page.click('[data-tab=data]'); await page.wait_for_timeout(300)
        ver = re.search(r'(\d+) · \d+ \w+ 20\d\d', await T('document.body.innerText'))
        check('the Data tab shows version 28 or newer', bool(ver) and int(ver.group(1)) >= 28, ver and ver.group(0))
        sw = open(pathlib.Path(__file__).resolve().parent.parent / 'sw.js', encoding='utf-8').read()
        check('the service worker cache has the number of the version', bool(ver) and f"const CACHE = 'nutrilog-v{ver.group(1)}'" in sw)
        check('no page errors', errs == [], errs[:5])
        await browser.close()
        print('\nALL PASS' if not problems else f'\n{len(problems)} FAILED: {problems}')
        sys.exit(1 if problems else 0)


asyncio.run(main())
