"""Reading the answer of an AI (version 20): the reader of "Paste from AI" forgives the slips real AIs make. Run with the web server on port 8765 (see CLAUDE.md).

Norbert's answer for "Finest Bakery Derelye túrós" (tests/fixture_ai_answer_derelye.json.txt, as it was pasted) was refused as "cannot be read as JSON":
its note had a " that was not escaped (the Hungarian quote „ékezési só" closed with a plain "), and the answer ended with one } too many.
Covers: that answer loads (also through the real sheet and through Import foods (JSON)); every slip on its own (inner quote before a comma, a colon, a closing bracket;
a new line in a text; extra } at the end; trailing and missing commas; True/False/None; \\'; curly quotes as the JSON quotes; a fence and prose around it);
nothing is changed in the data (the note keeps its quote, numbers stay numbers, "__proto__" is only a name); what is really broken is still an error, and the
message says what is wrong and shows the place (a cut-off answer keeps the old "cut off" sentence); the message cannot inject HTML; a deeply nested text and a long
text full of { are fast; the old strict cases still behave the same."""
import asyncio, json, os, pathlib, sys, time
from playwright.async_api import async_playwright

URL = 'http://127.0.0.1:8765/index.html'
HERE = pathlib.Path(__file__).resolve().parent
REAL = (HERE / 'fixture_ai_answer_derelye.json.txt').read_text(encoding='utf-8').strip()
SHOTS = os.environ.get('SHOTS', '')


def doc(note, extra=''):
    """A small valid-looking answer; the note is put in as it is (not escaped), so the tests can break it on purpose."""
    return ('{"app":"tapnaplo","version":1,"foods":{"u:t-1":{"id":"u:t-1","src":"user","name":"Test oat","brand":"","barcode":"",'
            '"basis":{"qty":100,"unit":"g"},"n":{"kcal":100,"protein":5,"carbohydrate":15,"fat":2}' + extra + ',"note":"' + note + '","created":0,"updated":0}}}')


def curlify(s):
    """Every " becomes an opening or a closing curly quote, in turn: an AI that typed its JSON with a word processor's quotes."""
    out, k = [], 0
    for c in s:
        if c == '"':
            out.append('\u201c' if k % 2 == 0 else '\u201d'); k += 1
        else:
            out.append(c)
    return ''.join(out)


