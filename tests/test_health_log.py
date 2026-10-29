"""Health log (version 25). Run with the web server on port 8765 (see CLAUDE.md).

A fifth tab "Health log" (before Data): a journal of short notes about your health, apart from the food diary. A note has a day and a time (24 h), ONE label (Symptom, Event
or Observation) and a text of 1..1000 characters (Unicode characters, an emoji is 1). The list is newest first and shows "date, time", the label and the first 100 characters;
a tap opens the whole note; notes can be edited ("Edited ..." line) and deleted (Undo). An unsaved new note stays as a draft on the device (localStorage).
Covers: the tab and the empty state, Add note (no label chosen at first, every error text, limits 1000 / 1001, emoji, whitespace only, a pasted 5000 characters is never cut),
date and time rules and the order of the list, the 100-character preview (line breaks, emoji, ellipsis), "Show older notes", the full note with its line breaks, Edit (Edited line, t
stays, Undo, no change = no edit), Delete and Undo, the draft (restore, discard, saved note clears it, blocked localStorage), reload and the remembered tab, damaged and old saves
(cleanNote / cleanHealth), the backup JSON (health key) and Restore (replace, empty list, old backup without health, invalid items counted, bad shape refused, hostile text),
Sync with a fake GitHub (health/YYYY-MM.json, two devices, edit, tombstone, bad remote records, the file does not change when the date is edited, an older app ignores the folder),
the CSV, the Share link (no notes, no tab in the viewer, nothing written), nothing counted in the food totals, touch targets, 16 px fields, contrast in light and dark, 390 and
320 px (five tabs), the simulated keyboard, the version number, no page errors."""
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

WATCH = """(() => {
  window.__w = { idbOpen: 0, idbWrite: 0, lsWrite: 0 };
  const o = indexedDB.open.bind(indexedDB); indexedDB.open = function () { window.__w.idbOpen++; return o.apply(this, arguments); };
  for (const m of ['put', 'add', 'delete', 'clear']) { const f = IDBObjectStore.prototype[m]; IDBObjectStore.prototype[m] = function () { window.__w.idbWrite++; return f.apply(this, arguments); }; }
  for (const m of ['setItem', 'removeItem', 'clear']) { const f = Storage.prototype[m]; Storage.prototype[m] = function () { window.__w.lsWrite++; return f.apply(this, arguments); }; }
})();"""
NO_LS = """(() => { for (const m of ['getItem', 'setItem', 'removeItem', 'clear']) Storage.prototype[m] = function () { throw new Error('localStorage is blocked'); }; })();"""
FAKE_VV = """(() => {
  const t = new EventTarget();
  Object.defineProperties(t, { height: { get: () => (window.__vvh ?? window.innerHeight) }, width: { get: () => window.innerWidth }, offsetTop: { get: () => (window.__vvt ?? 0) }, scale: { get: () => (window.__vvs ?? 1) } });
  Object.defineProperty(window, 'visualViewport', { value: t, configurable: true });
  window.__vv = t;
})();"""
SIZES = "(sel) => [...document.querySelectorAll(sel)].filter((e) => !e.hidden && e.getClientRects().length).map((e) => { const r = e.getBoundingClientRect(); return [(e.id || e.dataset.act || e.className || e.tagName) + ':' + e.textContent.trim().slice(0, 14), Math.round(r.width), Math.round(r.height)]; }).filter((x) => x[2] < 44 || x[1] < 44)"
OLD_SHARD = re.compile(r'^(entries/(\d{4}-\d{2}|undated)|foods/[0-7]|water/\d{4}|meta)\.json$')   # SYNC_SHARD of version 24


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


