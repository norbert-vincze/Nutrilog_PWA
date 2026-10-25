/* Nutrilog: calorie, macro and micronutrient diary. No build step, one script.
   Data: CIQUAL 2020 (Anses, CC BY 4.0) in ciqual.json; USDA FoodData Central (Foundation Foods, SR Legacy; U.S. public domain) in usda.json; Open Food Facts (ODbL) looked up live.
   Principle: missing data is not zero. Totals are lower estimates and always show their coverage. */
'use strict';
(() => {

/* ================= helpers ================= */
const LOC = 'en-GB';
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const norm = (s) => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const cap = (s) => (s ? s[0].toUpperCase() + s.slice(1) : s);
const uid = () => (crypto.randomUUID ? crypto.randomUUID() : 'i' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8));
const pad = (n) => String(n).padStart(2, '0');
const ymd = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const parseYmd = (s) => { const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d); };
const addDays = (s, n) => { const d = parseYmd(s); d.setDate(d.getDate() + n); return ymd(d); };
const hm = (d) => `${pad(d.getHours())}:${pad(d.getMinutes())}`;                          // 14:05
const validHm = (s) => typeof s === 'string' && /^([01]\d|2[0-3]):[0-5]\d$/.test(s);
/* The time field is plain text in 24-hour form (HH:MM). The phone's own time picker shows AM/PM when the phone is set to 12 hours, and a web page cannot change that. */
function shapeHm(v) {   // while typing: only digits and one colon; the colon is added after two digits
  v = String(v).replace(/[^\d:]/g, '');
  const i = v.indexOf(':');
  if (i >= 0) return v.slice(0, Math.min(i, 2)) + ':' + v.slice(i + 1).replace(/:/g, '').slice(0, 2);
  return v.length > 2 ? v.slice(0, 2) + ':' + v.slice(2, 4) : v;
}
function normHm(v) {   // when leaving the field or saving: 8:30 and 830 become 08:30
  const t = String(v).trim(), m = /^(\d{1,2}):(\d{2})$/.exec(t) || /^(\d{1,2})(\d{2})$/.exec(t);
  return m ? m[1].padStart(2, '0') + ':' + m[2] : t;
}
const prec = (v) => Number(Number(v).toPrecision(6));
const num = (s) => parseFloat(String(s).replace(',', '.'));        // accepts 1.5 and 1,5
const TOUCH = !!(window.matchMedia && window.matchMedia('(pointer: coarse)').matches);   // phone or tablet
const VERSION = '17 · 25 Oct 2026';   // shown in the Data tab; raise it (and CACHE in sw.js) with every change
const plural = (n, w) => `${n} ${w}${n === 1 ? '' : 's'}`;

/* Theme: the person picks Auto (follow the phone), Light or Dark in the Data tab. Saved in localStorage ('nutrilog.theme').
   The same rule runs in index.html before the first paint. */
const THEMES = [['auto', 'Auto'], ['light', 'Light'], ['dark', 'Dark']];
const mqDark = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
let themeMem = 'auto';   // used only when localStorage is blocked (private mode)
function themePref() {
  try { const p = localStorage.getItem('nutrilog.theme'); if (p === 'auto' || p === 'light' || p === 'dark') return p; } catch { /* private mode */ }
  return themeMem;
}
function applyTheme() {
  const p = themePref(), dark = p === 'dark' || (p === 'auto' && !!(mqDark && mqDark.matches));
  document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
  const m = document.querySelector('meta[name=theme-color]');
  if (m) m.setAttribute('content', dark ? '#000000' : '#ffffff');
}
function setTheme(p) {
  themeMem = p;
  try { localStorage.setItem('nutrilog.theme', p); } catch { /* private mode: the choice lasts until the page is closed */ }
  applyTheme();
}
if (mqDark) { if (mqDark.addEventListener) mqDark.addEventListener('change', applyTheme); else if (mqDark.addListener) mqDark.addListener(applyTheme); }

function fmt(v) {
  if (!Number.isFinite(v)) return '–';
  const a = Math.abs(v);
  const dec = a >= 100 ? 0 : a >= 10 ? 1 : a >= 0.1 ? 2 : 3;
  return v.toLocaleString(LOC, { minimumFractionDigits: 0, maximumFractionDigits: dec });
}
const fmtLong = (s) => parseYmd(s).toLocaleDateString(LOC, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
function dayTitle(s) {
  const t = ymd(new Date());
  if (s === t) return 'Today';
  if (s === addDays(t, -1)) return 'Yesterday';
  if (s === addDays(t, 1)) return 'Tomorrow';
  return parseYmd(s).toLocaleDateString(LOC, { weekday: 'long' });
}
const hash = (s) => { let h = 0; for (const ch of norm(s)) h = (h * 31 + ch.charCodeAt(0)) >>> 0; return h; };
const avatar = (name) => `<span class="av av${hash(name) % 6}" aria-hidden="true">${esc((String(name).match(/[A-Za-z0-9]/) || ['•'])[0].toUpperCase())}</span>`;

const SV = (d) => `<svg viewBox="0 0 24 24" aria-hidden="true">${d}</svg>`;
const IC = {
  diary: SV('<path d="M6 4h11a2 2 0 0 1 2 2v14H8a2 2 0 0 1-2-2zM6 18a2 2 0 0 1 2-2h11M10 8h5"/>'),
  nutr: SV('<circle cx="12" cy="12" r="8.5"/><path d="M12 3.5V12h8.5"/>'),
  foods: SV('<path d="M3 11h18a9 9 0 0 1-18 0zM8 7c0-2 2-2 2-4M13 7c0-2 2-2 2-4"/>'),
  data: SV('<path d="M12 4v11m0 0-4-4m4 4 4-4M5 20h14"/>'),
  plus: SV('<path d="M12 5v14M5 12h14"/>'),
  scan: SV('<path d="M4 8V6a2 2 0 0 1 2-2h2M16 4h2a2 2 0 0 1 2 2v2M20 16v2a2 2 0 0 1-2 2h-2M8 20H6a2 2 0 0 1-2-2v-2M8 9v6M12 9v6M16 9v6"/>'),
  tag: SV('<path d="M3.5 12.5V5A1.5 1.5 0 0 1 5 3.5h7.5l8 8-9 9z"/><circle cx="8" cy="8" r="1.2"/>'),
  left: SV('<path d="m14.5 6-6 6 6 6"/>'),
  right: SV('<path d="m9.5 6 6 6-6 6"/>'),
  cal: SV('<rect x="4" y="5" width="16" height="15" rx="3"/><path d="M8 3v4M16 3v4M4 10h16"/>'),
  close: SV('<path d="m6 6 12 12M18 6 6 18"/>'),
};

/* ================= storage ================= */
const Store = (() => {
  let db = null, mode = 'idb';
  const mem = {};
  const open = () => new Promise((resolve) => {
    try {
      const req = indexedDB.open('tapnaplo', 1);
      req.onupgradeneeded = () => req.result.createObjectStore('kv');
      req.onsuccess = () => { db = req.result; resolve(); };
      req.onerror = () => { mode = 'ls'; resolve(); };
      req.onblocked = () => { mode = 'ls'; resolve(); };
    } catch { mode = 'ls'; resolve(); }
  });
  const get = (k) => new Promise((res) => {
    if (mode === 'idb') {
      try {
        const r = db.transaction('kv').objectStore('kv').get(k);
        r.onsuccess = () => res(r.result ?? null);
        r.onerror = () => res(null);
      } catch { res(null); }
    } else {
      try { const s = localStorage.getItem('tn:' + k); res(s ? JSON.parse(s) : (mem[k] ?? null)); } catch { res(mem[k] ?? null); }
    }
  });
  const set = (k, v) => new Promise((res) => {
    if (mode === 'idb') {
      try {
        const tx = db.transaction('kv', 'readwrite');
        tx.objectStore('kv').put(v, k);
        tx.oncomplete = () => res(true);
        tx.onerror = () => res(false);
        tx.onabort = () => res(false);
      } catch { res(false); }
    } else {
      try { localStorage.setItem('tn:' + k, JSON.stringify(v)); res(true); } catch { mem[k] = v; res(false); }
    }
  });
  return { open, get, set, get mode() { return mode; } };
})();

/* ================= state ================= */
const MEAL_COUNT = 6;           // how many "Meal N" slots the diary shows
const MEALS = Array.from({ length: MEAL_COUNT }, (_, i) => ({ id: 'm' + (i + 1), name: 'Meal ' + (i + 1) }));
/* meta: last = last meal/amount per food, portions = your own portion sizes, nova = NOVA group you chose for CIQUAL and USDA foods (food id -> 1..4) */
const metaDefaults = () => ({ last: {}, portions: {}, nova: {}, backup: null });
const S = {
  log: [],                      // {id, d, m, f, a, t}
  foods: {},                    // custom and Open Food Facts foods
  meta: metaDefaults(),
  day: ymd(new Date()),
  tab: 'log',
  filter: '',
};
let CAT = null, CIQ = [], CIQ_BY_ID = new Map();   // CIQ_BY_ID holds the CIQUAL ('c:') and the USDA ('usda:') foods; 'u:' is already taken by foods you create
let USDA = [], USDA_ERR = '';
let DMBIO = [], DM_ERR = '';   // dmBio products sold by dm Hungary (dmbio.json); ids 'dm:<dm article id>'
let KEYS = [], UNITS = [], IDX = {}, NUT_N = 0;
let saveTimer = null;

/* ================= nutrient catalogue ================= */
const GROUPS = [
  ['mac', 'Energy & macronutrients', true],
  ['fa', 'Fatty acids & cholesterol', true],
  ['min', 'Minerals', true],
  ['vit', 'Vitamins', true],
  ['fad', 'Fatty acids (detail)', false],
  ['oth', 'Other components', false],
];
const L = {
  kcal: ['Energy', 'mac'], protein: ['Protein', 'mac'], carbohydrate: ['Carbohydrate', 'mac'], fat: ['Fat', 'mac'],
  fibres: ['Fibre', 'mac'], sugars: ['Sugars', 'mac'], salt: ['Salt', 'mac'],
  fa_saturated: ['Saturated fat', 'fa'], fa_mono: ['Monounsaturated fat', 'fa'], fa_poly: ['Polyunsaturated fat', 'fa'],
  fa_18_2_9c_12c_n_6: ['Linoleic acid (18:2 n-6)', 'fa'], fa_18_3_c9_c12_c15_n_3: ['Alpha-linolenic acid (18:3 n-3)', 'fa'],
  fa_20_4_5c_8c_11c_14c_n_6: ['Arachidonic acid (20:4 n-6)', 'fa'], fa_20_5_5c_8c_11c_14c_17c_n_3_epa: ['EPA (20:5 n-3)', 'fa'],
  fa_22_6_4c_7c_10c_13c_16c_19c_n_3_dha: ['DHA (22:6 n-3)', 'fa'], cholesterol: ['Cholesterol', 'fa'],
  calcium: ['Calcium', 'min'], iron: ['Iron', 'min'], magnesium: ['Magnesium', 'min'], potassium: ['Potassium', 'min'], sodium: ['Sodium', 'min'],
  zinc: ['Zinc', 'min'], phosphorus: ['Phosphorus', 'min'], iodine: ['Iodine', 'min'], selenium: ['Selenium', 'min'], copper: ['Copper', 'min'],
  manganese: ['Manganese', 'min'], chloride: ['Chloride', 'min'],
  retinol: ['Vitamin A (retinol)', 'vit'], beta_carotene: ['Beta-carotene', 'vit'], vitamin_d: ['Vitamin D', 'vit'], vitamin_e: ['Vitamin E', 'vit'],
  vitamin_k1: ['Vitamin K1', 'vit'], vitamin_k2: ['Vitamin K2', 'vit'], vitamin_c: ['Vitamin C', 'vit'],
  vitamin_b1_or_thiamin: ['Vitamin B1 (thiamin)', 'vit'], vitamin_b2_or_riboflavin: ['Vitamin B2 (riboflavin)', 'vit'],
  vitamin_b3_or_niacin: ['Vitamin B3 (niacin)', 'vit'], vitamin_b5_or_pantothenic_acid: ['Vitamin B5 (pantothenic acid)', 'vit'],
  vitamin_b6: ['Vitamin B6', 'vit'], vitamin_b9_or_folate: ['Vitamin B9 (folate)', 'vit'], vitamin_b12: ['Vitamin B12', 'vit'],
  water: ['Water', 'mac'], protein_crude_n_x_6_25: ['Crude protein (N × 6.25)', 'oth'], starch: ['Starch', 'oth'],
  fructose: ['Fructose', 'oth'], galactose: ['Galactose', 'oth'], glucose: ['Glucose', 'oth'], lactose: ['Lactose', 'oth'],
  maltose: ['Maltose', 'oth'], sucrose: ['Sucrose', 'oth'], polyols: ['Polyols', 'oth'], ash: ['Ash', 'oth'],
  alcohol: ['Alcohol', 'oth'], organic_acids: ['Organic acids', 'oth'],
};
const labelOf = (i) => (L[KEYS[i]] ? L[KEYS[i]][0] : CAT.nutrients[i].label);
const groupOf = (i) => {
  const k = KEYS[i];
  if (L[k]) return L[k][1];
  return k.startsWith('fa_') ? 'fad' : 'oth';
};
let TRACKED = [];          // indexes of the tracked nutrients (macros, fatty acids, minerals, vitamins)

/* ================= bilingual search: Hungarian and English words -> CIQUAL names ================= */
/* Keys are accent-free word stems. A typed word that starts with a key uses that key's English terms.
   Words that are not in the list are searched as typed, so plain English works without any entry. */
const DICT = {
  /* Hungarian */
  tojas: ['egg'], tej: ['milk'], tejfol: ['cream, 15-20% fat', 'cream, fat content unknown', 'sour cream', 'cream'], tejszin: ['cream, fat content unknown', 'cream'], sajt: ['cheese'],
  turo: ['quark', 'fresh cheese', 'uncured soft cheese', 'fromage blanc', 'cottage'],
  joghurt: ['yogurt', 'yoghurt'], kefir: ['kefir'], vaj: ['butter'], margarin: ['margarine'],
  kenyer: ['bread'], zsemle: ['bread', 'roll'], kifli: ['bread', 'roll'], rizs: ['rice'], teszta: ['pasta'], makaroni: ['pasta'],
  kuszkusz: ['couscous'], zab: ['oat'], zabpehely: ['oat'], muzli: ['muesli'], burgonya: ['potato'], krumpli: ['potato'],
  edesburgonya: ['sweet potato'], sargarepa: ['carrot'], cekla: ['beetroot'], brokkoli: ['broccoli'], karfiol: ['cauliflower'],
  spenot: ['spinach'], salata: ['lettuce', 'salad'], uborka: ['cucumber'], paradicsom: ['tomato'], paprika: ['pepper'],
  hagyma: ['onion'], fokhagyma: ['garlic'], cukkini: ['courgette', 'zucchini'], padlizsan: ['eggplant', 'aubergine'],
  gomba: ['mushroom'], kaposzta: ['cabbage'], kelkaposzta: ['kale', 'cabbage'], avokado: ['avocado'],
  alma: ['apple'], korte: ['pear'], banan: ['banana'], narancs: ['orange'], citrom: ['lemon'], eper: ['strawberr'],
  malna: ['raspberr'], afonya: ['blueberr'], szolo: ['grape'], szilva: ['plum'], barack: ['apricot', 'peach'],
  cseresznye: ['cherry'], dinnye: ['melon', 'watermelon'], kivi: ['kiwi'],
  mogyoro: ['hazelnut'], foldimogyoro: ['peanut'], dio: ['walnut'], mandula: ['almond'], kesudio: ['cashew'], pisztacia: ['pistachio'],
  napraforgomag: ['sunflower'], tokmag: ['pumpkin'], lenmag: ['flax', 'linseed'], chia: ['chia'], szezam: ['sesame'],
  olaj: ['oil'], olivaolaj: ['olive oil', 'oil, olive'], kokuszolaj: ['coconut'], cukor: ['sugar'], mez: ['honey'],
  csokolade: ['chocolate'], kave: ['coffee'], tea: ['tea'], viz: ['water'], bor: ['wine'], sor: ['beer'],
  csirke: ['chicken'], pulyka: ['turkey'], marha: ['beef'], sertes: ['pork'], borju: ['veal'], barany: ['lamb'], kacsa: ['duck'],
  sonka: ['ham'], szalami: ['salami'], kolbasz: ['sausage'], szalonna: ['bacon', 'lard'],
  hal: ['fish'], lazac: ['salmon'], tonhal: ['tuna'], szardinia: ['sardine'], makrela: ['mackerel'], pisztrang: ['trout'],
  ponty: ['carp'], garnela: ['shrimp', 'prawn'], tofu: ['tofu'], lencse: ['lentil'], bab: ['bean'], csicseriborso: ['hummus', 'legume', 'chickpea'],
  borso: ['pea'], kukorica: ['corn', 'maize'], szoja: ['soy'], mandulaital: ['almond drink', 'almond-based drink', 'almond milk'], mandulatej: ['almond drink', 'almond-based drink', 'almond milk'],
  zabital: ['oat-based drink', 'oat milk'], zabtej: ['oat-based drink', 'oat milk'], rizsital: ['rice-based drink', 'rice milk'], szojaital: ['soy drink', 'soy milk'], szojatej: ['soy drink', 'soy milk'], kokusztej: ['coconut milk'], kokusz: ['coconut'],
  kecske: ['goat'], juh: ['ewe', 'sheep'], liszt: ['flour'], eleszto: ['yeast'], so: ['salt'], ecet: ['vinegar'],
  majonez: ['mayonnaise'], ketchup: ['ketchup'], mustar: ['mustard'], pizza: ['pizza'], palacsinta: ['crepe', 'pancake'],
  keksz: ['biscuit'], suti: ['cake', 'pastry'], fagylalt: ['ice cream'], chips: ['crisps', 'chips'], popcorn: ['pop-corn'],
  fott: ['boiled', 'cooked'], sult: ['roasted', 'fried', 'grilled', 'baked'], sutott: ['baked', 'roasted'], nyers: ['raw'],
  szaritott: ['dried'], konzerv: ['canned'], fustolt: ['smoked'], rantott: ['fried', 'breaded'], piritott: ['toasted'],
  parolt: ['braised', 'stewed'], mirelit: ['frozen'], friss: ['fresh', 'raw'], teljes: ['whole', 'wholemeal'],
  zsirszegeny: ['low fat', 'reduced fat', 'skimmed'], pehely: ['flakes'], mell: ['breast'], comb: ['leg'],
  fino: ['fine'], feher: ['white'], barna: ['brown'], fekete: ['black'], zold: ['green'], piros: ['red'],
  majk: ['liver'], szarny: ['wing'], file: ['fillet'], leves: ['soup'], szosz: ['sauce'], befott: ['canned', 'compote'],
  lekvar: ['jam'], dzsem: ['jam'], granola: ['granola', 'muesli'], protein: ['protein'], turmix: ['smoothie'],
  gyumolcsle: ['fruit juice', 'juice'], gyumolcs: ['fruit'], zoldseg: ['vegetable'], tengeri: ['sea'], tonhalkonzerv: ['tuna, canned'],
  tejpor: ['milk powder', 'milk, powder'], sovany: ['pretzel', 'cracker'],
  /* English spelling variants and names that differ between UK/US/French usage */
  yogurt: ['yogurt', 'yoghurt'], yoghurt: ['yogurt', 'yoghurt'], zucchini: ['courgette', 'zucchini'], courgette: ['courgette', 'zucchini'],
  eggplant: ['eggplant', 'aubergine'], aubergine: ['eggplant', 'aubergine'], shrimp: ['shrimp', 'prawn'], prawn: ['shrimp', 'prawn'],
  cookie: ['biscuit', 'cookie'], biscuit: ['biscuit', 'cookie'], chickpea: ['hummus', 'legume', 'chickpea'], garbanzo: ['hummus', 'legume', 'garbanzo'],
  wholegrain: ['wholemeal', 'whole wheat', 'wholegrain'], wholewheat: ['wholemeal', 'whole wheat'], wholemeal: ['wholemeal', 'whole wheat'],
  mince: ['minced', 'ground'], candy: ['candy', 'confectionery', 'sweet'], sweets: ['candy', 'confectionery', 'sweet'],
  /* English words that would otherwise be caught by a Hungarian stem */
  sorbet: ['sorbet'], sorrel: ['sorrel'], halibut: ['halibut'], halloumi: ['halloumi'], baby: ['baby'],
};
const DICT_KEYS = Object.keys(DICT).sort((a, b) => b.length - a.length);
function keyAt(tok) {
  for (const k of DICT_KEYS) if (k.length <= 2 ? tok === k : tok.startsWith(k)) return k;
  return null;
}
const singular = (t) => (t.length > 3 && t.endsWith('ies') ? t.slice(0, -3) + 'y' : t.length > 3 && t.endsWith('oes') ? t.slice(0, -2)
  : t.length > 3 && t.endsWith('s') && !t.endsWith('ss') ? t.slice(0, -1) : t);
/* One typed word becomes 1-2 search groups: a known stem, plus the rest of a compound word (kecskesajt = kecske + sajt). */
function altsFor(tok) {
  const k = keyAt(tok);
  if (!k) { const s = singular(tok); return [s === tok ? [tok] : [tok, s]]; }
  const out = [[...new Set(DICT[k].map(norm))]];
  const rest = tok.slice(k.length);
  if (k.length >= 3 && rest.length >= 3) {
    const k2 = keyAt(rest);
    if (k2 && k2.length >= 3) out.push([...new Set(DICT[k2].map(norm))]);
  }
  return out;
}
const tokensOf = (q) => norm(q).split(/[^a-z0-9]+/).filter(Boolean);
function scoreName(nn, groups, plural = false) {   // plural: USDA names say “Apples, raw”, so a typed “apple” also counts as a whole word there
  let score = 0;
  for (const alts of groups) {
    let best = 0;
    for (const a of alts) {
      const i = nn.indexOf(a);
      if (i < 0) continue;
      const before = i === 0 || /[^a-z0-9]/.test(nn[i - 1]);
      let end = i + a.length;
      if (plural) { const m = /^(es|s)(?![a-z0-9])/.exec(nn.slice(end)); if (m) end += m[1].length; }
      const after = nn[end];
      const whole = after === undefined || /[^a-z0-9]/.test(after);
      let sc = 1;
      if (before) sc = whole ? 6 : 4;
      if (i === 0 && whole && (after === undefined || after === ',' || (after === ' ' && nn[end + 1] === '('))) sc += 3;
      sc += Math.min(a.length, 24) / 10;   // longer, more specific matches rank first
      best = Math.max(best, sc);
    }
    if (!best) return 0;
    score += best;
  }
  return score;
}
function rankFoods(groups, limit, pool = CIQ) {
  const out = [];
  for (const f of pool) {
    const s = scoreName(f._nn, groups, pool !== CIQ);
    if (s) out.push([s * 100 - f._nn.length + (/(^|[^a-z])raw($|[^a-z])/.test(f._nn) ? 30 : 0), f]);
  }
  out.sort((a, b) => b[0] - a[0]);
  return out.slice(0, limit).map((x) => x[1]);
}
/* Two-word English phrases whose meaning differs from the words alone (almond milk is “almond drink” in CIQUAL). */
const PHRASES = [
  [/\b(almond) (milk|drink|beverage)\b/g, 'mandulaital'], [/\boat (milk|drink|beverage)\b/g, 'zabital'],
  [/\b(soy|soya) (milk|drink|beverage)\b/g, 'szojaital'], [/\brice (milk|drink)\b/g, 'rizsital'],
  [/\bcoconut milk\b/g, 'kokusztej'], [/\bsour cream\b/g, 'tejfol'], [/\b(whipping|heavy|double|single) cream\b/g, 'tejszin'],
  [/\bcottage cheese\b/g, 'turo'], [/\bground (beef|pork|turkey|chicken)\b/g, 'minced $1'],
];
function searchPool(pool, q, limit, usePhrases) {
  let qq = norm(q);
  if (usePhrases) for (const [re, to] of PHRASES) qq = qq.replace(re, to);
  const groups = tokensOf(qq).flatMap(altsFor);
  if (!groups.length) return [];
  let res = rankFoods(groups, limit, pool);
  if (!res.length && groups.length > 1) {
    // drop words that match nothing and search with the rest
    const useful = groups.filter((g) => pool.some((f) => scoreName(f._nn, [g], pool !== CIQ)));
    if (useful.length && useful.length < groups.length) res = rankFoods(useful, limit, pool);
  }
  return res;
}
/* CIQUAL names differ from everyday English (almond milk = “almond drink”), so the phrase list only applies there. USDA names are plain US English. */
const searchCiqual = (q, limit = 40) => searchPool(CIQ, q, limit, true);
const searchUsda = (q, limit = 10) => searchPool(USDA, q, limit, false);
/* dmBio names are Hungarian, so the word list (Hungarian -> English) is not used. A typed English word is also searched as the Hungarian word
   it stands for (chocolate -> csokolad), and a typed Hungarian word also without its ending (csokolades -> csokolade -> csokolad). */
let HU_OF = null;
function huStems(tok) {
  if (!HU_OF) { HU_OF = {}; for (const [hu, ens] of Object.entries(DICT)) for (const e of ens) { const w = norm(e); if (/^[a-z]+$/.test(w) && w !== hu) (HU_OF[w] = HU_OF[w] || []).push(hu); } }
  return HU_OF[tok] || [];
}
/* Words of 1-3 letters only count at the start of a word (egg must not find meggy), longer ones anywhere (Hungarian compounds: tejcsokolade). */
const dmHas = (nn, a) => (a.length >= 4 ? nn.includes(a) : new RegExp('(^|[^a-z0-9])' + a).test(nn));
const DM_EN = { maple: ['juhar'], syrup: ['szirup'], drink: ['ital'], sauce: ['szosz'], soup: ['leves'], bar: ['szelet'], spread: ['krem'], baby: ['bebi', 'csecsemo'], cookie: ['keksz'], biscuit: ['keksz'] };
function searchDm(q, limit = 10) {
  if (!DMBIO.length) return [];
  const digits = q.replace(/\s/g, '');
  if (/^\d{6,}$/.test(digits)) { const v = codeVariants(digits); return DMBIO.filter((f) => v.includes(f.barcode)); }
  const groups = tokensOf(q).map((t) => {
    const alts = [t, ...huStems(t), ...(DM_EN[t] || [])];
    if (t.length >= 5) alts.push(t.slice(0, -1));
    if (t.length >= 6) alts.push(t.slice(0, -2));
    return [...new Set(alts)];
  });
  const rank = (gs) => {
    const out = [];
    for (const f of DMBIO) {
      if (!gs.every((g) => g.some((a) => dmHas(f._nn, a)))) continue;
      const sc = scoreName(f._nn, gs.map((g) => g.filter((a) => dmHas(f._nn, a))), true);
      if (sc) out.push([sc * 100 - f._nn.length, f]);
    }
    return out.sort((a, b) => b[0] - a[0]).slice(0, limit).map((x) => x[1]);
  };
  let res = groups.length ? rank(groups) : [];
  if (!res.length && groups.length > 1) {   // drop the words that match nothing (an English word without a Hungarian partner) and search with the rest
    const useful = groups.filter((g) => DMBIO.some((f) => g.some((a) => dmHas(f._nn, a))));
    if (useful.length && useful.length < groups.length) res = rank(useful);
  }
  return res;
}
function searchLocal(q, onlyGrams) {
  const toks = tokensOf(q);
  const digits = q.replace(/\s/g, '');
  const res = [];
  for (const f of Object.values(S.foods)) {
    if (onlyGrams && f.basis.unit !== 'g') continue;
    if (/^\d{6,}$/.test(digits) && f.barcode === digits) { res.unshift(f); continue; }
    if (!toks.length) continue;
    const hay = norm(f.name + ' ' + (f.brand || ''));
    if (toks.every((t) => hay.includes(t))) res.push(f);
  }
  return res;
}

/* ================= nutrition maths ================= */
const getFood = (id) => (id.startsWith('c:') || id.startsWith('usda:') || id.startsWith('dm:') ? CIQ_BY_ID.get(id) : S.foods[id]);
const isG = (f) => f.basis.unit === 'g';

function cellOf(food, i) {
  if (food._cells) return food._cells[i];            // CIQUAL and USDA foods keep their numbers in an array
  return food.n ? food.n[KEYS[i]] : undefined;
}
function parseCell(c) {
  if (c === null || c === undefined || c === '') return null;
  if (typeof c === 'number') return Number.isFinite(c) && c >= 0 ? [c, c] : null;
  if (c === 't') return [0, 0];
  if (typeof c === 'string' && c[0] === '<') { const x = parseFloat(c.slice(1)); return Number.isFinite(x) ? [0, x] : null; }
  return null;
}
/* Nutrients of one food per base amount (100 g or 1 unit). lo/hi = lower/upper value; NaN = no data. */
function vecOf(food) {
  if (food._vec) return food._vec;
  const lo = new Float64Array(NUT_N).fill(NaN), hi = new Float64Array(NUT_N).fill(NaN);
  for (let i = 0; i < NUT_N; i++) {
    const p = parseCell(cellOf(food, i));
    if (p) { lo[i] = p[0]; hi[i] = p[1]; }
  }
  food._vec = { lo, hi };
  return food._vec;
}
/* Which values are estimates, not label values: the energy of generic foods worked out from protein, carbohydrate and fat (estE),
   every dmBio value that is not on the dm label (f._lab = indexes of the label values; f.q = confidence of the estimate),
   and in the foods you made yourself the values listed in f.est (f.q = confidence, f.fortified = vitamins or minerals may have been added).
   Those three fields come from "Paste from AI" or from the Estimates part of the food editor; est only holds keys that also have a value in f.n.
   f._est is a cache of the indexes (it starts with _, so it is never saved, synced or exported). */
const CONF = { h: 'high', m: 'medium', l: 'low', v: 'very low', n: 'none' };
function estSet(f) {
  if (!f._est) f._est = new Set((Array.isArray(f.est) ? f.est : []).map((k) => IDX[k]).filter((i) => i !== undefined));
  return f._est;
}
const energyEstimated = (f) => (f._cells
  ? !!f.estE || (!!f._lab && !f._lab.has(0) && !Number.isNaN(vecOf(f).lo[0]))
  : estSet(f).has(0) && !Number.isNaN(vecOf(f).lo[0]));
function isEst(f, i, v) {
  if (Number.isNaN(v.lo[i])) return false;
  if (i === 0) return energyEstimated(f);
  return f._cells ? !!f._lab && !f._lab.has(i) : estSet(f).has(i);
}
function invalidate() { for (const f of Object.values(S.foods)) { delete f._vec; delete f._est; } }

function totalsFor(entries) {
  const lo = new Float64Array(NUT_N), hi = new Float64Array(NUT_N), cnt = new Uint16Array(NUT_N), est = new Uint16Array(NUT_N);
  const missing = Array.from({ length: NUT_N }, () => []), estNames = Array.from({ length: NUT_N }, () => []);
  let n = 0;
  for (const e of entries) {
    const f = getFood(e.f);
    if (!f) continue;
    n++;
    const v = vecOf(f), k = e.a / f.basis.qty;
    for (let i = 0; i < NUT_N; i++) {
      if (Number.isNaN(v.lo[i])) missing[i].push(f.name);
      else {
        lo[i] += v.lo[i] * k; hi[i] += v.hi[i] * k; cnt[i]++;
        if (isEst(f, i, v)) { est[i]++; estNames[i].push(f.q ? `${f.name} (${CONF[f.q]})` : f.name); }
      }
    }
  }
  return { lo, hi, cnt, est, n, missing, estNames };
}
const entriesOf = (day) => S.log.filter((e) => e.d === day && getFood(e.f));
/* Time of an entry: the saved time (tm, "HH:MM", editable); entries from before this feature use the moment they were added (t). */
const timeOf = (e) => (validHm(e.tm) ? e.tm : Number.isFinite(e.t) ? hm(new Date(e.t)) : '');
const byTime = (a, b) => timeOf(a).localeCompare(timeOf(b)) || (a.t || 0) - (b.t || 0);
const amountText = (e, f) => `${fmt(e.a)} ${f.basis.unit}`;
const trackedKnown = (f) => { const v = vecOf(f); return TRACKED.reduce((c, i) => c + (Number.isNaN(v.lo[i]) ? 0 : 1), 0); };
const trackedEst = (f) => { const v = vecOf(f); return TRACKED.reduce((c, i) => c + (isEst(f, i, v) ? 1 : 0), 0); };
const srcTag = (f) => (f.src === 'ciqual' ? 'CIQUAL' : f.src === 'usda' ? 'USDA' : f.src === 'dmbio' ? 'dmBio' : f.src === 'off' ? 'OFF' : 'custom');
const kcalPer = (f) => vecOf(f).lo[0];

/* ---- NOVA: how processed a food is (1 minimal … 4 ultra-processed) ----
   Open Food Facts gives a group for some products; CIQUAL and USDA give none. Unknown stays unknown: nothing is guessed.
   Foods you create and Open Food Facts foods are stored in S.foods and keep the group in food.nova (the same field as in Edit food).
   CIQUAL and USDA foods cannot be edited, so your choice for them is kept in S.meta.nova[food id]. */
const NOVA = [
  [1, 'Unprocessed or minimally processed', 'vegetables, fruit, eggs, milk, plain meat and fish, rice, flour, nuts'],
  [2, 'Processed culinary ingredients', 'oil, butter, sugar, salt, honey, vinegar'],
  [3, 'Processed foods', 'canned vegetables, cheese, fresh bread, salted nuts, fruit in syrup'],
  [4, 'Ultra-processed foods', 'soft drinks, packaged snacks, sweets, instant soups, ready meals, sausages, most breakfast cereals'],
];
const novaStored = (f) => f.src === 'user' || f.src === 'off';
function novaOf(f) {
  const v = Number(novaStored(f) ? f.nova : (S.meta.nova || {})[f.id]);
  return [1, 2, 3, 4].includes(v) ? v : null;
}
function setNova(f, v) {                             // v = 1..4, or null for "not classified"
  if (novaStored(f)) f.nova = v;
  else {
    if (!S.meta.nova || typeof S.meta.nova !== 'object') S.meta.nova = {};
    if (v) S.meta.nova[f.id] = v; else delete S.meta.nova[f.id];
  }
  save();
}
/* Energy of the given entries split by NOVA group (key 'u' = not classified), and one row per food. Entries without energy data
   cannot be weighed, so they are counted in noEnergy and left out of the shares. */
function novaStats(es) {
  const by = { 1: 0, 2: 0, 3: 0, 4: 0, u: 0 };
  const items = new Map();
  let noEnergy = 0;
  for (const e of es) {
    const food = getFood(e.f);
    if (!food) continue;
    const g = novaOf(food), kv = vecOf(food).lo[0];
    let it = items.get(food.id);
    if (!it) { it = { food, g, kcal: 0, known: 0 }; items.set(food.id, it); }
    if (Number.isNaN(kv)) { noEnergy++; continue; }
    const kcal = kv * e.a / food.basis.qty;
    it.kcal += kcal; it.known++; by[g || 'u'] += kcal;
  }
  const sum = by[1] + by[2] + by[3] + by[4] + by.u;
  return { by, sum, items: [...items.values()].sort((a, b) => b.kcal - a.kcal), noEnergy };
}
/* whole percents that add up to exactly 100 (largest remainder) */
function sharePct(vals, total) {
  const raw = vals.map((v) => (total > 0 ? v / total * 100 : 0));
  const out = raw.map(Math.floor);
  let rest = 100 - out.reduce((a, b) => a + b, 0);
  raw.map((r, i) => [r - out[i], i]).sort((a, b) => b[0] - a[0]).forEach(([, i]) => { if (rest > 0 && raw[i] > 0) { out[i]++; rest--; } });
  return out;
}
let novaOpen = false;                                // the "Set NOVA groups" list stays open while you work through it

/* ================= saving ================= */
function save() { clearTimeout(saveTimer); saveTimer = setTimeout(doSave, 120); }
async function doSave() {
  const clean = (o) => JSON.parse(JSON.stringify(o, (k, v) => (k[0] === '_' ? undefined : v)));
  await Store.set('log', S.log);
  await Store.set('foods', clean(S.foods));
  await Store.set('meta', S.meta);
  if (syncStamp()) { await Store.set('sync', syncPersist()); syncSoon(); }   // note which records changed, so Sync knows what to send
  try { navigator.storage?.persist?.(); } catch { /* not critical */ }
}

/* ================= sync with a private GitHub repository ================= */
/* The diary is kept in a private repository of your own. Every record has a time of its last change (u); when two devices
   changed the same record, the later change wins; a deleted record stays behind as a marker (tombstone), so the deletion reaches the other devices too.
   Records: 'e:<entry id>' diary entries, 'f:<food id>' foods you made or saved from Open Food Facts, 'p:<food id>' your own portion sizes,
   'n:<food id>' NOVA groups you chose for CIQUAL, USDA and dmBio foods. They live in files of the repository:
   entries/YYYY-MM.json, foods/0..7.json, meta.json. The state (times, hashes, files seen, token) is kept apart from the diary under the Store key 'sync',
   so the data records and the backup file are not changed by it. The token is never part of the backup. */
const SY = { cfg: null, rec: {}, shas: {}, last: 0, born: 0, info: '', err: '', offline: false, stop: false, busy: false, again: false, timer: null, progress: '', applied: 0, sent: 0, viewStale: false, ranAt: 0, toasted: false };
const SYNC_SHARD = /^(entries\/(\d{4}-\d{2}|undated)|foods\/[0-7]|meta)\.json$/;
const SYNC_DELAY = 4000;
const syncPersist = () => ({ cfg: SY.cfg, rec: SY.rec, shas: SY.shas, last: SY.last, born: SY.born, info: SY.info });

function hashNum(str) {   // cyrb53, a small fast hash; it only tells "changed or not", it is not for secrets
  let h1 = 0xdeadbeef, h2 = 0x41c6ce57;
  for (let i = 0; i < str.length; i++) { const ch = str.charCodeAt(i); h1 = Math.imul(h1 ^ ch, 2654435761); h2 = Math.imul(h2 ^ ch, 1597334677); }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507); h1 ^= Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507); h2 ^= Math.imul(h1 ^ (h1 >>> 13), 3266489909);
  return 4294967296 * (2097151 & h2) + (h1 >>> 0);
}
const hashStr = (s) => hashNum(s).toString(36);
/* the same JSON text for the same content: keys sorted, helper keys (starting with _) left out */
function canon(v) {
  return JSON.stringify(v, (k, x) => {
    if (k && k[0] === '_') return undefined;
    if (x && typeof x === 'object' && !Array.isArray(x)) { const o = {}; for (const kk of Object.keys(x).sort()) o[kk] = x[kk]; return o; }
    return x;
  });
}
/* everything that is synced, as key -> { v: value, s: file } */
function syncRecords() {
  const out = new Map();
  for (const e of S.log) {
    const m = /^\d{4}-\d{2}/.exec(e.d || '');
    out.set('e:' + e.id, { v: e, s: `entries/${m ? m[0] : 'undated'}.json` });
  }
  for (const [id, f] of Object.entries(S.foods)) out.set('f:' + id, { v: f, s: `foods/${hashNum(id) % 8}.json` });
  for (const [id, p] of Object.entries(S.meta.portions || {})) out.set('p:' + id, { v: p, s: 'meta.json' });
  for (const [id, n] of Object.entries(S.meta.nova || {})) out.set('n:' + id, { v: n, s: 'meta.json' });
  return out;
}
/* the time of a record that existed before it was ever synced: when it was made or last edited, so it never beats a real later change */
const baselineU = (v) => (v && typeof v === 'object' ? Number(v.updated) || Number(v.t) || Number(v.created) || 1 : 1);
/* Compare the data with what was noted last time. Changed or new record: new time (always later than the one known), pending. Gone record: tombstone.
   Returns true when something changed. */
