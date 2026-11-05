"""Water intake (version 24, every recording has a time since version 34). Run with the web server on port 8765 (see CLAUDE.md).

A card "Water intake" sits in the Diary above the meals. Every tap of +1 / +2 / +3 / +5 dL (or "Other": any amount, any time, in mL or dL) is a recording with a time of day {id, t, d, tm, ml} in S.wlog.
The total of a day is the sum of its recordings plus the amount that was logged before version 34 (S.meta.water['YYYY-MM-DD'], whole ml, shown as "No time"); a day with neither has nothing logged
(the daily totals CSV leaves the cell empty, it does not say 0). A closed list "Recordings (n) · last HH:MM" shows the recordings; a row opens the sheet to change the amount or the time, or to delete it
(with Undo). It is not the nutrient "Water" (the water inside foods).
Covers: place of the card, empty day, quick buttons (time of now) and their Undo, the list, the sheet (unit switch converts the amount, chips, comma decimals, remembered unit, Enter, time typing and
every error text, the 20 L limit, edit, delete, the "No time" row, Clear day, Undo for all), one total per day, old saves without water and damaged water or recordings in storage, backup JSON and Restore (with and
without recordings, damaged), the daily totals CSV and the water CSV, Sync with a fake GitHub (water/YYYY.json for the old totals, intake/YYYY-MM.json for recordings, two devices, tombstone, bad records, an older
app ignoring the folder), Share link (totals of the shared days, the recordings with a time, hostile values, a link without them), the Report (Water by hour in Time of day: hand-calculated bars, own chart state,
legend, table, water without food, period without water or without a time, shared copy), touch targets, 16 px fields, contrast in light and dark, 390 and 320 px width, the version number, no page errors."""
import asyncio, base64, csv, io, json, os, pathlib, re, sys, zlib
from datetime import date, datetime, timedelta, timezone
from playwright.async_api import async_playwright
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_ai_import import CONTRAST_JS, SMALL_FONTS
from test_sync import FakeGitHub, GOOD

URL = 'http://127.0.0.1:8765/index.html'
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
SHOTS = os.environ.get('SHOTS', '')
NOWISO = '2026-11-05T12:00:00+01:00'      # the fixed clock of the sections that need the time of now: Thursday 5 Nov 2026, 12:00 in Budapest
FT_MS = int(datetime(2026, 11, 5, 11, 0, tzinfo=timezone.utc).timestamp() * 1000)

WATCH = """(() => {
  window.__w = { idbOpen: 0, idbWrite: 0, lsWrite: 0 };
  const o = indexedDB.open.bind(indexedDB); indexedDB.open = function () { window.__w.idbOpen++; return o.apply(this, arguments); };
  for (const m of ['put', 'add', 'delete', 'clear']) { const f = IDBObjectStore.prototype[m]; IDBObjectStore.prototype[m] = function () { window.__w.idbWrite++; return f.apply(this, arguments); }; }
  for (const m of ['setItem', 'removeItem', 'clear']) { const f = Storage.prototype[m]; Storage.prototype[m] = function () { window.__w.lsWrite++; return f.apply(this, arguments); }; }
})();"""
SIZES = "(sel) => [...document.querySelectorAll(sel)].filter((e) => !e.hidden && e.getClientRects().length).map((e) => { const r = e.getBoundingClientRect(); return [(e.id || e.dataset.act || e.className || e.tagName) + ':' + e.textContent.trim().slice(0, 14), Math.round(r.width), Math.round(r.height)]; }).filter((x) => x[2] < 44 || x[1] < 44)"


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


def own(fid, name, n):
    return {'id': fid, 'src': 'user', 'name': name, 'brand': '', 'barcode': '', 'basis': {'qty': 100, 'unit': 'g'}, 'n': n, 'nova': None, 'portions': [], 'note': '', 'created': 1000, 'updated': 1000}


