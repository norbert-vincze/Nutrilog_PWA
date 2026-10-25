"""Input fields on an iPhone-sized screen. Run with the web server on port 8765 (see CLAUDE.md).

Why: iOS zooms into every field whose text is smaller than 16 px and the person has to zoom out again by hand.
This test measures the font size of every field in every view and sheet, checks that pinch zoom is still allowed,
that the main buttons of a sheet stay at the bottom, that the sheet follows the visible area while the on-screen keyboard is up
(simulated: Chromium here has no keyboard), that Return moves Name -> Brand -> Barcode and adds the food from the amount field,
and that the time field is a 24-hour HH:MM field. A real iPhone is still needed for the final check."""
import asyncio, json
from playwright.async_api import async_playwright
URL = 'http://127.0.0.1:8765/index.html'

# a fake visualViewport that the test controls: window.__vvh = height of the visible part, window.__vvt = its top, window.__vvs = zoom
FAKE_VV = """
(() => {
  const t = new EventTarget();
  Object.defineProperties(t, {
    height: { get: () => (window.__vvh ?? window.innerHeight) }, width: { get: () => window.innerWidth },
    offsetTop: { get: () => (window.__vvt ?? 0) }, scale: { get: () => (window.__vvs ?? 1) },
  });
  Object.defineProperty(window, 'visualViewport', { value: t, configurable: true });
  window.__vv = t;
})();
"""
SMALL_FONTS = """
() => [...document.querySelectorAll('input, select, textarea')]
  .filter((e) => !['hidden', 'file', 'radio', 'checkbox'].includes(e.type))
  .map((e) => [e.id || e.className || e.tagName, e.type, parseFloat(getComputedStyle(e).fontSize)])
  .filter((x) => x[2] < 16)
"""


