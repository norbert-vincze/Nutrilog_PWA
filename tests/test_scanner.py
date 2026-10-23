import asyncio, json, os
from playwright.async_api import async_playwright
URL='http://127.0.0.1:8765/index.html'
PROD={"status":1,"code":"5901234123457","product":{"code":"5901234123457","product_name":"Beolvasott teszt termék","brands":"Márka","nutriments":{"energy-kcal_100g":100,"proteins_100g":5,"carbohydrates_100g":10,"fat_100g":4}}}
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream','--use-file-for-fake-video-capture='+os.path.abspath('bar.y4m')])
        ctx = await b.new_context(viewport={'width':390,'height':844}, locale='en-GB', permissions=['camera'])
        page = await ctx.new_page()
        errs=[]
        page.on('pageerror', lambda e: errs.append('PE '+str(e)))
        page.on('console', lambda m: errs.append('C '+m.text) if m.type in ('error',) else None)
        async def route(r):
            h={'access-control-allow-origin':'*','content-type':'application/json'}
            await r.fulfill(status=200, headers=h, body=json.dumps(PROD))
        await page.route('**/*openfoodfacts.org/**', route)
        await page.goto(URL); await page.wait_for_selector('.hero')
        print('BarcodeDetector in this browser:', await page.evaluate("'BarcodeDetector' in window"))
        await page.click('.act.primary'); await page.click('[data-a=scan]')
        await page.wait_for_selector('#amt', timeout=20000)
        print('scan -> amount sheet:', (await page.inner_text('.sheet-b >> nth=-1')).replace('\n',' | ')[:160])
        print('ERRS', errs)
        await b.close()
asyncio.run(main())
