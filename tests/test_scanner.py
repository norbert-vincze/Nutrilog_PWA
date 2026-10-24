"""Camera scanner (ZXing path, because Chromium here has no BarcodeDetector). Run with the web server on port 8765 (see CLAUDE.md).
First `python3 make_barcode_video.py` and `python3 make_scan_fixtures.py` (fake camera videos).

Why this test exists: on the iPhone a dmBio package (4070765076189) was read as 6072101076189. ZXing-js misreads EAN codes when the bars are only
about 2 camera pixels wide, and the wrong number can still pass the check digit. So the scanner asks the camera for full HD, reads only shop barcodes
(not the QR code next to the barcode) and accepts a number only after it was read several times."""
import asyncio, json, os, re, time
from playwright.async_api import async_playwright
URL = 'http://127.0.0.1:8765/index.html'
PROD = {"status": 1, "code": "5901234123457", "product": {"code": "5901234123457", "product_name": "Beolvasott teszt termék", "brands": "Márka", "nutriments": {"energy-kcal_100g": 100, "proteins_100g": 5, "carbohydrates_100g": 10, "fat_100g": 4}}}
REAL = '4070765076189'   # dmBio Udon tészta, 200 g (dm article 3065602): in dmbio.json
CAMERA_SPY = """
(() => {
  window.__gum = [];
  const real = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
  navigator.mediaDevices.getUserMedia = (c) => { window.__gum.push(JSON.stringify(c)); return real(c); };
})();
"""
# reading sequences for the voting test: [text, width of one bar in camera pixels] or None (nothing readable in that frame)
SCRIPT_JS = """
(seq) => {
  const Z = window.ZXing; let i = 0;
  window.__asked = 0;
  Z.MultiFormatReader.prototype.decode = function () {
    window.__asked++;
    const s = seq[i++];
    if (!s) throw new Error('no barcode');
    const pts = [new Z.ResultPoint(100, 50), new Z.ResultPoint(100 + 92 * s[1], 50)];
    return new Z.Result(s[0], null, 0, pts, Z.BarcodeFormat.EAN_13, Date.now());
  };
}
"""


