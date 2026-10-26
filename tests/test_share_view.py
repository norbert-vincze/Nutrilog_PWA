"""Share diary and nutrients (version 23). Run with the web server on port 8765 (see CLAUDE.md).

The Data tab makes a link (#share=...) that holds the chosen days of the diary; opening it shows the Diary and Nutrients tabs of those days, read-only.
No password, no upload: the days are inside the link.
Covers: the sheet (periods, dates, messages, link length, the long-link note, Copy link and its fallback, Share link when the browser has it), the link itself (format that
Python can read, only the chosen days, notes and dates of foods left out, a link made without CompressionStream), the viewer (same numbers as the sender for every day: hero, meal
lines, entry lines, red salt, ~ and ≥, Nutrients rows, NOVA card; only two tabs; no buttons that change anything; day arrows stop at the ends), the guarantee that the viewer writes
nothing (IndexedDB is not even opened, no localStorage writes) and the diary of the person who opens the link stays as it was, only the food tables the link needs are loaded,
every kind of bad link (message, no crash, nothing written), a hostile link (escaped text, zip bomb, __proto__), a newer format, a browser that cannot unpack, a new link in the same tab,
touch targets, 16 px fields, contrast in light and dark, 390 px width, no outside request, no page errors, the version number."""
import asyncio, base64, json, os, pathlib, re, sys, time, zlib
from playwright.async_api import async_playwright
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_ai_import import CONTRAST_JS, SMALL_FONTS

URL = 'http://127.0.0.1:8765/index.html'
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
SHOTS = os.environ.get('SHOTS', '')


def b64u(b):
    return base64.urlsafe_b64encode(b).decode().rstrip('=')


def unb64u(s):
    return base64.urlsafe_b64decode(s + '=' * (-len(s) % 4))


def link(raw, prefix='z', text=None):
    """A link the way the app makes it, from a dict (or from the raw text of the JSON)."""
    data = (text if text is not None else json.dumps(raw, ensure_ascii=False)).encode('utf-8')
    return URL + '#share=' + prefix + '.' + b64u(zlib.compress(data) if prefix == 'z' else data)


CIQ_ID = 'c:' + str(json.loads((ROOT / 'ciqual.json').read_text())['foods'][0]['c'])


def valid(**over):
    d = {'app': 'tapnaplo-share', 'v': 1, 'made': 1761500000000, 'from': '2026-10-20', 'to': '2026-10-26', 'refs': [CIQ_ID], 'foods': [], 'nova': {},
         'days': {'2026-10-26': [['m1', 0, '08:00', 100]]}}
    d.update(over)
    return d


def own_food(**kw):
    f = {'id': 'u:abc', 'src': 'user', 'name': 'Own food', 'basis': {'qty': 100, 'unit': 'g'}, 'n': {'kcal': 100, 'protein': 5}}
    f.update(kw)
    return f


SEED = """() => {
  const T = window.__tapnaplo, S = T.S;
  S.log.length = 0; for (const k of Object.keys(S.foods)) delete S.foods[k]; S.meta.nova = {};
  const pad = (n) => String(n).padStart(2, '0');
  const dayAgo = (n) => { const d = new Date(); d.setDate(d.getDate() - n); return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); };
  const own = (id, name, n, kw) => Object.assign({ id, src: 'user', name, brand: '', barcode: '', basis: { qty: 100, unit: 'g' }, n, nova: null, portions: [{ label: 'x', grams: 5 }], note: 'SECRET-NOTE', created: 1000, updated: 1000 }, kw || {});
  const foods = [
    own('u:plain', 'Plain food', { kcal: 165, protein: 10, carbohydrate: 20, fat: 5, fibres: 2, salt: 1 }),
    own('u:est', 'Estimated food', { kcal: 120, protein: 10, carbohydrate: 5, fat: 4, fibres: 1, salt: 0.2, calcium: 150, vitamin_d: '<0.5' }, { est: ['protein', 'calcium'], q: 'l', fortified: true, nova: 3, brand: 'EstBrand' }),
    own('u:drink', 'Oat drink', { kcal: 40, protein: 1, carbohydrate: 7, fat: 1.5, salt: 0.1 }, { ml: true }),
    own('u:caps', 'Vitamin capsule', { vitamin_d: 10 }, { basis: { qty: 1, unit: 'capsule' } }),
    own('u:lt', 'Below limit food', { kcal: 20, salt: '<0.1', calcium: 't' }),
    { id: 'o:4070765076189', src: 'off', name: 'Saved yoghurt', brand: 'OffBrand', barcode: '4070765076189', basis: { qty: 100, unit: 'g' }, n: { kcal: 90, protein: 4, carbohydrate: 12, fat: 3, salt: 0.3 }, nova: 4, portions: [], note: '', created: 1, updated: 1 },
  ];
  for (const f of foods) S.foods[f.id] = f;
  const egg = T.searchCiqual('egg')[0], bread = T.searchCiqual('bread')[0], banana = T.searchUsda('banana', 3)[0], dm = T.DMBIO[0];
  S.meta.nova[egg.id] = 1; S.meta.nova[bread.id] = 3;
  let n = 0;
  const add = (day, m, f, a, tm, t) => S.log.push({ id: 'e' + (++n), d: dayAgo(day), m, f, a, t: t || 1000 + n, tm });
  add(0, 'm1', egg.id, 120, '07:30'); add(0, 'm1', 'u:plain', 50, '08:05'); add(0, 'm2', banana.id, 100, '10:15'); add(0, 'm2', dm.id, 80, '10:40');
  add(0, 'm2', 'u:drink', 250, '12:00'); add(0, 'm2', 'u:caps', 2, '12:05'); add(0, 'm3', 'u:est', 80, '18:30'); add(0, 'm3', 'c:999999999', 100, '19:00');
  const noTime = new Date(); noTime.setDate(noTime.getDate() - 1); noTime.setHours(9, 30, 0, 0);
  add(1, 'm1', bread.id, 60, undefined, noTime.getTime()); add(1, 'm1', 'o:4070765076189', 150, '08:00'); add(1, 'm1', 'u:lt', 40, '08:10');
  add(3, 'm1', egg.id, 60, '07:00'); add(3, 'm2', 'u:est', 100, '12:30');
  add(10, 'm1', egg.id, 100, '07:45');
  T.invalidate && T.invalidate(); T.save(); T.render();
  return { days: [0, 1, 2, 3].map(dayAgo), old: dayAgo(10), today: dayAgo(0), from7: dayAgo(6) };
}"""

