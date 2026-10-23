import asyncio, json
from playwright.async_api import async_playwright
URL='http://127.0.0.1:8765/index.html'
OFF_PRODUCT = {"status":1,"code":"5900000000017","product":{"code":"5900000000017","product_name":"Test almond drink","brands":"TestBrand","serving_quantity":250,"serving_size":"1 glass (250 ml)","nova_group":4,
 "nutriments":{"energy-kcal_100g":25,"proteins_100g":0.5,"carbohydrates_100g":3,"sugars_100g":2.5,"fat_100g":1.1,"saturated-fat_100g":0.1,"fiber_100g":0.4,"salt_100g":0.1,"calcium_100g":0.12,"vitamin-d_100g":0.00000075}}}
OFF_SEARCH = {"products":[OFF_PRODUCT["product"], {"code":"5900000000024","product_name":"Other product","nutriments":{}}]}
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={'width':390,'height':844}, locale='en-GB', accept_downloads=True, reduced_motion='reduce')
        page = await ctx.new_page()
        errs=[]
        page.on('pageerror', lambda e: errs.append('PE '+str(e)))
        page.on('console', lambda m: errs.append('C '+m.text) if m.type=='error' else None)
        async def route(r):
            u=r.request.url; h={'access-control-allow-origin':'*','content-type':'application/json'}
            if '/api/v2/product/5900000000017' in u: await r.fulfill(status=200, headers=h, body=json.dumps(OFF_PRODUCT))
            elif '/api/v2/product/' in u: await r.fulfill(status=200, headers=h, body=json.dumps({"status":0}))
            elif 'cgi/search.pl' in u: await r.fulfill(status=200, headers=h, body=json.dumps(OFF_SEARCH))
            else: await r.continue_()
        await page.route('**/*openfoodfacts.org/**', route)
        await page.goto(URL); await page.wait_for_selector('.hero')
        T = lambda e: page.evaluate(e)
        print('title:', await page.title(), '| html lang:', await T('document.documentElement.lang'))
        await page.screenshot(path='n_empty.png')
        # Hungarian + English search through the real UI
        async def top(q, n=3):
            await page.fill('#q', q)
            await page.wait_for_timeout(120)
            names = await page.locator('[data-pick] .item-name').all_inner_texts()
            return names[:n]
        await page.click('[data-act=add]')
        for q in ['tojás','egg','főtt tojás','boiled egg','eggs','kenyér','bread','kecskesajt','goat cheese','avokádó','avocado','yogurt','joghurt','zucchini','cukkini','shrimp','garnéla','chicken breast','csirkemell','salmon','lazac','oats','zabpehely','almond milk','mandulatej','sour cream','tejföl','cottage cheese','túró','sorbet','halloumi']:
            print(f'{q!r:20}', await top(q))
        await page.keyboard.press('Escape')
        # add entries
        async def add(q, amt, meal):
            await page.click(f'[data-act=add][data-meal={meal}]')
            await page.fill('#q', q); await page.wait_for_selector('[data-pick]')
            await page.click('[data-pick] >> nth=0'); await page.wait_for_selector('#amt')
            await page.fill('#amt', amt); await page.click('#ok'); await page.wait_for_timeout(150)
        await add('főtt tojás','50','m1'); await add('bread','60','m1'); await add('chicken breast','150','m2'); await add('lazac','100','m3')
        # OFF barcode
        await page.click('[data-act=add]'); await page.fill('#q','5900000000017'); await page.click('[data-a=code]')
        await page.wait_for_selector('#amt'); await page.fill('#amt','1,5'); await page.click('#ok'); await page.wait_for_timeout(200)
        print('amount typed "1,5" ->', await T('__tapnaplo.S.log.at(-1).a'))
        # custom unit food
        await page.click('[data-tab=foods]'); await page.click('[data-act=new-food]')
        await page.fill('#fname','Magnesium capsule'); await page.check('input[name=basis][value=u]'); await page.fill('#funit','capsule')
        await page.click('details.more > summary'); await page.fill('#n_magnesium','100'); await page.fill('#n_vitamin_d','<0.5')
        await page.screenshot(path='n_editor.png'); await page.click('#fok'); await page.wait_for_timeout(200)
        await page.click('[data-tab=log]'); await page.click('[data-act=add][data-meal=m5]'); await page.fill('#q','magnesium')
        await page.click('[data-pick] >> nth=0'); await page.fill('#amt','3'); await page.click('#ok'); await page.wait_for_timeout(200)
        # meals renamed, recipe gone
        print('meal headings:', await T("[...document.querySelectorAll('.meal-h h3')].map(h=>h.textContent)"))
        print('recipe UI present:', await T("document.body.innerText.toLowerCase().includes('recipe') || !!document.querySelector('[data-act=new-recipe]')"))
        print('actions:', await T("[...document.querySelectorAll('.act')].map(a=>a.textContent.trim())"))
        print('foods:', await T('Object.values(__tapnaplo.S.foods).map(f=>f.name)'))
        await page.screenshot(path='n_log.png', full_page=True)
        print('HERO:', (await page.inner_text('.hero')).replace('\n',' | '))
        await page.click('.entry >> nth=0'); await page.wait_for_selector('#amt'); await page.screenshot(path='n_amount.png'); await page.keyboard.press('Escape')
        await page.click('[data-tab=nutr]'); await page.wait_for_selector('.nrow'); await page.screenshot(path='n_nutr.png', full_page=True)
        await page.click('[data-tab=foods]'); await page.screenshot(path='n_foods.png')
        await page.click('[data-tab=data]'); await page.screenshot(path='n_data.png', full_page=True)
        await page.click('[data-tab=log]'); await page.click('[data-act=scan]'); await page.wait_for_selector('#scan-manual'); await page.screenshot(path='n_scan.png')
        await page.keyboard.press('Escape'); await page.keyboard.press('Escape')
        # reload persistence
        n0 = await T('__tapnaplo.S.log.length'); await page.wait_for_timeout(400); await page.reload(); await page.wait_for_selector('.hero')
        print('reload entries', n0, await T('__tapnaplo.S.log.length'))
        # any leftover Hungarian text in UI? scan visible text of each tab
        import re
        hu = re.compile(r'[őűáéíóöúüŐŰÁÉÍÓÖÚÜ]')
        for tab in ['log','nutr','foods','data']:
            await page.click(f'[data-tab={tab}]')
            txt = await page.inner_text('body')
            found = sorted(set(w for w in re.findall(r'\S*[őűáéíóöúüŐŰÁÉÍÓÖÚÜ]\S*', txt)))
            print('accented words on', tab, found[:15])
        print('ERRS', errs)
        # dark + desktop
        ctx2 = await b.new_context(viewport={'width':390,'height':844}, locale='en-GB', color_scheme='dark')
        p2 = await ctx2.new_page(); await p2.goto(URL); await p2.wait_for_selector('.hero')
        await p2.evaluate("(()=>{const S=__tapnaplo.S; S.log.push({id:'a',d:S.day,m:'m1',f:'c:22010',a:50,t:1},{id:'b',d:S.day,m:'m2',f:'c:20000'.replace('20000','25601'),a:150,t:2}); __tapnaplo.render();})()")
        await p2.screenshot(path='n_dark.png')
        await b.close()
asyncio.run(main())