function syncStamp() {
  const cur = syncRecords(), now = Date.now(), legacy = !SY.born;
  let changed = false;
  for (const [k, { v, s }] of cur) {
    const h = hashStr(canon(v)), r = SY.rec[k];
    if (r && r.h === h) continue;
    SY.rec[k] = { u: r ? Math.max(now, r.u + 1) : legacy ? baselineU(v) : now, h, s: r && r.s ? r.s : s, p: 1, sy: r ? r.sy : 0 };
    changed = true;
  }
  for (const [k, r] of Object.entries(SY.rec)) {
    if (r.h !== null && !cur.has(k)) { SY.rec[k] = { u: Math.max(now, r.u + 1), h: null, s: r.s, p: 1, sy: r.sy }; changed = true; }
  }
  if (!SY.born) { SY.born = now; changed = true; }
  return changed;
}
/* when sync is switched on: what was never synced counts as old data, whatever the clock said while it was saved */
function syncRebaseline() {
  const cur = syncRecords();
  for (const [k, r] of Object.entries(SY.rec)) if (!r.sy && r.h !== null && cur.has(k)) r.u = baselineU(cur.get(k).v);
}
function syncSoon(ms = SYNC_DELAY) {
  if (!SY.cfg) return;
  clearTimeout(SY.timer);
  SY.timer = setTimeout(() => syncRun('change'), ms);
}

/* ---- GitHub ---- */
async function ghFetch(cfg, path, opt = {}) {
  try {
    return await fetch('https://api.github.com' + path, {
      method: opt.method || 'GET', cache: 'no-store',   // no-store: GitHub answers may otherwise be served from the browser cache for a minute
      headers: { Authorization: 'Bearer ' + cfg.token, Accept: opt.accept || 'application/vnd.github+json', ...(opt.body ? { 'Content-Type': 'application/json' } : {}) },
      body: opt.body ? JSON.stringify(opt.body) : undefined,
    });
  } catch { throw Object.assign(new Error('Could not reach GitHub.'), { net: true }); }
}
async function ghError(r) {
  let detail = ''; try { detail = (await r.json()).message || ''; } catch { /* no details */ }
  const rate = r.status === 429 || (r.status === 403 && (r.headers.get('x-ratelimit-remaining') === '0' || !!r.headers.get('retry-after') || /rate limit|abuse/i.test(detail)));
  let msg;
  if (r.status === 401) msg = 'GitHub does not accept the token. It may have expired or been copied wrongly. Create a new token and connect again.';
  else if (rate) msg = 'GitHub is limiting requests for a while. Sync works again later.';
  else if (r.status === 403) msg = 'GitHub refuses this: the token needs the permission “Contents: Read and write” for this repository.';
  else if (r.status === 404) msg = 'GitHub cannot find the repository (or its branch), or the token has no access to it.';
  else msg = `GitHub answered with an error (${r.status}).${detail ? ' ' + detail : ''}`;
  return Object.assign(new Error(msg), { status: r.status, rate });
}
async function ghJson(cfg, path) {
  const r = await ghFetch(cfg, path);
  if (!r.ok) throw await ghError(r);
  return r.json();
}
/* files of the repository: Map path -> sha. An empty repository has no branch yet (HTTP 409). */
async function ghTree(cfg) {
  const r = await ghFetch(cfg, `/repos/${cfg.owner}/${cfg.repo}/git/trees/${encodeURIComponent(cfg.branch)}?recursive=1`);
  if (r.status === 409) return { files: new Map(), empty: true };
  if (!r.ok) throw await ghError(r);
  const j = await r.json();
  return { files: new Map((j.tree || []).filter((t) => t.type === 'blob').map((t) => [t.path, t.sha])), empty: false };
}
async function ghRaw(cfg, path) {
  const r = await ghFetch(cfg, `/repos/${cfg.owner}/${cfg.repo}/contents/${path}?ref=${encodeURIComponent(cfg.branch)}`, { accept: 'application/vnd.github.raw+json' });
  if (!r.ok) throw await ghError(r);
  return r.text();
}
const b64enc = (s) => { const b = new TextEncoder().encode(s); let bin = ''; for (let i = 0; i < b.length; i += 0x8000) bin += String.fromCharCode.apply(null, b.subarray(i, i + 0x8000)); return btoa(bin); };
/* write one file. conflict = somebody changed it since we looked (HTTP 409 or 422): look again */
async function ghPut(cfg, path, text, sha, empty) {
  const body = { message: 'Nutrilog sync: ' + path, content: b64enc(text) };
  if (sha) body.sha = sha;
  if (!empty) body.branch = cfg.branch;
  const r = await ghFetch(cfg, `/repos/${cfg.owner}/${cfg.repo}/contents/${path}`, { method: 'PUT', body });
  if (r.status === 409 || r.status === 422) return { conflict: true };
  if (!r.ok) throw await ghError(r);
  const j = await r.json();
  return { sha: j.content && j.content.sha };
}
async function mapLimit(list, n, fn) {
  const out = new Array(list.length); let next = 0;
  await Promise.all(Array.from({ length: Math.min(n, list.length) }, async () => { while (next < list.length) { const i = next++; out[i] = await fn(list[i]); } }));
  return out;
}

