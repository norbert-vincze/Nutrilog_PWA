"""Sync with a private GitHub repository, tested against a fake GitHub (api.github.com is not reachable from here and must not be).
Two or three "devices" are separate browser contexts (separate IndexedDB) that talk to the same fake repository.
Run with the web server on port 8765 (see CLAUDE.md)."""
import asyncio, base64, hashlib, json, re, time
from urllib.parse import urlparse, unquote
from playwright.async_api import async_playwright
URL = 'http://127.0.0.1:8765/index.html'
GOOD = 'github_pat_GOODTOKEN123'
CORS = {'access-control-allow-origin': '*', 'access-control-allow-headers': 'authorization,content-type,accept,x-github-api-version', 'access-control-allow-methods': 'GET,PUT,OPTIONS'}


class FakeGitHub:
    """A tiny GitHub: repo info, file list, read file, write file with the sha rule (409 when the sha is old)."""
    def __init__(self):
        self.files = {}              # path -> text
        self.token = GOOD
        self.calls = []              # (method, path)
        self.before_put = None       # hook(path) called once before a write: another device "writes first"
        self.net_fail = 0            # the next N requests fail like a lost connection
        self.rate = 0                # the next N requests are answered like GitHub's rate limit
        self.puts = 0

    @staticmethod
    def sha(text):
        b = text.encode()
        return hashlib.sha1(b'blob %d\0' % len(b) + b).hexdigest()

    async def handle(self, route):
        req = route.request
        u = urlparse(req.url); path = unquote(u.path)
        if req.method == 'OPTIONS':
            await route.fulfill(status=204, headers=CORS); return
        if self.net_fail > 0:
            self.net_fail -= 1; await route.abort('connectionfailed'); return
        self.calls.append((req.method, path))
        if self.rate > 0:
            self.rate -= 1; await route.fulfill(status=403, headers=dict(CORS, **{'content-type': 'application/json', 'x-ratelimit-remaining': '0'}), body=json.dumps({'message': 'API rate limit exceeded'})); return
        h = dict(CORS, **{'content-type': 'application/json'})
        def js(status, obj): return route.fulfill(status=status, headers=h, body=json.dumps(obj))
        if req.headers.get('authorization') != 'Bearer ' + self.token:
            await js(401, {'message': 'Bad credentials'}); return
        m = re.match(r'^/repos/([^/]+)/([^/]+)(/.*)?$', path)
        if not m: await js(404, {'message': 'Not Found'}); return
        owner, repo, rest = m.group(1), m.group(2), m.group(3) or ''
        if (owner, repo) == ('me', 'public-repo') and rest == '':
            await js(200, {'private': False, 'default_branch': 'main'}); return
        if (owner, repo) != ('me', 'nutrilog-data'): await js(404, {'message': 'Not Found'}); return
        if rest == '': await js(200, {'private': True, 'default_branch': 'main'}); return
        if rest.startswith('/git/trees/'):
            if not self.files: await js(409, {'message': 'Git Repository is empty.'}); return
            await js(200, {'tree': [{'path': p, 'type': 'blob', 'sha': self.sha(t)} for p, t in sorted(self.files.items())], 'truncated': False}); return
        if rest.startswith('/contents/'):
            p = rest[len('/contents/'):]
            if req.method == 'GET':
                if p not in self.files: await js(404, {'message': 'Not Found'}); return
                await route.fulfill(status=200, headers=dict(CORS, **{'content-type': 'text/plain; charset=utf-8'}), body=self.files[p]); return
            if req.method == 'PUT':
                body = json.loads(req.post_data)
                if self.before_put:
                    hook, self.before_put = self.before_put, None
                    hook(p)
                cur = self.sha(self.files[p]) if p in self.files else None
                if cur and body.get('sha') != cur: await js(409, {'message': f'{p} does not match {body.get("sha")}'}); return
                if not cur and body.get('sha'): await js(422, {'message': 'sha given for a new file'}); return
                text = base64.b64decode(body['content']).decode()
                self.files[p] = text; self.puts += 1
                await js(200 if cur else 201, {'content': {'path': p, 'sha': self.sha(text)}}); return
        await js(404, {'message': 'Not Found'})

    def recs(self):
        """all records in the repository: key -> {u, x}"""
        out = {}
        for p, t in self.files.items():
            if p.endswith('.json'):
                j = json.loads(t); out.update(j['recs'])
        return out


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

