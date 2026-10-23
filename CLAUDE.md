# Nutrilog – project notes for Claude

Calorie, macro and micronutrient diary as a static PWA. No build step, no server, no framework.
Owner: Norbert, a Hungarian service designer who is a beginner at coding. Reply in Hungarian, address him as Norbert,
explain every manual step (GitHub clicks, phone steps) in small numbered steps with the exact English button names.

## Hosting
- Repo `norbert-vincze/Nutrilog_PWA`, branch `main`, served by GitHub Pages from the root folder (public repo).
- Live: https://norbert-vincze.github.io/Nutrilog_PWA/ . A push is live after 1–10 minutes (Actions → "pages build and deployment").
- Norbert tests on an iPhone 14 (iOS 26, Chrome). That is WebKit: no `BarcodeDetector`, ZXing is used for scanning.

## Files
- `index.html`, `style.css`, `app.js` (all logic, ~1000 lines), `sw.js` (offline), `manifest.webmanifest`, icons.
- `ciqual.json` (CIQUAL 2020, 3186 foods, 64 nutrients, CC BY 4.0). Built from the CIQUAL Excel table (.xls, Zenodo 4770202) with `python3 tools/ciqual_to_json.py <table.xls> ciqual.json` (needs pandas and xlrd). The source table is not in the repo.
- `zxing.min.js` (vendored ZXing-js, Apache 2.0, licence in `ZXING-LICENSE.txt`).
- `README.md` is the Hungarian beginner guide for installing and using the app. Keep it in step with the app.
- `tests/` Playwright scripts (see below).

## Decisions already made with Norbert – do not undo
- UI is English. Food input and search understand Hungarian and English (`DICT`, `PHRASES`, `singular()` in app.js).
- Look: Revolut-inspired fintech style (big number, circular actions, grey cards, bottom sheets, light/dark). Do not copy the brand.
- Meals are `Meal 1` … `Meal N`, count set by `MEAL_COUNT` (6). No breakfast/lunch names.
- There is **no Recipe feature**. It was removed on purpose. Do not add it back.
- Missing data is not zero: values are lower/upper vectors with NaN; totals show `≥`, the `cnt/n` pill, `~` for energy estimated from macros, "Lower estimate" chip. Empty field = no data, 0 = real zero.
- Data stays in the browser (IndexedDB `tapnaplo`/`kv`, localStorage fallback). Backup JSON keeps the marker `app:'tapnaplo'`. CSV exports (entries, daily totals) are for analysis with Claude; columns ending `__max` are upper bounds of "<x" values, `__n` counts items with data.
- Barcode lookup is worldwide (Open Food Facts v2 by code). HTTP 404 means "not in the database", not an error. 12-digit and 13-digit variants are tried. A saved food with the same barcode wins and works offline. The Hungary filter applies only to name search and is opt-in.
- Liquids are treated as grams (1 ml ≈ 1 g).

## iPhone gotchas (learned the hard way)
- Never call `focus()` outside the tap that started the action. On iOS it leaves the field "focused" with no keyboard. On touch screens the amount field is not auto-focused; its first focus empties it and shows the old value as placeholder (`TOUCH` constant).
- GitHub Pages sends files with a 10-minute browser cache. `sw.js` therefore fetches with `cache: 'no-cache'`.
- With every change: raise `VERSION` in `app.js` **and** `CACHE` in `sw.js` (same number). The Data tab shows the version and has a "Reload app files" button (clears service worker and caches, keeps the diary).

## Testing
Chromium + Playwright for Python, OFF requests are mocked (the live API is not reachable from the sandbox).
```
python3 -m http.server 8765 --bind 127.0.0.1      # in the repo root, keep running
cd tests && python3 make_barcode_video.py          # creates bar.y4m (fake camera)
python3 test_full_flow.py      # search HU/EN, add, custom food, meals, tabs, persistence
python3 test_offline_import.py # service worker, offline reload, backup import
python3 test_scanner.py        # camera scan with fake video (ZXing path)
python3 test_barcode_keyboard.py  # not-found barcode, 12/13 digits, amount field, Hungary filter, reload button
```
Not testable here: a real iPhone, the live Open Food Facts API, the native BarcodeDetector. Ask Norbert for a screenshot.
Commit messages end with the attribution lines required by the session.