/* ---- files <-> records ---- */
function validRec(k, x) {
  if (!/^[efpn]:./.test(k)) return false;
  if (x === null) return true;
  const id = k.slice(2);
  if (k[0] === 'e') return typeof x === 'object' && !Array.isArray(x) && x.id === id && typeof x.d === 'string' && typeof x.f === 'string' && Number.isFinite(x.a);
  if (k[0] === 'f') return typeof x === 'object' && !Array.isArray(x) && x.id === id;
  if (k[0] === 'p') return Array.isArray(x);
  return [1, 2, 3, 4].includes(x);
}
function parseShard(text, path) {
  let j; try { j = JSON.parse(text); } catch { j = null; }
  if (!j || j.app !== 'tapnaplo-sync' || !j.recs || typeof j.recs !== 'object') throw new Error(`The file ${path} in the repository is not a Nutrilog sync file. Use an empty repository for Nutrilog.`);
  const out = new Map();
  for (const [k, rr] of Object.entries(j.recs)) if (rr && Number.isFinite(rr.u) && 'x' in rr && validRec(k, rr.x)) out.set(k, { u: rr.u, x: rr.x });
  return out;
}
const replaceObj = (o, x) => { for (const k of Object.keys(o)) if (k[0] !== '_') delete o[k]; Object.assign(o, x); };
function syncApply(k, x) {
  const id = k.slice(2);
  if (k[0] === 'e') {
    const i = S.log.findIndex((e) => e.id === id);
    if (x === null) { if (i >= 0) S.log.splice(i, 1); } else if (i >= 0) replaceObj(S.log[i], x); else S.log.push(x);   // an entry that is open in a sheet is changed in place
  } else if (k[0] === 'f') {
    if (x === null) delete S.foods[id]; else if (S.foods[id]) replaceObj(S.foods[id], x); else S.foods[id] = x;
  } else if (k[0] === 'p') {
    S.meta.portions = S.meta.portions || {};
    if (x === null) delete S.meta.portions[id]; else S.meta.portions[id] = x;
  } else {
    S.meta.nova = S.meta.nova || {};
    if (x === null) delete S.meta.nova[id]; else S.meta.nova[id] = x;
  }
}
/* remote: Map key -> { u, x, s }. The later change wins; with the same time the remote one (same on every device). Returns how many records were taken from the repository. */
function syncMerge(remote) {
  let applied = 0;
  for (const [k, rr] of remote) {
    const lr = SY.rec[k], rh = rr.x === null ? null : hashStr(canon(rr.x));
    if (lr && lr.h === rh) { lr.sy = 1; lr.p = lr.u > rr.u ? 1 : 0; lr.u = Math.max(lr.u, rr.u); continue; }   // same content
    if (lr && lr.u > rr.u) { lr.p = 1; continue; }                                                              // ours is newer: send it
    syncApply(k, rr.x); applied++;
    SY.rec[k] = { u: rr.u, h: rh, s: rr.s, p: 0, sy: 1 };
  }
  return applied;
}
/* One pass: look at the repository, take what is new, send what is ours. false = another device wrote at the same time, so look again. */
async function syncRound() {
  const cfg = SY.cfg;
  const { files, empty } = await ghTree(cfg);
  for (const p of Object.keys(SY.shas)) {
    if (!files.has(p)) { delete SY.shas[p]; for (const r of Object.values(SY.rec)) if (r.s === p) r.p = 1; }   // file gone from the repository: send it again
  }
  const changed = [...files.keys()].filter((p) => SYNC_SHARD.test(p) && files.get(p) !== SY.shas[p]);
  const texts = await mapLimit(changed, 4, (p) => ghRaw(cfg, p));
  /* from here to the first write there is no waiting, so nothing can change in between */
  const remote = new Map(), seen = new Map();
  changed.forEach((p, i) => {
    const ks = new Set();
    for (const [k, rr] of parseShard(texts[i], p)) { ks.add(k); const old = remote.get(k); if (!old || old.u < rr.u) remote.set(k, { ...rr, s: p }); }
    seen.set(p, ks);
  });
  syncStamp();
  SY.applied += syncMerge(remote);
  for (const [p, ks] of seen) for (const [k, r] of Object.entries(SY.rec)) if (r.s === p && !ks.has(k)) r.p = 1;   // the file lacks a record we have
  const byPath = new Map();
  for (const [k, r] of Object.entries(SY.rec)) { if (!byPath.has(r.s)) byPath.set(r.s, []); byPath.get(r.s).push(k); }
  const dirty = [...byPath.keys()].filter((p) => byPath.get(p).some((k) => SY.rec[k].p));
  for (const p of changed) if (!dirty.includes(p)) SY.shas[p] = files.get(p);
  const cur = syncRecords();
  let n = 0;
  for (const p of dirty) {
    const keys = byPath.get(p).sort(), stamp = {}, recs = {};
    for (const k of keys) {
      const r = SY.rec[k]; stamp[k] = r.u;
      if (r.h === null) recs[k] = { u: r.u, x: null };
      else if (cur.has(k)) recs[k] = { u: r.u, x: cur.get(k).v };
    }
    SY.progress = `Sending file ${++n} of ${dirty.length}…`; syncUi();
    if (n > 1) await new Promise((res) => setTimeout(res, 700));   // GitHub asks for a short pause between writes
    const text = JSON.stringify({ app: 'tapnaplo-sync', v: 1, recs }, (kk, x) => (kk && kk[0] === '_' ? undefined : x));
    const res = await ghPut(cfg, p, text, files.get(p), empty && !files.size);
    if (res.conflict) return false;
    SY.shas[p] = res.sha;
    for (const k of keys) { const r = SY.rec[k]; if (r && r.u === stamp[k]) { r.p = 0; r.sy = 1; SY.sent++; } }   // a record changed during the sending stays pending
  }
  return true;
}
async function syncRun(why) {
  if (!SY.cfg) return;
  if (SY.busy) { SY.again = true; return; }
  if (SY.stop && why !== 'manual' && why !== 'connect') return;
  if (!navigator.onLine) { SY.offline = true; syncUi(); return; }
  Object.assign(SY, { busy: true, offline: false, stop: false, err: '', applied: 0, sent: 0 }); syncUi();
  try {
    for (let round = 0; ; round++) {
      if (await syncRound()) break;
      if (round >= 3) throw new Error('Another device keeps writing at the same time. Try again in a moment.');
    }
    SY.last = Date.now(); SY.info = `Received ${SY.applied}, sent ${SY.sent}.`;
  } catch (e) {
    if (e.net) SY.offline = true;
    else { SY.err = e.message || 'Sync failed.'; if ([401, 403, 404].includes(e.status) && !e.rate) SY.stop = true; }
  } finally {
    SY.busy = false; SY.progress = ''; SY.ranAt = Date.now();
    await Store.set('sync', syncPersist());
    if (SY.applied) { invalidate(); S.log.sort((a, b) => (a.t || 0) - (b.t || 0)); save(); syncViewChanged(); }
    syncUi();
    if (SY.stop && !SY.toasted) { SY.toasted = true; toast('Sync stopped. Open Data → Sync to see why.'); }
    if (SY.again) { SY.again = false; syncSoon(500); }
  }
}
/* other devices changed something: draw the view again, or when a sheet is open, as soon as it is closed */
function syncViewChanged() { if (sheets.length) SY.viewStale = true; else render(); }
function syncStatusHtml() {
  if (!SY.cfg) return '';
  const pend = Object.values(SY.rec).filter((r) => r.p).length;
  const waiting = pend ? ` ${pend === 1 ? '1 change is' : pend + ' changes are'} waiting to be sent.` : '';
  if (SY.busy) return esc(SY.progress || 'Syncing…');
  if (SY.err) return `<span class="note" role="alert" style="display:block;margin:0">${esc(SY.err)}</span>`;
  const when = SY.last ? `Last sync: ${esc(new Date(SY.last).toLocaleString(LOC))}. ${esc(SY.info)}` : 'Not synced yet.';
  return (SY.offline ? 'Offline: your changes stay on this device and are sent when you are online again. ' : '') + when + waiting;
}
function syncUi() {
  const el = $('#sync-status'); if (el) el.innerHTML = syncStatusHtml();
  const b = $('#sync-now'); if (b) b.disabled = SY.busy;
}
function syncCard() {
  if (!SY.cfg) return `<div class="card"><div class="card-t">Sync</div>
      <p class="muted small" style="margin:6px 0 14px">Use the same diary on your phone and your computer. Your data is saved in a private GitHub repository that only you can open, and the devices are merged automatically. Needs a free GitHub account. Keep making file backups as well.</p>
      <button class="btn primary" data-act="sync-setup">Set up sync</button></div>`;
  return `<div class="card"><div class="card-t">Sync</div>
      <p class="muted small" style="margin:6px 0 10px">Connected to the private repository <b>${esc(SY.cfg.owner)}/${esc(SY.cfg.repo)}</b>. Changes are sent a few seconds after you make them, and new changes from other devices are fetched when you open the app.</p>
      <div class="small" id="sync-status" aria-live="polite">${syncStatusHtml()}</div>
      <div class="row gap" style="margin-top:14px"><button class="btn primary" id="sync-now" data-act="sync-now" ${SY.busy ? 'disabled' : ''}>Sync now</button><button class="btn" data-act="sync-off">Disconnect</button></div></div>`;
}
function openSyncSetup() {
  const sh = openSheet('Set up sync', `
    <p class="muted small" style="margin:0 0 12px">First create an empty <b>private</b> repository on GitHub and an access token that can only change that repository. The steps are in the guide (README). The token stays on this device and is never part of a backup file.</p>
    <label class="f">Repository<input type="text" enterkeyhint="next" id="sy-repo" placeholder="your-name/nutrilog-data" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false"></label>
    <label class="f" style="margin-top:10px">Access token<input type="password" enterkeyhint="go" id="sy-token" placeholder="github_pat_…" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false"></label>
    <div class="row gap sheet-actions"><button class="btn" data-dx>Cancel</button><span style="flex:1"></span><button class="btn primary" data-ok>Connect</button></div>`);
  const repo = $('#sy-repo', sh.el), tok = $('#sy-token', sh.el), ok = $('[data-ok]', sh.el);
  sh.el.addEventListener('input', (e) => { $$('.field-err', sh.el).forEach((x) => x.remove()); if (e.target.removeAttribute) e.target.removeAttribute('aria-invalid'); });
  $('[data-dx]', sh.el).onclick = () => sh.close();
  repo.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); tok.focus(); } });
  tok.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); ok.click(); } });
  ok.onclick = async () => {
    $$('.field-err', sh.el).forEach((x) => x.remove());
    const name = repo.value.trim().replace(/^https?:\/\/github\.com\//i, '').replace(/\.git$/i, '').replace(/\/+$/, '');
    const m = /^([A-Za-z0-9-]+)\/([A-Za-z0-9._-]+)$/.exec(name);
    if (!m) { fieldError(repo, 'Write it as name/repository, for example your-name/nutrilog-data.'); return; }
    const token = tok.value.trim();
    if (!token) { fieldError(tok, 'Paste the access token here.'); return; }
    ok.disabled = true; ok.textContent = 'Connecting…';
    const cfg = { owner: m[1], repo: m[2], branch: 'main', token };
    try {
      const j = await ghJson(cfg, `/repos/${cfg.owner}/${cfg.repo}`);
      if (j.private !== true) { fieldError(repo, 'This repository is public: everyone could read your diary. Make it private in its GitHub settings, or create a new private one.', false); return; }
      cfg.branch = j.default_branch || 'main';
      Object.assign(SY, { cfg, shas: {}, stop: false, err: '', offline: false, toasted: false });
      syncStamp(); syncRebaseline();
      await Store.set('sync', syncPersist());
      sh.close(); render(); syncRun('connect');
    } catch (e) { fieldError(e.status === 401 ? tok : repo, e.net ? 'Could not reach GitHub. Check your internet connection.' : e.message, false); }
    finally { ok.disabled = false; ok.textContent = 'Connect'; }
  };
  if (!TOUCH) setTimeout(() => repo.focus(), 60);
}
function syncOff() {
  askConfirm({
    title: 'Disconnect sync?', okLabel: 'Disconnect',
    text: 'This device stops syncing and forgets the token. Your diary stays on this device and in the repository. To connect again you need a token.',
    onOk: async () => {
      clearTimeout(SY.timer);
      Object.assign(SY, { cfg: null, shas: {}, err: '', offline: false, stop: false });
      await Store.set('sync', syncPersist());
      render(); toast('Sync is off');
    },
  });
}

/* ================= Open Food Facts ================= */
const OFF_MAP = {
  'proteins_100g': ['protein', 1], 'carbohydrates_100g': ['carbohydrate', 1], 'fat_100g': ['fat', 1], 'sugars_100g': ['sugars', 1],
  'fiber_100g': ['fibres', 1], 'saturated-fat_100g': ['fa_saturated', 1], 'monounsaturated-fat_100g': ['fa_mono', 1],
  'polyunsaturated-fat_100g': ['fa_poly', 1], 'cholesterol_100g': ['cholesterol', 1000], 'salt_100g': ['salt', 1],
  'sodium_100g': ['sodium', 1000], 'calcium_100g': ['calcium', 1000], 'iron_100g': ['iron', 1000], 'magnesium_100g': ['magnesium', 1000],
  'potassium_100g': ['potassium', 1000], 'zinc_100g': ['zinc', 1000], 'phosphorus_100g': ['phosphorus', 1000],
  'copper_100g': ['copper', 1000], 'manganese_100g': ['manganese', 1000], 'chloride_100g': ['chloride', 1000],
  'iodine_100g': ['iodine', 1e6], 'selenium_100g': ['selenium', 1e6], 'vitamin-d_100g': ['vitamin_d', 1e6],
  'vitamin-e_100g': ['vitamin_e', 1000], 'vitamin-c_100g': ['vitamin_c', 1000], 'vitamin-b1_100g': ['vitamin_b1_or_thiamin', 1000],
  'vitamin-b2_100g': ['vitamin_b2_or_riboflavin', 1000], 'vitamin-pp_100g': ['vitamin_b3_or_niacin', 1000],
  'pantothenic-acid_100g': ['vitamin_b5_or_pantothenic_acid', 1000], 'vitamin-b6_100g': ['vitamin_b6', 1000],
  'vitamin-b9_100g': ['vitamin_b9_or_folate', 1e6], 'vitamin-b12_100g': ['vitamin_b12', 1e6],
};
const OFF_FIELDS = 'code,product_name,product_name_en,product_name_hu,brands,quantity,serving_quantity,serving_size,nova_group,nutriments';
function offToFood(p) {
  const nm = p.nutriments || {};
  const val = (k) => { const x = nm[k]; if (x === null || x === undefined || x === '') return null; const v = Number(x); return Number.isFinite(v) && v >= 0 ? v : null; };
  const n = {};
  let kcal = val('energy-kcal_100g');
  if (kcal === null) { const kj = val('energy_100g'); if (kj !== null) kcal = kj / 4.184; }
  if (kcal !== null) n.kcal = prec(kcal);
  for (const [ok, [key, mult]] of Object.entries(OFF_MAP)) { const v = val(ok); if (v !== null) n[key] = prec(v * mult); }
  if (n.salt == null && n.sodium != null) n.salt = prec(n.sodium * 2.5 / 1000);
  if (n.sodium == null && n.salt != null) n.sodium = prec(n.salt * 400);
  const portions = [];
  const sq = Number(p.serving_quantity);
  if (Number.isFinite(sq) && sq > 0) portions.push({ label: p.serving_size ? String(p.serving_size).slice(0, 40) : '1 serving', grams: sq });
  return {
    id: 'o:' + p.code, src: 'off', name: String(p.product_name || p.product_name_en || p.product_name_hu || 'Unnamed product').slice(0, 120),
    brand: String(p.brands || '').slice(0, 80), barcode: String(p.code), basis: { qty: 100, unit: 'g' }, n,
    nova: [1, 2, 3, 4].includes(Number(p.nova_group)) ? Number(p.nova_group) : null, portions,
    note: 'Open Food Facts (community data, taken from the label)', fetched: Date.now(),
  };
}
/* allow404: for a barcode lookup Open Food Facts answers "404" when the product simply is not in the database */
async function offFetch(url, allow404) {
  const r = await fetch(url, { headers: { Accept: 'application/json' } });
  if (r.status === 404 && allow404) return { status: 0 };
  if (!r.ok) throw new Error('Open Food Facts is not available right now (HTTP ' + r.status + '). Try again in a minute.');
  return r.json();
}
/* the same product can be stored as a 12-digit UPC-A or as a 13-digit EAN with a leading 0 */
function codeVariants(code) {
  const c = String(code).replace(/\s/g, '');
  if (c.length === 12) return [c, '0' + c];
  if (c.length === 13 && c[0] === '0') return [c, c.slice(1)];
  return [c];
}
async function offProduct(code) {
  for (const c of codeVariants(code)) {
    const j = await offFetch(`https://world.openfoodfacts.org/api/v2/product/${encodeURIComponent(c)}.json?fields=${OFF_FIELDS}`, true);
    if (j.status === 1 && j.product) { j.product.code = j.product.code || c; return offToFood(j.product); }
  }
  return null;
}
async function offSearch(q, huOnly) {
  const p = new URLSearchParams({ search_terms: q, search_simple: '1', action: 'process', json: '1', page_size: '20', sort_by: 'unique_scans_n', fields: OFF_FIELDS });
  if (huOnly) { p.set('tagtype_0', 'countries'); p.set('tag_contains_0', 'contains'); p.set('tag_0', 'hungary'); }
  const j = await offFetch('https://world.openfoodfacts.org/cgi/search.pl?' + p);
  return (j.products || []).filter((x) => x.code).map(offToFood);
}
function keepOff(food) {
  const have = S.foods[food.id];
  if (have) return have;
  S.foods[food.id] = food;
  save();
  return food;
}

/* ================= sheets (bottom dialogs) and toast ================= */
const sheets = [];
function openSheet(title, html) {
  const wrap = document.createElement('div');
  wrap.className = 'sheet-wrap';
  wrap.innerHTML = `<div class="sheet" role="dialog" aria-modal="true"><header class="sheet-h"><h2></h2><button class="icon-btn" data-x aria-label="Close">${IC.close}</button></header><div class="sheet-b"></div></div>`;
  $('h2', wrap).textContent = title;
  $('.sheet', wrap).setAttribute('aria-label', title);
  const body = $('.sheet-b', wrap);
  body.innerHTML = html;
  if (body.querySelector(':scope > .sheet-actions')) wrap.classList.add('has-actions');   // the main buttons stay at the bottom, only the content above them scrolls
  const api = {
    el: body, wrap, onClose: null,
    close() {
      const i = sheets.indexOf(api);
      if (i < 0) return;
      sheets.splice(i, 1);
      wrap.remove();
      if (api.onClose) api.onClose();
      if (!sheets.length) { document.body.classList.remove('noscroll', 'kb'); if (SY.viewStale) { SY.viewStale = false; render(); } }   // sync brought changes while the sheet was open
    },
  };
  wrap.addEventListener('click', (ev) => { if (ev.target === wrap || ev.target.closest('[data-x]')) api.close(); });
  $('#sheets').append(wrap);
  sheets.push(api);
  document.body.classList.add('noscroll');
  fitSheets();
  return api;
}
document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && sheets.length) sheets[sheets.length - 1].close(); });
/* On an iPhone the on-screen keyboard covers the page instead of making it shorter, so a bottom sheet would end up behind it.
   While the keyboard is up (the visible part of the screen is clearly lower than the page), the sheets are only as tall as the visible part. Not while the page is pinch-zoomed. */
function fitSheets() {
  const vv = window.visualViewport;
  const up = !!vv && vv.scale <= 1.01 && (window.innerHeight - vv.height > 80 || vv.offsetTop > 1) && sheets.length > 0;
  if (up) { const r = document.documentElement.style; r.setProperty('--vvt', vv.offsetTop + 'px'); r.setProperty('--vvh', vv.height + 'px'); }
  document.body.classList.toggle('kb', up);
}
if (window.visualViewport) { window.visualViewport.addEventListener('resize', fitSheets); window.visualViewport.addEventListener('scroll', fitSheets); }

let toastTimer = null;
function toast(msg, undo) {
  const t = $('#toast');
  t.innerHTML = `<span>${esc(msg)}</span>${undo ? '<button type="button">Undo</button>' : ''}`;
  t.hidden = false;
  if (undo) $('button', t).onclick = () => { undo(); t.hidden = true; };
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.hidden = true; }, undo ? 6000 : 3000);
}

/* ================= header, tabs, views ================= */
const TABS = [['log', 'Diary', IC.diary], ['nutr', 'Nutrients', IC.nutr], ['foods', 'My foods', IC.foods], ['data', 'Data', IC.data]];

function renderChrome() {
  $('#tabbar').innerHTML = TABS.map(([id, name, ic]) => `<button class="tab" data-act="tab" data-tab="${id}" ${S.tab === id ? 'aria-current="page"' : ''}>${ic}<span>${name}</span></button>`).join('');
  const top = $('#topbar');
  if (S.tab === 'log' || S.tab === 'nutr') {
    const today = ymd(new Date());
    top.innerHTML = `<div class="title"><h1>${esc(dayTitle(S.day))}</h1><p class="sub">${esc(fmtLong(S.day))}</p></div>
      <div class="hdr-actions">
        ${S.day !== today ? '<button class="chip-btn accent" data-act="today">Today</button>' : ''}
        <button class="icon-btn" data-act="day" data-n="-1" aria-label="Previous day">${IC.left}</button>
        <button class="icon-btn" data-act="day" data-n="1" aria-label="Next day">${IC.right}</button>
        <label class="icon-btn" title="Pick a date">${IC.cal}<input type="date" id="datepick" value="${S.day}" aria-label="Date"></label>
      </div>`;
  } else {
    top.innerHTML = `<div class="title"><h1>${S.tab === 'foods' ? 'My foods' : 'Data &amp; backup'}</h1></div>`;
  }
}

function render() {
  renderChrome();
  $('#view').innerHTML = S.tab === 'log' ? viewLog() : S.tab === 'nutr' ? viewNutr() : S.tab === 'foods' ? viewFoods() : viewData();
  if (S.tab === 'data') persistState();
}

/* ---- Diary ---- */
function viewLog() {
  const es = entriesOf(S.day);
  const T = totalsFor(es);
  const g = (k) => T.lo[IDX[k]];
  const estE = es.some((e) => energyEstimated(getFood(e.f)));
  const noE = T.n - T.cnt[0];
  const p = g('protein') * 4, c = g('carbohydrate') * 4, f = g('fat') * 9, tot = p + c + f;
  const pct = (x) => (tot > 0 ? Math.round(x / tot * 100) + '% of kcal' : '–');

  let nova = '';
  if (es.length) {
    const { by, sum } = novaStats(es);
    if (sum > 0 && by[1] + by[2] + by[3] + by[4] > 0) {
      nova = `<div class="banner">Ultra-processed (NOVA 4): <b>${fmt(by[4] / sum * 100)}%</b> of energy · NOVA 1–3: ${fmt((by[1] + by[2] + by[3]) / sum * 100)}% · unclassified: ${fmt(by.u / sum * 100)}%</div>`;
    }
  }

  const lostU = USDA_ERR ? S.log.filter((e) => e.d === S.day && e.f.startsWith('usda:')).length : 0;
  const lostD = DM_ERR ? S.log.filter((e) => e.d === S.day && e.f.startsWith('dm:')).length : 0;
  const dmWarn = lostD ? `<div class="banner">The dmBio food data could not be loaded (${esc(DM_ERR)}), so ${lostD} ${lostD === 1 ? 'entry is' : 'entries are'} hidden on this day. Check your internet connection and reload the app.</div>` : '';
  const usdaWarn = lostU ? `<div class="banner">The USDA food data could not be loaded (${esc(USDA_ERR)}), so ${lostU} ${lostU === 1 ? 'entry is' : 'entries are'} hidden on this day. Check your internet connection and reload the app.</div>` : '';
  const meals = MEALS.map((m) => {
    const list = es.filter((e) => e.m === m.id).sort(byTime);
    let mk = 0, mkn = 0;
    for (const e of list) { const fd = getFood(e.f), v = vecOf(fd).lo[0]; if (!Number.isNaN(v)) { mk += v * e.a / fd.basis.qty; mkn++; } }
    const rows = list.map((e) => {
      const food = getFood(e.f), v = vecOf(food).lo[0], k = e.a / food.basis.qty;
      const kt = Number.isNaN(v) ? '–' : (energyEstimated(food) ? '~' : '') + fmt(v * k);
      return `<button class="entry" data-act="edit-entry" data-id="${e.id}">${avatar(food.name)}
        <span class="entry-main"><span class="entry-name">${esc(cap(food.name))}</span><span class="entry-sub">${timeOf(e) ? `<span class="entry-time">${timeOf(e)}</span> · ` : ''}${esc(amountText(e, food))} · ${esc(food.brand ? food.brand + ' · ' : '')}${srcTag(food)}</span></span>
        <span class="entry-kcal">${kt}<small>kcal</small></span></button>`;
    }).join('');
    return `<section class="meal"><div class="meal-h"><h3>${m.name}</h3>${mkn ? `<span class="mk">${fmt(mk)} kcal</span>` : ''}
      <button class="icon-btn sm" data-act="add" data-meal="${m.id}" aria-label="Log food in ${m.name}">${IC.plus}</button></div>
      <div class="rows">${rows}</div></section>`;
  }).join('');

  const empty = !S.log.length ? `<div class="card" style="margin-top:16px"><div class="card-t">Log your first food</div>
    <p class="muted small" style="margin-top:6px">Tap <b>Log food</b>. Search in English or Hungarian (egg, tojás, bread, kenyér, avocado), scan a barcode, or look a product up in Open Food Facts. Use <b>Create food</b> to enter your own from a label.</p></div>` : '';

  return `<section class="hero">
      <div class="hero-label">Energy</div>
      <div class="hero-num">${es.length ? (estE ? '~' : '') + fmt(T.lo[0]) : '0'}<small>kcal</small></div>
      ${noE > 0 ? `<span class="chip warn">Lower estimate · ${noE} without energy data</span>` : `<span class="chip">${es.length ? plural(es.length, 'item') + ' logged' : 'Nothing logged yet'}</span>`}
    </section>
    <div class="actions">
      <button class="act primary" data-act="add"><span class="act-c">${IC.plus}</span>Log food</button>
      <button class="act" data-act="scan"><span class="act-c">${IC.scan}</span>Scan</button>
      <button class="act" data-act="new-food"><span class="act-c">${IC.tag}</span>Create food</button>
    </div>
    <div class="card">
      <div class="bar" role="img" aria-label="Energy split between protein, carbohydrate and fat">${tot > 0
    ? `<i style="width:${p / tot * 100}%;background:var(--c-p)"></i><i style="width:${c / tot * 100}%;background:var(--c-c)"></i><i style="width:${f / tot * 100}%;background:var(--c-f)"></i>` : ''}</div>
      <div class="mtiles">
        <div><div class="mt-name"><span class="dot" style="background:var(--c-p)"></span>Protein</div><div class="mt-val">${fmt(g('protein'))}<small>g</small></div><div class="mt-pct">${pct(p)}</div></div>
        <div><div class="mt-name"><span class="dot" style="background:var(--c-c)"></span>Carbohydrate</div><div class="mt-val">${fmt(g('carbohydrate'))}<small>g</small></div><div class="mt-pct">${pct(c)}</div></div>
        <div><div class="mt-name"><span class="dot" style="background:var(--c-f)"></span>Fat</div><div class="mt-val">${fmt(g('fat'))}<small>g</small></div><div class="mt-pct">${pct(f)}</div></div>
      </div>
      <div class="mini"><span>Fibre <b>${fmt(g('fibres'))} g</b></span><span>Sugars <b>${fmt(g('sugars'))} g</b></span><span>Salt <b>${fmt(g('salt'))} g</b></span></div>
    </div>
    ${usdaWarn}${dmWarn}
    ${estE ? '<div class="banner">~ means the energy is an estimate, not a label value: calculated from protein, carbohydrate and fat (generic food data, Atwater factors), or marked as an estimate in a food you made.</div>' : ''}
    ${nova}${empty}${meals}`;
}

/* ---- Nutrients ---- */
function viewNutr() {
  const es = entriesOf(S.day);
  if (!es.length) return '<div class="card" style="margin-top:16px"><div class="card-t">Nothing logged for this day</div><p class="muted small" style="margin-top:6px">The daily nutrient summary is built from the foods you log in the Diary tab.</p><button class="btn primary" data-act="tab" data-tab="log" style="margin-top:14px">Go to Diary</button></div>';
  const T = totalsFor(es);
  const note = '<div class="banner">Missing data is not zero. Totals only include items that have data (the badge on the right shows how many items out of all), so they are lower estimates. Ranges come from values reported as “&lt; x” (below the detection limit).</div>'
    + (T.est.some((x) => x > 0) ? '<div class="banner">A <b>~</b> in front of a value means that part of it is an estimate, not a label value: energy calculated from protein, carbohydrate and fat, dmBio values estimated from the ingredient list, or values you marked as estimates in your own foods (for example from an AI answer). Open a row to see which items and how confident the estimate is.</div>' : '');
  const out = GROUPS.map(([gid, gname, open]) => {
    const idxs = KEYS.map((_, i) => i).filter((i) => groupOf(i) === gid);
    if (!idxs.length) return '';
    const rows = idxs.map((i) => {
      const cnt = T.cnt[i], n = T.n, lo = T.lo[i], hi = T.hi[i], unit = UNITS[i];
      const range = hi - lo > Math.max(lo * 0.1, 1e-9);
      const val = cnt === 0 ? '<span class="nval none">no data</span>'
        : `<span class="nval">${cnt < n ? '≥ ' : ''}${T.est[i] ? '~' : ''}${range ? fmt(lo) + '–' + fmt(hi) : fmt(lo)}<em>${esc(unit)}</em></span>`;
      const cls = cnt === n ? 'full' : cnt === 0 ? 'none' : 'part';
      const miss = T.missing[i];
      const estd = T.estNames[i];
      const detail = (miss.length ? `<div class="ndetail">No data for: ${esc([...new Set(miss)].map(cap).join('; '))}</div>` : '<div class="ndetail">Every item has data.</div>')
        + (estd.length ? `<div class="ndetail">Estimate, not a label value: ${esc([...new Set(estd)].map(cap).join('; '))}</div>` : '');
      return `<details class="nrow"><summary><span>${esc(labelOf(i))}</span>${val}<span class="pill ${cls}">${cnt}/${n}</span></summary>${detail}</details>`;
    }).join('');
    const list = `<div class="nlist">${rows}</div>`;
    return open ? `<section class="group"><h3>${gname}</h3>${list}</section>`
      : `<details class="group"><summary>${gname}</summary>${list}</details>`;
  }).join('');
  return note + `<div id="nova">${novaHtml(es)}</div>` + out;
}

