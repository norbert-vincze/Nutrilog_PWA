"""Entry time: stored, shown in the diary, editable, sorted, exported. Run with the web server on port 8765 (see CLAUDE.md)."""
import asyncio, csv, io
from playwright.async_api import async_playwright
URL = 'http://127.0.0.1:8765/index.html'


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        problems = []

        def check(name, ok, info=''):
            print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(info)) if info != '' else ''))
            if not ok: problems.append(name)

        ctx = await b.new_context(viewport={'width': 390, 'height': 844}, locale='en-GB', has_touch=True, is_mobile=True, reduced_motion='reduce', accept_downloads=True)
        page = await ctx.new_page()
        dialogs, errs = [], []
        page.on('dialog', lambda d: (dialogs.append(d.message), asyncio.ensure_future(d.dismiss())))
        page.on('pageerror', lambda e: errs.append(str(e)))
        T = page.evaluate
        await page.goto(URL); await page.wait_for_selector('.hero')

        async def open_food(query):
            await page.click('.act.primary'); await page.fill('#q', query)
            await page.tap('[data-pick] >> nth=0'); await page.wait_for_selector('#amt')

        times = lambda: page.locator('.entry-time').all_inner_texts()

        # ---- new entry: the Time field starts at the current time and fits the sheet
        await open_food('hard-boiled egg')
        now = await T("(()=>{const d=new Date();return d.getHours()*60+d.getMinutes()})()")
        v = await page.input_value('#tm')
        ok_fmt = len(v) == 5 and v[2] == ':'
        mins = int(v[:2]) * 60 + int(v[3:]) if ok_fmt else -999
        check('new entry: Time starts at the current time', ok_fmt and min(abs(mins - now), 1440 - abs(mins - now)) <= 1, f'{v} vs now {now}')
        box = await T("(()=>{const r=document.querySelector('#tm').getBoundingClientRect();return [Math.round(r.width),Math.round(r.height),Math.round(r.right)]})()")
        check('Time field is at least 44 px high and inside the 390 px screen', box[1] >= 44 and box[2] <= 390 and box[0] > 80, box)
        check('no sideways scrolling in the sheet', await T('document.documentElement.scrollWidth <= window.innerWidth'))
        check('Time label is visible', 'Time' in await page.inner_text('label:has(#tm)'))

        # ---- save with a chosen time; it shows in the diary
        await page.fill('#tm', '07:45'); await page.tap('#ok'); await page.wait_for_timeout(200)
        check('diary row shows 07:45', await times() == ['07:45'], await times())
        check('entry stores tm = 07:45 and keeps the creation stamp t', await T("(()=>{const e=__tapnaplo.S.log[0];return e.tm==='07:45' && Number.isFinite(e.t)})()"))

        # ---- second entry, earlier time, same meal: sorted by time
        await open_food('bread')
        check('second entry defaults to the same meal', await page.input_value('#meal') == 'm1')
        await page.fill('#tm', '06:10'); await page.tap('#ok'); await page.wait_for_timeout(200)
        check('entries of a meal are sorted by time', await times() == ['06:10', '07:45'], await times())

        # ---- edit shows the saved time and saves the new one
        await page.tap('.entry:has(.entry-time:text("07:45"))'); await page.wait_for_selector('#amt')
        check('edit entry shows the saved time', await page.input_value('#tm') == '07:45', await page.input_value('#tm'))
        await page.fill('#tm', '08:30'); await page.tap('#ok'); await page.wait_for_timeout(200)
        check('edited time is shown and sorted', await times() == ['06:10', '08:30'], await times())

        # ---- empty time is refused next to the field
        await page.tap('.entry:has(.entry-time:text("08:30"))'); await page.wait_for_selector('#amt')
        await page.fill('#tm', ''); await page.tap('#ok'); await page.wait_for_timeout(100)
        check('empty time: message shown, sheet stays open, amount message not shown',
              await page.is_visible('#tmerr') and not await page.is_visible('#amterr') and await page.is_visible('#amt'))
        check('empty time: nothing was changed', await T("__tapnaplo.S.log.filter(e=>e.tm==='08:30').length") == 1)
        check('time message sits right under the Meal/Time row', await T("document.querySelector('#tmerr').previousElementSibling.querySelector('#tm') !== null"))
        await page.fill('#amt', ''); await page.tap('#ok'); await page.wait_for_timeout(100)
        check('amount and time problems are both shown', await page.is_visible('#tmerr') and await page.is_visible('#amterr'))
        await page.fill('#amt', '60'); await page.fill('#tm', '09:00')
        check('typing a valid time hides the message', not await page.is_visible('#tmerr'))
        await page.keyboard.press('Escape'); await page.wait_for_timeout(150)
        check('closing without saving keeps the old time', await times() == ['06:10', '08:30'], await times())

        # ---- an entry from before this feature (no tm) shows the time it was added
        await T("""(()=>{const S=__tapnaplo.S, first=S.log[0]; const d=new Date(); d.setHours(5,20,0,0);
          S.log.push({id:'old1', d:S.day, m:'m1', f:first.f, a:50, t:d.getTime()}); __tapnaplo.save(); __tapnaplo.render();})()""")
        await page.wait_for_timeout(400)   # the app saves 120 ms after the last change
        check('old entry without tm shows its added time and sorts first', await times() == ['05:20', '06:10', '08:30'], await times())
        await page.tap('.entry:has(.entry-time:text("05:20"))'); await page.wait_for_selector('#amt')
        check('old entry: edit sheet is prefilled with the added time', await page.input_value('#tm') == '05:20', await page.input_value('#tm'))
        await page.keyboard.press('Escape'); await page.wait_for_timeout(150)

        # ---- survives a reload
        await page.reload(); await page.wait_for_selector('.hero'); await page.wait_for_timeout(300)
        check('times survive a reload', await times() == ['05:20', '06:10', '08:30'], await times())

        # ---- CSV has a time column
        await page.click('[data-tab=data]')
        async with page.expect_download() as d:
            await page.click('[data-act=export-entries]')
        dl = await d.value; await dl.save_as('entries_time.csv')
        rows = list(csv.reader(io.StringIO(open('entries_time.csv', encoding='utf-8-sig').read())))
        head = rows[0]
        check('CSV: second column is time', head[:3] == ['date', 'time', 'meal'], head[:4])
        check('CSV: rows carry the times in order', [r[1] for r in rows[1:]] == ['05:20', '06:10', '08:30'], [r[1] for r in rows[1:]])

        check('no native dialogs', dialogs == [], dialogs)
        check('no page errors', errs == [], errs)
        await b.close()
        print('\nPROBLEMS:', problems if problems else 'none')
        raise SystemExit(1 if problems else 0)

asyncio.run(main())