# the numbers of one day in both tabs, the same way in the sender and in the viewer (the note and the buttons that only one of them has are left out)
DAYSNAP = """(days) => {
  const T = window.__tapnaplo, out = {};
  const q = (s, r = document) => [...r.querySelectorAll(s)];
  const txt = (e) => (e ? e.textContent.replace(/\\s+/g, ' ').trim() : null);
  for (const d of days) {
    T.S.day = d; T.S.tab = 'log'; T.render();
    const log = { hero: txt(q('.hero')[0]), tiles: txt(q('.mtiles')[0]), mini: txt(q('.mini')[0]),
      banners: q('#view .banner').filter((b) => !b.classList.contains('view-note')).map(txt),
      meals: q('.meal').map((m) => ({ h: txt(m.querySelector('.meal-h')), sum: txt(m.querySelector('.meal-sum .ms-row')),
        entries: q('.entry', m).map((e) => ({ name: txt(e.querySelector('.entry-name')), sub: txt(e.querySelector('.entry-sub')), kcal: txt(e.querySelector('.entry-kcal')), ms: txt(e.querySelector('.entry-ms .ms-row')), hot: q('.ms.hot', e).length })) })) };
    T.S.tab = 'nutr'; T.render();
    const nutr = { rows: q('.nrow').map(txt), nova: txt(q('.nova-card')[0]), cards: q('#view > .card .card-t').map(txt), banners: q('#view > .banner').filter((b) => !b.classList.contains('view-note')).map(txt) };
    out[d] = { log, nutr };
  }
  T.S.tab = 'log'; T.render();
  return out;
}"""

WATCH = """(() => {
  window.__w = { idbOpen: 0, idbWrite: 0, lsWrite: 0 };
  const o = indexedDB.open.bind(indexedDB); indexedDB.open = function () { window.__w.idbOpen++; return o.apply(this, arguments); };
  for (const m of ['put', 'add', 'delete', 'clear']) { const f = IDBObjectStore.prototype[m]; IDBObjectStore.prototype[m] = function () { window.__w.idbWrite++; return f.apply(this, arguments); }; }
  for (const m of ['setItem', 'removeItem', 'clear']) { const f = Storage.prototype[m]; Storage.prototype[m] = function () { window.__w.lsWrite++; return f.apply(this, arguments); }; }
})();"""

