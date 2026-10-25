"""Import foods (JSON), version 15: adds the foods of a Nutrilog file to My foods without touching the diary. Run with the web server on port 8765 (see CLAUDE.md).

Covers: new ids are added (and the diary and the meta part of the file are ignored), a colliding id is never overwritten silently (Skip / Overwrite / Cancel),
Undo gives the foods back exactly as they were, invalid entries are skipped and counted, entries that are not foods you made are left out, every kind of bad file
(message next to the button, nothing changes), a unit change on a food the diary uses is refused, look-alikes and odd values are shown, the Hungarian confidence words
of the v3 prompt, "Paste from AI" and "Restore from file" with the same files, touch targets, contrast, no network, no page errors."""
import asyncio, json, os, pathlib, sys
from playwright.async_api import async_playwright
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_ai_import import CONTRAST_JS   # the contrast measurement of the AI import test

URL = 'http://127.0.0.1:8765/index.html'
HERE = pathlib.Path(__file__).resolve().parent
SHOTS = os.environ.get('SHOTS', '')   # set to a folder to get screenshots
BUTTON_SIZES = "(sel) => [...document.querySelectorAll(sel)].filter((e) => !e.hidden && e.getClientRects().length).map((e) => { const r = e.getBoundingClientRect(); return [e.dataset.fi || e.textContent.trim().slice(0, 20), Math.round(r.width), Math.round(r.height)]; }).filter((x) => x[2] < 44 || x[1] < 44)"
SNAP = "() => JSON.stringify([window.__tapnaplo.S.log, window.__tapnaplo.S.foods, window.__tapnaplo.S.meta], (k, v) => (k[0] === '_' ? undefined : v))"


def v3food(fid, name, **kw):
    """One food the way the v3 prompt writes it (confidence in Hungarian words, created and updated 0)."""
    f = {'id': fid, 'src': 'user', 'name': name, 'brand': 'Acme', 'barcode': '', 'basis': {'qty': 100, 'unit': 'g'},
         'n': {'kcal': 45, 'protein': 1.0, 'carbohydrate': 6.6, 'fat': 1.5, 'calcium': 120, 'vitamin_e': 1.1},
         'est': ['vitamin_e'], 'confidence': 'alacsony', 'fortified': True, 'nova': 4,
         'portions': [{'label': '100 ml', 'grams': 100}], 'note': 'Test note', 'created': 0, 'updated': 0}
    f.update(kw)
    return f


def ffile(foods, **extra):
    d = {'app': 'tapnaplo', 'version': 1, 'foods': foods}
    d.update(extra)
    return d