/* NOVA summary card and the list for setting a group by hand. Drawn again on its own after every tap (see novaTap). */
function novaHtml(es) {
  const s = novaStats(es);
  const vals = [s.by[1], s.by[2], s.by[3], s.by[4], s.by.u];
  const pc = sharePct(vals, s.sum);
  const names = [...NOVA.map(([n, name]) => `NOVA ${n}: ${name}`), 'Unclassified'];
  const pcText = (i) => (pc[i] === 0 && vals[i] > 0 ? '<1%' : pc[i] + '%');
  const colors = ['var(--n1)', 'var(--n2)', 'var(--n3)', 'var(--n4)', 'var(--n0)'];
  const bar = s.sum > 0 ? vals.map((v, i) => (v > 0 ? `<i style="width:${v / s.sum * 100}%;background:${colors[i]}"></i>` : '')).join('') : '';
  const label = s.sum > 0 ? 'Energy by NOVA group: ' + names.map((n, i) => `${n} ${pcText(i)}`).join(', ') : 'No energy data to split by NOVA group';
  const rows = names.map((nm, i) => {
    const head = i < 4 ? `<b>NOVA ${i + 1}</b> ${esc(NOVA[i][1])}` : '<b>Unclassified</b> no group set yet';
    return `<div class="nova-row"><span class="dot" style="background:${colors[i]}"></span><span class="nova-name">${head}</span>
      <span class="nova-val"><b>${s.sum > 0 ? pcText(i) : '–'}</b><small>${vals[i] > 0 ? fmt(vals[i]) + ' kcal' : ''}</small></span></div>`;
  }).join('');
  const un = s.items.filter((x) => !x.g), done = s.items.filter((x) => x.g);
  const itemHtml = (x) => {
    const sub = x.known ? fmt(x.kcal) + ' kcal today' : 'no energy data';
    return `<div class="nova-item"><div class="nova-item-main"><span class="nova-item-name">${esc(cap(x.food.name))}</span><span class="nova-item-sub">${esc(sub)}</span></div>
      <div class="nova-btns" role="group" aria-label="NOVA group of ${esc(x.food.name)}">${[1, 2, 3, 4].map((n) =>
    `<button type="button" class="nbtn" data-act="nova-set" data-id="${esc(x.food.id)}" data-v="${n}" aria-pressed="${x.g === n}" aria-label="NOVA ${n}: ${esc(NOVA[n - 1][1])}">${n}</button>`).join('')}</div></div>`;
  };
  const coverage = `${done.length} of ${plural(s.items.length, 'food')} classified.${s.noEnergy ? ` ${s.noEnergy} ${s.noEnergy === 1 ? 'entry has' : 'entries have'} no energy data and ${s.noEnergy === 1 ? 'is' : 'are'} not counted in the shares.` : ''}`;
  return `<div class="card nova-card">
      <div class="card-t">Food processing (NOVA)</div>
      <p class="muted small" style="margin:6px 0 14px">Share of today’s energy by how processed the foods are. Only items with energy data count.</p>
      <div class="bar" role="img" aria-label="${esc(label)}">${bar}</div>
      <div class="nova-rows">${rows}</div>
      <p class="muted small" style="margin:12px 0 0">${coverage}</p>
    </div>
    <details class="fold" id="novafold" ${novaOpen ? 'open' : ''}><summary>Set NOVA groups${un.length ? ` · ${un.length} unclassified` : ''}</summary>
      <p class="hint" style="margin:0 0 12px">Tap 1–4 for a food. 1 = minimal, 2 = culinary ingredient, 3 = processed, 4 = ultra-processed. Your choice is saved for the food, so you set it only once. Tap the chosen number again to clear it.</p>
      ${un.length ? `<h4 class="nova-h">Unclassified (${un.length})</h4>${un.map(itemHtml).join('')}` : '<p class="small" style="margin:0 0 12px">Every food of the day has a group.</p>'}
      ${done.length ? `<h4 class="nova-h">Classified (${done.length})</h4>${done.map(itemHtml).join('')}` : ''}
    </details>
    <details class="fold"><summary>What are the NOVA groups?</summary>
      <div class="nova-def">${NOVA.map(([n, name, ex]) => `<p><b>${n} · ${esc(name)}</b><br><span class="muted">${esc(cap(ex))}.</span></p>`).join('')}
      <p class="hint">NOVA sorts foods by how industrially they are processed, not by how healthy they are. A group is a judgement: ingredient lists and brands matter, so check it for your own foods.</p></div>
    </details>`;
}
function novaTap(id, v) {
  const f = getFood(id);
  if (!f) return;
  const before = novaOf(f), next = before === v ? null : v;
  setNova(f, next);
  refreshNova();
  const nm = cap(f.name.length > 38 ? f.name.slice(0, 37) + '…' : f.name);
  toast(next ? `${nm}: NOVA ${next}` : `${nm}: group cleared`, () => { setNova(f, before); refreshNova(); });
}
function refreshNova() {
  const el = $('#nova');
  if (el) el.innerHTML = novaHtml(entriesOf(S.day));
}

/* ---- My foods ---- */
function viewFoods() {
  return `<div class="row gap" style="margin:8px 0 14px"><button class="btn primary" data-act="new-food">${IC.plus.replace('<svg', '<svg width="18" height="18"')} Create food</button><button class="btn" data-act="ai-import">Paste from AI</button></div>
    <input type="search" class="search" enterkeyhint="search" id="ffilter" placeholder="Search my foods" value="${esc(S.filter)}" aria-label="Search my foods">
    <div id="flist" style="margin-top:12px">${foodListHtml()}</div>`;
}
const foodRow = (f, attr) => `<button class="item" ${attr}>${avatar(f.name)}
  <span class="item-main"><span class="item-name">${esc(cap(f.name))}</span><span class="item-sub"><span class="tag">${srcTag(f)}</span>${esc(f.brand || f.group || '')}</span></span>
  <span class="r"><b>${isG(f) ? (Number.isNaN(kcalPer(f)) ? 'no kcal' : (energyEstimated(f) ? '~' : '') + fmt(kcalPer(f)) + ' kcal') : '1 ' + esc(f.basis.unit)}</b>${isG(f) ? 'per 100 g · ' : ''}data ${trackedKnown(f)}/${TRACKED.length}</span></button>`;
function foodListHtml() {
  const toks = tokensOf(S.filter);
  const all = Object.values(S.foods).filter((f) => !toks.length || toks.every((t) => norm(f.name + ' ' + (f.brand || '')).includes(t)))
    .sort((a, b) => a.name.localeCompare(b.name, 'en'));
  if (!all.length) return `<p class="muted pad">${Object.keys(S.foods).length ? 'No matches.' : 'Your own foods and scanned products show up here.'}</p>`;
  return `<div class="rows">${all.map((f) => foodRow(f, `data-act="edit-food" data-id="${esc(f.id)}"`)).join('')}</div>`;
}

/* ---- Data ---- */
function viewData() {
  const b = S.meta.backup ? new Date(S.meta.backup).toLocaleString(LOC) : 'never';
  const tp = themePref();
  return `<div class="stack" style="margin-top:8px">
    <div class="card"><div class="card-t">Appearance</div>
      <p class="muted small" style="margin:6px 0 12px">Auto follows your phone’s light or dark setting. Light and Dark stay as you pick them.</p>
      <div class="seg" role="group" aria-label="Theme">${THEMES.map(([v, l]) => `<button data-act="theme" data-v="${v}" aria-pressed="${v === tp}">${l}</button>`).join('')}</div></div>
    <div class="card"><div class="card-t">Backup</div>
      <p class="muted small" style="margin:6px 0 14px">${SY.cfg ? 'Your data lives on this device and, through Sync, in your private GitHub repository.' : 'Your data lives only on this device, in this browser.'} Back up regularly and before switching devices. Last backup: ${esc(b)}.</p>
      <div class="row gap"><button class="btn primary" data-act="export-json">Save backup (JSON)</button><label class="btn" style="cursor:pointer">Restore from file<input type="file" id="importfile" accept="application/json,.json" hidden></label><label class="btn" style="cursor:pointer">Import foods (JSON)<input type="file" id="importfoods" accept="application/json,.json" hidden></label></div>
      <p class="muted small" style="margin:12px 0 0"><b>Restore from file</b> replaces everything in the app with the backup. <b>Import foods (JSON)</b> only adds foods to My foods from a file and never touches your diary.</p>
      <div id="fimp-msg" aria-live="polite"></div></div>
    ${syncCard()}
    <div class="card"><div class="card-t">For analysis</div>
      <p class="muted small" style="margin:6px 0 14px">Spreadsheet files (CSV, decimal points). An empty cell means no data, a 0 is a real zero. Some labels report a value as “&lt; x” (below the detection limit). Then the normal column holds the lowest possible value, 0, and the max-value column (its name ends in __max) holds x. A column whose name ends in __est marks values that are estimates, not label values (1 for an entry, a count of items for a day): estimated values of dmBio products, and values you marked as estimates in your own foods. The column estimate_confidence says how sure the estimate is. In the entries file, est_keys lists the estimated nutrients of that entry (separated by semicolons). In the daily totals file, est_share is the share of the day that is estimated, in percent: for every nutrient with data it takes the estimated part of the day’s amount, then averages those shares.</p>
      <div class="row gap"><button class="btn" data-act="export-entries">Entries (CSV)</button><button class="btn" data-act="export-days">Daily totals (CSV)</button></div></div>
    <div class="card"><div class="card-t">Storage</div>
      <p class="muted small" style="margin:6px 0 4px">Storage type: ${Store.mode === 'idb' ? 'IndexedDB' : 'localStorage (fallback)'}.</p>
      <p class="small" id="persist-state" style="margin:0 0 14px">Checking…</p>
      <button class="btn" data-act="persist">Request persistent storage</button></div>
    <div class="card"><div class="card-t">App version</div>
      <p class="muted small" style="margin:6px 0 14px">Nutrilog version <b>${esc(VERSION)}</b>. If a fix is published but you still see the old behaviour, tap the button: it reloads the app files. Your diary and foods stay untouched. Needs internet.</p>
      <button class="btn" data-act="refresh-app">Reload app files</button></div>
    <div class="card"><div class="card-t">Sources &amp; licences</div>
      <p class="small" style="margin:8px 0">Generic foods: Anses. 2020. Ciqual French food composition table. <a href="https://doi.org/10.5281/zenodo.4770202" target="_blank" rel="noopener">doi.org/10.5281/zenodo.4770202</a> (CC BY 4.0).</p>
      <p class="small" style="margin:8px 0">Generic foods (second source): U.S. Department of Agriculture, Agricultural Research Service. FoodData Central: Foundation Foods (April 2026) and SR Legacy (April 2018). <a href="https://fdc.nal.usda.gov" target="_blank" rel="noopener">fdc.nal.usda.gov</a> (U.S. public domain).</p>
      <p class="small" style="margin:8px 0">Packaged products (built in): dmBio products of dm Hungary, from the product pages on <a href="https://www.dm.hu" target="_blank" rel="noopener">dm.hu</a>. Energy and macronutrients come from dm’s nutrition tables (corrected where they were inconsistent). All other values are estimates calculated from the ingredient list with CIQUAL 2020 (dmBio estimate v3, 24 Oct 2026); the product page shows how confident each estimate is.</p>
      <p class="small" style="margin:8px 0">Packaged products (online): <a href="https://world.openfoodfacts.org" target="_blank" rel="noopener">Open Food Facts</a>, a community database, ODbL licence. Label data can be incomplete.</p>
      <p class="small muted" style="margin:8px 0">Barcode reader for browsers without a built-in one: ZXing-js, Apache 2.0 licence (ZXING-LICENSE.txt).</p>
      <p class="small muted" style="margin:8px 0">CIQUAL lists French market averages, USDA values describe the US market. This app is an information tool, not medical advice. Database: ${CAT ? CAT.foods.length : 0} CIQUAL foods, ${USDA.length} USDA foods, ${DMBIO.length} dmBio products, ${CAT ? CAT.nutrients.length : 0} nutrients.${USDA_ERR ? ` The USDA data could not be loaded (${esc(USDA_ERR)}).` : ''}${DM_ERR ? ` The dmBio data could not be loaded (${esc(DM_ERR)}).` : ''}</p></div>
  </div>`;
}

/* ================= food picker ================= */
function openPicker({ title = 'Log food', onlyGrams = false, onPick }) {
  const sh = openSheet(title, `
    <input id="q" type="search" class="search" inputmode="search" enterkeyhint="search" autocomplete="off" placeholder="Search: egg, tojás, bread, kenyér…" aria-label="Search foods">
    <div class="row gap"><button class="btn" data-a="scan">${IC.scan.replace('<svg', '<svg width="20" height="20"')} Scan barcode</button></div>
    <div id="res" aria-live="polite"></div>`);
  const q = $('#q', sh.el), res = $('#res', sh.el);
  let off = null, offMsg = '', notFound = false, huOnly = false, usdaLimit = 10, dmLimit = 10;
  const list = (arr, kind) => `<div class="rows">${arr.map((f) => foodRow(f, `data-pick="${esc(f.id)}" data-kind="${kind}"`)).join('')}</div>`;
  function paint() {
    const text = q.value.trim();
    let html = '';
    if (!text) {
      const seen = new Set(), rec = [];
      for (let i = S.log.length - 1; i >= 0 && rec.length < 12; i--) {
        const f = getFood(S.log[i].f);
        if (f && !seen.has(f.id) && (!onlyGrams || isG(f))) { seen.add(f.id); rec.push(f); }
      }
      html += rec.length ? `<h4>Recent foods</h4>${list(rec, 'x')}` : '<p class="muted">Start typing a food name in English or Hungarian, or scan a barcode.</p>';
    } else {
      const loc = searchLocal(text, onlyGrams);
      const ciq = searchCiqual(text);
      const usAll = searchUsda(text, usdaLimit + 1), us = usAll.slice(0, usdaLimit);
      const dmAll = searchDm(text, dmLimit + 1), dm = dmAll.slice(0, dmLimit);
      if (loc.length) html += `<h4>My foods &amp; saved products</h4>${list(loc, 'x')}`;
      if (dm.length) html += `<h4>dmBio (dm.hu products)</h4>${list(dm, 'x')}${dmAll.length > dm.length ? '<button class="btn block" data-a="more-dm" style="margin-top:8px">Show more dmBio results</button>' : ''}`;
      if (ciq.length) html += `<h4>CIQUAL (generic foods)</h4>${list(ciq, 'x')}`;
      if (us.length) html += `<h4>USDA (generic foods, US)</h4>${list(us, 'x')}${usAll.length > us.length ? '<button class="btn block" data-a="more-usda" style="margin-top:8px">Show more USDA results</button>' : ''}`;
      if (!loc.length && !dm.length && !ciq.length && !us.length) html += '<p class="muted">No local match. Try another word, or search Open Food Facts.</p>';
      if (/^\d{8,14}$/.test(text.replace(/\s/g, ''))) html += `<button class="btn block primary" data-a="code" style="margin-top:12px">Look up barcode: ${esc(text.replace(/\s/g, ''))}</button>`;
    }
    if (text) {
      const shown = text.length > 26 ? text.slice(0, 26) + '…' : text;
      html += `<div class="offbox"><h4>Open Food Facts (packaged products)</h4>
        <button class="btn block" data-a="off">Search “${esc(shown)}” in Open Food Facts</button>
        <label class="chk"><input type="checkbox" id="huonly" ${huOnly ? 'checked' : ''}> Only products sold in Hungary</label></div>`;
    }
    if (off) html += off.length ? list(off, 'off') : '<p class="muted">No results.</p>';
    if (offMsg) html += `<p class="note">${esc(offMsg)}</p>`;
    html += `<div class="row gap" style="margin-top:16px"><button class="btn${notFound ? ' primary' : ''}" data-a="new">+ Create food from label</button><button class="btn" data-a="ai">Paste from AI</button></div>`;
    res.innerHTML = html;
  }
  async function runOff(code) {
    offMsg = ''; notFound = false;
    const text = q.value.trim();
    if (!text) { offMsg = 'Type a name or a barcode first.'; paint(); return; }
    if (code) {
      /* a product you saved earlier (same barcode) wins, and works offline */
      const variants = codeVariants(code);
      const mine = Object.values(S.foods).find((f) => f.barcode && variants.includes(f.barcode));
      if (mine) { off = null; paint(); pick(mine); return; }
      /* so does a dmBio product: it is built into the app and needs no internet */
      const dmHit = DMBIO.find((f) => variants.includes(f.barcode));
      if (dmHit) { off = null; paint(); pick(dmHit); return; }
    }
    res.insertAdjacentHTML('afterbegin', '<p class="muted">Searching Open Food Facts…</p>');
    try {
      if (code) {
        const food = await offProduct(code);
        if (!food) {
          off = []; notFound = true;
          offMsg = `Open Food Facts does not have barcode ${code}. It is a community database, so some products are missing, especially supplements and items from outside Europe. Tap “Create food from label” and copy the values from the package. The barcode is filled in, so the next scan finds the product in your own foods. If the number is not the one printed under the barcode, the camera misread it: scan again or type it.`;
          paint(); return;
        }
        off = [food]; paint();
        const kept = keepOff(food);
        if (!Object.keys(kept.n).length) offMsg = 'Open Food Facts has no nutrition values for this product. Fill them in from the label: open My foods and tap the product.';
        pick(kept);
      } else {
        off = await offSearch(text, huOnly);
        if (!off.length && huOnly) offMsg = 'No results among products sold in Hungary. Untick the box to search worldwide.';
        paint();
      }
    } catch (err) {
      offMsg = err instanceof TypeError || !err || !err.message ? 'Could not reach Open Food Facts. Check your internet connection.' : err.message;
      paint();
    }
  }
  function pick(food) { onPick(food); }
  q.addEventListener('input', () => { notFound = false; usdaLimit = 10; dmLimit = 10; paint(); });
  sh.el.addEventListener('change', (e) => { if (e.target.id === 'huonly') huOnly = e.target.checked; });
  sh.el.addEventListener('click', (ev) => {
    const b = ev.target.closest('button');
    if (!b) return;
    if (b.dataset.pick) {
      let food = b.dataset.kind === 'off' ? (off || []).find((f) => f.id === b.dataset.pick) : getFood(b.dataset.pick);
      if (b.dataset.kind === 'off' && food) food = keepOff(food);
      if (food) pick(food);
    } else if (b.dataset.a === 'more-usda') { usdaLimit += 30; paint(); }
    else if (b.dataset.a === 'more-dm') { dmLimit += 30; paint(); }
    else if (b.dataset.a === 'off') runOff(null);
    else if (b.dataset.a === 'code') runOff(q.value.replace(/\s/g, ''));
    else if (b.dataset.a === 'scan') scanBarcode((code) => { q.value = code; paint(); runOff(code); });
    else if (b.dataset.a === 'new') openFoodEditor(null, { name: /\D/.test(q.value) ? q.value.trim() : '', barcode: /^\d{8,14}$/.test(q.value.trim()) ? q.value.trim() : '', after: (f) => pick(f) });
    else if (b.dataset.a === 'ai') openAiImport({ onSaved: (f) => pick(f) });
  });
  q.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); const t = q.value.replace(/\s/g, ''); if (/^\d{8,14}$/.test(t)) runOff(t); } });
  paint();
  /* iPhone: the keyboard only opens if focus() runs inside the tap that opened the sheet; elsewhere do it with a short delay */
  if (TOUCH) { try { q.focus({ preventScroll: true }); } catch { /* the field can be tapped */ } } else setTimeout(() => q.focus(), 60);
  return sh;
}

/* ================= barcode scanner ================= */
/* Why it looks like this (found with a real photo of a dmBio package):
   - ZXing-js reads EAN codes wrongly when the barcode is only about 2 camera pixels per bar width, and such a wrong number can still pass the EAN
     check digit (6072101076189 and 8070167076189 both do, the real code is 4070765076189). iOS gives only 640x480 unless a size is asked for, so the camera is asked
     for full HD, and a number is accepted only after it has been read 3 times. 2 times are enough when the bars are wide (2.5 camera pixels or more per
     bar width: a sharp, close barcode) and with the browser's own BarcodeDetector.
   - Only shop barcodes (EAN-13, EAN-8, UPC-A, UPC-E) are read. With all formats on, the QR code that dm prints next to the barcode was read as a "barcode".
     Note: MultiFormatReader.decode(image, hints) forgets the hints after every call, so they are passed in every call.
   - Voting cannot help when the same wrong number is read again and again (it happens at about 1.3 bar pixels), so the resolution matters most.
   - ZXing's own camera loop looks every 500 ms; this loop looks about every 120 ms. */
function scanBarcode(onCode) {
  const sh = openSheet('Scan barcode', `
    <video id="scan-v" playsinline muted autoplay></video>
    <p class="muted small" id="scan-msg">Point the camera at the barcode. Your browser will ask for camera permission. This only works on HTTPS.</p>
    <div class="row gap" style="flex-wrap:nowrap"><input id="scan-manual" type="text" inputmode="numeric" placeholder="or type the number" style="flex:1" aria-label="Barcode number"><button class="btn primary" id="scan-go">Look up</button></div>`);
  const video = $('#scan-v', sh.el), msg = $('#scan-msg', sh.el);
  let stream = null, timer = null, done = false;
  const wait = (ms) => new Promise((r) => { timer = setTimeout(r, ms); });
  const stop = () => { done = true; clearTimeout(timer); if (stream) stream.getTracks().forEach((t) => t.stop()); };
  sh.onClose = stop;
  const found = (code) => { if (done) return; stop(); sh.close(); onCode(String(code)); };
  /* a number counts when it was read `need` times among the last 10 readings and no other number was read twice */
  const reads = [];
  const vote = (code, need) => {
    reads.push(code); if (reads.length > 10) reads.shift();
    const count = (c) => reads.filter((x) => x === c).length;
    if (count(code) >= need && !reads.some((x) => x !== code && count(x) >= 2)) found(code);
  };
  $('#scan-go', sh.el).onclick = () => { const v = $('#scan-manual', sh.el).value.replace(/\s/g, ''); if (/^\d{6,14}$/.test(v)) found(v); else msg.textContent = 'Barcodes have 8–14 digits.'; };
  const HELP = 'Hold the phone 10–20 cm from the barcode, flat and steady, with good light.';
  async function openCamera() {
    stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1080 } }, audio: false });
    if (done) { stream.getTracks().forEach((t) => t.stop()); return false; }
    video.srcObject = stream;
    await video.play().catch(() => {});
    try {   // sharp close-ups: continuous autofocus where the browser allows it (not on iPhone, where it is the default)
      const track = stream.getVideoTracks()[0], caps = track.getCapabilities ? track.getCapabilities() : {};
      if (caps.focusMode && caps.focusMode.includes('continuous')) await track.applyConstraints({ advanced: [{ focusMode: 'continuous' }] });
    } catch { /* the default focus is fine */ }
    return true;
  }
  (async () => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { video.hidden = true; msg.textContent = 'This browser cannot open the camera (HTTPS is required). Type the barcode number instead.'; return; }
    try {
      const t0 = Date.now();
      const slow = () => { if (!done && Date.now() - t0 > 10000) msg.textContent = 'Still looking. Move the phone a little closer or further away, add light, or type the number below.'; };
      if ('BarcodeDetector' in window) {
        if (!(await openCamera())) return;
        msg.textContent = HELP;
        const det = new window.BarcodeDetector({ formats: ['ean_13', 'ean_8', 'upc_a', 'upc_e'] });
        while (!done) {
          try { const r = await det.detect(video); if (r[0]) vote(r[0].rawValue, 2); } catch { /* next frame */ }
          slow(); await wait(120);
        }
      } else {
        msg.textContent = 'Loading scanner…';
        await loadScript('zxing.min.js');
        if (done) return;
        const Z = window.ZXing;
        const formats = [Z.BarcodeFormat.EAN_13, Z.BarcodeFormat.EAN_8, Z.BarcodeFormat.UPC_A, Z.BarcodeFormat.UPC_E];
        const hints = new Map([[Z.DecodeHintType.POSSIBLE_FORMATS, formats]]);                                  // quick look: about 20 ms per HD frame
        const hardHints = new Map([[Z.DecodeHintType.POSSIBLE_FORMATS, formats], [Z.DecodeHintType.TRY_HARDER, true]]);   // thorough look: every row, about 250 ms, so only on every 3rd frame that fails
        const reader = new Z.MultiFormatReader();   // decode(image, hints) must get the hints every time: it resets them on each call
        if (!(await openCamera())) return;
        msg.textContent = HELP;
        const canvas = document.createElement('canvas'), g = canvas.getContext('2d', { willReadFrequently: true });
        let misses = 0;
        while (!done) {
          const t1 = performance.now();
          if (video.readyState >= 2 && video.videoWidth) {
            if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) { canvas.width = video.videoWidth; canvas.height = video.videoHeight; }
            g.drawImage(video, 0, 0);
            const bitmap = new Z.BinaryBitmap(new Z.HybridBinarizer(new Z.HTMLCanvasElementLuminanceSource(canvas)));
            let r = null;
            try { r = reader.decode(bitmap, hints); } catch {
              if (++misses % 3 === 0) { try { r = reader.decode(bitmap, hardHints); } catch { /* no readable barcode in this frame */ } }
            }
            if (r) {
              /* width of one bar in camera pixels: the two result points are the middles of the start and end guards, 92 bar widths apart */
              const p = r.getResultPoints(), f = r.getBarcodeFormat();
              const bar = p && p.length >= 2 && (f === Z.BarcodeFormat.EAN_13 || f === Z.BarcodeFormat.UPC_A) ? Math.hypot(p[1].getX() - p[0].getX(), p[1].getY() - p[0].getY()) / 92 : 0;
              vote(r.getText(), bar >= 2.5 ? 2 : 3);
            }
          }
          slow(); await wait(Math.max(30, 120 - (performance.now() - t1)));
        }
      }
    } catch (err) {
      video.hidden = true;
      msg.textContent = (err && err.name === 'NotAllowedError' ? 'Camera access was blocked for this site.' : 'Could not start the camera' + (err && err.name && err.name !== 'Error' ? ' (' + err.name + ')' : '') + '.') + ' Type the barcode number instead.';
    }
  })();
}
function loadScript(src) {
  return new Promise((res, rej) => {
    const s = document.createElement('script');
    s.src = src; s.onload = res; s.onerror = () => rej(new Error('scanner'));
    document.head.append(s);
  });
}

