"""Estimate marker (est), version 15: what the person sees of a value that is an estimate, and what the two CSV files say about it. Run with the web server on port 8765.

Covers: the ~ before an estimated value on the Nutrients tab (and not before a label value), the detail line, the line "Estimated values: N" in the Amount sheet,
totals that include the estimates, the entries CSV column est_keys (keys separated by ;, same as the __est columns, also for estimated energy and for dmBio products),
the daily CSV column est_share (worked out here by hand), old saves and old backups without est / q / fortified (nothing is marked, nothing breaks), a stale est key
that has no value (ignored), est without a confidence (still works), the description on the Data tab, touch targets."""
import asyncio, csv, io, json, os, pathlib, sys
from playwright.async_api import async_playwright
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_ai_import import CONTRAST_JS

URL = 'http://127.0.0.1:8765/index.html'
HERE = pathlib.Path(__file__).resolve().parent
SHOTS = os.environ.get('SHOTS', '')


def own(fid, name, n, **kw):
    f = {'id': fid, 'src': 'user', 'name': name, 'brand': '', 'barcode': '', 'basis': {'qty': 100, 'unit': 'g'}, 'n': n, 'nova': None, 'portions': [], 'note': '', 'created': 1000, 'updated': 1000}
    f.update(kw)
    return f