async def main():
    async with async_playwright() as p:
        problems, made = [], []

        def check(name, ok, info=''):
            print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(info)) if info != '' else ''))
            if not ok: problems.append(name)

        def write(name, data, raw=None):
            path = HERE / f'tmp_fi_{name}.json'
            path.write_text(raw if raw is not None else json.dumps(data, ensure_ascii=False), encoding='utf-8')
            made.append(path)
            return str(path)

        browser = await p.chromium.launch()
        errs, outside = [], []
        ctx = await browser.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True, locale='en-GB', service_workers='block', permissions=['clipboard-read', 'clipboard-write'])
        await ctx.route('**/*openfoodfacts.org/**', lambda r: r.fulfill(status=200, headers={'access-control-allow-origin': '*', 'content-type': 'application/json'}, body='{"products":[],"status":0}'))
        page = await ctx.new_page()
        page.on('pageerror', lambda e: errs.append(f'PE {e}'))
        page.on('console', lambda m: errs.append(f'C {m.text}') if m.type == 'error' and 'Failed to load resource' not in m.text else None)
        page.on('request', lambda r: outside.append(r.url) if not r.url.startswith('http://127.0.0.1') and not r.url.startswith('data:') and not r.url.startswith('blob:') else None)
        await page.goto(URL); await page.wait_for_selector('.hero')
        T = page.evaluate

        async def snap():
            return await T(SNAP)

        async def sheets():
            return await T("document.querySelectorAll('.sheet').length")

        async def close_all():
            for _ in range(8):
                if not await sheets(): break
                await page.click('.sheet-wrap:last-of-type [data-x]')
                await page.wait_for_timeout(120)
            await page.wait_for_timeout(100)

        async def data_tab():
            await page.click('[data-tab=data]'); await page.wait_for_selector('#importfoods', state='attached')

        async def pick(path):
            """Choose a file for 'Import foods (JSON)' and wait for the reaction (a sheet, a toast or a message next to the button)."""
            await T("() => { const t = document.querySelector('#toast'); t.hidden = true; const m = document.querySelector('#fimp-msg'); if (m) m.innerHTML = ''; }")
            await page.set_input_files('#importfoods', path)
            await page.wait_for_function("() => document.querySelector('.sheet') || !document.querySelector('#toast').hidden || document.querySelector('#fimp-msg').textContent.trim()", timeout=5000)
            await page.wait_for_timeout(150)

        async def toast_text():
            return (await page.inner_text('#toast span')).strip() if await T("!document.querySelector('#toast').hidden") else ''

        async def msg_text():
            return (await page.inner_text('#fimp-msg')).strip()

        async def sheet_text():
            return await page.inner_text('.sheet') if await sheets() else ''

        async def food(fid):
            return await T("(id) => { const f = window.__tapnaplo.S.foods[id]; return f ? JSON.parse(JSON.stringify(f, (k, v) => (k[0] === '_' ? undefined : v))) : null; }", fid)

        # ---- a starting state: one food of my own, one diary entry that uses it
        today = await T("(() => { const d = new Date(); const p = (n) => String(n).padStart(2, '0'); return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`; })()")
        await T("(d) => { const t = window.__tapnaplo; t.S.foods['u:mine'] = { id: 'u:mine', src: 'user', name: 'My own soup', brand: '', barcode: '4012345678901', basis: { qty: 100, unit: 'g' }, n: { kcal: 60, protein: 3, carbohydrate: 7, fat: 2 }, nova: null, portions: [], note: '', created: 1000, updated: 1000 }; t.S.log.push({ id: 'e-mine', d, m: 'm1', f: 'u:mine', a: 200, t: Date.now(), tm: '08:00' }); t.save(); t.render(); }", today)
        base = await snap()

        # =========================================================== 1 the button
        await data_tab()
        lab = page.locator('label.btn', has_text='Import foods (JSON)')
        check('Data tab: the label "Import foods (JSON)" is there', await lab.count() == 1)
        check('it stands in the same row as "Restore from file"', await T("document.querySelector('#importfoods').closest('.row') === document.querySelector('#importfile').closest('.row')"))
        check('the file field takes JSON files and is hidden (the label is the button)', await T("(() => { const i = document.querySelector('#importfoods'); return i.type === 'file' && /json/.test(i.accept) && i.hidden; })()"))
        box = await lab.bounding_box()
        check('the button is at least 44 px high', box['height'] >= 44, box)
        card = await T("document.querySelector('#importfoods').closest('.card').innerText")
        check('the card says what it does and that the diary is not touched', 'never touches your diary' in card and 'replaces everything' in card, card[:300])
        check('the message area is inside the same card, so errors stand next to the button', await T("document.querySelector('#fimp-msg').closest('.card') === document.querySelector('#importfoods').closest('.card')"))

        # =========================================================== 2 new ids: added, diary and meta part ignored
        f1 = write('new', ffile(
            {'u:ai-a': v3food('u:ai-a', 'Almond drink'),
             'u:ai-b': v3food('u:ai-b', 'Oat drink', est=[], confidence='nincs becslés', fortified=False, nova=None, portions=[])},
            log=[{'id': 'zz', 'd': '2020-01-01', 'm': 'm1', 'f': 'u:ai-a', 'a': 1, 't': 1}], meta={'portions': {'u:ai-a': [{'label': 'X', 'grams': 1}]}, 'last': {'u:ai-a': 77}}))
        await pick(f1)
        check('new ids: no question, the foods are added at once', await sheets() == 0 and (await toast_text()).startswith('Imported 2 foods'), await toast_text())
        a = await food('u:ai-a'); b = await food('u:ai-b')
        check('new ids: both foods are in S.foods with their own id', a is not None and b is not None and a['id'] == 'u:ai-a' and b['id'] == 'u:ai-b')
        check('a food is an own food (src user), with created and updated set to now (the file had 0)', a['src'] == 'user' and a['created'] > 1e12 and a['updated'] > 1e12, (a['created'], a['updated']))
        check('values, est, confidence as letter, fortified, nova, portion, note are kept', a['n'] == {'kcal': 45, 'protein': 1, 'carbohydrate': 6.6, 'fat': 1.5, 'calcium': 120, 'vitamin_e': 1.1} and a['est'] == ['vitamin_e'] and a['q'] == 'l'
              and a['fortified'] is True and a['nova'] == 4 and a['portions'] == [{'label': '100 ml', 'grams': 100}] and a['note'] == 'Test note' and a['brand'] == 'Acme' and a['basis'] == {'qty': 100, 'unit': 'g'}, a)
        check('the word "confidence" is not stored (the app keeps the letter q)', 'confidence' not in a and 'confidence' not in b)
        check('"nincs becslés" becomes q "n"; no est and no fortified key on a plain food', b['q'] == 'n' and 'est' not in b and 'fortified' not in b, b)
        cur = json.loads(await snap())
        old = json.loads(base)
        check('the diary is exactly as it was (the log of the file is ignored)', cur[0] == old[0] and len(cur[0]) == 1)
        check('the meta part is exactly as it was (the meta of the file is ignored)', cur[2] == old[2], (cur[2], old[2]))
        check('the food that was there is untouched', cur[1]['u:mine'] == old[1]['u:mine'])
        check('getFood finds an imported food (it can be logged)', await T("!!window.__tapnaplo.getFood('u:ai-a') && window.__tapnaplo.vecOf(window.__tapnaplo.getFood('u:ai-a')).lo[0] === 45"))
        check('the sync sees them as records to upload', await T("() => { const r = window.__tapnaplo.syncRecords(); return r.has('f:u:ai-a') && r.has('f:u:ai-b'); }"))
        await page.click('[data-tab=foods]'); await page.wait_for_selector('#ffilter')
        lst = await page.inner_text('#flist')
        check('My foods lists them', 'Almond drink' in lst and 'Oat drink' in lst and 'My own soup' in lst, lst[:200])
        await data_tab()

        # ---- Undo of a plain import
        # (take the two foods out again by hand, then import once more to get a fresh toast with Undo)
        await T("() => { const t = window.__tapnaplo; delete t.S.foods['u:ai-a']; delete t.S.foods['u:ai-b']; t.save(); }")
        before_import = await snap()
        await pick(f1)
        check('the toast offers Undo', await page.locator('#toast button').count() == 1 and (await toast_text()).startswith('Imported 2 foods'))
        await page.click('#toast button'); await page.wait_for_timeout(200)
        check('Undo: the foods are gone and everything is as before the import', await snap() == before_import)
        await pick(f1)   # and in again for the next steps
        check('importing again works after an Undo', await food('u:ai-a') is not None and await food('u:ai-b') is not None)

        # =========================================================== 3 a colliding id: Skip / Overwrite / Cancel
        a0 = await food('u:ai-a')
        newer = v3food('u:ai-a', 'Almond drink', n={'kcal': 61, 'protein': 1.0, 'carbohydrate': 10, 'fat': 2.5, 'calcium': 140, 'vitamin_e': 1.5}, est=[], confidence='nincs becslés', fortified=False)
        f2 = write('clash', ffile({'u:ai-a': newer, 'u:ai-c': v3food('u:ai-c', 'Cashew drink', brand='Zed')}))
        before = await snap()
        await pick(f2)
        txt = await sheet_text()
        check('a collision opens a sheet "Import foods" and nothing is changed while it is open', await sheets() == 1 and 'Import foods' in txt and await snap() == before, txt[:200])
        check('the sheet says which food is already there and what Skip and Overwrite do', 'Already there' in txt and 'Almond drink' in txt and 'Skip' in txt and 'Overwrite' in txt, txt)
        btns = await T("[...document.querySelectorAll('.sheet [data-fi]')].map((b) => [b.dataset.fi, b.textContent.trim(), b.className])")
        check('the buttons are Skip (the default, first, primary), Overwrite, Cancel', [x[1] for x in btns] == ['Skip', 'Overwrite', 'Cancel'] and 'primary' in btns[0][2], btns)
        small = await T(BUTTON_SIZES, '.sheet [data-fi]')
        check('all buttons of the sheet are at least 44 px', small == [], small)
        bad = await T(CONTRAST_JS, '.sheet')
        check('contrast of the sheet is at least 4.5:1 (3:1 for large text)', bad == [], bad[:4])
        if SHOTS: await page.screenshot(path=f'{SHOTS}/fi_sheet.png')
        # Cancel
        await page.click('[data-fi=cancel]'); await page.wait_for_timeout(200)
        check('Cancel: the sheet closes and nothing changes, no toast', await sheets() == 0 and await snap() == before and await toast_text() == '')
        # Skip
        await pick(f2)
        await page.click('[data-fi=skip]'); await page.wait_for_timeout(200)
        t = await toast_text()
        check('Skip: the toast says 1 imported, 1 kept', t.startswith('Imported 1 food') and '1 kept as it was' in t, t)
        check('Skip: the existing food is exactly as it was, the new one is added', await food('u:ai-a') == a0 and await food('u:ai-c') is not None)
        await page.click('#toast button'); await page.wait_for_timeout(200)
        check('Undo after Skip: the new food is removed again, the rest is as before', await snap() == before)
        # Overwrite
        await pick(f2)
        await page.click('[data-fi=over]'); await page.wait_for_timeout(200)
        t = await toast_text()
        a1 = await food('u:ai-a')
        check('Overwrite: the toast says 2 imported, 1 overwritten', t.startswith('Imported 2 foods') and '1 overwritten' in t, t)
        check('Overwrite: the existing food has the values of the file', a1['n']['kcal'] == 61 and a1['n']['calcium'] == 140 and a1['q'] == 'n' and 'est' not in a1 and 'fortified' not in a1, a1)
        check('Overwrite: the food keeps its id and its created time, updated moves on', a1['id'] == 'u:ai-a' and a1['created'] == a0['created'] and a1['updated'] >= a0['updated'])
        check('Overwrite: the new food is added too', await food('u:ai-c') is not None)
        cur = json.loads(await snap())
        check('Overwrite: the diary and the meta are untouched', cur[0] == old[0] and cur[2] == old[2])
        await page.click('#toast button'); await page.wait_for_timeout(200)
        check('Undo after Overwrite: the old version is back exactly, the added food is gone', await snap() == before)

        # a new food that a diary entry already uses is not deleted by a late Undo
        await pick(f2)
        await page.click('[data-fi=skip]'); await page.wait_for_timeout(200)
        await T("(d) => { const t = window.__tapnaplo; t.S.log.push({ id: 'e-late', d, m: 'm2', f: 'u:ai-c', a: 50, t: Date.now(), tm: '09:00' }); t.save(); }", today)
        await page.click('#toast button'); await page.wait_for_timeout(200)
        check('Undo does not delete a new food that a diary entry uses meanwhile', await food('u:ai-c') is not None and await T("window.__tapnaplo.S.log.some((e) => e.id === 'e-late')"))
        await T("() => { const t = window.__tapnaplo; t.S.log = t.S.log.filter((e) => e.id !== 'e-late'); delete t.S.foods['u:ai-c']; t.save(); }")

        # =========================================================== 4 a unit change on a food the diary uses
        await T("(d) => { const t = window.__tapnaplo; t.S.log.push({ id: 'e-a', d, m: 'm1', f: 'u:ai-a', a: 100, t: Date.now(), tm: '10:00' }); t.save(); }", today)
        caps = write('unit', ffile({'u:ai-a': v3food('u:ai-a', 'Almond drink', basis={'qty': 1, 'unit': 'capsule'}, portions=[], est=[], confidence='nincs becslés', fortified=False)}))
        before = await snap()
        await pick(caps)
        txt = await sheet_text()
        check('a different unit on a food the diary uses: the sheet says it cannot be overwritten', 'cannot be overwritten' in txt and 'unit differs' in txt, txt)
        await page.click('[data-fi=over]'); await page.wait_for_timeout(200)
        t = await toast_text()
        check('Overwrite is refused for that food: nothing imported, 1 kept, food unchanged', t.startswith('Nothing imported') and '1 kept' in t and await snap() == before, t)
        check('no Undo button when nothing was imported', await page.locator('#toast button').count() == 0)
        await T("() => { const t = window.__tapnaplo; t.S.log = t.S.log.filter((e) => e.id !== 'e-a'); t.save(); }")

        # =========================================================== 5 invalid entries and other ids
        mixed = {'u:ai-d': v3food('u:ai-d', 'Dates', brand='Zed'),
                 'u:bad1': v3food('u:bad1', ''),
                 'u:bad2': {k: v for k, v in v3food('u:bad2', 'No basis').items() if k != 'basis'},
                 'u:bad3': v3food('u:bad3', 'Bad number', n={'kcal': 'abc'}, est=[], confidence='nincs becslés'),
                 'u:bad4': v3food('u:bad4', 'Bad est', est=['zinc']),
                 'u:bad5': v3food('u:zzz', 'Wrong id'),
                 'u:bad6': 'not an object',
                 'o:5900000000001': {'id': 'o:5900000000001', 'src': 'off', 'name': 'Saved product', 'basis': {'qty': 100, 'unit': 'g'}, 'n': {'kcal': 10}}}
        f3 = write('mixed', ffile(mixed))
        before = await snap()
        await pick(f3)
        txt = await sheet_text()
        check('invalid entries: the sheet counts them (6) and says they are skipped, with a reason', '6 entries are not valid' in txt and 'will be skipped' in txt and 'Bad number' in txt, txt)
        check('entries with another id prefix are named as left out', '1 entry has an id that does not start with' in txt and 'left out' in txt, txt)
        check('the button says what will be imported: 1 food', await T("document.querySelector('.sheet [data-fi=skip]').textContent.trim()") == 'Import 1 food')
        check('still nothing changed while the sheet is open', await snap() == before)
        await page.click('[data-fi=skip]'); await page.wait_for_timeout(200)
        t = await toast_text()
        check('the toast counts everything: 1 imported, 6 invalid, 1 with another id', t == 'Imported 1 food · 6 invalid skipped · 1 with other ids skipped', t)
        keys = sorted(json.loads(await snap())[1].keys())
        check('only the valid food was added (no u:bad*, no o: food)', keys == sorted(['u:mine', 'u:ai-a', 'u:ai-b', 'u:ai-d']), keys)
        await page.click('#toast button'); await page.wait_for_timeout(200)
        check('Undo removes it', await snap() == before)

        # nothing valid at all: a message next to the button, no sheet
        f4 = write('allbad', ffile({'u:x1': v3food('u:x1', ''), 'u:x2': v3food('u:x2', 'No numbers', n={'kcal': 'abc'}, est=[], confidence='nincs becslés')}))
        await pick(f4)
        m = await msg_text()
        check('nothing valid: "No food could be imported" with the first reasons, next to the button, no sheet', await sheets() == 0 and m.startswith('No food could be imported') and 'No numbers' in m and await snap() == before, m)
        check('that message is an alert (read out by screen readers)', await T("document.querySelector('#fimp-msg [role=alert]') !== null"))
        bad = await T(CONTRAST_JS, '#fimp-msg')
        check('contrast of the message', bad == [], bad)

        # =========================================================== 6 bad files
        async def bad_file(label, path, needle):
            await pick(path)
            m = await msg_text()
            check(f'bad file: {label}', needle.lower() in m.lower() and await sheets() == 0 and await snap() == before and await toast_text() == '', m)

        await bad_file('not JSON at all', write('txt', None, raw='Sajnos nem találtam meg ezt a terméket.'), 'not a Nutrilog file')
        await bad_file('JSON without "app"', write('noapp', {'foods': {'u:a': v3food('u:a', 'A')}}), 'not a Nutrilog file')
        await bad_file('a list instead of an object', write('list', [1, 2]), 'not a Nutrilog file')
        await bad_file('"foods" missing', write('nofoods', {'app': 'tapnaplo', 'version': 1}), 'no “foods” part')
        await bad_file('"foods" is a list', write('foodslist', {'app': 'tapnaplo', 'foods': [v3food('u:a', 'A')]}), 'no “foods” part')
        await bad_file('"foods" is empty', write('empty', ffile({})), 'empty')
        await bad_file('an unknown version', write('v2', {'app': 'tapnaplo', 'version': 2, 'foods': {'u:a': v3food('u:a', 'A')}}), 'version 2')
        # the message goes away with the next try
        await pick(f1)   # these two ids are there already, so the sheet opens
        check('the next attempt clears the old message', await msg_text() == '' and await sheets() == 1, await msg_text())
        await page.click('[data-fi=cancel]'); await page.wait_for_timeout(150)

        # =========================================================== 7 reading is tolerant, like Paste from AI
        fenced = write('fence', None, raw='﻿Here is the file:\n```json\n' + json.dumps(ffile({'u:ai-f': v3food('u:ai-f', 'Fenced food', brand='Fen')}), ensure_ascii=False) + '\n```\nDone.')
        await pick(fenced)
        check('a BOM, a sentence and a ``` fence around the JSON are skipped', (await toast_text()).startswith('Imported 1 food') and await food('u:ai-f') is not None, await toast_text() or await msg_text())
        # a full backup: only the foods are read
        full = write('full', {'app': 'tapnaplo', 'version': 1, 'exported': 'x', 'log': [{'id': 'zz2', 'd': '2020-01-01', 'm': 'm1', 'f': 'u:ai-g', 'a': 5, 't': 1}], 'foods': {'u:ai-g': v3food('u:ai-g', 'From a backup', brand='Bak', confidence=None, est=[], q='m')}, 'meta': {'backup': 5}})
        before = await snap()
        await pick(full)
        check('a full backup file: its foods are read, its diary and meta are ignored, a q letter is accepted', (await toast_text()).startswith('Imported 1 food') and (await food('u:ai-g'))['q'] == 'm'
              and json.loads(await snap())[0] == json.loads(before)[0] and json.loads(await snap())[2] == json.loads(before)[2], await toast_text() or await msg_text())

        # =========================================================== 8 look-alikes and odd values
        like = write('like', ffile({'u:ai-h': v3food('u:ai-h', 'Another name', brand='Zed2', barcode='4012345678901', est=[], confidence='nincs becslés'),
                                    'u:ai-i': v3food('u:ai-i', 'Odd values', brand='Odd', n={'kcal': 500, 'protein': 1, 'carbohydrate': 1, 'fat': 1}, est=[], confidence='nincs becslés')}))
        await pick(like)
        txt = await sheet_text()
        check('a new food with the barcode of one you have: the sheet says they look alike', 'Look like foods you already have' in txt and 'Another name' in txt and 'separate foods' in txt, txt)
        check('odd values (energy far from protein, carbohydrate, fat) are shown before the import', 'Check these values after the import' in txt and 'Odd values' in txt, txt)
        await page.click('[data-fi=skip]'); await page.wait_for_timeout(200)
        check('they are still imported (the sheet only informs)', await food('u:ai-h') is not None and await food('u:ai-i') is not None and (await toast_text()).startswith('Imported 2 foods'), await toast_text())

        # =========================================================== 9 no network
        check('the whole import made no request to any other site', outside == [], outside)

        # =========================================================== 10 Paste from AI reads the same shape
        P = lambda x: T('(t) => window.__tapnaplo.parseAiImport(t)', x if isinstance(x, str) else json.dumps(x, ensure_ascii=False))
        r = await P(ffile({'u:ai-p': v3food('u:ai-p', 'Pasted'), 'u:ai-q': v3food('u:ai-q', 'Pasted two', est=[], confidence='nincs becslés')}))
        check('Paste from AI: the v3 answer is read (foods as an object)', r['errors'] == [] and [x['food']['name'] for x in r['foods']] == ['Pasted', 'Pasted two'] and r['foods'][0]['food']['q'] == 'l', r['errors'])
        check('Paste from AI: the id and src of the file are not part of the food (the editor makes its own)', all('id' not in x['food'] and 'src' not in x['food'] for x in r['foods']))
        words = [('közepes', 'm'), ('Közepes', 'm'), ('KÖZEPES', 'm'), ('alacsony', 'l'), ('nagyon alacsony', 'v'), ('Nagyon alacsony', 'v'), ('magas', 'h'), ('nincs becslés', 'n'), ('nincs becsles', 'n'), ('nincs', 'n'),
                 ('high', 'h'), ('very low', 'v'), ('very_low', 'v'), ('none', 'n')]
        ok = []
        for w, q in words:
            rr = await P(ffile({'u:w': v3food('u:w', 'W', est=['vitamin_e'], confidence=w)}))
            ok.append((w, bool(rr['foods']) and rr['foods'][0]['food'].get('q') == q))
        check('every confidence word is read: Hungarian (with or without accents, any case) and English', all(x[1] for x in ok), [x for x in ok if not x[1]])
        rr = await P(ffile({'u:w': v3food('u:w', 'W', confidence=None, q='l')}))
        check('a q letter (as in a backup) is read when there is no confidence word', rr['errors'] == [] and rr['foods'][0]['food']['q'] == 'l', rr['errors'])
        for w in ['constructor', 'toString', 'magasabb', 'x']:
            rr = await P(ffile({'u:w': v3food('u:w', 'W', confidence=w)}))
            check(f'confidence "{w}" is an error (not a lookup in the object prototype)', len(rr['errors']) == 1 and 'confidence' in rr['errors'][0], rr['errors'])
        rr = await P(ffile({'u:w': v3food('u:w', 'W', est=['vitamin_e'], confidence=None)}))
        check('estimates without any confidence are still an error', len(rr['errors']) == 1 and 'confidence' in rr['errors'][0], rr['errors'])
        rr = await P({'app': 'tapnaplo', 'version': 1, 'log': [], 'foods': {'u:a': v3food('u:a', 'A')}})
        check('Paste from AI: a full backup is refused with a pointer to "Restore from file"', len(rr['errors']) == 1 and 'full backup' in rr['errors'][0] and 'Restore from file' in rr['errors'][0] and rr['foods'] == [], rr['errors'])
        rr = await P(ffile({}))
        check('Paste from AI: empty "foods" is an error', len(rr['errors']) == 1 and 'empty' in rr['errors'][0], rr['errors'])
        rr = await P(ffile({'u:a': v3food('u:a', 'A'), 'u:b': v3food('u:b', 'B', basis={'qty': 50, 'unit': 'g'})}))
        check('Paste from AI: one bad food stops the whole answer and the message names the food', len(rr['errors']) >= 1 and 'Food 2 (B)' in rr['errors'][0] and rr['foods'] == [], rr['errors'])
        rr = await P('Itt a JSON:\n```json\n' + json.dumps(ffile({'u:a': v3food('u:a', 'Fenced A')}), ensure_ascii=False) + '\n```')
        check('Paste from AI: the v3 answer inside a fence and text is found', rr['errors'] == [] and rr['foods'][0]['food']['name'] == 'Fenced A', rr['errors'])
        rr = await P({'nutrilog_import': 1, 'foods': [{'name': 'Old shape', 'basis': {'qty': 100, 'unit': 'g'}, 'n': {'kcal': 10}}]})
        check('Paste from AI: the old v1 shape (nutrilog_import) still works', rr['errors'] == [] and len(rr['foods']) == 1, rr['errors'])
        # in the app: My foods > Paste from AI > Read > the food editor, prefilled
        await page.click('[data-tab=foods]'); await page.wait_for_selector('#ffilter')
        await page.click('[data-act=ai-import]'); await page.wait_for_selector('#ai-text')
        await page.fill('#ai-text', json.dumps(ffile({'u:ai-ui': v3food('u:ai-ui', 'Pasted in the app', brand='Pas')}), ensure_ascii=False))
        await page.click('#ai-read'); await page.wait_for_selector('#fok')
        check('Paste from AI in the app: the v3 answer opens the food editor with the name and the confidence filled', await page.input_value('#fname') == 'Pasted in the app' and await page.input_value('#fconf') == 'l')
        await close_all()

        # =========================================================== 11 Restore from file with these files
        await data_tab()
        before = await snap()
        foodsonly = write('foodsonly', ffile({'u:ai-a': v3food('u:ai-a', 'A')}))   # (f1 has a diary part, so Restore would take it for a backup)
        await T("() => { document.querySelector('#toast').hidden = true; }")
        await page.set_input_files('#importfile', foodsonly); await page.wait_for_timeout(500)
        t = await toast_text()
        check('Restore from file with a foods-only file: refused, and it points to "Import foods (JSON)"', 'has foods but no diary' in t and 'Import foods (JSON)' in t and await sheets() == 0 and await snap() == before, t)
        bk = write('bk', {'app': 'tapnaplo', 'version': 1, 'log': [], 'foods': {'u:ai-r': v3food('u:ai-r', 'Restored', confidence='közepes')}, 'meta': {}})
        await page.set_input_files('#importfile', bk); await page.wait_for_selector('[data-ok]'); await page.click('[data-ok]'); await page.wait_for_timeout(600)
        rf = await food('u:ai-r')
        check('Restore from file turns a confidence word into the letter (a backup made by an artifact has words)', rf is not None and rf['q'] == 'm' and 'confidence' not in rf, rf)
        check('and the restore replaced everything else, as it always did', list(json.loads(await snap())[1].keys()) == ['u:ai-r'])

        # =========================================================== 12 dark theme
        await T("() => { localStorage.setItem('nutrilog.theme', 'dark'); }")
        await page.reload(); await page.wait_for_selector('#tabbar .tab')   # the Data tab is remembered, so there is no Diary hero
        await data_tab()
        await page.set_input_files('#importfoods', write('dark', ffile({'u:ai-r': v3food('u:ai-r', 'Restored'), 'u:ai-z': v3food('u:ai-z', 'Dark one')})))
        await page.wait_for_selector('.sheet')
        bad = await T(CONTRAST_JS, '.sheet')
        check('dark theme: contrast of the sheet', bad == [], bad[:4])
        small = await T(BUTTON_SIZES, '.sheet [data-fi]')
        check('dark theme: buttons at least 44 px', small == [], small)
        if SHOTS: await page.screenshot(path=f'{SHOTS}/fi_sheet_dark.png')
        await close_all()

        check('no page errors in the whole run', errs == [], errs[:5])
        await browser.close()
        for pth in made:
            try: pth.unlink()
            except OSError: pass
        print('\n' + ('ALL OK' if not problems else f'{len(problems)} FAILED: ' + '; '.join(problems)))
        sys.exit(1 if problems else 0)


if __name__ == '__main__':
    asyncio.run(main())