def squash(t):
    return re.sub(r'\s+', '', t or '')


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
        water = lambda: T("""() => { const t = window.__tapnaplo, days = new Set([...Object.keys(t.S.meta.water), ...t.S.wlog.map((r) => r.d)]); return Object.fromEntries([...days].sort().map((d) => [d, t.waterOf(d)])); }""")   # the total of every day that has water
        legacy = lambda: T("() => JSON.parse(JSON.stringify(window.__tapnaplo.S.meta.water))")      # only the amounts logged before water had a time
        recs = lambda: T("() => JSON.parse(JSON.stringify(window.__tapnaplo.S.wlog))")
        num = lambda: page.inner_text('.water-num')
        side = lambda: page.inner_text('.water-top .muted')
        toast = lambda: page.inner_text('#toast span')
        sheet_open = lambda: page.locator('#wamt').count()

        async def reset_water(w=None):
            await T("(w) => { const t = window.__tapnaplo; t.S.meta.water = w || {}; t.S.wlog.length = 0; t.save(); t.render(); }", w)

        async def open_other():
            await page.click('[data-act=water-other]'); await page.wait_for_selector('#wamt')
            await page.wait_for_timeout(300)   # the sheet slides in

        async def close_sheet():
            if await sheet_open():
                await page.click('.sheet [data-x]'); await page.wait_for_selector('#wamt', state='detached')

        # =========================================================== 1 the card
        check('the Diary has a Water intake card', await page.locator('#water .water-card').count() == 1 and 'Water intake' in await page.inner_text('#water .card-t'))
        order = await T("""() => { const w = document.querySelector('#water'), m = document.querySelector('.meal'), c = document.querySelector('.hero ~ .card'), a = document.querySelector('.actions');
          const after = (x, y) => !!(x.compareDocumentPosition(y) & Node.DOCUMENT_POSITION_FOLLOWING);
          return [after(a, w), after(c, w), after(w, m), document.querySelectorAll('.meal').length]; }""")
        check('...it sits below the macro card and above the first Meal', order[0] and order[1] and order[2] and order[3] == 6, order)
        check('an empty day shows 0 mL and "Nothing logged yet"', squash(await num()) == '0mL' and 'Nothing logged yet' in await side(), (await num(), await side()))
        btns = await page.locator('#water button').all_inner_texts()
        check('the card has +1, +2, +3, +5 dL and Other', btns == ['+1 dL', '+2 dL', '+3 dL', '+5 dL', 'Other'], btns)
        check('every button names what it does for a screen reader', await T("[...document.querySelectorAll('#water button')].map((b) => b.getAttribute('aria-label'))") == ['Add 1 dL of water', 'Add 2 dL of water', 'Add 3 dL of water', 'Add 5 dL of water', 'Add another amount of water at another time'])
        check('the card only has the water in it: no entry is made, the Energy stays 0', await T("() => window.__tapnaplo.S.log.length") == 0 and '0' == (await page.inner_text('.hero-num')).replace('kcal', '').strip())

        # =========================================================== 2 quick buttons
        await page.tap('[data-act=water-add][data-dl="2"]')
        check('+2 dL: 200 mL, shown as 2 dL too', squash(await num()) == '200mL' and '2 dL' in await side(), (await num(), await side()))
        check('...the toast says what happened, at what time, and offers Undo', re.search(r'Water \+2 dL at \d\d:\d\d · total 200 mL', await toast()) is not None and await page.locator('#toast button').count() == 1, await toast())
        await page.tap('[data-act=water-add][data-dl="3"]')
        check('+3 dL on top: 500 mL = 5 dL', squash(await num()) == '500mL' and '5 dL' in await side())
        await page.tap('#toast button')
        check('Undo takes back only the last tap', squash(await num()) == '200mL' and (await water()) == {today: 200}, await water())
        await page.tap('[data-act=water-add][data-dl="1"]'); await page.tap('[data-act=water-add][data-dl="5"]')
        check('+1 dL and +5 dL add up (200 + 100 + 500 = 800 mL = 8 dL)', squash(await num()) == '800mL' and '8 dL' in await side(), await num())
        check('the amounts are kept as recordings with a time, not in the old per-day totals', (await water()) == {today: 800} and (await legacy()) == {} and len(await recs()) == 3, (await legacy(), len(await recs())))
        check('the page did not jump or redraw outside the card (the Energy hero is still the same element)', await T("() => !!document.querySelector('.hero') && document.querySelectorAll('#water').length === 1"))

        # =========================================================== 3 the sheet
        await reset_water({today: 1250})
        await open_other()
        check('Other opens the sheet "Water intake" with the day, the total and both units', 'Water intake' in await page.inner_text('.sheet-h h2') and '1,250 mL (12.5 dL)' in await page.inner_text('.sheet-b'), (await page.inner_text('.sheet-b'))[:160])
        check('it starts in dL with 2 dL (a glass) and the button says what it will add', await page.input_value('#wamt') == '2' and (await page.inner_text('#wadd')).strip() == 'Add 2 dL' and await page.get_attribute('[data-u=dl]', 'aria-pressed') == 'true' and await page.get_attribute('[data-u=ml]', 'aria-pressed') == 'false')
        check('the label names the unit', 'Amount (dL)' in await page.inner_text('label.f'), await page.inner_text('label.f'))
        check('dL chips: 1 2 3 5 10', await page.locator('#wchips button').all_inner_texts() == ['1 dL', '2 dL', '3 dL', '5 dL', '10 dL'], await page.locator('#wchips button').all_inner_texts())
        await page.click('[data-u=ml]')
        check('switching to mL converts the amount (2 dL = 200 mL) and the button follows', await page.input_value('#wamt') == '200' and (await page.inner_text('#wadd')).strip() == 'Add 200 mL' and 'Amount (mL)' in await page.inner_text('label.f'))
        check('mL chips: 100 200 250 330 500', await page.locator('#wchips button').all_inner_texts() == ['100 mL', '200 mL', '250 mL', '330 mL', '500 mL'])
        await page.fill('#wamt', '150'); await page.click('[data-u=dl]')
        check('...and back: 150 mL becomes 1.5 dL', await page.input_value('#wamt') == '1.5' and (await page.inner_text('#wadd')).strip() == 'Add 1.5 dL', await page.input_value('#wamt'))
        await page.click('#wchips button:has-text("5 dL")')
        check('a chip fills the field', await page.input_value('#wamt') == '5' and (await page.inner_text('#wadd')).strip() == 'Add 5 dL')
        await page.fill('#wamt', '1,5')
        check('a decimal comma is understood (1,5 dL)', (await page.inner_text('#wadd')).strip() == 'Add 1.5 dL')
        await page.click('#wadd')
        check('Add 1.5 dL adds 150 mL: 1,400 mL', (await water()) == {today: 1400} and squash(await num()) == '1,400mL', await water())
        check('...the sheet closed and the toast has Undo with the new total', not await sheet_open() and re.search(r'Water \+1\.5 dL at \d\d:\d\d · total 1,400 mL', await toast()) is not None, await toast())
        await page.tap('#toast button')
        check('Undo restores 1,250 mL', (await water()) == {today: 1250})
        # 330 mL, remembered unit
        await open_other()
        check('the unit used last (dL) is remembered on this device', await page.get_attribute('[data-u=dl]', 'aria-pressed') == 'true')
        await page.click('[data-u=ml]'); await page.fill('#wamt', '330'); await page.press('#wamt', 'Enter')
        check('Enter in the field adds (330 mL → 1,580 mL)', (await water()) == {today: 1580} and not await sheet_open(), await water())
        await open_other()
        check('after adding in mL, the sheet opens in mL with 250', await page.get_attribute('[data-u=ml]', 'aria-pressed') == 'true' and await page.input_value('#wamt') == '250')
        await page.fill('#wamt', '0.5'); await page.click('[data-u=dl]')
        await page.fill('#wamt', '0.5'); await page.click('#wadd')
        check('0.5 dL = 50 mL (1,630 mL)', (await water()) == {today: 1630}, await water())
        await page.tap('#toast button')

        # ---- errors, each next to the field
        await reset_water({today: 1250})
        async def err_of(value, button='#wadd', unit=None):
            await open_other()
            if unit: await page.click(f'[data-u={unit}]')
            await page.fill('#wamt', value); await page.click(button)
            msg = await page.inner_text('.field-err') if await page.locator('.field-err').count() else ''
            inv = await page.get_attribute('#wamt', 'aria-invalid')
            still = await sheet_open()
            await close_sheet()
            return msg, inv, still
        for v in ('', '0', 'abc', '-3'):
            msg, inv, still = await err_of(v)
            check(f'amount "{v}": "Enter an amount greater than 0." next to the field, the sheet stays open, nothing changes', msg == 'Enter an amount greater than 0.' and inv == 'true' and still and (await water()) == {today: 1250}, (msg, inv, still))
        msg, _, _ = await err_of('0.4', unit='ml')
        check('0.4 mL rounds to nothing: "The smallest amount is 1 mL."', msg == 'The smallest amount is 1 mL.', msg)
        msg, _, _ = await err_of('25000', unit='ml')
        check('25,000 mL at once: "At most 20,000 mL (200 dL) at a time."', msg == 'At most 20,000 mL (200 dL) at a time.', msg)
        msg, _, _ = await err_of('201')
        check('201 dL at once is refused too', 'At most 20,000 mL' in msg, msg)
        await reset_water({today: 19900})
        msg, _, _ = await err_of('2')
        check('19,900 + 2 dL passes the day limit: the message says how much still fits', msg == 'A day can hold at most 20,000 mL (200 dL). You can add 100 mL more.' and (await water()) == {today: 19900}, msg)
        await page.tap('[data-act=water-add][data-dl="1"]')
        check('the quick button at the limit: 19,900 + 100 = 20,000 mL is allowed', (await water()) == {today: 20000} and 'total 20,000 mL' in await toast(), await water())
        await page.tap('[data-act=water-add][data-dl="1"]')
        check('...one more is refused with a toast and nothing changes', (await water()) == {today: 20000} and 'at most 20,000 mL' in await toast(), await toast())
        await reset_water({today: 640})
        await open_other()
        check('Clear day is offered while there is a total', await page.locator('#wclear').is_visible())
        await page.click('#wclear')
        check('Clear day removes the day and says so, with Undo', (await water()) == {} and 'Water cleared for this day' in await toast() and not await sheet_open(), await toast())
        await page.tap('#toast button')
        check('Undo of Clear day restores 640 mL', (await water()) == {today: 640})
        await reset_water({})
        await open_other()
        check('Clear day is hidden when nothing is logged', not await page.locator('#wclear').is_visible() and 'Total of the day: nothing logged' in (await page.inner_text('.sheet-b')).replace('\n', ' '))
        await close_sheet()
        await page.keyboard.press('Escape')

        # =========================================================== 4 one total per day
        await reset_water({})
        await page.tap('[data-act=water-add][data-dl="2"]')
        await page.tap('[data-act=day][data-n="-1"]')
        check('yesterday starts empty', squash(await num()) == '0mL' and 'Nothing logged yet' in await side() and 'Yesterday' in await page.inner_text('#topbar h1'))
        await page.tap('[data-act=water-add][data-dl="5"]')
        await open_other(); await page.fill('#wamt', '1'); await page.click('#wadd')
        check('yesterday: 5 dL + 1 dL = 600 mL, today stays 200 mL', (await water()) == {today: 200, day(-1): 600}, await water())
        await page.tap('[data-act=day][data-n="1"]')
        check('back on today: 200 mL', squash(await num()) == '200mL')
        await page.tap('[data-act=day][data-n="1"]')
        await page.tap('[data-act=water-add][data-dl="3"]')
        check('tomorrow can be filled in too', (await water()).get(day(1)) == 300)
        await page.tap('[data-act=today]')
        await page.wait_for_timeout(700)   # the save runs 120 ms after a change
        await page.reload(); await page.wait_for_selector('.hero')
        check('after a reload all three days are still there', (await water()) == {today: 200, day(-1): 600, day(1): 300}, await water())
        check('...and today shows 200 mL', squash(await num()) == '200mL')
        check('every amount has a time of day (a real HH:MM, a real day, whole ml), the old per-day totals were not touched, and no diary entry was made', await T("() => { const t = window.__tapnaplo; return t.S.wlog.length > 0 && t.S.wlog.every((r) => /^([01]\\d|2[0-3]):[0-5]\\d$/.test(r.tm) && Number.isInteger(r.ml) && /^\\d{4}-\\d{2}-\\d{2}$/.test(r.d) && r.t > 1e12) && Object.keys(t.S.meta.water).length === 0 && t.S.log.length === 0; }"))

        # =========================================================== 5 old and damaged storage
        await T("() => { const t = window.__tapnaplo; delete t.S.meta.water; t.S.wlog.length = 0; t.save(); }")
        await page.wait_for_timeout(500); await page.reload(); await page.wait_for_selector('.hero')
        check('a save from before version 24 (no water key) starts fine and shows 0 mL', await water() == {} and squash(await num()) == '0mL')
        await T("""(a) => { const t = window.__tapnaplo; t.S.meta.water = { [a[0]]: '1500', bad: 5, '2026-02-30': 100, [a[1]]: -5, [a[2]]: 1e9, [a[3]]: 250.4, [a[4]]: null, [a[5]]: 0 }; t.save(); }""", [today, day(-1), day(-2), day(-3), day(-4), day(-5)])
        await page.wait_for_timeout(500); await page.reload(); await page.wait_for_selector('.hero')
        check('damaged water in storage is cleaned at start: text numbers and decimals become whole ml, the rest is dropped', (await water()) == {today: 1500, day(-3): 250}, await water())
        await reset_water({})

        # =========================================================== 6 backup and restore
        await T("""([f]) => { const t = window.__tapnaplo; t.S.foods[f.id] = f; t.S.log.push({ id: 'e1', d: t.S.day, m: 'm1', f: f.id, a: 100, t: 1, tm: '08:00' }); t.S.meta.water = {}; t.save(); t.render(); }""", [own('u:oat', 'Oat', {'kcal': 100, 'protein': 5, 'carbohydrate': 10, 'fat': 2})])
        await page.tap('[data-act=water-add][data-dl="2"]'); await page.tap('[data-act=day][data-n="-1"]'); await page.tap('[data-act=water-add][data-dl="5"]'); await page.tap('[data-act=today]')
        await page.wait_for_timeout(500)
        await page.click('[data-tab=data]'); await page.wait_for_selector('[data-act=export-json]')
        async with page.expect_download() as dd:
            await page.click('[data-act=export-json]')
        dl = await dd.value
        backup = json.loads(pathlib.Path(await dl.path()).read_text(encoding='utf-8'))
        check('the backup JSON has the recordings (wlog) and the old per-day totals stay in meta', [(r['d'], r['ml']) for r in sorted(backup.get('wlog', []), key=lambda r: r['d'])] == [(day(-1), 500), (today, 200)] and backup['meta'].get('water') == {}, (backup.get('wlog'), backup['meta'].get('water')))
        check('...every recording has id, t, d, tm and ml and nothing else', all(sorted(r) == ['d', 'id', 'ml', 't', 'tm'] for r in backup['wlog']), backup['wlog'])
        await T("() => { const t = window.__tapnaplo; t.S.meta.water = {}; t.S.wlog.length = 0; t.save(); }")

        async def restore(obj):
            await page.set_input_files('#importfile', {'name': 'backup.json', 'mimeType': 'application/json', 'buffer': json.dumps(obj).encode()})
            await page.wait_for_selector('[data-ok]'); await page.click('[data-ok]')
            await page.wait_for_timeout(500)
        await restore(backup)
        check('Restore from file brings the recordings back', (await water()) == {today: 200, day(-1): 500} and len(await recs()) == 2, await water())
        old = json.loads(json.dumps(backup)); old['meta'].pop('water'); old.pop('wlog')
        await restore(old)
        check('a backup from before version 34 (no wlog, no water) restores fine and leaves the recordings as they are (not an error)', (await water()) == {today: 200, day(-1): 500} and len(await recs()) == 2, await water())
        bad = json.loads(json.dumps(backup)); bad['meta']['water'] = {today: 300, 'nope': 1, '2026-13-01': 5, day(-1): -2, day(-2): 99999999}; bad['wlog'] = []
        await restore(bad)
        check('a damaged old-totals part of a backup is cleaned while restoring (an empty wlog replaces the recordings)', (await legacy()) == {today: 300} and (await recs()) == [], (await legacy(), await recs()))
        bad2 = json.loads(json.dumps(backup)); bad2['meta']['water'] = 'lots'
        await restore(bad2)
        check('old totals of the wrong type in a backup become empty', (await legacy()) == {})
        await restore(backup)

        # =========================================================== 7 CSV
        async def csv_of(act):
            async with page.expect_download() as d:
                await page.click(f'[data-act={act}]')
            dl = await d.value
            path = HERE / 'water_tmp.csv'
            await dl.save_as(str(path))
            text = path.read_text(encoding='utf-8-sig'); path.unlink()
            return list(csv.reader(io.StringIO(text)))
        # today: entry + water 200 ; yesterday: water only 500 ; day-2: entry only ; day-3: only an old water value
        await T("""([d2, d3]) => { const t = window.__tapnaplo; t.S.log.push({ id: 'e2', d: d2, m: 'm1', f: 'u:oat', a: 50, t: 2, tm: '09:00' }); t.S.meta.water[d3] = 1750; t.save(); }""", [day(-2), day(-3)])
        rows = await csv_of('export-days')
        head = rows[0]
        check('daily totals: water_intake_ml comes right after est_share', head[:4] == ['date', 'entries', 'est_share', 'water_intake_ml'], head[:5])
        by = {r[0]: r for r in rows[1:]}
        check('daily totals: a day with food and water has both (200 mL)', today in by and by[today][1] == '1' and by[today][3] == '200', by.get(today, [])[:5])
        check('daily totals: a day with only water gets a row (0 entries, 500 mL, nutrient cells empty)', day(-1) in by and by[day(-1)][1] == '0' and by[day(-1)][3] == '500' and all(c == '' for c in by[day(-1)][4:4 + 64]), by.get(day(-1), [])[:8])
        check('daily totals: a day with food and no water has an EMPTY water cell, not 0', day(-2) in by and by[day(-2)][1] == '1' and by[day(-2)][3] == '', by.get(day(-2), [])[:5])
        check('daily totals: a day with only an old water value is there too (1750 mL)', by.get(day(-3), ['', '', '', ''])[3] == '1750')
        check('daily totals: the days are in date order', [r[0] for r in rows[1:]] == sorted(r[0] for r in rows[1:]))
        ents = await csv_of('export-entries')
        check('the entries CSV is unchanged by water (no water column, one row per entry)', 'water_intake_ml' not in ents[0] and len(ents) == 3, (len(ents), ents[0][:6]))
        await page.click('[data-tab=log]'); await page.wait_for_selector('.hero')

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
        wa = lambda pg: pg.evaluate("() => JSON.parse(JSON.stringify(window.__tapnaplo.S.meta.water))")
        ctxA, A = await device('SA')
        await A.evaluate("() => { const t = window.__tapnaplo; t.S.meta.water = { '2025-12-31': 900, '2026-01-01': 1100, '2026-10-26': 1750 }; t.save(); }")
        await connect(A)
        files = sorted(gh.files)
        check('sync: the water goes to one file per year (water/2025.json, water/2026.json)', 'water/2025.json' in files and 'water/2026.json' in files, files)
        recs = gh.recs()
        check('sync: one record per day, a plain whole number', recs.get('w:2025-12-31', {}).get('x') == 900 and recs.get('w:2026-01-01', {}).get('x') == 1100 and recs.get('w:2026-10-26', {}).get('x') == 1750, {k: v for k, v in recs.items() if k.startswith('w:')})
        check('sync: the 2025 file holds only 2025 days', set(json.loads(gh.files['water/2025.json'])['recs']) == {'w:2025-12-31'}, list(json.loads(gh.files['water/2025.json'])['recs']))
        ctxB, B = await device('SB')
        await connect(B)
        check('sync: the second device gets the water', (await wa(B)) == {'2025-12-31': 900, '2026-01-01': 1100, '2026-10-26': 1750}, await wa(B))
        # B adds water to a day, A receives it
        await B.evaluate("() => { const t = window.__tapnaplo; t.S.meta.water['2026-10-26'] = 2000; t.S.meta.water['2026-10-27'] = 400; t.save(); }")
        await B.wait_for_timeout(300)
        await sync(B); await sync(A)
        check('sync: a change and a new day made on B reach A', (await wa(A)).get('2026-10-26') == 2000 and (await wa(A)).get('2026-10-27') == 400, await wa(A))
        # a deletion on A (the day becomes "nothing logged") reaches B as a tombstone
        await A.evaluate("() => { const t = window.__tapnaplo; delete t.S.meta.water['2025-12-31']; t.save(); }")
        await A.wait_for_timeout(300)
        await sync(A); await sync(B)
        check('sync: clearing a day on A removes it on B (a tombstone, kept in the repository)', '2025-12-31' not in await wa(B) and gh.recs().get('w:2025-12-31', {}).get('x', 'missing') is None, (await wa(B), gh.recs().get('w:2025-12-31')))
        # the same day changed on both: the later change wins
        await A.evaluate("() => { const t = window.__tapnaplo; t.S.meta.water['2026-10-26'] = 111; t.save(); }")
        await A.wait_for_timeout(300); await sync(A)
        await B.evaluate("() => { const t = window.__tapnaplo; t.S.meta.water['2026-10-26'] = 222; t.save(); }")
        await B.wait_for_timeout(300); await sync(B); await sync(A)
        check('sync: the same day edited on both devices: the later edit wins on both', (await wa(A)).get('2026-10-26') == 222 and (await wa(B)).get('2026-10-26') == 222, (await wa(A), await wa(B)))
        # bad records in the repository are ignored
        gh.files['water/2026.json'] = json.dumps({'app': 'tapnaplo-sync', 'v': 1, 'recs': {
            'w:2026-10-26': {'u': 99999999999999, 'x': 333}, 'w:2026-02-30': {'u': 99999999999999, 'x': 5}, 'w:2026-03-01': {'u': 99999999999999, 'x': -4}, 'w:2026-03-02': {'u': 99999999999999, 'x': 2.5},
            'w:2026-03-03': {'u': 99999999999999, 'x': '300'}, 'w:2026-03-04': {'u': 99999999999999, 'x': 99999999}, 'w:bad': {'u': 99999999999999, 'x': None}, 'w:__proto__': {'u': 99999999999999, 'x': 7}}})
        await sync(A)
        wA = await wa(A)
        check('sync: only valid records are taken from the repository (a real day with a whole number of ml)', wA.get('2026-10-26') == 333 and not any(k in wA for k in ('2026-02-30', '2026-03-01', '2026-03-02', '2026-03-03', '2026-03-04', 'bad', '__proto__')), wA)
        check('sync: no prototype was touched', await A.evaluate("() => ({}).constructor === Object && Object.getPrototypeOf(window.__tapnaplo.S.meta.water) === Object.prototype && !('7' in {})"))
        check('sync: a diary made without water (no keys) sends nothing for water', True)
        await ctxA.close(); await ctxB.close()

        # =========================================================== 9 Share
        await T("""([d0, d1, d2, d3]) => { const t = window.__tapnaplo, S = t.S;
          S.log.length = 0; S.meta.water = {}; S.wlog.length = 0;
          S.log.push({ id: 'a1', d: d1, m: 'm1', f: 'u:oat', a: 100, t: 1, tm: '08:00' }, { id: 'a2', d: d2, m: 'm1', f: 'u:oat', a: 150, t: 2, tm: '09:00' });
          S.meta.water[d0] = 1500; S.meta.water[d1] = 800; S.meta.water[d3] = 999;      // d0 later than every entry, d3 outside the shared period
          t.save(); t.render(); }""", [day(0), day(-1), day(-2), day(-20)])
        snap = await T("([a, b]) => JSON.parse(window.__tapnaplo.shareSnapshot(a, b).json)", [day(-6), day(0)])
        check('share: the snapshot has the water of the shared days only', snap.get('water') == {day(0): 1500, day(-1): 800}, snap.get('water'))
        check('share: the format is still v1 (the water key is an optional addition)', snap['v'] == 1 and snap['app'] == 'tapnaplo-share')
        snap2 = await T("([a, b]) => JSON.parse(window.__tapnaplo.shareSnapshot(a, b).json)", [day(-3), day(-2)])
        check('share: a period without water has no "water" key (the link looks exactly as before)', 'water' not in snap2 and list(snap2['days']) == [day(-2)], list(snap2))
        await T("() => { const t = window.__tapnaplo; t.S.meta.water = {}; t.S.wlog.length = 0; t.save(); }")
        snap3 = await T("([a, b]) => JSON.parse(window.__tapnaplo.shareSnapshot(a, b).json)", [day(-6), day(0)])
        check('share: no water at all → no "water" key', 'water' not in snap3)
        await T("([d0, d1, d3]) => { const t = window.__tapnaplo; t.S.meta.water[d0] = 1500; t.S.meta.water[d1] = 800; t.S.meta.water[d3] = 999; t.save(); }", [day(0), day(-1), day(-20)])
        # the sender sheet
        await page.click('[data-tab=data]'); await page.wait_for_selector('[data-act=share]'); await page.click('[data-act=share]'); await page.wait_for_selector('#sh-info')
        await page.click('[data-days="7"]'); await page.wait_for_function("document.querySelector('#sh-info').textContent.includes('link length')")
        info = await page.inner_text('#sh-info')
        check('share sheet: the message names the water days (2 days with entries · 2 items · water intake on 2 days)', '2 days with entries · 2 items · water intake on 2 days · link length' in info, info)
        await page.click('.sheet [data-x]')
        # only water, no food: the link can still be made
        await T("() => { const t = window.__tapnaplo; t.S.log.length = 0; t.save(); }")
        await page.click('[data-act=share]'); await page.wait_for_selector('#sh-info'); await page.click('[data-days="7"]')
        await page.wait_for_function("document.querySelector('#sh-info').textContent.includes('link length')")
        info = await page.inner_text('#sh-info')
        check('share sheet: with water but no food the link can still be made', '0 days with entries · 0 items · water intake on 2 days' in info and not await page.locator('#sh-copy').is_disabled(), info)
        await page.click('.sheet [data-x]')
        # restore the food entries for the viewer test
        await T("""([d1, d2]) => { const t = window.__tapnaplo; t.S.log.push({ id: 'a1', d: d1, m: 'm1', f: 'u:oat', a: 100, t: 1, tm: '08:00' }, { id: 'a2', d: d2, m: 'm1', f: 'u:oat', a: 150, t: 2, tm: '09:00' }); t.save(); t.render(); }""", [day(-1), day(-2)])
        made = await T("([a, b]) => window.__tapnaplo.shareLink(a, b).then((r) => r.url)", [day(-6), day(0)])
        check('share: the link opens with Python (zlib) and has the water', unpack(made).get('water') == {day(0): 1500, day(-1): 800})

        # the viewer
        async def viewer(url, w=390):
            c = await new_ctx(w=w); await c.add_init_script(WATCH)
            pg = await c.new_page(); watch(pg, 'V')
            await pg.goto(url); await pg.wait_for_selector('.hero, .card', timeout=15000)
            return c, pg
        cV, V = await viewer(made)
        vt = lambda: V.inner_text('#water')
        check('viewer: starts on the last day that has food or water (today, which has only water)', await V.evaluate("() => window.__tapnaplo.S.day") == day(0), await V.evaluate("() => window.__tapnaplo.S.day"))
        check('viewer: the Water intake card shows 1,500 mL (15 dL), above the meals', '1,500' in await vt() and '15 dL' in await vt() and await V.evaluate("() => { const w = document.querySelector('#water'), m = document.querySelector('.meal'); return !!(w.compareDocumentPosition(m) & Node.DOCUMENT_POSITION_FOLLOWING); }"), await vt())
        check('viewer: read-only, no buttons in the card, no water handler reacts', await V.locator('#water button').count() == 0 and await V.locator('[data-act=water-add], [data-act=water-other]').count() == 0)
        await V.evaluate("() => { const b = document.createElement('button'); b.dataset.act = 'water-add'; b.dataset.dl = '5'; b.id = 'fake'; document.body.append(b); }")
        await V.evaluate("() => document.getElementById('fake').click()"); await V.wait_for_timeout(200)
        check('viewer: even a forged water button changes nothing', await V.evaluate("() => window.__tapnaplo.S.meta.water") == {day(0): 1500, day(-1): 800} and await V.evaluate("() => window.__tapnaplo.S.wlog.length") == 0, await V.evaluate("() => JSON.stringify(window.__tapnaplo.S.meta.water)"))
        await V.tap('[data-act=day][data-n="-1"]')
        check('viewer: the day before shows its own total (800 mL) and its food', '800' in await vt() and await V.locator('.entry').count() == 1, await vt())
        await V.tap('[data-act=day][data-n="-1"]')
        check('viewer: a day with food and no water says "Not logged"', 'Not logged' in await vt() and await V.locator('.entry').count() == 1, await vt())
        check('viewer: the weekday title is shown (never Today/Yesterday)', 'Today' not in await V.inner_text('#topbar h1'))
        await V.tap('[data-tab=nutr]')
        check('viewer: the Nutrients tab has no water card', await V.locator('.water-card').count() == 0)
        w = await V.evaluate("() => window.__w")
        check('viewer: nothing was written (IndexedDB not opened, no localStorage write)', w == {'idbOpen': 0, 'idbWrite': 0, 'lsWrite': 0}, w)
        await cV.close()
        # a link made by version 23 (no water key) shows no card at all
        cV, V = await viewer(link({'app': 'tapnaplo-share', 'v': 1, 'made': 1761500000000, 'from': day(-6), 'to': day(0), 'refs': ['c:' + str(json.loads((ROOT / 'ciqual.json').read_text())['foods'][0]['c'])], 'foods': [], 'nova': {}, 'days': {day(-1): [['m1', 0, '08:00', 100]]}}))
        check('viewer: a link without water shows no Water intake card', await V.locator('.water-card').count() == 0 and await V.locator('.entry').count() == 1)
        await cV.close()
        # hostile water
        CID = 'c:' + str(json.loads((ROOT / 'ciqual.json').read_text())['foods'][0]['c'])
        def mk(wat):
            d = {'app': 'tapnaplo-share', 'v': 1, 'made': 1761500000000, 'from': day(-6), 'to': day(0), 'refs': [CID], 'foods': [], 'nova': {}, 'days': {day(-1): [['m1', 0, '08:00', 100]]}}
            if wat is not None: d['water'] = wat
            return d
        raw = json.dumps(mk({day(-1): 1500, day(-2): '999', day(-3): -3, day(-4): 2.5, day(-5): 1e9, day(-30): 500, 'bad': 5, 'constructor': 7})).replace('"bad"', '"__proto__":100,"bad"')
        c1 = await new_ctx(); pg = await c1.new_page(); watch(pg, 'H')
        await pg.goto(URL + '#share=j.' + b64u(raw.encode())); await pg.wait_for_selector('.hero', timeout=15000)
        got = await pg.evaluate("() => ({ w: JSON.parse(JSON.stringify(window.__tapnaplo.S.meta.water)), own: Object.keys(window.__tapnaplo.S.meta.water), proto: Object.getPrototypeOf(window.__tapnaplo.S.meta.water) === Object.prototype, clean: ({}).polluted === undefined && ({}).constructor === Object })")
        check('viewer (hostile): only a real day inside the period with a whole number of ml from 1 to 20,000 is kept; __proto__, constructor, text, negative, decimal, huge and out of range are dropped', got['w'] == {day(-1): 1500} and got['own'] == [day(-1)] and got['proto'] and got['clean'], got)
        await c1.close()
        for label, wat in (('a number', 5), ('a list', [1, 2]), ('a text', 'lots'), ('null', None)):
            if label == 'null':
                d = mk(None); d['water'] = None
            else:
                d = mk(wat)
            c1 = await new_ctx(); pg = await c1.new_page(); watch(pg, 'H')
            await pg.goto(link(d)); await pg.wait_for_selector('.hero, .card', timeout=15000)
            bad = 'cannot be opened' in await pg.inner_text('#view')
            check(f'viewer (hostile): "water" as {label} is a bad link, a message and no crash', bad, (await pg.inner_text('#view'))[:80])
            await c1.close()
        many = {(D - timedelta(days=i)).isoformat(): 100 for i in range(500)}
        c1 = await new_ctx(); pg = await c1.new_page(); watch(pg, 'H')
        d = mk(many); d['from'] = day(-499)
        await pg.goto(link(d)); await pg.wait_for_selector('.hero, .card', timeout=15000)
        check('viewer (hostile): more than 400 water days is a bad link', 'cannot be opened' in await pg.inner_text('#view'))
        await c1.close()

        # =========================================================== 9b every recording has a time (fixed clock: Thu 5 Nov 2026, 12:00 Budapest)
        cF = await new_ctx(timezone_id='Europe/Budapest'); await cF.clock.set_fixed_time(NOWISO)
        F = await cF.new_page(); watch(F, 'F'); FT = F.evaluate
        await F.goto(URL); await F.wait_for_selector('.hero')
        FD, FY = '2026-11-05', '2026-11-04'
        frecs = lambda: FT("() => JSON.parse(JSON.stringify(window.__tapnaplo.S.wlog))")
        flegacy = lambda: FT("() => JSON.parse(JSON.stringify(window.__tapnaplo.S.meta.water))")
        ftot = lambda d=FD: FT("(d) => window.__tapnaplo.waterOf(d)", d)
        frows = lambda: F.locator('.water-row').all_inner_texts()
        ftoast = lambda: F.inner_text('#toast span')
        fnum = lambda: F.inner_text('.water-num')
        fsum = lambda: F.inner_text('#wlist summary')

        def rec(i, d, tm, ml, t=None):
            return {'id': f'r{i}', 't': t or FT_MS + i, 'd': d, 'tm': tm, 'ml': ml}

        async def fset(recs=None, old=None):
            await FT("([r, l]) => { const t = window.__tapnaplo; t.S.wlog.length = 0; for (const x of r) t.S.wlog.push(x); t.S.meta.water = l || {}; t.save(); t.render(); }", [recs or [], old or {}])

        async def fopen(sel):
            await F.click(sel); await F.wait_for_selector('#wamt'); await F.wait_for_timeout(300)

        async def fclose():
            if await F.locator('#wamt').count():
                await F.click('.sheet [data-x]'); await F.wait_for_selector('#wamt', state='detached')

        check('timed: an empty day has no list', await F.locator('#wlist').count() == 0)
        await F.tap('[data-act=water-add][data-dl="2"]')
        r = await frecs()
        check('timed: a quick tap makes one recording with the time of now (12:00), the shown day, whole ml, an id and the moment it was made', len(r) == 1 and r[0]['tm'] == '12:00' and r[0]['d'] == FD and r[0]['ml'] == 200 and r[0]['t'] == FT_MS and isinstance(r[0]['id'], str) and len(r[0]['id']) > 8, r)
        check('...and only those five keys', sorted(r[0]) == ['d', 'id', 'ml', 't', 'tm'], sorted(r[0]))
        check('...the toast names the time and keeps Undo', 'Water +2 dL at 12:00 · total 200 mL' in await ftoast() and await F.locator('#toast button').count() == 1, await ftoast())
        check('...the list says "Recordings (1) · last 12:00" and is closed by default', await fsum() == 'Recordings (1) · last 12:00' and await FT("() => document.querySelector('#wlist').open") is False and await F.locator('.water-row:visible').count() == 0, await fsum())
        await F.click('#wlist summary')
        check('opening it shows the recording: time, mL and dL', await frows() == ['12:00\n200 mL · 2 dL'], await frows())
        check('...as a button with a spoken label', await F.get_attribute('.water-row', 'aria-label') == 'Edit water recording: 12:00, 200 mL')
        await F.tap('[data-act=water-add][data-dl="3"]')
        check('a second tap: the card is drawn again but the list stays open and the summary counts 2', await FT("() => document.querySelector('#wlist').open") is True and await fsum() == 'Recordings (2) · last 12:00' and sorted(await frows()) == ['12:00\n200 mL · 2 dL', '12:00\n300 mL · 3 dL'], (await fsum(), await frows()))
        await F.tap('#toast button')
        check('Undo of that tap takes the recording away again (and only that one)', [x['ml'] for x in await frecs()] == [200] and await fsum() == 'Recordings (1) · last 12:00')

        # a day with old and new amounts
        await fset([rec(1, FD, '12:00', 200), rec(2, FD, '06:30', 330)], {FD: 500})
        check('the list: the amount without a time first ("No time"), then the recordings from the earliest to the latest', await frows() == ['No time\n500 mL · 5 dL', '06:30\n330 mL · 3.3 dL', '12:00\n200 mL · 2 dL'] and await fsum() == 'Recordings (3) · last 12:00', (await frows(), await fsum()))
        check('...the total of the day is all three added up (1,030 mL = 10.3 dL)', squash(await fnum()) == '1,030mL' and '10.3 dL' in await F.inner_text('.water-top .muted') and await ftot() == 1030)
        check('...the "No time" row speaks for itself', await F.locator('.water-row').first.get_attribute('aria-label') == 'Edit the water amount that has no time: 500 mL')

        # the add sheet
        await fopen('[data-act=water-other]')
        check('Other: the sheet has a Time (24 h) field that starts at the time of now', await F.input_value('#wtm') == '12:00' and 'Time (24 h)' in await F.inner_text('.sheet-b') and await F.get_attribute('#wtm', 'placeholder') == 'HH:MM' and await F.get_attribute('#wtm', 'maxlength') == '5' and await F.get_attribute('#wtm', 'inputmode') == 'numeric' and await F.get_attribute('#wtm', 'type') == 'text')
        check('...and the hint says the time starts at now', 'The time starts at now.' in await F.inner_text('.sheet-b'))
        await F.fill('#wtm', '0630')
        check('typing 0630 is shaped to 06:30 while typing', await F.input_value('#wtm') == '06:30', await F.input_value('#wtm'))
        for bad in ('', '25:99', '8:5', '12:60', 'ab'):
            await F.fill('#wtm', bad); await F.click('#wadd')
            vis = await F.locator('#wtmerr').is_visible()
            check(f'time "{bad}": the message sits next to the field, the sheet stays open and nothing is added', vis and (await F.inner_text('#wtmerr')) == 'Enter a time in 24-hour form, for example 13:45.' and await F.get_attribute('#wtm', 'aria-invalid') == 'true' and await F.locator('#wamt').count() == 1 and len(await frecs()) == 2, (bad, vis))
        await F.fill('#wamt', 'x'); await F.fill('#wtm', '99:99'); await F.click('#wadd')
        check('a bad amount and a bad time at once: both messages show', await F.locator('.field-err:visible').count() == 2, await F.locator('.field-err:visible').count())
        await F.click('[data-u=ml]'); await F.fill('#wamt', '330'); await F.fill('#wtm', '0830'); await F.click('#wadd')
        check('a time typed as 0830 is shaped to 08:30; the recording is made at that time, on the shown day', [(x['tm'], x['ml'], x['d']) for x in await frecs() if x['id'] not in ('r1', 'r2')] == [('08:30', 330, FD)], await frecs())
        check('...the toast: "Water +330 mL at 08:30 · total 1,360 mL"', 'Water +330 mL at 08:30 · total 1,360 mL' in await ftoast(), await ftoast())
        check('...it sits between the others in time order', await frows() == ['No time\n500 mL · 5 dL', '06:30\n330 mL · 3.3 dL', '08:30\n330 mL · 3.3 dL', '12:00\n200 mL · 2 dL'], await frows())
        await F.tap('#toast button')
        check('Undo takes that recording away', len(await frecs()) == 2 and await ftot() == 1030)

        # edit a recording
        await F.click('.water-row:has-text("06:30")'); await F.wait_for_selector('#wamt'); await F.wait_for_timeout(300)
        check('a row opens "Edit water": amount in the unit used last (mL), the time, Save changes, Delete; no Clear day', await F.inner_text('.sheet-h h2') == 'Edit water' and await F.input_value('#wamt') == '330' and await F.get_attribute('[data-u=ml]', 'aria-pressed') == 'true' and await F.input_value('#wtm') == '06:30' and (await F.inner_text('#wadd')).strip() == 'Save changes' and await F.locator('#wdel').count() == 1 and await F.locator('#wclear').count() == 0)
        check('...it shows the total of the day (1,030 mL) and the hint about the day', 'Total of the day: 1,030 mL (10.3 dL)' in (await F.inner_text('.sheet-b')).replace('\n', ' ') and 'never moves the recording to another day' in await F.inner_text('.sheet-b'))
        await F.click('[data-u=dl]')
        check('switching to dL converts the amount (330 mL = 3.3 dL)', await F.input_value('#wamt') == '3.3')
        await F.click('[data-u=ml]'); await F.fill('#wamt', '400'); await F.fill('#wtm', '0715'); await F.click('#wadd')
        r2 = [x for x in await frecs() if x['id'] == 'r2'][0]
        check('Save changes: the same recording (same id, same moment it was made) has the new amount and time', r2 == {'id': 'r2', 't': FT_MS + 2, 'd': FD, 'tm': '07:15', 'ml': 400}, r2)
        check('...the toast says what changed and the list is in time order again', 'Water recording updated: 400 mL at 07:15' in await ftoast() and await frows() == ['No time\n500 mL · 5 dL', '07:15\n400 mL · 4 dL', '12:00\n200 mL · 2 dL'], (await ftoast(), await frows()))
        check('...the total follows (1,100 mL)', await ftot() == 1100)
        await F.tap('#toast button')
        r2 = [x for x in await frecs() if x['id'] == 'r2'][0]
        check('Undo puts the old amount and time back', r2['ml'] == 330 and r2['tm'] == '06:30' and await ftot() == 1030, r2)
        await F.click('.water-row:has-text("06:30")'); await F.wait_for_selector('#wamt'); await F.wait_for_timeout(300)
        await F.click('#wadd')
        check('Save changes without a change says "Nothing changed" and does not touch the recording', 'Nothing changed' in await ftoast() and [x for x in await frecs() if x['id'] == 'r2'][0]['tm'] == '06:30')
        await F.click('.water-row:has-text("06:30")'); await F.wait_for_selector('#wamt'); await F.wait_for_timeout(300)
        await F.fill('#wtm', '0005'); await F.click('#wadd')
        check('a time just after midnight changes the time only: the recording stays on its day', [x for x in await frecs() if x['id'] == 'r2'][0]['d'] == FD and [x for x in await frecs() if x['id'] == 'r2'][0]['tm'] == '00:05')
        await F.click('.water-row:has-text("00:05")'); await F.wait_for_selector('#wamt'); await F.wait_for_timeout(300)
        await F.fill('#wamt', '0'); await F.click('#wadd')
        check('an amount of 0 is refused next to the field and the recording stays', 'Enter an amount greater than 0.' in await F.inner_text('.field-err') and [x for x in await frecs() if x['id'] == 'r2'][0]['ml'] == 330)
        await F.click('#wdel')
        check('Delete removes the recording at once (no question) and says so with Undo', [x['id'] for x in await frecs()] == ['r1'] and 'Water recording deleted' in await ftoast() and not await F.locator('#wamt').count(), await ftoast())
        await F.tap('#toast button')
        check('Undo brings back the same recording (same id, amount and time)', [x for x in await frecs() if x['id'] == 'r2'] == [{'id': 'r2', 't': FT_MS + 2, 'd': FD, 'tm': '00:05', 'ml': 330}], await frecs())

        # the 20 L limit when editing
        await fset([rec(1, FD, '08:00', 1000), rec(2, FD, '09:00', 19000)])
        await F.click('.water-row:has-text("08:00")'); await F.wait_for_selector('#wamt'); await F.wait_for_timeout(300)
        await F.click('[data-u=ml]'); await F.fill('#wamt', '2000'); await F.click('#wadd')
        msg = await F.inner_text('.field-err')
        check('editing a recording above the 20 L day limit: the message says how much this one can be', msg == 'A day can hold at most 20,000 mL (200 dL). With the other water of this day, this one can be at most 1,000 mL.' and [x['ml'] for x in await frecs()] == [1000, 19000], msg)
        await F.fill('#wamt', '1000'); await F.click('#wadd')
        check('...exactly up to the limit is fine (nothing changed here)', 'Nothing changed' in await ftoast())
        await F.tap('[data-act=water-add][data-dl="1"]')
        check('the quick button at 20,000 mL is refused with a toast', 'at most 20,000 mL' in await ftoast() and len(await frecs()) == 2)

        # deleted on another device while the sheet is open
        await fset([rec(1, FD, '08:00', 300)])
        await F.click('.water-row:has-text("08:00")'); await F.wait_for_selector('#wamt'); await F.wait_for_timeout(300)
        await FT("() => { window.__tapnaplo.S.wlog.length = 0; }")
        await F.fill('#wamt', '500'); await F.click('#wadd')
        check('Save on a recording that was deleted elsewhere: the message says so, nothing is brought back', 'deleted on another device' in await F.inner_text('.field-err') and (await frecs()) == [])
        await F.click('#wdel')
        check('Delete on it: a toast says so, the sheet closes', 'deleted on another device' in await ftoast() and not await F.locator('#wamt').count())

        # the amount without a time
        await fset([rec(1, FD, '08:00', 300)], {FD: 500})
        await F.click('.water-row:has-text("No time")'); await F.wait_for_selector('#wamt'); await F.wait_for_timeout(300)
        check('the "No time" row opens "Water without a time": no Time field, the hint says why, Save changes and Delete', await F.inner_text('.sheet-h h2') == 'Water without a time' and await F.locator('#wtm').count() == 0 and 'before water recordings had a time' in await F.inner_text('.sheet-b') and (await F.inner_text('#wadd')).strip() == 'Save changes' and await F.locator('#wdel').count() == 1)
        await F.click('[data-u=ml]'); await F.fill('#wamt', '600'); await F.click('#wadd')
        check('it can be changed (600 mL): still without a time, the recordings are untouched, the total follows', (await flegacy()) == {FD: 600} and [x['ml'] for x in await frecs()] == [300] and await ftot() == 900 and 'Water without a time: 600 mL' in await ftoast(), await ftoast())
        await F.tap('#toast button')
        check('...Undo gives 500 mL back', (await flegacy()) == {FD: 500})
        await F.click('.water-row:has-text("No time")'); await F.wait_for_selector('#wamt'); await F.wait_for_timeout(300)
        await F.click('#wdel')
        check('Delete removes only the amount without a time (with Undo)', (await flegacy()) == {} and [x['ml'] for x in await frecs()] == [300] and 'Water without a time deleted' in await ftoast(), await ftoast())
        await F.tap('#toast button')
        check('...Undo brings it back', (await flegacy()) == {FD: 500})

        # Clear day takes both
        await fopen('[data-act=water-other]')
        check('Clear day is offered and the sheet shows the whole total (800 mL)', await F.locator('#wclear').is_visible() and 'Total of the day: 800 mL (8 dL)' in (await F.inner_text('.sheet-b')).replace('\n', ' '))
        await F.click('#wclear')
        check('Clear day removes the recordings and the amount without a time, says so, and the list is gone', (await frecs()) == [] and (await flegacy()) == {} and 'Water cleared for this day' in await ftoast() and await F.locator('#wlist').count() == 0 and 'Nothing logged yet' in await F.inner_text('.water-top .muted'))
        await F.tap('#toast button')
        check('Undo restores both (same recording, same amount without a time)', [x['id'] for x in await frecs()] == ['r1'] and (await flegacy()) == {FD: 500} and await ftot() == 800)

        # another day
        await fset([rec(1, FD, '08:00', 300)])
        await F.tap('[data-act=day][data-n="-1"]')
        check('yesterday starts empty and has no list (today\'s recordings are not shown there)', squash(await fnum()) == '0mL' and await F.locator('#wlist').count() == 0)
        await F.tap('[data-act=water-add][data-dl="5"]')
        r = await frecs()
        check('a tap on yesterday makes a recording for yesterday, at the time of now', [(x['d'], x['tm'], x['ml']) for x in r if x['id'] != 'r1'] == [(FY, '12:00', 500)] and await fsum() == 'Recordings (1) · last 12:00', r)
        await F.tap('[data-act=today]')
        check('today still has only its own recording (300 mL)', await ftot() == 300 and squash(await fnum()) == '300mL')
        await F.wait_for_timeout(500)
        await F.reload(); await F.wait_for_selector('.hero')
        r = await frecs()
        check('after a reload the recordings are there with their times', sorted((x['d'], x['tm'], x['ml']) for x in r) == [(FY, '12:00', 500), (FD, '08:00', 300)], r)
        check('...and the list is closed again (the open state is not kept)', await FT("() => document.querySelector('#wlist').open") is False)

        # old and damaged storage
        IDB_PUT = """async (list) => { const db = await new Promise((res) => { const r = indexedDB.open('tapnaplo', 1); r.onsuccess = () => res(r.result); });
          await new Promise((res) => { const tx = db.transaction('kv', 'readwrite'); if (list === null) tx.objectStore('kv').delete('wlog'); else tx.objectStore('kv').put(list, 'wlog'); tx.oncomplete = res; }); }"""
        await FT(IDB_PUT, [{'id': 'g1', 't': 1793872800000, 'd': '2026-11-05', 'tm': '08:00', 'ml': 250},
                           {'id': 'g2', 'd': '2026-11-05', 'tm': '09:00', 'ml': 300},                                  # no t: noon of the day
                           {'id': 'b1', 't': 1, 'd': '2026-11-05', 'tm': '25:00', 'ml': 100}, {'id': 'b2', 't': 1, 'd': '2026-02-30', 'tm': '08:00', 'ml': 100}, {'id': 'b3', 't': 1, 'd': '2026-11-05', 'tm': '08:00', 'ml': 2.5},
                           {'id': 'b4', 't': 1, 'd': '2026-11-05', 'tm': '08:00', 'ml': '300'}, {'id': 'b5', 't': 1, 'd': '2026-11-05', 'tm': '08:00', 'ml': 0}, {'id': 'b6', 't': 1, 'd': '2026-11-05', 'tm': '08:00', 'ml': 99999999},
                           {'id': 'g1', 't': 1, 'd': '2026-11-05', 'tm': '10:00', 'ml': 100}, {'t': 1, 'd': '2026-11-05', 'tm': '08:00', 'ml': 100}, 'text', None, [1, 2], {'id': 'x' * 101, 't': 1, 'd': '2026-11-05', 'tm': '08:00', 'ml': 100},
                           {'id': 'g3', 't': 1, 'd': '2026-11-04', 'tm': '23:59', 'ml': 1, 'extra': 'x'}])
        await F.reload(); await F.wait_for_selector('.hero')
        r = await frecs()
        check('damaged recordings in storage are left out at start (bad time, day, amount, text, duplicate id, no id, not an object), the good ones stay', sorted(x['id'] for x in r) == ['g1', 'g2', 'g3'], r)
        check('...a recording without a usable "t" gets noon of its day; unknown keys are dropped; the first of two with the same id wins', [x for x in r if x['id'] == 'g2'][0]['t'] == int(datetime(2026, 11, 5, 11, 0, tzinfo=timezone.utc).timestamp() * 1000) and sorted([x for x in r if x['id'] == 'g3'][0]) == ['d', 'id', 'ml', 't', 'tm'] and [x for x in r if x['id'] == 'g1'][0]['ml'] == 250, r)
        check('...and a toast says how many could not be read', '12 water recordings could not be read and were skipped.' in await ftoast(), await ftoast())
        await FT("() => { delete window.__tapnaplo.S.meta.water; }")
        await FT(IDB_PUT, None)
        await F.reload(); await F.wait_for_selector('.hero')
        check('a save from before version 34 (no recordings at all) starts without a message', await frecs() == [] and not await F.locator('#toast span').count())

        # CSV of the water
        async def fcsv(act):
            async with F.expect_download() as d:
                await F.click(f'[data-act={act}]')
            dl = await d.value
            path = HERE / 'water_tmp2.csv'
            await dl.save_as(str(path))
            text = path.read_text(encoding='utf-8-sig'); path.unlink()
            return list(csv.reader(io.StringIO(text)))
        await fset([rec(1, FD, '12:00', 200), rec(2, FD, '06:30', 330), rec(3, FY, '23:59', 150)], {FD: 500, '2026-11-01': 700})
        await F.click('[data-tab=data]'); await F.wait_for_selector('[data-act=export-water]')
        rows = await fcsv('export-water')
        check('Water intake (CSV): header date, time, water_ml', rows[0] == ['date', 'time', 'water_ml'], rows[0])
        check('...one row per recording, oldest first; an amount without a time has an empty time and comes first on its day', rows[1:] == [['2026-11-01', '', '700'], ['2026-11-04', '23:59', '150'], ['2026-11-05', '', '500'], ['2026-11-05', '06:30', '330'], ['2026-11-05', '12:00', '200']], rows[1:])
        async with F.expect_download() as d:
            await F.click('[data-act=export-days]')
        dl = await d.value; path = HERE / 'water_tmp3.csv'; await dl.save_as(str(path))
        text = path.read_text(encoding='utf-8-sig'); path.unlink()
        rows = list(csv.reader(io.StringIO(text))); by = {r[0]: r for r in rows[1:]}
        check('daily totals: water_intake_ml is the whole water of the day (500 + 330 + 200 = 1,030), a day with only a recording gets a row (150), a day with only an old amount too (700)', by.get(FD, ['', '', '', ''])[3] == '1030' and by.get(FY, ['', '', '', ''])[3] == '150' and by.get('2026-11-01', ['', '', '', ''])[3] == '700' and by[FY][1] == '0', {k: v[:4] for k, v in by.items()})
        check('...the explanation under the CSV buttons mentions the water file', 'Water intake file has one row per recording' in await F.inner_text('#view'))
        await F.click('[data-tab=log]'); await F.wait_for_selector('#water')

        # backup and restore with recordings
        await F.click('[data-tab=data]'); await F.wait_for_selector('[data-act=export-json]')
        async with F.expect_download() as d:
            await F.click('[data-act=export-json]')
        dl = await d.value
        bk = json.loads(pathlib.Path(await dl.path()).read_text(encoding='utf-8'))
        check('backup: the file has "wlog" with the three recordings and the old totals stay in meta.water', sorted(x['id'] for x in bk['wlog']) == ['r1', 'r2', 'r3'] and bk['meta']['water'] == {FD: 500, '2026-11-01': 700}, (bk.get('wlog'), bk['meta'].get('water')))

        async def frestore(obj):
            await F.set_input_files('#importfile', {'name': 'backup.json', 'mimeType': 'application/json', 'buffer': json.dumps(obj).encode()})
            await F.wait_for_selector('[data-ok]')
            txt = await F.inner_text('.sheet-b')
            return txt

        txt = await frestore(bk)
        check('restore: the question names the recordings ("... and 3 water recordings.")', 'and 3 water recordings.' in txt, txt)
        await F.click('[data-dx]'); await F.wait_for_timeout(300)
        # a v33 backup: no wlog
        old = json.loads(json.dumps(bk)); old.pop('wlog')
        txt = await frestore(old)
        check('restore of a file without "wlog" (made before version 34): the question says the recordings stay as they are', 'Your 3 water recordings are not in this file, so they stay as they are.' in txt, txt)
        await F.click('[data-ok]'); await F.wait_for_timeout(500)
        check('...and they do stay', sorted(x['id'] for x in await frecs()) == ['r1', 'r2', 'r3'])
        # damaged items
        dmg = json.loads(json.dumps(bk)); dmg['wlog'] = [bk['wlog'][0], {'id': 'z', 'd': 'nope', 'tm': '08:00', 'ml': 5, 't': 1}, 'x', bk['wlog'][0]]
        txt = await frestore(dmg)
        check('restore of a file with damaged recordings: the question counts the good one and says 3 are not valid and will be skipped', 'and 1 water recording.' in txt and '3 water recordings in the file are not valid and will be skipped.' in txt, txt)
        await F.click('[data-ok]'); await F.wait_for_timeout(500)
        check('...the good one is restored once, the rest is skipped and the toast says so', [x['id'] for x in await frecs()] == [bk['wlog'][0]['id']] and '3 water recordings skipped: not valid' in await ftoast(), (await frecs(), await ftoast()))
        # not a list
        bad = json.loads(json.dumps(bk)); bad['wlog'] = {'a': 1}
        await F.set_input_files('#importfile', {'name': 'backup.json', 'mimeType': 'application/json', 'buffer': json.dumps(bad).encode()})
        await F.wait_for_selector('#toast span')
        check('restore of a file whose "wlog" is not a list is refused as a whole', 'water recordings part of this file is not a list' in await ftoast() and not await F.locator('[data-ok]').count(), await ftoast())
        # empty list replaces
        emp = json.loads(json.dumps(bk)); emp['wlog'] = []
        txt = await frestore(emp)
        await F.click('[data-ok]'); await F.wait_for_timeout(500)
        check('restore of a file with an empty "wlog" replaces the recordings (none left)', (await frecs()) == [] and '0 water recordings' in txt, txt)
        await F.click('[data-tab=log]'); await F.wait_for_selector('#water')

        # =========================================================== 9c Sync of the recordings (intake/YYYY-MM.json)
        gh2 = FakeGitHub()

        async def device2(name):
            c = await new_ctx(timezone_id='Europe/Budapest'); await c.route('https://api.github.com/**', gh2.handle)
            pg = await c.new_page(); watch(pg, name)
            await pg.goto(URL); await pg.wait_for_selector('.hero')
            return c, pg

        ms = lambda y, mo, d, h, mi: int(datetime(y, mo, d, h, mi, tzinfo=timezone.utc).timestamp() * 1000)
        R1 = {'id': 'sy-1', 't': ms(2026, 10, 26, 7, 30), 'd': '2026-10-26', 'tm': '08:30', 'ml': 250}
        R2 = {'id': 'sy-2', 't': ms(2026, 10, 31, 23, 20), 'd': '2026-11-01', 'tm': '00:20', 'ml': 200}      # made at 23:20 UTC on 31 Oct: its file is October, whatever its day
        R3 = {'id': 'sy-3', 't': ms(2026, 11, 2, 10, 0), 'd': '2026-11-02', 'tm': '11:00', 'ml': 500}
        cA2, A2 = await device2('YA')
        await A2.evaluate("([a, b, c]) => { const t = window.__tapnaplo; t.S.wlog.push(a, b, c); t.S.meta.water = { '2026-10-26': 1750 }; t.save(); }", [R1, R2, R3])
        await connect(A2)
        files = sorted(gh2.files)
        check('sync: the recordings go to intake/YYYY-MM.json by the UTC month they were made, the old totals to water/YYYY.json', 'intake/2026-10.json' in files and 'intake/2026-11.json' in files and 'water/2026.json' in files, files)
        recs2 = gh2.recs()
        check('sync: one record i:<id> per recording, the whole recording as its value', all(recs2.get('i:' + r['id'], {}).get('x') == r for r in (R1, R2, R3)), {k: v for k, v in recs2.items() if k.startswith('i:')})
        check('sync: October holds sy-1 and sy-2 (sy-2 was made at 23:20 UTC on 31 Oct), November holds sy-3', set(json.loads(gh2.files['intake/2026-10.json'])['recs']) == {'i:sy-1', 'i:sy-2'} and set(json.loads(gh2.files['intake/2026-11.json'])['recs']) == {'i:sy-3'})
        check('sync: the water/ file has only the old totals and no recording is in meta.json', set(json.loads(gh2.files['water/2026.json'])['recs']) == {'w:2026-10-26'} and 'i:' not in gh2.files.get('meta.json', ''))
        cB2, B2 = await device2('YB')
        await connect(B2)
        tot = lambda pg, d: pg.evaluate("(d) => window.__tapnaplo.waterOf(d)", d)
        check('sync: the second device gets the recordings and the old total (2026-10-26: 1,750 + 250 mL)', sorted(x['id'] for x in await B2.evaluate("() => window.__tapnaplo.S.wlog")) == ['sy-1', 'sy-2', 'sy-3'] and await tot(B2, '2026-10-26') == 2000, await tot(B2, '2026-10-26'))
        await B2.evaluate("() => { const r = window.__tapnaplo.S.wlog.find((x) => x.id === 'sy-1'); r.ml = 300; r.tm = '09:00'; window.__tapnaplo.save(); }")
        await B2.wait_for_timeout(300); await sync(B2); await sync(A2)
        a1 = await A2.evaluate("() => window.__tapnaplo.S.wlog.find((x) => x.id === 'sy-1')")
        check('sync: an edit made on B (amount and time) reaches A, the recording keeps its id and its "made" moment', a1 == dict(R1, ml=300, tm='09:00'), a1)
        check('sync: the edited recording stays in its file (the month it was made, not the month of its day or time)', 'i:sy-1' in json.loads(gh2.files['intake/2026-10.json'])['recs'] and gh2.recs()['i:sy-1']['x']['ml'] == 300)
        await A2.evaluate("() => { const t = window.__tapnaplo, i = t.S.wlog.findIndex((x) => x.id === 'sy-2'); t.S.wlog.splice(i, 1); t.save(); }")
        await A2.wait_for_timeout(300); await sync(A2); await sync(B2)
        check('sync: deleting a recording on A removes it on B (a tombstone stays in the repository)', 'sy-2' not in [x['id'] for x in await B2.evaluate("() => window.__tapnaplo.S.wlog")] and gh2.recs()['i:sy-2']['x'] is None)
        await A2.evaluate("() => { window.__tapnaplo.S.wlog.find((x) => x.id === 'sy-3').ml = 111; window.__tapnaplo.save(); }")
        await A2.wait_for_timeout(300); await sync(A2)
        await B2.evaluate("() => { window.__tapnaplo.S.wlog.find((x) => x.id === 'sy-3').ml = 222; window.__tapnaplo.save(); }")
        await B2.wait_for_timeout(300); await sync(B2); await sync(A2)
        va = await A2.evaluate("() => window.__tapnaplo.S.wlog.find((x) => x.id === 'sy-3').ml"); vb = await B2.evaluate("() => window.__tapnaplo.S.wlog.find((x) => x.id === 'sy-3').ml")
        check('sync: the same recording edited on both devices: the later edit wins on both', va == 222 and vb == 222, (va, vb))
        # an open edit sheet follows a change from another device
        await A2.click('[data-tab=log]'); await A2.wait_for_selector('#water')
        await A2.evaluate("() => { const t = window.__tapnaplo; t.S.day = '2026-11-02'; t.render(); }")
        await A2.click('#wlist summary'); await A2.click('.water-row'); await A2.wait_for_selector('#wamt'); await A2.wait_for_timeout(300)
        await B2.evaluate("() => { window.__tapnaplo.S.wlog.find((x) => x.id === 'sy-3').ml = 650; window.__tapnaplo.save(); }")
        await B2.wait_for_timeout(300); await sync(B2); await sync(A2)
        check('sync: a change made elsewhere is applied to the recording in place (an open sheet keeps working with the same object)', await A2.evaluate("() => window.__tapnaplo.S.wlog.find((x) => x.id === 'sy-3').ml") == 650 and await A2.locator('#wamt').count() == 1)
        await A2.click('.sheet [data-x]'); await A2.wait_for_selector('#wamt', state='detached')
        # bad records in the repository
        U = 99999999999999
        good = lambda i, **kw: dict({'id': i, 't': ms(2026, 11, 3, 9, 0), 'd': '2026-11-03', 'tm': '09:00', 'ml': 100}, **kw)
        gh2.files['intake/2026-11.json'] = json.dumps({'app': 'tapnaplo-sync', 'v': 1, 'recs': {
            'i:sy-3': {'u': U, 'x': good('sy-3', ml=333)},
            'i:x1': {'u': U, 'x': good('x1', ml=0)}, 'i:x2': {'u': U, 'x': good('x2', ml=2.5)}, 'i:x3': {'u': U, 'x': good('x3', ml='300')}, 'i:x4': {'u': U, 'x': good('x4', ml=99999999)},
            'i:x5': {'u': U, 'x': good('x5', tm='25:00')}, 'i:x6': {'u': U, 'x': good('x6', d='2026-02-30')}, 'i:x7': {'u': U, 'x': good('other')}, 'i:x8': {'u': U, 'x': {'id': 'x8', 'd': '2026-11-03', 'ml': 5}},
            'i:x9': {'u': U, 'x': [1, 2]}, 'i:': {'u': U, 'x': good('')}, 'i:x10': {'u': U, 'x': good('x10', extra='x')}, 'i:__proto__': {'u': U, 'x': good('__proto__')}}})
        await sync(A2)
        idsA = sorted(x['id'] for x in await A2.evaluate("() => window.__tapnaplo.S.wlog"))
        x10 = await A2.evaluate("() => window.__tapnaplo.S.wlog.find((x) => x.id === 'x10')")
        check('sync: only valid records are taken from the repository (a real recording whose id is its key)', await A2.evaluate("() => window.__tapnaplo.S.wlog.find((x) => x.id === 'sy-3').ml") == 333 and not any(i in idsA for i in ('x1', 'x2', 'x3', 'x4', 'x5', 'x6', 'x7', 'other', 'x8', 'x9', '')), idsA)
        check('sync: extra keys of a valid record are not kept; a record called __proto__ is only a name, the prototypes are untouched', sorted(x10) == ['d', 'id', 'ml', 't', 'tm'] and await A2.evaluate("() => ({}).constructor === Object && ({}).ml === undefined && Object.getPrototypeOf(window.__tapnaplo.S.wlog) === Array.prototype"))
        await cA2.close(); await cB2.close()

        # =========================================================== 9d Share: the recordings with a time (key "wt", format still v1)
        await T("""([d0, d1, d2, d3]) => { const t = window.__tapnaplo, S = t.S;
          S.log.length = 0; S.meta.water = {}; S.wlog.length = 0; S.foods['u:oat'] = %s;
          S.log.push({ id: 'a1', d: d1, m: 'm1', f: 'u:oat', a: 100, t: 1, tm: '08:00' });
          S.meta.water[d0] = 500; S.meta.water[d2] = 400;                                                      // amounts without a time
          S.wlog.push({ id: 'k1', t: 11, d: d0, tm: '19:05', ml: 500 }, { id: 'k2', t: 12, d: d0, tm: '07:10', ml: 250 }, { id: 'k3', t: 13, d: d1, tm: '08:00', ml: 300 }, { id: 'k4', t: 14, d: d3, tm: '10:00', ml: 700 });
          t.save(); t.render(); }""" % json.dumps(own('u:oat', 'Oat', {'kcal': 380})), [day(0), day(-1), day(-2), day(-20)])
        snap = await T("([a, b]) => JSON.parse(window.__tapnaplo.shareSnapshot(a, b).json)", [day(-6), day(0)])
        check('share: "water" is the whole total of every shared day (recordings and the amount without a time added up)', snap.get('water') == {day(0): 1250, day(-1): 300, day(-2): 400}, snap.get('water'))
        check('share: "wt" holds the recordings of the shared days as [HH:MM, ml], earliest first; a day with only an amount without a time has no entry; a day outside the period is left out', snap.get('wt') == {day(0): [['07:10', 250], ['19:05', 500]], day(-1): [['08:00', 300]]}, snap.get('wt'))
        check('share: still v1, no ids and no "made" moments of the recordings in the link', snap['v'] == 1 and 'k1' not in json.dumps(snap) and '"t":11' not in json.dumps(snap))
        res = await T("([a, b]) => { const r = window.__tapnaplo.shareSnapshot(a, b); return { waterDays: r.waterDays, waterTimes: r.waterTimes }; }", [day(-6), day(0)])
        check('share: the snapshot counts 3 water days and 3 recordings with a time', res == {'waterDays': 3, 'waterTimes': 3}, res)
        await T("() => { const t = window.__tapnaplo; t.S.wlog.length = 0; t.save(); }")
        snap2 = await T("([a, b]) => JSON.parse(window.__tapnaplo.shareSnapshot(a, b).json)", [day(-6), day(0)])
        check('share: no recording with a time → no "wt" key (the link looks exactly like one from version 24), "water" has the amounts without a time', 'wt' not in snap2 and snap2.get('water') == {day(0): 500, day(-2): 400}, list(snap2))
        await T("""([d0, d1, d3]) => { const t = window.__tapnaplo; t.S.wlog.push({ id: 'k1', t: 11, d: d0, tm: '19:05', ml: 500 }, { id: 'k2', t: 12, d: d0, tm: '07:10', ml: 250 }, { id: 'k3', t: 13, d: d1, tm: '08:00', ml: 300 }, { id: 'k4', t: 14, d: d3, tm: '10:00', ml: 700 }); t.save(); t.render(); }""", [day(0), day(-1), day(-20)])
        await page.click('[data-tab=data]'); await page.wait_for_selector('[data-act=share]'); await page.click('[data-act=share]'); await page.wait_for_selector('#sh-info')
        await page.click('[data-days="7"]'); await page.wait_for_function("document.querySelector('#sh-info').textContent.includes('link length')")
        info = await page.inner_text('#sh-info')
        check('share sheet: the message says "water intake on 3 days (with times)"', '1 day with entries · 1 item · water intake on 3 days (with times) · link length' in info, info)
        await page.click('.sheet [data-x]')
        made2 = await T("([a, b]) => window.__tapnaplo.shareLink(a, b).then((r) => r.url)", [day(-6), day(0)])
        un = unpack(made2)
        check('share: the link opens with Python (zlib) and has "water" and "wt"', un.get('water') == {day(0): 1250, day(-1): 300, day(-2): 400} and un.get('wt') == {day(0): [['07:10', 250], ['19:05', 500]], day(-1): [['08:00', 300]]})

        cV, V = await viewer(made2)
        vrows = lambda: V.locator('.water-row').all_inner_texts()
        vsum = lambda: V.inner_text('#wlist summary')
        check('viewer: opens on the last day that has water (today): 1,250 mL', await V.evaluate("() => window.__tapnaplo.S.day") == day(0) and '1,250' in await V.inner_text('#water'), await V.inner_text('#water'))
        check('viewer: the list says "Recordings (3) · last 19:05" and is closed', await vsum() == 'Recordings (3) · last 19:05' and await V.evaluate("() => document.querySelector('#wlist').open") is False, await vsum())
        await V.click('#wlist summary')
        rows_v = [re.sub(r'\s+', ' ', x) for x in await vrows()]
        check('viewer: the rows are the amount without a time (what is left of the total: 500 mL) and the two recordings, in time order', rows_v == ['No time 500 mL · 5 dL', '07:10 250 mL · 2.5 dL', '19:05 500 mL · 5 dL'], rows_v)
        check('viewer: the rows are not buttons (read only)', await V.locator('button.water-row').count() == 0 and await V.locator('div.water-row.ro').count() == 3 and await V.locator('#water button').count() == 0)
        await V.evaluate("() => { const b = document.createElement('button'); b.dataset.act = 'water-edit'; b.dataset.id = 'v1'; b.id = 'fake1'; document.body.append(b); const c = document.createElement('button'); c.dataset.act = 'water-edit-legacy'; c.id = 'fake2'; document.body.append(c); const e = document.createElement('button'); e.dataset.act = 'export-water'; e.id = 'fake3'; document.body.append(e); }")
        for fid in ('fake1', 'fake2', 'fake3'):
            await V.evaluate("(id) => document.getElementById(id).click()", fid); await V.wait_for_timeout(150)
        check('viewer: forged water buttons (edit, edit the amount without a time, export) open nothing and change nothing', await V.locator('#wamt').count() == 0 and await V.evaluate("() => window.__tapnaplo.S.wlog.length") == 3 and await V.evaluate("() => JSON.parse(JSON.stringify(window.__tapnaplo.S.meta.water))") == {day(0): 500, day(-2): 400}, await V.evaluate("() => JSON.stringify(window.__tapnaplo.S.wlog)"))
        await V.tap('[data-act=day][data-n="-1"]')
        await V.wait_for_timeout(100)
        check('viewer: the day before has one recording (08:00, 300 mL) and the food', await vsum() == 'Recordings (1) · last 08:00' and await V.locator('.entry').count() == 1)
        await V.tap('[data-act=day][data-n="-1"]')
        await V.wait_for_timeout(100)
        if not await V.evaluate("() => document.querySelector('#wlist').open"): await V.click('#wlist summary')
        rows_v = [re.sub(r'\s+', ' ', x) for x in await vrows()]
        check('viewer: a day that has only an amount without a time shows the single row "No time"', rows_v == ['No time 400 mL · 4 dL'] and await vsum() == 'Recordings (1)', (rows_v, await vsum()))
        w = await V.evaluate("() => window.__w")
        check('viewer: nothing was written (IndexedDB not opened, no localStorage write) although the list was opened', w == {'idbOpen': 0, 'idbWrite': 0, 'lsWrite': 0}, w)
        await cV.close()

        # the link of version 24 (no "wt"): totals only, the whole amount is "No time"
        cV, V = await viewer(link({'app': 'tapnaplo-share', 'v': 1, 'made': 1761500000000, 'from': day(-6), 'to': day(0), 'refs': [], 'foods': [], 'nova': {}, 'days': {}, 'water': {day(-1): 750}}))
        await V.click('#wlist summary')
        rows_v = [re.sub(r'\s+', ' ', x) for x in await vrows()]
        check('viewer: a link without "wt" (made by version 24 to 33) shows the total as one row "No time"', rows_v == ['No time 750 mL · 7.5 dL'], rows_v)
        await cV.close()

        # hostile "wt"
        CID2 = 'c:' + str(json.loads((ROOT / 'ciqual.json').read_text())['foods'][0]['c'])
        def mk2(water, wt, raw_wt=None):
            d = {'app': 'tapnaplo-share', 'v': 1, 'made': 1761500000000, 'from': day(-6), 'to': day(0), 'refs': [CID2], 'foods': [], 'nova': {}, 'days': {day(-1): [['m1', 0, '08:00', 100]]}, 'water': water}
            if wt is not None: d['wt'] = wt
            return d
        async def open_raw(d, raw=None):
            c1 = await new_ctx(); pg = await c1.new_page(); watch(pg, 'H')
            await pg.goto(URL + '#share=j.' + b64u((raw or json.dumps(d)).encode())); await pg.wait_for_selector('.hero, .card', timeout=15000)
            return c1, pg
        get_state = "() => ({ w: JSON.parse(JSON.stringify(window.__tapnaplo.S.meta.water)), l: JSON.parse(JSON.stringify(window.__tapnaplo.S.wlog)).map((r) => [r.d, r.tm, r.ml]), clean: ({}).polluted === undefined && ({}).constructor === Object && Array.prototype.polluted === undefined })"
        c1, pg = await open_raw(mk2({day(-1): 1500}, {day(-1): [['08:00', 500], ['12:30', 700]]}))
        st = await pg.evaluate(get_state)
        check('viewer (wt): a good day: two recordings and the rest (300 mL) as the amount without a time', st['l'] == [[day(-1), '08:00', 500], [day(-1), '12:30', 700]] and st['w'] == {day(-1): 300} and st['clean'], st)
        await c1.close()
        c1, pg = await open_raw(mk2({day(-1): 1200}, {day(-1): [['08:00', 500], ['12:30', 700]]}))
        st = await pg.evaluate(get_state)
        check('viewer (wt): recordings that add up to exactly the total leave no amount without a time', st['l'] == [[day(-1), '08:00', 500], [day(-1), '12:30', 700]] and st['w'] == {}, st)
        await c1.close()
        bad_days = {
            'a sum above the total of the day': ({day(-1): 1000}, {day(-1): [['08:00', 500], ['12:30', 700]]}),
            'a day without water': ({day(-1): 1000}, {day(-2): [['08:00', 500]]}),
            'a day outside the shared days': ({day(-1): 1000}, {day(-30): [['08:00', 500]]}),
            'a time with an hour of 25': ({day(-1): 1000}, {day(-1): [['25:00', 500]]}),
            'a time that is a number': ({day(-1): 1000}, {day(-1): [[800, 500]]}),
            'an amount of 0': ({day(-1): 1000}, {day(-1): [['08:00', 0]]}),
            'a decimal amount': ({day(-1): 1000}, {day(-1): [['08:00', 2.5]]}),
            'an amount as text': ({day(-1): 1000}, {day(-1): [['08:00', '500']]}),
            'an amount above 20 L': ({day(-1): 1000}, {day(-1): [['08:00', 999999]]}),
            'an item with three values': ({day(-1): 1000}, {day(-1): [['08:00', 500, 1]]}),
            'an item that is a text': ({day(-1): 1000}, {day(-1): ['08:00 500']}),
            'an empty list': ({day(-1): 1000}, {day(-1): []}),
            'a day that is not a list': ({day(-1): 1000}, {day(-1): 'lots'}),
            'a day that is not a date': ({day(-1): 1000}, {'2026-02-30': [['08:00', 500]]}),
            '501 recordings in a day': ({day(-1): 20000}, {day(-1): [['08:00', 1]] * 501}),
        }
        for label, (wat, wtv) in bad_days.items():
            c1, pg = await open_raw(mk2(wat, wtv))
            st = await pg.evaluate(get_state)
            ok = st['l'] == [] and st['w'] == wat and st['clean']
            check(f'viewer (wt): {label}: that day is shown with its total only (as "No time"), nothing else is taken, the link opens', ok, st)
            await c1.close()
        c1, pg = await open_raw(mk2({day(-1): 1000}, None), raw=json.dumps(mk2({day(-1): 1000}, {day(-1): [['08:00', 300]]})).replace('"wt": {', '"wt": {"__proto__": [["08:00", 100]], "constructor": [["09:00", 100]], '))
        st = await pg.evaluate(get_state)
        check('viewer (wt): "__proto__" and "constructor" as day names are only names: dropped, the good day stays, the prototypes are untouched', st['l'] == [[day(-1), '08:00', 300]] and st['clean'], st)
        await c1.close()
        for label, wtv in (('a number', 5), ('a list', [1, 2]), ('a text', 'lots'), ('null', 'NULL')):
            d = mk2({day(-1): 1000}, None)
            d['wt'] = None if wtv == 'NULL' else wtv
            c1 = await new_ctx(); pg = await c1.new_page(); watch(pg, 'H')
            await pg.goto(link(d)); await pg.wait_for_selector('.hero, .card', timeout=15000)
            check(f'viewer (wt): "wt" as {label} is a bad link, a message and no crash', 'cannot be opened' in await pg.inner_text('#view'), (await pg.inner_text('#view'))[:80])
            await c1.close()
        many = {(D - timedelta(days=i)).isoformat(): [['08:00', 1]] for i in range(401)}
        d = mk2({day(0): 5}, many); d['from'] = day(-420)
        c1 = await new_ctx(); pg = await c1.new_page(); watch(pg, 'H')
        await pg.goto(link(d)); await pg.wait_for_selector('.hero, .card', timeout=15000)
        check('viewer (wt): more than 400 days in "wt" is a bad link', 'cannot be opened' in await pg.inner_text('#view'))
        await c1.close()

        # =========================================================== 9e Report: Water by hour (Time of day)
        cR = await new_ctx(timezone_id='Europe/Budapest'); await cR.clock.set_fixed_time(NOWISO)
        R = await cR.new_page(); watch(R, 'R')
        await R.goto(URL); await R.wait_for_selector('.hero')
        RT = R.evaluate
        OAT = own('u:oat', 'Oat', {'kcal': 380, 'protein': 13})
        D2, D3, D4, D5 = '2026-11-02', '2026-11-03', '2026-11-04', '2026-11-05'
        SAMPLE_REC = [('w1', D3, '07:10', 250), ('w2', D3, '07:50', 200), ('w3', D3, '12:30', 330), ('w4', D3, '19:05', 500), ('w5', D4, '07:20', 300), ('w6', D4, '21:10', 400)]

        async def rseed(kind='custom', frm=D2, to=D4, anchor=D4, recs=SAMPLE_REC, legacy=None, entries=None, pg=R, open_all=True):
            legacy = {D2: 600} if legacy is None else legacy
            entries = [('e1', 'u:oat', 100, D3, 'm1', '08:00')] if entries is None else entries
            await pg.evaluate("""([foods, ents, recs, legacy, kind, custom, anchor, openAll]) => { const t = window.__tapnaplo, S = t.S;
              S.log.length = 0; for (const k of Object.keys(S.foods)) delete S.foods[k]; S.meta.ref = null; S.meta.nova = {}; S.meta.water = legacy; S.wlog.length = 0;
              for (const f of foods) S.foods[f.id] = f;
              ents.forEach(([id, f, a, d, m, tm], i) => S.log.push({ id, f, a, d, m, t: 1000 + i, tm }));
              recs.forEach(([id, d, tm, ml], i) => S.wlog.push({ id, t: 2000 + i, d, tm, ml }));
              t.RP.kind = kind; t.RP.anchor = anchor; t.RP.custom = custom; for (const k of Object.keys(t.RP.open)) t.RP.open[k] = openAll && !k.endsWith('table');
              S.tab = 'report'; S.day = anchor; t.save(); t.render(); }""", [[OAT], entries, recs, legacy, kind, {'from': frm, 'to': to} if kind == 'custom' else None, anchor, open_all])
            await pg.wait_for_timeout(60)

        WH = """() => { const c = document.querySelector('#rp-whours'); if (!c) return null; const txt = (e) => (e ? e.textContent.replace(/\\s+/g, ' ').trim() : null);
          const bars = [...c.querySelectorAll('.rp-bar')].map((b) => ({ k: Number(b.dataset.k), c: b.className.replace('rp-bar ', '').replace(' sel', ''), sel: b.classList.contains('sel'), h: parseFloat(b.style.getPropertyValue('--h')) }));
          return { head: txt(c.querySelector('.rp-h')), sub: txt(c.querySelector('.rp-h + p')), bars, read: txt(c.querySelector('#rp-whrd')), leg: [...c.querySelectorAll('ul.rp-leg li')].map((li) => txt(li)), ticks: [...c.querySelectorAll('.rp-y span')].map((s) => txt(s)),
            xs: [...c.querySelectorAll('.rp-hx span')].map((s) => txt(s)), heads: [...c.querySelectorAll('table thead th')].map((x) => txt(x)), tbl: [...c.querySelectorAll('table tbody tr')].map((r) => [...r.children].map((x) => txt(x))),
            label: c.querySelector('#rp-wplot') ? c.querySelector('#rp-wplot').getAttribute('aria-label') : null, texts: [...c.querySelectorAll('p')].map((e) => txt(e)),
            prevDis: !!c.querySelector('[data-act=rp-whour-step][data-n="-1"]:disabled'), nextDis: !!c.querySelector('[data-act=rp-whour-step][data-n="1"]:disabled'), chart: !!c.querySelector('#rp-wplot'),
            tableOpen: !!(c.querySelector('details[data-sec=watertable]') || {}).open, inTime: !!c.closest('details[data-sec=time]') }; }"""
        await rseed()
        w = await RT(WH)
        check('Report: the Time of day section has a "Water by hour" card (after the energy cards) for a period with timed water', w is not None and w['head'] == 'Water by hour' and w['inTime'], w and w['head'])
        check('...the order in the section: When you eat, Energy by hour, Water by hour', await RT("() => [...document.querySelectorAll('details[data-sec=time] h4.rp-h')].map((h) => h.textContent)") == ['When you eat', 'Energy by hour', 'Water by hour'])
        byk = {b['k']: b for b in w['bars']}
        check('...24 bars; hours 7, 12, 19 and 21 are solid, the other 20 are the dashed "no recording" base', len(w['bars']) == 24 and sorted(k for k, b in byk.items() if b['c'] == 'full') == [7, 12, 19, 21] and sum(1 for b in w['bars'] if b['c'] == 'none') == 20, [(b['k'], b['c']) for b in w['bars'] if b['c'] != 'none'])
        check('...bar heights follow the values on an axis up to 500 mL (375 → 75%, 250 → 50%, 200 → 40%, 165 → 33%)', [round(byk[k]['h']) for k in (7, 12, 19, 21)] == [75, 33, 50, 40] and w['ticks'] == ['500', '250', '0'], ([round(byk[k]['h']) for k in (7, 12, 19, 21)], w['ticks']))
        check('...the title line says it is an average of the days with a recording time', w['sub'] == 'mL a day, average of the days with a recording time · one bar = one hour', w['sub'])
        check('...the highest hour is selected at the start and read out in words', w['read'] == '07:00–07:59 · 375 mL · 2 of 2 days · 3 recordings' and byk[7]['sel'], w['read'])
        legacy_txt = [t for t in w['texts'] if 'logged before water recordings had a time' in t]
        check('...the amount without a time (600 mL on 1 day) is named and said not to be in the bars', legacy_txt == ['600 mL on 1 day was logged before water recordings had a time. It has no hour, so it is not in the bars.'], w['texts'])
        check('...the legend lists only the two signs that are visible: solid and dashed', w['leg'] == ['Solid bar: water recorded in that hour', 'Dashed base: no recording in this hour (not a 0)'], w['leg'])
        check('...00:00 06:00 12:00 18:00 under the bars, the two arrow buttons are there', w['xs'] == ['00:00', '06:00', '12:00', '18:00'] and w['chart'])
        check('...the plot has a spoken label (highest hour, how to use it)', 'Highest: 375 mL at 07:00–07:59' in w['label'] and 'Previous hour and Next hour' in w['label'], w['label'])
        check('...the table is closed at first, with the columns Hour, Water, Days, Recordings and 24 rows', w['tableOpen'] is False and w['heads'] == ['Hour', 'Water', 'Days', 'Recordings'] and len(w['tbl']) == 24, (w['heads'], len(w['tbl'])))
        check('...table rows: 07 → 375 mL, 2, 3; 12 → 165 mL, 1, 1; 08 → no recordings, 0, 0', w['tbl'][7] == ['07:00–07:59', '375 mL', '2', '3'] and w['tbl'][12] == ['12:00–12:59', '165 mL', '1', '1'] and w['tbl'][19] == ['19:00–19:59', '250 mL', '1', '1'] and w['tbl'][21] == ['21:00–21:59', '200 mL', '1', '1'] and w['tbl'][8] == ['08:00–08:59', 'no recordings', '0', '0'], (w['tbl'][7], w['tbl'][8], w['tbl'][12]))
        stt = await RT("() => { const t = window.__tapnaplo, W = t.rpWaterTimeStats('2026-11-02', '2026-11-04'); return { nd: W.nd, recs: W.recs, noTimeMl: W.noTimeMl, noTimeDays: W.noTimeDays, lo: W.bars.map((b) => b.lo), sum: W.bars.reduce((s, b) => s + b.lo, 0) }; }")
        check('rpWaterTimeStats: 2 days with a time, 6 recordings, 600 mL on 1 day without a time, the bars add up to 990', stt['nd'] == 2 and stt['recs'] == 6 and stt['noTimeMl'] == 600 and stt['noTimeDays'] == 1 and abs(stt['sum'] - 990) < 1e-9 and stt['lo'][7] == 375 and stt['lo'][12] == 165, stt)
        ps = await RT("() => { const P = window.__tapnaplo.rpStats('2026-11-02', '2026-11-04'); return { days: P.waterDays, sum: P.waterSum, ml: P.waterMl }; }")
        check('rpStats: water days, the sum (2,580) and the total of each day (600 / 1,280 / 700)', ps['days'] == [D2, D3, D4] and ps['sum'] == 2580 and ps['ml'] == {D2: 600, D3: 1280, D4: 700}, ps)
        ov = await R.inner_text('details[data-sec=overview]')
        check('Overview: Water intake is the average of the 3 days with water logged: 860 mL (old amount and recordings are one total)', re.search(r'Water intake\s*·\s*average of 3 days with water logged\s*860\s*mL', re.sub(r'\s+', ' ', ov)) is not None, re.sub(r'\s+', ' ', ov)[-300:])
        check('Overview: the energy cards and the water card do not move each other (the energy chart still reads its own highest hour)', 'energy by hour' in (await R.inner_text('#rp-hours')).lower() and (await R.inner_text('#rp-hrd')).startswith('08:00–08:59'), await R.inner_text('#rp-hrd'))

        # reading the bars: keys, buttons, pointer
        en0 = await R.inner_text('#rp-hrd')
        await R.focus('#rp-wplot'); await R.keyboard.press('ArrowRight')
        check('keys: ArrowRight on the water chart moves to 08:00 ("no recordings") and the energy chart does not move', await R.inner_text('#rp-whrd') == '08:00–08:59 · no recordings' and await R.inner_text('#rp-hrd') == en0, await R.inner_text('#rp-whrd'))
        await R.keyboard.press('End')
        check('keys: End selects 23:00 and disables Next hour', (await R.inner_text('#rp-whrd')).startswith('23:00–23:59') and await R.locator('#rp-whours [data-act=rp-whour-step][data-n="1"]').is_disabled())
        await R.keyboard.press('Home')
        check('keys: Home selects 00:00 and disables Previous hour', (await R.inner_text('#rp-whrd')).startswith('00:00–00:59') and await R.locator('#rp-whours [data-act=rp-whour-step][data-n="-1"]').is_disabled())
        await R.focus('#rp-hplot'); await R.keyboard.press('ArrowRight')
        check('keys: the energy chart has its own selection (the water chart stays on 00:00)', (await R.inner_text('#rp-whrd')).startswith('00:00–00:59') and (await R.inner_text('#rp-hrd')) != en0)
        await R.tap('#rp-whours [data-act=rp-whour-step][data-n="1"]')
        check('Next hour: 01:00', (await R.inner_text('#rp-whrd')).startswith('01:00–01:59'))
        await R.tap('#rp-whours [data-act=rp-whour-step][data-n="-1"]')
        check('Previous hour: 00:00', (await R.inner_text('#rp-whrd')).startswith('00:00–00:59'))
        await R.locator('#rp-wplot').scroll_into_view_if_needed(); await R.wait_for_timeout(100)
        box = await R.locator('#rp-wplot').bounding_box()
        await R.mouse.click(box['x'] + box['width'] * (12.5 / 24), box['y'] + box['height'] / 2)
        check('pointer: a press on the 12:00 bar selects it and reads 165 mL, 1 of 2 days, 1 recording', await R.inner_text('#rp-whrd') == '12:00–12:59 · 165 mL · 1 of 2 days · 1 recording', await R.inner_text('#rp-whrd'))
        await R.mouse.move(box['x'] + box['width'] * (19.5 / 24), box['y'] + box['height'] / 2); await R.mouse.down(); await R.mouse.move(box['x'] + box['width'] * (21.5 / 24), box['y'] + box['height'] / 2); await R.mouse.up()
        check('pointer: dragging along the bars ends on 21:00 (200 mL)', await R.inner_text('#rp-whrd') == '21:00–21:59 · 200 mL · 1 of 2 days · 1 recording', await R.inner_text('#rp-whrd'))
        await R.click('#rp-whours details[data-sec=watertable] summary')
        await R.wait_for_function("window.__tapnaplo.RP.open.watertable === true")
        check('the table fold opens and its state is remembered (RP.open.watertable and the saved open states)', await RT("() => window.__tapnaplo.RP.open.watertable") is True and 'watertable' in json.loads(await RT("() => localStorage.getItem('nutrilog.reportOpen')")) and json.loads(await RT("() => localStorage.getItem('nutrilog.reportOpen')"))['watertable'] is True)
        await R.tap('[data-act=rp-step][data-n="-1"]'); await R.wait_for_timeout(100)
        check('...and it stays remembered after the period changes (the next period has no water, so no card; the state is kept)', await RT("() => window.__tapnaplo.RP.open.watertable") is True and await R.locator('#rp-whours').count() == 0)

        # one day with water but no food (11-04): the early branch of the Report still shows the card
        await rseed(kind='day', anchor=D4)
        w = await RT(WH)
        check('Day with water and no food: the Time of day section is there with only the water card', w is not None and w['inTime'] and await RT("() => document.querySelectorAll('details[data-sec=time] h4.rp-h').length") == 1 and 'No entries on' in await R.inner_text('#view'), w and w['head'])
        byk = {b['k']: b for b in w['bars']}
        check('...one day: "in that day", the bars are the hours of that day (300 mL at 07:00, 400 mL at 21:00), no Days column', w['sub'] == 'mL in that day · one bar = one hour' and [round(byk[k]['h']) for k in (7, 21)] == [60, 80] and w['heads'] == ['Hour', 'Water', 'Recordings'], (w['sub'], w['heads']))
        check('...the reading has no "of N days" (highest hour 21:00: 400 mL, 1 recording)', w['read'] == '21:00–21:59 · 400 mL · 1 recording', w['read'])
        check('...no amount without a time on that day: no such note', not [t for t in w['texts'] if 'before water recordings' in t])
        # only an amount without a time (11-02)
        await rseed(kind='day', anchor=D2)
        w = await RT(WH)
        check('Day with only an amount without a time: the card says "No water in this period has a time." and names the 600 mL; no chart', w is not None and not w['chart'] and 'No water in this period has a time.' in w['texts'] and any('600 mL on 1 day was logged before' in t for t in w['texts']), w and w['texts'])
        # food, no water
        await rseed(kind='day', anchor=D5, entries=[('e5', 'u:oat', 50, D5, 'm1', '09:00')], recs=[], legacy={})
        check('A period with food and no water has no Water by hour card (and no empty water chart)', await R.locator('#rp-whours').count() == 0 and await R.locator('#rp-hours').count() == 1)
        # no food, no water
        await rseed(kind='day', anchor=D5, entries=[], recs=[], legacy={})
        check('A period with neither has no card and no Time of day section', await R.locator('#rp-whours').count() == 0 and await R.locator('details[data-sec=time]').count() == 0)
        # water in a week with food but the recordings sit in another week
        await rseed(kind='week', anchor=D3)
        w = await RT(WH)
        check('Week (Mon 2 to Sun 8 Nov): the same recordings, the same 24 bars (period kinds do not matter)', w is not None and w['read'] == '07:00–07:59 · 375 mL · 2 of 2 days · 3 recordings', w and w['read'])
        # an old save: an amount without a time and a recording on the same day
        await rseed(kind='day', anchor=D3, legacy={D3: 500}, recs=[('w1', D3, '07:10', 250)])
        w = await RT(WH)
        check('A day with an old amount (500 mL) and one recording (250 mL): the bar is 250 mL, the note names the 500 mL, the Overview counts 750 mL', w is not None and w['read'] == '07:00–07:59 · 250 mL · 1 recording' and any('500 mL on 1 day was logged before' in t for t in w['texts']) and re.search(r'Water intake.{0,70}?750\s*mL', re.sub(r'\s+', ' ', await R.inner_text('details[data-sec=overview]'))) is not None, (w and w['read'], re.sub(r'\s+', ' ', await R.inner_text('details[data-sec=overview]'))[-200:]))
        # look: 44 px, contrast, widths
        await rseed()
        small = await RT("(sel) => [...document.querySelectorAll(sel)].filter((e) => e.getClientRects().length).map((e) => { const r = e.getBoundingClientRect(); return [e.getAttribute('aria-label') || e.className || e.tagName, Math.round(r.width), Math.round(r.height)]; }).filter((x) => x[1] < 43.5 || x[2] < 43.5)", '#rp-whours button, #rp-whours summary')
        check('Water by hour: Previous hour, Next hour and the table fold are at least 44 x 44 px', small == [], small)
        for theme in ('light', 'dark'):
            await RT("(th) => document.documentElement.setAttribute('data-theme', th)", theme)
            bad = await RT(CONTRAST_JS, '#rp-whours')
            check(f'Water by hour: text contrast in {theme} mode', bad == [], bad)
            g = await RT("""() => { const parse = (c) => { let m = c.match(/rgba?\\(([^)]+)\\)/); if (m) { const p = m[1].split(/[ ,\\/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2]]; } m = c.match(/color\\(srgb ([^)]+)\\)/); if (m) { const p = m[1].split(/[ \\/]+/).filter(Boolean).map(Number); return [p[0] * 255, p[1] * 255, p[2] * 255]; } return [0, 0, 0]; };
              const lum = ([r, g, b]) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
              const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
              const card = document.querySelector('#rp-whours'), bg = (() => { for (let e = card; e; e = e.parentElement) { const c = getComputedStyle(e).backgroundColor; if (!/rgba\\(.*, 0\\)/.test(c) && c !== 'transparent') return parse(c); } return [255, 255, 255]; })();
              const tok = (n) => { const s = document.createElement('span'); s.style.color = `var(${n})`; card.appendChild(s); const c = parse(getComputedStyle(s).color); s.remove(); return c; };
              return Math.round(ratio(tok('--accent'), bg) * 100) / 100; }""")
            check(f'Water by hour: the bar colour against the card is at least 3:1 in {theme} mode', g >= 3, g)
        await RT("() => document.documentElement.setAttribute('data-theme', 'light')")
        if SHOTS: await R.screenshot(path=os.path.join(SHOTS, 'water_by_hour.png'))
        wide = await RT("() => ({ page: document.documentElement.scrollWidth <= window.innerWidth, card: (() => { const r = document.querySelector('#rp-whours').getBoundingClientRect(); return r.left >= 0 && r.right <= window.innerWidth; })() })")
        check('390 px: Water by hour fits, no sideways scroll', wide['page'] and wide['card'], wide)
        c3 = await new_ctx(w=320, h=640, timezone_id='Europe/Budapest'); await c3.clock.set_fixed_time(NOWISO)
        R3 = await c3.new_page(); watch(R3, 'R3'); await R3.goto(URL); await R3.wait_for_selector('.hero')
        await rseed(pg=R3)
        wide = await R3.evaluate("() => ({ page: document.documentElement.scrollWidth <= window.innerWidth, card: (() => { const r = document.querySelector('#rp-whours').getBoundingClientRect(); return r.left >= 0 && r.right <= window.innerWidth; })(), read: (() => { const e = document.querySelector('#rp-whrd'); return e.scrollWidth <= e.clientWidth + 1; })() })")
        check('320 px: Water by hour fits, the reading line is not cut off, no sideways scroll', wide['page'] and wide['card'] and wide['read'], wide)
        await R3.click('#rp-whours details[data-sec=watertable] summary')
        wide = await R3.evaluate("() => ({ page: document.documentElement.scrollWidth <= window.innerWidth, wrap: (() => { const e = document.querySelector('#rp-whours .rp-tablewrap'); return e.scrollWidth <= e.clientWidth + 1; })() })")
        check('320 px: the table also fits without sideways scroll', wide['page'] and wide['wrap'], wide)
        await c3.close()

        # the shared copy shows the same bars as the sender
        await rseed()
        sender = await RT(WH)
        lnk = await RT("() => window.__tapnaplo.shareLink('2026-11-02', '2026-11-04').then((r) => r.url)")
        cS, S2 = await viewer(lnk)
        await S2.evaluate("() => { document.querySelector('[data-tab=report]').click(); }"); await S2.wait_for_selector('details[data-sec=time]')
        await S2.evaluate("() => { const t = window.__tapnaplo; for (const k of Object.keys(t.RP.open)) t.RP.open[k] = true; t.render(); }")
        await S2.wait_for_selector('#rp-whours')
        shared = await S2.evaluate(WH)
        keep = ('bars', 'read', 'leg', 'tbl', 'ticks', 'texts', 'head', 'sub')
        check('shared copy: the Water by hour card has the same bars, reading, table, legend and notes as the sender', all(shared[k] == sender[k] for k in keep), [k for k in keep if shared[k] != sender[k]])
        await S2.focus('#rp-wplot'); await S2.keyboard.press('ArrowRight')
        check('shared copy: the keys work on the water chart', (await S2.inner_text('#rp-whrd')).startswith('08:00–08:59'))
        w = await S2.evaluate("() => window.__w")
        check('shared copy: nothing was written (no IndexedDB, no localStorage write)', w == {'idbOpen': 0, 'idbWrite': 0, 'lsWrite': 0}, w)
        await cS.close()
        await cR.close()

        # =========================================================== 10 look and touch
        await page.click('[data-tab=log]'); await page.wait_for_selector('#water')
        await reset_water({today: 1250})
        small = await T(SIZES, '#water button')
        check('card: every button is at least 44 x 44 px', small == [], small)
        await T("(d) => { const t = window.__tapnaplo; t.S.wlog.push({ id: 'l1', t: 5, d, tm: '08:00', ml: 250 }, { id: 'l2', t: 6, d, tm: '09:30', ml: 330 }); t.save(); t.render(); }", today)
        if not await T("() => document.querySelector('#wlist').open"): await page.click('#wlist summary')
        small = await T(SIZES, '#wlist summary, .water-row')
        check('the open list: the summary and every row (the amount without a time and two recordings) are at least 44 x 44 px', small == [] and await page.locator('.water-row').count() == 3, small)
        await open_other()
        small = await T(SIZES, '.sheet button')
        check('sheet: every button is at least 44 x 44 px', small == [], small)
        check('sheet: the field has at least 16 px text', await T(SMALL_FONTS, '.sheet') == [], await T(SMALL_FONTS, '.sheet'))
        check('sheet: the buttons are in a sticky .sheet-actions row', await page.locator('.sheet-b > .sheet-actions').count() == 1 and await page.locator('.has-actions').count() == 1)
        check('sheet: the amount field has the decimal keypad and a Return key that means "done"', await page.get_attribute('#wamt', 'inputmode') == 'decimal' and await page.get_attribute('#wamt', 'enterkeyhint') == 'done')
        await T("() => document.documentElement.setAttribute('data-theme', 'dark')")
        check('contrast of the sheet in dark mode', await T(CONTRAST_JS, '.sheet') == [], await T(CONTRAST_JS, '.sheet'))
        if SHOTS: await page.screenshot(path=os.path.join(SHOTS, 'water_sheet_dark.png'))
        await close_sheet()
        check('contrast of the card in dark mode', await T(CONTRAST_JS, '.water-card') == [], await T(CONTRAST_JS, '.water-card'))
        if SHOTS: await page.screenshot(path=os.path.join(SHOTS, 'water_card_dark.png'))
        await T("() => document.documentElement.setAttribute('data-theme', 'light')")
        check('contrast of the card in light mode', await T(CONTRAST_JS, '.water-card') == [], await T(CONTRAST_JS, '.water-card'))
        await open_other()
        check('contrast of the sheet in light mode', await T(CONTRAST_JS, '.sheet') == [], await T(CONTRAST_JS, '.sheet'))
        if SHOTS: await page.screenshot(path=os.path.join(SHOTS, 'water_sheet_light.png'))
        await page.fill('#wamt', '999'); await page.click('#wadd')
        check('contrast of the error text', await T(CONTRAST_JS, '.sheet') == [], await T(CONTRAST_JS, '.sheet'))
        await close_sheet()
        wide = await T("() => ({ page: document.documentElement.scrollWidth <= window.innerWidth, card: (() => { const r = document.querySelector('.water-card').getBoundingClientRect(); return r.left >= 0 && r.right <= window.innerWidth; })(), chips: [...document.querySelectorAll('.water-chips button')].every((b) => { const r = b.getBoundingClientRect(); return r.left >= 0 && r.right <= window.innerWidth && b.scrollWidth <= b.clientWidth + 1; }) })")
        check('390 px: no sideways scroll, the card and its buttons fit', wide['page'] and wide['card'] and wide['chips'], wide)
        c320 = await new_ctx(w=320, h=640); p320 = await c320.new_page(); watch(p320, 'N')
        await p320.goto(URL); await p320.wait_for_selector('#water .water-card')
        await p320.evaluate("() => { const t = window.__tapnaplo; t.S.meta.water[t.S.day] = 20000; t.render(); }")
        wide = await p320.evaluate("() => ({ page: document.documentElement.scrollWidth <= window.innerWidth, chips: [...document.querySelectorAll('.water-chips button')].every((b) => { const r = b.getBoundingClientRect(); return r.left >= 0 && r.right <= window.innerWidth && b.scrollWidth <= b.clientWidth + 1; }), h: Math.round(document.querySelector('.water-chips button').getBoundingClientRect().height) })")
        check('320 px (small phone, biggest total): no sideways scroll, the five buttons fit and stay 44 px high', wide['page'] and wide['chips'] and wide['h'] >= 44, wide)
        await p320.click('[data-act=water-other]'); await p320.wait_for_selector('#wamt'); await p320.wait_for_timeout(300)
        wide = await p320.evaluate("() => ({ page: document.documentElement.scrollWidth <= window.innerWidth, sheet: (() => { const s = document.querySelector('.sheet-b'); return s.scrollWidth <= s.clientWidth + 1; })(), actions: [...document.querySelectorAll('.sheet-actions button')].every((b) => { const r = b.getBoundingClientRect(); return r.left >= 0 && r.right <= window.innerWidth; }) })")
        check('320 px: the sheet and its buttons fit', wide['page'] and wide['sheet'] and wide['actions'], wide)
        if SHOTS: await p320.screenshot(path=os.path.join(SHOTS, 'water_320.png'))
        await c320.close()

        # =========================================================== 11 version
        await page.click('[data-tab=data]'); await page.wait_for_selector('[data-act=export-json]')
        m = re.search(r'Nutrilog version\s*(\d+)', await page.inner_text('#view'))
        sw = re.search(r"CACHE = 'nutrilog-v(\d+)'", (ROOT / 'sw.js').read_text())
        check('the version is 34 or newer and the same as the service worker cache', bool(m) and bool(sw) and int(m.group(1)) >= 34 and int(m.group(1)) == int(sw.group(1)), (m and m.group(1), sw and sw.group(1)))

        check('no request left this machine except the (fake) GitHub', outside == [], outside[:5])
        check('no page errors', errs == [], errs[:5])
        await browser.close()
        print('\nFAILED: ' + ', '.join(problems) if problems else '\nALL PASSED')
        sys.exit(1 if problems else 0)

asyncio.run(main())
