/* Nutrilog: calorie, macro and micronutrient diary. No build step, one script.
   Data: CIQUAL 2020 (Anses, CC BY 4.0) in ciqual.json; Open Food Facts (ODbL) looked up live.
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
const prec = (v) => Number(Number(v).toPrecision(6));
const num = (s) => parseFloat(String(s).replace(',', '.'));        // accepts 1.5 and 1,5
const plural = (n, w) => `${n} ${w}${n === 1 ? '' : 's'}`;

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
const S = {
  log: [],                      // {id, d, m, f, a, t}
  foods: {},                    // custom and Open Food Facts foods
  meta: { last: {}, portions: {}, backup: null },
  day: ymd(new Date()),
  tab: 'log',
  filter: '',
};
let CAT = null, CIQ = [], CIQ_BY_ID = new Map();
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
  water: ['Water', 'oth'], protein_crude_n_x_6_25: ['Crude protein (N × 6.25)', 'oth'], starch: ['Starch', 'oth'],
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
  tojas: ['egg'], tej: ['milk'], tejfol: ['cream, 15-20% fat', 'cream, fat content unknown', 'cream'], tejszin: ['cream, fat content unknown', 'cream'], sajt: ['cheese'],
  turo: ['quark', 'fresh cheese', 'uncured soft cheese', 'fromage blanc'],
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
  olaj: ['oil'], olivaolaj: ['olive oil'], kokuszolaj: ['coconut'], cukor: ['sugar'], mez: ['honey'],
  csokolade: ['chocolate'], kave: ['coffee'], tea: ['tea'], viz: ['water'], bor: ['wine'], sor: ['beer'],
  csirke: ['chicken'], pulyka: ['turkey'], marha: ['beef'], sertes: ['pork'], borju: ['veal'], barany: ['lamb'], kacsa: ['duck'],
  sonka: ['ham'], szalami: ['salami'], kolbasz: ['sausage'], szalonna: ['bacon', 'lard'],
  hal: ['fish'], lazac: ['salmon'], tonhal: ['tuna'], szardinia: ['sardine'], makrela: ['mackerel'], pisztrang: ['trout'],
  ponty: ['carp'], garnela: ['shrimp', 'prawn'], tofu: ['tofu'], lencse: ['lentil'], bab: ['bean'], csicseriborso: ['hummus', 'legume'],
  borso: ['pea'], kukorica: ['corn', 'maize'], szoja: ['soy'], mandulaital: ['almond drink', 'almond-based drink'], mandulatej: ['almond drink', 'almond-based drink'],
  zabital: ['oat-based drink'], zabtej: ['oat-based drink'], rizsital: ['rice-based drink'], szojaital: ['soy drink'], szojatej: ['soy drink'], kokusztej: ['coconut milk'], kokusz: ['coconut'],
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
  cookie: ['biscuit', 'cookie'], biscuit: ['biscuit', 'cookie'], chickpea: ['hummus', 'legume'], garbanzo: ['hummus', 'legume'],
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
function scoreName(nn, groups) {
  let score = 0;
  for (const alts of groups) {
    let best = 0;
    for (const a of alts) {
      const i = nn.indexOf(a);
      if (i < 0) continue;
      const before = i === 0 || /[^a-z0-9]/.test(nn[i - 1]);
      const after = nn[i + a.length];
      const whole = after === undefined || /[^a-z0-9]/.test(after);
      let sc = 1;
      if (before) sc = whole ? 6 : 4;
      if (i === 0 && whole && (after === undefined || after === ',' || (after === ' ' && nn[i + a.length + 1] === '('))) sc += 3;
      sc += Math.min(a.length, 24) / 10;   // longer, more specific matches rank first
      best = Math.max(best, sc);
    }
    if (!best) return 0;
    score += best;
  }
  return score;
}
function rankFoods(groups, limit) {
  const out = [];
  for (const f of CIQ) {
    const s = scoreName(f._nn, groups);
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
function searchCiqual(q, limit = 40) {
  let qq = norm(q);
  for (const [re, to] of PHRASES) qq = qq.replace(re, to);
  const groups = tokensOf(qq).flatMap(altsFor);
  if (!groups.length) return [];
  let res = rankFoods(groups, limit);
  if (!res.length && groups.length > 1) {
    // drop words that match nothing and search with the rest
    const useful = groups.filter((g) => CIQ.some((f) => scoreName(f._nn, [g])));
    if (useful.length && useful.length < groups.length) res = rankFoods(useful, limit);
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
const getFood = (id) => (id.startsWith('c:') ? CIQ_BY_ID.get(id) : S.foods[id]);
const isG = (f) => f.basis.unit === 'g';

function cellOf(food, i) {
  if (food.src === 'ciqual') return food._cells[i];
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
const energyEstimated = (f) => f.src === 'ciqual' && !!f.estE;
function invalidate() { for (const f of Object.values(S.foods)) delete f._vec; }

function totalsFor(entries) {
  const lo = new Float64Array(NUT_N), hi = new Float64Array(NUT_N), cnt = new Uint16Array(NUT_N);
  const missing = Array.from({ length: NUT_N }, () => []);
  let n = 0;
  for (const e of entries) {
    const f = getFood(e.f);
    if (!f) continue;
    n++;
    const v = vecOf(f), k = e.a / f.basis.qty;
    for (let i = 0; i < NUT_N; i++) {
      if (Number.isNaN(v.lo[i])) missing[i].push(f.name);
      else { lo[i] += v.lo[i] * k; hi[i] += v.hi[i] * k; cnt[i]++; }
    }
  }
  return { lo, hi, cnt, n, missing };
}
const entriesOf = (day) => S.log.filter((e) => e.d === day && getFood(e.f));
const amountText = (e, f) => `${fmt(e.a)} ${f.basis.unit}`;
const trackedKnown = (f) => { const v = vecOf(f); return TRACKED.reduce((c, i) => c + (Number.isNaN(v.lo[i]) ? 0 : 1), 0); };
const srcTag = (f) => (f.src === 'ciqual' ? 'CIQUAL' : f.src === 'off' ? 'OFF' : 'custom');
const kcalPer = (f) => vecOf(f).lo[0];

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
async function offFetch(url) {
  const r = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!r.ok) throw new Error('Open Food Facts did not respond (HTTP ' + r.status + ').');
  return r.json();
}
async function offProduct(code) {
  const j = await offFetch(`https://world.openfoodfacts.org/api/v2/product/${encodeURIComponent(code)}.json?fields=${OFF_FIELDS}`);
  if (j.status !== 1 || !j.product) return null;
  j.product.code = j.product.code || code;
  return offToFood(j.product);
}
async function offSearch(q, huOnly) {
  const p = new URLSearchParams({ search_terms: q, search_simple: '1', action: 'process', json: '1', page_size: '15', fields: OFF_FIELDS });
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
const TABS = [['log', 'Diary', IC.diary], ['nutr', 'Nutrients', IC.nutr], ['foods', 'Foods', IC.foods], ['data', 'Data', IC.data]];

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
    const by = { 1: 0, 2: 0, 3: 0, 4: 0, u: 0 };
    for (const e of es) {
      const food = getFood(e.f), kv = vecOf(food).lo[0];
      if (Number.isNaN(kv)) continue;
      by[food.nova || 'u'] += kv * e.a / food.basis.qty;
    }
    const sum = by[1] + by[2] + by[3] + by[4] + by.u;
    if (sum > 0 && by[1] + by[2] + by[3] + by[4] > 0) {
      nova = `<div class="banner">Ultra-processed (NOVA 4): <b>${fmt(by[4] / sum * 100)}%</b> of energy · NOVA 1–3: ${fmt((by[1] + by[2] + by[3]) / sum * 100)}% · unclassified: ${fmt(by.u / sum * 100)}%</div>`;
    }
  }

  const meals = MEALS.map((m) => {
    const list = es.filter((e) => e.m === m.id);
    let mk = 0, mkn = 0;
    for (const e of list) { const fd = getFood(e.f), v = vecOf(fd).lo[0]; if (!Number.isNaN(v)) { mk += v * e.a / fd.basis.qty; mkn++; } }
    const rows = list.map((e) => {
      const food = getFood(e.f), v = vecOf(food).lo[0], k = e.a / food.basis.qty;
      const kt = Number.isNaN(v) ? '–' : (energyEstimated(food) ? '~' : '') + fmt(v * k);
      return `<button class="entry" data-act="edit-entry" data-id="${e.id}">${avatar(food.name)}
        <span class="entry-main"><span class="entry-name">${esc(cap(food.name))}</span><span class="entry-sub">${esc(amountText(e, food))} · ${esc(food.brand ? food.brand + ' · ' : '')}${srcTag(food)}</span></span>
        <span class="entry-kcal">${kt}<small>kcal</small></span></button>`;
    }).join('');
    return `<section class="meal"><div class="meal-h"><h3>${m.name}</h3>${mkn ? `<span class="mk">${fmt(mk)} kcal</span>` : ''}
      <button class="icon-btn sm" data-act="add" data-meal="${m.id}" aria-label="Add food to ${m.name}">${IC.plus}</button></div>
      <div class="rows">${rows}</div></section>`;
  }).join('');

  const empty = !S.log.length ? `<div class="card" style="margin-top:16px"><div class="card-t">Log your first food</div>
    <p class="muted small" style="margin-top:6px">Tap <b>Add food</b>. Search in English or Hungarian (egg, tojás, bread, kenyér, avocado), scan a barcode, or look a product up in Open Food Facts. Use <b>New food</b> to enter your own from a label.</p></div>` : '';

  return `<section class="hero">
      <div class="hero-label">Energy</div>
      <div class="hero-num">${es.length ? (estE ? '~' : '') + fmt(T.lo[0]) : '0'}<small>kcal</small></div>
      ${noE > 0 ? `<span class="chip warn">Lower estimate · ${noE} without energy data</span>` : `<span class="chip">${es.length ? plural(es.length, 'item') + ' logged' : 'Nothing logged yet'}</span>`}
    </section>
    <div class="actions">
      <button class="act primary" data-act="add"><span class="act-c">${IC.plus}</span>Add food</button>
      <button class="act" data-act="scan"><span class="act-c">${IC.scan}</span>Scan</button>
      <button class="act" data-act="new-food"><span class="act-c">${IC.tag}</span>New food</button>
    </div>
    <div class="card">
      <div class="bar" role="img" aria-label="Energy split between protein, carbohydrate and fat">${tot > 0
    ? `<i style="width:${p / tot * 100}%;background:var(--c-p)"></i><i style="width:${c / tot * 100}%;background:var(--c-c)"></i><i style="width:${f / tot * 100}%;background:var(--c-f)"></i>` : ''}</div>
      <div class="mtiles">
        <div><div class="mt-name"><span class="dot" style="background:var(--c-p)"></span>Protein</div><div class="mt-val">${fmt(g('protein'))}<small>g</small></div><div class="mt-pct">${pct(p)}</div></div>
        <div><div class="mt-name"><span class="dot" style="background:var(--c-c)"></span>Carbs</div><div class="mt-val">${fmt(g('carbohydrate'))}<small>g</small></div><div class="mt-pct">${pct(c)}</div></div>
        <div><div class="mt-name"><span class="dot" style="background:var(--c-f)"></span>Fat</div><div class="mt-val">${fmt(g('fat'))}<small>g</small></div><div class="mt-pct">${pct(f)}</div></div>
      </div>
      <div class="mini"><span>Fibre <b>${fmt(g('fibres'))} g</b></span><span>Sugars <b>${fmt(g('sugars'))} g</b></span><span>Salt <b>${fmt(g('salt'))} g</b></span></div>
    </div>
    ${estE ? '<div class="banner">~ means the energy was calculated from protein, carbohydrate and fat (CIQUAL, Atwater factors).</div>' : ''}
    ${nova}${empty}${meals}`;
}

/* ---- Nutrients ---- */
function viewNutr() {
  const es = entriesOf(S.day);
  if (!es.length) return '<div class="card" style="margin-top:16px"><div class="card-t">Nothing logged for this day</div><p class="muted small" style="margin-top:6px">The daily nutrient summary is built from the foods you log in the Diary tab.</p></div>';
  const T = totalsFor(es);
  const note = '<div class="banner">Missing data is not zero. Totals only include items that have data (the badge on the right shows how many items out of all), so they are lower estimates. Ranges come from values reported as “&lt; x” (below the detection limit).</div>';
  const out = GROUPS.map(([gid, gname, open]) => {
    const idxs = KEYS.map((_, i) => i).filter((i) => groupOf(i) === gid);
    if (!idxs.length) return '';
    const rows = idxs.map((i) => {
      const cnt = T.cnt[i], n = T.n, lo = T.lo[i], hi = T.hi[i], unit = UNITS[i];
      const range = hi - lo > Math.max(lo * 0.1, 1e-9);
      const val = cnt === 0 ? '<span class="nval none">no data</span>'
        : `<span class="nval">${cnt < n ? '≥ ' : ''}${range ? fmt(lo) + '–' + fmt(hi) : fmt(lo)}<em>${esc(unit)}</em></span>`;
      const cls = cnt === n ? 'full' : cnt === 0 ? 'none' : 'part';
      const miss = T.missing[i];
      const detail = miss.length ? `<div class="ndetail">No data for: ${esc([...new Set(miss)].map(cap).join('; '))}</div>` : '';
      return `<details class="nrow"><summary><span>${esc(labelOf(i))}</span>${val}<span class="pill ${cls}">${cnt}/${n}</span></summary>${detail || '<div class="ndetail">Every item has data.</div>'}</details>`;
    }).join('');
    const list = `<div class="nlist">${rows}</div>`;
    return open ? `<section class="group"><h3>${gname}</h3>${list}</section>`
      : `<details class="group"><summary>${gname}</summary>${list}</details>`;
  }).join('');
  return note + out;
}