async def main():
    async with async_playwright() as p:
        problems = []

        def check(name, ok, info=''):
            print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(info)) if info != '' else ''))
            if not ok: problems.append(name)

        browser = await p.chromium.launch()
        errs = []
        ctx = await browser.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True, locale='en-GB', service_workers='block')
        await ctx.route('**/*openfoodfacts.org/**', lambda r: r.fulfill(status=200, headers={'access-control-allow-origin': '*', 'content-type': 'application/json'}, body='{"products":[],"status":0}'))
        page = await ctx.new_page()
        page.on('pageerror', lambda e: errs.append(f'PE {e}'))
        page.on('console', lambda m: errs.append(f'C {m.text}') if m.type == 'error' and 'Failed to load resource' not in m.text else None)
        await page.goto(URL); await page.wait_for_selector('.hero')
        T = page.evaluate

        async def parse(text):
            return await T("(t) => { const r = window.__tapnaplo.parseAiImport(t); return { errors: r.errors, foods: r.foods.map((x) => x.food), warnings: r.foods.map((x) => x.warnings) }; }", text)

        async def ok_note(note, note_expected, label):
            r = await parse(doc(note))
            good = r['errors'] == [] and len(r['foods']) == 1 and r['foods'][0]['name'] == 'Test oat' and r['foods'][0].get('note') == note_expected
            check(label, good, r['errors'] or (r['foods'][0].get('note') if r['foods'] else 'no food'))
            return r

        # ---- 1 the real answer ----
        r = await parse(REAL)
        f = r['foods'][0] if r['foods'] else {}
        check('the answer Norbert pasted loads: no error, one food', r['errors'] == [] and len(r['foods']) == 1, r['errors'])
        check('name, brand, barcode, basis, portion', f.get('name') == 'Finest Bakery Derelye túrós' and f.get('brand') == 'Finest Bakery' and f.get('barcode') == '4099200704739' and f.get('basis') == {'qty': 100, 'unit': 'g'} and f.get('portions') == [{'label': '1 adag', 'grams': 150}], f)
        check('values are numbers and unchanged', f.get('n') == {'kcal': 200, 'protein': 7, 'carbohydrate': 40, 'sugars': 6.3, 'fat': 1.2, 'fa_saturated': 0.5, 'salt': 0.65, 'sodium': 260}, f.get('n'))
        check('estimate, confidence and NOVA are read (sodium is an estimate, high)', f.get('est') == ['sodium'] and f.get('q') == 'h' and f.get('nova') == 4, [f.get('est'), f.get('q'), f.get('nova')])
        check('"fortified": false is not kept, it is only ever true', 'fortified' not in f)
        check('the note keeps its quote and every word', '(pl. „ékezési só"). A nátrium' in f.get('note', '') and f['note'].startswith('Gyártói címke') and f['note'].endswith('feldolgozott termék).'), f.get('note', '')[-120:])
        check('no warning for this answer', r['warnings'] == [[]], r['warnings'])

        # ---- 2 through the real sheet ----
        await page.click('[data-tab=foods]'); await page.wait_for_selector('#ffilter')
        await page.click('[data-act=ai-import]'); await page.wait_for_selector('#ai-text')
        await page.fill('#ai-text', REAL)
        await page.click('#ai-read'); await page.wait_for_selector('#fok', timeout=5000)
        check('the sheet opens the review of the food (no red message)', await T("document.querySelector('#ai-msg .note') === null") and await T("document.querySelector('#fname').value") == 'Finest Bakery Derelye túrós', await T("document.querySelector('#fname') && document.querySelector('#fname').value"))
        check('the note field of the review holds the whole note with the quote', '„ékezési só"' in await T("document.querySelector('#fnote').value"))
        await page.click('#fok'); await page.wait_for_timeout(500)
        saved = await T("Object.values(window.__tapnaplo.S.foods).find((x) => x.name === 'Finest Bakery Derelye túrós')")
        check('Save keeps it: barcode, est, quality letter and the note with the quote', bool(saved) and saved['barcode'] == '4099200704739' and saved['est'] == ['sodium'] and saved['q'] == 'h' and '„ékezési só"' in saved['note'], saved)
        for _ in range(6):
            if not await T("document.querySelectorAll('.sheet').length"): break
            await page.click('.sheet-wrap:last-of-type [data-x]'); await page.wait_for_timeout(120)

        # ---- 3 the same text as a file for Import foods (JSON) ----
        pf = await T("(t) => { const r = window.__tapnaplo.parseFoodsFile(t); return { error: r.error, n: r.foods.length, names: r.foods.map((x) => x.food.name), invalid: r.invalid.length }; }", REAL)
        check('Import foods (JSON) reads the same text too', pf['error'] == '' and pf['n'] == 1 and pf['names'] == ['Finest Bakery Derelye túrós'] and pf['invalid'] == 0, pf)

        # ---- 4 every slip on its own ----
        await ok_note('Sima megjegyzés.', 'Sima megjegyzés.', 'baseline: a clean answer still loads')
        await ok_note('pl. „ékezési só" a címkén', 'pl. „ékezési só" a címkén', 'a " before a space and a word is a quote inside the text')
        await ok_note('He said "yes", and left', 'He said "yes", and left', 'a " before a comma and a word is a quote inside the text')
        await ok_note('see "salt": 0,65 g', 'see "salt": 0,65 g', 'a " before a colon inside a text that is not a name is kept')
        await ok_note('end with a quote "x"', 'end with a quote "x"', 'a note that ends with a quoted word')
        await ok_note('a (b) [c] {d} „e" "f"', 'a (b) [c] {d} „e" "f"', 'brackets and braces inside the note do not matter')
        await ok_note('curly “idézet” is fine', 'curly “idézet” is fine', 'curly quotes inside a text stay as they are')
        await ok_note('line one\nline two', 'line one\nline two', 'a real new line inside a text')
        await ok_note('tab\there', 'tab\there', 'a real tab inside a text')
        await ok_note('it\\\'s ok', "it's ok", "a wrong escape \\' is the character itself")
        await ok_note('real \\"escaped\\" quote and \\n new line and \\u00e9', 'real "escaped" quote and \n new line and é', 'correct escapes still work (\\" \\n \\u00e9)')
        await ok_note('x', 'x', 'baseline again')
        r = await parse(doc('x') + '}}')
        check('two extra } at the end are ignored', r['errors'] == [] and len(r['foods']) == 1, r['errors'])
        r = await parse('Itt a tétel:\n```json\n' + doc('x') + '\n```\nKész, jó étvágyat!')
        check('a fence and sentences around it are ignored', r['errors'] == [] and len(r['foods']) == 1, r['errors'])
        r = await parse(doc('x').replace('"fat":2}', '"fat":2,}').replace('"updated":0}}}', '"updated":0,}}}'))
        check('trailing commas are ignored', r['errors'] == [] and len(r['foods']) == 1, r['errors'])
        r = await parse(doc('x').replace('"brand":"","barcode":""', '"brand":"" "barcode":""'))
        check('a comma missing before the next name is let through', r['errors'] == [] and len(r['foods']) == 1, r['errors'])
        r = await parse(doc('x', ',"fortified":True,"nova":None'))
        check('True / None (Python style) are read', r['errors'] == [] and len(r['foods']) == 1 and r['foods'][0].get('fortified') is True and r['foods'][0].get('nova') in (None, 0), [r['errors'], r['foods']])
        r = await parse(curlify(doc('Sima')))
        check('a whole answer in curly quotes (every " an opening or closing one) still loads', len(r['foods']) == 1 and r['errors'] == [], r['errors'])
        r = await parse('{"nutrilog_import":1,"foods":[{"name":"V1 food","basis":{"qty":100,"unit":"g"},"n":{"kcal":10},"note":"mondta: "igen" és ment"}]}')
        check('the older answer shape (nutrilog_import, a list) gets the same forgiveness', r['errors'] == [] and len(r['foods']) == 1 and r['foods'][0]['note'] == 'mondta: "igen" és ment', r['errors'])
        r = await parse('{"app":"tapnaplo","foods":{"u:a":{"name":"Proto","basis":{"qty":100,"unit":"g"},"n":{"kcal":10},"__proto__":{"polluted":1}}}}')
        check('"__proto__" is only a name: nothing leaks into other objects', await T("({}).polluted") is None and await T("Object.prototype.polluted") is None)

        # ---- 5 what is really broken stays an error, and the message says where ----
        cut = doc('x')[:-25]
        r = await parse(cut)
        check('a cut-off answer: the old "cut off" sentence', len(r['errors']) == 1 and 'cannot be read as JSON' in r['errors'][0] and 'cut off' in r['errors'][0] and '⟨here⟩' not in r['errors'][0] and r['foods'] == [], r['errors'])
        r = await parse(doc('x').replace('"kcal":100', '"kcal":'))
        e = r['errors'][0] if r['errors'] else ''
        check('a missing value: says so and shows the place', 'cannot be read as JSON: a value was expected here' in e and '⟨here⟩' in e and '"kcal":⟨here⟩,"protein":5' in e and 'cut off' not in e and r['foods'] == [], e)
        r = await parse(doc('x').replace('"kcal":100', '"kcal":0,65'))
        e = r['errors'][0] if r['errors'] else ''
        check('a decimal comma in a number: the place is shown', 'a name in quotes was expected here' in e and '"kcal":0,⟨here⟩65,"protein"' in e, e)
        r = await parse(doc('x').replace('"id":"u:t-1",', '"id" "u:t-1",'))
        e = r['errors'][0] if r['errors'] else ''
        check('a colon missing after a name: the place is shown', 'a colon was expected after the name' in e and '⟨here⟩' in e, e)
        r = await parse(doc('x').replace('"n":{"kcal":100,"protein":5,"carbohydrate":15,"fat":2}', '"n":{"kcal":100 "protein"5}'))
        e = r['errors'][0] if r['errors'] else ''
        check('another slip in the numbers: error, no food, place shown', 'cannot be read as JSON' in e and '⟨here⟩' in e and r['foods'] == [], e)
        r = await parse('Itt egy példa: {"a":1} és ennyi.')
        check('JSON without the Nutrilog marker: "No JSON found", as before', len(r['errors']) == 1 and r['errors'][0].startswith('No JSON found'), r['errors'])
        r = await parse('csak szöveg, nincs benne semmi')
        check('plain text: "No JSON found", as before', len(r['errors']) == 1 and r['errors'][0].startswith('No JSON found'), r['errors'])
        r = await parse('   ')
        check('empty box: "Paste the answer", as before', len(r['errors']) == 1 and r['errors'][0].startswith('Paste the answer'), r['errors'])
        r = await parse('{"app":"tapnaplo","version":1,"foods":{"u:a":{"name":"Bad unit","basis":{"qty":100,"unit":"g"},"n":{"kcal":"abc"}}}}')
        check('a readable answer with a bad value: the old food error, not a JSON error', len(r['errors']) >= 1 and 'cannot be read as JSON' not in r['errors'][0], r['errors'])

        # ---- 6 the message in the real sheet: shown, and not HTML ----
        evil = doc('x').replace('"kcal":100', '"kcal":<b id=injected>X</b>')
        await page.click('[data-tab=foods]'); await page.wait_for_selector('#ffilter')
        await page.click('[data-act=ai-import]'); await page.wait_for_selector('#ai-text')
        await page.fill('#ai-text', evil)
        await page.click('#ai-read'); await page.wait_for_timeout(300)
        msg = await page.inner_text('#ai-msg')
        check('the sheet shows the problem and its place', 'cannot be read as JSON' in msg and '⟨here⟩' in msg, msg)
        check('text of the answer is shown as text (no element is created from it)', await T("document.querySelector('#injected') === null") and '<b id=injected>' in msg, msg)
        check('the box is marked invalid and the sheet stays open', await page.get_attribute('#ai-text', 'aria-invalid') == 'true' and await T("document.querySelectorAll('.sheet').length") == 1)
        if SHOTS:
            await page.screenshot(path=os.path.join(SHOTS, 'ai_json_error.png'))
        for _ in range(6):
            if not await T("document.querySelectorAll('.sheet').length"): break
            await page.click('.sheet-wrap:last-of-type [data-x]'); await page.wait_for_timeout(120)

        # ---- 7 speed and safety ----
        t0 = time.time()
        r = await parse('{"app":"tapnaplo","x":' + '[' * 30000)
        dt = time.time() - t0
        check('a text nested 30 000 deep is an error, not a crash, and quick', len(r['errors']) == 1 and r['foods'] == [] and dt < 3, [r['errors'], round(dt, 2)])
        t0 = time.time()
        r = await parse(('{ ' * 3000) + ' "tapnaplo" ' + ('} ' * 3000))
        dt = time.time() - t0
        check('3 000 braces in a row are quick (at most 300 starting points are tried)', dt < 5, round(dt, 2))
        t0 = time.time()
        big = '{"app":"tapnaplo","version":1,"foods":{' + ','.join('"u:b%d":{"name":"Food %d","basis":{"qty":100,"unit":"g"},"n":{"kcal":%d},"note":"n „x" y"}' % (i, i, i) for i in range(400)) + '}}'
        r = await parse(big)
        dt = time.time() - t0
        check('400 foods in one answer, every note with an inner quote: all read, quick', r['errors'] == [] and len(r['foods']) == 400 and dt < 3, [r['errors'][:1], len(r['foods']), round(dt, 2)])

        check('no page errors', errs == [], errs[:5])
        await browser.close()
        print('\nALL PASS' if not problems else f'\n{len(problems)} FAILED: {problems}')
        sys.exit(1 if problems else 0)


asyncio.run(main())