/* ================= amount sheet (new entry / edit entry) ================= */
function portionsOf(f) { return [...(f.portions || []), ...(S.meta.portions[f.id] || [])]; }
/* Which portion a new entry starts with: the serving of a packaged product, or a portion the person saved. USDA household measures only appear as buttons: a start of 100 g is clearer than "1 cup". */
const startPortion = (f) => [...(f.src === 'usda' || f.src === 'dmbio' ? [] : f.portions || []), ...(S.meta.portions[f.id] || [])][0];
/* What a person should know before trusting a dmBio product: which values are from the dm label, which are estimated, how sure the estimate is. */
function dmInfo(f) {
  if (f.src !== 'dmbio') return '';
  const lab = [...f._lab].sort((a, b) => a - b).map(labelOf);
  const ml = f.portions.some((p) => /^100 ml$/.test(p.label)), dry = f.portions.some((p) => /prepared/.test(p.label));
  return `<details class="fold"><summary>${f.q === 'n' ? 'No micronutrient estimate' : 'Estimated values · confidence ' + CONF[f.q]}</summary>
    <p class="small" style="margin:0 0 8px">${lab.length ? `From the dm.hu label: ${esc(lab.join(', ').toLowerCase())}.` : 'dm.hu has no nutrition table for this product, so there are no label values.'}
      ${f.q === 'n' ? ' No other nutrient is estimated.' : ` Every other value is an <b>estimate</b> from the ingredient list (CIQUAL 2020 raw ingredients). Confidence of the estimate: <b>${CONF[f.q]}</b>.`}
      ${f.fortified ? ' The product may be <b>fortified</b> with vitamins or minerals. The estimate is made from the raw ingredients, so the estimated vitamin and mineral values can be <b>too low</b>.' : ''}</p>
    ${ml ? '<p class="small muted" style="margin:0 0 8px">The values are per 100 g, not per 100 ml. The “100 ml” button enters the weight of 100 ml.</p>' : ''}
    ${dry ? '<p class="small muted" style="margin:0 0 8px">The values are for 100 g of the dry product. The “prepared” buttons enter the grams of powder that are in that amount of the made-up soup or drink.</p>' : ''}
    <p class="small" style="margin:0 0 8px"><a href="https://www.dm.hu/p/d/${esc(f.url)}" target="_blank" rel="noopener">Open on dm.hu</a></p>
    ${f.info ? `<p class="hint" style="margin:0 0 12px">Note from the estimate file (Hungarian): ${esc(f.info)}</p>` : ''}</details>`;
}
/* The same kind of note for a food you made (or imported from an AI answer): which values are estimates, how sure the estimate is, the fortified warning and your note. */
function ownInfo(f) {
  if (f._cells || f.src === 'dmbio') return '';
  const v = vecOf(f);
  const names = [...estSet(f)].filter((i) => !Number.isNaN(v.lo[i])).sort((a, b) => a - b).map(labelOf);
  if (!names.length && !f.fortified) return '';
  const conf = f.q ? CONF[f.q] : 'not set';
  return `<details class="fold"><summary>${names.length ? 'Estimated values: ' + names.length + ' · confidence ' + conf : 'May be fortified'}</summary>
    <p class="small" style="margin:0 0 8px">${names.length ? `<b>Estimates, not label values:</b> ${esc(names.join(', ').toLowerCase())}. Confidence of the estimate: <b>${conf}</b>. Every other value is from the label.` : ''}
      ${f.fortified ? ' The product may be <b>fortified</b> with vitamins or minerals. Vitamin and mineral values estimated from raw ingredients can be <b>too low</b>.' : ''}</p>
    ${f.note ? `<p class="hint" style="margin:0 0 12px;overflow-wrap:anywhere">Note: ${esc(f.note)}</p>` : ''}</details>`;
}
function openAmount({ food, entry, meal, afterAdd }) {
  const unitG = isG(food);
  const start = entry ? entry.a : (S.meta.last[food.id] ?? (startPortion(food) ? startPortion(food).grams : unitG ? 100 : 1));
  const chips = (unitG ? [...portionsOf(food).map((p) => [p.label, p.grams]), ...[10, 30, 50, 100, 200].map((g) => [g + ' g', g])] : [0.5, 1, 2, 3].map((x) => [x + ' ' + food.basis.unit, x]));
  const startTime = (entry && timeOf(entry)) || hm(new Date());   // new entry: now; existing entry: the saved time
  const sh = openSheet(entry ? 'Edit entry' : 'Amount', `
    <div class="row gap" style="flex-wrap:nowrap">${avatar(food.name)}<div style="min-width:0"><b>${esc(cap(food.name))}</b><br><span class="muted small">${esc(food.brand || '')} ${esc(srcTag(food))}${unitG ? '' : ' · unit: ' + esc(food.basis.unit)}</span></div></div>
    <label class="f">Amount (${esc(food.basis.unit)})<input type="text" inputmode="decimal" enterkeyhint="done" id="amt" value="${esc(String(start))}"></label>
    <p class="note field-err" id="amterr" role="alert" hidden>Enter an amount greater than 0.</p>
    <div class="chips" id="chips">${chips.map(([l, v]) => `<button class="chip-btn" data-v="${v}">${esc(l)}</button>`).join('')}</div>
    ${unitG ? '<button class="chip-btn accent" id="saveportion" style="justify-self:start">+ Save as portion</button>' : ''}
    <div class="grid2">
      <label class="f">Meal<select id="meal">${MEALS.map((m) => `<option value="${m.id}" ${m.id === (entry ? entry.m : meal) ? 'selected' : ''}>${m.name}</option>`).join('')}</select></label>
      <label class="f">Time (24 h)<input type="text" id="tm" inputmode="numeric" enterkeyhint="done" autocomplete="off" autocorrect="off" spellcheck="false" maxlength="5" placeholder="HH:MM" value="${startTime}"></label>
    </div>
    <p class="note field-err" id="tmerr" role="alert" hidden>Enter a time in 24-hour form, for example 13:45.</p>
    <div class="card" id="prev"></div>
    ${dmInfo(food)}${ownInfo(food)}
    <div class="row gap sheet-actions">${entry ? '<button class="btn danger" id="del">Delete</button>' : ''}${food._cells ? '' : '<button class="btn" id="editfood">Edit food</button>'}<span style="flex:1"></span><button class="btn primary" id="ok"></button></div>`);
  const amt = $('#amt', sh.el), ok = $('#ok', sh.el), amterr = $('#amterr', sh.el);
  const val = () => { const v = num(amt.value); return Number.isFinite(v) && v > 0 ? v : NaN; };
  function prev() {
    const a = val(), v = vecOf(food);
    ok.textContent = (entry ? 'Save' : 'Add') + (Number.isNaN(a) ? '' : ' ' + fmt(a) + ' ' + food.basis.unit);
    if (Number.isNaN(a)) { $('#prev', sh.el).innerHTML = '<span class="muted">Enter a positive number.</span>'; return; }
    const k = a / food.basis.qty, g = (key) => v.lo[IDX[key]] * k;
    const known = trackedKnown(food);
    $('#prev', sh.el).innerHTML = `<div class="card-t">${Number.isNaN(v.lo[0]) ? 'no energy data' : (energyEstimated(food) ? '~' : '') + fmt(v.lo[0] * k) + ' kcal'}</div>
      <div class="muted small" style="margin-top:4px">protein ${fmt(g('protein'))} g · carbohydrate ${fmt(g('carbohydrate'))} g · fat ${fmt(g('fat'))} g · fibre ${fmt(g('fibres'))} g</div>
      <div class="small" style="margin-top:8px">Data for <b>${known}</b> of the ${TRACKED.length} tracked nutrients${trackedEst(food) ? ` (<b>${trackedEst(food)}</b> of them estimated, not from a label)` : ''}${known < TRACKED.length * 0.6 ? ' <span style="color:var(--warn)">(few — micronutrient totals will be incomplete)</span>' : ''}</div>`;
  }
  amt.addEventListener('input', () => { amterr.hidden = true; amt.removeAttribute('aria-invalid'); prev(); });
  $('#chips', sh.el).addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) { amt.value = String(b.dataset.v); amterr.hidden = true; prev(); } });
  const sp = $('#saveportion', sh.el);
  if (sp) sp.onclick = () => {
    const a = val();
    if (Number.isNaN(a)) { amterr.hidden = false; amt.focus(); return; }
    askText({
      title: 'Save as portion', label: 'Portion name (e.g. 1 piece, 1 tbsp)', value: '1 piece', okLabel: 'Save portion',
      onOk: (label) => {
        (S.meta.portions[food.id] = S.meta.portions[food.id] || []).push({ label, grams: a });
        save(); toast('Portion saved: ' + label); sh.close(); openAmount({ food, entry, meal, afterAdd });
      },
    });
  };
  const tm = $('#tm', sh.el), tmerr = $('#tmerr', sh.el);
  tm.addEventListener('input', () => { tm.value = shapeHm(tm.value); tmerr.hidden = true; tm.removeAttribute('aria-invalid'); });
  tm.addEventListener('blur', () => { tm.value = normHm(tm.value); });
  tm.addEventListener('focus', () => setTimeout(() => { try { tm.setSelectionRange(0, tm.value.length); } catch { /* ignore */ } }, 40));
  tm.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); ok.click(); } });
  ok.onclick = () => {
    const a = val(), tmv = normHm(tm.value);
    const badTime = !validHm(tmv);
    if (badTime) { tmerr.hidden = false; tm.setAttribute('aria-invalid', 'true'); }   // no focus() on the time field: on iOS it can stay "focused" without opening the picker
    if (Number.isNaN(a)) { amterr.hidden = false; amt.setAttribute('aria-invalid', 'true'); amt.focus(); return; }
    if (badTime) { tmerr.scrollIntoView({ block: 'center' }); return; }
    const m = $('#meal', sh.el).value;
    const mealName = (MEALS.find((x) => x.id === m) || {}).name;
    if (entry) { entry.a = a; entry.m = m; entry.tm = tmv; } else S.log.push({ id: uid(), d: S.day, m, f: food.id, a, t: Date.now(), tm: tmv });
    S.meta.last[food.id] = a;
    save(); sh.close(); render();
    toast(entry ? `Updated: ${cap(food.name)}, ${fmt(a)} ${food.basis.unit}` : `Added: ${cap(food.name)}, ${fmt(a)} ${food.basis.unit} to ${mealName}`);
    if (afterAdd) afterAdd();
  };
  const del = $('#del', sh.el);
  if (del) del.onclick = () => {
    const i = S.log.indexOf(entry), copy = { ...entry };
    S.log.splice(i, 1); save(); sh.close(); render();
    toast('Deleted', () => { S.log.splice(Math.min(i, S.log.length), 0, copy); save(); render(); });
  };
  const ef = $('#editfood', sh.el);
  if (ef) ef.onclick = () => openFoodEditor(food, { after: () => { sh.close(); render(); } });
  prev();
  /* The value is always visible in the field. Computers: focus and select it, so typing replaces it.
     Touch screens: no focus() by hand (on an iPhone it leaves the field "focused" without a keyboard);
     the person taps the field and the number is selected, where the browser allows it. */
  amt.addEventListener('focus', () => setTimeout(() => { try { amt.setSelectionRange(0, amt.value.length); } catch { /* ignore */ } }, 40));
  amt.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); ok.click(); } });
  if (!TOUCH) setTimeout(() => { amt.focus(); amt.select(); }, 60);
  else if (document.activeElement && document.activeElement !== document.body) document.activeElement.blur();
}

/* In-app replacements for window.confirm and window.prompt: native dialogs freeze the page on some browsers and look foreign. */
function askConfirm({ title, text, okLabel = 'OK', danger = false, onOk }) {
  const d = openSheet(title, `<p>${esc(text)}</p><div class="row gap sheet-actions"><button class="btn" data-dx>Cancel</button><span style="flex:1"></span><button class="btn ${danger ? 'danger' : 'primary'}" data-ok>${esc(okLabel)}</button></div>`);
  $('[data-dx]', d.el).onclick = () => d.close();
  $('[data-ok]', d.el).onclick = () => { d.close(); onOk(); };
  return d;
}
function askText({ title, label, value = '', okLabel = 'Save', onOk }) {
  const d = openSheet(title, `<label class="f">${esc(label)}<input type="text" enterkeyhint="done" id="ask-v" value="${esc(value)}" maxlength="40"></label>
    <p class="note field-err" id="ask-err" role="alert" hidden>Type a name first.</p>
    <div class="row gap sheet-actions"><button class="btn" data-dx>Cancel</button><span style="flex:1"></span><button class="btn primary" data-ok>${esc(okLabel)}</button></div>`);
  const inp = $('#ask-v', d.el);
  const go = () => { const v = inp.value.trim().slice(0, 40); if (!v) { $('#ask-err', d.el).hidden = false; inp.focus(); return; } d.close(); onOk(v); };
  $('[data-dx]', d.el).onclick = () => d.close();
  $('[data-ok]', d.el).onclick = go;
  inp.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); go(); } });
  inp.addEventListener('input', () => { $('#ask-err', d.el).hidden = true; });
  if (!TOUCH) setTimeout(() => { inp.focus(); inp.select(); }, 60);
  return d;
}

function addFlow(meal) {
  let pk = null;
  pk = openPicker({ onPick: (food) => openAmount({ food, meal, afterAdd: () => pk && pk.close() }) });
  return pk;
}

/* ================= food editor (from a label, or to fix an Open Food Facts product) ================= */
function parseInput(s) {
  const t = String(s).trim().replace(',', '.');
  if (t === '') return { empty: true };
  if (t[0] === '<') { const x = parseFloat(t.slice(1)); return Number.isFinite(x) && x >= 0 ? { v: '<' + x } : { err: true }; }
  const x = Number(t);
  return Number.isFinite(x) && x >= 0 ? { v: x } : { err: true };
}
const ESSENTIAL = ['kcal', 'protein', 'carbohydrate', 'sugars', 'fat', 'fa_saturated', 'fibres', 'salt'];
function nutField(food, i) {
  const cur = food && food.n ? food.n[KEYS[i]] : undefined;
  const shown = cur === undefined || cur === null ? '' : String(cur);
  return `<div class="nin"><label for="n_${KEYS[i]}">${esc(labelOf(i))}</label><input type="text" inputmode="decimal" id="n_${KEYS[i]}" data-k="${KEYS[i]}" value="${esc(shown)}" placeholder="–"><span class="u">${esc(UNITS[i])}</span><button type="button" class="est-btn" data-est="${KEYS[i]}" aria-pressed="false" hidden>~</button></div>`;
}
function nutInputs(food) {
  const has = (i) => food && food.n && food.n[KEYS[i]] != null;
  const ess = ESSENTIAL.map((k) => IDX[k]).filter((i) => i !== undefined);
  let moreHas = false;
  const groups = GROUPS.map(([gid, gname]) => {
    const idxs = KEYS.map((_, i) => i).filter((i) => groupOf(i) === gid && !ess.includes(i) && !(gid === 'oth' && UNITS[i] === 'kcal'));
    if (!idxs.length) return '';
    const any = idxs.some(has);
    if (any) moreHas = true;
    return `<details class="fold" ${['fa', 'min', 'vit'].includes(gid) || any ? 'open' : ''}><summary>${gname}</summary>${idxs.map((i) => nutField(food, i)).join('')}</details>`;
  }).join('');
  return `<div class="card ess"><div class="card-t">Essentials</div>${ess.map((i) => nutField(food, i)).join('')}</div>
    <details class="fold more" ${moreHas ? 'open' : ''}><summary>More values (fatty acids, minerals, vitamins…)</summary>${groups}</details>`;
}
/* Show an error right under the field, open any folded group around it, and put the cursor there. */
function fieldError(input, msg, focus = true) {   // focus = false after waiting for the network: focus() outside the tap leaves the field "focused" without a keyboard on iOS
  const host = input.closest('.nin, label.f') || input;
  $$('.field-err', host.parentNode).forEach((x) => x.remove());
  host.insertAdjacentHTML('afterend', `<p class="note field-err" role="alert">${esc(msg)}</p>`);
  input.setAttribute('aria-invalid', 'true');
  for (let d = input.closest('details'); d; d = d.parentElement && d.parentElement.closest('details')) d.open = true;
  if (focus) input.focus();
  input.scrollIntoView({ block: 'center' });
}
function portionRows(list) {
  return list.map((p) => `<div class="ing"><input type="text" class="pl" value="${esc(p.label)}" aria-label="Portion name" placeholder="e.g. 1 piece"><input type="text" inputmode="decimal" class="pg" value="${esc(String(p.grams))}" aria-label="Portion in grams" placeholder="g"><button class="icon-btn sm" data-rm aria-label="Remove">${IC.close}</button></div>`).join('');
}
function collectPortions(root) {
  return $$('#ports .ing', root).map((r) => ({ label: $('.pl', r).value.trim(), grams: num($('.pg', r).value) })).filter((p) => p.label && p.grams > 0);
}

/* opts: name, barcode (start values), after(food) (called after saving),
   prefill (a food from an AI answer, see parseAiImport: the editor opens filled in, the food counts as new), title, notice (HTML above the form) */
function openFoodEditor(food, opts = {}) {
  const isNew = !food;
  const f0 = food || opts.prefill || { name: opts.name || '', brand: '', barcode: opts.barcode || '', basis: { qty: 100, unit: 'g' }, n: {}, nova: null, portions: [], note: '' };
  const perUnit = !isG(f0);
  const estOpen = !!opts.prefill || !!(f0.est && f0.est.length) || !!f0.q || !!f0.fortified;
  const sh = openSheet(opts.title || (isNew ? 'Create food from label' : 'Edit food'), `
    ${opts.notice || ''}
    <label class="f">Name<input type="text" enterkeyhint="next" id="fname" value="${esc(f0.name)}" maxlength="120" placeholder="e.g. Almond barista drink"></label>
    <div class="grid2"><label class="f">Brand<input type="text" enterkeyhint="next" id="fbrand" value="${esc(f0.brand || '')}" maxlength="80"></label>
      <label class="f">Barcode<input type="text" inputmode="numeric" enterkeyhint="done" id="fcode" value="${esc(f0.barcode || '')}" maxlength="14"></label></div>
    <fieldset><legend class="muted small" style="margin-bottom:8px;font-weight:600">The values below are per</legend>
      <div class="row gap"><label class="chk"><input type="radio" name="basis" value="g" ${perUnit ? '' : 'checked'}> 100 g</label>
      <label class="chk"><input type="radio" name="basis" value="u" ${perUnit ? 'checked' : ''}> 1 unit (capsule, tablet, piece)</label>
      <input type="text" enterkeyhint="done" id="funit" value="${esc(perUnit ? f0.basis.unit : 'capsule')}" style="width:140px" aria-label="Unit name" ${perUnit ? '' : 'hidden'}></div></fieldset>
    <details class="fold" id="estfold" ${estOpen ? 'open' : ''}><summary>Estimates (optional)</summary>
      <p class="hint" style="margin:0 0 10px">For values that are not on the label, for example worked out from the ingredient list. Tap the <b>~</b> next to a value below to mark it as an estimate. Estimates show a ~ in the totals and in the CSV.</p>
      <label class="f">Estimate confidence<select id="fconf"><option value="">Not set</option>${Object.entries(CONF).map(([c, name]) => `<option value="${c}" ${f0.q === c ? 'selected' : ''}>${cap(name)}</option>`).join('')}</select></label>
      <label class="chk tall"><input type="checkbox" id="ffort" ${f0.fortified ? 'checked' : ''}> May be fortified (vitamins or minerals added)</label></details>
    <p class="muted small">Fill in what the label shows. An empty field means “no data”, a 0 is a real zero. Write &lt;0.3 for a value below a detection limit.</p>
    <div id="nuts">${nutInputs(f0)}</div>
    <details class="fold" ${f0.nova ? 'open' : ''}><summary>Food-processing group (NOVA, optional)</summary>
      <p class="hint" style="margin:0 0 10px">1 = unprocessed or minimally processed, 2 = culinary ingredient (oil, butter, sugar, salt), 3 = processed food (bread, canned vegetables), 4 = ultra-processed (soft drinks, packaged snacks). Leave it unset if you are not sure.</p>
      <label class="f">NOVA group<select id="fnova"><option value="">Not set</option>${[1, 2, 3, 4].map((n) => `<option value="${n}" ${f0.nova === n ? 'selected' : ''}>${n}${n === 4 ? ' (ultra-processed)' : ''}</option>`).join('')}</select></label></details>
    <div id="portwrap"><h4>Portions (in grams)</h4><div id="ports">${portionRows(f0.portions || [])}</div><button class="chip-btn" id="addport" style="margin-top:8px">+ Portion</button></div>
    <label class="f">Notes (source, confidence)<textarea id="fnote" maxlength="1200">${esc(f0.note || '')}</textarea></label>
    <div class="row gap sheet-actions">${isNew ? '' : '<button class="btn danger" id="fdel">Delete</button>'}<span style="flex:1"></span><button class="btn primary" id="fok">Save</button></div>`);
  const radios = $$('input[name=basis]', sh.el), unit = $('#funit', sh.el);
  const syncBasis = () => { const u = radios.find((r) => r.checked).value === 'u'; unit.hidden = !u; unit.disabled = !u; $('#portwrap', sh.el).hidden = u; };
  radios.forEach((r) => r.addEventListener('change', syncBasis)); syncBasis();
  /* Return on the keyboard: Name → Brand → Barcode, and the keyboard closes after the Barcode (the unit name closes it too) */
  const chain = ['#fname', '#fbrand', '#fcode'].map((q) => $(q, sh.el));
  chain.forEach((el, i) => el.addEventListener('keydown', (e) => { if (e.key !== 'Enter') return; e.preventDefault(); if (chain[i + 1]) chain[i + 1].focus(); else el.blur(); }));
  unit.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); unit.blur(); } });
  /* ~ buttons: a value can be marked as an estimate (not a label value). The mark goes when the field is emptied. Buttons show on filled fields while the Estimates part is open. */
  const estOn = new Set((f0.est || []).filter((k) => IDX[k] !== undefined));
  const estFold = $('#estfold', sh.el);
  function refreshEst() {
    for (const b of $$('[data-est]', sh.el)) {
      const k = b.dataset.est, has = !parseInput($('#n_' + k, sh.el).value).empty;
      if (!has) estOn.delete(k);
      const on = estOn.has(k);
      b.hidden = !(has && (on || estFold.open));
      b.setAttribute('aria-pressed', String(on));
      b.setAttribute('aria-label', `${labelOf(IDX[k])}: ${on ? 'estimated value. Tap to mark it as a label value' : 'label value. Tap to mark it as an estimate'}`);
      b.parentElement.classList.toggle('est', on);
    }
    $('#nuts', sh.el).classList.toggle('est-on', estFold.open || estOn.size > 0);
  }
  estFold.addEventListener('toggle', refreshEst);
  sh.el.addEventListener('click', (e) => { const b = e.target.closest('[data-est]'); if (b) { const k = b.dataset.est; if (estOn.has(k)) estOn.delete(k); else estOn.add(k); refreshEst(); } });
  sh.el.addEventListener('input', (e) => { if (e.target.dataset && e.target.dataset.k) refreshEst(); });
  refreshEst();
  $('#addport', sh.el).onclick = () => $('#ports', sh.el).insertAdjacentHTML('beforeend', portionRows([{ label: '', grams: '' }]));
  sh.el.addEventListener('click', (e) => { const b = e.target.closest('[data-rm]'); if (b) b.closest('.ing').remove(); });
  sh.el.addEventListener('input', (e) => { $$('.field-err', sh.el).forEach((x) => x.remove()); if (e.target.removeAttribute) e.target.removeAttribute('aria-invalid'); });
  $('#fok', sh.el).onclick = () => {
    const name = $('#fname', sh.el).value.trim();
    if (!name) { fieldError($('#fname', sh.el), 'Give the food a name.'); return; }
    const n = {};
    for (const inp of $$('[data-k]', sh.el)) {
      const p = parseInput(inp.value);
      if (p.err) { fieldError(inp, 'Invalid number for ' + labelOf(IDX[inp.dataset.k]) + '. Use a positive number, or <x for a value below the detection limit.'); return; }
      if (!p.empty) n[inp.dataset.k] = p.v;
    }
    const u = radios.find((r) => r.checked).value === 'u';
    const unitName = unit.value.trim() || 'unit';
    const estKeys = [...estOn].filter((k) => n[k] !== undefined).sort((a, b) => IDX[a] - IDX[b]);
    const conf = $('#fconf', sh.el).value;
    if (estKeys.length && !conf) { estFold.open = true; fieldError($('#fconf', sh.el), 'Choose how confident the estimate is.'); return; }
    const fields = {
      name, brand: $('#fbrand', sh.el).value.trim(), barcode: $('#fcode', sh.el).value.trim(),
      basis: u ? { qty: 1, unit: unitName } : { qty: 100, unit: 'g' }, n,
      nova: Number($('#fnova', sh.el).value) || null, portions: u ? [] : collectPortions(sh.el),
      note: $('#fnote', sh.el).value.trim(),
    };
    if (estKeys.length) fields.est = estKeys;
    const q = estKeys.length ? conf : conf === 'n' ? 'n' : '';   // a confidence without any estimate only means something as “none”
    if (q) fields.q = q;
    if ($('#ffort', sh.el).checked) fields.fortified = true;
    const finish = (out, how) => {
      sh.close();
      if (S.tab === 'foods') render();
      if (how !== 'updated') toast('Food saved');   // an update has its own message, with Undo
      if (opts.after) opts.after(out, how);
    };
    if (opts.prefill && !food) { saveImportedFood(fields, finish); return; }   // asks first when the food is already there
    const out = food || { id: 'u:' + uid(), src: 'user', created: Date.now() };
    applyFoodFields(out, fields);
    if (food && food.src === 'off') out.edited = true;
    S.foods[out.id] = out;
    invalidate(); save();
    finish(out, 'saved');
  };
  const del = $('#fdel', sh.el);
  if (del) del.onclick = () => deleteFood(food, () => { sh.close(); render(); });
}
function deleteFood(food, done) {
  const used = S.log.filter((e) => e.f === food.id).length;
  if (used) { toast(`Can't delete: used in ${used === 1 ? '1 diary entry' : used + ' diary entries'}.`); return; }
  const copy = S.foods[food.id];
  delete S.foods[food.id]; invalidate(); save(); done();
  toast('Deleted: ' + cap(food.name), () => { S.foods[copy.id] = copy; invalidate(); save(); render(); });
}