async def main():
    async with async_playwright() as p:
        problems, made = [], []

        def check(name, ok, info=''):
            print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(info)) if info != '' else ''))
            if not ok: problems.append(name)

        browser = await p.chromium.launch()
        errs = []
        ctx = await browser.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True, locale='en-GB', service_workers='block', accept_downloads=True)
        await ctx.route('**/*openfoodfacts.org/**', lambda r: r.fulfill(status=200, headers={'access-control-allow-origin': '*', 'content-type': 'application/json'}, body='{"products":[],"status":0}'))
        page = await ctx.new_page()
        page.on('pageerror', lambda e: errs.append(f'PE {e}'))
        page.on('console', lambda m: errs.append(f'C {m.text}') if m.type == 'error' and 'Failed to load resource' not in m.text else None)
        await page.goto(URL); await page.wait_for_selector('.hero')
        T = page.evaluate

        async def csv_of(act, name):
            async with page.expect_download() as d:
                await page.click(f'[data-act={act}]')
            dl = await d.value
            path = HERE / name
            await dl.save_as(str(path)); made.append(path)
            return list(csv.DictReader(io.StringIO(path.read_text(encoding='utf-8-sig'))))

        nrow = lambda name: T("(n) => { const d = [...document.querySelectorAll('details.nrow')].find((x) => x.querySelector('summary').innerText.includes(n)); return d ? d.innerText : null; }", name)

        today, yesterday = await T("""(() => { const f = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; const a = new Date(), b = new Date(); b.setDate(b.getDate() - 1); return [f(a), f(b)]; })()""")

        # ---- foods: E has two estimated micronutrients, L is label only, K has an estimated energy, N has an est without a confidence
        E = own('u:est', 'Oat flakes', {'kcal': 50, 'protein': 2, 'carbohydrate': 8, 'fat': 1, 'calcium': 100, 'vitamin_e': 1.0, 'zinc': 0.4}, est=['vitamin_e', 'zinc'], q='l', fortified=True, note='A note')
        L = own('u:lab', 'Label only', {'kcal': 100, 'protein': 10, 'carbohydrate': 10, 'fat': 3, 'calcium': 50, 'vitamin_e': 2.0})
        K = own('u:ken', 'Rice cake', {'kcal': 80, 'protein': 4, 'carbohydrate': 10, 'fat': 2, 'vitamin_e': 0.5}, est=['kcal', 'vitamin_e'], q='m')
        N = own('u:noq', 'Soy bar', {'kcal': 70, 'protein': 3, 'carbohydrate': 9, 'fat': 2, 'zinc': 1.0}, est=['zinc'])
        await T("""([foods, d1, d2]) => { const t = window.__tapnaplo; for (const f of foods) t.S.foods[f.id] = f;
            const e = (id, d, f, a, tm) => ({ id, d, m: 'm1', f, a, t: Date.now(), tm });
            t.S.log.push(e('e1', d1, 'u:est', 200, '08:00'), e('e2', d1, 'u:lab', 100, '09:00'), e('e3', d2, 'u:est', 100, '08:00'), e('e4', d1, 'u:ken', 100, '10:00'), e('e5', d1, 'u:noq', 100, '11:00'));
            t.save(); t.render(); }""", [[E, L, K, N], today, yesterday])

        # =========================================================== 1 Nutrients tab
        await page.click('[data-tab=nutr]'); await page.wait_for_selector('details.nrow')
        await T("document.querySelectorAll('#view details').forEach((d) => d.open = true)")
        ve, ca, zn, en = await nrow('Vitamin E'), await nrow('Calcium'), await nrow('Zinc'), await nrow('Energy')
        check('Nutrients tab: an estimated value (vitamin E) has a ~ before the number', ve is not None and '~' in ve.split('Estimate')[0], ve)
        check('Nutrients tab: another estimated value (zinc) has a ~', zn is not None and '~' in zn.split('Estimate')[0], zn)
        check('Nutrients tab: a label value (calcium) has no ~ and no estimate line', ca is not None and '~' not in ca and 'Estimate' not in ca, ca)
        check('Nutrients tab: the detail line names the foods and their confidence', ve is not None and 'Estimate, not a label value' in ve and 'Oat flakes (low)' in ve and 'Rice cake (medium)' in ve, ve)
        check('Nutrients tab: an est without a confidence is marked too, the line names the food without a confidence', zn is not None and 'Soy bar' in zn and 'Soy bar (' not in zn, zn)
        check('Nutrients tab: the energy of one entry is estimated, so the energy has a ~ as well', en is not None and '~' in en.split('Estimate')[0], en)
        # totals include the estimates: vitamin E = 2.0 (200 g E) + 2.0 (L) + 0.5 (K) = 4.5 mg
        check('the totals include the estimated values (vitamin E 4.5 mg)', await T("() => { const t = window.__tapnaplo; const T = t.totalsFor(t.S.log.filter((e) => e.d === '" + today + "')); return Math.abs(T.lo[t.IDX.vitamin_e] - 4.5) < 1e-9 && T.est[t.IDX.vitamin_e] === 2; }"))
        if SHOTS: await page.screenshot(path=f'{SHOTS}/est_nutrients.png', full_page=True)

        # =========================================================== 2 Amount sheet
        await page.click('[data-tab=log]'); await page.wait_for_selector('.hero')
        await page.click('.entry:has-text("Oat flakes")'); await page.wait_for_selector('#amt')
        summ = await T("[...document.querySelectorAll('.sheet details > summary')].map((s) => s.innerText.trim())")
        check('Amount sheet: a line "Estimated values: 2 · confidence low" (the number of estimated values)', 'Estimated values: 2 · confidence low' in summ, summ)
        small = await T("[...document.querySelectorAll('.sheet details > summary')].map((s) => Math.round(s.getBoundingClientRect().height)).filter((h) => h < 44)")
        check('the summary line is a touch target of at least 44 px', small == [], small)
        await T("document.querySelectorAll('.sheet details').forEach((d) => d.open = true)")
        txt = await T("[...document.querySelectorAll('.sheet details')].map((d) => d.innerText).join('\\n')")
        check('Amount sheet: opens to the names of the estimated values, the fortified warning and the note', 'vitamin e' in txt.lower() and 'zinc' in txt.lower() and 'fortified' in txt.lower() and 'A note' in txt, txt)
        bad = await T(CONTRAST_JS, '.sheet')
        check('Amount sheet: contrast', bad == [], bad[:3])
        await page.click('.sheet-wrap:last-of-type [data-x]'); await page.wait_for_timeout(200)
        await page.click('.entry:has-text("Label only")'); await page.wait_for_selector('#amt')
        summ = await T("[...document.querySelectorAll('.sheet details > summary')].map((s) => s.innerText.trim())")
        check('Amount sheet: a label-only food has no estimate line', not any('Estimated' in x for x in summ), summ)
        await page.click('.sheet-wrap:last-of-type [data-x]'); await page.wait_for_timeout(200)
        await page.click('.entry:has-text("Soy bar")'); await page.wait_for_selector('#amt')
        summ = await T("[...document.querySelectorAll('.sheet details > summary')].map((s) => s.innerText.trim())")
        check('Amount sheet: an est without a confidence says "confidence not set"', 'Estimated values: 1 · confidence not set' in summ, summ)
        await page.click('.sheet-wrap:last-of-type [data-x]'); await page.wait_for_timeout(200)

        # =========================================================== 3 entries CSV: est_keys
        await page.click('[data-tab=data]'); await page.wait_for_selector('[data-act=export-entries]')
        rows = await csv_of('export-entries', 'tmp_est_entries.csv')
        head = list(rows[0].keys())
        check('entries CSV: est_keys comes right after estimate_confidence', head[head.index('estimate_confidence') + 1] == 'est_keys', head[:14])
        byid = {r['food_id']: r for r in rows if r['date'] == today}
        idx = await T("window.__tapnaplo.IDX")
        order = lambda ks: ';'.join(sorted(ks, key=lambda k: idx[k]))
        check('est_keys: the estimated keys of the entry, separated by ;', byid['u:est']['est_keys'] == order(['vitamin_e', 'zinc']) and ';' in byid['u:est']['est_keys'], byid['u:est']['est_keys'])
        check('est_keys: empty for a label-only food', byid['u:lab']['est_keys'] == '')
        check('est_keys: estimated energy is named (kcal) together with the other keys, and energy_estimated is 1', byid['u:ken']['est_keys'] == order(['kcal', 'vitamin_e']) and byid['u:ken']['energy_estimated'] == '1', (byid['u:ken']['est_keys'], byid['u:ken']['energy_estimated']))
        check('est_keys: an est without a confidence is listed too (estimate_confidence is empty)', byid['u:noq']['est_keys'] == 'zinc' and byid['u:noq']['estimate_confidence'] == '', (byid['u:noq']['est_keys'], byid['u:noq']['estimate_confidence']))
        # the same keys as the __est columns, for every row
        est_cols = [h for h in head if h.endswith('__est')]
        same = all(set(filter(None, r['est_keys'].split(';'))) == {h[:-len('__est')].rsplit('_', 1)[0] for h in est_cols if r[h] == '1'} for r in rows)
        check('est_keys agrees with the __est columns in every row', same)

        # a dmBio product: every value that is not on the dm label is an estimate
        dm = 'dm:1459848'   # Bio olívaolaj: label values for energy and macros, the rest estimated (confidence high)
        if await T("(id) => !!window.__tapnaplo.getFood(id)", dm):
            await T("([id, d]) => { const t = window.__tapnaplo; t.S.log.push({ id: 'e-dm', d, m: 'm2', f: id, a: 100, t: Date.now(), tm: '12:00' }); t.save(); t.render(); }", [dm, today])
            await page.click('[data-tab=data]'); await page.wait_for_selector('[data-act=export-entries]')
            rows = await csv_of('export-entries', 'tmp_est_entries2.csv')
            r = [x for x in rows if x['food_id'] == dm][0]
            keys = [k for k in r['est_keys'].split(';') if k]
            cols = [h for h in r.keys() if h.endswith('__est') and r[h] == '1']
            check('dmBio product: est_keys lists its estimated values (as many as the __est columns say)', len(keys) == len(cols) and (len(keys) > 0 or r['estimate_confidence'] in ('none', '')), (len(keys), len(cols), r['estimate_confidence']))
            await T("() => { const t = window.__tapnaplo; t.S.log = t.S.log.filter((e) => e.id !== 'e-dm'); t.save(); }")
        else:
            check('dmBio product: found for the check', False)

        # =========================================================== 4 daily CSV: est_share
        await page.click('[data-tab=data]'); await page.wait_for_selector('[data-act=export-days]')
        days = await csv_of('export-days', 'tmp_est_days.csv')
        head = list(days[0].keys())
        check('daily CSV: est_share stands after "entries"', head[:3] == ['date', 'entries', 'est_share'], head[:4])
        d = {r['date']: r for r in days}
        # yesterday: only 100 g of E. Nutrients with data: kcal, protein, carbohydrate, fat, calcium, vitamin_e, zinc. Estimated parts: vitamin_e 100 %, zinc 100 %, the others 0 %: 2 / 7 = 28.6 %
        check('est_share, a day with one food: (0+0+0+0+0+1+1) / 7 = 28.6', d[yesterday]['est_share'] == '28.6', d[yesterday]['est_share'])
        # today: E 200 g, L 100 g, K 100 g, N 100 g.
        #   kcal: 100+100+80+70 = 350, estimated (K) 80 -> 0.22857
        #   protein 4+10+4+3 = 21 (est share 0), carbohydrate 16+10+10+9 (0), fat 2+3+2+2 (0), calcium 200+50 (0)
        #   vitamin_e: 2.0 + 2.0 + 0.5 = 4.5; estimated: E 2.0 + K 0.5 = 2.5 -> 0.55556
        #   zinc: 0.8 (E, est) + 1.0 (N, est) = 1.8 -> all estimated = 1
        want = round(100 * (80 / 350 + 0 + 0 + 0 + 0 + 2.5 / 4.5 + 1) / 7, 1)
        check(f'est_share, a day with four foods, worked out by hand: {want}', abs(float(d[today]['est_share']) - want) < 0.051, (d[today]['est_share'], want))
        check('est_share has one decimal at most', all(len(r['est_share'].split('.')[-1]) <= 1 for r in days if r['est_share']))
        # a day with label values only
        await T("() => { const t = window.__tapnaplo; t.S.log.push({ id: 'e-lab', d: '2020-05-05', m: 'm1', f: 'u:lab', a: 100, t: 5, tm: '08:00' }); t.save(); }")
        await page.click('[data-tab=log]'); await page.click('[data-tab=data]'); await page.wait_for_selector('[data-act=export-days]')
        days = await csv_of('export-days', 'tmp_est_days2.csv')
        d = {r['date']: r for r in days}
        check('est_share is 0 for a day that is label values only', d['2020-05-05']['est_share'] == '0', d['2020-05-05']['est_share'])
        check('the __est count columns are still there for the days with estimates', 'vitamin_e_mg__est' in d[today] and d[today]['vitamin_e_mg__est'] == '2' and d[today]['zinc_mg__est'] == '2', {k: d[today].get(k) for k in ('vitamin_e_mg__est', 'zinc_mg__est')})
        # a day that has entries but no nutrient with data
        await T("() => { const t = window.__tapnaplo; t.S.foods['u:empty'] = { id: 'u:empty', src: 'user', name: 'Empty food', brand: '', barcode: '', basis: { qty: 100, unit: 'g' }, n: {}, nova: null, portions: [], note: '', created: 1, updated: 1 }; t.S.log.push({ id: 'e-empty', d: '2020-05-06', m: 'm1', f: 'u:empty', a: 100, t: 6, tm: '08:00' }); t.save(); }")
        await page.click('[data-tab=log]'); await page.click('[data-tab=data]'); await page.wait_for_selector('[data-act=export-days]')
        days = await csv_of('export-days', 'tmp_est_days3.csv')
        d = {r['date']: r for r in days}
        check('est_share is empty (not 0) when no nutrient has data that day', d['2020-05-06']['est_share'] == '', d['2020-05-06']['est_share'])
        txt = await page.inner_text('#view')
        check('Data tab: the CSV description names est_keys and est_share', 'est_keys' in txt and 'est_share' in txt and 'semicolons' in txt, [l for l in txt.split('\n') if 'est_' in l][:2])

        # =========================================================== 5 old saves and old backups
        old = {'app': 'tapnaplo', 'version': 1, 'log': [
                  {'id': 'o1', 'd': today, 'm': 'm1', 'f': 'u:old', 'a': 150, 't': 1700000000000},          # no tm: made before version 6
                  {'id': 'o2', 'd': today, 'm': 'm1', 'f': 'u:stale', 'a': 100, 't': 1700000001000, 'tm': '10:00'}],
               'foods': {'u:old': own('u:old', 'Old food', {'kcal': 120, 'protein': 6, 'carbohydrate': 15, 'fat': 4, 'calcium': 80, 'vitamin_e': 0.8}),   # no est, q or fortified at all
                         'u:stale': own('u:stale', 'Stale est', {'kcal': 60, 'protein': 2, 'carbohydrate': 9, 'fat': 1}, est=['zinc'], q='l'),             # est lists a key that has no value
                         'u:empty-est': own('u:empty-est', 'Empty est', {'kcal': 30, 'protein': 1}, est=[])},
               'meta': {}}
        path = HERE / 'tmp_est_old.json'; path.write_text(json.dumps(old), encoding='utf-8'); made.append(path)
        await page.click('[data-tab=data]'); await page.wait_for_selector('#importfile', state='attached')
        await page.set_input_files('#importfile', str(path)); await page.wait_for_selector('[data-ok]'); await page.click('[data-ok]'); await page.wait_for_timeout(600)
        check('the old backup is restored', await T("Object.keys(window.__tapnaplo.S.foods).sort().join()") == 'u:empty-est,u:old,u:stale')
        await page.click('[data-tab=nutr]'); await page.wait_for_selector('details.nrow')
        await T("document.querySelectorAll('#view details').forEach((d) => d.open = true)")
        txt = await T("[...document.querySelectorAll('details.nrow')].map((d) => d.innerText).join('\\n')")
        check('old backup: no ~ anywhere on the Nutrients tab and no estimate line', '~' not in txt and 'Estimate' not in txt, [l for l in txt.split('\n') if '~' in l or 'Estimate' in l][:3])
        await page.click('[data-tab=log]'); await page.wait_for_selector('.hero')
        hero = await page.inner_text('.hero')
        check('old backup: the Diary has no ~', '~' not in hero and 'estimate' not in (await page.inner_text('#view')).lower(), hero.replace('\n', ' '))
        await page.click('.entry:has-text("Old food")'); await page.wait_for_selector('#amt')
        summ = await T("[...document.querySelectorAll('.sheet details > summary')].map((s) => s.innerText.trim())")
        check('old backup: the Amount sheet has no estimate line', not any('Estimated' in x for x in summ), summ)
        await page.click('.sheet-wrap:last-of-type [data-x]'); await page.wait_for_timeout(200)
        await page.click('.entry:has-text("Stale est")'); await page.wait_for_selector('#amt')
        summ = await T("[...document.querySelectorAll('.sheet details > summary')].map((s) => s.innerText.trim())")
        check('an est key without a value is ignored (no estimate line)', not any('Estimated' in x for x in summ), summ)
        await page.click('.sheet-wrap:last-of-type [data-x]'); await page.wait_for_timeout(200)
        await page.click('[data-tab=data]'); await page.wait_for_selector('[data-act=export-entries]')
        rows = await csv_of('export-entries', 'tmp_est_entries3.csv')
        check('old backup: est_keys is empty in every row (also with a stale est key)', len(rows) == 2 and all(r['est_keys'] == '' for r in rows), [(r['food_id'], r['est_keys']) for r in rows])
        check('old backup: no __est column at all', not [h for h in rows[0].keys() if h.endswith('__est')], [h for h in rows[0].keys() if h.endswith('__est')])
        days = await csv_of('export-days', 'tmp_est_days4.csv')
        check('old backup: est_share is 0', all(r['est_share'] == '0' for r in days), [(r['date'], r['est_share']) for r in days])
        # saving an old food again does not add est, q or fortified
        await page.click('[data-tab=foods]'); await page.wait_for_selector('#ffilter')
        await page.click('[data-act=edit-food][data-id="u:old"]'); await page.wait_for_selector('#fok')
        await page.click('#fok'); await page.wait_for_timeout(300)
        f = await T("(() => { const f = window.__tapnaplo.S.foods['u:old']; return Object.keys(f).filter((k) => ['est', 'q', 'fortified', 'confidence'].includes(k)); })()")
        check('saving an old food in the editor leaves it without est, q and fortified', f == [], f)

        check('no page errors in the whole run', errs == [], errs[:5])
        await browser.close()
        for pth in made:
            try: pth.unlink()
            except OSError: pass
        print('\n' + ('ALL OK' if not problems else f'{len(problems)} FAILED: ' + '; '.join(problems)))
        sys.exit(1 if problems else 0)


if __name__ == '__main__':
    asyncio.run(main())
