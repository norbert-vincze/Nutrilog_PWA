# Nutrilog – project notes for Claude

Calorie, macro and micronutrient diary as a static PWA. No build step, no server, no framework.
Owner: Norbert, a Hungarian service designer who is a beginner at coding. Reply in Hungarian, address him as Norbert,
explain every manual step (GitHub clicks, phone steps) in small numbered steps with the exact English button names.

## Hosting
- Repo `norbert-vincze/Nutrilog_PWA`, branch `main`, served by GitHub Pages from the root folder (public repo).
- Live: https://norbert-vincze.github.io/Nutrilog_PWA/ . A push is live after 1–10 minutes (Actions → "pages build and deployment").
- Norbert tests on an iPhone 14 (iOS 26, Chrome). That is WebKit: no `BarcodeDetector`, ZXing is used for scanning.

## Files
- `index.html`, `style.css`, `app.js` (all logic, ~1200 lines), `sw.js` (offline), `manifest.webmanifest`, icons.
- `ciqual.json` (CIQUAL 2020, 3186 foods, 64 nutrients, CC BY 4.0). Built from the CIQUAL Excel table (.xls, Zenodo 4770202) with `python3 tools/ciqual_to_json.py <table.xls> ciqual.json` (needs pandas and xlrd). The source table is not in the repo.
- `usda.json` (USDA FoodData Central: Foundation Foods April 2026, 436 foods + SR Legacy April 2018, 7793 foods; U.S. public domain; 3.5 MB, about 0.9 MB gzipped). Same 64 nutrients in the same order as `ciqual.json` (`keys` is checked at load). Built from the two CSV downloads at fdc.nal.usda.gov/download-datasets with `python3 -I tools/usda_to_json.py <foundation_csv_dir> <sr_legacy_csv_dir> ciqual.json usda.json` (needs pandas). The CSV folders are not in the repo.
- `zxing.min.js` (vendored ZXing-js, Apache 2.0, licence in `ZXING-LICENSE.txt`).
- `README.md` is the Hungarian beginner guide for installing and using the app. Keep it in step with the app.
- `tests/` Playwright scripts (see below).

## Decisions already made with Norbert – do not undo
- UI is English, sentence case. Food input and search understand Hungarian and English (`DICT`, `PHRASES`, `singular()` in app.js).
- Names: tabs Diary / Nutrients / My foods / Data; actions **Log food**, **Scan**, **Create food**; one term per nutrient everywhere (Carbohydrate, not Carbs).
- Look: Revolut-inspired fintech style (big number, circular actions, grey cards, bottom sheets, light/dark). Do not copy the brand.
- Meals are `Meal 1` … `Meal N`, count set by `MEAL_COUNT` (6). No breakfast/lunch names. A new entry defaults to the meal of the latest entry on the shown day (Meal 1 on an empty day).
- Every diary entry has a time of day: `tm` ("HH:MM", local, 24 h), editable in the Amount/Edit entry sheet (`#tm`, `<input type="time">`, next to Meal). New entries start at the current time. Entries without `tm` (made before version 6) show the time they were added (`t`, never changed). The time never moves an entry to another day (`d` stays the shown day). Within a meal entries are sorted by time (`byTime`); `defaultMeal()` still uses the creation order `t`. The entries CSV has a `time` column after `date`. Do not call `focus()` on the time field (iOS).
- Theme is a manual setting: Data tab → **Appearance** → Auto / Light / Dark (`localStorage` key `nutrilog.theme`, not part of the backup). CSS has only `:root` (light) and `:root[data-theme="dark"]`; there is no `prefers-color-scheme` block. `data-theme` is always set to `light` or `dark`: first by the inline script in `index.html` (before first paint, no flash), then by `applyTheme()` in app.js, which also follows live phone changes while Auto is on. Keep the rule in both places identical. The `theme-color` meta is a single tag updated by script.
- USDA is a second source of generic foods next to CIQUAL (Norbert asked for it after seeing that kaloriabazis.hu uses USDA). It is bundled, not a live API: the FDC API needs a key in every request and deactivates keys found in public repos. Search sheet order: My foods, CIQUAL, USDA (10 rows, "Show more USDA results" adds 30), Open Food Facts. USDA foods: id `usda:<fdc_id>`, `src:'usda'`, tag USDA, 100 g basis, no Edit food, household measures from FDC as buttons but the amount still starts at 100 g (`startPortion`). The search uses the same DICT (Hungarian) but not PHRASES, and matches plurals ("Apples"). Id prefixes: `c:` CIQUAL, `usda:` USDA, `o:` Open Food Facts, `u:` foods you create (never reuse `u:` for anything else). Missing stays missing: only salt (from sodium), crude protein (nitrogen x 6.25), vitamin D from IU and energy from kJ/Atwater are derived, see the docstring of the converter. Fatty acids use exact isomers only, vitamin K2 is MK-4 only. If `usda.json` cannot load, the app starts without it and the Diary says how many entries are hidden.
- NOVA (food-processing group 1–4) has a summary card on the Nutrients tab, above the nutrient groups (`novaHtml`, container `#nova`), plus a fold "Set NOVA groups" where the group is set by hand. The share is of **energy** (kcal, lower value) and counts only entries with energy data; they are reported in the coverage line (`noEnergy`). Unknown stays unknown: **nothing is guessed** (no mapping from CIQUAL/USDA food groups), CIQUAL and USDA foods start "Unclassified". `novaOf(food)` is the one place that gives the effective group (Diary banner, card, CSV `nova` column all use it); `setNova(food, v)` writes it: foods in `S.foods` (`u:` and `o:`, `src` user/off) keep it in `food.nova` (the same field as the NOVA select in Edit food, and the group Open Food Facts delivers; a hand choice overwrites it), CIQUAL and USDA foods keep it in `S.meta.nova[food id]` (backup JSON includes `meta.nova`; `metaDefaults()` is the single source of the meta shape, used at start, in `init()` and in `importJson`, so old backups without `nova` still load). Tapping the chosen number again clears it, every change has an Undo toast. The list re-draws only `#nova` (`refreshNova`) and its open state is kept in `novaOpen`, because replacing the whole view would close the fold after each tap. Shares are whole percents that add up to 100 (`sharePct`, largest remainder), below 1% shows `<1%`. NOVA group names and examples are the `NOVA` constant (flour is group 1, not 2).
- There is **no Recipe feature**. It was removed on purpose. Do not add it back.
- Missing data is not zero: values are lower/upper vectors with NaN; totals show `≥`, the `cnt/n` pill, `~` for energy estimated from macros, "Lower estimate" chip. Empty field = no data, 0 = real zero.
- Data stays in the browser (IndexedDB `tapnaplo`/`kv`, localStorage fallback). Backup JSON keeps the marker `app:'tapnaplo'`. CSV exports (entries, daily totals) are for analysis with Claude; columns ending `__max` are upper bounds of "<x" values, `__n` counts items with data.
- Barcode lookup is worldwide (Open Food Facts v2 by code). HTTP 404 means "not in the database", not an error. 12-digit and 13-digit variants are tried. A saved food with the same barcode wins and works offline. The Hungary filter applies only to name search and is opt-in.
- Liquids are treated as grams (1 ml ≈ 1 g).

