"""Reference intake (version 26). Run with the web server on port 8765 (see CLAUDE.md).

The Nutrients tab can show the EFSA Dietary Reference Values for adults (18+) next to the day's totals: a thin bar and "≥ 77% of 950 mg · PRI" under the rows that have a value.
A small profile (sex or pregnant/nursing, age 18-24 or 25+, menopause for women, zinc phytate level) decides which value applies. PRI = solid bar, AI = dashed bar, SAI = dotted bar.
Missing data is never zero: "≥" when an item has no data, "~" for estimates, a range for "<x" values, no bar and no 0% without data. Vitamin A is counted in retinol equivalents, B1 and niacin
follow the energy of the day (only with complete energy data), niacin is always a lower value. Fibre and EPA + DHA are included.
Covers: the value table (a hand-typed copy of the EFSA tables, every profile), the percent and its marks, every special row, the profile card and its sheet (quick Male/Female, Change, Save, Remove,
Undo), cleanRef, old and damaged saves, backup and Restore (also old and damaged files), Sync with a fake GitHub (ref/profile.json, two devices, tombstone, bad records), Share (switch, same numbers
in the viewer, nothing written, hostile ref), the other tabs untouched, touch targets, contrast in light and dark, 390 and 320 px, the version number, no page errors."""
import asyncio, base64, csv, io, json, math, os, pathlib, re, sys, zlib
from datetime import date, timedelta
from playwright.async_api import async_playwright
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_ai_import import CONTRAST_JS, SMALL_FONTS
from test_sync import FakeGitHub, GOOD

URL = 'http://127.0.0.1:8765/index.html'
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
SHOTS = os.environ.get('SHOTS', '')

WATCH = """(() => {
  window.__w = { idbOpen: 0, idbWrite: 0, lsWrite: 0 };
  const o = indexedDB.open.bind(indexedDB); indexedDB.open = function () { window.__w.idbOpen++; return o.apply(this, arguments); };
  for (const m of ['put', 'add', 'delete', 'clear']) { const f = IDBObjectStore.prototype[m]; IDBObjectStore.prototype[m] = function () { window.__w.idbWrite++; return f.apply(this, arguments); }; }
  for (const m of ['setItem', 'removeItem', 'clear']) { const f = Storage.prototype[m]; Storage.prototype[m] = function () { window.__w.lsWrite++; return f.apply(this, arguments); }; }
})();"""
SIZES = "(sel) => [...document.querySelectorAll(sel)].filter((e) => !e.hidden && e.getClientRects().length).map((e) => { const r = e.getBoundingClientRect(); return [(e.id || e.dataset.act || e.className || e.tagName) + ':' + e.textContent.trim().slice(0, 14), Math.round(r.width), Math.round(r.height)]; }).filter((x) => x[2] < 44 || x[1] < 44)"
# the bar against what is behind it: at least 3:1 (a graphic, not text)
BAR_CONTRAST = """() => {
  const parse = (c) => { const m = c.match(/rgba?\\(([^)]+)\\)/); if (!m) return null; const p = m[1].split(/[ ,\\/]+/).filter(Boolean).map(Number); return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; };
  const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const behind = (el) => { for (let e = el; e; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor); if (c && c.a > 0.9) return c; } return { r: 255, g: 255, b: 255, a: 1 }; };
  const out = [];
  for (const t of document.querySelectorAll('.rtrack')) {
    const cs = getComputedStyle(t), bg = behind(t.parentElement), fill = parse(getComputedStyle(t.firstElementChild).backgroundColor);
    const edge = t.classList.contains('pri') ? parse(cs.backgroundColor) : parse(cs.borderTopColor);
    const kinds = t.className;
    if (edge && ratio(edge, bg) < 1.1 && !t.classList.contains('pri')) out.push(['edge', kinds, ratio(edge, bg).toFixed(2)]);
    if (t.classList.contains('pri') && fill && ratio(fill, parse(cs.backgroundColor)) < 3) out.push(['fill', kinds, ratio(fill, parse(cs.backgroundColor)).toFixed(2)]);
    if (!t.classList.contains('pri') && edge && ratio(edge, bg) < 3) out.push(['dash', kinds, ratio(edge, bg).toFixed(2)]);
    if (fill && fill.a > 0.5 && ratio(fill, bg) < 3) out.push(['fill-vs-row', kinds, ratio(fill, bg).toFixed(2)]);
  }
  return out;
}"""

# ---- the EFSA tables, typed in by hand (a separate copy of section 4 of the plan, so a slip in app.js cannot hide) ----
# key: (type, male, female before menopause, female past menopause, pregnant, nursing)
TABLE = {
    'phosphorus': ('AI', 550, 550, 550, 550, 550),
    'magnesium': ('AI', 350, 300, 300, 300, 300),
    'potassium': ('AI', 3500, 3500, 3500, 3500, 4000),
    'sodium': ('SAI', 2000, 2000, 2000, 2000, 2000),
    'chloride': ('SAI', 3100, 3100, 3100, 3100, 3100),
    'iron': ('PRI', 11, 16, 11, 16, 16),
    'copper': ('AI', 1.6, 1.3, 1.3, 1.5, 1.5),
    'manganese': ('AI', 3.0, 3.0, 3.0, 3.0, 3.0),
    'selenium': ('AI', 70, 70, 70, 70, 85),
    'iodine': ('AI', 150, 150, 150, 200, 200),
    'retinol': ('PRI', 750, 650, 650, 700, 1300),
    'vitamin_d': ('AI', 15, 15, 15, 15, 15),
    'vitamin_e': ('AI', 13, 11, 11, 11, 11),
    'vitamin_k1': ('AI', 70, 70, 70, 70, 70),
    'vitamin_c': ('PRI', 110, 95, 95, 105, 155),
    'vitamin_b1_or_thiamin': ('PRI', 0.1, 0.1, 0.1, 0.1, 0.1),        # mg per MJ
    'vitamin_b2_or_riboflavin': ('PRI', 1.6, 1.6, 1.6, 1.9, 2.0),
    'vitamin_b3_or_niacin': ('PRI', 1.6, 1.6, 1.6, 1.6, 1.6),         # mg NE per MJ
    'vitamin_b5_or_pantothenic_acid': ('AI', 5, 5, 5, 5, 7),
    'vitamin_b6': ('PRI', 1.7, 1.6, 1.6, 1.8, 1.7),
    'vitamin_b9_or_folate': ('PRI', 330, 330, 330, 600, 500),         # pregnant: AI 600
    'vitamin_b12': ('AI', 4.0, 4.0, 4.0, 4.5, 5.0),
    'fibres': ('AI', 25, 25, 25, 25, 25),
    'epa_dha': ('AI', 250, 250, 250, 350, 350),
}
ZINC = {  # phytate 300 / 600 / 900 / 1200 mg
    'm': [9.4, 11.7, 14.0, 16.3], 'f': [7.5, 9.3, 11.0, 12.7], 'p': [9.1, 10.9, 12.6, 14.3], 'n': [10.4, 12.2, 13.9, 15.6]}
PROFILES = {  # name: (profile, column of TABLE)
    'm': ({'sex': 'm', 'age': '25', 'zinc': 600}, 1),
    'f-pre': ({'sex': 'f', 'age': '25', 'meno': 'pre', 'zinc': 600}, 2),
    'f-post': ({'sex': 'f', 'age': '25', 'meno': 'post', 'zinc': 600}, 3),
    'p': ({'sex': 'p', 'age': '25', 'zinc': 600}, 4),
    'n': ({'sex': 'n', 'age': '25', 'zinc': 600}, 5),
}


def b64u(b):
    return base64.urlsafe_b64encode(b).decode().rstrip('=')


def unb64u(s):
    return base64.urlsafe_b64decode(s + '=' * (-len(s) % 4))


def link(raw, prefix='z'):
    data = json.dumps(raw).encode('utf-8')
    return URL + '#share=' + prefix + '.' + b64u(zlib.compress(data) if prefix == 'z' else data)


def unpack(url):
    m = re.search(r'#share=([zj])\.(.+)$', url)
    raw = unb64u(m.group(2))
    return json.loads(zlib.decompress(raw) if m.group(1) == 'z' else raw)