SIZES = "(sel) => [...document.querySelectorAll(sel)].filter((e) => !e.hidden && e.getClientRects().length).map((e) => { const r = e.getBoundingClientRect(); return [(e.id || e.dataset.act || e.className || e.tagName) + ':' + e.textContent.trim().slice(0, 14), Math.round(r.width), Math.round(r.height)]; }).filter((x) => x[2] < 44 || x[1] < 44)"


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
            pg.on('request', lambda r: outside.append(r.url) if not r.url.startswith('http://127.0.0.1') and not r.url.startswith('data:') and not r.url.startswith('blob:') else None)

        async def new_ctx(**kw):
            c = await browser.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True, locale='en-GB', service_workers='block', permissions=['clipboard-read', 'clipboard-write'], **kw)
            await c.route('**/*openfoodfacts.org/**', lambda r: r.fulfill(status=200, headers={'access-control-allow-origin': '*', 'content-type': 'application/json'}, body='{"products":[],"status":0}'))
            return c

        # =========================== the sender ===========================
        ctx = await new_ctx()
        page = await ctx.new_page(); watch(page, 'S')
        await page.goto(URL); await page.wait_for_selector('.hero')
        T = page.evaluate
        info = await T(SEED)
        days = info['days']
        before = await T("() => JSON.stringify([window.__tapnaplo.S.log, window.__tapnaplo.S.foods, window.__tapnaplo.S.meta])")

        await page.click('[data-act=tab][data-tab=data]')
        check('the Data tab has the card and the button "Share diary and nutrients"', await page.locator('.card .card-t', has_text='Share diary and nutrients').count() == 1 and await page.locator('button[data-act=share]').inner_text() == 'Share diary and nutrients')
        await page.click('[data-act=share]')
        await page.wait_for_function("document.querySelector('#sh-copy') && !document.querySelector('#sh-copy').disabled")
        info7 = await page.inner_text('#sh-info')
        check('the sheet opens with the last 7 days chosen', await page.input_value('#sh-from') == info['from7'] and await page.input_value('#sh-to') == info['today'] and await page.get_attribute('[data-days="7"]', 'aria-pressed') == 'true', (await page.input_value('#sh-from'), info['from7']))
        m = re.match(r'(\d+) days? with entries · (\d+) items? · link length ([\d,]+) characters · (\d+) item left out', info7)
        check('it says how many days, items and characters the link has, and that the entry with an unknown food is left out', bool(m) and m.group(1) == '3' and m.group(2) == '12' and m.group(4) == '1', info7)
        check('there is no Share link button in a browser without the share function, Copy link is the main button', await page.locator('#sh-send').count() == 0 and 'primary' in (await page.get_attribute('#sh-copy', 'class')))
        check('a short link has no warning', await page.locator('#sh-long').is_hidden())
        await page.click('#sh-copy')
        await page.wait_for_function("document.querySelector('#toast') && !document.querySelector('#toast').hidden")
        url = await T('navigator.clipboard.readText()')
        check('Copy link puts the link on the clipboard and says so', url.startswith(URL + '#share=z.') and 'Link copied' in await page.inner_text('#toast'))
        check('the length in the message is the length of the link', m and int(m.group(3).replace(',', '')) == len(url), (m.group(3) if m else None, len(url)))
        raw = json.loads(zlib.decompress(unb64u(url.split('#share=z.')[1])).decode('utf-8'))
        check('Python can read the link: zlib, JSON, the marker and version 1', raw['app'] == 'tapnaplo-share' and raw['v'] == 1 and raw['from'] == info['from7'] and raw['to'] == info['today'])
        flat = json.dumps(raw)
        check('only the chosen days are in it (the entry from 10 days ago is not)', info['old'] not in flat and sorted(raw['days'].keys()) == sorted([days[0], days[1], days[3]]), sorted(raw['days'].keys()))
        check('own foods are inside, notes, dates and portions of foods are not', {f['id'] for f in raw['foods']} == {'u:plain', 'u:est', 'u:drink', 'u:caps', 'u:lt', 'o:4070765076189'} and 'SECRET-NOTE' not in flat and 'created' not in flat and 'portions' not in flat, [f['id'] for f in raw['foods']])
        check('generic foods are only named by id, the NOVA group you set by hand comes along', all(not f['id'].startswith(('c:', 'usda:', 'dm:')) for f in raw['foods']) and len(raw['nova']) == 2 and set(raw['nova'].values()) == {1, 3}, raw['nova'])
        est = next(f for f in raw['foods'] if f['id'] == 'u:est')
        check('estimate marks, confidence, fortified and NOVA of an own food come along', est['est'] == ['protein', 'calcium'] and est['q'] == 'l' and est['fortified'] is True and est['nova'] == 3 and est['brand'] == 'EstBrand', est)
        check('the drink keeps its ml flag, the capsule its unit', next(f for f in raw['foods'] if f['id'] == 'u:drink')['ml'] is True and next(f for f in raw['foods'] if f['id'] == 'u:caps')['basis']['unit'] == 'capsule')
        check('an entry without a saved time gets the time it was added (09:30)', any(e[2] == '09:30' for e in raw['days'][days[1]]), raw['days'][days[1]])
        check('the sender\'s own diary was not changed by making the link', await T("() => JSON.stringify([window.__tapnaplo.S.log, window.__tapnaplo.S.foods, window.__tapnaplo.S.meta])") == before)
        if SHOTS: await page.screenshot(path=SHOTS + '/share_sheet.png')

        # --- periods and dates ---
        async def wait_ready():
            await page.wait_for_function("(() => { const b = document.querySelector('#sh-copy'); return b && !b.disabled; })()")

        async def info_now():
            await page.wait_for_function("document.querySelector('#sh-info').textContent !== 'Preparing the link…'")
            return await page.inner_text('#sh-info')
        await page.click('[data-days="14"]')
        await wait_ready()
        i14 = await info_now()
        check('14 days include the entry from 10 days ago', i14.startswith('4 days with entries · 13 items') and await page.get_attribute('[data-days="14"]', 'aria-pressed') == 'true' and await page.get_attribute('[data-days="7"]', 'aria-pressed') == 'false', i14)
        await page.click('[data-days="30"]')
        await wait_ready()
        check('30 days works the same way', (await info_now()).startswith('4 days with entries · 13 items'))
        await page.fill('#sh-from', days[1]); await page.fill('#sh-to', days[1])
        await wait_ready()
        i1 = await info_now()
        check('one chosen day: one day, its items, no preset is pressed', i1.startswith('1 day with entries · 3 items') and await page.locator('[data-days][aria-pressed=true]').count() == 0, i1)
        await page.fill('#sh-from', days[0]); await page.fill('#sh-to', days[1])
        await page.wait_for_selector('#sh-err:not([hidden])')
        check('the first day after the last day: the message sits under the dates and the buttons are off', 'must not be after' in await page.inner_text('#sh-err') and await page.is_disabled('#sh-copy'), await page.inner_text('#sh-err'))
        await page.fill('#sh-from', days[3]); await page.fill('#sh-to', days[0])
        await wait_ready()
        check('the message goes away when the dates are right', await page.locator('#sh-err').is_hidden())
        await page.fill('#sh-from', '2026-01-01')
        await page.wait_for_selector('#sh-err:not([hidden])')
        check('more than 62 days is refused with a reason', 'at most 62 days' in await page.inner_text('#sh-err') and await page.is_disabled('#sh-copy'), await page.inner_text('#sh-err'))
        await page.fill('#sh-from', '')
        await page.wait_for_function("!document.querySelector('#sh-err').hidden && document.querySelector('#sh-err').textContent.includes('Choose')")
        check('an empty date is refused with a reason', await page.is_disabled('#sh-copy'))
        await page.fill('#sh-from', '2020-01-01'); await page.fill('#sh-to', '2020-01-07')
        await page.wait_for_function("document.querySelector('#sh-info').textContent.includes('no diary entries')")
        i0 = await page.inner_text('#sh-info')
        check('days without entries: it says so and does not offer a link', 'no diary entries' in i0 and await page.is_disabled('#sh-copy'), i0)
        await page.click('[data-days="7"]'); await wait_ready()

        # --- clipboard refused: the link is in a box ---
        await T("() => { navigator.clipboard.writeText = () => Promise.reject(new Error('no')); }")
        await page.click('#sh-copy')
        await page.wait_for_selector('#sh-link')
        check('when copying is refused the link is in a read-only box, nothing else changes', (await page.input_value('#sh-link')).startswith(URL + '#share=z.') and await page.get_attribute('#sh-link', 'readonly') is not None)
        check('the sheet fits 390 px', await T('() => document.documentElement.scrollWidth <= window.innerWidth && (() => { const b = document.querySelector(".sheet-b"); return b.scrollWidth <= b.clientWidth; })()'))
        check('date fields are at least 16 px, buttons at least 44 px', await T(SMALL_FONTS, '.sheet') == [] and await T(SIZES, '.sheet button') == [], (await T(SMALL_FONTS, '.sheet'), await T(SIZES, '.sheet button')))
        light = await T(CONTRAST_JS, '.sheet')
        check('contrast of the sheet (light)', light == [], light)
        await T("() => document.documentElement.setAttribute('data-theme','dark')")
        dark = await T(CONTRAST_JS, '.sheet')
        check('contrast of the sheet (dark)', dark == [], dark)
        if SHOTS: await page.screenshot(path=SHOTS + '/share_sheet_dark.png')
        await T("() => document.documentElement.setAttribute('data-theme','light')")
        await page.click('.sheet [data-x]')
        light = await T(CONTRAST_JS, '#view')
        check('contrast of the Data tab with the new card (light)', light == [], light)
        await T("() => document.documentElement.setAttribute('data-theme','dark')")
        dark = await T(CONTRAST_JS, '#view')
        check('contrast of the Data tab with the new card (dark)', dark == [], dark)
        await T("() => document.documentElement.setAttribute('data-theme','light')")

        # --- the long-link note ---
        ctxL = await new_ctx()
        pl = await ctxL.new_page(); watch(pl, 'L')
        await pl.goto(URL); await pl.wait_for_selector('.hero')
        await pl.evaluate("""() => { const T = window.__tapnaplo, S = T.S; S.log.length = 0;
          const pad = (n) => String(n).padStart(2, '0'); let r = 7;
          const rnd = () => (r = (r * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
          const keys = T.KEYS;
          for (let i = 0; i < 90; i++) { const n = {}; keys.forEach((k) => { n[k] = Math.round(rnd() * 100000) / 1000; }); S.foods['u:l' + i] = { id: 'u:l' + i, src: 'user', name: 'Long food number ' + i, brand: '', barcode: '', basis: { qty: 100, unit: 'g' }, n, nova: null, portions: [], note: '', created: 1, updated: 1 }; }
          for (let d = 0; d < 30; d++) { const dt = new Date(); dt.setDate(dt.getDate() - d); const day = dt.getFullYear() + '-' + pad(dt.getMonth() + 1) + '-' + pad(dt.getDate());
            for (let i = 0; i < 12; i++) S.log.push({ id: 'l' + d + '_' + i, d: day, m: 'm' + (1 + (i % 6)), f: 'u:l' + Math.floor(rnd() * 90), a: Math.round(10 + rnd() * 300), t: i, tm: pad(7 + i) + ':' + pad(Math.floor(rnd() * 60)) }); }
          T.render(); }""")
        await pl.click('[data-act=tab][data-tab=data]'); await pl.click('[data-act=share]')
        await pl.wait_for_function("document.querySelector('#sh-copy') && !document.querySelector('#sh-copy').disabled")
        await pl.click('[data-days="30"]')
        await pl.wait_for_function("document.querySelector('#sh-info').textContent.includes('30 days')")
        await pl.wait_for_function("!document.querySelector('#sh-copy').disabled")
        long_info = await pl.inner_text('#sh-info')
        longlen = int(re.search(r'link length ([\d,]+)', long_info).group(1).replace(',', ''))
        check('a long link (30 days, many different own foods) is allowed but gets a note about chat apps', longlen > 4000 and await pl.locator('#sh-long').is_visible() and 'Telegram' in await pl.inner_text('#sh-long') and 'email' in await pl.inner_text('#sh-long'), long_info)
        print('   (a long link of 30 days x 12 items with 90 different own foods of 64 values each:', longlen, 'characters)')
        await pl.click('.sheet [data-x]')
        await pl.evaluate("() => { window.__tapnaplo.S.log.splice(3); }")   # three entries of today are left
        await pl.click('[data-act=share]')
        await pl.wait_for_function("document.querySelector('#sh-info').textContent.startsWith('1 day with') && !document.querySelector('#sh-copy').disabled")
        short_info = await pl.inner_text('#sh-info')
        check('a short link (3 items) has no note', await pl.locator('#sh-long').is_hidden() and int(re.search(r'link length ([\d,]+)', short_info).group(1).replace(',', '')) < 4000, short_info)
        await ctxL.close()

        # --- a browser that has the share function ---
        ctxS = await new_ctx()
        await ctxS.add_init_script("window.__shared = []; navigator.share = (d) => { window.__shared.push(d); return window.__shareResult ? window.__shareResult() : Promise.resolve(); };")
        ps = await ctxS.new_page(); watch(ps, 'H')
        await ps.goto(URL); await ps.wait_for_selector('.hero')
        await ps.evaluate(SEED)
        await ps.click('[data-act=tab][data-tab=data]'); await ps.click('[data-act=share]')
        check('Share link shows up and is the main button, Copy link is the second one', await ps.locator('#sh-send').count() == 1 and 'primary' in (await ps.get_attribute('#sh-send', 'class')) and 'primary' not in (await ps.get_attribute('#sh-copy', 'class')))
        await ps.wait_for_function("!document.querySelector('#sh-send').disabled")
        await ps.click('#sh-send')
        shared = await ps.evaluate('window.__shared')
        check('Share link hands the link and a title to the phone\'s share sheet, inside the tap', len(shared) == 1 and shared[0]['url'].startswith(URL + '#share=z.') and shared[0]['title'] == 'Nutrilog diary', shared)
        await ps.evaluate("() => { window.__shareResult = () => Promise.reject(Object.assign(new Error('x'), { name: 'AbortError' })); }")
        await ps.click('#sh-send'); await ps.wait_for_timeout(300)
        check('cancelling the share sheet says nothing', await ps.evaluate("() => document.querySelector('#toast').hidden || !document.querySelector('#toast').textContent.includes('did not work')"))
        await ps.evaluate("() => { window.__shareResult = () => Promise.reject(Object.assign(new Error('x'), { name: 'NotAllowedError' })); }")
        await ps.click('#sh-send')
        await ps.wait_for_function("document.querySelector('#toast') && !document.querySelector('#toast').hidden && document.querySelector('#toast').textContent.includes('did not work')")
        check('a share that fails points to Copy link', 'Copy link' in await ps.inner_text('#toast'))
        await ctxS.close()

        # --- a browser that cannot compress: the link is longer and still works ---
        ctxP = await new_ctx()
        await ctxP.add_init_script("delete window.CompressionStream;")
        pp = await ctxP.new_page(); watch(pp, 'P')
        await pp.goto(URL); await pp.wait_for_selector('.hero')
        await pp.evaluate(SEED)
        await pp.click('[data-act=tab][data-tab=data]'); await pp.click('[data-act=share]')
        await pp.wait_for_function("!document.querySelector('#sh-copy').disabled")
        await pp.click('#sh-copy'); await pp.wait_for_selector('#toast:not([hidden])')
        plain_url = await pp.evaluate('navigator.clipboard.readText()')
        check('without CompressionStream the link starts with j. and holds the same JSON', plain_url.startswith(URL + '#share=j.') and json.loads(unb64u(plain_url.split('#share=j.')[1]))['days'].keys() == raw['days'].keys())
        await ctxP.close()

        # =========================== the viewer ===========================
        snap_sender = await T(DAYSNAP, days)
        ctxB = await new_ctx()
        await ctxB.add_init_script(WATCH)
        own_page = await ctxB.new_page(); watch(own_page, 'O')
        await own_page.goto(URL); await own_page.wait_for_selector('.hero')
        await own_page.evaluate("""() => { const T = window.__tapnaplo, S = T.S;
          S.foods['u:hers'] = { id: 'u:hers', src: 'user', name: 'Her own food', brand: '', barcode: '', basis: { qty: 100, unit: 'g' }, n: { kcal: 77 }, nova: null, portions: [], note: '', created: 1, updated: 1 };
          S.log.push({ id: 'her1', d: S.day, m: 'm1', f: 'u:hers', a: 100, t: 5, tm: '06:00' }); T.save(); try { localStorage.setItem('nutrilog.tab', 'foods'); } catch (e) {} }""")
        await own_page.wait_for_timeout(700)
        hers_before = await own_page.evaluate("() => JSON.stringify([window.__tapnaplo.S.log, window.__tapnaplo.S.foods, window.__tapnaplo.S.meta, localStorage.getItem('nutrilog.tab')], (k, v) => (k[0] === '_' ? undefined : v))")
        await own_page.close()

        reqs = []
        vp = await ctxB.new_page(); watch(vp, 'V')
        vp.on('request', lambda r: reqs.append(r.url.split('/')[-1].split('#')[0]))
        await vp.goto(url); await vp.wait_for_selector('.hero')
        V = vp.evaluate
        check('the link opens the Diary, on the last day that has entries', await V("() => window.__tapnaplo.S.day") == days[0] and await V("() => !!window.__tapnaplo.VIEW") and 'Shared diary · read-only' in await vp.inner_text('.view-note'))
        check('only two tabs: Diary and Nutrients', await V("() => [...document.querySelectorAll('#tabbar .tab')].map((t) => t.textContent.trim())") == ['Diary', 'Nutrients'])
        check('no Log food, Scan, Create food, no + on a meal, no Today button', await V("() => document.querySelectorAll('.actions, [data-act=add], [data-act=scan], [data-act=new-food], [data-act=today], [data-act=edit-entry]').length") == 0)
        check('the entries are not buttons and tapping one opens nothing', await V("() => document.querySelectorAll('button.entry').length") == 0 and await V("() => document.querySelectorAll('.entry').length") > 0)
        await vp.click('.entry >> nth=0'); await vp.wait_for_timeout(200)
        check('...no sheet appeared', await V("() => document.querySelectorAll('.sheet-wrap').length") == 0)
        check('the note says that it is a read-only copy and which days', 'read-only' in await vp.inner_text('.view-note') and 'made' in await vp.inner_text('.view-note'), await vp.inner_text('.view-note'))
        check('only the tables the link needs were loaded: this link has CIQUAL, USDA and dmBio foods, so all three', all(f in reqs for f in ['ciqual.json', 'usda.json', 'dmbio.json']), [r for r in reqs if r.endswith('.json')])
        snap_viewer = await V(DAYSNAP, days)
        same = all(snap_sender[d] == snap_viewer[d] for d in days)
        check('every shared day shows the same numbers as in the sender: hero, meal lines, entry lines, Nutrients rows, NOVA card', same)
        if not same:
            for d in days:
                if snap_sender[d] != snap_viewer[d]:
                    for part in ('log', 'nutr'):
                        if snap_sender[d][part] != snap_viewer[d][part]:
                            print('   DIFF', d, part)
                            for k in snap_sender[d][part]:
                                if snap_sender[d][part][k] != snap_viewer[d][part][k]: print('     ', k, '\n       S:', json.dumps(snap_sender[d][part][k])[:600], '\n       V:', json.dumps(snap_viewer[d][part][k])[:600])
        d0 = snap_viewer[days[0]]
        check('the day has its marks: ~ on an estimate, ≥ on a lower value, a red salt value above 0.4 g', any('~' in e['ms'] for m in d0['log']['meals'] for e in m['entries']) and any('≥' in (m['sum'] or '') for dd in days for m in snap_viewer[dd]['log']['meals']) and any(e['hot'] for m in d0['log']['meals'] for e in m['entries']))
        check('a drink shows ml and a capsule its unit, as in the sender', any('250 ml' in e['sub'] for m in d0['log']['meals'] for e in m['entries']) and any('2 capsule' in e['sub'] for m in d0['log']['meals'] for e in m['entries']))
        check('the entry without a saved time shows the time it was added, in the right place', any(e['sub'].startswith('09:30') for m in snap_viewer[days[1]]['log']['meals'] for e in m['entries']))
        check('the NOVA group set by hand for a CIQUAL food is in the NOVA card', snap_viewer[days[0]]['nutr']['nova'] == snap_sender[days[0]]['nutr']['nova'] and '%' in snap_viewer[days[0]]['nutr']['nova'])
        check('the Nutrients tab has no "Set NOVA groups" part and no NOVA buttons', await V("() => { window.__tapnaplo.S.tab = 'nutr'; window.__tapnaplo.render(); return document.querySelectorAll('#novafold, [data-act=nova-set]').length; }") == 0 and 'What are the NOVA groups?' in await vp.inner_text('#view'))
        check('...and the tab note is still there', 'read-only' in await vp.inner_text('#view .view-note'))
        await V("() => { window.__tapnaplo.S.tab = 'log'; window.__tapnaplo.S.day = '%s'; window.__tapnaplo.render(); }" % days[0])

        # --- walking through the days ---
        check('the date picker is limited to the shared days', await vp.get_attribute('#datepick', 'min') == info['from7'] and await vp.get_attribute('#datepick', 'max') == info['today'])
        check('Next day is off on the last day, Previous day works', await vp.is_disabled('[data-act=day][data-n="1"]') and not await vp.is_disabled('[data-act=day][data-n="-1"]'))
        await vp.click('[data-act=day][data-n="-1"]')
        check('Previous day shows the day before', await V("() => window.__tapnaplo.S.day") == days[1])
        for _ in range(8):
            if await vp.is_disabled('[data-act=day][data-n="-1"]'): break
            await vp.click('[data-act=day][data-n="-1"]')
        check('Previous day stops at the first shared day', await V("() => window.__tapnaplo.S.day") == info['from7'] and await vp.is_disabled('[data-act=day][data-n="-1"]'))
        await vp.fill('#datepick', days[3])
        check('the date picker jumps to a day', await V("() => window.__tapnaplo.S.day") == days[3])
        await vp.fill('#datepick', '2019-01-01')
        check('a date outside the shared days is pulled back into them', await V("() => window.__tapnaplo.S.day") == info['from7'])
        await vp.click('[data-act=tab][data-tab=nutr]')
        check('the Nutrients tab opens', await V("() => window.__tapnaplo.S.tab") == 'nutr')
        await vp.evaluate("(d) => { window.__tapnaplo.S.day = d; window.__tapnaplo.render(); }", days[2])
        check('an empty day in the Nutrients tab says so', 'Nothing logged for this day' in await vp.inner_text('#view'))
        await vp.click('#view [data-act=tab][data-tab=log]')
        check('Go to Diary switches the tab, and the empty day says so there too', await V("() => window.__tapnaplo.S.tab") == 'log' and 'Nothing logged on this day' in await vp.inner_text('#view'))

        # --- writes ---
        w = await V('window.__w')
        check('the viewer did not open the storage of the browser, wrote nothing to it, and wrote nothing to localStorage', w == {'idbOpen': 0, 'idbWrite': 0, 'lsWrite': 0}, w)
        check('the viewer started no Sync', await V("() => !window.__tapnaplo.SY.cfg && !window.__tapnaplo.SY.busy") and all('github' not in r for r in outside))
        check('an edit through the page code is not saved either (save does nothing)', await V("() => { window.__tapnaplo.save(); return true; }") and await vp.evaluate("() => new Promise((r) => setTimeout(() => r(window.__w), 400))") == {'idbOpen': 0, 'idbWrite': 0, 'lsWrite': 0})
        for bad in ('add', 'edit-entry', 'export-json', 'nova-set', 'share', 'sync-now', 'refresh-app'):
            await vp.evaluate("(a) => { const b = document.createElement('button'); b.dataset.act = a; b.dataset.id = 'x'; b.dataset.v = '1'; document.body.append(b); b.click(); b.remove(); }", bad)
        await vp.wait_for_timeout(300)
        check('even a button with another action injected into the page does nothing in a shared copy', await V("() => document.querySelectorAll('.sheet-wrap').length") == 0 and await V('window.__w') == {'idbOpen': 0, 'idbWrite': 0, 'lsWrite': 0})
        # layout and look
        await V("() => { window.__tapnaplo.S.day = '%s'; window.__tapnaplo.S.tab = 'log'; window.__tapnaplo.render(); }" % days[0])
        check('390 px: no sideways scroll', await V('() => document.documentElement.scrollWidth <= window.innerWidth'))
        check('touch targets of the shared copy are at least 44 px', await V(SIZES, '.tab, .icon-btn, .btn') == [], await V(SIZES, '.tab, .icon-btn, .btn'))
        light = await V(CONTRAST_JS, '#view'); lh = await V(CONTRAST_JS, '#topbar')
        check('contrast (light)', light == [] and lh == [], light + lh)
        if SHOTS: await vp.screenshot(path=SHOTS + '/share_view_light.png')
        await V("() => document.documentElement.setAttribute('data-theme','dark')")
        dark = await V(CONTRAST_JS, '#view'); dh = await V(CONTRAST_JS, '#topbar')
        check('contrast (dark)', dark == [] and dh == [], dark + dh)
        if SHOTS: await vp.screenshot(path=SHOTS + '/share_view_dark.png')
        await V("() => document.documentElement.setAttribute('data-theme','light')")
        await vp.close()

        # --- her own diary is as it was ---
        own2 = await ctxB.new_page(); watch(own2, 'O2')
        await own2.goto(URL); await own2.wait_for_function('window.__tapnaplo && window.__tapnaplo.S.log.length > 0')
        await own2.wait_for_timeout(300)
        hers_after = await own2.evaluate("() => JSON.stringify([window.__tapnaplo.S.log, window.__tapnaplo.S.foods, window.__tapnaplo.S.meta, localStorage.getItem('nutrilog.tab')], (k, v) => (k[0] === '_' ? undefined : v))")
        check('the diary, foods, settings and remembered tab of the person who opened the link are exactly as before', hers_after == hers_before and 'u:hers' in hers_after and 'Plain food' not in hers_after)
        await own2.close()

        # --- only the tables the link needs ---
        async def open_link(u, ctxx=None, expect='.hero'):
            pg = await (ctxx or ctxB).new_page(); watch(pg, 'X')
            rq = []
            pg.on('request', lambda r: rq.append(r.url.split('/')[-1].split('#')[0]))
            await pg.goto(u); await pg.wait_for_selector(expect, timeout=15000)
            return pg, [r for r in rq if r.endswith('.json')]
        pg, got = await open_link(link(valid()))
        check('a link with only a CIQUAL food loads only ciqual.json', got == ['ciqual.json'], got)
        check('...and shows the food and its energy', await pg.evaluate("() => document.querySelectorAll('.entry').length") == 1)
        await pg.close()
        pg, got = await open_link(link(valid(refs=['usda:170000'], days={'2026-10-26': [['m1', 0, '08:00', 100]]})))
        check('a link with a USDA food loads usda.json and not dmbio.json', 'usda.json' in got and 'dmbio.json' not in got, got)
        await pg.close()
        dmid = await page.evaluate("() => window.__tapnaplo.DMBIO[0].id")
        pg, got = await open_link(link(valid(refs=[dmid], days={'2026-10-26': [['m1', 0, '08:00', 100]]})))
        check('a link with a dmBio food loads dmbio.json and not usda.json', 'dmbio.json' in got and 'usda.json' not in got, got)
        await pg.close()
        pg, got = await open_link(link(valid(refs=['c:99999999'])))
        check('a food that this version does not know: the day says so instead of hiding it silently', 'cannot be shown' in await pg.inner_text('#view'), (await pg.inner_text('#view'))[:200])
        await pg.close()

        # --- plain link, trailing characters, new link in the same tab ---
        pg, _ = await open_link(link(valid(), prefix='j'))
        check('a plain (j.) link opens', await pg.evaluate("() => !!window.__tapnaplo.VIEW && document.querySelectorAll('.entry').length") == 1)
        await pg.close()
        for tail in ('.', ')', ',', '!'):
            pg, _ = await open_link(link(valid()) + tail)
            check(f'a chat app adding "{tail}" behind the link does not matter', await pg.evaluate("() => document.querySelectorAll('.entry').length") == 1)
            await pg.close()
        pg, _ = await open_link(link(valid()))
        newer = link(valid(days={'2026-10-26': [['m1', 0, '08:00', 100], ['m2', 0, '09:00', 50]]}))
        await pg.evaluate("(h) => { location.hash = h; }", newer.split('#')[1])
        await pg.wait_for_function("document.querySelectorAll('.entry').length === 2", timeout=10000)
        check('a second link put into the same tab replaces the first one', await pg.evaluate("() => document.querySelectorAll('.entry').length") == 2)
        await pg.close()

        # --- bad links ---
        async def bad_link(name, u, title, ctxx=None, extra=None):
            pg = await (ctxx or ctxB).new_page(); watch(pg, 'B')
            e0 = len(errs)
            t0 = time.time()
            await pg.goto(u); await pg.wait_for_selector('#view .card-t', timeout=15000)
            await pg.wait_for_timeout(150)
            got = await pg.inner_text('#view .card-t')
            w = await pg.evaluate('window.__w')
            ok = got == title and w == {'idbOpen': 0, 'idbWrite': 0, 'lsWrite': 0} and len(errs) == e0 and await pg.locator('#vw-reload').count() == 1 and await pg.evaluate("() => document.querySelectorAll('.entry, .tab').length") == 0
            check(f'bad link: {name}', ok, (got, w, round(time.time() - t0, 1)))
            if extra: await extra(pg)
            await pg.close()
        BAD, NEW, BROWSER = 'This link cannot be opened', 'This link needs a newer version', 'This browser cannot open the link'
        good = link(valid())
        await bad_link('nothing but the marker', URL + '#share=', BAD)
        await bad_link('random text', URL + '#share=hello', BAD)
        await bad_link('not base64', URL + '#share=z.%%%%%%%%%%', BAD)
        await bad_link('cut in half (a chat app cut it)', good[:len(good) // 2], BAD)
        await bad_link('cut a little (the end is missing)', good[:-6], BAD)
        await bad_link('plain text that is not JSON', link(None, prefix='j', text='this is not json at all'), BAD)
        await bad_link('JSON of something else', link({'app': 'tapnaplo', 'version': 1, 'foods': {}}), BAD)
        await bad_link('a list instead of an object', link([1, 2, 3]), BAD)
        await bad_link('a newer format (v 2)', link(valid(v=2)), NEW)
        await bad_link('an unknown packing prefix', URL + '#share=q.' + b64u(b'something in a new packing'), NEW)
        await bad_link('version 0', link(valid(v=0)), BAD)
        await bad_link('first day after last day', link(valid(**{'from': '2026-10-27'})), BAD)
        await bad_link('a date that does not exist', link(valid(**{'from': '2026-02-30'})), BAD)
        await bad_link('a period of many years', link(valid(**{'from': '2020-01-01'})), BAD)
        await bad_link('a day outside the period', link(valid(days={'2026-11-02': [['m1', 0, '08:00', 100]]})), BAD)
        await bad_link('a day key that is not a date (__proto__)', link(None, text='{"app":"tapnaplo-share","v":1,"made":1,"from":"2026-10-20","to":"2026-10-26","refs":["%s"],"foods":[],"nova":{},"days":{"__proto__":[["m1",0,"08:00",100]]}}' % CIQ_ID), BAD)
        await bad_link('a meal that does not exist', link(valid(days={'2026-10-26': [['breakfast', 0, '08:00', 100]]})), BAD)
        await bad_link('a food number that is not in the list', link(valid(days={'2026-10-26': [['m1', 5, '08:00', 100]]})), BAD)
        await bad_link('a negative amount', link(valid(days={'2026-10-26': [['m1', 0, '08:00', -5]]})), BAD)
        await bad_link('an amount that is text', link(valid(days={'2026-10-26': [['m1', 0, '08:00', '100']]})), BAD)
        await bad_link('a time that is not a time', link(valid(days={'2026-10-26': [['m1', 0, '25:99', 100]]})), BAD)
        await bad_link('an entry with the wrong number of parts', link(valid(days={'2026-10-26': [['m1', 0, '08:00']]})), BAD)
        await bad_link('a food id that is not an id', link(valid(refs=['<script>alert(1)</script>'])), BAD)
        await bad_link('a food id of a kind that does not exist', link(valid(refs=['x:1'])), BAD)
        await bad_link('an own food that is not in the foods list', link(valid(refs=['u:missing'])), BAD)
        await bad_link('an own food without a name', link(valid(refs=['u:abc'], foods=[own_food(name='')])), BAD)
        await bad_link('an own food with a basis of 0', link(valid(refs=['u:abc'], foods=[own_food(basis={'qty': 0, 'unit': 'g'})])), BAD)
        await bad_link('two foods with the same id', link(valid(refs=['u:abc'], foods=[own_food(), own_food()])), BAD)
        await bad_link('foods that is not a list', link(valid(foods={'u:abc': own_food()})), BAD)
        await bad_link('a zip bomb (30 MB of zeros in a 30 KB link)', URL + '#share=z.' + b64u(zlib.compress(b'0' * 30_000_000, 9)), BAD)

        async def reload_works(pg):
            await pg.click('#vw-reload')
            await pg.wait_for_selector('#view .card-t')
            check('the Reload page button on the message reloads without a crash', 'cannot be opened' in await pg.inner_text('#view .card-t'))
        await bad_link('(reload button)', URL + '#share=hello', BAD, extra=reload_works)

        # --- hostile content in a good link ---
        evil = '<img src=x onerror="window.__pwn=1">'
        pg, _ = await open_link(link(valid(refs=['u:abc'], foods=[own_food(name=evil, brand='<b>x</b>', n={'kcal': 100, 'protein': '<script>', 'salt': 1})])))
        await pg.wait_for_timeout(300)
        check('a food name with HTML is shown as text, nothing runs', await pg.evaluate("() => window.__pwn") is None and evil in await pg.inner_text('#view') and await pg.evaluate("() => document.querySelectorAll('#view img, #view script').length") == 0)
        check('...a value that is not a number is dropped (no data), not shown', 'script' not in (await pg.inner_text('#view')).lower().replace('<img', ''))
        await pg.close()
        pg, _ = await open_link(link(None, text='{"app":"tapnaplo-share","v":1,"made":1,"from":"2026-10-20","to":"2026-10-26","refs":["u:abc"],"foods":[{"id":"u:abc","name":"Proto","basis":{"qty":100,"unit":"g"},"n":{"kcal":100,"__proto__":{"x":1},"constructor":5},"__proto__":{"polluted":1},"src":"user"}],"nova":{"__proto__":1},"days":{"2026-10-26":[["m1",0,"08:00",100]]}}'))
        check('__proto__ and constructor keys do nothing', await pg.evaluate("() => ({}).polluted === undefined && ({}).x === undefined && document.querySelectorAll('.entry').length") == 1)
        await pg.close()

        # --- a browser that cannot unpack ---
        ctxN = await new_ctx()
        await ctxN.add_init_script("delete window.DecompressionStream;")
        await ctxN.add_init_script(WATCH)
        await bad_link('packed (z.) link in a browser without DecompressionStream says so', good, BROWSER, ctxx=ctxN)
        pg, _ = await open_link(link(valid(), prefix='j'), ctxx=ctxN)
        check('a plain (j.) link still opens there', await pg.evaluate("() => document.querySelectorAll('.entry').length") == 1)
        await pg.close()
        await ctxN.close()

        # --- the other way round: a link from the sender that was made without compression opens with the same numbers ---
        pg, _ = await open_link(plain_url)
        sv = await pg.evaluate(DAYSNAP, days)
        check('the uncompressed link from the old browser shows the same numbers as the sender', all(snap_sender[d] == sv[d] for d in days))
        await pg.close()

        # --- version ---
        app_js = (ROOT / 'app.js').read_text(); sw = (ROOT / 'sw.js').read_text()
        ver = re.search(r"const VERSION = '(\d+)", app_js).group(1)
        cache = re.search(r"const CACHE = 'nutrilog-v(\d+)'", sw).group(1)
        check('the version is 23 or newer and the service worker cache has the same number', int(ver) >= 23 and ver == cache, (ver, cache))
        check('nothing outside the local server was requested', outside == [], outside[:5])
        check('no page errors', errs == [], errs[:5])
        await browser.close()
        print('\nFAILED: ' + ', '.join(problems) if problems else '\nALL PASSED')
        sys.exit(1 if problems else 0)

asyncio.run(main())