/* ================= Paste from AI ================= */
/* An AI looks a product up with a fixed prompt (tools/ai_prompt.md, v3.1 since version 16) and answers with a JSON block: the foods file of "Import foods (JSON)"
   (the older answer shape "nutrilog_import": 1 of prompt v1 is still read, see AI_IMPORT_VERSION). The person pastes the answer,
   reviews the food in the food editor and saves it by hand. The pasted text is not stored and nothing is sent anywhere.
   A food from an AI answer has the fields of every food you make (name, brand, barcode, basis, n, nova, portions, note) and three more:
   est (the keys of n that are estimates), q (confidence code, see CONF) and fortified (vitamins or minerals may have been added). */
const AI_IMPORT_VERSION = 1;
/* >>> AI prompt: written by tools/embed_ai_prompt.py from tools/ai_prompt.md. Do not edit by hand. */
const AI_PROMPT = `# Nutrilog tételpontosító (v3.1, végleges)

Te egy személyes tápanyagnapló (Nutrilog) adatfelviteli segédje vagy. A kimeneted JSON-része az app „Import foods (JSON)” funkciójával kerül be, ezért a formátum pontossága és a „nem találgatok” szabály fontosabb a teljességnél. Magyarul válaszolj.

## 0. Előfeltétel

A becsléshez a CIQUAL 2020 referenciaértékek kellenek. Ezek a \`ciqual_ref.json\` fájlban vannak (a 6. pont kódjainak sorai; ugyanolyan szerkezetű, mint a Nutrilog repo teljes \`ciqual.json\` fájlja: \`nutrients\` a 64 kulcs sorrendjében, \`foods\` tömb, a \`c\` mező a kód, a \`v\` tömb a \`nutrients\` sorrendjében). Ha a felhasználó csatolta ezt (vagy a teljes \`ciqual.json\`-t), a 6. pontban felsorolt kódok értékeit onnan vedd, kódfuttatással, ne fejből. Ha nincs csatolva, kérd meg egyszer. Ha a referencia nem áll rendelkezésre, csak címkeértékeket adj, becslést ne végezz, és ezt írd a note-ba. Értékeket soha ne találj ki.

## 1. Bemenet

Egy vagy több termék: név, márka, vonalkód, a csomagolás fotója, a tápérték-táblázat és a hozzávalók szövege, vagy link.

- Ha lényeges adat hiányzik (nem látszik a hozzávalólista, vagy nem tudni, mire vonatkozik a táblázat: 100 g, 100 ml vagy adag), kérdezz vissza egyszer, legfeljebb 3 rövid kérdéssel.
- Webkeresésnél a gyártó oldalát és a bolt termékoldalát (pl. dm.hu) használd. Az Open Food Facts csak akkor, ha összevethető a csomagolással. Eltérésnél a csomagolás fotója az elsődleges; az eltérést írd a note-ba.
- A vonalkódot, a tápértéket, a hozzávalót és az arányokat soha nem találod ki.

## 2. Háromféle érték

1. **Címkeérték:** a csomagoláson vagy a gyártónál szerepel. Bekerül az \`n\`-be.
2. **Átváltott érték:** pontos átszámítás. Bekerül az \`n\`-be, a note-ban meg kell nevezni.
   - kJ → kcal: ÷ 4,184
   - só (g) → nátrium (mg): × 400
   - nátrium (mg) → só (g): × 2,5 ÷ 1000
   - IU → µg D-vitamin: × 0,025
   - folyadék: 1 ml = 1 g (az app így kezeli)
3. **Becslés:** nincs a címkén, a hozzávalókból és a referenciából számolod. Bekerül az \`n\`-be és az \`est\` listába.

A hiányzó adat nem nulla. Ami nincs a forrásban és nem becsülhető megalapozottan, annak a kulcsát hagyd ki. A 0 csak akkor szerepelhet, ha a címke 0-t ír, vagy becslésnél minden felismert összetevő referenciaértéke 0. Ha a címke önmagának ellentmond, hagyd a címkeértéket, és jelezd a note-ban.

## 3. Alap (\`basis\`)

- Alapértelmezés: 100 g, \`{"qty": 100, "unit": "g"}\`.
- Folyadék, amelynek értékeit a címke 100 ml-re adja: 100 g-ra váltva (1 ml = 1 g), \`portions\`: \`[{"label": "100 ml", "grams": 100}]\`.
- Por, amelynek értékeit a címke az elkészített italra adja: 100 g por az alap; \`portions\`-ba az elkészített mennyiség és a por grammja (pl. \`{"label": "250 ml kész", "grams": 20}\`).
- Kapszula, tabletta, kiegészítő, darabos termék: \`{"qty": 1, "unit": "capsule"}\` (vagy \`tablet\`, \`scoop\`, \`piece\`), az értékek 1 egységre vonatkoznak, \`portions\` üres. Kiegészítőre nem becsülsz: az \`est\` üres, a \`confidence\` „nincs becslés”.
- \`portions\` csak 100 g alapnál van: a csomagon szereplő adag (pl. \`{"label": "1 szelet", "grams": 30}\`).

## 4. Becslés a hozzávalókból

Csak 100 g alapú termékre, ismert hozzávalólistával.

1. A címke energiája és makrói (zsír, telített zsír, szénhidrát, cukor, rost, fehérje, só) mérvadóak, nem írod felül. Ha a címke nem ad makrót, azt is becsülheted, és ezt a note-ba írod.
2. Minden más kulcsra becslés a 6. pont referenciaértékei alapján.
3. Összetevők feldolgozása:
   a. A hozzávalólista vesszővel vagy pontosvesszővel elválasztott tételei. A zárójeles alösszetevőket figyelmen kívül hagyod, a zárójel előtti nevet használod.
   b. Figyelmen kívül hagyandó (nem számít a lefedettségbe sem, nem számít a tételszámba sem): víz, só, fűszerek és ízesítők, aroma, kivonat, emulgeálószer, sűrítő, savanyító, tartósító, antioxidáns, színezék, élesztő, vitamin- és ásványianyag-adalék, adalékanyag (E-szám, „térfogatnövelő szer”, „-karbonát”, „-szulfát”, „-klorid” stb.).
   c. Súly:
      - Ha legalább két (nem ignorált) tételnél szerepel százalék: a százalékos tétel súlya a százalék; a százalék nélküli (nem ignorált) tételek a 100 − Σszázalék maradékon (legalább 0) egyenlően osztoznak.
      - Egyébként a súly 1/(sorszám+1). A sorszám 0-tól indul, és az **eredeti hozzávalólistabeli hely**: az ignorált tételek is számítanak a sorszámba. Példa: „víz, zab, mandula, cukor”: a víz sorszáma 0 (ignorált), a zabé 1 (súly 1/2), a mandulaé 2 (1/3), a cukoré 3 (1/4).
   d. Érték kulcsonként: Σ(súly × referenciaérték) / Σ(súly), csak azokon a tételeken, ahol a referenciának van értéke. Ha egyiken sincs, a kulcs kimarad. Ha az eredmény 0, de a felismert tételek egy részének nincs értéke arra a kulcsra, a kulcs szintén kimarad (a hiányzó nem nulla).
   e. Felismerhetetlen tétel: a súlya a lefedettség nevezőjében van, de értékhez nem járul hozzá.
   f. **Skálázás a címke energiájához (hígítás és sűrűsödés).** A 4.3.d eredménye úgy viselkedik, mintha a termék 100 g-ja csupa száraz összetevőből állna: a víz ignorált, ezért nem hígít. Ezt a lépés javítja, a 4.3.d után, a 3 értékes jegyre kerekítés előtt.
      - Címke-energia: a címke kcal értéke (kJ-ból átváltva is jó). Keverék-energia: a 4.3.d szerint a \`kcal\` kulcsra számolt érték.
      - Ha van címke-energia (> 0), a keverék-energia > 0, és a lefedettség ≥ 0,6: s = címke-energia ÷ keverék-energia. A 4.2 pont szerint becsült kulcsok értékét szorozd s-sel. A címkeértékeket és az átváltott értékeket nem. A \`water\` kulcsot ilyenkor ne becsüld (a keverék vizéből skálázva értelmetlen szám lenne): hagyd ki, kivéve ha a címke megadja.
      - Ha a címke-energia 0, vagy a lefedettség 0,6 alatt van: nem skálázol, és a becsült kulcsokat kihagyod (az \`est\` üres, a \`confidence\` „nincs becslés”). A note-ba írd az okot.
      - Ha a címke nem ad energiát: ha a víz a hozzávalólista első három helye között van, a becsült kulcsokat kihagyod (a hígítás nem becsülhető); egyébként skálázás nélkül becsülhetsz, és ezt a note-ba írod.
      - Az s értékét a note-ba írd: „Skálázás: ×0,04 a címke energiájához.”
4. Lefedettség = felismert súly / (felismert súly + felismerhetetlen súly).
5. Dúsítás: ha a hozzávalók között vitamin vagy ásványi anyag szerepel, vagy a csomagon „dúsított” áll, \`fortified: true\`. A címkén megadott dúsított értékek címkeértékek. A nyers összetevőkből becsült vitamin- és ásványianyag-érték alulbecslés; ezt írd a note-ba.
6. Megbízhatóság a becsült kulcsokra. A „tétel” az ignorált összetevőkön kívüli tételek száma (felismert és felismerhetetlen együtt):
   - nincs felismert tétel: „nincs becslés”
   - lefedettség ≥ 0,99 és legfeljebb 2 tétel: „közepes”
   - lefedettség ≥ 0,9 és legfeljebb 4 tétel: „közepes”
   - lefedettség ≥ 0,6: „alacsony”
   - egyébként: „nagyon alacsony”
   - dúsított termék, amely „közepes”, eggyel lejjebb sorolódik („alacsony”).

## 5. Ami nem becsülhető

Aroma, kivonat, összetett összetevő (pl. ostya, csokoládébevonat, „fűszerek”), enzim: felismerhetetlen. Ha egy kulcshoz egyetlen felismert tételnek sincs referenciaértéke, a kulcs kimarad.

## 6. Referencialista (CIQUAL 2020 kód)

Csak ezeket a kódokat használd. A 64 értéket a \`ciqual_ref.json\` (vagy a teljes \`ciqual.json\`) \`v\` tömbjéből vedd.

- Gabonák: zab 9310 · zabital 18905 · rizs (száraz) 9100 · rizs (főtt) 9104 · tönköly 9001 · árpa 9320 · hajdina 9380 · köles 9330 · quinoa 9340 · kukorica 9200
- Búzaliszt: finomliszt, BL55 vagy típus nélküli „búzaliszt” 9436 (süteményliszt: 9440) · BL80 9445 · teljes kiőrlésű 9415 · T110 9410 · kifejezetten 65-ös liszt 9435. A magyar és a francia lisztípusok közelítő megfelelők (BL55 ≈ T55, BL80 ≈ T80, teljes kiőrlésű ≈ T150): ezt egy rövid szóval jelezd a note-ban. Durumbúza (egész): 9060, csak durum-alapú terméknél. Más búzatermék (pl. egész búzaszem, búzakorpa): felismerhetetlen.
- Hüvelyesek, gumósok: lencse (fajta nélkül, száraz) 20504 · vörös lencse (száraz) 20535 · zöld lencse (száraz) 20585 · lencse (főtt) 20587 · burgonya (főtt) 4003. Burgonyapehely, burgonyakeményítő: felismerhetetlen.
- **Főtt sorok** (9104, 20587, 4003): csak kész ételben vagy kifejezetten főtt összetevőnél. Száraz, ipari termékben (liszt, tészta, snack, keverék) a száraz sort használd.
- Magvak, diófélék: kókuszhús 15006 · kókuszvíz 18011 · mandula 15041 · mandulaital 18107 · mogyoró 15004 · földimogyoró 15001 · kesudió 15054 · pisztácia 15044 · napraforgómag 15011 · szezámmag 15010 · tahini 15203 · lenmag 15034
- Kakaó, csokoládé: kakaópor 18100 · kakaóvaj 16030 · étcsokoládé 70% kakaótartalom alatt 31005 · étcsokoládé 70% fölött 31074 · tejcsokoládé 31004 · fehér csokoládé 31010. „Csokoládé” fajta és kakaótartalom nélkül: felismerhetetlen.
- Olajok, zsírok: napraforgóolaj 17440 · repceolaj 17130 · olívaolaj 17270 · „növényi olaj” fajta nélkül 17001 (átlag) · kókuszzsír / kókuszolaj: finomított 16060 (alapértelmezett, ha a címke nem mondja), extra szűz vagy hidegen sajtolt 16040 · pálmaolaj 16129 (a finomított értékei azonosak) · pálmamagzsír 16200 · vaj 16400
- Cukor, méz: cukor, glükózszirup, maltodextrin, dextróz, nádszirup 31016 · méz 31008
- Gyümölcsök: alma 13050 · banán 13005 · datolya 13011 · mazsola 13046 · narancs 13034 · citrom 13009 · eper 13014 · áfonya 13028 · málna 13015 · vörösáfonya 13113
- Zöldségek: sárgarépa 20009 · spenót 20059 · paradicsom 20047 · cékla 20091 · brokkoli 20057 · hagyma 20034 · uborka 20210
- Tejtermékek: tehéntej (teljes tej, UHT) 19023 · joghurt 19600 · tejszín 19402
- Szója, rizs: szójaital 18900 · szójaliszt 20900 · rizsital 18904

Nincs a listán, ezért nem becsülhető, felismerhetetlen: tökmag (a CIQUAL 20044 tökhús, nem tökmag), kókusztej-ital (a 18011 kókuszvíz, nem kókusztej), és **minden olyan olaj vagy zsír, amelyhez nincs fenti kód**. Zsírra nincs általános nulla-szabály: ismeretlen zsír felismerhetetlen, a telített zsír és az E-vitamin nem lesz 0. A felismerhetetlen tételt a note-ba írd.

Referencia-érték kezelés: a referenciasorban a \`"<x"\` cella (kimutatási határ alatt) helyett x/2 értéket használj; a \`"t"\` (nyom) cella helyett 0-t. Az ilyen érték is értéknek számít a kulcs súlyozott átlagában. Minden ilyen esetet egyetlen rövid sorban jelezz a note-ban: „x/2-vel számolt: vitamin_k1, vitamin_b12 (+N további)”.

## 7. Tápanyagkulcsok

Csak ezek a kulcsok, pontosan így írva. A zárójelben a mértékegység áll, az érték szám (nem szöveg, nem mértékegységgel), legfeljebb 3 értékes jeggyel. Kimutatási határ alatt szövegként: \`"<0.3"\`.

- Energia és makrók: \`kcal\` (kcal); \`water\`, \`protein\`, \`carbohydrate\`, \`fat\`, \`sugars\`, \`starch\`, \`fibres\`, \`polyols\`, \`ash\`, \`alcohol\`, \`organic_acids\` (g). A címke fehérjéje a \`protein\`-be kerül.
- Cukrok (g): \`fructose\`, \`galactose\`, \`glucose\`, \`lactose\`, \`maltose\`, \`sucrose\`.
- Zsírsavak (g): \`fa_saturated\`, \`fa_mono\`, \`fa_poly\`, \`fa_4_0\`, \`fa_6_0\`, \`fa_8_0\`, \`fa_10_0\`, \`fa_12_0\`, \`fa_14_0\`, \`fa_16_0\`, \`fa_18_0\`, \`fa_18_1_n_9_cis\`, \`fa_18_2_9c_12c_n_6\`, \`fa_18_3_c9_c12_c15_n_3\`, \`fa_20_4_5c_8c_11c_14c_n_6\`, \`fa_20_5_5c_8c_11c_14c_17c_n_3_epa\`, \`fa_22_6_4c_7c_10c_13c_16c_19c_n_3_dha\`.
- Egyéb: \`cholesterol\` (mg), \`salt\` (g).
- Ásványi anyagok: \`calcium\`, \`chloride\`, \`copper\`, \`iron\`, \`magnesium\`, \`manganese\`, \`phosphorus\`, \`potassium\`, \`sodium\`, \`zinc\` (mg); \`iodine\`, \`selenium\` (µg).
- Vitaminok: \`retinol\`, \`beta_carotene\`, \`vitamin_d\`, \`vitamin_k1\`, \`vitamin_k2\`, \`vitamin_b9_or_folate\`, \`vitamin_b12\` (µg); \`vitamin_e\`, \`vitamin_c\`, \`vitamin_b1_or_thiamin\`, \`vitamin_b2_or_riboflavin\`, \`vitamin_b3_or_niacin\`, \`vitamin_b5_or_pantothenic_acid\`, \`vitamin_b6\` (mg).

A-vitamin: \`retinol\` csak akkor, ha a forrás retinolt vagy retinil-észtert mond; β-karotinból származó érték a \`beta_carotene\`. RAE/RE értéknél, ha nem derül ki a forma, hagyd ki, és írd a note-ba.

## 8. NOVA (\`nova\`)

Javaslat; a felhasználó az appban dönt. Csak akkor adj számot, ha a hozzávalólistából egyértelmű, egyébként \`null\`.

- 1: egy vagy kevés, minimálisan feldolgozott összetevő.
- 2: kulináris alapanyag (olaj, vaj, cukor, só).
- 3: egyszerűen feldolgozott étel (sajt, kenyér, konzerv, ipari adalék nélkül).
- 4: ipari adalékok vagy jellemző összetevők (aroma, emulgeálószer, ízfokozó, módosított keményítő, glükóz-fruktózszirup, hidrolizált fehérje, édesítőszer).

Az indokot írd a note-ba: „NOVA-javaslat: 4 (aroma, emulgeálószer).”

## 9. Kimenet

Két rész, ebben a sorrendben:

1. Ellenőrző összefoglaló, legfeljebb 8 sor: név, alap, hány címkeérték, hány becsült érték, megbízhatóság, dúsítás, skálázás, átváltások és eltérések, források, referencia-hiányok.
2. Egyetlen \`\`\`json blokk, benne csak érvényes JSON, komment nélkül. Ez az app „Import foods (JSON)” funkciójának formátuma: a \`log\` és a \`meta\` nincs benne, mert az import figyelmen kívül hagyja őket, és így nem érinti a naplót.

\`\`\`json
{
  "app": "tapnaplo",
  "version": 1,
  "foods": {
    "u:ai-pelda-mandulaital": {
      "id": "u:ai-pelda-mandulaital",
      "src": "user",
      "name": "Példa mandulaital, cukormentes",
      "brand": "Példa Márka",
      "barcode": "",
      "basis": { "qty": 100, "unit": "g" },
      "n": { "kcal": 24, "protein": 0.9, "carbohydrate": 0.2, "fat": 2.1, "fa_saturated": 0.2, "fibres": 0.4, "salt": 0.11, "sodium": 44, "calcium": 120, "vitamin_e": 1.1 },
      "est": ["vitamin_e"],
      "confidence": "alacsony",
      "fortified": true,
      "nova": 4,
      "portions": [{ "label": "100 ml", "grams": 100 }],
      "note": "Forrás: csomag fotója, 2026-10-25. Címke: kcal, protein, carbohydrate, fat, fa_saturated, fibres, salt, calcium (dúsított). Átváltás: sodium = só × 400. Becslés: 1 kulcs (vitamin_e), megbízhatóság alacsony; dúsított, ezért alulbecslés. Skálázás: ×0,04 a címke energiájához. NOVA-javaslat: 4 (aroma, emulgeálószer).",
      "created": 0,
      "updated": 0
    }
  }
}
\`\`\`

Mezőszabályok:

- \`id\`: \`u:ai-\` és a név vagy a vonalkód kisbetűs, kötőjeles, **ékezet nélküli** változata (pl. „Sütőtök-krém” → \`u:ai-sutotok-krem\`). Egyedi legyen.
- \`name\`: legfeljebb 120 karakter, a csomagon szereplő név. \`brand\`: legfeljebb 80 karakter vagy \`""\`. \`barcode\`: csak számjegyek (8–14) vagy \`""\`.
- \`n\`: csak az ismert vagy becsült kulcsok.
- \`est\`: a becsült kulcsok listája. Az app \`~\` jellel jelöli őket a Nutrients fülön, az Amount lapon és a CSV-ben; a címke- és az átváltott kulcsok nincsenek benne.
- \`confidence\`, \`fortified\`: ahogy a 4. pontban.
- \`nova\`: 1–4 vagy \`null\`.
- \`note\`: magyarul, **legfeljebb 1200 karakter** (az app jegyzetmezőjének határa). Nem sorolod fel a becsült kulcsokat egyenként: a címke- és átváltott kulcsokat sorold fel, és írd le, hány további kulcs becslés. Tartalma ebben a fontossági sorrendben: megbízhatóság és dúsítás; skálázás (×s); felismerhetetlen összetevők; x/2-vel számolt kulcsok (egy sor); átváltások; eltérések; NOVA-indoklás; forrás és dátum. Ha nem fér bele, a sor végéről hagyj el. Az \`est\` és a \`confidence\` mezőt ez nem érinti.
- \`created\`, \`updated\`: maradjon 0.
- Több termék: a \`foods\` objektumban több kulcs.

A JSON-t az app Data fülén az „Import foods (JSON)” gombbal töltsd be, vagy másold vágólapra, és használd az app „Paste from AI” funkcióját. Ne a „Restore from file”-lal: az utóbbi a teljes adatbázist felülírja.

## 10. Ellenőrzés a válasz előtt

- Minden \`est\`-kulcs benne van az \`n\`-ben. A címke- és átváltott értékek nincsenek az \`est\`-ben.
- 100 g alapnál: kcal ≈ 4 × fehérje + 4 × szénhidrát + 9 × zsír (+ 7 × alkohol), ±15%. Telített + egyszeresen + többszörösen telítetlen ≤ zsír. Cukor ≤ szénhidrát. Fehérje + szénhidrát + zsír + víz + hamu ≤ 100 g. Só ≈ nátrium × 2,5 ÷ 1000.
- A mértékegység a kulcs mértékegysége (mg és µg ne keveredjen).
- A becsült kulcsok skálázva vannak (4.3.f), vagy a note megmondja, miért nem; az s értéke a note-ban van.
- A note legfeljebb 1200 karakter.
- Ha valamelyik ellenőrzés nem jön ki, ne simítsd el: hagyd a címkeértéket, és írd az összefoglalóba és a note-ba.
`;
/* <<< AI prompt */
const AI_FIELDS = ['est', 'q', 'fortified'];
/* The confidence words of an answer: English, Hungarian (the v3 prompt writes them in Hungarian) and the one-letter codes of a backup. Looked up without accents. */
const AI_CONF = { high: 'h', medium: 'm', low: 'l', 'very low': 'v', none: 'n', magas: 'h', kozepes: 'm', alacsony: 'l', 'nagyon alacsony': 'v', 'nincs becsles': 'n', nincs: 'n', h: 'h', m: 'm', l: 'l', v: 'v', n: 'n' };
const aiConf = (c) => {
  const k = norm(c).replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim();
  return Object.prototype.hasOwnProperty.call(AI_CONF, k) ? AI_CONF[k] : undefined;   // not "constructor" and the like
};
const basisText = (b) => (b.unit === 'g' ? '100 g' : `${b.qty} ${b.unit}`);

/* the prompt for "Copy AI prompt": the text of tools/ai_prompt.md as it is (it has its own list of nutrient keys, checked against KEYS and UNITS by tests/test_ai_import.py) */
function aiPrompt() { return AI_PROMPT; }

