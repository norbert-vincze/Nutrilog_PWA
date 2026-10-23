"""NOVA summary on the Nutrients tab and setting a group by hand. Run with the web server on port 8765 (see CLAUDE.md)."""
import asyncio, csv, io, json
from playwright.async_api import async_playwright
URL = 'http://127.0.0.1:8765/index.html'

CONTRAST_JS = """
() => {
  const parse = (c) => {
    let m = c.match(/rgba?\\(([^)]+)\\)/);
    if (m) { const p = m[1].split(/[ ,\\/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; }
    m = c.match(/color\\(srgb ([^)]+)\\)/);
    if (m) { const p = m[1].split(/[ \\/]+/).filter(Boolean).map(Number); return [p[0] * 255, p[1] * 255, p[2] * 255, p.length > 3 ? p[3] : 1]; }
    return [0, 0, 0, 0];
  };
  const lum = ([r, g, b]) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  const bgOf = (el) => {
    let layers = [];
    for (let e = el; e; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor); if (c[3] > 0) layers.push(c); if (c[3] >= 1) break; }
    let base = [255, 255, 255];
    if (!layers.length || layers[layers.length - 1][3] < 1) base = parse(getComputedStyle(document.body).backgroundColor).slice(0, 3);
    for (let i = layers.length - 1; i >= 0; i--) { const [r, g, b, a] = layers[i]; base = [r * a + base[0] * (1 - a), g * a + base[1] * (1 - a), b * a + base[2] * (1 - a)]; }
    return base;
  };
  const out = [];
  const root = document.querySelector('#view');
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const seen = new Set();
  while (walker.nextNode()) {
    const n = walker.currentNode; if (!n.textContent.trim()) continue;
    const el = n.parentElement; if (!el || seen.has(el)) continue; seen.add(el);
    const r = el.getBoundingClientRect(); if (!r.width || !r.height) continue;
    const cs = getComputedStyle(el); if (cs.visibility === 'hidden' || cs.display === 'none') continue;
    const fg = parse(cs.color), bg = bgOf(el);
    const a = fg[3]; const f = [fg[0] * a + bg[0] * (1 - a), fg[1] * a + bg[1] * (1 - a), fg[2] * a + bg[2] * (1 - a)];
    const L1 = lum(f), L2 = lum(bg), ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    const size = parseFloat(cs.fontSize), bold = parseInt(cs.fontWeight) >= 700;
    const need = (size >= 24 || (size >= 18.66 && bold)) ? 3 : 4.5;
    if (ratio < need) out.push(el.tagName.toLowerCase() + '.' + (el.className || '') + ' "' + n.textContent.trim().slice(0, 28) + '" ' + ratio.toFixed(2));
  }
  return out;
}
"""

SETUP = """
() => {
  const t = window.__tapnaplo, S = t.S;
  const rice = t.searchCiqual('rice', 1)[0];
  const mk = (id, name, kcal) => ({ id, src: 'user', name, brand: '', barcode: '', basis: { qty: 100, unit: 'g' }, n: kcal == null ? { protein: 20 } : { kcal }, nova: null, portions: [], note: '' });
  S.log = []; S.foods = {}; S.meta.nova = {};
  S.foods['o:111'] = t.offToFood({ code: '111', product_name: 'Test cola', nutriments: { 'energy-kcal_100g': 42 }, nova_group: 4 });
  S.foods['o:222'] = t.offToFood({ code: '222', product_name: 'Plain yogurt', nutriments: { 'energy-kcal_100g': 60 } });
  S.foods['u:t1'] = mk('u:t1', 'Home granola', 400);
  S.foods['u:t2'] = mk('u:t2', 'Mystery bar with a very long name that must wrap inside the narrow phone screen without any sideways scrolling', null);
  const add = (f, a, i) => S.log.push({ id: 'n' + i, d: S.day, m: 'm1', f, a, t: Date.now() + i, tm: '08:0' + i });
  add('usda:173424', 100, 1); add(rice.id, 200, 2); add('o:111', 330, 3); add('u:t1', 50, 4); add('u:t2', 40, 5); add('o:222', 150, 6); add('u:t1', 50, 7);
  t.render();
  return { rice: rice.id, riceName: rice.name };
}
"""