def preview(text):
    flat = ' '.join(text.split())
    return flat if len(flat) <= 100 else flat[:100] + '…'


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
            pg.on('console', lambda m: errs.append(f'{tag} C {m.text}') if m.type == 'error' and 'Failed to load resource' not in m.text and 'localStorage is blocked' not in m.text else None)
            pg.on('request', lambda r: outside.append(r.url) if not r.url.startswith('http://127.0.0.1') and not r.url.startswith('data:') and not r.url.startswith('blob:') and 'api.github.com' not in r.url else None)

        async def new_ctx(w=390, h=844, scripts=(), **kw):
            c = await browser.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2, is_mobile=True, has_touch=True, locale='en-GB', service_workers='block', accept_downloads=True, permissions=['clipboard-read', 'clipboard-write'], **kw)
            for s in scripts: await c.add_init_script(s)
            await c.route('**/*openfoodfacts.org/**', lambda r: r.fulfill(status=200, headers={'access-control-allow-origin': '*', 'content-type': 'application/json'}, body='{"products":[],"status":0}'))
            return c

        ctx = await new_ctx()
        page = await ctx.new_page(); watch(page, 'A')
        await page.goto(URL); await page.wait_for_selector('.hero')
        T = page.evaluate
        today = await T("""(() => { const d = new Date(); const p = (n) => String(n).padStart(2, '0'); return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`; })()""")
        D = date.fromisoformat(today)
        day = lambda n: (D + timedelta(days=n)).isoformat()
        notes = lambda pg=None: (pg or page).evaluate("() => JSON.parse(JSON.stringify(window.__tapnaplo.S.health))")
        toast = lambda: page.inner_text('#toast span')
        rows = lambda: page.locator('.health-row').all_inner_texts()

        async def seed(lst, pg=None):
            pg = pg or page
            await pg.evaluate("(l) => { const t = window.__tapnaplo; t.S.health = l; t.save(); t.render(); }", lst)

        def note(i, d, tm, label='symptom', x='x', t=None, **kw):
            n = {'id': f'n{i}', 't': t if t is not None else 1700000000000 + i * 1000, 'd': d, 'tm': tm, 'label': label, 'x': x}
            n.update(kw)
            return n

        async def go_health():
            await page.click('[data-tab=health]'); await page.wait_for_selector('.health-bar')

        async def open_add():
            await go_health()
            await page.click('[data-act=health-add]'); await page.wait_for_selector('#hx'); await page.wait_for_timeout(300)   # the sheet slides in

        async def close_sheet():
            if await page.locator('.sheet').count():
                await page.click('.sheet [data-x]'); await page.wait_for_selector('.sheet', state='detached')

        async def save_note():
            await page.click('#hsave')

        async def add(label, text, d=None, tm=None):
            await open_add()
            if label: await page.click(f'#hlabels [data-l={label}]')
            await page.fill('#hx', text)
            if d: await page.fill('#hd', d)
            if tm is not None: await page.fill('#htm', tm)
            await save_note(); await page.wait_for_selector('#hx', state='detached')

        # =========================================================== 1 the tab
        tabs = await page.locator('#tabbar .tab span').all_inner_texts()
        check('five tabs: Diary, Nutrients, My foods, Health log, Data', tabs == ['Diary', 'Nutrients', 'My foods', 'Health log', 'Data'], tabs)
        await go_health()
        check('the title is "Health log" and there are no day arrows', await page.inner_text('#topbar h1') == 'Health log' and await page.locator('#topbar [data-act=day]').count() == 0)
        check('empty state: "No notes yet. Add your first note." and an Add note button', 'No notes yet. Add your first note.' in await page.inner_text('#view') and 'Add note' in await page.inner_text('.health-bar .act'), await page.inner_text('#view'))
        check('...no count is shown while there are no notes', (await page.inner_text('.health-count')).strip() == '')
        check('the tab is remembered', await T("() => localStorage.getItem('nutrilog.tab')") == 'health')
        check('a new device starts with an empty list in the store', await notes() == [])

        # =========================================================== 2 Add note
        await page.click('[data-act=health-add]'); await page.wait_for_selector('#hx'); await page.wait_for_timeout(300)
        check('the sheet is called "Add note"', await page.inner_text('.sheet-h h2') == 'Add note')
        pressed = await page.locator('#hlabels [data-l]').evaluate_all("(bs) => bs.map((b) => [b.textContent, b.getAttribute('aria-pressed')])")
        check('three labels, none chosen at first (no hidden default)', pressed == [['Symptom', 'false'], ['Event', 'false'], ['Observation', 'false']], pressed)
        now = await T("() => { const d = new Date(), p = (n) => String(n).padStart(2, '0'); return p(d.getHours()) + ':' + p(d.getMinutes()); }")
        check('the date starts as today and the time as now (24 h)', await page.input_value('#hd') == today and abs(int(now[:2]) * 60 + int(now[3:]) - (int((await page.input_value('#htm'))[:2]) * 60 + int((await page.input_value('#htm'))[3:]))) <= 2, (await page.input_value('#hd'), await page.input_value('#htm'), now))
        check('the date field cannot pick a day after today', await page.get_attribute('#hd', 'max') == today)
        check('the counter starts at 0 / 1000', (await page.inner_text('#hcount')).strip() == '0 / 1000')
        check('the text field has no maxlength (nothing is cut silently) and Enter is a new line', await page.get_attribute('#hx', 'maxlength') is None)
        await page.fill('#hx', 'abc')
        check('the counter follows the typing', (await page.inner_text('#hcount')).strip() == '3 / 1000')
        # errors
        await page.fill('#hx', ''); await save_note()
        check('nothing filled in: the label error and the text error sit next to their fields', await page.locator('#hlaberr:visible').count() == 1 and 'Choose a label.' in await page.inner_text('#hlaberr') and 'Write a note.' in await page.inner_text('#hxerr'))
        check('...the sheet stays open and nothing was saved', await page.locator('#hx').count() == 1 and await notes() == [])
        await page.click('#hlabels [data-l=event]')
        check('choosing a label removes its error', await page.locator('#hlaberr:visible').count() == 0)
        await page.fill('#hx', '   \n\t  '); await save_note()
        check('only spaces and line breaks: "Write a note."', 'Write a note.' in await page.inner_text('#hxerr') and await notes() == [])
        await page.fill('#hx', 'a')
        check('typing removes the text error', await page.locator('#hxerr:visible').count() == 0)
        # a normal note
        await page.click('#hlabels [data-l=symptom]'); await page.fill('#hx', '  Fejfájás délután, a bal halánték körül.  ')
        check('the chosen label is marked pressed (and only one)', await page.locator('#hlabels [aria-pressed=true]').all_inner_texts() == ['Symptom'])
        await save_note(); await page.wait_for_selector('#hx', state='detached')
        n1 = await notes()
        check('a note was saved with id, t, d, tm, label and the TRIMMED text, no "e"', len(n1) == 1 and set(n1[0]) == {'id', 't', 'd', 'tm', 'label', 'x'} and n1[0]['x'] == 'Fejfájás délután, a bal halánték körül.' and n1[0]['label'] == 'symptom' and n1[0]['d'] == today, n1)
        check('...t is the time it was made', abs(n1[0]['t'] - await T("() => Date.now()")) < 60000)
        check('the toast says "Note added"', 'Note added' in await toast())
        check('the list shows the note: date and time, label, text; and "1 note"', len(await rows()) == 1 and 'Symptom' in (await rows())[0] and 'Fejfájás délután' in (await rows())[0] and (await page.inner_text('.health-count')).strip() == '1 note', await rows())
        check('the row starts with the day and the time ("29 Oct 2026, 16:25" form)', re.match(r'^\d{1,2} \w{3,4} \d{4}, \d\d:\d\d', (await rows())[0]) is not None, (await rows())[0][:30])

        # =========================================================== 3 limits
        await seed([])
        for count, label_ in ((1000, 'a'), (1001, 'a')):
            await open_add(); await page.click('#hlabels [data-l=observation]'); await page.fill('#hx', label_ * count)
            check(f'{count} characters: counter shows {count} / 1000', (await page.inner_text('#hcount')).startswith(f'{count} / 1000'), await page.inner_text('#hcount'))
            await save_note(); await page.wait_for_timeout(200)
            if count == 1000:
                check('exactly 1000 characters can be saved', len(await notes()) == 1 and len((await notes())[0]['x']) == 1000 and await page.locator('#hx').count() == 0)
            else:
                msg = await page.inner_text('#hxerr')
                check('1001 characters: the error names the limit and the count', 'The note can be 1,000 characters at most. It is 1,001 characters now.' in msg, msg)
                check('...the counter turns red and says how many are too many', await page.locator('#hcount.over').count() == 1 and '1 character too many' in await page.inner_text('#hcount'), await page.inner_text('#hcount'))
                check('...nothing more was saved', len(await notes()) == 1)
                await page.fill('#hx', 'a' * 1000); await save_note(); await page.wait_for_selector('#hx', state='detached')
                check('...after deleting the extra character it saves', len(await notes()) == 2)
        # emoji and accents are one character each
        await seed([])
        await open_add(); await page.click('#hlabels [data-l=event]'); await page.fill('#hx', '😀' * 1000)
        check('1000 emoji count as 1000 characters (not 2000)', (await page.inner_text('#hcount')).startswith('1000 / 1000'), await page.inner_text('#hcount'))
        await save_note(); await page.wait_for_selector('#hx', state='detached')
        check('...and are saved whole', len(await notes()) == 1 and [*(await notes())[0]['x']] == ['😀'] * 1000)
        await open_add(); await page.click('#hlabels [data-l=event]'); await page.fill('#hx', 'é' * 1000 + '😀'); await save_note()
        check('1000 accented letters + 1 emoji = 1001: refused', 'It is 1,001 characters now.' in await page.inner_text('#hxerr'))
        # a pasted long text is not cut
        await page.fill('#hx', 'b' * 5000)
        check('a pasted text of 5000 characters stays whole in the field', await page.evaluate("() => document.getElementById('hx').value.length") == 5000)
        await save_note()
        check('...saving is refused with the real count, nothing is cut', 'It is 5,000 characters now.' in await page.inner_text('#hxerr') and len(await notes()) == 1)
        # the limit counts the typed text, edges are trimmed when saved
        await page.fill('#hx', ' ' + 'c' * 1000); await save_note()
        check('1000 characters plus a space at the start is 1001 typed characters: refused', 'It is 1,001 characters now.' in await page.inner_text('#hxerr'))
        await page.fill('#hx', 'Line one\n\nLine  two\twith   spaces\n'); await save_note(); await page.wait_for_selector('#hx', state='detached')
        check('line breaks and inner spaces are kept as typed, only the ends are trimmed', (await notes())[-1]['x'] == 'Line one\n\nLine  two\twith   spaces', (await notes())[-1]['x'])

        # =========================================================== 4 date and time
        await seed([])
        await open_add(); await page.click('#hlabels [data-l=event]'); await page.fill('#hx', 'future'); await page.fill('#hd', day(1)); await save_note()
        check('tomorrow is refused: "The date cannot be in the future."', 'The date cannot be in the future.' in await page.inner_text('#hderr') and await notes() == [])
        await page.fill('#hd', day(-3))
        check('changing the date removes the date error', await page.locator('#hderr:visible').count() == 0)
        await page.fill('#hd', ''); await save_note()
        check('an empty date: "Choose a date."', 'Choose a date.' in await page.inner_text('#hderr'))
        await page.fill('#hd', day(-3))
        await page.fill('#htm', '1745')
        check('typing 1745 gives 17:45', await page.input_value('#htm') == '17:45', await page.input_value('#htm'))
        await page.fill('#htm', '2460'); await save_note()
        check('24:60 is refused: "Enter a time between 00:00 and 23:59."', 'Enter a time between 00:00 and 23:59.' in await page.inner_text('#htmerr') and await notes() == [], await page.inner_text('#htmerr'))
        await page.fill('#htm', '')
        await save_note()
        check('an empty time is refused', await page.locator('#htmerr:visible').count() == 1)
        await page.fill('#htm', '8:30'); await page.click('#hx')
        check('8:30 becomes 08:30 when the field is left', await page.input_value('#htm') == '08:30', await page.input_value('#htm'))
        await page.click('#htm'); await page.keyboard.press('Enter'); await page.wait_for_selector('#hx', state='detached')
        n = await notes()
        check('Enter in the time field saves; a past day is accepted', len(n) == 1 and n[0]['d'] == day(-3) and n[0]['tm'] == '08:30', n)
        check('the entry did not create or change anything in the food diary', await T("() => window.__tapnaplo.S.log.length") == 0)
        # order: day, then time, then the time made; newest first
        await seed([note(1, '2026-10-01', '09:00', t=5000), note(2, '2026-10-03', '07:00', t=1000), note(3, '2026-10-03', '18:30', t=2000), note(4, '2026-10-03', '18:30', t=9000), note(5, '2026-09-30', '23:59', t=99999)])
        await go_health()
        order = await page.locator('.health-row').evaluate_all("(rs) => rs.map((r) => r.dataset.id)")
        check('order: newest day first, then later time, then the one made later; two notes at the same minute keep a stable order', order == ['n4', 'n3', 'n2', 'n1', 'n5'], order)
        await T("() => { const t = window.__tapnaplo; t.S.health.reverse(); t.render(); }")
        order2 = await page.locator('.health-row').evaluate_all("(rs) => rs.map((r) => r.dataset.id)")
        check('...whatever the stored order', order2 == order, order2)
        check('the count says "5 notes"', (await page.inner_text('.health-count')).strip() == '5 notes')

        # =========================================================== 5 the list
        long = 'Fejfájás délután, a bal halánték körül, kb. 2 órán át, a második kávé után kezdődött, és az ibuprofen sem segített igazán. Este jobb lett.'
        exact100 = ('x' * 99) + 'é'
        flat = 'first line\n\n   second    line\twith tabs\r\nthird'
        emoji150 = '😀' * 150
        await seed([note(1, day(-1), '10:00', x=long), note(2, day(-2), '10:00', x=exact100), note(3, day(-3), '10:00', x=exact100 + 'y'), note(4, day(-4), '10:00', x=flat), note(5, day(-5), '10:00', x=emoji150), note(6, day(-6), '10:00', x='short')])
        await go_health()
        prevs = await page.locator('.health-prev').all_inner_texts()
        check('a long note shows its first 100 characters and "…"', prevs[0] == preview(long) and prevs[0].endswith('…') and len(prevs[0]) == 101, prevs[0])
        check('exactly 100 characters: no "…"', prevs[1] == exact100, prevs[1])
        check('101 characters: the first 100 and "…"', prevs[2] == exact100 + '…' and len(prevs[2]) == 101, prevs[2])
        check('line breaks, tabs and repeated spaces become one space', prevs[3] == 'first line second line with tabs third', prevs[3])
        check('150 emoji: the first 100 whole emoji and "…" (none is cut in half)', prevs[4] == '😀' * 100 + '…', (len(prevs[4]), prevs[4][-3:]))
        check('a short note is shown as it is, without "…"', prevs[5] == 'short')
        # the preview is text, not HTML
        await seed([note(1, day(-1), '10:00', x='<img src=x onerror="window.__pwn=1"><b>bold</b> & "quotes"')])
        await go_health(); await page.wait_for_timeout(100)
        check('HTML in a note is shown as text and does not run', await page.locator('.health-prev').inner_text() == '<img src=x onerror="window.__pwn=1"><b>bold</b> & "quotes"' and await T("() => window.__pwn") is None and await page.locator('.health-prev b, .health-prev img').count() == 0)
        # Show older notes
        many = [note(i, (D - timedelta(days=i // 10)).isoformat(), f'{i % 24:02d}:{i % 60:02d}', x=f'note number {i}', t=1700000000000 + i) for i in range(250)]
        await seed(many)
        await go_health()
        check('250 notes: 100 rows and "Show older notes"; the count says 250 notes', await page.locator('.health-row').count() == 100 and await page.locator('[data-act=health-more]').count() == 1 and (await page.inner_text('.health-count')).strip() == '250 notes')
        await page.click('[data-act=health-more]')
        check('Show older notes adds 100 more', await page.locator('.health-row').count() == 200 and await page.locator('[data-act=health-more]').count() == 1)
        await page.click('[data-act=health-more]')
        check('...and then the last 50; the button is gone', await page.locator('.health-row').count() == 250 and await page.locator('[data-act=health-more]').count() == 0)
        await page.click('[data-tab=log]'); await page.click('[data-tab=health]')
        check('coming back to the tab starts with 100 rows again', await page.locator('.health-row').count() == 100)
        # exactly 100 notes: no button
        await seed(many[:100]); await go_health()
        check('exactly 100 notes: no "Show older notes"', await page.locator('.health-row').count() == 100 and await page.locator('[data-act=health-more]').count() == 0)

        # =========================================================== 6 view and edit
        text = 'Line one\n\nLine two with <b>tags</b> & "quotes"\n  indented line\n' + 'z' * 1200 * 0
        nid = 'v1'
        await seed([{**note(1, day(-2), '16:25', 'symptom', text.strip('\n'), t=1761750000000), 'id': nid}, note(2, day(-1), '09:00', 'event', 'second')])
        await go_health()
        await page.click(f'[data-id={nid}]'); await page.wait_for_selector('#hedit'); await page.wait_for_timeout(300)
        title = await page.inner_text('.sheet-h h2')
        check('the note opens: the title is the long date and the time', title.endswith(', 16:25') and 'October' in title, title)
        body = await page.inner_text('.health-text')
        check('the full text is shown with its line breaks (and tags as text)', body == 'Line one\n\nLine two with <b>tags</b> & "quotes"\n  indented line', repr(body))
        ws = await T("() => getComputedStyle(document.querySelector('.health-text')).whiteSpace")
        check('...white-space is pre-wrap', ws == 'pre-wrap', ws)
        check('the label is shown as a word', 'Symptom' in await page.inner_text('.sheet-b .label-chip'))
        check('a note that was never edited has no "Edited" line', 'Edited' not in await page.inner_text('.sheet-b'))
        check('the buttons are Edit and Delete', await page.locator('.sheet-actions button').all_inner_texts() == ['Delete', 'Edit'])
        # the long text of 1000 characters is whole in the sheet
        await close_sheet()
        big = ('Ö' * 99 + '\n') * 9 + 'Ö' * 100
        await seed([note(1, day(-1), '08:00', 'observation', big, t=1761750000000)])
        await go_health(); await page.click('[data-id=n1]'); await page.wait_for_selector('#hedit')
        check('a 1000-character note is shown whole in its sheet', len(big) == 1000 and await page.inner_text('.health-text') == big, len(await page.inner_text('.health-text')))
        await close_sheet()
        # edit
        await seed([{**note(1, day(-2), '16:25', 'symptom', 'old text', t=1761750000000), 'id': 'e1'}])
        await go_health(); await page.click('[data-id=e1]'); await page.wait_for_selector('#hedit'); await page.click('#hedit'); await page.wait_for_selector('#hx'); await page.wait_for_timeout(300)
        check('Edit opens "Edit note" with the saved values, no draft banner, and the button "Save changes"', await page.inner_text('.sheet-h h2') == 'Edit note' and await page.input_value('#hx') == 'old text' and await page.input_value('#hd') == day(-2) and await page.input_value('#htm') == '16:25' and await page.locator('#hdraft').count() == 0 and await page.inner_text('#hsave') == 'Save changes')
        check('...the saved label is pressed', await page.locator('#hlabels [aria-pressed=true]').all_inner_texts() == ['Symptom'])
        check('...the counter shows the saved length', (await page.inner_text('#hcount')).strip() == '8 / 1000')
        await save_note(); await page.wait_for_selector('#hx', state='detached')
        check('saving without a change is not an edit (no "e")', 'e' not in (await notes())[0])
        await page.click('[data-id=e1]'); await page.wait_for_selector('#hedit'); await page.click('#hedit'); await page.wait_for_selector('#hx'); await page.wait_for_timeout(300)
        await page.click('#hlabels [data-l=observation]'); await page.fill('#hx', 'new text'); await page.fill('#hd', day(-3)); await page.fill('#htm', '07:05')
        await save_note(); await page.wait_for_selector('#hx', state='detached')
        e1 = (await notes())[0]
        check('edited: label, text, day and time changed; id and t stay; "e" is set', e1['label'] == 'observation' and e1['x'] == 'new text' and e1['d'] == day(-3) and e1['tm'] == '07:05' and e1['id'] == 'e1' and e1['t'] == 1761750000000 and abs(e1['e'] - await T("() => Date.now()")) < 60000, e1)
        check('the toast says "Note updated" and has Undo', 'Note updated' in await toast() and await page.locator('#toast button').count() == 1)
        check('the list shows the new text and label', 'new text' in (await rows())[0] and 'Observation' in (await rows())[0])
        await page.click('#toast button')
        e1b = (await notes())[0]
        check('Undo puts the old note back, including no "e"', e1b['label'] == 'symptom' and e1b['x'] == 'old text' and e1b['d'] == day(-2) and 'e' not in e1b, e1b)
        await page.click('[data-id=e1]'); await page.wait_for_selector('#hedit'); await page.click('#hedit'); await page.wait_for_selector('#hx'); await page.wait_for_timeout(300)
        await page.fill('#hx', 'second edit'); await save_note(); await page.wait_for_selector('#hx', state='detached')
        await page.click('[data-id=e1]'); await page.wait_for_selector('#hedit')
        edited_line = await page.locator('.sheet-b .hint').inner_text()
        check('an edited note shows "Edited <date>, <time>"', re.match(r'^Edited \d{1,2} \w{3,4} \d{4}, \d\d:\d\d$', edited_line) is not None, edited_line)
        # edit a note that another device deleted
        await T("() => { const t = window.__tapnaplo; t.S.health.length = 0; }")
        await page.click('#hedit')
        check('Edit of a note that has meanwhile been deleted says so (no crash)', 'deleted on another device' in await toast() and await page.locator('#hx').count() == 0)

        # =========================================================== 7 delete
        await seed([note(1, day(-1), '10:00', 'event', 'to delete'), note(2, day(-2), '10:00', 'event', 'keep')])
        await go_health(); await page.click('[data-id=n1]'); await page.wait_for_selector('#hdel'); await page.click('#hdel')
        check('Delete removes the note at once (no confirm dialog) with "Note deleted" and Undo', [n['id'] for n in await notes()] == ['n2'] and 'Note deleted' in await toast() and await page.locator('#toast button').count() == 1 and await page.locator('.health-row').count() == 1)
        await page.click('#toast button')
        check('Undo brings the same note back (same id and time)', sorted(n['id'] for n in await notes()) == ['n1', 'n2'] and await page.locator('.health-row').count() == 2)
        check('...in the right place in the list', (await page.locator('.health-row').first.get_attribute('data-id')) == 'n1')

        # =========================================================== 8 the draft
        await seed([])
        await open_add(); await page.click('#hlabels [data-l=event]'); await page.fill('#hx', 'Started magnesium 400 mg')
        d_raw = await T("(k) => localStorage.getItem(k)", 'nutrilog.healthDraft')
        check('typing keeps a draft on the device (label and text)', json.loads(d_raw) == {'label': 'event', 'x': 'Started magnesium 400 mg'}, d_raw)
        await page.click('#hcancel'); await page.wait_for_selector('.sheet', state='detached')
        check('Cancel keeps the draft and saves nothing', await notes() == [] and (await T("(k) => localStorage.getItem(k)", 'nutrilog.healthDraft')) is not None)
        await page.click('[data-act=health-add]'); await page.wait_for_selector('#hx'); await page.wait_for_timeout(300)
        check('the next Add note brings the draft back: "Draft restored", text and label', 'Draft restored' in await page.inner_text('#hdraft') and await page.input_value('#hx') == 'Started magnesium 400 mg' and await page.locator('#hlabels [aria-pressed=true]').all_inner_texts() == ['Event'])
        check('...date and time are the present, not the old ones', await page.input_value('#hd') == today)
        check('...the counter is right', (await page.inner_text('#hcount')).strip() == '24 / 1000')
        await page.click('#hdisc')
        check('Discard draft clears the form, the banner and the stored draft', await page.input_value('#hx') == '' and await page.locator('#hdraft').count() == 0 and await page.locator('#hlabels [aria-pressed=true]').count() == 0 and (await T("(k) => localStorage.getItem(k)", 'nutrilog.healthDraft')) is None)
        await page.fill('#hx', 'second draft'); await page.click('#hlabels [data-l=symptom]'); await save_note(); await page.wait_for_selector('#hx', state='detached')
        check('saving the note clears the draft', (await T("(k) => localStorage.getItem(k)", 'nutrilog.healthDraft')) is None and len(await notes()) == 1)
        await page.click('[data-act=health-add]'); await page.wait_for_selector('#hx'); await page.wait_for_timeout(300)
        check('...the next form is empty', await page.input_value('#hx') == '' and await page.locator('#hdraft').count() == 0)
        await page.fill('#hx', '');
        check('an emptied text leaves no draft', (await T("(k) => localStorage.getItem(k)", 'nutrilog.healthDraft')) is None)
        await page.fill('#hx', 'draft that survives a reload'); await close_sheet()
        await page.reload(); await page.wait_for_selector('.health-bar')
        await page.click('[data-act=health-add]'); await page.wait_for_selector('#hx'); await page.wait_for_timeout(300)
        check('the draft survives closing and opening the app again', await page.input_value('#hx') == 'draft that survives a reload')
        await page.click('#hdisc'); await close_sheet()
        # editing never uses the draft
        await T("(k) => localStorage.setItem(k, JSON.stringify({ label: 'event', x: 'stale draft' }))", 'nutrilog.healthDraft')
        await page.click('.health-row'); await page.wait_for_selector('#hedit'); await page.click('#hedit'); await page.wait_for_selector('#hx'); await page.wait_for_timeout(300)
        check('Edit note does not show or touch the draft', await page.input_value('#hx') == 'second draft' and await page.locator('#hdraft').count() == 0)
        await page.fill('#hx', 'edited, not a draft')
        check('...typing while editing writes no draft', json.loads(await T("(k) => localStorage.getItem(k)", 'nutrilog.healthDraft'))['x'] == 'stale draft')
        await close_sheet()
        await T("(k) => localStorage.removeItem(k)", 'nutrilog.healthDraft')
        for bad in ('not json', '[1,2]', '{"x":5}', '{"x":"  "}', 'null'):
            await T("([k, v]) => localStorage.setItem(k, v)", ['nutrilog.healthDraft', bad])
            await page.click('[data-act=health-add]'); await page.wait_for_selector('#hx'); await page.wait_for_timeout(250)
            ok = await page.input_value('#hx') == '' and await page.locator('#hdraft').count() == 0
            await close_sheet()
            check(f'a damaged draft ({bad}) is ignored', ok)
        await T("([k, v]) => localStorage.setItem(k, v)", ['nutrilog.healthDraft', json.dumps({'label': '__proto__', 'x': 'text with a bad label'})])
        await page.click('[data-act=health-add]'); await page.wait_for_selector('#hx'); await page.wait_for_timeout(250)
        check('a draft with an unknown label restores the text and no label', await page.input_value('#hx') == 'text with a bad label' and await page.locator('#hlabels [aria-pressed=true]').count() == 0)
        await page.click('#hdisc'); await close_sheet()

        # blocked localStorage
        cB = await new_ctx(scripts=[NO_LS]); B = await cB.new_page(); watch(B, 'LS')
        await B.goto(URL); await B.wait_for_selector('.hero')
        await B.click('[data-tab=health]'); await B.click('[data-act=health-add]'); await B.wait_for_selector('#hx'); await B.wait_for_timeout(300)
        await B.click('#hlabels [data-l=event]'); await B.fill('#hx', 'works without localStorage'); await B.click('#hsave'); await B.wait_for_selector('#hx', state='detached')
        check('with localStorage blocked: the note still saves, no error', len(await notes(B)) == 1 and 'Note added' in await B.inner_text('#toast span'))
        await B.click('[data-act=health-add]'); await B.wait_for_selector('#hx'); await B.wait_for_timeout(250)
        check('...and there is simply no draft', await B.input_value('#hx') == '' and await B.locator('#hdraft').count() == 0)
        await cB.close()

        # =========================================================== 9 reload, old and damaged data
        await seed([note(1, day(-1), '10:00', 'event', 'persisted')])
        await page.wait_for_timeout(400)
        await page.reload(); await page.wait_for_selector('.health-bar')
        check('after a reload the notes are there and the Health log tab is still open', await page.locator('.health-row').count() == 1 and await page.inner_text('#topbar h1') == 'Health log')
        # old save without health
        cO = await new_ctx(); O = await cO.new_page(); watch(O, 'O')
        await O.goto(URL); await O.wait_for_selector('.hero')
        await O.evaluate("""async () => { const db = await new Promise((res) => { const r = indexedDB.open('tapnaplo', 1); r.onsuccess = () => res(r.result); });
          await new Promise((res) => { const tx = db.transaction('kv', 'readwrite'); tx.objectStore('kv').put([], 'log'); tx.objectStore('kv').put({}, 'foods'); tx.objectStore('kv').put({ last: {}, portions: {}, nova: {} }, 'meta'); tx.objectStore('kv').delete('health'); tx.oncomplete = res; }); }""")
        await O.reload(); await O.wait_for_selector('.hero')
        check('an old save without notes starts fine with an empty Health log', await notes(O) == [] and await O.evaluate("() => window.__tapnaplo.S.meta.water !== undefined"))
        await O.evaluate("""async () => { const db = await new Promise((res) => { const r = indexedDB.open('tapnaplo', 1); r.onsuccess = () => res(r.result); });
          await new Promise((res) => { const tx = db.transaction('kv', 'readwrite'); tx.objectStore('kv').put([
            { id: 'ok1', t: 1761750000000, d: '2026-10-20', tm: '09:00', label: 'event', x: 'fine' },
            { id: 'bad-day', t: 1, d: '2026-02-30', tm: '09:00', label: 'event', x: 'x' },
            { id: 'bad-time', t: 1, d: '2026-10-20', tm: '24:00', label: 'event', x: 'x' },
            { id: 'bad-label', t: 1, d: '2026-10-20', tm: '09:00', label: 'bogus', x: 'x' },
            { id: 'empty', t: 1, d: '2026-10-20', tm: '09:00', label: 'event', x: '   ' },
            { id: 'ok1', t: 2, d: '2026-10-21', tm: '09:00', label: 'event', x: 'duplicate id' },
            'text', 5, null, [1], { id: 5 }], 'health'); tx.oncomplete = res; }); }""")
        await O.reload(); await O.wait_for_selector('.hero')
        got = await notes(O)
        check('damaged items in the store are left out; the valid one stays; each id once', [n['id'] for n in got] == ['ok1'] and got[0]['x'] == 'fine', got)
        check('...and the person is told (a toast)', 'could not be read' in await O.inner_text('#toast span') and '10 Health log notes' in await O.inner_text('#toast span'), await O.inner_text('#toast span'))
        await O.evaluate("""async () => { const db = await new Promise((res) => { const r = indexedDB.open('tapnaplo', 1); r.onsuccess = () => res(r.result); });
          await new Promise((res) => { const tx = db.transaction('kv', 'readwrite'); tx.objectStore('kv').put({ not: 'a list' }, 'health'); tx.oncomplete = res; }); }""")
        await O.reload(); await O.wait_for_selector('.hero')
        check('"health" that is not a list: an empty log, no crash', await notes(O) == [])
        await cO.close()
        # cleanNote on its own
        r = await T("""() => { const t = window.__tapnaplo, c = t.cleanNote, base = { id: 'a', t: 1761750000000, d: '2026-10-20', tm: '09:00', label: 'event', x: ' hi ' };
          const long = (n) => 'a'.repeat(n);
          return {
            trim: c(base).x, extra: Object.keys(c({ ...base, junk: 1, __proto__: { z: 1 }, e: 1761760000000 })).sort().join(),
            noT: c({ ...base, t: undefined }).t === new Date(2026, 9, 20, 12).getTime(), badT: c({ ...base, t: -5 }).t === new Date(2026, 9, 20, 12).getTime(), hugeT: c({ ...base, t: 1e18 }).t === new Date(2026, 9, 20, 12).getTime(),
            badE: 'e' in c({ ...base, e: 'x' }) || 'e' in c({ ...base, e: -1 }), l1000: !!c({ ...base, x: long(1000) }), l1001: c({ ...base, x: long(1001) }),
            emoji: !!c({ ...base, x: '😀'.repeat(1000) }), emoji1001: c({ ...base, x: '😀'.repeat(1001) }), idNum: c({ ...base, id: 5 }), idEmpty: c({ ...base, id: '' }), idLong: c({ ...base, id: long(101) }),
            arr: c([base]), nul: c(null), str: c('x'), xNum: c({ ...base, x: 5 }), dayText: c({ ...base, d: '20 Oct' }), time: [c({ ...base, tm: '9:00' }), c({ ...base, tm: '23:59' }) && 'ok'],
            protoId: c({ ...base, id: '__proto__' }) && 'ok', polluted: ({}).z === undefined && Object.getPrototypeOf(c(base)) === Object.prototype };
        }""")
        check('cleanNote: trims the text, keeps only id, t, d, tm, label, x, e', r['trim'] == 'hi' and r['extra'] == 'd,e,id,label,t,tm,x', r)
        check('cleanNote: a missing, negative or huge t becomes noon of the day; a bad e is dropped', r['noT'] and r['badT'] and r['hugeT'] and not r['badE'], r)
        check('cleanNote: 1000 characters pass, 1001 do not (emoji count once)', r['l1000'] and r['l1001'] is None and r['emoji'] and r['emoji1001'] is None, r)
        check('cleanNote: bad id, list, null, text, number text, bad day or time are refused', r['idNum'] is None and r['idEmpty'] is None and r['idLong'] is None and r['arr'] is None and r['nul'] is None and r['str'] is None and r['xNum'] is None and r['dayText'] is None and r['time'][0] is None, r)
        check('cleanNote: the id "__proto__" is only a name (a plain object, nothing polluted)', r['protoId'] == 'ok' and r['polluted'])

        # =========================================================== 10 backup JSON and Restore
        await seed([note(1, day(-1), '10:00', 'event', 'in the backup', e=1761760000000), note(2, day(-2), '11:00', 'symptom', 'second')])
        await page.click('[data-tab=data]'); await page.wait_for_selector('[data-act=export-json]')
        async with page.expect_download() as dl:
            await page.click('[data-act=export-json]')
        bk = json.loads(pathlib.Path(await (await dl.value).path()).read_text())
        check('the backup JSON has a "health" list with the notes', bk.get('app') == 'tapnaplo' and [n['id'] for n in bk['health']] == ['n1', 'n2'] and bk['health'][0]['x'] == 'in the backup' and bk['health'][0]['e'] == 1761760000000, list(bk))
        check('...next to log, foods and meta (those are unchanged)', all(k in bk for k in ('log', 'foods', 'meta')))

        async def restore(obj, pg=None, confirm=True):
            pg = pg or page
            await pg.set_input_files('#importfile', files=[{'name': 'b.json', 'mimeType': 'application/json', 'buffer': json.dumps(obj).encode()}])
            await pg.wait_for_selector('.sheet, #toast', timeout=5000)
            if confirm and await pg.locator('.sheet [data-ok]').count():
                text = await pg.inner_text('.sheet-b p')
                await pg.click('.sheet [data-ok]'); await pg.wait_for_selector('.sheet', state='detached')
                return text
            return None
        base = {'app': 'tapnaplo', 'version': 1, 'log': [], 'foods': {}, 'meta': {}}
        txt = await restore({**base, 'health': [note(7, '2026-10-01', '08:00', 'observation', 'restored one'), note(8, '2026-10-02', '08:00', 'event', 'restored two')]})
        check('Restore with a "health" part: the confirm text names the notes', txt is not None and '2 Health log notes' in txt, txt)
        check('...and replaces the notes', sorted(n['id'] for n in await notes()) == ['n7', 'n8'])
        txt = await restore({**base, 'health': []})
        check('a backup with an empty "health" list clears the notes (it is an intended replace)', await notes() == [] and '0 Health log notes' in txt, txt)
        await seed([note(1, day(-1), '10:00', 'event', 'mine')])
        txt = await restore(base)
        check('a backup from before version 25 (no "health") leaves the notes alone', [n['id'] for n in await notes()] == ['n1'], await notes())
        check('...and the confirm text says so', 'Your Health log note is not in this file, so it stays as it is.' in txt, txt)
        txt = await restore({**base, 'health': [note(1, '2026-10-01', '08:00', 'event', 'ok'), note(2, '2026-02-30', '08:00', 'event', 'bad day'), {'id': 'x'}, 'junk', note(1, '2026-10-02', '08:00', 'event', 'same id'), note(3, '2026-10-03', '08:00', 'bogus', 'bad label')]})
        check('invalid items in the file are skipped and counted in the confirm text and in the toast', '5 notes in the file are not valid and will be skipped' in txt and '5 notes skipped: not valid' in await toast() and [n['id'] for n in await notes()] == ['n1'], (txt, await toast()))
        before = await notes()
        await page.set_input_files('#importfile', files=[{'name': 'b.json', 'mimeType': 'application/json', 'buffer': json.dumps({**base, 'health': {'a': 1}}).encode()}])
        await page.wait_for_selector('#toast')
        check('"health" that is not a list: the file is refused with a message and nothing changes', 'Health log part of this file is not a list' in await toast() and await notes() == before and await page.locator('.sheet').count() == 0, await toast())
        hostile = '{"app":"tapnaplo","version":1,"log":[],"foods":{},"meta":{},"health":[{"id":"__proto__","t":1761750000000,"d":"2026-10-01","tm":"08:00","label":"event","x":"<img src=x onerror=window.__pwn2=1>"},{"id":"c","t":1761750000000,"d":"2026-10-01","tm":"08:00","label":"event","x":"ok","__proto__":{"polluted":1},"constructor":"x"}]}'
        await page.set_input_files('#importfile', files=[{'name': 'b.json', 'mimeType': 'application/json', 'buffer': hostile.encode()}])
        await page.wait_for_selector('.sheet [data-ok]'); await page.click('.sheet [data-ok]'); await page.wait_for_selector('.sheet', state='detached')
        got = await notes()
        check('hostile backup: "__proto__" as an id and extra keys are only data; nothing is polluted', len(got) == 2 and all(set(n) <= {'id', 't', 'd', 'tm', 'label', 'x', 'e'} for n in got) and await T("() => ({}).polluted === undefined && ({}).constructor === Object"), got)
        await go_health(); await page.wait_for_timeout(100)
        check('...and the HTML in a restored note is shown as text', await T("() => window.__pwn2") is None and await page.locator('.health-prev img').count() == 0)

        # =========================================================== 11 CSV
        tricky = 'He said "stop", then\nleft; ok? ,,'
        await seed([note(1, '2026-10-03', '09:00', 'event', 'plain'), note(2, '2026-10-01', '23:30', 'symptom', tricky, e=1761760000000), note(3, '2026-10-01', '08:15', 'observation', 'ünï ✓ 😀'), note(4, '2026-10-01', '08:15', 'event', 'same minute, made later', t=1700000009999)])
        await page.click('[data-tab=data]'); await page.wait_for_selector('[data-act=export-health]')
        check('the Data tab has a "Health log (CSV)" button next to the other two', await page.locator('[data-act=export-health]').inner_text() == 'Health log (CSV)')
        async with page.expect_download() as dl:
            await page.click('[data-act=export-health]')
        dlv = await dl.value
        raw = pathlib.Path(await dlv.path()).read_bytes()
        check('the file is named nutrilog-health-log-<date>.csv, UTF-8 with a BOM', re.fullmatch(r'nutrilog-health-log-\d{4}-\d{2}-\d{2}\.csv', dlv.suggested_filename) is not None and raw.startswith(b'\xef\xbb\xbf'), dlv.suggested_filename)
        rows_ = list(csv.reader(io.StringIO(raw.decode('utf-8-sig'), newline='')))
        check('columns: date, time, label, note, edited', rows_[0] == ['date', 'time', 'label', 'note', 'edited'], rows_[0])
        check('oldest note first (day, then time, then the time made)', [r[3][:6] for r in rows_[1:]] == ['ünï ✓ ', 'same m', 'He sai', 'plain'], [r[3][:6] for r in rows_[1:]])
        check('a text with a quote, a comma, a line break and a semicolon comes back unchanged', rows_[3][3] == tricky, rows_[3])
        check('label is the plain word; "edited" is "YYYY-MM-DD HH:MM" for an edited note and empty otherwise', rows_[3][2] == 'symptom' and re.fullmatch(r'\d{4}-\d{2}-\d{2} \d\d:\d\d', rows_[3][4]) is not None and rows_[1][4] == '' and rows_[4][4] == '', [r[4] for r in rows_[1:]])
        check('emoji and accents survive', rows_[1][3] == 'ünï ✓ 😀')
        await seed([])
        await page.click('[data-tab=data]')
        async with page.expect_download() as dl:
            await page.click('[data-act=export-health]')
        rows_ = list(csv.reader(io.StringIO(pathlib.Path(await (await dl.value).path()).read_bytes().decode('utf-8-sig'), newline='')))
        check('with no notes the file has only the header row', rows_ == [['date', 'time', 'label', 'note', 'edited']], rows_)
        # the food CSVs do not change
        await T("() => { const t = window.__tapnaplo; t.S.health = [{ id: 'q', t: 1, d: '2026-10-01', tm: '08:00', label: 'event', x: 'x' }]; t.S.meta.water = {}; t.save(); }")
        async with page.expect_download() as dl:
            await page.click('[data-act=export-days]')
        days_rows = list(csv.reader(io.StringIO(pathlib.Path(await (await dl.value).path()).read_bytes().decode('utf-8-sig'), newline='')))
        check('the Daily totals CSV does not change because of notes (no extra column, no extra day)', len(days_rows) == 1 and days_rows[0][:4] == ['date', 'entries', 'est_share', 'water_intake_ml'] and 'note' not in days_rows[0] and 'health' not in ' '.join(days_rows[0]), days_rows[0][:6])

        # =========================================================== 12 nothing counted in the food totals
        await seed([note(i, today, '10:00', 'symptom', 'sugar 100 g, 500 kcal') for i in range(5)])
        await page.click('[data-tab=log]')
        check('notes never change the Diary: Energy stays 0 and no entries exist', (await page.inner_text('.hero-num')).replace('kcal', '').strip() == '0' and await T("() => window.__tapnaplo.S.log.length") == 0)
        await page.click('[data-tab=nutr]')
        check('...nor the Nutrients tab', 'Nothing logged' in await page.inner_text('#view') or await T("() => window.__tapnaplo.totalsFor([]).n") == 0)

        # =========================================================== 13 Sync with a fake GitHub
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
        ctxA, A = await device('SA')
        t_oct = int(datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc).timestamp() * 1000)
        t_dec = int(datetime(2025, 12, 31, 23, 30, tzinfo=timezone.utc).timestamp() * 1000)
        await seed([note(1, '2026-10-15', '14:00', 'symptom', 'headache', t=t_oct), note(2, '2026-01-02', '08:00', 'event', 'old december note', t=t_dec)], A)
        await connect(A)
        files = sorted(gh.files)
        check('sync: notes go to health/YYYY-MM.json by the month they were MADE (UTC)', 'health/2026-10.json' in files and 'health/2025-12.json' in files, files)
        recs = gh.recs()
        check('sync: one record per note, h:<id>, holding the whole note', recs.get('h:n1', {}).get('x', {}).get('x') == 'headache' and recs.get('h:n2', {}).get('x', {}).get('label') == 'event' and recs['h:n1']['x']['id'] == 'n1', {k: v for k, v in recs.items() if k.startswith('h:')})
        check('sync: each file holds only the notes of its month', set(json.loads(gh.files['health/2025-12.json'])['recs']) == {'h:n2'})
        ctxB, B2 = await device('SB')
        await connect(B2)
        got = await notes(B2)
        check('sync: the second device gets both notes, whole', sorted(n['id'] for n in got) == ['n1', 'n2'] and [n for n in got if n['id'] == 'n1'][0]['x'] == 'headache' and [n for n in got if n['id'] == 'n1'][0]['t'] == t_oct, got)
        # a new note added in the app on B, received by A
        await B2.click('[data-tab=health]'); await B2.click('[data-act=health-add]'); await B2.wait_for_selector('#hx'); await B2.wait_for_timeout(300)
        await B2.click('#hlabels [data-l=observation]'); await B2.fill('#hx', 'added on B with ü and 😀'); await B2.click('#hsave'); await B2.wait_for_selector('#hx', state='detached')
        await B2.wait_for_timeout(300); await sync(B2); await sync(A)
        gotA = await notes(A)
        check('sync: a note added in the app on B reaches A', any(n['x'] == 'added on B with ü and 😀' and n['label'] == 'observation' for n in gotA) and len(gotA) == 3, gotA)
        # edit the date of a note into another month: the record stays in its file
        await A.evaluate("() => { const t = window.__tapnaplo, n = t.S.health.find((x) => x.id === 'n1'); n.d = '2026-12-24'; n.e = Date.now(); t.save(); }")
        await A.wait_for_timeout(300); await sync(A); await sync(B2)
        in_files = {p: sorted(json.loads(t_)['recs']) for p, t_ in gh.files.items() if p.startswith('health/')}
        check('sync: editing the date of a note does not move its record to another file', 'h:n1' in in_files['health/2026-10.json'] and not any('h:n1' in v for p, v in in_files.items() if p != 'health/2026-10.json'), in_files)
        nB = [n for n in await notes(B2) if n['id'] == 'n1'][0]
        check('sync: the edit (day and "e") reaches B', nB['d'] == '2026-12-24' and 'e' in nB, nB)
        # the same note edited on both: the later edit wins
        await A.evaluate("() => { const t = window.__tapnaplo, n = t.S.health.find((x) => x.id === 'n1'); n.x = 'edit on A'; n.e = Date.now(); t.save(); }")
        await A.wait_for_timeout(300); await sync(A)
        await B2.evaluate("() => { const t = window.__tapnaplo, n = t.S.health.find((x) => x.id === 'n1'); n.x = 'edit on B, later'; n.e = Date.now(); t.save(); }")
        await B2.wait_for_timeout(300); await sync(B2); await sync(A)
        xa = [n for n in await notes(A) if n['id'] == 'n1'][0]['x']; xb = [n for n in await notes(B2) if n['id'] == 'n1'][0]['x']
        check('sync: the same note edited on both devices: the later edit wins, as a whole note', xa == xb == 'edit on B, later', (xa, xb))
        # delete on A -> tombstone -> B
        await A.evaluate("() => { const t = window.__tapnaplo, i = t.S.health.findIndex((x) => x.id === 'n2'); t.S.health.splice(i, 1); t.save(); }")
        await A.wait_for_timeout(300); await sync(A); await sync(B2)
        check('sync: a deleted note becomes a tombstone and disappears on B', 'n2' not in [n['id'] for n in await notes(B2)] and gh.recs().get('h:n2', {}).get('x', 'missing') is None, (await notes(B2), gh.recs().get('h:n2')))
        # a note open in a sheet on B is changed in place when A edits it
        await B2.click('[data-tab=health]'); await B2.click('[data-id=n1]'); await B2.wait_for_selector('#hedit')
        await A.evaluate("() => { const t = window.__tapnaplo, n = t.S.health.find((x) => x.id === 'n1'); n.x = 'third edit'; n.e = Date.now(); t.save(); }")
        await A.wait_for_timeout(300); await sync(A); await sync(B2)
        check('sync: a received change leaves an open note sheet alone; the list shows it once the sheet is closed', await B2.locator('#hedit').count() == 1)
        await B2.click('.sheet [data-x]'); await B2.wait_for_selector('.sheet', state='detached')
        check('...and then the list has the new text', any('third edit' in t_ for t_ in await B2.locator('.health-row').all_inner_texts()), await B2.locator('.health-row').all_inner_texts())
        # bad records in the repository
        u_big = 99999999999999
        good = {'id': 'g1', 't': t_oct, 'd': '2026-10-02', 'tm': '10:00', 'label': 'event', 'x': 'from the repository'}
        gh.files['health/2026-10.json'] = json.dumps({'app': 'tapnaplo-sync', 'v': 1, 'recs': {
            'h:g1': {'u': u_big, 'x': good},
            'h:wrong': {'u': u_big, 'x': {**good, 'id': 'other'}},
            'h:long': {'u': u_big, 'x': {**good, 'id': 'long', 'x': 'a' * 1001}},
            'h:bogus': {'u': u_big, 'x': {**good, 'id': 'bogus', 'label': 'nope'}},
            'h:day': {'u': u_big, 'x': {**good, 'id': 'day', 'd': '2026-02-30'}},
            'h:time': {'u': u_big, 'x': {**good, 'id': 'time', 'tm': '24:00'}},
            'h:list': {'u': u_big, 'x': [1, 2]}, 'h:text': {'u': u_big, 'x': 'text'}, 'h:num': {'u': u_big, 'x': 5},
            'h:': {'u': u_big, 'x': None}, 'h:junk': {'u': u_big, 'x': {**good, 'id': 'junk', 'extra': 'dropped', '__proto__': {'polluted': 1}}}}})
        await sync(A)
        gotA = await notes(A)
        ids = sorted(n['id'] for n in gotA)
        check('sync: only valid notes are taken from the repository (a wrong id, too long, unknown label, bad day, bad time, list, text, number are ignored)', 'g1' in ids and 'junk' in ids and not any(i in ids for i in ('wrong', 'other', 'long', 'bogus', 'day', 'time', 'list', 'text', 'num')), ids)
        check('...extra keys of a remote note are dropped; nothing is polluted', set([n for n in gotA if n['id'] == 'junk'][0]) <= {'id', 't', 'd', 'tm', 'label', 'x', 'e'} and await A.evaluate("() => ({}).polluted === undefined"))
        check('sync: an older app (version 24) would not read the health/ folder at all', all(OLD_SHARD.match(p) is None for p in gh.files if p.startswith('health/')) and OLD_SHARD.match('water/2026.json') is not None)
        # a file in the folder that is not a Nutrilog sync file stops the sync with a message
        gh.files['health/2026-11.json'] = '{"hello": "world"}'
        await A.evaluate("window.__tapnaplo.syncRun('manual')"); await A.wait_for_function('!window.__tapnaplo.SY.busy')
        check('sync: a foreign file in health/ stops the sync with a clear message', 'health/2026-11.json' in await A.evaluate("() => window.__tapnaplo.SY.err"), await A.evaluate("() => window.__tapnaplo.SY.err"))
        await ctxA.close(); await ctxB.close()

        # =========================================================== 14 Share
        await T("""([d1]) => { const t = window.__tapnaplo; t.S.log.length = 0; t.S.foods = {}; t.S.meta.water = {};
          t.S.log.push({ id: 'a1', d: d1, m: 'm1', f: 'u:oat', a: 100, t: 1, tm: '08:00' });
          t.S.foods['u:oat'] = { id: 'u:oat', src: 'user', name: 'Oat', brand: '', barcode: '', basis: { qty: 100, unit: 'g' }, n: { kcal: 370, protein: 13 }, nova: null, portions: [], note: '', created: 1, updated: 1 };
          t.S.health = [{ id: 'h1', t: 1761750000000, d: d1, tm: '09:00', label: 'symptom', x: 'SECRET-HEALTH-NOTE-TEXT' }]; t.save(); t.render(); }""", [day(-1)])
        snapj = await T("([a, b]) => window.__tapnaplo.shareSnapshot(a, b).json", [day(-6), day(0)])
        check('share: the snapshot has the diary but not the notes', 'SECRET-HEALTH-NOTE-TEXT' not in snapj and 'health' not in json.loads(snapj) and json.loads(snapj)['days'] != {}, list(json.loads(snapj)))
        made = await T("([a, b]) => window.__tapnaplo.shareLink(a, b).then((r) => r.url)", [day(-6), day(0)])
        check('share: the decoded link has no note text and no "health" key', 'SECRET-HEALTH-NOTE-TEXT' not in json.dumps(unpack(made)) and 'health' not in unpack(made) and 'SECRET' not in made)
        await page.click('[data-tab=data]'); await page.wait_for_selector('[data-act=share]'); await page.click('[data-act=share]'); await page.wait_for_selector('#sh-info')
        check('the Share sheet says "Health log notes are not included in the link."', 'Health log notes are not included in the link.' in await page.inner_text('.sheet-b'))
        await page.click('.sheet [data-x]')

        async def viewer(url, w=390):
            c = await new_ctx(w=w, scripts=[WATCH])
            pg = await c.new_page(); watch(pg, 'V')
            await pg.goto(url); await pg.wait_for_selector('.hero, .card', timeout=15000)
            return c, pg
        cV, V = await viewer(made)
        vtabs = await V.locator('#tabbar .tab span').all_inner_texts()
        check('viewer: only the Diary and Nutrients tabs, no Health log tab', vtabs == ['Diary', 'Nutrients'], vtabs)
        check('viewer: the tab bar has two columns', await V.evaluate("() => getComputedStyle(document.querySelector('#tabbar')).gridTemplateColumns.split(' ').length") == 2)
        check('viewer: the page holds no notes', await notes(V) == [] and 'SECRET' not in await V.content())
        await V.evaluate("() => { for (const [id, a] of [['f1', 'health-add'], ['f2', 'health-open'], ['f3', 'export-health']]) { const b = document.createElement('button'); b.dataset.act = a; b.dataset.id = 'h1'; b.id = id; document.body.append(b); } const t = document.createElement('button'); t.dataset.act = 'tab'; t.dataset.tab = 'health'; t.id = 'f4'; document.body.append(t); }")
        for fid in ('f1', 'f2', 'f3', 'f4'):
            await V.evaluate("(i) => document.getElementById(i).click()", fid)
        await V.wait_for_timeout(300)
        check('viewer: forged Health log buttons do nothing (no sheet, no tab, no download)', await V.locator('.sheet').count() == 0 and await V.evaluate("() => window.__tapnaplo.S.tab") in ('log', 'nutr') and await V.locator('.health-bar').count() == 0)
        w = await V.evaluate("() => window.__w")
        check('viewer: nothing was written (IndexedDB not opened, no localStorage write)', w == {'idbOpen': 0, 'idbWrite': 0, 'lsWrite': 0}, w)
        await cV.close()

        # =========================================================== 15 look and touch
        await seed([note(1, day(-1), '10:00', 'symptom', long), note(2, day(-2), '09:00', 'event', 'second'), note(3, day(-3), '08:00', 'observation', 'third')])
        await go_health()
        small = await T(SIZES, '.health-bar button, .health-row, #tabbar .tab')
        check('tab bar, Add note and every row are at least 44 x 44 px', small == [], small)
        await T("() => document.documentElement.setAttribute('data-theme', 'light')")
        check('contrast of the list and the tab bar in light mode', await T(CONTRAST_JS, '#view') == [] and await T(CONTRAST_JS, '#tabbar') == [], (await T(CONTRAST_JS, '#view'), await T(CONTRAST_JS, '#tabbar')))
        if SHOTS: await page.screenshot(path=os.path.join(SHOTS, 'health_list_light.png'))
        await T("() => document.documentElement.setAttribute('data-theme', 'dark')")
        check('contrast of the list and the tab bar in dark mode', await T(CONTRAST_JS, '#view') == [] and await T(CONTRAST_JS, '#tabbar') == [], (await T(CONTRAST_JS, '#view'), await T(CONTRAST_JS, '#tabbar')))
        if SHOTS: await page.screenshot(path=os.path.join(SHOTS, 'health_list_dark.png'))
        await page.click('[data-id=n1]'); await page.wait_for_selector('#hedit'); await page.wait_for_timeout(300)
        check('note sheet: buttons 44 px, contrast in dark mode', await T(SIZES, '.sheet button') == [] and await T(CONTRAST_JS, '.sheet') == [], (await T(SIZES, '.sheet button'), await T(CONTRAST_JS, '.sheet')))
        if SHOTS: await page.screenshot(path=os.path.join(SHOTS, 'health_note_dark.png'))
        await T("() => document.documentElement.setAttribute('data-theme', 'light')")
        check('note sheet: contrast in light mode', await T(CONTRAST_JS, '.sheet') == [])
        await page.click('#hedit'); await page.wait_for_selector('#hx'); await page.wait_for_timeout(300)
        check('form: the note, date and time fields have at least 16 px text', await T(SMALL_FONTS, '.sheet') == [], await T(SMALL_FONTS, '.sheet'))
        small = await T(SIZES, '.sheet button')
        check('form: every button is at least 44 px (labels, Cancel, Save)', small == [], small)
        check('form: the date and time fields are at least 44 px high', await T("() => [...document.querySelectorAll('#hd, #htm, #hx')].every((e) => e.getBoundingClientRect().height >= 44)"))
        check('form: Cancel and Save are in the sticky button row', await page.locator('.sheet-b > .sheet-actions').count() == 1 and await page.locator('.has-actions').count() == 1)
        check('form: time field is a text field with the numeric keypad, label "Time (24 h)"', await page.get_attribute('#htm', 'type') == 'text' and await page.get_attribute('#htm', 'inputmode') == 'numeric' and 'Time (24 h)' in await page.inner_text('.sheet-b'))
        await page.click('#hlabels [data-l=event]'); await page.fill('#hx', 'x' * 1100); await page.click('#hsave')
        check('form: contrast of the error and the red counter in light mode', await T(CONTRAST_JS, '.sheet') == [], await T(CONTRAST_JS, '.sheet'))
        await T("() => document.documentElement.setAttribute('data-theme', 'dark')")
        check('form: contrast of the error and the red counter in dark mode', await T(CONTRAST_JS, '.sheet') == [], await T(CONTRAST_JS, '.sheet'))
        if SHOTS: await page.screenshot(path=os.path.join(SHOTS, 'health_form_dark.png'))
        await T("() => document.documentElement.setAttribute('data-theme', 'light')")
        await close_sheet()
        fits = await T("""() => ({ page: document.documentElement.scrollWidth <= window.innerWidth,
          tabs: [...document.querySelectorAll('.tab')].every((t) => { const s = t.querySelector('span'), a = t.getBoundingClientRect(), b = s.getBoundingClientRect(); return b.left >= a.left - 0.5 && b.right <= a.right + 0.5 && s.scrollWidth <= s.clientWidth + 1; }),
          bar: (() => { const r = document.querySelector('#tabbar').getBoundingClientRect(); return r.left >= 0 && r.right <= window.innerWidth; })() })""")
        check('390 px: no sideways scroll, all five tab names fit', fits['page'] and fits['tabs'] and fits['bar'], fits)
        c320 = await new_ctx(w=320, h=640); p320 = await c320.new_page(); watch(p320, 'N')
        await p320.goto(URL); await p320.wait_for_selector('.hero')
        await seed([note(1, day(-1), '10:00', 'symptom', long), note(2, day(-2), '09:00', 'observation', 'x' * 400)], p320)
        await p320.click('[data-tab=health]'); await p320.wait_for_selector('.health-bar')
        fits = await p320.evaluate("""() => ({ page: document.documentElement.scrollWidth <= window.innerWidth,
          tabs: [...document.querySelectorAll('.tab')].map((t) => { const s = t.querySelector('span'), a = t.getBoundingClientRect(), b = s.getBoundingClientRect(); return [s.textContent, Math.round(b.width), Math.round(a.width), b.left >= a.left - 0.5 && b.right <= a.right + 0.5 && s.scrollWidth <= s.clientWidth + 1]; }),
          rows: [...document.querySelectorAll('.health-row')].every((r) => r.getBoundingClientRect().right <= window.innerWidth && r.scrollWidth <= r.clientWidth + 1) })""")
        check('320 px: no sideways scroll, all five tab names fit inside their tab, rows fit', fits['page'] and all(t[3] for t in fits['tabs']) and fits['rows'], fits)
        if SHOTS: await p320.screenshot(path=os.path.join(SHOTS, 'health_320.png'))
        await p320.click('[data-act=health-add]'); await p320.wait_for_selector('#hx'); await p320.wait_for_timeout(300)
        await p320.fill('#hx', 'x' * 1200)
        fits = await p320.evaluate("""() => ({ page: document.documentElement.scrollWidth <= window.innerWidth, sheet: (() => { const s = document.querySelector('.sheet-b'); return s.scrollWidth <= s.clientWidth + 1; })(),
          labels: [...document.querySelectorAll('#hlabels button')].map((b) => [b.textContent, b.scrollWidth <= b.clientWidth + 1]), actions: [...document.querySelectorAll('.sheet-actions button')].every((b) => { const r = b.getBoundingClientRect(); return r.left >= 0 && r.right <= window.innerWidth; }),
          grid: [...document.querySelectorAll('#hd, #htm')].every((e) => { const r = e.getBoundingClientRect(); return r.left >= 0 && r.right <= window.innerWidth; }) })""")
        check('320 px: the form fits (three label buttons, date and time side by side, buttons)', fits['page'] and fits['sheet'] and all(l[1] for l in fits['labels']) and fits['actions'] and fits['grid'], fits)
        if SHOTS: await p320.screenshot(path=os.path.join(SHOTS, 'health_form_320.png'))
        await c320.close()

        # the on-screen keyboard (simulated): Save note stays in view
        cK = await new_ctx(scripts=[FAKE_VV]); K = await cK.new_page(); watch(K, 'K')
        await K.goto(URL); await K.wait_for_selector('.hero')
        await K.click('[data-tab=health]'); await K.click('[data-act=health-add]'); await K.wait_for_selector('#hx'); await K.wait_for_timeout(300)
        await K.evaluate("window.__vvh = 380; window.__vv.dispatchEvent(new Event('resize'))"); await K.wait_for_timeout(150)
        pos = await K.evaluate("() => { const b = document.getElementById('hsave').getBoundingClientRect(), s = document.querySelector('.sheet').getBoundingClientRect(); return { kb: document.body.classList.contains('kb'), bottom: Math.round(b.bottom), top: Math.round(b.top), sheetBottom: Math.round(s.bottom) }; }")
        check('keyboard open: the sheet fits the visible part and "Save note" stays in view', pos['kb'] and pos['bottom'] <= 380 and pos['top'] >= 0 and pos['sheetBottom'] <= 380, pos)
        await cK.close()

        # =========================================================== 16 version
        await page.click('[data-tab=data]'); await page.wait_for_selector('[data-act=export-json]')
        m = re.search(r'Nutrilog version\s*(\d+)', await page.inner_text('#view'))
        sw = re.search(r"CACHE = 'nutrilog-v(\d+)'", (ROOT / 'sw.js').read_text())
        check('the version is 25 or newer and the same as the service worker cache', bool(m) and bool(sw) and int(m.group(1)) >= 25 and int(m.group(1)) == int(sw.group(1)), (m and m.group(1), sw and sw.group(1)))

        check('no request left this machine except the (fake) GitHub', outside == [], outside[:5])
        check('no page errors', errs == [], errs[:5])
        await browser.close()
        print('\nFAILED: ' + ', '.join(problems) if problems else '\nALL PASSED')
        sys.exit(1 if problems else 0)

asyncio.run(main())