/* ---- reading the answer: the AI may wrap the JSON in text or a ``` fence, use curly quotes, a trailing comma, numbers as text with a decimal comma ---- */
const aiStraight = (t) => t.replace(/[“”„‟″]/g, '"');
function aiBraceEnd(t, start) {   // the index after the } that closes the { at start (quotes respected); -1 when it never closes
  let depth = 0, inStr = false;
  for (let i = start; i < t.length; i++) {
    const c = t[i];
    if (inStr) { if (c === '\\') i++; else if (c === '"') inStr = false; }
    else if (c === '"') inStr = true;
    else if (c === '{') depth++;
    else if (c === '}' && --depth === 0) return i + 1;
  }
  return -1;
}
function aiLoose(s) {
  try { return JSON.parse(s); } catch { /* try again without the commas before } and ] */ }
  try { return JSON.parse(s.replace(/,(\s*[}\]])/g, '$1')); } catch { return undefined; }
}
/* The shape of a Nutrilog file that holds foods: { "app": "tapnaplo", "foods": { "<id>": { … } } } (the v3 prompt answers like this, and so does a backup). */
const isFoodsFile = (j) => !!j && typeof j === 'object' && j.app === 'tapnaplo' && !!j.foods && typeof j.foods === 'object' && !Array.isArray(j.foods);
function aiFindJson(text) {
  const clean = String(text).replace(/[﻿​-‍⁠]/g, '').replace(/ /g, ' ');
  for (const t of [clean, aiStraight(clean)]) {   // a curly quote can be a real quote of the JSON, or only a quote inside a text: try both
    let tries = 0;
    for (let s = t.indexOf('{'); s >= 0 && tries < 300; s = t.indexOf('{', s + 1), tries++) {
      const e = aiBraceEnd(t, s);
      if (e < 0) continue;
      const j = aiLoose(t.slice(s, e));
      if (j && typeof j === 'object' && !Array.isArray(j) && ('nutrilog_import' in j || Array.isArray(j.foods) || isFoodsFile(j))) return { json: j, marker: true };
    }
  }
  return { json: null, marker: /nutrilog_import|"tapnaplo"/.test(clean) };
}
function aiNum(x) {   // a number, or text such as "0,5"; NaN when it is neither
  if (typeof x === 'number') return Number.isFinite(x) ? x : NaN;
  if (typeof x === 'string' && x.trim() !== '') return Number(x.trim().replace(',', '.'));
  return NaN;
}
/* Warnings, not errors: the food can be loaded, but a value looks wrong. Only numbers are compared (a "<x" value is skipped). */
function aiChecks(n, basis) {
  const w = [], v = (k) => (typeof n[k] === 'number' ? n[k] : null);
  const kcal = v('kcal'), pr = v('protein'), ch = v('carbohydrate'), fa = v('fat'), alc = v('alcohol') || 0;
  if (kcal !== null && pr !== null && ch !== null && fa !== null) {
    const calc = 4 * pr + 4 * ch + 9 * fa + 7 * alc, d = Math.abs(kcal - calc);
    if (d >= 5 && d / Math.max(kcal, calc) > 0.2) w.push(`Energy is ${fmt(kcal)} kcal, but protein, carbohydrate and fat add up to about ${fmt(calc)} kcal (more than 20% apart). Fibre and polyols explain part of a gap, not all of it.`);
  }
  const sat = v('fa_saturated'), mono = v('fa_mono'), poly = v('fa_poly'), sug = v('sugars');
  if (sat !== null && fa !== null && sat > fa) w.push(`Saturated fat (${fmt(sat)} g) is more than total fat (${fmt(fa)} g).`);
  if (sug !== null && ch !== null && sug > ch) w.push(`Sugars (${fmt(sug)} g) are more than carbohydrate (${fmt(ch)} g).`);
  if (fa !== null && [sat, mono, poly].filter((x) => x !== null).length >= 2) {
    const sum = (sat || 0) + (mono || 0) + (poly || 0);
    if (sum > fa * 1.05) w.push(`Saturated, monounsaturated and polyunsaturated fat add up to ${fmt(sum)} g, more than total fat (${fmt(fa)} g).`);
  }
  if (basis.unit === 'g') {
    const sum = ['protein', 'carbohydrate', 'fat', 'water', 'ash'].reduce((a, k) => a + (v(k) || 0), 0);
    if (sum > 105) w.push(`Protein, carbohydrate, fat, water and ash add up to ${fmt(sum)} g in 100 g.`);
  }
  const salt = v('salt'), na = v('sodium');
  if (salt !== null && na !== null) {
    const exp = na * 2.5 / 1000, d = Math.abs(salt - exp);
    if (d >= 0.03 && d / Math.max(salt, exp) > 0.2) w.push(`Salt (${fmt(salt)} g) and sodium (${fmt(na)} mg) do not match: sodium × 2.5 would be ${fmt(exp)} g salt.`);
  }
  return w;
}
/* One food of the answer. Pushes errors to out.errors, or the checked food and its warnings to out.foods. */
function aiFood(raw, k, count, out) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) { out.errors.push(`Food ${k + 1} is not an object.`); return; }
  const str = (v) => (typeof v === 'string' ? v.trim() : typeof v === 'number' ? String(v) : '');
  const name = str(raw.name), errs = [], warns = [];
  const label = count > 1 ? `Food ${k + 1}${name ? ' (' + name.slice(0, 40) + ')' : ''}: ` : '';
  const err = (m) => errs.push(label + m), warn = (m) => warns.push(m);
  if (!name) err('"name" is missing.');
  const brand = str(raw.brand), barcode = str(raw.barcode).replace(/[\s-]/g, '');

  let basis = null;
  const b = raw.basis;
  if (!b || typeof b !== 'object' || Array.isArray(b)) err('"basis" is missing. It says what the values are per, for example {"qty": 100, "unit": "g"} or {"qty": 1, "unit": "capsule"}.');
  else {
    const qty = aiNum(b.qty), unit = str(b.unit);
    if (!(qty > 0) || !unit) err('"basis" needs a "qty" greater than 0 and a "unit", for example {"qty": 100, "unit": "g"}.');
    else if (/^g(rams?)?$/i.test(unit)) { if (qty === 100) basis = { qty: 100, unit: 'g' }; else err(`The values must be per 100 g, but "basis" says ${qty} g. Convert them to 100 g.`); }
    else if (qty !== 1) err(`"basis" must be 100 g or 1 piece, not ${qty} ${unit}. Convert the values to 100 g (ml with the density) or to 1 ${unit}.`);
    else if (unit.length > 30) err('The unit name in "basis" is too long (30 characters at most).');
    else basis = { qty: 1, unit };
  }

  const n = {}, unknown = [], given = new Set();
  if (!raw.n || typeof raw.n !== 'object' || Array.isArray(raw.n)) err('"n" is missing. It lists the nutrient values.');
  else {
    for (const [key, v] of Object.entries(raw.n)) {
      if (v === null || v === undefined || (typeof v === 'string' && v.trim() === '')) continue;   // no value = no data
      given.add(key);
      if (IDX[key] === undefined) { unknown.push(key); continue; }
      const p = parseInput(typeof v === 'number' || typeof v === 'string' ? String(v) : '?');
      if (p.err || p.empty) err(`${key}: ${JSON.stringify(v)} is not a number of 0 or more (or <x for a value below a detection limit).`);
      else n[key] = p.v;
    }
    if (unknown.length) warn(`Unknown nutrient keys were skipped: ${unknown.join(', ')}.`);
    if (!Object.keys(n).length && !unknown.length) warn('The food has no nutrient values.');
  }

  const est = [];
  if (raw.est !== undefined && raw.est !== null) {
    if (!Array.isArray(raw.est)) err('"est" must be a list of nutrient keys, for example ["vitamin_e"].');
    else for (const key of raw.est) {
      if (typeof key !== 'string') err('"est" can only hold nutrient keys (text).');
      else if (!given.has(key)) err(`"est" lists ${key}, but "n" has no value for it. Only values you give can be estimates.`);
      else if (n[key] !== undefined && !est.includes(key)) est.push(key);
    }
  }
  let q;
  const c = raw.confidence !== undefined && raw.confidence !== null && raw.confidence !== '' ? raw.confidence : raw.q;   // q = the letter a backup file uses
  if (c !== undefined && c !== null && c !== '') {
    q = aiConf(c);
    if (!q) err('"confidence" must be high, medium, low, very low or none (in Hungarian: magas, közepes, alacsony, nagyon alacsony, nincs becslés).');
  } else if (est.length) err('"est" lists estimated values, so "confidence" is needed (high, medium, low, very low or none).');
  if (q === 'n' && est.length) warn('"confidence" is none, but "est" lists estimated values. Check which values are estimates.');

  let fortified = false;
  const fo = raw.fortified;
  if (fo === true || fo === 1 || (typeof fo === 'string' && /^true$/i.test(fo.trim()))) fortified = true;
  else if (fo !== undefined && fo !== null && fo !== false && fo !== 0 && !(typeof fo === 'string' && /^false$/i.test(fo.trim()))) warn('"fortified" should be true or false. It was ignored.');

  let nova = null;
  if (raw.nova !== undefined && raw.nova !== null && raw.nova !== '') {
    const v = aiNum(raw.nova);
    if ([1, 2, 3, 4].includes(v)) nova = v; else err('"nova" must be 1, 2, 3, 4 or null.');
  }

  const portions = [];
  if (raw.portions !== undefined && raw.portions !== null) {
    if (!Array.isArray(raw.portions)) err('"portions" must be a list, for example [{"label": "1 slice", "grams": 30}].');
    else {
      raw.portions.forEach((p, i) => {
        const ok = p && typeof p === 'object', l = ok ? str(p.label) : '', g = ok ? aiNum(p.grams) : NaN;
        if (!l || !(g > 0)) err(`Portion ${i + 1} needs a "label" and "grams" greater than 0.`);
        else portions.push({ label: l, grams: g });
      });
      if (basis && basis.unit !== 'g' && raw.portions.length) err('"portions" are only for foods measured per 100 g. Leave the list empty for a capsule or another single piece.');
    }
  }

  const note = str(raw.note);
  if (note.length > 1200) warn(`The note is ${note.length} characters long (the prompt asks for 1200 at most). It is kept in full.`);
  if (name.length > 120) warn(`The name is ${name.length} characters long (120 at most is expected). It is kept in full.`);
  if (brand.length > 80) warn(`The brand is ${brand.length} characters long (80 at most is expected). It is kept in full.`);
  if (barcode && !/^\d{8,14}$/.test(barcode)) warn(`The barcode “${barcode}” does not have 8 to 14 digits. Check it on the package.`);
  if (basis) warns.push(...aiChecks(n, basis));

  if (errs.length) { out.errors.push(...errs); return; }
  const food = { name, brand, barcode, basis, n, nova, portions, note };
  if (est.length) food.est = est;
  if (q) food.q = q;
  if (fortified) food.fortified = true;
  out.foods.push({ food, warnings: warns });
}
/* text -> { errors: [messages], foods: [{ food, warnings }] }. Any error stops the import: nothing is loaded from an answer that has an error. */
function parseAiImport(text) {
  const out = { errors: [], foods: [] };
  if (!String(text).trim()) { out.errors.push('Paste the answer of the AI first.'); return out; }
  const found = aiFindJson(text);
  if (!found.json) {
    out.errors.push(found.marker
      ? 'The answer has Nutrilog data, but it cannot be read as JSON. Often its end is missing because the answer was cut off: ask the AI to send only the JSON block again.'
      : 'No JSON found. Paste the whole answer of the AI, including the block that starts with { and has "nutrilog_import" in it.');
    return out;
  }
  const j = found.json;
  if (j.nutrilog_import === undefined && isFoodsFile(j)) {   // the v3 answer: foods in an object, the id is the key. The ids are not used here: the food editor gives a new one, and duplicates are found by barcode or name.
    if (Array.isArray(j.log)) { out.errors.push('This is a full backup, not the answer of an AI. Use “Restore from file” on the Data tab for a backup.'); return out; }
    const list = Object.values(j.foods);
    if (!list.length) { out.errors.push('“foods” is empty: there is nothing to read.'); return out; }
    list.forEach((raw, k) => aiFood(raw, k, list.length, out));
    if (out.errors.length) out.foods = [];
    return out;
  }
  const ver = typeof j.nutrilog_import === 'string' ? Number(j.nutrilog_import) : j.nutrilog_import;
  if (j.nutrilog_import === undefined) out.errors.push('The JSON has no "nutrilog_import" field. Is it the answer to the Nutrilog prompt? Use “Copy AI prompt” and ask again.');
  else if (ver !== AI_IMPORT_VERSION) out.errors.push(`This answer is version ${JSON.stringify(j.nutrilog_import)} of the import format, but this app reads version ${AI_IMPORT_VERSION}. Use “Copy AI prompt” in this app and ask again (or update the app: Data → Reload app files).`);
  if (out.errors.length) return out;
  if (!Array.isArray(j.foods) || !j.foods.length) { out.errors.push('"foods" must be a list with at least one food.'); return out; }
  j.foods.forEach((raw, k) => aiFood(raw, k, j.foods.length, out));
  if (out.errors.length) out.foods = [];
  return out;
}

/* ---- saving: the same food may already be there ---- */
const nameKey = (s) => norm(s).replace(/[^a-z0-9]+/g, ' ').trim();
function findDuplicate(f) {   // among the foods you made and the Open Food Facts products you saved: same barcode, or same name and brand
  const foods = Object.values(S.foods);
  if (/^\d{8,14}$/.test(f.barcode || '')) {
    const v = codeVariants(f.barcode), hit = foods.find((x) => x.barcode && v.includes(x.barcode));
    if (hit) return { food: hit, why: 'the same barcode' };
  }
  const key = nameKey(f.name) + '|' + nameKey(f.brand || '');
  const hit = foods.find((x) => nameKey(x.name) + '|' + nameKey(x.brand || '') === key);
  return hit ? { food: hit, why: 'the same name and brand' } : null;
}
function applyFoodFields(out, fields) {
  Object.assign(out, JSON.parse(JSON.stringify(fields)), { updated: Date.now() });   // a copy, so the food shares nothing with the list or form it came from
  for (const k of AI_FIELDS) if (!(k in fields)) delete out[k];   // an update must not keep the estimates of the old version
}
/* Save a food from an AI answer. When it is already there, ask: update the existing food, save a new one, or cancel (the caller stays open).
   done(food, how) runs after saving; how is 'new' or 'updated'. */
function saveImportedFood(fields, done) {
  const dup = findDuplicate(fields);
  const addNew = () => {
    const out = { id: 'u:' + uid(), src: 'user', created: Date.now() };
    applyFoodFields(out, fields);
    S.foods[out.id] = out; invalidate(); save();
    done(out, 'new');
  };
  if (!dup) { addNew(); return; }
  const ex = dup.food, used = S.log.filter((e) => e.f === ex.id).length;
  const sameBasis = ex.basis.qty === fields.basis.qty && ex.basis.unit === fields.basis.unit;
  const blocked = used > 0 && !sameBasis;
  const d = openSheet('Already in your foods', `
    <p style="margin:0 0 8px"><b>${esc(cap(ex.name))}</b>${ex.brand ? ' · ' + esc(ex.brand) : ''} is already saved (${dup.why}).</p>
    <p class="small muted" style="margin:0 0 8px"><b>Update existing</b> replaces its values with the imported ones. The food stays the same, so ${used ? `the <b>${used === 1 ? '1 diary entry' : used + ' diary entries'}</b> that ${used === 1 ? 'uses' : 'use'} it will show the new values` : 'diary entries that use it later will show the new values'}. You can undo it. <b>Save as new</b> keeps both foods.</p>
    ${blocked ? `<p class="note" role="alert">The saved food is measured per ${esc(basisText(ex.basis))}, the imported one per ${esc(basisText(fields.basis))}. The diary entries cannot be moved from one to the other, so use Save as new.</p>` : ''}
    <div class="sheet-actions col">
      <button class="btn primary block" data-dup="update" ${blocked ? 'disabled' : ''}>Update existing</button>
      <button class="btn block" data-dup="new">Save as new</button>
      <button class="btn block" data-dup="cancel">Cancel</button></div>`);
  d.el.addEventListener('click', (e) => {
    const b = e.target.closest('[data-dup]');
    if (!b || b.disabled) return;
    d.close();
    if (b.dataset.dup === 'new') addNew();
    else if (b.dataset.dup === 'update') {
      const before = { ...ex };   // the Undo copy; the values are replaced, not changed in place
      const m = { ...fields };
      if (!m.barcode && ex.barcode) m.barcode = ex.barcode;                       // what the import does not say stays as it was
      if (!m.nova && ex.nova) m.nova = ex.nova;
      if (!m.note && ex.note) m.note = ex.note;
      if (!m.portions.length && ex.basis.unit === 'g' && ex.portions && ex.portions.length) m.portions = ex.portions;
      applyFoodFields(ex, m);
      if (ex.src === 'off') ex.edited = true;
      invalidate(); save();
      toast('Updated: ' + cap(ex.name.length > 38 ? ex.name.slice(0, 37) + '…' : ex.name), () => { S.foods[before.id] = before; invalidate(); save(); render(); });
      done(ex, 'updated');
    }
  });
}

/* ---- the screens ---- */
function aiNotice(food, warnings) {
  const nAll = Object.keys(food.n).length, nEst = (food.est || []).length;
  return `<div class="banner" style="margin:0 0 12px"><b>From an AI answer, not saved yet.</b> ${nAll} ${nAll === 1 ? 'value' : 'values'}: ${nAll - nEst} from the label or converted, ${nEst} estimated${food.q ? ` (confidence ${CONF[food.q]})` : ''}. Compare them with the package, then tap Save.</div>`
    + (warnings.length ? `<div class="note" role="status"><b>Check these:</b><ul>${warnings.map((w) => `<li>${esc(w)}</li>`).join('')}</ul></div>` : '');
}
function openAiImport({ onSaved } = {}) {
  const sh = openSheet('Paste from AI', `
    <p class="small muted" style="margin:0 0 12px">Ask an AI (Claude, ChatGPT…) to look a product up with the Nutrilog prompt, then paste its answer here. Nothing is saved until you have reviewed the food and tapped Save. The pasted text is not kept and nothing is sent anywhere.</p>
    <div class="row gap"><button class="btn" id="ai-paste">Paste from clipboard</button><button class="btn" id="ai-copy">Copy AI prompt</button></div>
    <p class="small muted" id="ai-prompt-hint" style="margin:8px 0 0">The prompt works best in a Claude chat that can run code, with the file <b>ciqual_ref.json</b> attached. Without that file the AI gives label values only and does not estimate.</p>
    <label class="f" style="margin-top:12px">AI answer<textarea id="ai-text" rows="7" autocapitalize="off" autocorrect="off" spellcheck="false" placeholder="Paste the whole answer here. The JSON block is found automatically."></textarea></label>
    <div id="ai-msg" aria-live="polite"></div>
    <div class="row gap sheet-actions"><button class="btn" data-dx>Cancel</button><span style="flex:1"></span><button class="btn primary" id="ai-read">Read</button></div>`);
  const ta = $('#ai-text', sh.el), msg = $('#ai-msg', sh.el);
  const say = (html) => { msg.innerHTML = html; };
  const noteHtml = (t) => `<p class="note" role="alert">${t}</p>`;
  $('[data-dx]', sh.el).onclick = () => sh.close();
  ta.addEventListener('input', () => { ta.removeAttribute('aria-invalid'); say(''); });
  function readNow() {
    const r = parseAiImport(ta.value);
    if (r.errors.length) {
      ta.setAttribute('aria-invalid', 'true');
      say(`<div class="note field-err" role="alert"><b>${r.errors.length > 1 ? 'This answer cannot be loaded yet:' : 'This answer cannot be loaded:'}</b><ul>${r.errors.map((e) => `<li>${esc(e)}</li>`).join('')}</ul></div>`);
      return;
    }
    say(''); ta.removeAttribute('aria-invalid');
    if (r.foods.length === 1) {
      const { food, warnings } = r.foods[0];
      openFoodEditor(null, { prefill: food, title: 'Review imported food', notice: aiNotice(food, warnings), after: (f) => { sh.close(); if (onSaved) onSaved(f); } });
    } else openAiList(r.foods, { done: () => sh.close() });
  }
  $('#ai-read', sh.el).onclick = readNow;
  $('#ai-paste', sh.el).onclick = async () => {
    try {
      if (!navigator.clipboard || !navigator.clipboard.readText) throw new Error('no clipboard access');
      const t = await navigator.clipboard.readText();
      if (!t.trim()) { say(noteHtml('The clipboard is empty. Copy the answer of the AI first.')); return; }
      ta.value = t; readNow();   // no focus() here: it runs after waiting, outside the tap
    } catch {
      say(noteHtml('This browser did not let the app read the clipboard (on an iPhone you have to tap the “Paste” bubble that appears). Press and hold in the box above, choose <b>Paste</b>, then tap <b>Read</b>.'));
    }
  };
  $('#ai-copy', sh.el).onclick = async () => {
    const text = aiPrompt();
    try {
      if (!navigator.clipboard || !navigator.clipboard.writeText) throw new Error('no clipboard access');
      await navigator.clipboard.writeText(text);
      say(''); toast('AI prompt copied');
    } catch {
      say(`${noteHtml('This browser did not allow copying. The prompt is in the box below: press and hold in it, choose <b>Select All</b>, then <b>Copy</b>.')}<label class="f">AI prompt<textarea id="ai-prompt-box" rows="6" readonly>${esc(text)}</textarea></label>`);
    }
  };
  return sh;
}
/* several foods in one answer: a list; each one is reviewed (Review) or saved as it is (Save) by hand */
function openAiList(items, { done }) {
  const saved = items.map(() => '');   // '' = not yet, else 'Saved' or 'Updated'
  const row = ({ food, warnings }, i) => {
    const nAll = Object.keys(food.n).length, nEst = (food.est || []).length;
    return `<div class="card ai-row" data-i="${i}"><b>${esc(cap(food.name))}</b>
      <div class="muted small">${esc(food.brand ? food.brand + ' · ' : '')}per ${esc(basisText(food.basis))} · ${nAll} ${nAll === 1 ? 'value' : 'values'}${nEst ? `, ${nEst} estimated${food.q ? ' (' + CONF[food.q] + ')' : ''}` : ''}</div>
      ${warnings.length ? `<ul class="note ai-warn">${warnings.map((w) => `<li>${esc(w)}</li>`).join('')}</ul>` : ''}
      <div class="row gap" style="margin-top:10px">${saved[i] ? `<span class="tag ok">${saved[i]}</span>` : '<button class="btn" data-ai="review">Review</button><button class="btn primary" data-ai="save">Save</button>'}</div></div>`;
  };
  const sh = openSheet('Review imported foods', `
    <p class="small muted" style="margin:0 0 12px">${items.length} foods found. Nothing is saved yet. Tap <b>Review</b> to check and change a food, or <b>Save</b> to save it as it is.</p>
    <div id="ai-rows" class="stack">${items.map(row).join('')}</div>
    <div class="row gap sheet-actions"><span style="flex:1"></span><button class="btn primary" data-dx>Done</button></div>`);
  const redraw = (i) => { const el = $(`.ai-row[data-i="${i}"]`, sh.el); if (el) el.outerHTML = row(items[i], i); };
  const mark = (i) => (f, how) => { saved[i] = how === 'updated' ? 'Updated' : 'Saved'; redraw(i); if (how !== 'updated') toast('Food saved'); };
  $('[data-dx]', sh.el).onclick = () => { sh.close(); done(); };
  sh.el.addEventListener('click', (e) => {
    const b = e.target.closest('[data-ai]');
    if (!b) return;
    const i = Number(b.closest('.ai-row').dataset.i), { food, warnings } = items[i];
    if (b.dataset.ai === 'review') openFoodEditor(null, { prefill: food, title: 'Review imported food', notice: aiNotice(food, warnings), after: (f, how) => { saved[i] = how === 'updated' ? 'Updated' : 'Saved'; redraw(i); } });
    else saveImportedFood({ ...food }, mark(i));
  });
  return sh;
}