/* ---- My foods ---- */
function viewFoods() {
  return `<div class="row gap" style="margin:8px 0 14px"><button class="btn primary" data-act="new-food">${IC.plus.replace('<svg', '<svg width="18" height="18"')} New food</button></div>
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
  return `<div class="stack" style="margin-top:8px">
    <div class="card"><div class="card-t">Backup</div>
      <p class="muted small" style="margin:6px 0 14px">Your data lives only on this device, in this browser. Back up regularly and before switching devices. Last backup: ${esc(b)}.</p>
      <div class="row gap"><button class="btn primary" data-act="export-json">Save backup (JSON)</button><label class="btn" style="cursor:pointer">Restore from file<input type="file" id="importfile" accept="application/json,.json" hidden></label></div></div>
    <div class="card"><div class="card-t">For analysis</div>
      <p class="muted small" style="margin:6px 0 14px">UTF-8 CSV with decimal points. An empty cell means no data. Columns ending in __max hold the upper bound for values reported as “&lt; x”.</p>
      <div class="row gap"><button class="btn" data-act="export-entries">Entries (CSV)</button><button class="btn" data-act="export-days">Daily totals (CSV)</button></div></div>
    <div class="card"><div class="card-t">Storage</div>
      <p class="muted small" style="margin:6px 0 14px">Mode: ${Store.mode === 'idb' ? 'IndexedDB' : 'localStorage (fallback)'} · <span id="persist-state">persistent storage: checking…</span></p>
      <button class="btn" data-act="persist">Request persistent storage</button></div>
    <div class="card"><div class="card-t">Sources &amp; licences</div>
      <p class="small" style="margin:8px 0">Generic foods: Anses. 2020. Ciqual French food composition table. <a href="https://doi.org/10.5281/zenodo.4770202" target="_blank" rel="noopener">doi.org/10.5281/zenodo.4770202</a> (CC BY 4.0).</p>
      <p class="small" style="margin:8px 0">Packaged products: <a href="https://world.openfoodfacts.org" target="_blank" rel="noopener">Open Food Facts</a>, a community database, ODbL licence. Label data can be incomplete.</p>
      <p class="small muted" style="margin:8px 0">Barcode reader for browsers without a built-in one: ZXing-js, Apache 2.0 licence (ZXING-LICENSE.txt).</p>
      <p class="small muted" style="margin:8px 0">CIQUAL lists French market averages. This app is an information tool, not medical advice. Database: ${CAT ? CAT.foods.length : 0} CIQUAL foods, ${CAT ? CAT.nutrients.length : 0} nutrients.</p></div>
  </div>`;
}

/* ================= food picker ================= */
function openPicker({ title = 'Add food', onlyGrams = false, onPick }) {
  const sh = openSheet(title, `
    <input id="q" type="search" class="search" inputmode="search" autocomplete="off" placeholder="Search: egg, tojás, bread, kenyér…" aria-label="Search foods">
    <div class="row gap"><button class="btn" data-a="scan">${IC.scan.replace('<svg', '<svg width="20" height="20"')} Scan barcode</button><button class="btn" data-a="off">Search Open Food Facts</button></div>
    <label class="chk"><input type="checkbox" id="huonly" checked> Open Food Facts: Hungarian market only</label>
    <div id="res" aria-live="polite"></div>`);
  const q = $('#q', sh.el), res = $('#res', sh.el);
  let off = null, offMsg = '';
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
      if (loc.length) html += `<h4>My foods &amp; saved products</h4>${list(loc, 'x')}`;
      if (ciq.length) html += `<h4>CIQUAL (generic foods)</h4>${list(ciq, 'x')}`;
      if (!loc.length && !ciq.length) html += '<p class="muted">No local match. Try another word, or search Open Food Facts.</p>';
      if (/^\d{8,14}$/.test(text.replace(/\s/g, ''))) html += `<button class="btn block primary" data-a="code" style="margin-top:12px">Look up barcode: ${esc(text.replace(/\s/g, ''))}</button>`;
    }
    if (off) html += `<h4>Open Food Facts</h4>${off.length ? list(off, 'off') : '<p class="muted">No results.</p>'}`;
    if (offMsg) html += `<p class="note">${esc(offMsg)}</p>`;
    html += '<div class="row gap" style="margin-top:16px"><button class="btn" data-a="new">+ New food from label</button></div>';
    res.innerHTML = html;
  }
  async function runOff(code) {
    offMsg = '';
    const text = q.value.trim();
    if (!text) { offMsg = 'Type a name or a barcode first.'; paint(); return; }
    res.insertAdjacentHTML('afterbegin', '<p class="muted">Searching Open Food Facts…</p>');
    try {
      if (code) {
        const food = await offProduct(code);
        if (!food) { off = []; offMsg = 'This barcode is not in Open Food Facts. Add it yourself with “New food from label”.'; paint(); return; }
        off = [food]; paint();
        const kept = keepOff(food);
        if (!Object.keys(kept.n).length) offMsg = 'Open Food Facts has no nutrition values for this product. Fill them in from the label under My foods.';
        pick(kept);
      } else {
        off = await offSearch(text, $('#huonly', sh.el).checked);
        if (!off.length && $('#huonly', sh.el).checked) offMsg = 'No Hungarian results. Untick “Hungarian market only” to search everywhere.';
        paint();
      }
    } catch (err) {
      offMsg = err instanceof TypeError || !err || !err.message ? 'Could not reach Open Food Facts. Check your internet connection.' : err.message;
      paint();
    }
  }
  function pick(food) { onPick(food); }
  q.addEventListener('input', () => { paint(); });
  sh.el.addEventListener('click', (ev) => {
    const b = ev.target.closest('button');
    if (!b) return;
    if (b.dataset.pick) {
      let food = b.dataset.kind === 'off' ? (off || []).find((f) => f.id === b.dataset.pick) : getFood(b.dataset.pick);
      if (b.dataset.kind === 'off' && food) food = keepOff(food);
      if (food) pick(food);
    } else if (b.dataset.a === 'off') runOff(null);
    else if (b.dataset.a === 'code') runOff(q.value.replace(/\s/g, ''));
    else if (b.dataset.a === 'scan') scanBarcode((code) => { q.value = code; paint(); runOff(code); });
    else if (b.dataset.a === 'new') openFoodEditor(null, { name: /\D/.test(q.value) ? q.value.trim() : '', barcode: /^\d{8,14}$/.test(q.value.trim()) ? q.value.trim() : '', after: (f) => pick(f) });
  });
  q.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); const t = q.value.replace(/\s/g, ''); if (/^\d{8,14}$/.test(t)) runOff(t); } });
  paint();
  setTimeout(() => q.focus(), 60);
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
function openAmount({ food, entry, meal, afterAdd }) {
  const unitG = isG(food);
  const start = entry ? entry.a : (S.meta.last[food.id] ?? (portionsOf(food)[0] ? portionsOf(food)[0].grams : unitG ? 100 : 1));
  const chips = (unitG ? [...portionsOf(food).map((p) => [p.label, p.grams]), ...[10, 30, 50, 100, 200].map((g) => [g + ' g', g])] : [0.5, 1, 2, 3].map((x) => [x + ' ' + food.basis.unit, x]));
  const sh = openSheet(entry ? 'Edit entry' : 'Amount', `
    <div class="row gap" style="flex-wrap:nowrap">${avatar(food.name)}<div style="min-width:0"><b>${esc(cap(food.name))}</b><br><span class="muted small">${esc(food.brand || '')} ${esc(srcTag(food))}${unitG ? '' : ' · unit: ' + esc(food.basis.unit)}</span></div></div>
    <label class="f">Amount (${esc(food.basis.unit)})<input type="text" inputmode="decimal" id="amt" value="${esc(String(start))}"></label>
    <div class="chips" id="chips">${chips.map(([l, v]) => `<button class="chip-btn" data-v="${v}">${esc(l)}</button>`).join('')}</div>
    ${unitG ? '<button class="chip-btn accent" id="saveportion" style="justify-self:start">+ Save as portion</button>' : ''}
    <label class="f">Meal<select id="meal">${MEALS.map((m) => `<option value="${m.id}" ${m.id === (entry ? entry.m : meal) ? 'selected' : ''}>${m.name}</option>`).join('')}</select></label>
    <div class="card" id="prev"></div>
    <div class="row gap">${entry ? '<button class="btn danger" id="del">Delete</button>' : ''}${food.src !== 'ciqual' ? '<button class="btn" id="editfood">Edit food</button>' : ''}<span style="flex:1"></span><button class="btn primary" id="ok">${entry ? 'Save' : 'Add'}</button></div>`);
  const amt = $('#amt', sh.el);
  const val = () => { const v = num(amt.value); return Number.isFinite(v) && v > 0 ? v : NaN; };
  function prev() {
    const a = val(), v = vecOf(food);
    if (Number.isNaN(a)) { $('#prev', sh.el).innerHTML = '<span class="muted">Enter a positive number.</span>'; return; }
    const k = a / food.basis.qty, g = (key) => v.lo[IDX[key]] * k;
    const known = trackedKnown(food);
    $('#prev', sh.el).innerHTML = `<div class="card-t">${Number.isNaN(v.lo[0]) ? 'no energy data' : (energyEstimated(food) ? '~' : '') + fmt(v.lo[0] * k) + ' kcal'}</div>
      <div class="muted small" style="margin-top:4px">protein ${fmt(g('protein'))} g · carbs ${fmt(g('carbohydrate'))} g · fat ${fmt(g('fat'))} g · fibre ${fmt(g('fibres'))} g</div>
      <div class="small" style="margin-top:8px">Data for <b>${known}</b> of the ${TRACKED.length} tracked nutrients${known < TRACKED.length * 0.6 ? ' <span style="color:var(--warn)">(few — micronutrient totals will be incomplete)</span>' : ''}</div>`;
  }
  amt.addEventListener('input', prev);
  $('#chips', sh.el).addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) { amt.value = String(b.dataset.v); prev(); } });
  const sp = $('#saveportion', sh.el);
  if (sp) sp.onclick = () => {
    const a = val();
    if (Number.isNaN(a)) return;
    const label = window.prompt('Portion name (e.g. 1 piece, 1 tbsp):', '1 piece');
    if (!label) return;
    (S.meta.portions[food.id] = S.meta.portions[food.id] || []).push({ label: label.trim().slice(0, 40), grams: a });
    save(); toast('Portion saved: ' + label.trim()); sh.close(); openAmount({ food, entry, meal, afterAdd });
  };
  $('#ok', sh.el).onclick = () => {
    const a = val();
    if (Number.isNaN(a)) { amt.focus(); return; }
    const m = $('#meal', sh.el).value;
    if (entry) { entry.a = a; entry.m = m; } else S.log.push({ id: uid(), d: S.day, m, f: food.id, a, t: Date.now() });
    S.meta.last[food.id] = a;
    save(); sh.close(); render();
    toast(entry ? 'Updated' : 'Added: ' + cap(food.name));
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
  setTimeout(() => { amt.focus(); amt.select(); }, 60);
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
function nutInputs(food) {
  return GROUPS.map(([gid, gname]) => {
    const idxs = KEYS.map((_, i) => i).filter((i) => groupOf(i) === gid && !(gid === 'oth' && UNITS[i] === 'kcal'));
    const fields = idxs.map((i) => {
      const cur = food && food.n ? food.n[KEYS[i]] : undefined;
      const shown = cur === undefined || cur === null ? '' : String(cur);
      return `<div class="nin"><label for="n_${KEYS[i]}">${esc(labelOf(i))}</label><input type="text" inputmode="decimal" id="n_${KEYS[i]}" data-k="${KEYS[i]}" value="${esc(shown)}" placeholder="–"><span class="u">${esc(UNITS[i])}</span></div>`;
    }).join('');
    return `<details class="fold" ${['mac', 'min', 'vit'].includes(gid) || idxs.some((i) => food && food.n && food.n[KEYS[i]] != null) ? 'open' : ''}><summary>${gname}</summary>${fields}</details>`;
  }).join('');
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
  const sh = openSheet(isNew ? 'New food (from label)' : 'Edit food', `
    <label class="f">Name<input type="text" id="fname" value="${esc(f0.name)}" maxlength="120" placeholder="e.g. Almond barista drink"></label>
    <div class="grid2"><label class="f">Brand<input type="text" id="fbrand" value="${esc(f0.brand || '')}" maxlength="80"></label>
      <label class="f">Barcode<input type="text" inputmode="numeric" id="fcode" value="${esc(f0.barcode || '')}" maxlength="14"></label></div>
    <fieldset><legend class="muted small" style="margin-bottom:8px;font-weight:600">The values below are per</legend>
      <div class="row gap"><label class="chk"><input type="radio" name="basis" value="g" ${perUnit ? '' : 'checked'}> 100 g</label>
      <label class="chk"><input type="radio" name="basis" value="u" ${perUnit ? 'checked' : ''}> 1 unit (capsule, tablet, piece)</label>
      <input type="text" id="funit" value="${esc(perUnit ? f0.basis.unit : 'capsule')}" style="width:140px" aria-label="Unit name" ${perUnit ? '' : 'disabled'}></div></fieldset>
    <label class="f">NOVA group (degree of processing)<select id="fnova"><option value="">unknown</option>${[1, 2, 3, 4].map((n) => `<option value="${n}" ${f0.nova === n ? 'selected' : ''}>${n}${n === 4 ? ' (ultra-processed)' : ''}</option>`).join('')}</select></label>
    <p class="muted small">Fill in what the label shows. An empty field means “no data”, a 0 is a real zero. Write &lt;0.3 for a value below a detection limit.</p>
    <div id="nuts">${nutInputs(f0)}</div>
    <div id="portwrap"><h4>Portions (in grams)</h4><div id="ports">${portionRows(f0.portions || [])}</div><button class="chip-btn" id="addport" style="margin-top:8px">+ Portion</button></div>
    <label class="f">Notes (source, confidence)<textarea id="fnote" maxlength="400">${esc(f0.note || '')}</textarea></label>
    <p class="note" id="ferr" hidden></p>
    <div class="row gap">${isNew ? '' : '<button class="btn danger" id="fdel">Delete</button>'}<span style="flex:1"></span><button class="btn primary" id="fok">Save</button></div>`);
  const radios = $$('input[name=basis]', sh.el), unit = $('#funit', sh.el);
  const syncBasis = () => { const u = radios.find((r) => r.checked).value === 'u'; unit.disabled = !u; $('#portwrap', sh.el).hidden = u; };
  radios.forEach((r) => r.addEventListener('change', syncBasis)); syncBasis();
  $('#addport', sh.el).onclick = () => $('#ports', sh.el).insertAdjacentHTML('beforeend', portionRows([{ label: '', grams: '' }]));
  sh.el.addEventListener('click', (e) => { const b = e.target.closest('[data-rm]'); if (b) b.closest('.ing').remove(); });
  $('#fok', sh.el).onclick = () => {
    const err = $('#ferr', sh.el);
    const name = $('#fname', sh.el).value.trim();
    if (!name) { err.textContent = 'Give the food a name.'; err.hidden = false; return; }
    const n = {};
    for (const inp of $$('[data-k]', sh.el)) {
      const p = parseInput(inp.value);
      if (p.err) { err.textContent = 'Invalid number: ' + labelOf(IDX[inp.dataset.k]) + '. Use a positive number or <x.'; err.hidden = false; inp.focus(); return; }
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
  if (!window.confirm('Delete “' + food.name + '”?')) return;
  delete S.foods[food.id]; invalidate(); save(); done();
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
  const rows = [...S.log].filter((e) => getFood(e.f)).sort((a, b) => a.d.localeCompare(b.d) || a.t - b.t);
  const withMax = new Set();
  const data = rows.map((e) => {
    const f = getFood(e.f), v = vecOf(f), k = e.a / f.basis.qty;
    const lo = [], hi = [];
    for (let i = 0; i < NUT_N; i++) { lo.push(Number.isNaN(v.lo[i]) ? '' : num6(v.lo[i] * k)); hi.push(Number.isNaN(v.hi[i]) ? '' : num6(v.hi[i] * k)); if (!Number.isNaN(v.lo[i]) && v.hi[i] - v.lo[i] > 1e-12) withMax.add(i); }
    return { e, f, lo, hi };
  });
  const mi = [...withMax].sort((a, b) => a - b);
  const head = ['date', 'meal', 'food_id', 'food', 'brand', 'source', 'amount', 'unit', 'nova', 'energy_estimated', ...KEYS.map((_, i) => ucol(i)), ...mi.map((i) => ucol(i) + '__max')];
  const lines = [csvLine(head)];
  for (const { e, f, lo, hi } of data) {
    lines.push(csvLine([e.d, (MEALS.find((m) => m.id === e.m) || {}).name, f.id, f.name, f.brand || '', f.src, e.a, f.basis.unit, f.nova || '', energyEstimated(f) ? 1 : 0, ...lo, ...mi.map((i) => hi[i])]));
  }
  download(`nutrilog-entries-${ymd(new Date())}.csv`, BOM + lines.join('\n'), 'text/csv;charset=utf-8');
}
function exportDays() {
  const days = [...new Set(S.log.filter((e) => getFood(e.f)).map((e) => e.d))].sort();
  const per = days.map((d) => ({ d, T: totalsFor(entriesOf(d)) }));
  const withMax = new Set();
  per.forEach(({ T }) => { for (let i = 0; i < NUT_N; i++) if (T.cnt[i] && T.hi[i] - T.lo[i] > 1e-9) withMax.add(i); });
  const mi = [...withMax].sort((a, b) => a - b);
  const head = ['date', 'entries', ...KEYS.map((_, i) => ucol(i)), ...mi.map((i) => ucol(i) + '__max'), ...KEYS.map((_, i) => KEYS[i] + '__n')];
  const lines = [csvLine(head)];
  for (const { d, T } of per) {
    lines.push(csvLine([d, T.n, ...KEYS.map((_, i) => (T.cnt[i] ? num6(T.lo[i]) : '')), ...mi.map((i) => (T.cnt[i] ? num6(T.hi[i]) : '')), ...KEYS.map((_, i) => T.cnt[i])]));
  }
  download(`nutrilog-daily-totals-${ymd(new Date())}.csv`, BOM + lines.join('\n'), 'text/csv;charset=utf-8');
}
function importJson(file) {
  const rd = new FileReader();
  rd.onload = () => {
    try {
      const j = JSON.parse(rd.result);
      if (j.app !== 'tapnaplo' || !Array.isArray(j.log) || typeof j.foods !== 'object') throw new Error('this is not a Nutrilog backup file.');
      if (!window.confirm(`This replaces your current data with ${plural(j.log.length, 'entry').replace('entrys', 'entries')} and ${plural(Object.keys(j.foods).length, 'food')}. Continue?`)) return;
      S.log = j.log; S.foods = j.foods; S.meta = Object.assign({ last: {}, portions: {}, backup: null }, j.meta || {});
      invalidate(); save(); render(); toast('Restored');
    } catch (err) { toast('Could not restore: ' + err.message); }
  };
  rd.readAsText(file);
}

/* ================= events ================= */
document.addEventListener('click', (ev) => {
  const t = ev.target.closest('[data-act]');
  if (!t) return;
  const a = t.dataset.act;
  if (a === 'tab') { S.tab = t.dataset.tab; render(); window.scrollTo(0, 0); }
  else if (a === 'day') { S.day = addDays(S.day, +t.dataset.n); render(); }
  else if (a === 'today') { S.day = ymd(new Date()); render(); }
  else if (a === 'add') addFlow(t.dataset.meal || defaultMeal());
  else if (a === 'scan') { const pk = addFlow(defaultMeal()); const b = $('[data-a=scan]', pk.el); if (b) b.click(); }
  else if (a === 'edit-entry') { const e = S.log.find((x) => x.id === t.dataset.id); if (e) openAmount({ food: getFood(e.f), entry: e }); }
  else if (a === 'new-food') openFoodEditor(null);
  else if (a === 'edit-food') { const f = S.foods[t.dataset.id]; if (f) openFoodEditor(f); }
  else if (a === 'export-json') exportJson();
  else if (a === 'export-entries') exportEntries();
  else if (a === 'export-days') exportDays();
  else if (a === 'persist') {
    (navigator.storage && navigator.storage.persist ? navigator.storage.persist() : Promise.resolve(false)).then((ok) => { toast(ok ? 'Persistent storage enabled' : 'The browser declined. Install the app to your home screen and back up regularly.'); persistState(); });
  }
});
document.addEventListener('change', (ev) => {
  if (ev.target.id === 'datepick' && ev.target.value) { S.day = ev.target.value; render(); }
  if (ev.target.id === 'importfile' && ev.target.files[0]) { importJson(ev.target.files[0]); ev.target.value = ''; }
});
document.addEventListener('input', (ev) => {
  if (ev.target.id === 'ffilter') { S.filter = ev.target.value; $('#flist').innerHTML = foodListHtml(); }
});
function defaultMeal() {
  const h = new Date().getHours();
  return h < 10 ? 'm1' : h < 15 ? 'm2' : h < 21 ? 'm3' : 'm4';
}
function persistState() {
  const el = $('#persist-state');
  if (!el) return;
  if (!(navigator.storage && navigator.storage.persisted)) { el.textContent = 'persistent storage: not supported'; return; }
  navigator.storage.persisted().then((p) => { el.textContent = 'persistent storage: ' + (p ? 'on' : 'off'); });
}

/* ================= start ================= */
async function loadCatalog() {
  const r = await fetch('ciqual.json');
  if (!r.ok) throw new Error('ciqual.json could not be loaded (HTTP ' + r.status + ').');
  CAT = await r.json();
  KEYS = CAT.nutrients.map((n) => n.key);
  UNITS = CAT.nutrients.map((n) => n.unit);
  NUT_N = KEYS.length;
  KEYS.forEach((k, i) => { IDX[k] = i; });
  TRACKED = KEYS.map((_, i) => i).filter((i) => ['mac', 'fa', 'min', 'vit'].includes(groupOf(i)));
  CIQ = CAT.foods.map((f) => ({
    id: 'c:' + f.c, src: 'ciqual', name: f.n, group: [f.G, f.g].filter(Boolean).join(' › '),
    basis: { qty: 100, unit: 'g' }, portions: [], nova: null, estE: !!f.e, _cells: f.v, _nn: norm(f.n),
  }));
  CIQ_BY_ID = new Map(CIQ.map((f) => [f.id, f]));
}

async function init() {
  try {
    await Promise.all([Store.open(), loadCatalog()]);
    const [log, foods, meta] = await Promise.all([Store.get('log'), Store.get('foods'), Store.get('meta')]);
    if (Array.isArray(log)) S.log = log;
    if (foods && typeof foods === 'object') S.foods = foods;
    if (meta && typeof meta === 'object') S.meta = Object.assign({ last: {}, portions: {}, backup: null }, meta);
    render();
    persistState();
    if ('serviceWorker' in navigator && /^https?:$/.test(location.protocol)) navigator.serviceWorker.register('sw.js').catch(() => {});
  } catch (err) {
    $('#view').innerHTML = `<div class="card" style="margin-top:16px"><div class="card-t">The app could not start.</div><p class="muted small" style="margin-top:6px">${esc(err.message)}</p><p class="muted small" style="margin-top:6px">If you opened the file straight from your computer, upload the files to a host (for example GitHub Pages) or start a local web server.</p></div>`;
  }
}
window.__tapnaplo = { S, HU: DICT, vecOf, totalsFor, searchCiqual, getFood, offToFood, fmt, get KEYS() { return KEYS; }, get IDX() { return IDX; }, render };
init();

})();