async def main():
    async with async_playwright() as p:
        problems = []

        def check(name, ok, info=''):
            print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(info)) if info != '' else ''))
            if not ok: problems.append(name)

        b = await p.chromium.launch(args=['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'])
        ctx = await b.new_context(viewport={'width': 390, 'height': 560}, device_scale_factor=3, is_mobile=True, has_touch=True, locale='en-GB', permissions=['camera'], service_workers='block')
        await ctx.route('**/*openfoodfacts.org/**', lambda r: r.fulfill(status=200, headers={'access-control-allow-origin': '*', 'content-type': 'application/json'}, body='{"products":[],"status":0}'))
        await ctx.add_init_script(FAKE_VV)
        page = await ctx.new_page()
        errs = []
        page.on('pageerror', lambda e: errs.append('PE ' + str(e)))
        page.on('console', lambda m: errs.append('C ' + m.text) if m.type == 'error' and 'Failed to load resource' not in m.text else None)
        T = page.evaluate
        await page.goto(URL); await page.wait_for_selector('.hero')

        # ---- 1 pinch zoom stays possible
        vp = await T("document.querySelector('meta[name=viewport]').content")
        check('viewport meta is unchanged and allows zoom', vp == 'width=device-width, initial-scale=1, viewport-fit=cover' and 'maximum-scale' not in vp and 'user-scalable' not in vp, vp)

        # ---- 2 font size of every field, view by view
        async def small(label):
            r = await T(SMALL_FONTS)
            check(f'{label}: every field has at least 16 px text', r == [], r)
        await small('Diary')
        await page.click('[data-tab=nutr]'); await small('Nutrients')
        await page.click('[data-tab=foods]'); await page.wait_for_selector('#ffilter'); await small('My foods')
        await page.click('[data-tab=data]'); await page.wait_for_selector('[data-act=export-json]'); await small('Data')
        await page.click('[data-act=sync-setup]'); await page.wait_for_selector('#sy-repo'); await small('Set up sync sheet')
        check('Set up sync: Return hints next and go', await T("[document.querySelector('#sy-repo').enterKeyHint, document.querySelector('#sy-token').enterKeyHint]") == ['next', 'go'])
        await page.click('.sheet [data-x]')
        await page.click('[data-tab=log]'); await page.wait_for_selector('.hero')

        # ---- 3 the picker, the amount sheet, Return adds the food
        await page.click('.act.primary'); await page.wait_for_selector('#q')
        await small('Log food sheet')
        check('search field says Search on the keyboard', await T("document.querySelector('#q').enterKeyHint") == 'search')
        await page.fill('#q', 'rice'); await page.wait_for_selector('[data-pick]')
        await page.click('[data-pick] >> nth=0'); await page.wait_for_selector('#amt')
        await small('Amount sheet')
        check('Amount: Return key says Done', await T("document.querySelector('#amt').enterKeyHint") == 'done')
        sh = await T("(() => { const w = document.querySelector('.sheet-wrap').getBoundingClientRect(), s = document.querySelector('.sheet').getBoundingClientRect(); return [Math.round(w.top), Math.round(w.height), Math.round(s.bottom), innerHeight]; })()")
        check('the sheet area is as high as the screen (100dvh) and the sheet sits at its bottom', sh[0] == 0 and abs(sh[1] - sh[3]) <= 1 and abs(sh[2] - sh[3]) <= 1, sh)
        await page.wait_for_timeout(450)   # the sheet slides up for 0.3 s
        btn = await T("(() => { const r = document.querySelector('#ok').getBoundingClientRect(); return [Math.round(r.top), Math.round(r.bottom), innerHeight]; })()")
        check('the Add button is on screen', btn[0] >= 0 and btn[1] <= btn[2], btn)
        before = await T('__tapnaplo.S.log.length')
        await page.fill('#amt', '80'); await page.press('#amt', 'Enter'); await page.wait_for_timeout(250)
        check('Return in the amount field adds the food and closes the sheet', await T('__tapnaplo.S.log.length') == before + 1 and await page.locator('.sheet-wrap').count() == 0 and await T('__tapnaplo.S.log[__tapnaplo.S.log.length-1].a') == 80)

        # ---- 4 the time field: 24 hours, typed
        await page.click('.entry >> nth=0'); await page.wait_for_selector('#tm')
        await small('Edit entry sheet')
        check('time field is a text field with a number keypad (HH:MM)', await T("(() => { const t = document.querySelector('#tm'); return [t.type, t.inputMode, t.placeholder, t.enterKeyHint]; })()") == ['text', 'numeric', 'HH:MM', 'done'])
        await page.click('#tm'); await page.wait_for_timeout(120)
        await page.keyboard.type('0830')
        check('typing 0830 gives 08:30 (colon added)', await page.input_value('#tm') == '08:30', await page.input_value('#tm'))
        await page.keyboard.press('Backspace'); await page.keyboard.press('Backspace')
        check('Backspace works through the colon (08:3 then 08:)', await page.input_value('#tm') == '08:', await page.input_value('#tm'))
        await page.keyboard.type('45')
        check('and typing on gives 08:45', await page.input_value('#tm') == '08:45', await page.input_value('#tm'))
        await page.fill('#tm', '8:30'); await page.click('#amt'); await page.wait_for_timeout(100)
        check('8:30 becomes 08:30 when the field is left', await page.input_value('#tm') == '08:30', await page.input_value('#tm'))
        await page.fill('#tm', ''); await page.click('#tm'); await page.wait_for_timeout(120); await page.keyboard.type('a1 7x:4b5')
        check('letters and spaces are dropped (17:45)', await page.input_value('#tm') == '17:45', await page.input_value('#tm'))
        await page.fill('#tm', '25:99'); await page.click('#ok'); await page.wait_for_timeout(150)
        check('25:99 is refused with a message next to the field and the sheet stays open', await page.is_visible('#tmerr') and 'in 24-hour form' in await page.inner_text('#tmerr') and await page.locator('#tm').count() == 1)
        await page.fill('#tm', '1745'); await page.press('#tm', 'Enter'); await page.wait_for_timeout(250)
        check('Return in the time field saves the entry (1745 is 17:45)', await T('__tapnaplo.S.log[0].tm') == '17:45' and await page.locator('.sheet-wrap').count() == 0, await T('__tapnaplo.S.log[0].tm'))

        # ---- 5 Create food: fields, Return chain, fixed Save bar on a short screen
        await page.click('[data-tab=foods]'); await page.click('[data-act=new-food]'); await page.wait_for_selector('#fname')
        await small('Create food sheet (all values opened)')
        await T("document.querySelectorAll('#nuts details').forEach(d => d.open = true)")
        await small('Create food sheet (all values opened)')
        hints = await T("['fname','fbrand','fcode','funit'].map(i => document.getElementById(i).enterKeyHint)")
        check('Return keys: next, next, done, done', hints == ['next', 'next', 'done', 'done'], hints)
        await page.click('#fname'); await page.keyboard.type('Test bar')
        await page.keyboard.press('Enter')
        a1 = await T('document.activeElement.id')
        await page.keyboard.type('Brandy'); await page.keyboard.press('Enter')
        a2 = await T('document.activeElement.id')
        await page.keyboard.type('123456'); await page.keyboard.press('Enter')
        a3 = await T("document.activeElement.tagName + ':' + document.activeElement.id")
        check('Return goes Name to Brand to Barcode, then the keyboard closes', [a1, a2] == ['fbrand', 'fcode'] and a3 == 'BODY:', [a1, a2, a3])
        check('the sheet stays open and the typed values are kept', await T("[fname.value, fbrand.value, fcode.value]") == ['Test bar', 'Brandy', '123456'])
        sc = await T("(() => { const b = document.querySelector('.sheet-b'); return [b.scrollHeight, b.clientHeight]; })()")
        check('the form is longer than the screen (it scrolls)', sc[0] > sc[1] + 200, sc)
        async def save_visible():
            return await T("(() => { const r = document.querySelector('#fok').getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight + 0.5 && r.height >= 44; })()")
        check('Save is on screen at the top of the form', await save_visible())
        await T("document.querySelector('.sheet-b').scrollTop = 600")
        check('Save is on screen in the middle of the form', await save_visible())
        await T("document.querySelector('.sheet-b').scrollTop = 99999")
        check('Save is on screen at the end of the form', await save_visible())
        bar = await T("(() => { const a = document.querySelector('.sheet-actions').getBoundingClientRect(), b = document.querySelector('.sheet-b').getBoundingClientRect(); return [Math.round(a.bottom), Math.round(b.bottom), Math.round(a.left), Math.round(a.right), innerWidth]; })()")
        check('the button bar sits flush at the bottom edge and spans the sheet', abs(bar[0] - bar[1]) <= 1 and bar[2] <= 1 and bar[3] >= bar[4] - 1, bar)

        # ---- 6 the keyboard (simulated): the sheet shrinks to the visible area, the Save button stays visible
        await T("window.__vvh = 300; window.__vv.dispatchEvent(new Event('resize'))")
        kb = await T("(() => { const w = document.querySelector('.sheet-wrap').getBoundingClientRect(), r = document.querySelector('#fok').getBoundingClientRect(), s = document.querySelector('.sheet').getBoundingClientRect(); return [document.body.classList.contains('kb'), Math.round(w.height), Math.round(r.bottom), Math.round(s.top)]; })()")
        check('with the keyboard up the sheet area is only as high as the visible part', kb[0] and kb[1] == 300, kb)
        check('and Save is above the keyboard, the sheet top is on screen', kb[2] <= 300 and kb[3] >= 0, kb)
        await T("window.__vvh = 300; window.__vvt = 40; window.__vv.dispatchEvent(new Event('scroll'))")
        kb2 = await T("(() => { const w = document.querySelector('.sheet-wrap').getBoundingClientRect(); return [Math.round(w.top), Math.round(w.height)]; })()")
        check('when iOS scrolls the visible area down, the sheet follows it', kb2 == [40, 300], kb2)
        await T("window.__vvs = 1.8; window.__vv.dispatchEvent(new Event('resize'))")
        check('while the page is pinch-zoomed the sheet is left alone', not await T("document.body.classList.contains('kb')"))
        await T("window.__vvs = 1; window.__vvh = undefined; window.__vvt = 0; window.__vv.dispatchEvent(new Event('resize'))")
        kb3 = await T("(() => { const w = document.querySelector('.sheet-wrap').getBoundingClientRect(); return [document.body.classList.contains('kb'), Math.round(w.height), innerHeight]; })()")
        check('keyboard gone: back to the full height', kb3[0] is False and abs(kb3[1] - kb3[2]) <= 1, kb3)
        await T("window.__vvh = 300; window.__vv.dispatchEvent(new Event('resize'))")
        await page.click('.sheet [data-x]'); await page.wait_for_timeout(100)
        check('closing the last sheet drops the keyboard mode', not await T("document.body.classList.contains('kb')"))
        await T("window.__vvh = undefined; window.__vv.dispatchEvent(new Event('resize'))")

        # ---- 7 other sheets: save as portion (askText), confirm, scanner
        await page.click('[data-tab=log]'); await page.click('.act.primary'); await page.fill('#q', 'rice'); await page.wait_for_selector('[data-pick]')
        await page.click('[data-pick] >> nth=0'); await page.wait_for_selector('#saveportion')
        await page.click('#saveportion'); await page.wait_for_selector('#ask-v')
        await small('Name-a-portion sheet')
        check('name field: Return says Done, and the Save button is in the bottom bar', await T("document.querySelector('#ask-v').enterKeyHint") == 'done' and await T("!!document.querySelector('.sheet-actions [data-ok]')"))
        await page.click('[data-dx]'); await page.wait_for_timeout(100)      # Cancel closes the small sheet only
        check('Cancel closes only the name sheet', await page.locator('.sheet-wrap').count() == 2)
        await page.click('.sheet-wrap >> nth=-1 >> [data-x]'); await page.wait_for_timeout(150)   # the Amount sheet
        await page.click('.sheet-wrap >> nth=-1 >> [data-x]'); await page.wait_for_timeout(150)   # the picker
        check('all sheets closed', await page.locator('.sheet-wrap').count() == 0)
        await page.click('[data-act=scan]'); await page.wait_for_selector('#scan-manual', timeout=15000)
        await small('Scanner sheet')
        await page.click('.sheet-wrap >> nth=-1 >> [data-x]'); await page.wait_for_timeout(150)

        # ---- 8 touch behaviour of buttons and links
        ta = await T("""() => ['.btn', '.chip-btn', '.tab', '.icon-btn', 'summary', 'select', 'a'].map((q) => { const e = document.querySelector(q); return e ? [q, getComputedStyle(e).touchAction] : [q, 'none found']; }).filter((x) => x[1] !== 'manipulation' && x[1] !== 'none found')""")
        check('buttons, links, tabs and folds use touch-action: manipulation', ta == [], ta)

        check('no page errors or console errors', errs == [], errs[:5])
        await b.close()
        print('\nPROBLEMS:', problems if problems else 'none')
        raise SystemExit(1 if problems else 0)

asyncio.run(main())
