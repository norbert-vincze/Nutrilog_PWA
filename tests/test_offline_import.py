import asyncio, json
from playwright.async_api import async_playwright
URL='http://127.0.0.1:8765/index.html'
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={'width':390,'height':844}, locale='en-GB', color_scheme='dark', accept_downloads=True)
        page = await ctx.new_page()
        errs=[]
        page.on('pageerror', lambda e: errs.append('PE '+str(e)))
        page.on('console', lambda m: errs.append('C '+m.text) if m.type=='error' else None)
        await page.route('**/*openfoodfacts.org/**', lambda r: r.abort())   # OFF unreachable
        await page.goto(URL); await page.wait_for_selector('.hero')
        T = lambda e: page.evaluate(e)
        # add 2 entries
        async def add(q, amt, meal='m2'):
            await page.click(f'[data-act=add][data-meal={meal}]')
            await page.fill('#q', q)
            await page.wait_for_selector('[data-pick]')
            await page.click('[data-pick] >> nth=0')
            await page.wait_for_selector('#amt')
            await page.fill('#amt', amt)
            await page.click('#ok')
            await page.wait_for_timeout(150)
        await add('kenyér','60','m1'); await add('csirkemell','150'); await add('lazac','100','m3')
        print('entries', await T('__tapnaplo.S.log.length'), (await page.inner_text('.hero')).replace('\n',' | '))
        # OFF failure message
        await page.click('.act.primary'); await page.fill('#q','nutella'); await page.click('[data-a=off]')
        await page.wait_for_selector('.note'); print('OFF fail msg:', await page.locator('.note').last.inner_text())
        await page.keyboard.press('Escape')
        # edit entry
        await page.click('.entry >> nth=0'); await page.wait_for_selector('#amt')
        await page.fill('#amt','80,5'); await page.click('#ok'); await page.wait_for_timeout(150)
        print('edited amount:', await T('__tapnaplo.S.log[0].a'))
        # delete + undo
        await page.click('.entry >> nth=0'); await page.click('#del'); await page.wait_for_timeout(150)
        n1 = await T('__tapnaplo.S.log.length')
        await page.click('#toast button'); await page.wait_for_timeout(150)
        n2 = await T('__tapnaplo.S.log.length'); print('delete/undo', n1, n2)
        # date navigation
        await page.click('[data-act=day][data-n="-1"]'); 
        print('prev day empty:', (await page.inner_text('.hero')).replace('\n',' | ')[:40])
        await page.click('[data-act=today]')
        # nutrients with ranges
        await page.click('[data-tab=nutr]'); await page.wait_for_selector('.nrow')
        await page.click('.nrow >> nth=0')
        await page.screenshot(path='s_dark_nutr.png')
        await page.click('[data-tab=log]'); await page.screenshot(path='s_dark_log.png')
        # scanner manual
        await page.click('.act.primary'); await page.click('[data-a=scan]'); await page.wait_for_selector('#scan-manual')
        await page.screenshot(path='s_scan.png')
        await page.fill('#scan-manual','5900000000099'); await page.click('#scan-go')
        await page.wait_for_timeout(500)
        print('after scan q:', await T("document.querySelector('#q').value"), '|', (await page.locator('.note').last.inner_text()))
        await page.keyboard.press('Escape')
        # service worker + offline
        await page.wait_for_timeout(1500)
        ready = await T("navigator.serviceWorker.ready.then(r=>!!r.active)")
        print('SW active', ready)
        keys = await T("caches.keys().then(async ks=>{const o={};for(const k of ks){o[k]=(await (await caches.open(k)).keys()).length}return o})")
        print('cache', keys)
        await ctx.set_offline(True)
        await page.reload(); await page.wait_for_selector('.hero', timeout=10000)
        print('offline reload ok; entries', await T('__tapnaplo.S.log.length'))
        await ctx.set_offline(False)
        # import roundtrip
        await page.click('[data-tab=data]')
        async with page.expect_download() as d:
            await page.click('[data-act=export-json]')
        dl = await d.value; await dl.save_as('exp2.json')
        await T("(()=>{const S=__tapnaplo.S; S.log.length=0; })()")
        await page.set_input_files('#importfile','exp2.json'); await page.wait_for_selector('[data-ok]'); await page.click('[data-ok]'); await page.wait_for_timeout(400)
        print('after import entries', await T('__tapnaplo.S.log.length'))
        await page.screenshot(path='s_dark_data.png', full_page=True)
        # desktop
        await page.set_viewport_size({'width':1200,'height':800}); await page.click('[data-tab=log]'); await page.screenshot(path='s_desktop.png')
        print('ERRS', errs)
        await b.close()
asyncio.run(main())
