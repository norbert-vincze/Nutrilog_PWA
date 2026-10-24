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
const prec = (v) => Number(Number(v).toPrecision(6));
const num = (s) => parseFloat(String(s).replace(',', '.'));        // accepts 1.5 and 1,5
const TOUCH = !!(window.matchMedia && window.matchMedia('(pointer: coarse)').matches);   // phone or tablet
const VERSION = '10 · 24 Oct 2026';   // shown in the Data tab; raise it (and CACHE in sw.js) with every change
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
   and every dmBio value that is not on the dm label (f._lab = indexes of the label values; f.q = confidence of the estimate). */
const CONF = { h: 'high', m: 'medium', l: 'low', v: 'very low', n: 'none' };
const energyEstimated = (f) => !!f._cells && (!!f.estE || (!!f._lab && !f._lab.has(0) && !Number.isNaN(vecOf(f).lo[0])));
function isEst(f, i, v) {
  if (Number.isNaN(v.lo[i])) return false;
  return i === 0 ? energyEstimated(f) : !!f._lab && !f._lab.has(i);
}
function invalidate() { for (const f of Object.values(S.foods)) delete f._vec; }

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
  try { navigator.storage?.persist?.(); } catch { /* not critical */ }
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
  const api = {
    el: body, wrap, onClose: null,
    close() {
      const i = sheets.indexOf(api);
      if (i < 0) return;
      sheets.splice(i, 1);
      wrap.remove();
      if (api.onClose) api.onClose();
      if (!sheets.length) document.body.classList.remove('noscroll');
    },
  };
  wrap.addEventListener('click', (ev) => { if (ev.target === wrap || ev.target.closest('[data-x]')) api.close(); });
  $('#sheets').append(wrap);
  sheets.push(api);
  document.body.classList.add('noscroll');
  return api;
}
document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && sheets.length) sheets[sheets.length - 1].close(); });

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
    ${estE ? '<div class="banner">~ means the energy was calculated from protein, carbohydrate and fat (generic food data, Atwater factors).</div>' : ''}
    ${nova}${empty}${meals}`;
}

/* ---- Nutrients ---- */
function viewNutr() {
  const es = entriesOf(S.day);
  if (!es.length) return '<div class="card" style="margin-top:16px"><div class="card-t">Nothing logged for this day</div><p class="muted small" style="margin-top:6px">The daily nutrient summary is built from the foods you log in the Diary tab.</p><button class="btn primary" data-act="tab" data-tab="log" style="margin-top:14px">Go to Diary</button></div>';
  const T = totalsFor(es);
  const note = '<div class="banner">Missing data is not zero. Totals only include items that have data (the badge on the right shows how many items out of all), so they are lower estimates. Ranges come from values reported as “&lt; x” (below the detection limit).</div>'
    + (T.est.some((x) => x > 0) ? '<div class="banner">A <b>~</b> in front of a value means that part of it is an estimate, not a label value: energy calculated from protein, carbohydrate and fat, or dmBio values estimated from the ingredient list. Open a row to see which items and how confident the estimate is.</div>' : '');
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
  return `<div class="row gap" style="margin:8px 0 14px"><button class="btn primary" data-act="new-food">${IC.plus.replace('<svg', '<svg width="18" height="18"')} Create food</button></div>
    <input type="search" class="search" id="ffilter" placeholder="Search my foods" value="${esc(S.filter)}" aria-label="Search my foods">
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
      <p class="muted small" style="margin:6px 0 14px">Your data lives only on this device, in this browser. Back up regularly and before switching devices. Last backup: ${esc(b)}.</p>
      <div class="row gap"><button class="btn primary" data-act="export-json">Save backup (JSON)</button><label class="btn" style="cursor:pointer">Restore from file<input type="file" id="importfile" accept="application/json,.json" hidden></label></div></div>
    <div class="card"><div class="card-t">For analysis</div>
      <p class="muted small" style="margin:6px 0 14px">Spreadsheet files (CSV, decimal points). An empty cell means no data, a 0 is a real zero. Some labels report a value as “&lt; x” (below the detection limit). Then the normal column holds the lowest possible value, 0, and the max-value column (its name ends in __max) holds x. A column whose name ends in __est marks values that are estimates, not label values (1 for an entry, a count of items for a day).</p>
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
    <input id="q" type="search" class="search" inputmode="search" autocomplete="off" placeholder="Search: egg, tojás, bread, kenyér…" aria-label="Search foods">
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
    html += `<div class="row gap" style="margin-top:16px"><button class="btn${notFound ? ' primary' : ''}" data-a="new">+ Create food from label</button></div>`;
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
          offMsg = `Open Food Facts does not have barcode ${code}. It is a community database, so some products are missing, especially supplements and items from outside Europe. Tap “Create food from label” and copy the values from the package. The barcode is filled in, so the next scan finds the product in your own foods.`;
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
  });
  q.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); const t = q.value.replace(/\s/g, ''); if (/^\d{8,14}$/.test(t)) runOff(t); } });
  paint();
  /* iPhone: the keyboard only opens if focus() runs inside the tap that opened the sheet; elsewhere do it with a short delay */
  if (TOUCH) { try { q.focus({ preventScroll: true }); } catch { /* the field can be tapped */ } } else setTimeout(() => q.focus(), 60);
  return sh;
}

