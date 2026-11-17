// Treasury sync: pulls income and costs from the sources configured in
// ~/.claude/agent-quest/treasury-sources.json (bank CSV exports, invoicing systems, payment gateways,
// marketplaces), converts foreign currencies to PLN at the NBP rate of the day, assigns each entry to
// a project by the person's rules, and adds what is new to treasury.json. Manual entries are never
// touched. Secrets stay in the config file: they are sent only to each service's own API.

const fs = require("fs");
const os = require("os");
const path = require("path");

const DATA = path.join(os.homedir(), ".claude", "agent-quest");
const CONFIG = path.join(DATA, "treasury-sources.json");
const STATE = path.join(DATA, "treasury-sync.json");
const RATES = path.join(DATA, "nbp-rates.json");
const TREASURY = path.join(DATA, "treasury.json");
const FIRST_LOOKBACK_DAYS = 365;
const OVERLAP_DAYS = 3; // re-read a few days back each time: late bookings arrive, duplicates are skipped

const readJson = (file, fallback) => { try { return JSON.parse(fs.readFileSync(file, "utf8")); } catch { return fallback; } };
const writeJson = (file, value) => { fs.mkdirSync(path.dirname(file), { recursive: true }); fs.writeFileSync(file, JSON.stringify(value, null, 2)); };

// every importer module in ./importers (not tests, not the README)
function importers() {
  const dir = path.join(__dirname, "importers");
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter(f => f.endsWith(".js")).map(f => {
    try { delete require.cache[require.resolve(path.join(dir, f))]; return require(path.join(dir, f)); } catch (e) { return { name: f.replace(/\.js$/, ""), label: f, broken: e.message }; }
  }).filter(m => m.name);
}

// The config file is created with every source switched off, for the person to fill in; a source
// added later gets its empty fields appended, and nothing the person wrote is ever changed.
function ensureConfig() {
  const config = fs.existsSync(CONFIG) ? readJson(CONFIG, null) : {
    _jak: "Wpisz klucze API tylko tutaj. Ten plik zostaje na tym komputerze; klucze trafiają wyłącznie do API danej usługi. Puste pola = źródło wyłączone. Po zapisaniu kliknij „Synchronizuj” w Skarbcu.",
    _reguly: "Reguły przypisują wpis do projektu, gdy jego tytuł lub kontrahent zawiera podany tekst (bez rozróżniania wielkości liter). Pierwsza pasująca wygrywa.",
    reguly: [],
    domyslnyProjekt: "",
    zrodla: {},
  };
  if (!config) return {}; // a file the person broke: leave it alone, the Sources tab says so
  fs.mkdirSync(path.join(DATA, "bank"), { recursive: true }); // where bank CSV exports are dropped
  let changed = !fs.existsSync(CONFIG);
  config.zrodla = config.zrodla ?? {};
  for (const m of importers().filter(x => !x.broken)) {
    if (config.zrodla[m.name]) continue;
    config.zrodla[m.name] = Object.fromEntries([...(m.fields ?? []).map(f => [f, m.name === "bank-csv" && f === "folder" ? path.join(DATA, "bank") : ""]), ["projekt", ""]]);
    changed = true;
  }
  if (changed) writeJson(CONFIG, config);
  return config;
}

// ---------- currencies: NBP table A mid rate of the day (or the last working day before it) ----------
let rates = null;
async function toPLN(amount, currency, date, fetchImpl = fetch) {
  const code = String(currency || "PLN").toUpperCase();
  if (code === "PLN") return { pln: amount, rate: 1 };
  rates ??= readJson(RATES, {});
  for (let back = 0; back < 8; back++) {
    const d = new Date(Date.parse(date) - back * 86400_000).toISOString().slice(0, 10);
    const key = `${code}:${d}`;
    if (rates[key] === null) continue; // known: no table that day
    if (typeof rates[key] !== "number") {
      try {
        const r = await fetchImpl(`https://api.nbp.pl/api/exchangerates/rates/a/${code.toLowerCase()}/${d}/?format=json`);
        rates[key] = r.ok ? (await r.json()).rates?.[0]?.mid ?? null : null;
      } catch { return null; } // offline: try again next sync
      writeJson(RATES, rates);
    }
    if (typeof rates[key] === "number") return { pln: Math.round(amount * rates[key] * 100) / 100, rate: rates[key] };
  }
  return null;
}

