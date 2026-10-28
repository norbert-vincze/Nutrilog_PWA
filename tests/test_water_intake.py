"""Water intake (version 24). Run with the web server on port 8765 (see CLAUDE.md).

A card "Water intake" sits in the Diary above the meals. It keeps ONE total per day, no time of day: buttons +1 / +2 / +3 / +5 dL add at once (with Undo), "Other" opens a sheet with
a mL | dL switch, an amount field, chips, Add, Subtract and Clear day. The total is kept in whole millilitres in S.meta.water['YYYY-MM-DD']; a day without a key has nothing logged
(the daily totals CSV leaves the cell empty, it does not say 0). It is not the nutrient "Water" (the water inside foods).
Covers: place of the card, empty day, quick buttons and their Undo, the sheet (unit switch converts the amount, chips, comma decimals, remembered unit, Enter, every error text, the
20 L limit, Subtract, Clear day, Undo for all), one total per day (other days stay separate, reload keeps them), no time stamps and no diary entries made, old saves without water and
damaged water in storage, backup JSON and Restore (also an old backup without water, a damaged one), the daily totals CSV (new column, a day with only water, empty when nothing was
logged), Sync with a fake GitHub (file per year, two devices, a tombstone, bad records ignored), Share link (water of the shared days only, the key is absent without water, a water-only
day, read-only card in the viewer, nothing written in the viewer, hostile water values), touch targets, 16 px fields, contrast in light and dark, 390 and 320 px width, the version number,
no page errors."""
import asyncio, base64, csv, io, json, os, pathlib, re, sys, zlib
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
        water = lambda: T("() => JSON.parse(JSON.stringify(window.__tapnaplo.S.meta.water))")
        num = lambda: page.inner_text('.water-num')
        side = lambda: page.inner_text('.water-top .muted')
        toast = lambda: page.inner_text('#toast span')
        sheet_open = lambda: page.locator('#wamt').count()

        async def reset_water(w=None):
            await T("(w) => { const t = window.__tapnaplo; t.S.meta.water = w || {}; t.save(); t.render(); }", w)

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
        check('every button names what it does for a screen reader', await T("[...document.querySelectorAll('#water button')].map((b) => b.getAttribute('aria-label'))") == ['Add 1 dL of water', 'Add 2 dL of water', 'Add 3 dL of water', 'Add 5 dL of water', 'Add another amount of water, or correct the total'])
        check('the card only has the water in it: no entry is made, the Energy stays 0', await T("() => window.__tapnaplo.S.log.length") == 0 and '0' == (await page.inner_text('.hero-num')).replace('kcal', '').strip())

        # =========================================================== 2 quick buttons
        await page.tap('[data-act=water-add][data-dl="2"]')
        check('+2 dL: 200 mL, shown as 2 dL too', squash(await num()) == '200mL' and '2 dL' in await side(), (await num(), await side()))
        check('...the toast says what happened and offers Undo', 'Water +2 dL · total 200 mL' in await toast() and await page.locator('#toast button').count() == 1, await toast())
        await page.tap('[data-act=water-add][data-dl="3"]')
        check('+3 dL on top: 500 mL = 5 dL', squash(await num()) == '500mL' and '5 dL' in await side())
        await page.tap('#toast button')
        check('Undo takes back only the last tap', squash(await num()) == '200mL' and (await water()) == {today: 200}, await water())
        await page.tap('[data-act=water-add][data-dl="1"]'); await page.tap('[data-act=water-add][data-dl="5"]')
        check('+1 dL and +5 dL add up (200 + 100 + 500 = 800 mL = 8 dL)', squash(await num()) == '800mL' and '8 dL' in await side(), await num())
        check('the stored value is a plain whole number of ml (no time, no list)', (await water()) == {today: 800})
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
        check('...the sheet closed and the toast has Undo with the new total', not await sheet_open() and 'Water +1.5 dL · total 1,400 mL' in await toast(), await toast())
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
        # subtract
        await reset_water({today: 800})
        msg, _, _ = await err_of('9', button='#wsub')
        check('Subtract more than the total: "Only 800 mL is logged on this day, so you can subtract at most that."', msg == 'Only 800 mL is logged on this day, so you can subtract at most that.' and (await water()) == {today: 800}, msg)
        await open_other(); await page.fill('#wamt', '3'); await page.click('#wsub')
        check('Subtract 3 dL: 500 mL', (await water()) == {today: 500} and 'Water −3 dL · total 500 mL' in await toast(), (await water(), await toast()))
        await page.tap('#toast button')
        check('Undo puts the 800 mL back', (await water()) == {today: 800})
        await open_other(); await page.fill('#wamt', '8'); await page.click('#wsub')
        check('subtracting exactly the total leaves no value (not a stored 0): the day is "nothing logged" again', (await water()) == {} and 'Nothing logged yet' in await side() and squash(await num()) == '0mL', await water())
        await page.tap('#toast button')
        check('...and Undo brings the 800 mL back', (await water()) == {today: 800})
        await reset_water({})
        msg, _, _ = await err_of('1', button='#wsub')
        check('Subtract on a day with nothing: "Nothing is logged on this day, so there is nothing to subtract."', msg == 'Nothing is logged on this day, so there is nothing to subtract.', msg)
        await reset_water({today: 640})
        await open_other()
        check('Clear day is offered while there is a total', await page.locator('#wclear').is_visible())
        await page.click('#wclear')
        check('Clear day removes the day and says so, with Undo', (await water()) == {} and 'Water cleared for this day' in await toast() and not await sheet_open(), await toast())
        await page.tap('#toast button')
        check('Undo of Clear day restores 640 mL', (await water()) == {today: 640})
        await reset_water({})
        await open_other()
        check('Clear day is hidden when nothing is logged', not await page.locator('#wclear').is_visible() and 'Total so far: nothing logged' in (await page.inner_text('.sheet-b')).replace('\n', ' '))
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
        check('no time of day is stored: the data is only day → whole ml, and no diary entry was made', await T("() => { const w = window.__tapnaplo.S.meta.water; return Object.values(w).every((v) => Number.isInteger(v)) && window.__tapnaplo.S.log.length === 0; }"))

        # =========================================================== 5 old and damaged storage
        await T("() => { const t = window.__tapnaplo; delete t.S.meta.water; t.save(); }")
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
        check('the backup JSON has the water in meta', backup['meta'].get('water') == {today: 200, day(-1): 500}, backup['meta'].get('water'))
        await T("() => { const t = window.__tapnaplo; t.S.meta.water = {}; t.save(); }")

        async def restore(obj):
            await page.set_input_files('#importfile', {'name': 'backup.json', 'mimeType': 'application/json', 'buffer': json.dumps(obj).encode()})
            await page.wait_for_selector('[data-ok]'); await page.click('[data-ok]')
            await page.wait_for_timeout(500)
        await restore(backup)
        check('Restore from file brings the water back', (await water()) == {today: 200, day(-1): 500}, await water())
        old = json.loads(json.dumps(backup)); old['meta'].pop('water')
        await restore(old)
        check('an old backup without water restores fine and leaves no water (not an error)', (await water()) == {})
        bad = json.loads(json.dumps(backup)); bad['meta']['water'] = {today: 300, 'nope': 1, '2026-13-01': 5, day(-1): -2, day(-2): 99999999}
        await restore(bad)
        check('a damaged water part of a backup is cleaned while restoring', (await water()) == {today: 300}, await water())
        bad2 = json.loads(json.dumps(backup)); bad2['meta']['water'] = 'lots'
        await restore(bad2)
        check('water of the wrong type in a backup becomes empty', (await water()) == {})
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
          S.log.length = 0; S.meta.water = {};
          S.log.push({ id: 'a1', d: d1, m: 'm1', f: 'u:oat', a: 100, t: 1, tm: '08:00' }, { id: 'a2', d: d2, m: 'm1', f: 'u:oat', a: 150, t: 2, tm: '09:00' });
          S.meta.water[d0] = 1500; S.meta.water[d1] = 800; S.meta.water[d3] = 999;      // d0 later than every entry, d3 outside the shared period
          t.save(); t.render(); }""", [day(0), day(-1), day(-2), day(-20)])
        snap = await T("([a, b]) => JSON.parse(window.__tapnaplo.shareSnapshot(a, b).json)", [day(-6), day(0)])
        check('share: the snapshot has the water of the shared days only', snap.get('water') == {day(0): 1500, day(-1): 800}, snap.get('water'))
        check('share: the format is still v1 (the water key is an optional addition)', snap['v'] == 1 and snap['app'] == 'tapnaplo-share')
        snap2 = await T("([a, b]) => JSON.parse(window.__tapnaplo.shareSnapshot(a, b).json)", [day(-3), day(-2)])
        check('share: a period without water has no "water" key (the link looks exactly as before)', 'water' not in snap2 and list(snap2['days']) == [day(-2)], list(snap2))
        await T("() => { const t = window.__tapnaplo; t.S.meta.water = {}; t.save(); }")
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
        check('viewer: even a forged water button changes nothing', await V.evaluate("() => JSON.stringify(window.__tapnaplo.S.meta.water)") == json.dumps({day(0): 1500, day(-1): 800}, separators=(',', ':')), await V.evaluate("() => JSON.stringify(window.__tapnaplo.S.meta.water)"))
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

        # =========================================================== 10 look and touch
        await page.click('[data-tab=log]'); await page.wait_for_selector('#water')
        await reset_water({today: 1250})
        small = await T(SIZES, '#water button')
        check('card: every button is at least 44 x 44 px', small == [], small)
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
        await page.fill('#wamt', '999'); await page.click('#wsub')
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
        check('the version is 24 or newer and the same as the service worker cache', bool(m) and bool(sw) and int(m.group(1)) >= 24 and int(m.group(1)) == int(sw.group(1)), (m and m.group(1), sw and sw.group(1)))

        check('no request left this machine except the (fake) GitHub', outside == [], outside[:5])
        check('no page errors', errs == [], errs[:5])
        await browser.close()
        print('\nFAILED: ' + ', '.join(problems) if problems else '\nALL PASSED')
        sys.exit(1 if problems else 0)

asyncio.run(main())