def own(fid, name, n, **extra):
    d = {'id': fid, 'src': 'user', 'name': name, 'brand': '', 'barcode': '', 'basis': {'qty': 100, 'unit': 'g'}, 'n': n, 'nova': None, 'portions': [], 'note': '', 'created': 1000, 'updated': 1000}
    d.update(extra)
    return d


def pct(x):  # the same rounding as Math.round
    return math.floor(x + 0.5)


async def main():
    async with async_playwright() as p:
        problems = []

        def check(name, ok, info=''):
            print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(info)) if info != '' else ''))
            if not ok: problems.append(name)

        browser = await p.chromium.launch()
        errs, outside = [], []

        def watch(pg, tag):
            pg.on('pageerror', lambda e: errs.append(f'{tag} PE {e}'))
            pg.on('console', lambda m: errs.append(f'{tag} C {m.text}') if m.type == 'error' and 'Failed to load resource' not in m.text else None)
            pg.on('request', lambda r: outside.append(r.url) if not r.url.startswith('http://127.0.0.1') and not r.url.startswith('data:') and not r.url.startswith('blob:') and 'api.github.com' not in r.url else None)

        async def new_ctx(w=390, h=844, **kw):
            c = await browser.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2, is_mobile=True, has_touch=True, locale='en-GB', service_workers='block', accept_downloads=True, permissions=['clipboard-read', 'clipboard-write'], **kw)
            await c.route('**/*openfoodfacts.org/**', lambda r: r.fulfill(status=200, headers={'access-control-allow-origin': '*', 'content-type': 'application/json'}, body='{"products":[],"status":0}'))
            return c

        ctx = await new_ctx()
        page = await ctx.new_page(); watch(page, 'A')
        await page.goto(URL); await page.wait_for_selector('.hero')
        T = page.evaluate
        today = await T("""(() => { const d = new Date(); const p = (n) => String(n).padStart(2, '0'); return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`; })()""")
        D = date.fromisoformat(today)
        day = lambda n: (D + timedelta(days=n)).isoformat()
        ref = lambda pg=page: pg.evaluate("() => JSON.parse(JSON.stringify(window.__tapnaplo.S.meta.ref))")

        async def seed(foods, entries, prof=None, tab='nutr', pg=page):
            """own foods and entries (food id, grams) for today; a profile or none; the tab is shown"""
            await pg.evaluate("""([foods, entries, prof, tab]) => { const t = window.__tapnaplo, S = t.S; S.foods = {}; for (const f of foods) S.foods[f.id] = f;
              S.log.length = 0; entries.forEach((e, i) => S.log.push({ id: 'e' + i, d: S.day, m: 'm1', f: e[0], a: e[1], t: i + 1, tm: '08:0' + i }));
              S.meta.ref = prof; S.tab = tab; t.save(); t.render(); }""", [foods, entries, prof, tab])

        row = lambda label, pg=page: pg.evaluate("""(label) => { const r = [...document.querySelectorAll('.nrow')].find((x) => x.querySelector('summary > span').textContent === label); if (!r) return null;
          const t = r.querySelector('.rtxt'), tr = r.querySelector('.rtrack'), f = r.querySelector('.rfill'), sr = r.querySelector('.rline .sr-only');
          return { txt: t ? t.textContent : null, cls: tr ? tr.className : null, w: f ? f.style.width : null, sr: sr ? sr.textContent : null, detail: [...r.querySelectorAll('.ndetail')].map((d) => d.textContent), val: r.querySelector('.nval').textContent, pill: r.querySelector('.pill').textContent, hasLine: !!r.querySelector('.rline') }; }""", label)
        lines = lambda pg=page: pg.evaluate("() => [...document.querySelectorAll('.nrow')].filter((r) => r.querySelector('.rline')).map((r) => [r.querySelector('summary > span').textContent, r.querySelector('.rtxt').textContent])")

        # =========================================================== 1 the value table (every profile, every row)
        got = {}
        for name, (prof, col) in PROFILES.items():
            got[name] = await T("""(prof) => { const D = window.__tapnaplo.DRV; return Object.fromEntries(Object.entries(D).map(([k, d]) => [k, [typeof d.type === 'function' ? d.type(prof) : d.type, d.v(prof)]])); }""", prof)
        bad = []
        for name, (prof, col) in PROFILES.items():
            for k, row_ in TABLE.items():
                typ = row_[0]
                if k == 'vitamin_b9_or_folate' and name == 'p': typ = 'AI'
                g = got[name].get(k)
                if g is None or g[0] != typ or abs(g[1] - row_[col]) > 1e-9: bad.append((name, k, g, (typ, row_[col])))
        check('value table: all 24 rows + fibre + EPA/DHA, for male, female before/past menopause, pregnant, nursing: value and type match the hand-typed EFSA table', not bad, bad[:4])
        check('value table: 26 rows (24 EFSA micronutrient rows + Fibre + EPA + DHA) plus calcium and zinc', len(TABLE) + 2 == len(await T("() => Object.keys(window.__tapnaplo.DRV)")), len(await T("() => Object.keys(window.__tapnaplo.DRV)")))
        cal = {(a, s): (await T("([a, s]) => window.__tapnaplo.DRV.calcium.v({ sex: s, age: a, zinc: 600 })", [a, s])) for a in ('18', '25') for s in 'mfpn'}
        check('value table: calcium 1000 mg at 18–24, 950 mg at 25 and over, for every sex', all(v == (1000 if a == '18' else 950) for (a, s), v in cal.items()), cal)
        zbad = []
        for s in 'mfpn':
            for i, z in enumerate((300, 600, 900, 1200)):
                v = await T("([s, z]) => window.__tapnaplo.DRV.zinc.v({ sex: s, age: '25', meno: 'pre', zinc: z })", [s, z])
                if abs(v - ZINC[s][i]) > 1e-9: zbad.append((s, z, v, ZINC[s][i]))
        check('value table: zinc for four phytate levels and four groups (16 values)', not zbad, zbad)
        check('value table: calcium and zinc are PRI', await T("() => ['calcium', 'zinc'].every((k) => window.__tapnaplo.DRV[k].type === 'PRI')"))
        check('value table: 10 PRI, 12 AI, 2 SAI among the 24 micronutrient rows (folate counted as PRI; pregnant is the one AI exception)', await T("""() => { const D = window.__tapnaplo.DRV, p = { sex: 'f', age: '25', meno: 'pre', zinc: 600 };
          const keys = Object.keys(D).filter((k) => k !== 'fibres' && k !== 'epa_dha'); const t = keys.map((k) => typeof D[k].type === 'function' ? D[k].type(p) : D[k].type);
          return [keys.length, t.filter((x) => x === 'PRI').length, t.filter((x) => x === 'AI').length, t.filter((x) => x === 'SAI').length].join(); }""") == '24,10,12,2')
        keys_ok = await T("() => { const t = window.__tapnaplo; return Object.entries(t.DRV).every(([k, d]) => (d.comps || [[k]]).every(([c]) => c in t.IDX)); }")
        check('value table: every row points at a nutrient that exists in the food tables (and the unit shown is the unit of the table, or RE/DFE/NE)', keys_ok)
        units = await T("() => { const t = window.__tapnaplo, K = t.KEYS; return Object.fromEntries(Object.entries(t.DRV).filter(([k, d]) => !d.comps).map(([k, d]) => [k, d.u])); }")
        tableunits = {n['key']: n['unit'] for n in json.loads((ROOT / 'ciqual.json').read_text())['nutrients']}
        okunits = all(u == tableunits[k] or (k == 'vitamin_b3_or_niacin' and u == 'mg NE') or (k == 'vitamin_b9_or_folate' and u == 'µg DFE') for k, u in units.items())
        check('value table: units agree with ciqual.json', okunits, {k: (u, tableunits[k]) for k, u in units.items() if u != tableunits[k]})

        # =========================================================== 2 cleanRef
        cr = lambda x: T("(x) => window.__tapnaplo.cleanRef(x)", x)
        check('cleanRef: a good man, woman (with menopause), pregnant and nursing profile', await cr({'sex': 'm', 'age': '25', 'zinc': 600}) == {'sex': 'm', 'age': '25', 'zinc': 600} and await cr({'sex': 'f', 'age': '18', 'meno': 'post', 'zinc': 300}) == {'sex': 'f', 'age': '18', 'meno': 'post', 'zinc': 300} and await cr({'sex': 'p', 'age': '25', 'zinc': 1200}) is not None and await cr({'sex': 'n', 'age': '18', 'zinc': 900}) is not None)
        check('cleanRef: "meno" on a man, pregnant or nursing profile is left out', await cr({'sex': 'm', 'age': '25', 'meno': 'pre', 'zinc': 600}) == {'sex': 'm', 'age': '25', 'zinc': 600} and 'meno' not in (await cr({'sex': 'p', 'age': '25', 'meno': 'post', 'zinc': 600})))
        check('cleanRef: unknown keys are dropped (nothing can ride along)', await cr({'sex': 'm', 'age': '25', 'zinc': 600, 'weight': 80, 'name': 'x'}) == {'sex': 'm', 'age': '25', 'zinc': 600})
        badr = [None, 5, 'text', [], {}, {'sex': 'x', 'age': '25', 'zinc': 600}, {'sex': 'm', 'age': 25, 'zinc': 600}, {'sex': 'm', 'age': '30', 'zinc': 600}, {'sex': 'm', 'age': '25', 'zinc': '600'}, {'sex': 'm', 'age': '25', 'zinc': 500},
                {'sex': 'f', 'age': '25', 'zinc': 600}, {'sex': 'f', 'age': '25', 'meno': 'maybe', 'zinc': 600}, {'sex': 'm', 'age': '25'}, {'sex': '__proto__', 'age': '25', 'zinc': 600}, {'sex': ['m'], 'age': '25', 'zinc': 600}]
        check('cleanRef: a damaged profile is no profile (15 bad shapes: wrong type, unknown sex, age as a number, other age, zinc as text or another level, woman without menopause, missing zinc)', all([await cr(b) is None for b in badr]), [b for b in badr if await cr(b) is not None])
        check('cleanRef: the age is never stored as a date or a number (only "18" or "25")', await T("() => window.__tapnaplo.cleanRef({ sex: 'm', age: '1990-01-01', zinc: 600 })") is None)

        # =========================================================== 3 the card and the profile
        await seed([own('u:a', 'Food A', {'kcal': 250, 'calcium': 237.5, 'iron': 4})], [('u:a', 200)], None)
        check('no profile: the Nutrients tab shows the "Reference intake" card with Male and Female, and no bars', await page.locator('#refcard .ref-card').count() == 1 and (await page.locator('#refcard [data-act=ref-quick]').all_inner_texts()) == ['Male', 'Female'] and await page.locator('.rline').count() == 0)
        check('no profile: no EPA + DHA row, and the card says what it is for', await page.locator('.nrow:has-text("EPA + DHA")').count() == 0 and 'EFSA' in await page.inner_text('#refcard'))
        check('no profile: the card is the first thing under the header, above the explanation banners', await T("() => { const c = document.querySelector('#refcard'), b = document.querySelector('.banner'); return !!(c.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING); }"))
        await page.tap('[data-act=ref-quick][data-sex=f]'); await page.wait_for_selector('.rline')
        await page.wait_for_timeout(300)
        check('Female: one tap sets 25 and over, before menopause, phytate 600', await ref() == {'sex': 'f', 'age': '25', 'meno': 'pre', 'zinc': 600}, await ref())
        check('...the card shows every choice and a Change button, the long-term sentence', 'Female · 25 years and over · before menopause · zinc: phytate 600 mg' in await page.inner_text('#refcard') and await page.locator('[data-act=ref-change]').count() == 1 and 'One day below them is not a deficiency' in await page.inner_text('#refcard'), await page.inner_text('#refcard'))
        check('...toast with Undo', 'Reference intake is on' in await page.inner_text('#toast span') and await page.locator('#toast button').count() == 1)
        await page.tap('#toast button')
        check('Undo takes the profile away again (and the bars)', await ref() is None and await page.locator('.rline').count() == 0 and await page.locator('[data-act=ref-quick]').count() == 2)
        await page.tap('[data-act=ref-quick][data-sex=m]'); await page.wait_for_selector('.rline')
        check('Male: {sex m, age 25, zinc 600}, no menopause key', await ref() == {'sex': 'm', 'age': '25', 'zinc': 600}, await ref())
        # the sheet
        await page.tap('[data-act=ref-change]'); await page.wait_for_selector('#rs-save'); await page.wait_for_timeout(350)
        pressed = lambda: T("() => [...document.querySelectorAll('.sheet [data-k]')].filter((b) => b.getAttribute('aria-pressed') === 'true').map((b) => b.dataset.k + '=' + b.dataset.v).join(' ')")
        check('settings sheet: shows the saved choices (Male, 25 and over, 600) and hides Menopause for a man', await pressed() == 'sex=m age=25 zinc=600' and await page.locator('#rs-meno-w').is_hidden(), await pressed())
        check('...four sex buttons, two ages, four phytate levels', await page.locator('[data-k=sex]').all_inner_texts() == ['Male', 'Female', 'Pregnant', 'Nursing'] and await page.locator('[data-k=age]').all_inner_texts() == ['18–24', '25 and over'] and await page.locator('[data-k=zinc]').all_inner_texts() == ['300', '600', '900', '1,200'])
        check('...it says that only these choices are kept, and where they go', 'not your age or birth date' in await page.inner_text('.sheet-b') and 'private GitHub repository' in await page.inner_text('.sheet-b'))
        await page.tap('[data-k=sex][data-v=f]')
        check('choosing Female shows Menopause (Not yet is chosen)', await page.locator('#rs-meno-w').is_visible() and 'meno=pre' in await pressed(), await pressed())
        await page.tap('[data-k=meno][data-v=post]'); await page.tap('[data-k=age][data-v="18"]'); await page.tap('[data-k=zinc][data-v="900"]')
        await page.tap('#rs-save'); await page.wait_for_timeout(400)
        check('Save stores the new profile', await ref() == {'sex': 'f', 'age': '18', 'meno': 'post', 'zinc': 900}, await ref())
        check('...the sheet closed, a toast says so, the card follows', await page.locator('#rs-save').count() == 0 and 'Reference intake settings saved' in await page.inner_text('#toast span') and 'Female · 18–24 years · past menopause · zinc: phytate 900 mg' in await page.inner_text('#refcard'))
        await page.tap('#toast button')
        check('Undo puts the old profile back (Male)', await ref() == {'sex': 'm', 'age': '25', 'zinc': 600}, await ref())
        await page.tap('[data-act=ref-change]'); await page.wait_for_selector('#rs-save'); await page.wait_for_timeout(350)
        await page.tap('[data-k=sex][data-v=p]'); await page.tap('#rs-save'); await page.wait_for_timeout(300)
        check('Pregnant: no menopause key is stored', await ref() == {'sex': 'p', 'age': '25', 'zinc': 600}, await ref())
        await page.tap('[data-act=ref-change]'); await page.wait_for_selector('#rs-save'); await page.wait_for_timeout(350)
        await page.tap('#rs-save'); await page.wait_for_timeout(300)
        check('Save with nothing changed says "Nothing changed" and stores nothing new', 'Nothing changed' in await page.inner_text('#toast span'))
        await page.tap('[data-act=ref-change]'); await page.wait_for_selector('#rs-cancel'); await page.wait_for_timeout(350)
        await page.tap('[data-k=sex][data-v=n]'); await page.tap('#rs-cancel'); await page.wait_for_timeout(300)
        check('Cancel leaves the profile as it was', (await ref())['sex'] == 'p')
        await page.tap('[data-act=ref-change]'); await page.wait_for_selector('#rs-remove'); await page.wait_for_timeout(350)
        check('Remove settings is a red button inside the sheet content', 'danger' in (await page.get_attribute('#rs-remove', 'class')))
        await page.tap('#rs-remove'); await page.wait_for_timeout(300)
        check('Remove settings: no profile, no bars, a toast with Undo', await ref() is None and await page.locator('.rline').count() == 0 and 'removed' in await page.inner_text('#toast span'))
        await page.tap('#toast button')
        check('Undo of Remove settings brings the pregnant profile back', (await ref())['sex'] == 'p' and await page.locator('.rline').count() > 0)
        await page.tap('[data-tab=log]'); await page.wait_for_selector('.hero')
        check('the Diary tab has no reference bar, no card', await page.locator('.rline, .ref-card').count() == 0)
        await page.tap('[data-tab=nutr]'); await page.wait_for_selector('#refcard')

        # =========================================================== 4 percent and marks
        F = [own('u:a', 'Food A', {'kcal': 250, 'calcium': 237.5, 'iron': 4, 'magnesium': 75, 'vitamin_c': 47.5, 'fibres': 6.25, 'zinc': 4.65, 'vitamin_b1_or_thiamin': 0.1, 'vitamin_b3_or_niacin': 3.2,
                                       'retinol': 100, 'beta_carotene': 600, 'vitamin_d': 7.5, 'sodium': 500, 'potassium': 1000, 'vitamin_b9_or_folate': 82.5, 'salt': 1.0,
                                       'fa_20_5_5c_8c_11c_14c_17c_n_3_epa': 0.05, 'fa_22_6_4c_7c_10c_13c_16c_19c_n_3_dha': 0.2})]
        FEM = {'sex': 'f', 'age': '25', 'meno': 'pre', 'zinc': 600}
        await seed(F, [('u:a', 200)], FEM)
        mj = 500 / 238.83
        r = await row('Calcium')
        check('female: calcium 475 mg = 50% of 950 mg · PRI (solid bar, half full)', r['txt'] == '50% of 950 mg · PRI' and 'pri' in r['cls'] and r['w'] == '50%', r)
        for label, want in (('Iron', '50% of 16 mg · PRI'), ('Magnesium', '50% of 300 mg · AI'), ('Vitamin C', '100% of 95 mg · PRI'), ('Fibre', '50% of 25 g · AI'), ('Zinc', '100% of 9.3 mg · PRI'),
                            ('Vitamin D', '100% of 15 µg · AI'), ('Sodium', '50% of 2,000 mg · SAI'), ('Potassium', '57% of 3,500 mg · AI'), ('Vitamin B9 (folate)', '50% of 330 µg DFE · PRI')):
            rr = await row(label)
            check(f'female: {label}: {want}', rr and rr['txt'] == want, rr and rr['txt'])
        b1 = await row('Vitamin B1 (thiamin)')
        want_b1 = f"{pct(0.2 / (0.1 * mj) * 100)}% of 0.21 mg · PRI"
        check('B1 follows the energy of the day: 500 kcal = 2.09 MJ, so 0.21 mg; 0.2 mg is 96%', b1['txt'] == want_b1 == '96% of 0.21 mg · PRI', (b1['txt'], want_b1))
        check('...the opened row shows the calculation', any('Energy of this day: 2.09 MJ (500 kcal)' in d and 'the reference is 0.21 mg' in d for d in b1['detail']) and any('0.1 mg per MJ of energy (PRI, woman)' in d for d in b1['detail']), b1['detail'])
        b3 = await row('Vitamin B3 (niacin)')
        want_b3 = f"≥ {pct(6.4 / (1.6 * mj) * 100)}% of 3.35 mg NE · PRI"
        check('niacin is always a lower value: "≥" even when every item has data; mg NE per MJ', b3['txt'] == want_b3, (b3['txt'], want_b3))
        check('...and says why (tryptophan)', any('tryptophan' in d for d in b3['detail']) and 'at least' in b3['sr'], b3['detail'])
        va = await row('Vitamin A (retinol)')
        check('vitamin A: retinol 200 + beta-carotene 1200 ÷ 6 = 400 µg RE = 62% of 650 µg RE · PRI, no "≥" because both parts have data', va['txt'] == '62% of 650 µg RE · PRI · with beta-carotene' and va['val'].startswith('200'), (va['txt'], va['val']))
        check('...the opened row explains the retinol equivalents and that other carotenoids are missing', any('retinol plus beta-carotene ÷ 6' in d and 'lower value' in d for d in va['detail']), va['detail'])
        bc = await row('Beta-carotene')
        check('the beta-carotene row has no bar, but says it is counted in Vitamin A', not bc['hasLine'] and any('Counted in Vitamin A' in d for d in bc['detail']), bc)
        ed = await row('EPA + DHA')
        check('EPA + DHA: (0.05 + 0.2) g × 2 = 500 mg = 200% of 250 mg · AI, as a row right under DHA in Fatty acids', ed['txt'] == '200% of 250 mg · AI' and 'ai' in ed['cls'] and ed['w'] == '100%' and ed['val'].startswith('500') and await T("() => { const r = [...document.querySelectorAll('.nrow')]; const i = r.findIndex((x) => x.querySelector('summary > span').textContent.startsWith('DHA')); return r[i + 1].querySelector('summary > span').textContent; }") == 'EPA + DHA', ed)
        check('Salt has no reference (EFSA gives none)', not (await row('Salt'))['hasLine'])
        nobar = [(l, (await row(l))['hasLine']) for l in ('Energy', 'Protein', 'Sugars', 'Cholesterol')]
        check('rows without an EFSA value have no bar (Energy, Protein, Cholesterol, Sugars)', not any(h for _, h in nobar), nobar)
        n_lines = len(await lines())
        check('26 rows have a line for this day when the data is there (24 micronutrients + Fibre + EPA + DHA, minus vitamin K1 and the ones the food lacks show "no data")', n_lines == 26, n_lines)
        k1 = await row('Vitamin K1')
        check('a nutrient with no data in the day: no bar, no 0%, "no data to compare" with the reference', k1['txt'] == 'Reference 70 µg · AI · no data to compare' and k1['cls'] is None and '0%' not in k1['txt'], k1)
        sod = await row('Sodium')
        check('sodium: dotted bar (SAI), opened row says it is no goal and about 5 g of salt', 'sai' in sod['cls'] and any('not a goal to reach' in d for d in sod['detail']) and any('about 5 g of salt' in d for d in sod['detail']), sod['detail'])
        mg = await row('Magnesium')
        check('an AI row: dashed bar, opened row says what the AI rests on and that staying below is no deficiency', 'ai' in mg['cls'] and any(d.startswith('AI · based on the average intake observed in EU countries') for d in mg['detail']) and any('Staying below this is not a deficiency' in d for d in mg['detail']), mg['detail'])
        ca = await row('Calcium')
        check('a PRI row has no "based on" line and no "not a deficiency" sentence of its own', not any(d.startswith('AI ·') or 'Staying below' in d for d in ca['detail']) and any('Reference intake: 950 mg a day (PRI, woman, 25 years and over)' in d for d in ca['detail']), ca['detail'])
        check('screen reader text: full words, no symbols', ca['sr'] == 'Calcium: 50 percent of the reference intake of 950 milligrams (population reference intake).', ca['sr'])
        check('...the visible line is hidden from the screen reader (aria-hidden), the bar too', await T("() => { const l = document.querySelector('.nrow .rline'); return l.querySelector('.rtxt').getAttribute('aria-hidden') === 'true' && l.querySelector('.rtrack').getAttribute('aria-hidden') === 'true'; }"))
        weak = await T("""() => [...document.querySelectorAll('.nrow')].filter((r) => r.textContent.includes('Staying below this is not a deficiency')).map((r) => r.querySelector('summary > span').textContent)""")
        check('"Staying below this is not a deficiency" is on exactly the five weakest AI rows (magnesium, copper, manganese, vitamin E, B5)', sorted(weak) == sorted(['Magnesium', 'Copper', 'Manganese', 'Vitamin E', 'Vitamin B5 (pantothenic acid)']), weak)

        # partial, estimate, range, none, big, tiny
        await seed(F + [own('u:b', 'Food B', {'kcal': 100, 'retinol': 50})], [('u:a', 200), ('u:b', 100)], FEM)
        ca = await row('Calcium')
        check('an item without data: "≥ 50% of 950 mg · PRI" (the lower value, not 0 for the missing item)', ca['txt'] == '≥ 50% of 950 mg · PRI' and ca['pill'] == '1/2', ca)
        va = await row('Vitamin A (retinol)')
        check('vitamin A with an item that has retinol but no beta-carotene: "≥ 69%" ((400 + 50) / 650)', va['txt'] == f"≥ {pct(450 / 650 * 100)}% of 650 µg RE · PRI · with beta-carotene" and 'incomplete' not in va['txt'], va['txt'])
        check('...and it names the item that lacks a part', any('Missing retinol or beta-carotene for the reference: Food B' in d for d in va['detail']), va['detail'])
        mj2 = 600 / 238.83
        b1 = await row('Vitamin B1 (thiamin)')
        check('B1 with an item that has energy but no thiamin: still the energy of both items (600 kcal) and "≥"', b1['txt'] == f"≥ {pct(0.2 / (0.1 * mj2) * 100)}% of 0.25 mg · PRI", b1['txt'])
        ed = await row('EPA + DHA')
        check('EPA + DHA: one item has both, one has none: "≥" (nothing is invented for the second)', ed['txt'] == '≥ 200% of 250 mg · AI' and ed['pill'] == '1/2', ed)
        await seed(F + [own('u:c', 'Food C no energy', {'calcium': 95, 'vitamin_b1_or_thiamin': 0.1})], [('u:a', 200), ('u:c', 100)], FEM)
        b1 = await row('Vitamin B1 (thiamin)')
        check('B1 with an item that has no energy data: no percent, no bar: "needs complete energy data"', b1['txt'] == 'Reference 0.1 mg per MJ · PRI · needs complete energy data' and b1['cls'] is None and '%' not in b1['txt'], b1)
        check('...the opened row says why', any('only when every item of the day has energy data' in d for d in b1['detail']), b1['detail'])
        ca = await row('Calcium')
        check('...the other rows are not affected by the missing energy (calcium has data from both: 570 mg = 60%)', ca['txt'] == '60% of 950 mg · PRI', ca['txt'])
        await seed([own('u:e', 'Food E', {'kcal': 100, 'calcium': 95}, est=['calcium'], q='l')], [('u:e', 100)], FEM)
        ca = await row('Calcium')
        check('an estimated value: "~10% of 950 mg · PRI"', ca['txt'] == '~10% of 950 mg · PRI', ca['txt'])
        await seed([own('u:r', 'Food R', {'kcal': 100, 'calcium': '<190'})], [('u:r', 100)], FEM)
        ca = await row('Calcium')
        check('a "<x" value: a range from 0 to 20% (lowest and highest possible), the bar follows the lower end', ca['txt'] == '0–20% of 950 mg · PRI' and ca['w'] == '0%', ca)
        await seed([own('u:z', 'Food Z', {'kcal': 100, 'calcium': 1425, 'vitamin_c': 4, 'vitamin_d': 1500})], [('u:z', 100)], FEM)
        ca = await row('Calcium'); vd = await row('Vitamin D')
        check('150% of a PRI: the number goes on, the bar stops at 100%, no warning colour or sentence', ca['txt'] == '150% of 950 mg · PRI' and ca['w'] == '100%' and not any('high' in d.lower() or 'too much' in d.lower() or 'upper' in d.lower() for d in ca['detail']), ca)
        check('...an AI at 10,000% shows the number with a thousands separator and a full bar', vd['txt'] == '10,000% of 15 µg · AI' and vd['w'] == '100%', vd['txt'])
        vc = await row('Vitamin C')
        check('a tiny amount is "<1%", not "0%" (4 mg of 95 mg is 4%; 0.4 mg would be <1%)', vc['txt'] == '4% of 95 mg · PRI', vc['txt'])
        await seed([own('u:t', 'Food T', {'kcal': 100, 'calcium': 4})], [('u:t', 100)], FEM)
        check('0.4% shows "<1%"', (await row('Calcium'))['txt'] == '<1% of 950 mg · PRI')
        await seed([own('u:n', 'Food N', {'kcal': 100})], [('u:n', 100)], FEM)
        check('a day with energy only: every micronutrient row says "no data to compare", no bar at all', await page.locator('.rtrack').count() == 0 and (await row('Calcium'))['txt'] == 'Reference 950 mg · PRI · no data to compare')
        check('...no row shows 0% (missing is not zero)', not any(re.search(r'(^|[^\d])0%', t) for _, t in await lines()), await lines())
        await seed([own('u:z0', 'Food zero', {'kcal': 100, 'calcium': 0})], [('u:z0', 100)], FEM)
        check('a real zero (calcium 0 mg) is a real 0%, with a bar of no width', (await row('Calcium'))['txt'] == '0% of 950 mg · PRI' and (await row('Calcium'))['w'] == '0%')

        # profiles in the rows
        await seed(F, [('u:a', 200)], {'sex': 'm', 'age': '18', 'zinc': 900})
        check('male 18–24, phytate 900: calcium 1,000 mg, iron 11 mg, zinc 14 mg', (await row('Calcium'))['txt'].endswith('of 1,000 mg · PRI') and (await row('Iron'))['txt'].endswith('of 11 mg · PRI') and (await row('Zinc'))['txt'].endswith('of 14 mg · PRI'), [(await row(x))['txt'] for x in ('Calcium', 'Iron', 'Zinc')])
        await seed(F, [('u:a', 200)], {'sex': 'p', 'age': '25', 'zinc': 1200})
        fo = await row('Vitamin B9 (folate)')
        check('pregnant: folate is an AI of 600 µg DFE (dashed bar), zinc 14.3 mg, EPA + DHA 350 mg', fo['txt'] == '28% of 600 µg DFE · AI' and 'ai' in fo['cls'] and (await row('Zinc'))['txt'].endswith('of 14.3 mg · PRI') and (await row('EPA + DHA'))['txt'] == '143% of 350 mg · AI', (fo['txt'], (await row('EPA + DHA'))['txt']))
        check('...the EPA + DHA row explains the 350 mg', any('extra 100–200 mg DHA' in d and '350 mg' in d for d in (await row('EPA + DHA'))['detail']))
        await seed(F, [('u:a', 200)], {'sex': 'n', 'age': '25', 'zinc': 600})
        check('nursing: potassium 4,000 mg, vitamin A 1,300 µg RE, vitamin C 155 mg, selenium 85 µg', (await row('Potassium'))['txt'].endswith('of 4,000 mg · AI') and (await row('Vitamin A (retinol)'))['txt'].startswith('31% of 1,300 µg RE') and (await row('Vitamin C'))['txt'].endswith('of 155 mg · PRI'))
        await seed(F, [('u:a', 200)], {'sex': 'f', 'age': '25', 'meno': 'post', 'zinc': 600})
        ir = await row('Iron')
        check('female past menopause: iron 11 mg (PRI) and no "95%" sentence', ir['txt'] == '73% of 11 mg · PRI' and not any('95%' in d for d in ir['detail']), ir)
        await seed(F, [('u:a', 200)], FEM)
        check('female before menopause: iron 16 mg, the opened row says 16 mg covers about 95% of women, not 97.5%', any('about 95% of women, not 97.5%' in d for d in (await row('Iron'))['detail']))
        check('zinc says what it depends on', any('phytate 600 mg a day' in d for d in (await row('Zinc'))['detail']))
        check('vitamin E and D: the EFSA footnotes are in the opened rows', any('alpha-tocopherol' in d for d in (await row('Vitamin E'))['detail']) and any('minimal skin synthesis' in d for d in (await row('Vitamin D'))['detail']) and any('phylloquinone' in d for d in (await row('Vitamin K1'))['detail']) and any('Folic acid counts 1.7 times' in d for d in (await row('Vitamin B9 (folate)'))['detail']) and any('depend on the method' in d for d in (await row('Fibre'))['detail']))

        # an empty day
        await seed([], [], FEM)
        check('an empty day: the card is there (so the profile can be set on any day) above "Nothing logged for this day"', await page.locator('#refcard .ref-card').count() == 1 and 'Nothing logged for this day' in await page.inner_text('#view') and await page.locator('.rline').count() == 0)
        await seed(F, [('u:a', 200)], None)

        # =========================================================== 5 saving, old saves, damaged saves
        await page.tap('[data-act=ref-quick][data-sex=f]'); await page.wait_for_timeout(600)
        await page.reload(); await page.wait_for_selector('#tabbar .tab[aria-current]')
        check('the profile survives a reload', await ref() == FEM, await ref())
        await T("() => { const t = window.__tapnaplo; delete t.S.meta.ref; t.save(); }")
        await page.wait_for_timeout(500); await page.reload(); await page.wait_for_selector('#tabbar .tab[aria-current]')
        check('a save from before version 26 (no "ref" key) starts fine with no profile', await ref() is None)
        for junk in ({'sex': 'x'}, 'female', 5, {'sex': 'f', 'age': '25', 'zinc': 600}, [1]):
            await T("(j) => { const t = window.__tapnaplo; t.S.meta.ref = j; t.save(); }", junk)
            await page.wait_for_timeout(500); await page.reload(); await page.wait_for_selector('#tabbar .tab[aria-current]')
            check(f'a damaged profile in storage ({json.dumps(junk)}) is no profile after start (nothing is repaired)', await ref() is None, await ref())
        await page.tap('[data-tab=nutr]'); await page.wait_for_selector('#refcard')
        check('...and the card offers Male / Female again', await page.locator('[data-act=ref-quick]').count() == 2)

        # =========================================================== 6 backup and restore
        await seed(F, [('u:a', 200)], FEM, tab='data')
        await page.wait_for_timeout(500)
        await page.wait_for_selector('[data-act=export-json]')
        async with page.expect_download() as dd:
            await page.click('[data-act=export-json]')
        dl = await dd.value
        backup = json.loads(pathlib.Path(await dl.path()).read_text(encoding='utf-8'))
        check('the backup JSON has the profile in meta.ref (and nothing else new)', backup['meta'].get('ref') == FEM, backup['meta'].get('ref'))
        await T("() => { const t = window.__tapnaplo; t.S.meta.ref = { sex: 'm', age: '18', zinc: 300 }; t.save(); }")

        async def restore(obj, ok=True):
            await page.set_input_files('#importfile', {'name': 'backup.json', 'mimeType': 'application/json', 'buffer': json.dumps(obj).encode()})
            await page.wait_for_selector('[data-ok]')
            text = await page.inner_text('.sheet-b')
            if ok: await page.click('[data-ok]')
            await page.wait_for_timeout(500)
            return text
        await restore(backup)
        check('Restore from file brings the profile of the file back', await ref() == FEM, await ref())
        old = json.loads(json.dumps(backup)); old['meta'].pop('ref')
        text = await restore(old)
        check('a backup made before version 26 (no "ref") leaves your profile as it is, and the confirm text says so', await ref() == FEM and 'reference intake settings are not in this file, so they stay as they are' in text, (await ref(), text[-160:]))
        none = json.loads(json.dumps(backup)); none['meta']['ref'] = None
        await restore(none)
        check('a backup with "ref": null clears the profile (the file wins)', await ref() is None, await ref())
        await T("() => { const t = window.__tapnaplo; t.S.meta.ref = { sex: 'm', age: '18', zinc: 300 }; t.save(); }")
        for junk in ({'sex': 'x'}, 'lots', {'sex': 'f', 'age': '25', 'zinc': 600}):
            bad = json.loads(json.dumps(backup)); bad['meta']['ref'] = junk
            text = await restore(bad)
            check(f'a damaged profile in a backup ({json.dumps(junk)}) is skipped, yours stays, and the confirm text says so', await ref() == {'sex': 'm', 'age': '18', 'zinc': 300} and 'reference intake settings in the file are not valid' in text, (await ref(), text[-200:]))
        await restore(backup)
        check('Restore keeps the rest (the entry is back)', await T("() => window.__tapnaplo.S.log.length") == 1)

        # =========================================================== 7 other files unchanged
        async def csv_of(act):
            async with page.expect_download() as d:
                await page.click(f'[data-act={act}]')
            dl = await d.value
            path = HERE / 'ref_tmp.csv'
            await dl.save_as(str(path))
            text = path.read_text(encoding='utf-8-sig'); path.unlink()
            return list(csv.reader(io.StringIO(text)))
        await page.tap('[data-tab=data]'); await page.wait_for_selector('[data-act=export-days]')
        days = await csv_of('export-days'); ents = await csv_of('export-entries')
        check('the CSV files are unchanged by the profile (no reference columns)', not any('ref' in h.lower() or 'pri' == h.lower() for h in days[0] + ents[0]) and days[0][:4] == ['date', 'entries', 'est_share', 'water_intake_ml'], days[0][:5])
        check('the Data tab names EFSA under Sources & licences, and shows version 26', 'EFSA' in await page.inner_text('#view') and 'Reference intakes (Nutrients tab)' in await page.inner_text('#view') and 'version 26' in (await page.inner_text('#view')).replace('Nutrilog version', 'version'), '')
        check('sw.js cache name is v26', "'nutrilog-v26'" in (ROOT / 'sw.js').read_text())

        # =========================================================== 8 Sync with a fake GitHub
        gh = FakeGitHub()

        async def device(name):
            c = await new_ctx(); await c.route('https://api.github.com/**', gh.handle)
            pg = await c.new_page(); watch(pg, name)
            await pg.goto(URL); await pg.wait_for_selector('.hero')
            return c, pg

        async def sync(pg):
            for _ in range(3):
                await pg.wait_for_function('!window.__tapnaplo.SY.busy')
                await pg.evaluate("window.__tapnaplo.syncRun('manual')")
            await pg.wait_for_function('!window.__tapnaplo.SY.busy')

        async def connect(pg):
            await pg.click('[data-tab=data]'); await pg.wait_for_selector('[data-act=sync-setup]')
            await pg.click('[data-act=sync-setup]'); await pg.fill('#sy-repo', 'me/nutrilog-data'); await pg.fill('#sy-token', GOOD); await pg.click('[data-ok]')
            await sync(pg)
        setref = lambda pg, v: pg.evaluate("(v) => { const t = window.__tapnaplo; t.S.meta.ref = v; t.save(); }", v)
        ctxA, A = await device('SA')
        await setref(A, FEM)
        await connect(A)
        recs = gh.recs()
        check('sync: the profile goes to its own file ref/profile.json as one record "r:profile"', 'ref/profile.json' in gh.files and recs.get('r:profile', {}).get('x') == FEM and list(json.loads(gh.files['ref/profile.json'])['recs']) == ['r:profile'], list(gh.files))
        check('sync: meta.json does not carry it (an older app that rewrites meta.json cannot lose it)', 'r:profile' not in json.loads(gh.files.get('meta.json', '{"recs":{}}'))['recs'])
        ctxB, B = await device('SB')
        await connect(B)
        check('sync: a second device without a profile receives it', await ref(B) == FEM, await ref(B))
        await setref(B, {'sex': 'p', 'age': '25', 'zinc': 600}); await B.wait_for_timeout(300)
        await sync(B); await sync(A)
        check('sync: a change on B reaches A', await ref(A) == {'sex': 'p', 'age': '25', 'zinc': 600}, await ref(A))
        await setref(A, None); await A.wait_for_timeout(300)
        await sync(A); await sync(B)
        check('sync: Remove settings on A removes it on B (a tombstone stays in the repository)', await ref(B) is None and gh.recs().get('r:profile', {}).get('x', 'missing') is None, (await ref(B), gh.recs().get('r:profile')))
        await setref(B, {'sex': 'm', 'age': '18', 'zinc': 300}); await B.wait_for_timeout(300); await sync(B); await sync(A)
        check('sync: a profile set again after the removal comes back to A', await ref(A) == {'sex': 'm', 'age': '18', 'zinc': 300}, await ref(A))
        await setref(A, {'sex': 'f', 'age': '25', 'meno': 'post', 'zinc': 900}); await A.wait_for_timeout(300); await sync(A)
        await setref(B, {'sex': 'n', 'age': '25', 'zinc': 600}); await B.wait_for_timeout(300); await sync(B); await sync(A)
        check('sync: set on both devices: the later change wins on both', await ref(A) == {'sex': 'n', 'age': '25', 'zinc': 600} and await ref(B) == {'sex': 'n', 'age': '25', 'zinc': 600}, (await ref(A), await ref(B)))
        gh.files['ref/profile.json'] = json.dumps({'app': 'tapnaplo-sync', 'v': 1, 'recs': {'r:profile': {'u': 99999999999999, 'x': {'sex': 'robot', 'age': '25', 'zinc': 600}}, 'r:other': {'u': 99999999999999, 'x': FEM}, 'r:__proto__': {'u': 99999999999999, 'x': FEM}}})
        await sync(A)
        check('sync: a damaged remote profile and other "r:" keys are refused, the local profile stays', await ref(A) == {'sex': 'n', 'age': '25', 'zinc': 600}, await ref(A))
        check('sync: the remote record is checked with the same rules (a profile is only taken when cleanRef accepts it)', await A.evaluate("() => [window.__tapnaplo.validRec('r:profile', { sex: 'm', age: '25', zinc: 600 }), window.__tapnaplo.validRec('r:profile', null), window.__tapnaplo.validRec('r:profile', { sex: 'q' }), window.__tapnaplo.validRec('r:x', { sex: 'm', age: '25', zinc: 600 }), window.__tapnaplo.validRec('r:profile', 'text')].join()") == 'true,true,false,false,false')
        await ctxA.close(); await ctxB.close()
        # connecting with a different profile on the second device: the repository wins (no clock decides for data that has no time of its own)
        gh2 = FakeGitHub()
        c1 = await new_ctx(); await c1.route('https://api.github.com/**', gh2.handle); a = await c1.new_page(); watch(a, 'S1'); await a.goto(URL); await a.wait_for_selector('.hero')
        c2 = await new_ctx(); await c2.route('https://api.github.com/**', gh2.handle); b = await c2.new_page(); watch(b, 'S2'); await b.goto(URL); await b.wait_for_selector('.hero')
        gh = gh2
        await setref(a, FEM); await connect(a)
        await setref(b, {'sex': 'm', 'age': '25', 'zinc': 600}); await connect(b)
        check('sync: a second device that already had its own profile takes the one in the repository when it connects', await ref(b) == FEM, await ref(b))
        await c1.close(); await c2.close()

        # =========================================================== 9 Share
        MAKE = [own('u:a', 'Food A', {'kcal': 250, 'calcium': 237.5, 'iron': 4, 'magnesium': 75, 'vitamin_c': 47.5, 'fibres': 6.25, 'vitamin_b1_or_thiamin': 0.1, 'retinol': 100, 'beta_carotene': 600, 'sodium': 500, 'salt': 1.2, 'vitamin_d': '<2'}),
                own('u:b', 'Food B', {'kcal': 100, 'calcium': 95}, est=['calcium'], q='m')]
        PRG = {'sex': 'p', 'age': '25', 'zinc': 1200}
        await seed(MAKE, [('u:a', 200), ('u:b', 100)], PRG, tab='nutr')
        snap = await T("([a, b]) => window.__tapnaplo.shareSnapshot(a, b, true)", [day(-6), day(0)])
        check('share: with the switch on, the link carries the profile; the format is still v1', json.loads(snap['json']).get('ref') == PRG and json.loads(snap['json'])['v'] == 1 and snap['withRef'])
        snap = await T("([a, b]) => window.__tapnaplo.shareSnapshot(a, b, false)", [day(-6), day(0)])
        check('share: with the switch off the link has no "ref" key at all (it looks exactly like a version 25 link)', 'ref' not in json.loads(snap['json']) and not snap['withRef'])
        await T("() => { const t = window.__tapnaplo; t.S.meta.ref = null; }")
        snap = await T("([a, b]) => window.__tapnaplo.shareSnapshot(a, b, true)", [day(-6), day(0)])
        check('share: no profile, switch "on": no "ref" key', 'ref' not in json.loads(snap['json']))
        await T("(p) => { const t = window.__tapnaplo; t.S.meta.ref = p; t.save(); t.render(); }", PRG)
        # the sender sheet
        await page.click('[data-tab=data]'); await page.wait_for_selector('[data-act=share]'); await page.click('[data-act=share]'); await page.wait_for_selector('#sh-info')
        await page.click('[data-days="7"]'); await page.wait_for_function("document.querySelector('#sh-info').textContent.includes('link length')")
        check('share sheet: with a profile there is a checked switch "Include reference intake settings", and it warns about pregnancy and that a link cannot be taken back', await page.is_checked('#sh-ref') and 'Include reference intake settings' in await page.inner_text('.sheet-b') and 'including whether you are pregnant or nursing' in await page.inner_text('.sheet-b') and 'cannot be taken back' in await page.inner_text('.sheet-b'))
        check('share sheet: the message says the link comes with the settings', 'with reference intake settings' in await page.inner_text('#sh-info'), await page.inner_text('#sh-info'))
        check('share sheet: the switch is a 44 px row with a 20 px box', (await T("() => { const r = document.querySelector('#sh-ref').closest('label').getBoundingClientRect(); return Math.round(r.height); }")) >= 44)
        len_on = int(re.search(r'link length ([\d,]+)', await page.inner_text('#sh-info')).group(1).replace(',', ''))
        await page.uncheck('#sh-ref'); await page.wait_for_function("!document.querySelector('#sh-info').textContent.includes('with reference intake settings') && document.querySelector('#sh-info').textContent.includes('link length')")
        len_off = int(re.search(r'link length ([\d,]+)', await page.inner_text('#sh-info')).group(1).replace(',', ''))
        check('share sheet: switching it off makes the link shorter and drops the note', len_off < len_on, (len_on, len_off))
        await page.check('#sh-ref'); await page.wait_for_function("document.querySelector('#sh-info').textContent.includes('with reference intake settings')")
        await page.click('.sheet [data-x]')
        await T("() => { const t = window.__tapnaplo; t.S.meta.ref = null; t.render(); }")
        await page.click('[data-act=share]'); await page.wait_for_selector('#sh-info')
        check('share sheet: without a profile there is no switch', await page.locator('#sh-ref').count() == 0)
        await page.click('.sheet [data-x]')
        await T("(p) => { const t = window.__tapnaplo; t.S.meta.ref = p; t.render(); }", PRG)
        made = await T("([a, b]) => window.__tapnaplo.shareLink(a, b, true).then((r) => r.url)", [day(-6), day(0)])
        made_off = await T("([a, b]) => window.__tapnaplo.shareLink(a, b, false).then((r) => r.url)", [day(-6), day(0)])
        check('share: the link opens with Python (zlib) and has the profile', unpack(made).get('ref') == PRG and 'ref' not in unpack(made_off))
        await page.tap('[data-tab=nutr]'); await page.wait_for_selector('#refcard')
        sender_lines = await lines()
        sender_card = await page.inner_text('#refcard .ref-card')

        async def viewer(url, w=390):
            c = await new_ctx(w=w); await c.add_init_script(WATCH)
            pg = await c.new_page(); watch(pg, 'V')
            await pg.goto(url); await pg.wait_for_selector('.hero, .card', timeout=15000)
            return c, pg
        cV, V = await viewer(made)
        await V.tap('[data-tab=nutr]'); await V.wait_for_selector('#refcard .ref-card')
        vlines = await lines(V)
        check('viewer: the Nutrients tab shows the same bars and the same words as the sender, for every row', vlines == sender_lines and len(vlines) > 20, (len(vlines), [x for x in zip(vlines, sender_lines) if x[0] != x[1]][:3]))
        check('viewer: the card shows the profile and has no Change button, no Male/Female', 'Pregnant · 25 years and over · zinc: phytate 1,200 mg' in await V.inner_text('#refcard') and await V.locator('[data-act=ref-change], [data-act=ref-quick]').count() == 0, await V.inner_text('#refcard'))
        check('viewer: the shared-copy banner is first, then the card', await V.evaluate("() => { const n = document.querySelector('.view-note'), c = document.querySelector('#refcard'); return !!(n.compareDocumentPosition(c) & Node.DOCUMENT_POSITION_FOLLOWING); }"))
        await V.evaluate("() => { const b = document.createElement('button'); b.dataset.act = 'ref-quick'; b.dataset.sex = 'm'; b.id = 'fake'; document.body.append(b); const c = document.createElement('button'); c.dataset.act = 'ref-change'; c.id = 'fake2'; document.body.append(c); }")
        await V.evaluate("() => { document.getElementById('fake').click(); document.getElementById('fake2').click(); }"); await V.wait_for_timeout(300)
        check('viewer: even forged buttons change nothing and open nothing', await V.evaluate("() => JSON.stringify(window.__tapnaplo.S.meta.ref)") == json.dumps(PRG, separators=(',', ':')) and await V.locator('.sheet').count() == 0)
        w = await V.evaluate("() => window.__w")
        check('viewer: nothing was written (IndexedDB not opened, no localStorage write)', w == {'idbOpen': 0, 'idbWrite': 0, 'lsWrite': 0}, w)
        await cV.close()
        cV, V = await viewer(made_off)
        await V.tap('[data-tab=nutr]'); await V.wait_for_selector('.nrow')
        check('viewer: a link without the profile shows no card and no bars (nothing about the settings)', await V.locator('#refcard .ref-card, .rline, .rtrack').count() == 0 and await V.locator('.nrow').count() > 20)
        await cV.close()
        # hostile ref in a link
        CID = 'c:' + str(json.loads((ROOT / 'ciqual.json').read_text())['foods'][0]['c'])
        def mk(r):
            d = {'app': 'tapnaplo-share', 'v': 1, 'made': 1761500000000, 'from': day(-6), 'to': day(0), 'refs': [CID], 'foods': [], 'nova': {}, 'days': {day(0): [['m1', 0, '08:00', 100]]}}
            if not (isinstance(r, str) and r == 'none'): d['ref'] = r
            return d
        for label, r in (('an unknown sex', {'sex': 'robot', 'age': '25', 'zinc': 600}), ('a text', 'female'), ('a list', ['f']), ('a number', 7), ('null', None), ('zinc as text', {'sex': 'm', 'age': '25', 'zinc': '600'}),
                         ('__proto__', {'__proto__': {'sex': 'm'}, 'sex': 'm', 'age': '25', 'zinc': 600, 'constructor': 1}), ('a woman without menopause', {'sex': 'f', 'age': '25', 'zinc': 600})):
            raw = json.dumps(mk(r))
            c1 = await new_ctx(); pg = await c1.new_page(); watch(pg, 'H')
            await pg.goto(URL + '#share=j.' + b64u(raw.encode())); await pg.wait_for_selector('.hero, .card', timeout=15000)
            await pg.tap('[data-tab=nutr]'); await pg.wait_for_selector('.nrow, .card')
            got = await pg.evaluate("() => ({ ref: JSON.parse(JSON.stringify(window.__tapnaplo.S.meta.ref)), bars: document.querySelectorAll('.rline').length, ok: !document.querySelector('#view').textContent.includes('cannot be opened'), clean: ({}).sex === undefined && ({}).constructor === Object })")
            ok = got['ok'] and got['clean'] and (got['ref'] is None and got['bars'] == 0 if label not in ('__proto__',) else got['ref'] == {'sex': 'm', 'age': '25', 'zinc': 600} and got['bars'] > 0)
            check(f'viewer (hostile): "ref" as {label}: the link still opens, a bad profile is left out (no bars), nothing is polluted', ok, got)
            await c1.close()

        # =========================================================== 10 look and touch
        await seed(F, [('u:a', 200)], FEM, tab='nutr')
        await page.evaluate("window.scrollTo(0, 0)")
        small = await T(SIZES, '#refcard button')
        check('card: Change is at least 44 px', small == [], small)
        await T("() => { const t = window.__tapnaplo; t.S.meta.ref = null; t.render(); }")
        small = await T(SIZES, '#refcard button')
        check('card without a profile: Male and Female are at least 44 px', small == [], small)
        await T("(p) => { const t = window.__tapnaplo; t.S.meta.ref = p; t.render(); }", FEM)
        small = await T("() => [...document.querySelectorAll('.nrow > summary')].map((s) => Math.round(s.getBoundingClientRect().height)).filter((h) => h < 48)")
        check('every nutrient row is still at least 48 px high (a tap target)', small == [], small)
        await page.tap('[data-act=ref-change]'); await page.wait_for_selector('#rs-save'); await page.wait_for_timeout(350)
        small = await T(SIZES, '.sheet button')
        check('sheet: every button is at least 44 px', small == [], small)
        check('sheet: no field below 16 px (it has no text fields), buttons in a sticky .sheet-actions row', await T(SMALL_FONTS, '.sheet') == [] and await page.locator('.sheet-b > .sheet-actions').count() == 1 and await page.locator('.has-actions').count() == 1)
        check('sheet: the groups have labels for a screen reader (role=group, aria-labelledby)', await T("() => [...document.querySelectorAll('.sheet [role=group]')].every((g) => !!document.getElementById(g.getAttribute('aria-labelledby')))"))
        await T("() => document.documentElement.setAttribute('data-theme', 'dark')")
        check('contrast of the sheet in dark mode', await T(CONTRAST_JS, '.sheet') == [], await T(CONTRAST_JS, '.sheet'))
        if SHOTS: await page.screenshot(path=os.path.join(SHOTS, 'ref_sheet_dark.png'))
        await page.click('#rs-cancel')
        for theme in ('dark', 'light'):
            await T("(t) => document.documentElement.setAttribute('data-theme', t)", theme)
            check(f'contrast of the card, the rows and the bar text in {theme} mode', await T(CONTRAST_JS, '#refcard') == [] and await T(CONTRAST_JS, '.nlist') == [], (await T(CONTRAST_JS, '#refcard'), await T(CONTRAST_JS, '.nlist')))
            check(f'the bars (solid, dashed, dotted) are visible against the row in {theme} mode (3:1)', await T(BAR_CONTRAST) == [], await T(BAR_CONTRAST))
            if SHOTS:
                await page.evaluate("window.scrollTo(0, document.querySelector('.group').offsetTop - 40)")
                await page.screenshot(path=os.path.join(SHOTS, f'ref_rows_{theme}.png'))
        await page.evaluate("window.scrollTo(0, 0)")
        classes = await T("() => [...new Set([...document.querySelectorAll('.rtrack')].map((t) => t.className))].sort()")
        check('all three bar styles are on this page (pri, ai, sai) and nothing else', sorted(classes) == ['rtrack ai', 'rtrack pri', 'rtrack sai'], classes)
        check('no colour judges the percent: the fill is the same accent colour at 5% and at 500% (no red, no green)', await T("() => new Set([...document.querySelectorAll('.rtrack.pri .rfill')].map((f) => getComputedStyle(f).backgroundColor)).size") == 1)
        wide = await T("() => ({ page: document.documentElement.scrollWidth <= window.innerWidth, rows: [...document.querySelectorAll('.nrow .rline')].every((l) => { const r = l.getBoundingClientRect(); return r.left >= 0 && r.right <= window.innerWidth; }), tabs: document.querySelectorAll('#tabbar .tab').length })")
        check('390 px: no sideways scroll, every bar and line fits, five tabs', wide['page'] and wide['rows'] and wide['tabs'] == 5, wide)
        c320 = await new_ctx(w=320, h=640); p320 = await c320.new_page(); watch(p320, 'N')
        await p320.goto(URL); await p320.wait_for_selector('.hero')
        await seed(F + [own('u:c', 'Food C no energy', {'calcium': 95})], [('u:a', 200), ('u:c', 100)], {'sex': 'n', 'age': '18', 'zinc': 1200}, pg=p320)
        wide = await p320.evaluate("() => ({ page: document.documentElement.scrollWidth <= window.innerWidth, rows: [...document.querySelectorAll('.nrow .rline')].every((l) => { const r = l.getBoundingClientRect(); return r.left >= 0 && r.right <= window.innerWidth; }), card: (() => { const r = document.querySelector('#refcard .ref-card').getBoundingClientRect(); return r.left >= 0 && r.right <= window.innerWidth; })() })")
        check('320 px (small phone, longest texts: nursing, "needs complete energy data"): no sideways scroll, every line fits', wide['page'] and wide['rows'] and wide['card'], wide)
        await p320.tap('[data-act=ref-change]'); await p320.wait_for_selector('#rs-save'); await p320.wait_for_timeout(350)
        wide = await p320.evaluate("() => ({ page: document.documentElement.scrollWidth <= window.innerWidth, sheet: (() => { const s = document.querySelector('.sheet-b'); return s.scrollWidth <= s.clientWidth + 1; })(), buttons: [...document.querySelectorAll('.sheet button')].every((b) => { const r = b.getBoundingClientRect(); return r.left >= 0 && r.right <= window.innerWidth && b.scrollWidth <= b.clientWidth + 1; }) })")
        check('320 px: the settings sheet and its buttons fit (four phytate buttons, 2 x 2 sex buttons)', wide['page'] and wide['sheet'] and wide['buttons'], wide)
        if SHOTS: await p320.screenshot(path=os.path.join(SHOTS, 'ref_320_sheet.png'))
        await c320.close()
        check('no page errors, and nothing was requested outside this server (and the fake GitHub)', not errs and not outside, (errs[:3], outside[:3]))
        await browser.close()
        print('\n' + ('ALL PASSED' if not problems else f'{len(problems)} FAILED: ' + '; '.join(problems)))
        sys.exit(1 if problems else 0)


asyncio.run(main())