async def main():
    async with async_playwright() as p:
        problems = []

        def check(name, ok, info=''):
            print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(info)) if info != '' else ''))
            if not ok: problems.append(name)

        async def session(video):
            """a browser with a fake camera that shows this video"""
            b = await p.chromium.launch(args=['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream', '--use-file-for-fake-video-capture=' + os.path.abspath(video)])
            ctx = await b.new_context(viewport={'width': 390, 'height': 844}, locale='en-GB', permissions=['camera'], service_workers='block')
            page = await ctx.new_page()
            page.errs, page.calls = [], []
            page.on('pageerror', lambda e: page.errs.append('PE ' + str(e)))
            page.on('console', lambda m: page.errs.append('C ' + m.text) if m.type == 'error' else None)

            async def route(r):
                page.calls.append(r.request.url)
                h = {'access-control-allow-origin': '*', 'content-type': 'application/json'}
                await r.fulfill(status=200, headers=h, body=json.dumps(PROD if '5901234123457' in r.request.url else {"status": 0, "products": []}))
            await page.route('**/*openfoodfacts.org/**', route)
            await page.add_init_script(CAMERA_SPY)
            await page.goto(URL); await page.wait_for_selector('.hero')
            return b, page

        async def open_scan(page):
            await page.click('.act.primary'); await page.click('[data-a=scan]')

        async def product_calls(page):
            return [re.search(r'/product/(\d+)', c).group(1) for c in page.calls if '/product/' in c]

        # ---- 1 a clean synthetic barcode, Open Food Facts answers
        b, page = await session('bar.y4m')
        print('BarcodeDetector in this browser:', await page.evaluate("'BarcodeDetector' in window"))
        await open_scan(page)
        await page.wait_for_selector('#amt', timeout=20000)
        check('clean barcode -> Open Food Facts product in the amount sheet', 'Beolvasott teszt termék' in await page.inner_text('.sheet-b >> nth=-1'))
        check('the camera was asked for full HD, rear camera', await page.evaluate("window.__gum.some(c=>{const v=JSON.parse(c).video;return v.width.ideal>=1920 && v.height.ideal>=1080 && v.facingMode.ideal==='environment'})"), await page.evaluate('window.__gum'))
        check('no page errors', page.errs == [], page.errs)
        await b.close()

        # ---- 2 a sharp photo of the real dm barcode: found in the app itself, no internet needed
        b, page = await session('scan_good.y4m')
        t0 = time.time(); await open_scan(page)
        await page.wait_for_selector('#amt', timeout=15000); dt = time.time() - t0
        check('real dm barcode (4070765076189) opens the dmBio product "Udon tészta"', 'Udon' in await page.inner_text('.sheet-b >> nth=-1'))
        check('and Open Food Facts was not asked', await product_calls(page) == [], await product_calls(page))
        check('it takes under 4 seconds', dt < 4, round(dt, 1))
        await b.close()

        # ---- 3 a small, shaky, noisy picture of the same barcode: the right product, or still scanning, never another number
        outcomes = []
        for run in range(3):
            b, page = await session('scan_hard.y4m')
            await open_scan(page)
            t0 = time.time(); res = 'still scanning'
            while time.time() - t0 < 15:
                await asyncio.sleep(0.2)
                if await page.locator('#scan-manual').count() == 0:
                    await asyncio.sleep(0.4)
                    res = 'dmBio Udon' if 'Udon' in (await page.inner_text('.sheet-b >> nth=-1') if await page.locator('#amt').count() else '') else 'WRONG ' + str(await product_calls(page))
                    break
            outcomes.append(res); await b.close()
        check('small shaky picture: never a wrong number (3 runs)', not any(o.startswith('WRONG') for o in outcomes), outcomes)
        check('and it does find the real product', outcomes.count('dmBio Udon') >= 2, outcomes)

        # ---- 4 a QR code only (dm prints one beside the barcode): it must not be taken for a barcode
        b, page = await session('scan_qr.y4m')
        await open_scan(page); await asyncio.sleep(5)
        check('a QR code is ignored: the scanner is still open', await page.locator('#scan-manual').count() == 1)
        check('and nothing was looked up', await product_calls(page) == [], await product_calls(page))
        await b.close()

        # ---- 5 voting: scripted readings instead of the picture
        async def vote_run(seq, wait=3.0):
            b, page = await session('scan_blank.y4m')
            await open_scan(page); await page.wait_for_selector('#scan-manual')
            await page.wait_for_function('window.ZXing')
            await asyncio.sleep(0.6)
            await page.evaluate(SCRIPT_JS, seq)
            t0 = time.time()
            while time.time() - t0 < wait and await page.locator('#scan-manual').count() == 1:
                await asyncio.sleep(0.1)
            closed = await page.locator('#scan-manual').count() == 0
            await asyncio.sleep(0.4)
            calls = await product_calls(page); asked = await page.evaluate('window.__asked')
            await b.close(); return closed, calls, asked

        A, W1, W2 = '1111111111116', '2222222222222', '3333333333339'
        none = None
        closed, calls, asked = await vote_run([[W1, 1.5]] + [none] * 40)
        check('one reading is not enough', not closed and calls == [], (closed, calls))
        closed, calls, asked = await vote_run([[W1, 1.5], [A, 1.5], [W2, 1.5], [A, 1.5], [A, 1.5]] + [none] * 40)
        check('small bars (1.5 px): a wrong number between right ones is skipped, the right one is taken on its 3rd reading', closed and calls == [A] and asked == 5, (closed, calls, asked))
        closed, calls, asked = await vote_run([[W1, 1.5], [A, 1.5], [A, 1.5]] + [none] * 40)
        check('small bars: two readings are not enough', not closed and calls == [], (closed, calls))
        closed, calls, asked = await vote_run([[W1, 4], [A, 4], [A, 4]] + [none] * 40)
        check('wide bars (4 px): the right number is taken on its 2nd reading', closed and calls == [A] and asked == 3, (closed, calls, asked))
        W3, W4 = '4444444444443', '5555555555558'
        closed, calls, asked = await vote_run([[W1, 4], [W2, 4], [W3, 4], [W4, 4]] + [none] * 40)
        check('readings that are all different never close the scanner', not closed and calls == [], (closed, calls))
        closed, calls, asked = await vote_run([[W1, 1.5], [W2, 1.5], [W1, 1.5], [W2, 1.5], [W1, 1.5], [W2, 1.5]] + [none] * 40)
        check('two numbers that keep competing never close the scanner', not closed and calls == [], (closed, calls))
        closed, calls, asked = await vote_run([[A, 4], [W1, 4], [A, 4]] + [none] * 40)
        check('wide bars: not-consecutive readings count too', closed and calls == [A], (closed, calls))

        # ---- 6 the not-found message helps with a misread
        b, page = await session('bar.y4m')
        await page.click('.act.primary'); await page.fill('#q', '6072101076189'); await page.click('[data-a=code]'); await page.wait_for_selector('.note', timeout=5000)
        note = await page.inner_text('.note')
        check('an unknown number says that the camera may have misread it', 'does not have barcode 6072101076189' in note and 'misread' in note, note[-120:])
        check('the Scan barcode button is still on screen for another try', await page.locator('[data-a=scan]').count() == 1)
        await b.close()
        print('\nPROBLEMS:', problems if problems else 'none')
        raise SystemExit(1 if problems else 0)

asyncio.run(main())