ADD = """
([food, d, a]) => {
  const t = window.__tapnaplo, S = t.S;
  const e = { id: crypto.randomUUID(), d, m: 'm1', f: food, a, t: Date.now(), tm: '12:00' };
  S.log.push(e); t.save(); return e.id;
}
"""


async def main():
    async with async_playwright() as p:
        problems = []

        def check(name, ok, info=''):
            print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(info)) if info != '' else ''))
            if not ok: problems.append(name)

        browser = await p.chromium.launch()
        gh = FakeGitHub()
        errs = []

        async def device(name, w=390, h=844):
            ctx = await browser.new_context(viewport={'width': w, 'height': h}, locale='en-GB', service_workers='block', accept_downloads=True)
            await ctx.route('https://api.github.com/**', gh.handle)
            await ctx.route('**/*openfoodfacts.org/**', lambda r: r.fulfill(status=200, headers={'access-control-allow-origin': '*', 'content-type': 'application/json'}, body='{"products":[]}'))
            await ctx.add_init_script("window.__off = 0; { const n = Date.now.bind(Date); Date.now = () => n() + (window.__off || 0); }")
            page = await ctx.new_page()
            page.dname = name
            page.on('pageerror', lambda e: errs.append(f'{name} PE {e}'))
            page.on('console', lambda m: errs.append(f'{name} C {m.text}') if m.type == 'error' and 'Failed to load resource' not in m.text else None)
            await page.goto(URL); await page.wait_for_selector('.hero, .card')
            return ctx, page

        async def sync(page):
            for _ in range(2):
                await page.wait_for_function('!window.__tapnaplo.SY.busy')
                await page.evaluate("window.__tapnaplo.syncRun('manual')")
            await page.wait_for_function('!window.__tapnaplo.SY.busy')

        async def state(page, js):
            return await page.evaluate(js)

        async def open_data(page):
            await page.click('[data-tab=data]'); await page.wait_for_selector('[data-act=export-json]')

        async def connect(page, repo='me/nutrilog-data', token=GOOD):
            await open_data(page)
            await page.click('[data-act=sync-setup]')
            await page.fill('#sy-repo', repo); await page.fill('#sy-token', token)
            await page.click('[data-ok]')

        ids = lambda page: page.evaluate('window.__tapnaplo.S.log.map(e => e.id).sort()')
        amount = lambda page, i: page.evaluate('(i) => { const e = window.__tapnaplo.S.log.find(x => x.id === i); return e ? e.a : null }', i)
        pending = lambda page: page.evaluate('Object.values(window.__tapnaplo.SY.rec).filter(r => r.p).length')

        # ================= device A (phone) =================
        ctxA, A = await device('A')
        today = await A.evaluate("(() => { const d = new Date(); const p = (n) => String(n).padStart(2, '0'); return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`; })()")
        rice = await A.evaluate("window.__tapnaplo.searchCiqual('rice', 1)[0].id")
        egg = await A.evaluate("window.__tapnaplo.searchCiqual('egg', 1)[0].id")
        check('no sync card state before setup: "Set up sync" is offered', await A.locator('[data-tab=data]').count() == 1)
        await open_data(A)
        check('the Sync card offers "Set up sync" while not connected', await A.locator('[data-act=sync-setup]').count() == 1 and await A.locator('#sync-now').count() == 0)

        # data made before sync was connected (like version 11 data): entries in two months, an own food, a portion, a NOVA choice
        await A.evaluate("""([rice, egg]) => {
          const t = window.__tapnaplo, S = t.S;
          S.foods['u:food1'] = { id: 'u:food1', src: 'user', name: 'Own porridge', brand: '', barcode: '', basis: { qty: 100, unit: 'g' }, n: { kcal: 90, protein: 3 }, nova: null, portions: [], note: '', created: Date.now() - 5e6 };
          S.meta.portions[rice] = [{ label: '1 bowl', grams: 180 }];
          S.meta.nova[egg] = 1;
          t.save();
        }""", [rice, egg])
        e1 = await A.evaluate(ADD, [rice, '2026-09-30', 150])
        e2 = await A.evaluate(ADD, [egg, '2026-10-24', 120])
        e3 = await A.evaluate(ADD, [egg, today, 60])
        await A.wait_for_timeout(400)
        check('records are noted, none is sent yet (no connection)', await pending(A) >= 6 and gh.calls == [], (await pending(A), gh.calls))

        # ---- connect dialog
        await A.click('[data-act=sync-setup]')
        await A.click('[data-ok]')
        check('empty repository field: error next to the field', 'name/repository' in await A.inner_text('.sheet-b'))
        await A.fill('#sy-repo', 'nonsense'); await A.click('[data-ok]')
        check('a wrong repository name format is refused', 'name/repository' in await A.inner_text('.sheet-b') and gh.calls == [])
        await A.fill('#sy-repo', 'https://github.com/me/nutrilog-data.git'); await A.click('[data-ok]')
        check('empty token field: error next to the token field', 'Paste the access token' in await A.inner_text('.sheet-b'))
        await A.fill('#sy-token', 'wrong-token'); await A.click('[data-ok]')
        await A.wait_for_function("document.querySelector('.sheet-b').innerText.includes('does not accept the token')")
        check('a wrong token: "does not accept the token", and the sheet stays open', True)
        check('the Connect button is usable again after an error', await A.locator('[data-ok]').is_enabled() and (await A.inner_text('[data-ok]')) == 'Connect')
        await A.fill('#sy-token', GOOD); await A.fill('#sy-repo', 'me/public-repo'); await A.click('[data-ok]')
        await A.wait_for_function("document.querySelector('.sheet-b').innerText.includes('public')")
        check('a public repository is refused (the diary would be readable by everyone)', True)
        await A.fill('#sy-repo', 'me/missing'); await A.click('[data-ok]')
        await A.wait_for_function("document.querySelector('.sheet-b').innerText.includes('cannot find the repository')")
        check('an unknown repository: "cannot find the repository"', True)
        check('nothing was written while the connection failed', gh.puts == 0 and await A.evaluate('window.__tapnaplo.SY.cfg') is None)
        await A.fill('#sy-repo', 'me/nutrilog-data'); await A.click('[data-ok]')
        await A.wait_for_selector('#sync-now')
        await sync(A)
        check('connected: the card names the private repository', 'me/nutrilog-data' in await A.inner_text('.card:has(#sync-now)'))
        check('the status line says when the last sync was', 'Last sync' in await A.inner_text('#sync-status'), await A.inner_text('#sync-status'))

        # ---- what was written
        check('the empty repository received entries, foods and meta files', {'entries/2026-09.json', 'entries/2026-10.json', 'meta.json'} <= set(gh.files) and any(f.startswith('foods/') for f in gh.files), sorted(gh.files))
        rec = gh.recs()
        check('every diary entry is in the repository', all(('e:' + i) in rec and rec[('e:' + i)]['x'] for i in (e1, e2, e3)))
        check('the own food, the portion and the NOVA choice are in the repository', 'f:u:food1' in rec and ('p:' + rice) in rec and rec[('n:' + egg)]['x'] == 1, sorted(rec)[:12])
        check('files are sync files with an app marker', all(json.loads(t)['app'] == 'tapnaplo-sync' for t in gh.files.values()))
        check('the token is in none of the files', all('github_pat' not in t for t in gh.files.values()))
        check('nothing is waiting after the sync', await pending(A) == 0)
        check('the old entry of September is in the September file, the other two in October', e1 in gh.files['entries/2026-09.json'] and e2 in gh.files['entries/2026-10.json'] and e1 not in gh.files['entries/2026-10.json'])
        first_puts = gh.puts

        # ---- a sync with nothing to do only asks for the file list
        gh.calls.clear()
        await sync(A)
        await A.wait_for_timeout(300)
        check('a sync with nothing new costs one request per pass and writes nothing', gh.puts == first_puts and all(m == 'GET' and '/git/trees/' in pth for m, pth in gh.calls) and len(gh.calls) <= 2, gh.calls)

        # ---- backup file does not contain the token or the sync state
        async with A.expect_download() as dl:
            await A.click('[data-act=export-json]')
        d = await dl.value
        bk = open(await d.path(), encoding='utf-8').read()
        j = json.loads(bk)
        check('the backup file has no token and no sync state', 'github_pat' not in bk and 'tapnaplo-sync' not in bk and set(j) == {'app', 'version', 'exported', 'log', 'foods', 'meta'}, sorted(j))
        check('the backup file still holds the diary', len(j['log']) == 3 and 'u:food1' in j['foods'])

        # ================= device B (computer) =================
        ctxB, B = await device('B', 1100, 800)
        await connect(B)
        await B.wait_for_selector('#sync-now')
        await sync(B)
        check('device B receives all entries after connecting', await ids(B) == sorted([e1, e2, e3]), await ids(B))
        check('device B has the own food, the portion and the NOVA choice', await B.evaluate("(r) => { const S = window.__tapnaplo.S; return !!S.foods['u:food1'] && S.meta.portions[r[0]][0].grams === 180 && S.meta.nova[r[1]] === 1 }", [rice, egg]))
        await B.click('[data-tab=log]'); await B.wait_for_selector('.hero')
        check('today\'s entry is visible in the Diary of device B', await B.locator(f'[data-act=edit-entry][data-id="{e3}"]').count() == 1)
        check('B holds no pending change after the first pull', await pending(B) == 0, await pending(B))
        check('B sent nothing in its first sync (all was already in the repository)', gh.puts == first_puts, (gh.puts, first_puts))

        # ---- both add something, then both sync
        x = await A.evaluate(ADD, [egg, today, 50])
        y = await B.evaluate(ADD, [rice, today, 70])
        await sync(A); await sync(B); await sync(A)
        check('two devices adding at the same time: both entries end up on both', await ids(A) == await ids(B) == sorted([e1, e2, e3, x, y]), (await ids(A), await ids(B)))

        # ---- an edit through the real edit sheet on B reaches A
        await B.click('[data-tab=log]')
        await B.click(f'[data-act=edit-entry][data-id="{e3}"]')
        await B.fill('#amt', '75'); await B.click('#ok')
        await B.wait_for_timeout(300)
        check('editing an amount on B (real sheet) changes the entry on B', await amount(B, e3) == 75)
        await sync(B); await sync(A)
        check('the edit reaches A', await amount(A, e3) == 75, await amount(A, e3))

        # ---- the Diary of A is redrawn when another device changed something
        await A.click('[data-tab=log]'); await A.wait_for_selector('.hero')
        z = await B.evaluate(ADD, [egg, today, 33])
        await sync(B); await sync(A)
        await A.wait_for_selector(f'[data-act=edit-entry][data-id="{z}"]', timeout=3000)
        check('the Diary on A shows the entry that B added without a reload', True)

        # ---- delete and undo
        await A.evaluate("(i) => { const S = window.__tapnaplo.S; const k = S.log.findIndex(e => e.id === i); window.__del = { ...S.log[k] }; S.log.splice(k, 1); window.__tapnaplo.save(); }", z)
        await A.wait_for_timeout(300)
        await sync(A)
        check('a deleted entry stays in the repository as a marker (x null)', gh.recs()['e:' + z]['x'] is None)
        await sync(B)
        check('the deletion reaches B', z not in await ids(B))
        await A.evaluate("() => { const S = window.__tapnaplo.S; S.log.push(window.__del); window.__tapnaplo.save(); }")
        await A.wait_for_timeout(300)
        await sync(A); await sync(B)
        check('Undo of a deletion (the entry comes back) wins over the marker and reaches B', z in await ids(B) and gh.recs()['e:' + z]['x'] is not None)

        # ---- clock 10 minutes behind on B: its later edit must still win (each change is newer than the version it started from)
        await B.evaluate('window.__off = -600000')
        await A.evaluate("(i) => { window.__tapnaplo.S.log.find(e => e.id === i).a = 100; window.__tapnaplo.save(); }", e2)
        await A.wait_for_timeout(300)
        await sync(A); await sync(B)
        check('B (clock behind) first receives A\'s edit', await amount(B, e2) == 100)
        await B.evaluate("(i) => { window.__tapnaplo.S.log.find(e => e.id === i).a = 222; window.__tapnaplo.save(); }", e2)
        await B.wait_for_timeout(300)
        await sync(B); await sync(A)
        check('an edit made after receiving a newer version wins even when the clock is behind', await amount(A, e2) == 222 and gh.recs()['e:' + e2]['x']['a'] == 222, (await amount(A, e2), gh.recs()['e:' + e2]['x']['a']))
        await B.evaluate('window.__off = 0')

        # ---- the same entry edited on both without syncing in between: the later edit wins
        await A.evaluate("(i) => { window.__tapnaplo.S.log.find(e => e.id === i).a = 10; window.__tapnaplo.save(); }", e1)
        await A.wait_for_timeout(300)
        await B.evaluate("(i) => { window.__tapnaplo.S.log.find(e => e.id === i).a = 20; window.__tapnaplo.save(); }", e1)
        await B.wait_for_timeout(300)
        await sync(A); await sync(B); await sync(A)
        check('same entry edited on two devices: the later edit (20) wins on both', await amount(A, e1) == 20 and await amount(B, e1) == 20, (await amount(A, e1), await amount(B, e1)))

        # ---- own food edited on B, portion and NOVA changed on A
        await B.evaluate("() => { const t = window.__tapnaplo; t.S.foods['u:food1'].name = 'Own porridge 2'; t.save(); }")
        await A.evaluate("([r, e]) => { const t = window.__tapnaplo; t.S.meta.nova[e] = 2; t.S.meta.portions[r].push({ label: '1 cup', grams: 90 }); t.save(); }", [rice, egg])
        await B.wait_for_timeout(300); await A.wait_for_timeout(300)
        await sync(B); await sync(A); await sync(B)
        check('a food edited on B arrives on A', await A.evaluate("window.__tapnaplo.S.foods['u:food1'].name") == 'Own porridge 2')
        check('a changed NOVA group and a new portion arrive on B', await B.evaluate("([r, e]) => { const S = window.__tapnaplo.S; return S.meta.nova[e] === 2 && S.meta.portions[r].length === 2 }", [rice, egg]))
        await A.evaluate("(e) => { const t = window.__tapnaplo; delete t.S.meta.nova[e]; t.save(); }", egg)
        await A.wait_for_timeout(300)
        await sync(A); await sync(B)
        check('clearing a NOVA group on A clears it on B', await B.evaluate("(e) => window.__tapnaplo.S.meta.nova[e] === undefined", egg))

        # ---- no connection: changes wait, then go
        await ctxA.set_offline(True)
        w = await A.evaluate(ADD, [rice, today, 44])
        await A.wait_for_timeout(300)
        await A.evaluate("window.__tapnaplo.syncRun('manual')")
        await open_data(A)
        st = await A.inner_text('#sync-status')
        check('offline: the status says so and counts the waiting change', 'Offline' in st and 'waiting' in st, st)
        check('offline: no error is shown, nothing was sent', await A.evaluate('window.__tapnaplo.SY.err') == '' and w not in str(gh.files))
        await ctxA.set_offline(False)
        await sync(A); await sync(B)
        check('back online: the waiting entry is sent and reaches B', w in await ids(B) and await pending(A) == 0)
        # a failing connection while the browser believes it is online
        v = await A.evaluate(ADD, [rice, today, 45])
        await A.wait_for_timeout(300)
        gh.net_fail = 1
        await A.evaluate("window.__tapnaplo.syncRun('manual')")
        await A.wait_for_function('!window.__tapnaplo.SY.busy')
        check('a lost connection is "offline", not an error, and the entry stays pending', await A.evaluate('window.__tapnaplo.SY.offline') and await A.evaluate('window.__tapnaplo.SY.err') == '' and await pending(A) >= 1)
        await sync(A)
        check('the next sync sends it', await pending(A) == 0 and ('e:' + v) in gh.recs())

        # ---- GitHub's rate limit is not a token problem: say so, and try again later
        r1 = await A.evaluate(ADD, [rice, today, 46])
        await A.wait_for_timeout(300)
        gh.rate = 1
        await A.evaluate("window.__tapnaplo.syncRun('manual')")
        await A.wait_for_function('!window.__tapnaplo.SY.busy')
        check('rate limit: a message about limited requests, and automatic syncs are not switched off', 'limiting requests' in await A.evaluate('window.__tapnaplo.SY.err') and not await A.evaluate('window.__tapnaplo.SY.stop'), await A.evaluate('window.__tapnaplo.SY.err'))
        await sync(A)
        check('after the limit the entry is sent', ('e:' + r1) in gh.recs() and await A.evaluate('window.__tapnaplo.SY.err') == '')

        # ---- another device writes between our look and our write (HTTP 409): look again and merge
        stranger = {'id': 'zz-stranger', 'd': today[:7] + '-02', 'm': 'm2', 'f': rice, 'a': 99, 't': 1, 'tm': '08:00'}
        month = f'entries/{today[:7]}.json'
        def other_device_writes(path):
            j = json.loads(gh.files[month]); j['recs']['e:zz-stranger'] = {'u': int(time.time() * 1000) + 5, 'x': stranger}
            gh.files[month] = json.dumps(j)
        u = await A.evaluate(ADD, [egg, today, 21])
        await A.wait_for_timeout(300)
        gh.before_put = other_device_writes
        await sync(A)
        check('a write that meets a newer file (409) is repeated after merging', 'zz-stranger' in await ids(A) and ('e:' + u) in gh.recs() and gh.recs()['e:zz-stranger']['x']['a'] == 99)
        await sync(B)
        check('and nothing was lost on B either', 'zz-stranger' in await ids(B) and u in await ids(B))

        # ---- automatic sync a few seconds after a change (no manual button)
        q = await B.evaluate(ADD, [rice, today, 12])
        t0 = time.time()
        while time.time() - t0 < 12 and ('e:' + q) not in gh.recs(): await asyncio.sleep(0.25)
        check('a change is sent automatically within about 10 seconds', ('e:' + q) in gh.recs(), round(time.time() - t0, 1))

        # ---- A comes back to the front: fetches by itself
        await A.evaluate("window.__tapnaplo.SY.ranAt = 0")
        await A.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
        await A.wait_for_function("(i) => window.__tapnaplo.S.log.some(e => e.id === i)", arg=q, timeout=5000)
        check('coming back to the front fetches new entries by itself', True)

        # ---- a record never synced before connecting must not beat a newer remote version (device C: old copy of e3, remote has 75)
        ctxC, C = await device('C')
        await C.evaluate("([e3, rice, today]) => { const t = window.__tapnaplo; t.S.log.push({ id: e3, d: today, m: 'm1', f: rice, a: 999, t: Date.now() - 86400000, tm: '09:00' }); t.S.log.push({ id: 'only-on-c', d: today, m: 'm3', f: rice, a: 5, t: Date.now() - 3600000, tm: '10:00' }); t.save(); }", [e3, egg, today])
        await C.wait_for_timeout(300)
        await connect(C); await C.wait_for_selector('#sync-now'); await sync(C)
        check('connecting with an old copy: the newer version from the repository wins (75, not 999)', await amount(C, e3) == 75, await amount(C, e3))
        check('an entry that exists only on C is kept and sent', 'only-on-c' in await ids(C) and 'e:only-on-c' in gh.recs())
        await sync(A)
        check('and it reaches A', 'only-on-c' in await ids(A))

        # ---- restore from a file replaces the data everywhere
        bk_small = json.dumps({'app': 'tapnaplo', 'version': 1, 'log': [{'id': 'restored-1', 'd': today, 'm': 'm1', 'f': rice, 'a': 80, 't': 1, 'tm': '07:00'}], 'foods': {}, 'meta': {'last': {}, 'portions': {}, 'nova': {}, 'backup': None}})
        open('/tmp/claude-0/-home-claude/1a7e5c78-719b-5c60-8617-fed0ab4bbcee/scratchpad/restore_small.json', 'w').write(bk_small)
        await open_data(A)
        await A.set_input_files('#importfile', '/tmp/claude-0/-home-claude/1a7e5c78-719b-5c60-8617-fed0ab4bbcee/scratchpad/restore_small.json')
        await A.wait_for_selector('.sheet-b [data-ok]')
        check('the restore question says that other devices will get the data too', 'other devices will get the restored data' in await A.inner_text('.sheet-b'))
        await A.click('.sheet-b [data-ok]')
        await A.wait_for_timeout(400)
        await sync(A); await sync(B)
        check('restore on A: B ends with exactly the restored entry', await ids(B) == ['restored-1'] and await ids(A) == ['restored-1'], await ids(B))
        check('the removed entries are markers in the repository', all(r['x'] is None for k, r in gh.recs().items() if k.startswith('e:') and k != 'e:restored-1'))
        await sync(C)
        check('and C follows as well', await ids(C) == ['restored-1'])

        # ---- the token stops working: clear message, no hammering, and a way back
        gh.token = 'rotated'
        await A.evaluate(ADD, [egg, today, 8])
        await A.wait_for_timeout(300)
        await A.evaluate("window.__tapnaplo.syncRun('manual')")
        await A.wait_for_function('!window.__tapnaplo.SY.busy')
        await open_data(A)
        check('a token that GitHub no longer accepts: a message in the Sync card', 'does not accept the token' in await A.inner_text('#sync-status'), await A.inner_text('#sync-status'))
        n = len(gh.calls)
        await A.evaluate("window.__tapnaplo.syncRun('change')")
        await A.evaluate("window.__tapnaplo.syncRun('timer')")
        check('automatic syncs stop asking GitHub after that (only the "Sync now" button tries again)', len(gh.calls) == n)
        await A.click('[data-act=sync-off]')
        await A.click('.sheet-b [data-ok]')
        await A.wait_for_selector('[data-act=sync-setup]')
        check('Disconnect forgets the token and the data stays', await A.evaluate('window.__tapnaplo.SY.cfg') is None and len(await ids(A)) == 2, await ids(A))
        gh.token = GOOD
        await connect(A); await A.wait_for_selector('#sync-now'); await sync(A)
        check('connecting again sends the change made while disconnected', await pending(A) == 0 and len(gh.recs()) > 0 and any(r['x'] and r['x'].get('a') == 8 for k, r in gh.recs().items() if k.startswith('e:')))

        # ---- a foreign file in the repository is not overwritten
        gh.files['entries/2026-11.json'] = '{"hello": "world"}'
        await A.evaluate("window.__tapnaplo.syncRun('manual')")
        await A.wait_for_function('!window.__tapnaplo.SY.busy')
        check('a file that is not a Nutrilog sync file stops the sync with a clear message', 'not a Nutrilog sync file' in await A.evaluate('window.__tapnaplo.SY.err'), await A.evaluate('window.__tapnaplo.SY.err'))
        del gh.files['entries/2026-11.json']
        await sync(A)

        # ---- speed with a big diary
        t_ms = await A.evaluate("""() => {
          const t = window.__tapnaplo, S = t.S, f = t.searchCiqual('rice', 1)[0].id;
          for (let i = 0; i < 6000; i++) S.log.push({ id: 'big' + i, d: '2025-0' + (1 + i % 9) + '-1' + (i % 9), m: 'm1', f, a: 50 + i % 90, t: i, tm: '12:00' });
          let t0 = performance.now(); t.syncStamp(); const first = performance.now() - t0;
          S.log[5].a = 7; t0 = performance.now(); t.syncStamp(); return [first, performance.now() - t0];
        }""")
        check('noting changes in a 6000-entry diary is fast (first, then one change)', t_ms[0] < 1500 and t_ms[1] < 400, [round(x) for x in t_ms])

        # ---- the Sync card looks right: contrast, touch targets, both themes
        for theme in ('light', 'dark'):
            await A.evaluate("(th) => { localStorage.setItem('nutrilog.theme', th); }", theme)
            await A.reload(); await A.wait_for_selector('.hero, .card')
            await open_data(A)
            low = await A.evaluate(CONTRAST_JS)
            check(f'{theme}: text contrast of the Data tab (with the Sync card) is at least 4.5:1', low == [], low[:4])
            small = await A.evaluate("() => [...document.querySelectorAll('#view .card:has(#sync-now) button, #view .card:has([data-act=sync-setup]) button')].filter(b => b.getBoundingClientRect().height < 44).map(b => b.textContent)")
            check(f'{theme}: Sync buttons are at least 44 px high', small == [], small)
            await A.screenshot(path=f'sync_data_{theme}.png', full_page=True)
        await A.evaluate("() => { localStorage.removeItem('nutrilog.theme'); }")
        await A.click('[data-act=sync-off]'); await A.click('.sheet-b [data-ok]')
        await A.click('[data-act=sync-setup]')
        small = await A.evaluate("() => [...document.querySelectorAll('.sheet-b input, .sheet-b button')].filter(b => b.getBoundingClientRect().height < 44).map(b => b.id || b.textContent)")
        check('the setup sheet: fields and buttons are at least 44 px high', small == [], small)
        check('the token field hides what is typed', await A.get_attribute('#sy-token', 'type') == 'password')
        await A.screenshot(path='sync_setup_sheet.png')

        check('no page errors or console errors on any device', errs == [], errs[:5])
        await browser.close()
        print('\nPROBLEMS:', problems if problems else 'none')
        raise SystemExit(1 if problems else 0)

asyncio.run(main())