KCAL_JS = """
() => {
  const t = window.__tapnaplo, by = {};
  for (const e of t.S.log) { const f = t.getFood(e.f), k = t.vecOf(f).lo[0] * e.a / f.basis.qty; by[f.name] = (by[f.name] || 0) + (Number.isNaN(k) ? 0 : k); }
  return by;
}
"""

PCT_JS = """
() => [...document.querySelectorAll('#nova .nova-row .nova-val b')].map((b) => { const s = b.textContent.trim(); return s === '–' ? null : s === '<1%' ? 0.5 : parseInt(s); })
"""


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        problems = []

        def check(name, ok, info=''):
            print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(info)) if info != '' else ''))
            if not ok: problems.append(name)

        ctx = await b.new_context(viewport={'width': 390, 'height': 844}, locale='en-GB', has_touch=True, is_mobile=True, reduced_motion='reduce', accept_downloads=True)
        page = await ctx.new_page()
        dialogs, errs = [], []
        page.on('dialog', lambda d: (dialogs.append(d.message), asyncio.ensure_future(d.dismiss())))
        page.on('pageerror', lambda e: errs.append(str(e)))
        T = page.evaluate
        await page.goto(URL); await page.wait_for_selector('.hero')
        info = await T(SETUP)
        kc = await T(KCAL_JS)
        total = sum(kc.values())
        cola = kc['Test cola']

        # ---- the card
        await page.click('[data-tab=nutr]'); await page.wait_for_selector('#nova .nova-card')
        check('Nutrients tab has the NOVA card', 'Food processing (NOVA)' in await page.inner_text('#nova .card-t'))
        check('the card sits above the nutrient groups', await T("(()=>{const c=document.querySelector('#nova'),g=document.querySelector('section.group');return !!(c.compareDocumentPosition(g)&Node.DOCUMENT_POSITION_FOLLOWING)})()"))
        pc = await T(PCT_JS)
        check('five rows: NOVA 1, 2, 3, 4, unclassified', len(pc) == 5, pc)
        check('shares add up to exactly 100%', sum(x for x in pc if x is not None) == 100, pc)
        check('NOVA 4 share is the cola from Open Food Facts (group 4 came with the product)', abs(pc[3] - cola / total * 100) <= 1, (pc[3], cola / total * 100))
        check('everything else is unclassified', abs(pc[4] - (total - cola) / total * 100) <= 1 and pc[0] == 0 and pc[1] == 0 and pc[2] == 0, pc)
        cov = await page.inner_text('#nova .nova-card > p:last-of-type')
        check('coverage line: 1 of 6 foods classified, 1 entry without energy data', '1 of 6 foods classified' in cov and '1 entry has no energy data' in cov, cov)
        label = await page.get_attribute('#nova .bar', 'aria-label')
        check('the bar has a text alternative', label.startswith('Energy by NOVA group') and 'NOVA 4: Ultra-processed foods' in label, label)
        summ = await page.inner_text('#novafold > summary')
        check('the list says how many foods are unclassified', 'Set NOVA groups' in summ and '5 unclassified' in summ, summ)

        # ---- the list
        await page.tap('#novafold > summary'); await page.wait_for_timeout(100)
        heads = await T("[...document.querySelectorAll('#novafold .nova-h')].map(h=>h.textContent)")
        check('headings: Unclassified (5), Classified (1)', heads == ['Unclassified (5)', 'Classified (1)'], heads)
        names = await T("[...document.querySelectorAll('#novafold .nova-item-name')].map(n=>n.textContent)")
        check('a food logged twice is listed once', sum(1 for n in names if n == 'Home granola') == 1 and len(names) == 6, names)
        un_names = names[:5]
        exp = sorted([n for n in kc if n != 'Test cola'], key=lambda n: -kc[n])
        check('unclassified foods come with the biggest energy first', [n.lower() for n in un_names] == [n.lower() for n in exp], (un_names, exp))
        subs = await T("[...document.querySelectorAll('#novafold .nova-item')].map(i=>i.querySelector('.nova-item-sub').textContent)")
        check('a food without energy data says so', 'no energy data' in subs, subs)
        sizes = await T("[...document.querySelectorAll('#novafold .nbtn')].map(b=>{const r=b.getBoundingClientRect();return [r.width,r.height,r.right]})")
        check('every 1-4 button is at least 44 x 44 px and on the screen', len(sizes) == 24 and all(w >= 44 and h >= 44 and r <= 390 for w, h, r in sizes), sizes[:3])
        check('no sideways scrolling (long food name wraps)', await T('document.documentElement.scrollWidth <= window.innerWidth'))
        pressed = await T("[...document.querySelectorAll('#novafold .nbtn[aria-pressed=true]')].map(b=>b.dataset.id+':'+b.dataset.v)")
        check('only the cola shows a pressed button (4)', pressed == ['o:111:4'], pressed)
        lab = await page.get_attribute('#novafold .nbtn', 'aria-label')
        check('buttons are named for screen readers', lab.startswith('NOVA 1: Unprocessed'), lab)

        # ---- set a group, undo, clear
        egg = '#novafold [data-act=nova-set][data-id="usda:173424"]'
        await page.tap(egg + '[data-v="1"]'); await page.wait_for_timeout(120)
        meta = await T('__tapnaplo.S.meta.nova')
        check('USDA food: the group is kept in meta.nova', meta == {'usda:173424': 1}, meta)
        check('the list stays open and the food moved to Classified', await page.is_visible('#novafold .nova-item') and (await T("[...document.querySelectorAll('#novafold .nova-h')].map(h=>h.textContent)")) == ['Unclassified (4)', 'Classified (2)'])
        toast = await page.inner_text('#toast')
        check('toast says what happened and offers Undo', 'NOVA 1' in toast and 'Undo' in toast, toast)
        pc = await T(PCT_JS)
        check('NOVA 1 share = the egg', abs(pc[0] - kc['Egg, whole, cooked, hard-boiled'] / total * 100) <= 1 and sum(pc) == 100, pc)
        check('the chosen button is pressed', await page.get_attribute(egg + '[data-v="1"]', 'aria-pressed') == 'true')
        await page.tap('#toast button'); await page.wait_for_timeout(120)
        check('Undo takes the group back', await T('__tapnaplo.S.meta.nova') == {} and 'Unclassified (5)' in await page.inner_text('#novafold'))
        await page.tap(egg + '[data-v="1"]'); await page.wait_for_timeout(100)
        await page.tap(egg + '[data-v="1"]'); await page.wait_for_timeout(100)
        check('tapping the chosen number again clears it', await T('__tapnaplo.S.meta.nova') == {} and 'group cleared' in await page.inner_text('#toast'))
        await page.tap(egg + '[data-v="1"]'); await page.wait_for_timeout(100)
        await page.tap(f'#novafold [data-act=nova-set][data-id="{info["rice"]}"][data-v="1"]'); await page.wait_for_timeout(100)

        # ---- the Diary banner uses the same groups
        await page.click('[data-tab=log]'); await page.wait_for_selector('.hero')
        ban = await page.inner_text('.banner')
        check('Diary banner shows the ultra-processed share', 'Ultra-processed (NOVA 4)' in ban and 'NOVA 1–3:' in ban, ban)
        share4 = float(ban.split('NOVA 4): ')[1].split('%')[0].replace(',', '.'))
        check('Diary banner share of NOVA 4 is right', abs(share4 - cola / total * 100) < 0.2, (share4, cola / total * 100))
        await page.click('[data-tab=nutr]'); await page.wait_for_selector('#nova .nova-card')
        check('the list is still open after leaving and coming back', await page.get_attribute('#novafold', 'open') is not None)

        # ---- foods you create and Open Food Facts foods keep the group in the food itself
        await page.tap('#novafold [data-act=nova-set][data-id="u:t1"][data-v="2"]'); await page.wait_for_timeout(100)
        await page.tap('#novafold [data-act=nova-set][data-id="o:222"][data-v="3"]'); await page.wait_for_timeout(100)
        await page.tap('#novafold [data-act=nova-set][data-id="o:111"][data-v="3"]'); await page.wait_for_timeout(100)
        st = await T("({g:__tapnaplo.S.foods['u:t1'].nova, y:__tapnaplo.S.foods['o:222'].nova, c:__tapnaplo.S.foods['o:111'].nova, meta:__tapnaplo.S.meta.nova})")
        check('own food and OFF foods: food.nova is set, meta.nova only holds generic foods', st['g'] == 2 and st['y'] == 3 and st['c'] == 3 and set(st['meta']) == {'usda:173424', info['rice']}, st)
        check('a group that came from Open Food Facts can be changed by hand (cola 4 -> 3)', st['c'] == 3)
        await page.tap('#novafold [data-act=nova-set][data-id="u:t2"][data-v="1"]'); await page.wait_for_timeout(100)
        pc = await T(PCT_JS)
        check('all foods classified: unclassified 0%, shares add up to 100', pc[4] == 0 and sum(pc) == 100, pc)
        check('the empty state says every food has a group', 'Every food of the day has a group' in await page.inner_text('#novafold') and 'Unclassified (' not in await page.inner_text('#novafold'))
        check('the summary line no longer counts unclassified foods', (await page.inner_text('#novafold > summary')).strip() == 'Set NOVA groups')
        cov = await page.inner_text('#nova .nova-card > p:last-of-type')
        check('coverage line: 6 of 6 foods classified', '6 of 6 foods classified' in cov, cov)
        check('a food without energy data does not change the shares (granola, rice, egg, cola, yogurt only)', abs(pc[0] + pc[1] + pc[2] + pc[3] - 100) == 0)

        # ---- the same group shows in Edit food, and Edit food changes the card
        await page.click('[data-tab=foods]'); await page.wait_for_selector('#flist')
        await page.tap('#flist .item:has-text("Home granola")'); await page.wait_for_selector('#fnova')
        check('Edit food shows the group set in the Nutrients tab', await page.input_value('#fnova') == '2')
        await page.select_option('#fnova', '4'); await page.tap('#fok'); await page.wait_for_timeout(200)
        await page.click('[data-tab=nutr]'); await page.wait_for_selector('#nova .nova-card')
        check('and the card follows what Edit food saved (granola now 4)', await page.get_attribute('#novafold [data-id="u:t1"][data-v="4"]', 'aria-pressed') == 'true')

        # ---- the choice is saved, works on other days, and goes into the files
        await T('__tapnaplo.save()'); await page.wait_for_timeout(500)
        await page.reload(); await page.wait_for_selector('#nova .nova-card'); await page.wait_for_timeout(200)
        check('after a reload the groups are still there', await T('__tapnaplo.S.meta.nova["usda:173424"]') == 1 and await page.get_attribute('#novafold [data-id="usda:173424"][data-v="1"]', 'aria-pressed') == 'true')
        await page.click('[data-act=day][data-n="-1"]'); await page.wait_for_timeout(100)
        await T("(()=>{const S=__tapnaplo.S;S.log.push({id:'prev1',d:S.day,m:'m1',f:'usda:173424',a:50,t:Date.now(),tm:'09:00'});__tapnaplo.render()})()")
        pc = await T(PCT_JS)
        check('the same egg is already NOVA 1 on another day', pc[0] == 100 and pc[4] == 0, pc)
        await page.click('[data-act=today]'); await page.wait_for_timeout(100)
        await page.click('[data-tab=data]'); await page.wait_for_selector('[data-act=export-entries]')
        async with page.expect_download() as d:
            await page.click('[data-act=export-entries]')
        dl = await d.value; await dl.save_as('entries_nova.csv')
        rows = list(csv.DictReader(io.StringIO(open('entries_nova.csv', encoding='utf-8-sig').read())))
        by = {r['food']: r['nova'] for r in rows}
        check('CSV nova column holds the chosen groups (also for USDA food), cola is 3', by.get('Egg, whole, cooked, hard-boiled') == '1' and by.get('Test cola') == '3' and by.get('Home granola') == '4' and by.get('Plain yogurt') == '3', by)
        async with page.expect_download() as d2:
            await page.click('[data-act=export-json]')
        dj = await d2.value; await dj.save_as('backup_nova.json')
        bk = json.load(open('backup_nova.json', encoding='utf-8'))
        check('backup file keeps meta.nova', bk['meta']['nova'].get('usda:173424') == 1 and bk['app'] == 'tapnaplo', bk['meta'])
        old = {'app': 'tapnaplo', 'version': 1, 'log': [], 'foods': {}, 'meta': {'last': {}, 'portions': {}, 'backup': None}}
        json.dump(old, open('old_backup.json', 'w'))
        await page.set_input_files('#importfile', 'old_backup.json'); await page.wait_for_selector('[data-ok]'); await page.click('[data-ok]'); await page.wait_for_timeout(300)
        check('an older backup without NOVA data restores with an empty NOVA map', await T('JSON.stringify(__tapnaplo.S.meta.nova)') == '{}')
        await page.click('[data-tab=nutr]')
        check('Nutrients tab with no entries still works after the restore', 'Nothing logged for this day' in await page.inner_text('#view'))

        # ---- tiny shares show as <1%
        await T("""(()=>{const t=__tapnaplo,S=t.S;
          S.foods['u:p']={id:'u:p',src:'user',name:'Pinch',brand:'',barcode:'',basis:{qty:100,unit:'g'},n:{kcal:400},nova:2,portions:[],note:''};
          S.foods['u:b']={id:'u:b',src:'user',name:'Big',brand:'',barcode:'',basis:{qty:100,unit:'g'},n:{kcal:100},nova:1,portions:[],note:''};
          S.log=[{id:'a',d:S.day,m:'m1',f:'u:p',a:0.1,t:1,tm:'08:00'},{id:'b',d:S.day,m:'m1',f:'u:b',a:500,t:2,tm:'08:01'}];t.render()})()""")
        pc = await T(PCT_JS)
        txt = await page.inner_text('#nova .nova-rows')
        check('a share below 1% is shown as <1% and the rest still adds up to 100', '<1%' in txt and pc[0] == 100 and pc[1] == 0.5, (pc, txt.replace('\n', ' | ')))
        check('sharePct with nothing to split gives zeros', await T('JSON.stringify(__tapnaplo.sharePct([0,0,0,0,0],0))') == '[0,0,0,0,0]')
        check('sharePct 1/1/1 gives 34/33/33', await T('JSON.stringify(__tapnaplo.sharePct([1,1,1,0,0],3))') == '[34,33,33,0,0]')

        # ---- nothing classified and no energy data at all
        await T("""(()=>{const t=__tapnaplo,S=t.S;S.log=[{id:'c',d:S.day,m:'m1',f:'u:t2',a:40,t:1,tm:'08:00'}];S.foods['u:t2']={id:'u:t2',src:'user',name:'Mystery bar',brand:'',barcode:'',basis:{qty:100,unit:'g'},n:{protein:20},nova:null,portions:[],note:''};t.render()})()""")
        txt = await page.inner_text('#nova .nova-rows')
        check('with no energy data the shares show a dash, not 0%', txt.count('–') == 5, txt.replace('\n', ' | '))
        label = await page.get_attribute('#nova .bar', 'aria-label')
        check('and the bar says so in words', label == 'No energy data to split by NOVA group', label)

        # ---- contrast in light and dark, with everything open
        await T(SETUP)
        await page.click('[data-tab=log]'); await page.click('[data-tab=nutr]'); await page.wait_for_selector('#nova .nova-card')
        await T("document.querySelectorAll('#view details.fold').forEach(d=>d.open=true)"); await page.wait_for_timeout(100)
        light = await T(CONTRAST_JS)
        check('text contrast >= 4.5:1 on the Nutrients tab in light mode', light == [], light)
        await T("document.documentElement.setAttribute('data-theme','dark')"); await page.wait_for_timeout(100)
        dark = await T(CONTRAST_JS)
        check('text contrast >= 4.5:1 on the Nutrients tab in dark mode', dark == [], dark)
        await T("document.documentElement.setAttribute('data-theme','light')")
        defs = await page.inner_text('#view details.fold:last-of-type')
        check('the definitions explain all four groups', all(f'{n} · ' in defs for n in '1234') and 'not by how healthy' in defs, defs[:120])

        check('no native dialogs', dialogs == [], dialogs)
        check('no page errors', errs == [], errs)
        await b.close()
        print('\nPROBLEMS:', problems if problems else 'none')
        raise SystemExit(1 if problems else 0)

asyncio.run(main())