/* ================= barcode scanner ================= */
function scanBarcode(onCode) {
  const sh = openSheet('Scan barcode', `
    <video id="scan-v" playsinline muted autoplay></video>
    <p class="muted small" id="scan-msg">Point the camera at the barcode. Your browser will ask for camera permission. This only works on HTTPS.</p>
    <div class="row gap" style="flex-wrap:nowrap"><input id="scan-manual" type="text" inputmode="numeric" placeholder="or type the number" style="flex:1" aria-label="Barcode number"><button class="btn primary" id="scan-go">Look up</button></div>`);
  const video = $('#scan-v', sh.el), msg = $('#scan-msg', sh.el);
  let stream = null, timer = null, reader = null, done = false;
  const stop = () => { done = true; clearInterval(timer); if (reader && reader.reset) try { reader.reset(); } catch { /* nothing */ } if (stream) stream.getTracks().forEach((t) => t.stop()); };
  sh.onClose = stop;
  const found = (code) => { if (done) return; stop(); sh.close(); onCode(String(code)); };
  $('#scan-go', sh.el).onclick = () => { const v = $('#scan-manual', sh.el).value.replace(/\s/g, ''); if (/^\d{6,14}$/.test(v)) found(v); else msg.textContent = 'Barcodes have 8–14 digits.'; };
  (async () => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { video.hidden = true; msg.textContent = 'This browser cannot open the camera (HTTPS is required). Type the barcode number instead.'; return; }
    try {
      if ('BarcodeDetector' in window) {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false });
        if (done) { stream.getTracks().forEach((t) => t.stop()); return; }
        video.srcObject = stream;
        await video.play().catch(() => {});
        const det = new window.BarcodeDetector({ formats: ['ean_13', 'ean_8', 'upc_a', 'upc_e'] });
        timer = setInterval(async () => { try { const r = await det.detect(video); if (r[0]) found(r[0].rawValue); } catch { /* next frame */ } }, 300);
      } else {
        msg.textContent = 'Loading scanner…';
        await loadScript('zxing.min.js');
        if (done) return;
        reader = new window.ZXing.BrowserMultiFormatReader();
        msg.textContent = 'Point the camera at the barcode.';
        await reader.decodeFromConstraints({ video: { facingMode: 'environment' }, audio: false }, video, (res) => { if (res) found(res.getText()); });
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
function openAmount({ food, entry, meal, afterAdd }) {
  const unitG = isG(food);
  const start = entry ? entry.a : (S.meta.last[food.id] ?? (startPortion(food) ? startPortion(food).grams : unitG ? 100 : 1));
  const chips = (unitG ? [...portionsOf(food).map((p) => [p.label, p.grams]), ...[10, 30, 50, 100, 200].map((g) => [g + ' g', g])] : [0.5, 1, 2, 3].map((x) => [x + ' ' + food.basis.unit, x]));
  const startTime = (entry && timeOf(entry)) || hm(new Date());   // new entry: now; existing entry: the saved time
  const sh = openSheet(entry ? 'Edit entry' : 'Amount', `
    <div class="row gap" style="flex-wrap:nowrap">${avatar(food.name)}<div style="min-width:0"><b>${esc(cap(food.name))}</b><br><span class="muted small">${esc(food.brand || '')} ${esc(srcTag(food))}${unitG ? '' : ' · unit: ' + esc(food.basis.unit)}</span></div></div>
    <label class="f">Amount (${esc(food.basis.unit)})<input type="text" inputmode="decimal" id="amt" value="${esc(String(start))}"></label>
    <p class="note field-err" id="amterr" role="alert" hidden>Enter an amount greater than 0.</p>
    <div class="chips" id="chips">${chips.map(([l, v]) => `<button class="chip-btn" data-v="${v}">${esc(l)}</button>`).join('')}</div>
    ${unitG ? '<button class="chip-btn accent" id="saveportion" style="justify-self:start">+ Save as portion</button>' : ''}
    <div class="grid2">
      <label class="f">Meal<select id="meal">${MEALS.map((m) => `<option value="${m.id}" ${m.id === (entry ? entry.m : meal) ? 'selected' : ''}>${m.name}</option>`).join('')}</select></label>
      <label class="f">Time<input type="time" id="tm" value="${startTime}"></label>
    </div>
    <p class="note field-err" id="tmerr" role="alert" hidden>Enter a time, for example 13:45.</p>
    <div class="card" id="prev"></div>
    ${dmInfo(food)}
    <div class="row gap">${entry ? '<button class="btn danger" id="del">Delete</button>' : ''}${food._cells ? '' : '<button class="btn" id="editfood">Edit food</button>'}<span style="flex:1"></span><button class="btn primary" id="ok"></button></div>`);
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
  tm.addEventListener('input', () => { tmerr.hidden = true; tm.removeAttribute('aria-invalid'); });
  ok.onclick = () => {
    const a = val(), tmv = tm.value;
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
  const d = openSheet(title, `<p>${esc(text)}</p><div class="row gap"><button class="btn" data-dx>Cancel</button><span style="flex:1"></span><button class="btn ${danger ? 'danger' : 'primary'}" data-ok>${esc(okLabel)}</button></div>`);
  $('[data-dx]', d.el).onclick = () => d.close();
  $('[data-ok]', d.el).onclick = () => { d.close(); onOk(); };
  return d;
}
function askText({ title, label, value = '', okLabel = 'Save', onOk }) {
  const d = openSheet(title, `<label class="f">${esc(label)}<input type="text" id="ask-v" value="${esc(value)}" maxlength="40"></label>
    <p class="note field-err" id="ask-err" role="alert" hidden>Type a name first.</p>
    <div class="row gap"><button class="btn" data-dx>Cancel</button><span style="flex:1"></span><button class="btn primary" data-ok>${esc(okLabel)}</button></div>`);
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
  return `<div class="nin"><label for="n_${KEYS[i]}">${esc(labelOf(i))}</label><input type="text" inputmode="decimal" id="n_${KEYS[i]}" data-k="${KEYS[i]}" value="${esc(shown)}" placeholder="–"><span class="u">${esc(UNITS[i])}</span></div>`;
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
function fieldError(input, msg) {
  const host = input.closest('.nin, label.f') || input;
  $$('.field-err', host.parentNode).forEach((x) => x.remove());
  host.insertAdjacentHTML('afterend', `<p class="note field-err" role="alert">${esc(msg)}</p>`);
  input.setAttribute('aria-invalid', 'true');
  for (let d = input.closest('details'); d; d = d.parentElement && d.parentElement.closest('details')) d.open = true;
  input.focus();
  input.scrollIntoView({ block: 'center' });
}
function portionRows(list) {
  return list.map((p) => `<div class="ing"><input type="text" class="pl" value="${esc(p.label)}" aria-label="Portion name" placeholder="e.g. 1 piece"><input type="text" inputmode="decimal" class="pg" value="${esc(String(p.grams))}" aria-label="Portion in grams" placeholder="g"><button class="icon-btn sm" data-rm aria-label="Remove">${IC.close}</button></div>`).join('');
}
function collectPortions(root) {
  return $$('#ports .ing', root).map((r) => ({ label: $('.pl', r).value.trim(), grams: num($('.pg', r).value) })).filter((p) => p.label && p.grams > 0);
}

function openFoodEditor(food, opts = {}) {
  const isNew = !food;
  const f0 = food || { name: opts.name || '', brand: '', barcode: opts.barcode || '', basis: { qty: 100, unit: 'g' }, n: {}, nova: null, portions: [], note: '' };
  const perUnit = !isG(f0);
  const sh = openSheet(isNew ? 'Create food from label' : 'Edit food', `
    <label class="f">Name<input type="text" id="fname" value="${esc(f0.name)}" maxlength="120" placeholder="e.g. Almond barista drink"></label>
    <div class="grid2"><label class="f">Brand<input type="text" id="fbrand" value="${esc(f0.brand || '')}" maxlength="80"></label>
      <label class="f">Barcode<input type="text" inputmode="numeric" id="fcode" value="${esc(f0.barcode || '')}" maxlength="14"></label></div>
    <fieldset><legend class="muted small" style="margin-bottom:8px;font-weight:600">The values below are per</legend>
      <div class="row gap"><label class="chk"><input type="radio" name="basis" value="g" ${perUnit ? '' : 'checked'}> 100 g</label>
      <label class="chk"><input type="radio" name="basis" value="u" ${perUnit ? 'checked' : ''}> 1 unit (capsule, tablet, piece)</label>
      <input type="text" id="funit" value="${esc(perUnit ? f0.basis.unit : 'capsule')}" style="width:140px" aria-label="Unit name" ${perUnit ? '' : 'hidden'}></div></fieldset>
    <p class="muted small">Fill in what the label shows. An empty field means “no data”, a 0 is a real zero. Write &lt;0.3 for a value below a detection limit.</p>
    <div id="nuts">${nutInputs(f0)}</div>
    <details class="fold" ${f0.nova ? 'open' : ''}><summary>Food-processing group (NOVA, optional)</summary>
      <p class="hint" style="margin:0 0 10px">1 = unprocessed or minimally processed, 2 = culinary ingredient (oil, butter, sugar, salt), 3 = processed food (bread, canned vegetables), 4 = ultra-processed (soft drinks, packaged snacks). Leave it unset if you are not sure.</p>
      <label class="f">NOVA group<select id="fnova"><option value="">Not set</option>${[1, 2, 3, 4].map((n) => `<option value="${n}" ${f0.nova === n ? 'selected' : ''}>${n}${n === 4 ? ' (ultra-processed)' : ''}</option>`).join('')}</select></label></details>
    <div id="portwrap"><h4>Portions (in grams)</h4><div id="ports">${portionRows(f0.portions || [])}</div><button class="chip-btn" id="addport" style="margin-top:8px">+ Portion</button></div>
    <label class="f">Notes (source, confidence)<textarea id="fnote" maxlength="400">${esc(f0.note || '')}</textarea></label>
    <div class="row gap">${isNew ? '' : '<button class="btn danger" id="fdel">Delete</button>'}<span style="flex:1"></span><button class="btn primary" id="fok">Save</button></div>`);
  const radios = $$('input[name=basis]', sh.el), unit = $('#funit', sh.el);
  const syncBasis = () => { const u = radios.find((r) => r.checked).value === 'u'; unit.hidden = !u; unit.disabled = !u; $('#portwrap', sh.el).hidden = u; };
  radios.forEach((r) => r.addEventListener('change', syncBasis)); syncBasis();
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
    const out = food || { id: 'u:' + uid(), src: 'user', created: Date.now() };
    Object.assign(out, {
      name, brand: $('#fbrand', sh.el).value.trim(), barcode: $('#fcode', sh.el).value.trim(),
      basis: u ? { qty: 1, unit: unitName } : { qty: 100, unit: 'g' }, n,
      nova: Number($('#fnova', sh.el).value) || null, portions: u ? [] : collectPortions(sh.el),
      note: $('#fnote', sh.el).value.trim(), updated: Date.now(),
    });
    if (food && food.src === 'off') out.edited = true;
    S.foods[out.id] = out;
    invalidate(); save(); sh.close();
    if (S.tab === 'foods') render();
    toast('Food saved');
    if (opts.after) opts.after(out);
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
  const head = ['date', 'time', 'meal', 'food_id', 'food', 'brand', 'source', 'amount', 'unit', 'nova', 'energy_estimated', 'estimate_confidence', ...KEYS.map((_, i) => ucol(i)), ...mi.map((i) => ucol(i) + '__max'), ...ei.map((i) => ucol(i) + '__est')];
  const lines = [csvLine(head)];
  for (const { e, f, lo, hi, est } of data) {
    lines.push(csvLine([e.d, timeOf(e), (MEALS.find((m) => m.id === e.m) || {}).name, f.id, f.name, f.brand || (f.src === 'dmbio' ? 'dmBio' : ''), f.src, e.a, f.basis.unit, novaOf(f) || '', energyEstimated(f) ? 1 : 0, f.src === 'dmbio' ? CONF[f.q] : '', ...lo, ...mi.map((i) => hi[i]), ...ei.map((i) => est[i])]));
  }
  download(`nutrilog-entries-${ymd(new Date())}.csv`, BOM + lines.join('\n'), 'text/csv;charset=utf-8');
}
function exportDays() {
  const days = [...new Set(S.log.filter((e) => getFood(e.f)).map((e) => e.d))].sort();
  const per = days.map((d) => ({ d, T: totalsFor(entriesOf(d)) }));
  const withMax = new Set();
  per.forEach(({ T }) => { for (let i = 0; i < NUT_N; i++) if (T.cnt[i] && T.hi[i] - T.lo[i] > 1e-9) withMax.add(i); });
  const mi = [...withMax].sort((a, b) => a - b);
  const ei = KEYS.map((_, i) => i).filter((i) => per.some(({ T }) => T.est[i] > 0));
  const head = ['date', 'entries', ...KEYS.map((_, i) => ucol(i)), ...mi.map((i) => ucol(i) + '__max'), ...ei.map((i) => ucol(i) + '__est'), ...KEYS.map((_, i) => KEYS[i] + '__n')];
  const lines = [csvLine(head)];
  for (const { d, T } of per) {
    lines.push(csvLine([d, T.n, ...KEYS.map((_, i) => (T.cnt[i] ? num6(T.lo[i]) : '')), ...mi.map((i) => (T.cnt[i] ? num6(T.hi[i]) : '')), ...ei.map((i) => T.est[i]), ...KEYS.map((_, i) => T.cnt[i])]));
  }
  download(`nutrilog-daily-totals-${ymd(new Date())}.csv`, BOM + lines.join('\n'), 'text/csv;charset=utf-8');
}
function importJson(file) {
  const rd = new FileReader();
  rd.onload = () => {
    try {
      const j = JSON.parse(rd.result);
      if (j.app !== 'tapnaplo' || !Array.isArray(j.log) || typeof j.foods !== 'object') throw new Error('this is not a Nutrilog backup file.');
      const nE = j.log.length, nF = Object.keys(j.foods).length;
      askConfirm({
        title: 'Replace your data?', danger: true, okLabel: 'Replace',
        text: `This replaces everything in the app with the backup: ${nE === 1 ? '1 entry' : nE + ' entries'} and ${nF === 1 ? '1 food' : nF + ' foods'}. Save a backup of the current data first if you are not sure.`,
        onOk: () => {
          S.log = j.log; S.foods = j.foods; S.meta = Object.assign(metaDefaults(), j.meta || {});
          invalidate(); save(); render(); toast('Restored');
        },
      });
    } catch (err) { toast('Could not restore: ' + err.message); }
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
  else if (a === 'edit-food') { const f = S.foods[t.dataset.id]; if (f) openFoodEditor(f); }
  else if (a === 'export-json') exportJson();
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
    const [log, foods, meta] = await Promise.all([Store.get('log'), Store.get('foods'), Store.get('meta')]);
    if (Array.isArray(log)) S.log = log;
    if (foods && typeof foods === 'object') S.foods = foods;
    if (meta && typeof meta === 'object') S.meta = Object.assign(metaDefaults(), meta);
    try { const tab = localStorage.getItem('nutrilog.tab'); if (TABS.some((x) => x[0] === tab)) S.tab = tab; } catch { /* private mode */ }
    render();
    if ('serviceWorker' in navigator && /^https?:$/.test(location.protocol)) navigator.serviceWorker.register('sw.js').catch(() => {});
  } catch (err) {
    $('#view').innerHTML = `<div class="card" style="margin-top:16px"><div class="card-t">The app could not start.</div><p class="muted small" style="margin-top:6px">${esc(err.message)}</p><p class="muted small" style="margin-top:6px">If you opened the file straight from your computer, upload the files to a host (for example GitHub Pages) or start a local web server.</p></div>`;
  }
}
window.__tapnaplo = { S, HU: DICT, vecOf, totalsFor, searchCiqual, searchUsda, getFood, offToFood, fmt, novaOf, setNova, novaStats, sharePct, get KEYS() { return KEYS; }, get IDX() { return IDX; }, get USDA() { return USDA; }, get DMBIO() { return DMBIO; }, searchDm, isEst, CONF, trackedEst, render, save };
init();

})();