/* ================= export / import ================= */
function download(name, text, type) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text], { type }));
  a.download = name;
  document.body.append(a); a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1500);
}
const csvCell = (v) => { const s = v === null || v === undefined ? '' : String(v); return /[",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
const csvLine = (arr) => arr.map(csvCell).join(',');
const ucol = (i) => `${KEYS[i]}_${UNITS[i].replace('µ', 'u')}`;
const num6 = (v) => (Number.isFinite(v) ? prec(v) : '');
const BOM = '﻿';

function exportJson() {
  const clean = JSON.parse(JSON.stringify({ app: 'tapnaplo', version: 1, exported: new Date().toISOString(), log: S.log, foods: S.foods, meta: S.meta }, (k, v) => (k[0] === '_' ? undefined : v)));
  S.meta.backup = Date.now(); save();
  download(`nutrilog-backup-${ymd(new Date())}.json`, JSON.stringify(clean), 'application/json');
  toast('Backup downloaded'); if (S.tab === 'data') render();
}
function exportEntries() {
  const rows = [...S.log].filter((e) => getFood(e.f)).sort((a, b) => a.d.localeCompare(b.d) || byTime(a, b));
  const withMax = new Set(), withEst = new Set();
  const data = rows.map((e) => {
    const f = getFood(e.f), v = vecOf(f), k = e.a / f.basis.qty;
    const lo = [], hi = [], est = [];
    for (let i = 0; i < NUT_N; i++) {
      lo.push(Number.isNaN(v.lo[i]) ? '' : num6(v.lo[i] * k)); hi.push(Number.isNaN(v.hi[i]) ? '' : num6(v.hi[i] * k));
      if (!Number.isNaN(v.lo[i]) && v.hi[i] - v.lo[i] > 1e-12) withMax.add(i);
      est.push(isEst(f, i, v) ? 1 : 0); if (est[i]) withEst.add(i);
    }
    return { e, f, lo, hi, est };
  });
  const mi = [...withMax].sort((a, b) => a - b), ei = [...withEst].sort((a, b) => a - b);
  const head = ['date', 'time', 'meal', 'food_id', 'food', 'brand', 'source', 'amount', 'unit', 'nova', 'energy_estimated', 'estimate_confidence', 'est_keys', ...KEYS.map((_, i) => ucol(i)), ...mi.map((i) => ucol(i) + '__max'), ...ei.map((i) => ucol(i) + '__est')];
  const lines = [csvLine(head)];
  for (const { e, f, lo, hi, est } of data) {
    lines.push(csvLine([e.d, timeOf(e), (MEALS.find((m) => m.id === e.m) || {}).name, f.id, f.name, f.brand || (f.src === 'dmbio' ? 'dmBio' : ''), f.src, e.a, f.basis.unit, novaOf(f) || '', energyEstimated(f) ? 1 : 0, (f.q && CONF[f.q]) || '', KEYS.filter((_, i) => est[i]).join(';'), ...lo, ...mi.map((i) => hi[i]), ...ei.map((i) => est[i])]));
  }
  download(`nutrilog-entries-${ymd(new Date())}.csv`, BOM + lines.join('\n'), 'text/csv;charset=utf-8');
}
/* How much of a day is estimated, as one percentage (one decimal). Amounts of different nutrients cannot be added, so every tracked nutrient that has data and a total above 0
   gets its own share (estimated part of the lower value / the whole), and the shares are averaged. Empty when no nutrient qualifies. */
function estShare(entries) {
  const tot = new Float64Array(NUT_N), est = new Float64Array(NUT_N);
  for (const e of entries) {
    const f = getFood(e.f);
    if (!f) continue;
    const v = vecOf(f), k = e.a / f.basis.qty;
    for (const i of TRACKED) {
      if (Number.isNaN(v.lo[i])) continue;
      tot[i] += v.lo[i] * k;
      if (isEst(f, i, v)) est[i] += v.lo[i] * k;
    }
  }
  let sum = 0, c = 0;
  for (const i of TRACKED) if (tot[i] > 0) { sum += est[i] / tot[i]; c++; }
  return c ? Math.round(1000 * sum / c) / 10 : '';
}
function exportDays() {
  const days = [...new Set(S.log.filter((e) => getFood(e.f)).map((e) => e.d))].sort();
  const per = days.map((d) => ({ d, T: totalsFor(entriesOf(d)) }));
  const withMax = new Set();
  per.forEach(({ T }) => { for (let i = 0; i < NUT_N; i++) if (T.cnt[i] && T.hi[i] - T.lo[i] > 1e-9) withMax.add(i); });
  const mi = [...withMax].sort((a, b) => a - b);
  const ei = KEYS.map((_, i) => i).filter((i) => per.some(({ T }) => T.est[i] > 0));
  const head = ['date', 'entries', 'est_share', ...KEYS.map((_, i) => ucol(i)), ...mi.map((i) => ucol(i) + '__max'), ...ei.map((i) => ucol(i) + '__est'), ...KEYS.map((_, i) => KEYS[i] + '__n')];
  const lines = [csvLine(head)];
  for (const { d, T } of per) {
    lines.push(csvLine([d, T.n, estShare(entriesOf(d)), ...KEYS.map((_, i) => (T.cnt[i] ? num6(T.lo[i]) : '')), ...mi.map((i) => (T.cnt[i] ? num6(T.hi[i]) : '')), ...ei.map((i) => T.est[i]), ...KEYS.map((_, i) => T.cnt[i])]));
  }
  download(`nutrilog-daily-totals-${ymd(new Date())}.csv`, BOM + lines.join('\n'), 'text/csv;charset=utf-8');
}
function importJson(file) {
  const rd = new FileReader();
  rd.onload = () => {
    try {
      const j = JSON.parse(rd.result);
      if (isFoodsFile(j) && !Array.isArray(j.log)) throw new Error('this file has foods but no diary. Use “Import foods (JSON)” to add its foods.');
      if (j.app !== 'tapnaplo' || !Array.isArray(j.log) || typeof j.foods !== 'object') throw new Error('this is not a Nutrilog backup file.');
      Object.values(j.foods).forEach(normConfidence);
      const nE = j.log.length, nF = Object.keys(j.foods).length;
      askConfirm({
        title: 'Replace your data?', danger: true, okLabel: 'Replace',
        text: `This replaces everything in the app with the backup: ${nE === 1 ? '1 entry' : nE + ' entries'} and ${nF === 1 ? '1 food' : nF + ' foods'}. Save a backup of the current data first if you are not sure.${SY.cfg ? ' Sync is on, so your other devices will get the restored data as well.' : ''}`,
        onOk: () => {
          S.log = j.log; S.foods = j.foods; S.meta = Object.assign(metaDefaults(), j.meta || {});
          invalidate(); save(); render(); toast('Restored');
        },
      });
    } catch (err) { toast('Could not restore: ' + err.message); }
  };
  rd.readAsText(file);
}

/* A foods file from the v3 prompt names the confidence in words ("confidence": "alacsony"). The app keeps a letter (q), so a restore turns the word into it. */
function normConfidence(f) {
  if (!f || typeof f !== 'object' || !('confidence' in f)) return;
  if (!f.q) { const q = aiConf(f.confidence); if (q) f.q = q; }
  delete f.confidence;
}

/* ================= Import foods (JSON) ================= */
/* Adds the foods of a Nutrilog file to My foods. The file has the shape of a backup ({ "app": "tapnaplo", "foods": { "<id>": { … } } }), but only "foods" is read:
   "log" and "meta" are ignored, so the diary is never touched. Only foods you made (ids starting with "u:") are imported. Every food is checked with the rules of
   "Paste from AI" (aiFood). A food whose id is already there is never overwritten without asking: the person chooses Skip or Overwrite. */
function parseFoodsFile(text) {
  const out = { error: '', foods: [], invalid: [], other: [], total: 0 };
  const raw = String(text).replace(/^﻿/, '');
  let j;
  try { j = JSON.parse(raw); } catch { j = aiFindJson(raw).json; }   // a pasted-into-a-file answer may still have a ``` fence or a sentence around it
  if (!j || typeof j !== 'object' || Array.isArray(j) || j.app !== 'tapnaplo') { out.error = 'This is not a Nutrilog file. A file from this app or from the Nutrilog AI prompt has "app": "tapnaplo" at the top.'; return out; }
  if (j.version !== undefined && Number(j.version) !== 1) { out.error = `This file is version ${JSON.stringify(j.version)} of the format, but this app reads version 1.`; return out; }
  if (!j.foods || typeof j.foods !== 'object' || Array.isArray(j.foods)) { out.error = 'The file has no “foods” part, so there is nothing to import.'; return out; }
  const entries = Object.entries(j.foods);
  if (!entries.length) { out.error = 'The “foods” part of the file is empty.'; return out; }
  out.total = entries.length;
  const now = Date.now();
  for (const [id, r] of entries) {
    const isObj = r && typeof r === 'object' && !Array.isArray(r);
    const shown = isObj && typeof r.name === 'string' && r.name.trim() ? r.name.trim() : id;
    if (!id.startsWith('u:')) { out.other.push({ id, name: shown }); continue; }
    if (!isObj) { out.invalid.push({ id, name: shown, reasons: ['It is not an object.'] }); continue; }
    const one = { errors: [], foods: [] };
    if (r.id !== undefined && String(r.id) !== id) one.errors.push(`Its "id" (${JSON.stringify(r.id)}) is not the same as its key (${JSON.stringify(id)}).`);
    aiFood(r, 0, 1, one);
    if (one.errors.length || !one.foods.length) { out.invalid.push({ id, name: shown, reasons: one.errors }); continue; }
    const c = Number(r.created);
    out.foods.push({ id, food: one.foods[0].food, warnings: one.foods[0].warnings, created: Number.isFinite(c) && c > 0 ? c : now });
  }
  return out;
}
/* Which of the importable foods are new, which have an id that is already there, and which of those cannot be overwritten
   (the unit differs and diary entries use the food, so the amounts would change their meaning). */
function planFoodsImport(parsed) {
  const clash = [], fresh = [], blocked = [];
  for (const x of parsed.foods) {
    const ex = S.foods[x.id];
    if (!ex) { fresh.push(x); continue; }
    clash.push(x);
    if (S.log.some((e) => e.f === x.id) && !(ex.basis.qty === x.food.basis.qty && ex.basis.unit === x.food.basis.unit)) blocked.push(x);
  }
  return { clash, fresh, blocked, like: fresh.filter((x) => findDuplicate(x.food)) };
}
function applyFoodsImport(parsed, overwrite) {
  const plan = planFoodsImport(parsed), now = Date.now(), changes = [];
  let added = 0, replaced = 0, kept = 0;
  for (const x of parsed.foods) {
    const ex = S.foods[x.id];
    if (ex && !(overwrite && !plan.blocked.includes(x))) { kept++; continue; }
    S.foods[x.id] = { id: x.id, src: 'user', created: ex && ex.created > 0 ? ex.created : x.created, ...JSON.parse(JSON.stringify(x.food)), updated: now };
    changes.push({ id: x.id, before: ex });   // the old object is kept as it was, for Undo
    if (ex) replaced++; else added++;
  }
  if (changes.length) { invalidate(); save(); }
  return { added, replaced, kept, changes };
}
function undoFoodsImport(changes) {
  const used = new Set(S.log.map((e) => e.f));
  for (const c of changes) {
    if (c.before) S.foods[c.id] = c.before;
    else if (!used.has(c.id)) delete S.foods[c.id];   // a new food that a diary entry already uses stays, so no entry loses its food
  }
  invalidate(); save(); render();
}
function finishFoodsImport(parsed, res) {
  const n = res.added + res.replaced, plural = (k, one, many) => `${k} ${k === 1 ? one : many}`;
  const parts = [n ? `Imported ${plural(n, 'food', 'foods')}` : 'Nothing imported'];
  if (res.replaced) parts.push(`${res.replaced} overwritten`);
  if (res.kept) parts.push(`${res.kept} kept as ${res.kept === 1 ? 'it was' : 'they were'}`);
  if (parsed.invalid.length) parts.push(`${parsed.invalid.length} invalid skipped`);
  if (parsed.other.length) parts.push(`${parsed.other.length} with other ids skipped`);
  toast(parts.join(' · '), n ? () => undoFoodsImport(res.changes) : undefined);
  if (S.tab === 'data' || S.tab === 'foods') render();
}
function openFoodsImportSheet(parsed, plan) {
  const nf = (k) => `${k} ${k === 1 ? 'food' : 'foods'}`;
  const list = (xs, max, f) => esc(xs.slice(0, max).map(f).join(', ')) + (xs.length > max ? ` and ${xs.length - max} more` : '');
  const nm = (x) => cap(x.food ? x.food.name : x.name);
  const html = [`<p style="margin:0 0 10px">The file has ${nf(parsed.total)}. ${nf(parsed.foods.length)} can be imported: ${plan.fresh.length} new${plan.clash.length ? ', ' + plan.clash.length + ' with an id that is already in My foods' : ''}.</p>`];
  if (plan.clash.length) {
    html.push(`<p class="small" style="margin:0 0 8px"><b>Already there:</b> ${list(plan.clash, 8, nm)}.</p>`);
    html.push(`<p class="small muted" style="margin:0 0 8px"><b>Skip</b> keeps your versions and adds only the new foods. <b>Overwrite</b> replaces your versions with the ones from the file; the diary entries that use them then show the new values.${plan.blocked.length ? ` ${list(plan.blocked, 5, nm)} cannot be overwritten: the unit differs and diary entries use the food. ${plan.blocked.length === 1 ? 'It stays' : 'They stay'} as ${plan.blocked.length === 1 ? 'it is' : 'they are'}.` : ''}</p>`);
  }
  if (parsed.invalid.length) {
    html.push(`<div class="note" role="status"><b>${parsed.invalid.length} ${parsed.invalid.length === 1 ? 'entry is' : 'entries are'} not valid and will be skipped:</b><ul>${parsed.invalid.slice(0, 5).map((x) => `<li>${esc(cap(x.name))}: ${esc(x.reasons[0] || 'not valid.')}</li>`).join('')}${parsed.invalid.length > 5 ? `<li>and ${parsed.invalid.length - 5} more</li>` : ''}</ul></div>`);
  }
  if (parsed.other.length) {
    html.push(`<p class="small muted" style="margin:0 0 8px">${parsed.other.length} ${parsed.other.length === 1 ? 'entry has' : 'entries have'} an id that does not start with “u:” (saved Open Food Facts products, for example). Only foods you made are imported, so ${parsed.other.length === 1 ? 'it is' : 'they are'} left out.</p>`);
  }
  if (plan.like.length) {
    html.push(`<div class="note" role="status"><b>Look like foods you already have</b> (same barcode, or same name and brand): ${list(plan.like, 5, nm)}. They are added as separate foods. Delete the extra ones in My foods if you do not want both.</div>`);
  }
  const warned = parsed.foods.filter((x) => x.warnings.length);
  if (warned.length) {
    html.push(`<div class="note" role="status"><b>Check these values after the import:</b><ul>${warned.slice(0, 5).map((x) => `<li>${esc(nm(x))}: ${esc(x.warnings[0])}</li>`).join('')}${warned.length > 5 ? `<li>and ${warned.length - 5} more</li>` : ''}</ul></div>`);
  }
  html.push(plan.clash.length
    ? '<div class="sheet-actions col"><button class="btn primary block" data-fi="skip">Skip</button><button class="btn danger block" data-fi="over">Overwrite</button><button class="btn block" data-fi="cancel">Cancel</button></div>'
    : `<div class="sheet-actions col"><button class="btn primary block" data-fi="skip">Import ${nf(parsed.foods.length)}</button><button class="btn block" data-fi="cancel">Cancel</button></div>`);
  const d = openSheet('Import foods', html.join(''));
  d.el.addEventListener('click', (e) => {
    const b = e.target.closest('[data-fi]');
    if (!b) return;
    d.close();
    if (b.dataset.fi !== 'cancel') finishFoodsImport(parsed, applyFoodsImport(parsed, b.dataset.fi === 'over'));
  });
}
function importFoods(file) {
  const say = (html) => { const m = $('#fimp-msg'); if (m) m.innerHTML = html; };
  const fail = (t) => say(`<p class="note field-err" role="alert">${esc(t)}</p>`);
  say('');
  const rd = new FileReader();
  rd.onerror = () => fail('The file could not be read.');
  rd.onload = () => {
    const parsed = parseFoodsFile(rd.result);
    if (parsed.error) { fail(parsed.error); return; }
    if (!parsed.foods.length) {
      const why = parsed.invalid.slice(0, 3).map((x) => `${cap(x.name)}: ${x.reasons[0] || 'not valid.'}`).join(' ');
      fail(`No food could be imported. ${why || (parsed.other.length ? 'Only foods you made (ids starting with “u:”) are imported.' : '')}`.trim());
      return;
    }
    const plan = planFoodsImport(parsed);
    if (plan.clash.length || parsed.invalid.length || parsed.other.length || plan.like.length || parsed.foods.some((x) => x.warnings.length)) openFoodsImportSheet(parsed, plan);
    else finishFoodsImport(parsed, applyFoodsImport(parsed, false));
  };
  rd.readAsText(file);
}

/* ================= events ================= */
document.addEventListener('click', (ev) => {
  const t = ev.target.closest('[data-act]');
  if (!t) return;
  const a = t.dataset.act;
  if (a === 'tab') { S.tab = t.dataset.tab; try { localStorage.setItem('nutrilog.tab', S.tab); } catch { /* private mode */ } render(); window.scrollTo(0, 0); }
  else if (a === 'day') { S.day = addDays(S.day, +t.dataset.n); render(); }
  else if (a === 'today') { S.day = ymd(new Date()); render(); }
  else if (a === 'add') addFlow(t.dataset.meal || defaultMeal());
  else if (a === 'scan') { const pk = addFlow(defaultMeal()); const b = $('[data-a=scan]', pk.el); if (b) b.click(); }
  else if (a === 'edit-entry') { const e = S.log.find((x) => x.id === t.dataset.id); if (e) openAmount({ food: getFood(e.f), entry: e }); }
  else if (a === 'new-food') openFoodEditor(null);
  else if (a === 'ai-import') openAiImport({});
  else if (a === 'edit-food') { const f = S.foods[t.dataset.id]; if (f) openFoodEditor(f); }
  else if (a === 'export-json') exportJson();
  else if (a === 'sync-setup') openSyncSetup();
  else if (a === 'sync-now') syncRun('manual');
  else if (a === 'sync-off') syncOff();
  else if (a === 'nova-set') novaTap(t.dataset.id, Number(t.dataset.v));
  else if (a === 'theme') {
    setTheme(t.dataset.v);
    $$('[data-act=theme]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.v === t.dataset.v)));
  }
  else if (a === 'export-entries') exportEntries();
  else if (a === 'export-days') exportDays();
  else if (a === 'refresh-app') refreshApp();
  else if (a === 'persist') {
    (navigator.storage && navigator.storage.persist ? navigator.storage.persist() : Promise.resolve(false)).then((ok) => { toast(ok ? 'Persistent storage enabled' : 'The browser declined. Install the app to your home screen and back up regularly.'); persistState(); });
  }
});
/* 'toggle' does not bubble, so listen while it travels down (third argument true) */
document.addEventListener('toggle', (ev) => { if (ev.target.id === 'novafold') novaOpen = ev.target.open; }, true);
document.addEventListener('change', (ev) => {
  if (ev.target.id === 'datepick' && ev.target.value) { S.day = ev.target.value; render(); }
  if (ev.target.id === 'importfile' && ev.target.files[0]) { importJson(ev.target.files[0]); ev.target.value = ''; }
  if (ev.target.id === 'importfoods' && ev.target.files[0]) { importFoods(ev.target.files[0]); ev.target.value = ''; }
});
document.addEventListener('input', (ev) => {
  if (ev.target.id === 'ffilter') { S.filter = ev.target.value; $('#flist').innerHTML = foodListHtml(); }
});
/* Forget the saved copy of the app files and load them again. The diary lives in IndexedDB and is not touched. */
async function refreshApp() {
  if (!navigator.onLine) { toast('You are offline. Connect to the internet first.'); return; }
  toast('Reloading app files…');
  try {
    if ('serviceWorker' in navigator) for (const r of await navigator.serviceWorker.getRegistrations()) await r.unregister();
    if (window.caches) for (const k of await caches.keys()) await caches.delete(k);
  } catch { /* reload anyway */ }
  location.reload();
}
/* The meal of the most recent entry on the day shown; Meal 1 when the day is still empty. */
function defaultMeal() {
  const last = S.log.filter((e) => e.d === S.day).sort((a, b) => b.t - a.t)[0];
  return last && MEALS.some((m) => m.id === last.m) ? last.m : MEALS[0].id;
}
function persistState() {
  const el = $('#persist-state');
  if (!el) return;
  if (!(navigator.storage && navigator.storage.persisted)) { el.textContent = 'This browser cannot tell whether your diary is protected. Back up regularly.'; return; }
  navigator.storage.persisted().then((p) => {
    el.innerHTML = p ? '<b>Persistent:</b> the browser keeps your diary unless you clear the site data. Still back up now and then.'
      : '<b>Not persistent:</b> the browser may clear your diary if the device runs low on space. Back up regularly and add the app to your home screen.';
  }).catch(() => { el.textContent = 'Could not check the storage status.'; });
}

/* ================= start ================= */
async function loadCatalog() {
  const [r, ru, rd] = await Promise.all([fetch('ciqual.json'), fetch('usda.json').catch((e) => e), fetch('dmbio.json').catch((e) => e)]);   // the three files load at the same time
  if (!r.ok) throw new Error('ciqual.json could not be loaded (HTTP ' + r.status + ').');
  CAT = await r.json();
  KEYS = CAT.nutrients.map((n) => n.key);
  UNITS = CAT.nutrients.map((n) => n.unit);
  NUT_N = KEYS.length;
  KEYS.forEach((k, i) => { IDX[k] = i; });
  TRACKED = KEYS.map((_, i) => i).filter((i) => ['mac', 'fa', 'min', 'vit'].includes(groupOf(i)) && KEYS[i] !== 'water');   // water is shown with the macronutrients, but it is not a nutrient that has to be "known"
  CIQ = CAT.foods.map((f) => ({
    id: 'c:' + f.c, src: 'ciqual', name: f.n, group: [f.G, f.g].filter(Boolean).join(' › '),
    basis: { qty: 100, unit: 'g' }, portions: [], nova: null, estE: !!f.e, _cells: f.v, _nn: norm(f.n),
  }));
  CIQ_BY_ID = new Map(CIQ.map((f) => [f.id, f]));
  /* USDA is a second source of generic foods. CIQUAL is the base: the app still starts if usda.json cannot be read. */
  try {
    if (!ru || !ru.ok) throw new Error(ru && ru.status ? 'HTTP ' + ru.status : 'no connection');
    const U = await ru.json();
    if (!Array.isArray(U.keys) || U.keys.join() !== KEYS.join()) throw new Error('its nutrient list differs from ciqual.json');
    USDA = U.foods.map((f) => ({
      id: 'usda:' + f.c, src: 'usda', name: f.n, group: f.g || '',
      basis: { qty: 100, unit: 'g' }, portions: (f.p || []).map(([label, grams]) => ({ label, grams })), nova: null, estE: !!f.e, _cells: f.v, _nn: norm(f.n),
    }));
    for (const f of USDA) CIQ_BY_ID.set(f.id, f);
  } catch (err) { USDA = []; USDA_ERR = (err && err.message) || 'unknown error'; }
  /* dmBio (dm.hu products) is also optional: the app still starts without it */
  try {
    if (!rd || !rd.ok) throw new Error(rd && rd.status ? 'HTTP ' + rd.status : 'no connection');
    const D = await rd.json();
    if (!Array.isArray(D.keys) || D.keys.join() !== KEYS.join()) throw new Error('its nutrient list differs from ciqual.json');
    DMBIO = D.foods.map((f) => ({
      id: 'dm:' + f.c, src: 'dmbio', name: f.n, brand: '', group: f.q === 'n' ? 'no micronutrient estimate' : 'micronutrient estimate: ' + CONF[f.q], barcode: f.b,
      basis: { qty: 100, unit: 'g' }, portions: (f.p || []).map(([label, grams]) => ({ label, grams })), nova: null, estE: false,
      q: f.q, fortified: !!f.f, url: f.u, info: f.x || '', _lab: new Set(f.l), _cells: f.v, _nn: norm(f.n + ' dmbio'),
    }));
    for (const f of DMBIO) CIQ_BY_ID.set(f.id, f);
  } catch (err) { DMBIO = []; DM_ERR = (err && err.message) || 'unknown error'; }
}

async function init() {
  try {
    await Promise.all([Store.open(), loadCatalog()]);
    const [log, foods, meta, sy] = await Promise.all([Store.get('log'), Store.get('foods'), Store.get('meta'), Store.get('sync')]);
    if (Array.isArray(log)) S.log = log;
    if (foods && typeof foods === 'object') S.foods = foods;
    if (meta && typeof meta === 'object') S.meta = Object.assign(metaDefaults(), meta);
    if (sy && typeof sy === 'object') Object.assign(SY, { cfg: sy.cfg || null, rec: sy.rec || {}, shas: sy.shas || {}, last: sy.last || 0, born: sy.born || 0, info: sy.info || '' });
    try { const tab = localStorage.getItem('nutrilog.tab'); if (TABS.some((x) => x[0] === tab)) S.tab = tab; } catch { /* private mode */ }
    if (syncStamp()) await Store.set('sync', syncPersist());   // changes made while the app was closed, and the first start with Sync built in
    render();
    if ('serviceWorker' in navigator && /^https?:$/.test(location.protocol)) navigator.serviceWorker.register('sw.js').catch(() => {});
    syncStart();
  } catch (err) {
    $('#view').innerHTML = `<div class="card" style="margin-top:16px"><div class="card-t">The app could not start.</div><p class="muted small" style="margin-top:6px">${esc(err.message)}</p><p class="muted small" style="margin-top:6px">If you opened the file straight from your computer, upload the files to a host (for example GitHub Pages) or start a local web server.</p></div>`;
  }
}
/* Sync runs at start, when the app comes back to the front, when the network returns, every 5 minutes while it is in front, and a few seconds after each change */
function syncStart() {
  syncRun('start');   // does nothing while Sync is not connected; the listeners below are in place for when it gets connected
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible' && Date.now() - SY.ranAt > 20000) syncRun('front'); });
  window.addEventListener('online', () => syncRun('online'));
  setInterval(() => { if (document.visibilityState === 'visible') syncRun('timer'); }, 300000);
}
window.__tapnaplo = { SY, syncRun, syncStamp, syncRecords, canon, S, HU: DICT, vecOf, totalsFor, searchCiqual, searchUsda, getFood, offToFood, fmt, novaOf, setNova, novaStats, sharePct, get KEYS() { return KEYS; }, get IDX() { return IDX; }, get USDA() { return USDA; }, get DMBIO() { return DMBIO; }, searchDm, isEst, CONF, trackedEst, render, save, parseAiImport, aiPrompt, findDuplicate, estSet, AI_IMPORT_VERSION, parseFoodsFile, planFoodsImport, estShare, aiConf };
init();

})();