function assign(entry, config, sourceConfig) {
  const text = `${entry.title ?? ""} ${entry.counterparty ?? ""}`.toLowerCase();
  for (const r of config.reguly ?? []) if (r?.zawiera && r.projekt && text.includes(String(r.zawiera).toLowerCase())) return r.projekt;
  return sourceConfig?.projekt || config.domyslnyProjekt || null;
}

let running = null;
/** Run every configured source once. Returns the per-source status. */
async function syncAll({ fetchImpl = fetch } = {}) {
  if (running) return running;
  running = (async () => {
    const config = ensureConfig();
    const state = readJson(STATE, {});
    const book = readJson(TREASURY, {});
    const entries = Array.isArray(book.entries) ? book.entries : [];
    const known = new Set(entries.map(e => e.id));
    for (const mod of importers()) {
      const own = config.zrodla?.[mod.name];
      const st = state[mod.name] ?? {};
      if (mod.broken) { state[mod.name] = { ...st, lastError: `Importer nie wczytał się: ${mod.broken}` }; continue; }
      if (!own || !mod.isConfigured?.(own)) continue;
      const since = st.lastSync ? new Date(Date.parse(st.lastSync) - OVERLAP_DAYS * 86400_000) : new Date(Date.now() - FIRST_LOOKBACK_DAYS * 86400_000);
      try {
        const saveConfig = patch => { const c = readJson(CONFIG, {}); c.zrodla = c.zrodla ?? {}; c.zrodla[mod.name] = { ...c.zrodla[mod.name], ...patch }; writeJson(CONFIG, c); };
        const found = await mod.fetchEntries(own, since, { log: () => {}, fetch: fetchImpl, saveConfig });
        let added = 0, pending = 0;
        for (const e of found ?? []) {
          if (!e || !e.extId || !(e.amount > 0) || !/^\d{4}-\d{2}-\d{2}$/.test(e.date ?? "")) continue;
          const id = `${mod.name}:${e.extId}`;
          if (known.has(id)) continue;
          const pln = await toPLN(e.amount, e.currency, e.date, fetchImpl);
          if (!pln) { pending++; continue; } // no rate yet: picked up by a later sync
          entries.push({
            id, source: mod.name, root: assign(e, config, own), kind: e.kind === "cost" ? "cost" : "income", amount: pln.pln, date: e.date,
            category: mod.label ?? mod.name, note: [e.title, e.counterparty].filter(Boolean).join(" · ").slice(0, 300),
            ...(pln.rate !== 1 ? { original: { amount: e.amount, currency: String(e.currency).toUpperCase(), rate: pln.rate } } : {}),
          });
          known.add(id); added++;
        }
        state[mod.name] = { lastSync: new Date().toISOString(), lastError: null, lastAdded: added, pendingRates: pending, total: (st.total ?? 0) + added };
      } catch (err) {
        state[mod.name] = { ...st, lastError: String(err?.message ?? err).slice(0, 400), lastTry: new Date().toISOString() };
      }
    }
    writeJson(TREASURY, { ...book, entries });
    writeJson(STATE, state);
    return status();
  })();
  try { return await running; } finally { running = null; }
}

/** What the Sources tab shows: no secrets, only whether each field is filled. */
function status() {
  const config = ensureConfig(), state = readJson(STATE, {});
  return {
    configFile: CONFIG, configBroken: fs.existsSync(CONFIG) && readJson(CONFIG, null) === null,
    rules: config.reguly ?? [], defaultProject: config.domyslnyProjekt ?? "",
    sources: importers().map(m => {
      const own = config.zrodla?.[m.name];
      return { name: m.name, label: m.label ?? m.name, broken: m.broken ?? null, configured: Boolean(own && !m.broken && m.isConfigured?.(own)),
        fields: (m.fields ?? []).map(f => ({ name: f, filled: Boolean(own?.[f]) })), project: own?.projekt ?? "", ...state[m.name] };
    }),
  };
}

/** Add a rule from the game ("entries containing X belong to project Y") and apply it to unassigned entries. */
function addRule(keyword, root) {
  if (!keyword || !root) return null;
  const c = ensureConfig();
  c.reguly = [...(c.reguly ?? []).filter(r => r.zawiera !== keyword), { zawiera: keyword, projekt: root }];
  writeJson(CONFIG, c);
  const book = readJson(TREASURY, {});
  for (const e of book.entries ?? []) if (!e.root && (e.note ?? "").toLowerCase().includes(keyword.toLowerCase())) e.root = root;
  writeJson(TREASURY, book);
  return status();
}

module.exports = { syncAll, status, addRule, ensureConfig, toPLN, assign, CONFIG };