## iPhone gotchas (learned the hard way)
- Never call `focus()` outside the tap that started the action. On iOS it leaves the field "focused" with no keyboard. On touch screens the amount field is not auto-focused (`TOUCH` constant). The amount field always shows its real value (never an empty field with a hidden default); the button says what it will log ("Add 100 g").
- No `window.confirm`/`prompt`/`alert`: they freeze the page in some browsers. Use `askConfirm`/`askText` (in-app sheets) or the Undo toast pattern (diary entries, foods).
- Errors go next to the field (`fieldError`), never only at the bottom of a long sheet. Touch targets are at least 44 px. Text contrast at least 4.5:1 in light and dark (`tests/test_audit_fixes.py` measures it).
- The Create food form shows **Essentials** first; everything else is under **More values**.
- The toast (`#toast`) is `position: fixed; left: 50%`, which squeezes its width to half the screen unless it has `width: max-content`. Its Undo button is a 44 px target.
- The active tab is remembered (`localStorage` key `nutrilog.tab`).
- GitHub Pages sends files with a 10-minute browser cache. `sw.js` therefore fetches with `cache: 'no-cache'`.
- `sw.js` keeps `ciqual.json` and `usda.json` in their own cache `DATA` (`nutrilog-data-1`), cache-first, so a new app version does not download the 4.9 MB again. Raise the number in `DATA` only when one of the two files changes (the "Reload app files" button clears everything anyway).
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
python3 test_audit_fixes.py    # the 18 points of the UX/accessibility audit (contrast, 44 px targets, wording, errors, dialogs)
python3 test_entry_time.py     # entry time: default now, edit, sort, empty-time error, old entries, reload, CSV column
python3 test_theme.py          # Auto/Light/Dark: no flash, saved, survives reload, Auto follows the phone live
python3 test_usda.py           # USDA: data values, search (HU/EN, plurals), household measures, CSV, offline cache, app without usda.json
python3 test_nova.py           # NOVA card: shares, hand-set groups (generic / own / OFF foods), Undo, clear, reload, other day, CSV, backup, <1%, contrast
```
Not testable here: a real iPhone, the live Open Food Facts API, the native BarcodeDetector. Ask Norbert for a screenshot.
Commit messages end with the attribution lines required by the session.
