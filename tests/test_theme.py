"""Theme setting: Auto / Light / Dark in the Data tab. Run with the web server on port 8765 (see CLAUDE.md)."""
import asyncio
from playwright.async_api import async_playwright
URL = 'http://127.0.0.1:8765/index.html'


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        problems = []

        def check(name, ok, info=''):
            print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(info)) if info != '' else ''))
            if not ok: problems.append(name)

        ctx = await b.new_context(viewport={'width': 390, 'height': 844}, locale='en-GB', color_scheme='dark', has_touch=True, is_mobile=True, reduced_motion='reduce')
        page = await ctx.new_page()
        dialogs, errs = [], []
        page.on('dialog', lambda d: (dialogs.append(d.message), asyncio.ensure_future(d.dismiss())))
        page.on('pageerror', lambda e: errs.append(str(e)))
        T = page.evaluate
        theme = lambda: T("document.documentElement.getAttribute('data-theme')")
        bg = lambda: T("getComputedStyle(document.body).backgroundColor")
        meta = lambda: T("document.querySelector('meta[name=theme-color]').getAttribute('content')")
        pressed = lambda: T("[...document.querySelectorAll('[data-act=theme]')].filter(b=>b.getAttribute('aria-pressed')==='true').map(b=>b.dataset.v)")

        # ---- first start on a dark phone: dark before the app code runs (no flash)
        await page.goto(URL, wait_until='domcontentloaded')
        check('first start follows the phone (dark), set before first paint', await theme() == 'dark' and await bg() == 'rgb(0, 0, 0)', (await theme(), await bg()))
        await page.wait_for_selector('.hero')
        await page.click('[data-tab=data]')
        check('Appearance card is on the Data tab', await page.locator('.card-t', has_text='Appearance').count() == 1)
        check('three choices: Auto, Light, Dark', await T("[...document.querySelectorAll('[data-act=theme]')].map(b=>b.textContent)") == ['Auto', 'Light', 'Dark'])
        check('Auto is selected by default', await pressed() == ['auto'], await pressed())
        sizes = await T("[...document.querySelectorAll('[data-act=theme]')].map(b=>{const r=b.getBoundingClientRect();return [Math.round(r.width),Math.round(r.height)]})")
        check('choices are at least 44 px high', all(h >= 44 and w >= 44 for w, h in sizes), sizes)

        # ---- Light on a dark phone
        await page.tap('[data-act=theme][data-v=light]'); await page.wait_for_timeout(100)
        check('Light: page turns light', await theme() == 'light' and await bg() == 'rgb(255, 255, 255)', (await theme(), await bg()))
        check('Light: the button shows it is selected', await pressed() == ['light'], await pressed())
        check('Light: browser bar colour follows', await meta() == '#ffffff', await meta())
        check('Light: saved', await T("localStorage.getItem('nutrilog.theme')") == 'light')
        await page.reload(wait_until='domcontentloaded')
        check('Light survives a reload, even on a dark phone', await theme() == 'light' and await bg() == 'rgb(255, 255, 255)', (await theme(), await bg()))
        await page.wait_for_selector('[data-act=theme]')   # the Data tab is remembered, so no .hero here
        check('Light is still on after the app started', await theme() == 'light')

        # ---- Dark on a light phone
        await page.emulate_media(color_scheme='light')
        check('Light stays light when the phone changes', await theme() == 'light')
        await page.click('[data-tab=data]')
        check('Data tab shows Light selected after reload', await pressed() == ['light'], await pressed())
        await page.tap('[data-act=theme][data-v=dark]'); await page.wait_for_timeout(100)
        check('Dark: page turns dark on a light phone', await theme() == 'dark' and await bg() == 'rgb(0, 0, 0)' and await meta() == '#000000', (await theme(), await bg(), await meta()))

        # ---- Auto follows the phone, live
        await page.tap('[data-act=theme][data-v=auto]'); await page.wait_for_timeout(100)
        check('Auto on a light phone is light', await theme() == 'light' and await pressed() == ['auto'], (await theme(), await pressed()))
        await page.emulate_media(color_scheme='dark'); await page.wait_for_timeout(150)
        check('Auto switches when the phone switches to dark', await theme() == 'dark', await theme())
        await page.emulate_media(color_scheme='light'); await page.wait_for_timeout(150)
        check('Auto switches back to light', await theme() == 'light', await theme())

        # ---- a forced choice ignores the phone
        await page.tap('[data-act=theme][data-v=dark]'); await page.wait_for_timeout(100)
        await page.emulate_media(color_scheme='light'); await page.wait_for_timeout(150)
        check('Dark stays dark when the phone is light', await theme() == 'dark', await theme())

        check('no native dialogs', dialogs == [], dialogs)
        check('no page errors', errs == [], errs)
        await b.close()
        print('\nPROBLEMS:', problems if problems else 'none')
        raise SystemExit(1 if problems else 0)

asyncio.run(main())
