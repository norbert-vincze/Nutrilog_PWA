import asyncio, json
from playwright.async_api import async_playwright
URL = 'http://127.0.0.1:8765/index.html'
PROD13 = {"status": 1, "code": "0587780211012", "product": {"code": "0587780211012", "product_name": "US supplement", "brands": "Acme",
          "nutriments": {"energy-kcal_100g": 100, "proteins_100g": 5, "carbohydrates_100g": 10, "fat_100g": 4}}}

async def run(touch):
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={'width': 390, 'height': 844}, locale='en-GB', has_touch=touch, is_mobile=touch)
        page = await ctx.new_page()
        errs = []
        page.on('pageerror', lambda e: errs.append('PE ' + str(e)))
        calls = []
        mode = {'v': 'none'}

        async def route(r):
            u = r.request.url
            calls.append(u)
            h = {'access-control-allow-origin': '*', 'content-type': 'application/json'}
            if '/api/v2/product/' in u:
                code = u.split('/api/v2/product/')[1].split('.json')[0]
                if mode['v'] == 'err':
                    await r.fulfill(status=500, headers=h, body='{}')
                elif mode['v'] == 'padded' and code == '0587780211012':
                    await r.fulfill(status=200, headers=h, body=json.dumps(PROD13))
                else:
                    await r.fulfill(status=404, headers=h, body='{"status":0,"status_verbose":"product not found"}')
            else:
                await r.fulfill(status=200, headers=h, body='{"products":[]}')
        await page.route('**/*openfoodfacts.org/**', route)
        await page.goto(URL); await page.wait_for_selector('.hero')
        print('--- touch' if touch else '--- desktop', '| TOUCH const:', await page.evaluate("matchMedia('(pointer: coarse)').matches"))

        async def scan(code):
            await page.click('.act.primary'); await page.wait_for_selector('#q')
            await page.click('[data-a=scan]'); await page.wait_for_selector('#scan-manual')
            await page.fill('#scan-manual', code); await page.click('#scan-go')
            await page.wait_for_timeout(500)

        # 1 unknown barcode -> friendly "not found", no HTTP 404 text, primary New food
        mode['v'] = 'none'; await scan('587780211012')
        txt = await page.inner_text('#res')
        print('1 not found msg:', txt.replace('\n', ' | ')[:230])
        print('  contains HTTP 404:', 'HTTP 404' in txt, '| primary New food:', await page.locator('[data-a=new].primary').count())
        print('  tried:', [c.split('/product/')[1].split('.json')[0] for c in calls if '/product/' in c])
        # editor prefilled with barcode
        await page.click('[data-a=new]'); await page.wait_for_selector('#fcode')
        print('  editor barcode prefilled:', await page.input_value('#fcode'))
        await page.fill('#fname', 'My supplement'); await page.click('details.more > summary'); await page.fill('#n_magnesium', '120'); await page.click('#fok')
        await page.wait_for_selector('#amt'); await page.click('#ok'); await page.wait_for_timeout(200)

        # 2 same code again -> own food found, no network call
        n0 = len(calls); await scan('587780211012')
        await page.wait_for_selector('#amt', timeout=3000)
        print('2 own food found by barcode, new network calls:', len(calls) - n0, '| sheet:', (await page.inner_text('.sheet-b >> nth=-1')).split('\n')[0])
        await page.keyboard.press('Escape'); await page.keyboard.press('Escape')

        # 3 padded variant: scan 12 digits, product stored in OFF as 13 digits (own food removed first)
        await page.evaluate("(()=>{const S=__tapnaplo.S; for(const k of Object.keys(S.foods)) if(S.foods[k].barcode==='587780211012') delete S.foods[k]; S.log=S.log.filter(e=>S.foods[e.f]); })()")
        mode['v'] = 'padded'; calls.clear()
        await scan('587780211012')
        print('3 padded: tried', [c.split('/product/')[1].split('.json')[0] for c in calls if '/product/' in c], '| amount sheet:', await page.locator('#amt').count())
        if await page.locator('#amt').count():
            print('  product:', (await page.inner_text('.sheet-b >> nth=-1')).split('\n')[1:3])

        # 4 amount field: keyboard-related behaviour
        active = await page.evaluate("document.activeElement && document.activeElement.id")
        print('4 activeElement after amount opens:', repr(active), '(touch: must NOT be amt; desktop: amt)')
        if touch:
            await page.tap('#amt'); await page.wait_for_timeout(150)   # the number gets selected shortly after the tap
        await page.keyboard.type('75')
        print('  typed value:', await page.input_value('#amt'))
        await page.keyboard.press('Enter'); await page.wait_for_timeout(300)
        print('  Enter saved entry, last amount:', await page.evaluate('__tapnaplo.S.log.at(-1).a'))

        # 5 server error message
        mode['v'] = 'err'; await scan('5449000000996')
        print('5 error msg:', (await page.inner_text('#res')).replace('\n', ' | ')[-150:])
        await page.keyboard.press('Escape'); await page.keyboard.press('Escape')

        # 6 Hungary filter default off
        await page.click('.act.primary'); await page.wait_for_selector('#q')
        await page.fill('#q', 'muesli')
        print('6 huonly checked by default:', await page.is_checked('#huonly'))
        calls.clear(); await page.click('[data-a=off]'); await page.wait_for_timeout(300)
        print('  search url has hungary:', any('hungary' in c for c in calls), '| sorted:', any('unique_scans_n' in c for c in calls))
        await page.check('#huonly'); calls.clear(); await page.click('[data-a=off]'); await page.wait_for_timeout(300)
        print('  with box ticked has hungary:', any('hungary' in c for c in calls))
        # 7 version label + "Reload app files" keeps the diary
        await page.keyboard.press('Escape'); await page.keyboard.press('Escape')
        await page.click('[data-tab=data]')
        print('7 version text:', (await page.inner_text('.card:has-text("App version")')).replace('\n', ' | ')[:120])
        n_before = await page.evaluate('__tapnaplo.S.log.length')
        await page.wait_for_timeout(800)
        await page.click('[data-act=refresh-app]')
        await page.wait_for_load_state('load'); await page.wait_for_selector('[data-act=refresh-app]'); await page.wait_for_timeout(1500)
        print('  tab after reload (remembered):', await page.evaluate('__tapnaplo.S.tab'))
        print('  entries before/after reload:', n_before, await page.evaluate('__tapnaplo.S.log.length'))
        print('  caches after reload:', await page.evaluate('caches.keys()'))
        print('ERRS', errs)
        await b.close()

async def main():
    await run(False)
    await run(True)
asyncio.run(main())
