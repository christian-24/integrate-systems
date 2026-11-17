"use strict";
// Importer: bank statement CSV exports dropped into a folder (mBank, PKO BP, ING, Santander,
// Millennium, Pekao, Revolut). Read only, local files only. See README.md for the contract.
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const DEFAULT_FOLDER = "C:\\Users\\Guest\\.claude\\agent-quest\\bank";
const MAX_ITEMS = 5000;

function folderOf(config) {
  const f = config && typeof config.folder === "string" ? config.folder.trim() : "";
  return f || DEFAULT_FOLDER;
}

// ---------- decoding ----------
function decodeBuffer(buf) {
  let text;
  try {
    text = new TextDecoder("utf-8", { fatal: true }).decode(buf);
  } catch {
    text = new TextDecoder("windows-1250").decode(buf);
  }
  return text.replace(/^\uFEFF/, "");
}

// ---------- CSV parsing ----------
function parseCsv(text, delim) {
  const rows = [];
  let row = [];
  let cell = "";
  let inQ = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQ) {
      if (c === '"') {
        if (text[i + 1] === '"') { cell += '"'; i++; } else inQ = false;
      } else cell += c;
    } else if (c === '"') {
      inQ = true;
    } else if (c === delim) {
      row.push(cell); cell = "";
    } else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(cell); cell = "";
      rows.push(row); row = [];
    } else cell += c;
  }
  if (cell !== "" || row.length) { row.push(cell); rows.push(row); }
  return rows;
}

// ---------- value helpers ----------
function norm(s) {
  return String(s ?? "")
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .replace(/\u0142/g, "l").replace(/\u0141/g, "L")
    .replace(/^#/, "").toLowerCase().replace(/\s+/g, " ").trim();
}
function clean(s) { return String(s ?? "").replace(/\s+/g, " ").trim(); }

function parseDate(s) {
  const m = String(s ?? "").trim().match(/^(?:(\d{4})-(\d{2})-(\d{2})|(\d{2})[.\-](\d{2})[.\-](\d{4}))(?!\d)/);
  if (!m) return null;
  const [y, mo, d] = m[1] ? [m[1], m[2], m[3]] : [m[6], m[5], m[4]];
  const dt = new Date(Date.UTC(+y, +mo - 1, +d));
  if (dt.getUTCFullYear() !== +y || dt.getUTCMonth() !== +mo - 1 || dt.getUTCDate() !== +d) return null;
  return `${y}-${mo}-${d}`;
}

/** "1 234,56", "-12,00", "1234.56", "1.234,56", "-1 234,56 PLN" -> number (NaN when not a number). */
function parseAmount(s) {
  let t = String(s ?? "").replace(/[\s\u00a0\u202f]/g, "").replace(/[\u2212\u2013]/g, "-").replace(/[A-Za-z]+/g, "");
  if (!/\d/.test(t)) return NaN;
  const neg = t.includes("-") || /^\(.*\)$/.test(t);
  t = t.replace(/[^\d.,]/g, "");
  const lc = t.lastIndexOf(","), ld = t.lastIndexOf(".");
  if (lc >= 0 && ld >= 0) {
    const dec = lc > ld ? "," : ".";
    const thou = dec === "," ? "." : ",";
    t = t.split(thou).join("").replace(dec, ".");
  } else if (lc >= 0) {
    t = t.split(",").length > 2 ? t.split(",").join("") : t.replace(",", ".");
  } else if (ld >= 0 && t.split(".").length > 2) {
    t = t.split(".").join("");
  }
  const v = Number(t);
  return Number.isFinite(v) ? (neg ? -v : v) : NaN;
}

function sinceDay(since) {
  const d = since instanceof Date ? since : new Date(since);
  if (Number.isNaN(d.getTime())) return "0000-00-00";
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

// ---------- format table ----------
// Each format: normalized header columns that must all be present, and a row mapper.
// ctx.get(row, name) returns the cell for a normalized header name.
const FORMATS = [
  {
    id: "revolut",
    required: ["type", "started date", "completed date", "description", "amount", "fee", "currency"],
    map(r, c) {
      const state = norm(c.get(r, "state"));
      if (state && state !== "completed") return [];
      const date = parseDate(c.get(r, "completed date")) || parseDate(c.get(r, "started date"));
      const amt = parseAmount(c.get(r, "amount"));
      const fee = parseAmount(c.get(r, "fee"));
      const currency = clean(c.get(r, "currency")) || "PLN";
      const title = clean(c.get(r, "description"));
      const out = [];
      if (date && Number.isFinite(amt)) out.push({ date, signed: amt, currency, title, counterparty: "" });
      if (date && Number.isFinite(fee) && fee !== 0) {
        out.push({ date, signed: -Math.abs(fee), currency, title, counterparty: "", isFee: true });
      }
      return out;
    },
  },
  {
    id: "mbank",
    required: ["data operacji", "opis operacji", "rachunek", "kategoria", "kwota"],
    map(r, c) {
      const date = parseDate(c.get(r, "data operacji"));
      const raw = c.get(r, "kwota");
      const amt = parseAmount(raw);
      if (!date || !Number.isFinite(amt)) return [];
      const cur = (String(raw).match(/[A-Za-z]{3}/) || [])[0] || c.meta.currency || "PLN";
      return [{ date, signed: amt, currency: cur.toUpperCase(), title: clean(c.get(r, "opis operacji")), counterparty: "" }];
    },
  },
  {
    id: "pko",
    required: ["data operacji", "data waluty", "typ transakcji", "kwota", "waluta"],
    map(r, c) {
      const date = parseDate(c.get(r, "data operacji"));
      const amt = parseAmount(c.get(r, "kwota"));
      if (!date || !Number.isFinite(amt)) return [];
      const start = c.header.indexOf("opis transakcji");
      const cells = (start >= 0 ? r.slice(start) : []).map(clean).filter(Boolean);
      const labelled = (re) => {
        const hit = cells.find((x) => re.test(x));
        return hit ? clean(hit.replace(/^[^:]*:/, "")) : "";
      };
      const title = labelled(/^tytu[l\u0142]\s*:/i) || cells.join(" ") || clean(c.get(r, "typ transakcji"));
      const counterparty = labelled(/^nazwa (odbiorcy|nadawcy)\s*:/i);
      return [{ date, signed: amt, currency: clean(c.get(r, "waluta")) || "PLN", title, counterparty }];
    },
  },
  {
    id: "ing",
    required: ["data transakcji", "data ksiegowania", "dane kontrahenta", "tytul", "kwota transakcji (waluta rachunku)"],
    map(r, c) {
      const date = parseDate(c.get(r, "data transakcji")) || parseDate(c.get(r, "data ksiegowania"));
      const ai = c.header.indexOf("kwota transakcji (waluta rachunku)");
      const amt = parseAmount(r[ai]);
      if (!date || !Number.isFinite(amt)) return [];
      // the "Waluta" column right after the amount column
      const ci = c.header.findIndex((h, i) => i > ai && h === "waluta");
      return [{
        date, signed: amt, currency: clean(ci >= 0 ? r[ci] : "") || "PLN",
        title: clean(c.get(r, "tytul")), counterparty: clean(c.get(r, "dane kontrahenta")),
      }];
    },
  },
  {
    id: "santander",
    required: ["data ksiegowania", "data operacji", "opis operacji", "tytul", "nadawca/odbiorca", "kwota"],
    map(r, c) {
      const date = parseDate(c.get(r, "data operacji")) || parseDate(c.get(r, "data ksiegowania"));
      const amt = parseAmount(c.get(r, "kwota"));
      if (!date || !Number.isFinite(amt)) return [];
      const title = clean(c.get(r, "tytul")) || clean(c.get(r, "opis operacji"));
      return [{ date, signed: amt, currency: c.meta.currency || "PLN", title, counterparty: clean(c.get(r, "nadawca/odbiorca")) }];
    },
  },
  {
    id: "millennium",
    required: ["data transakcji", "odbiorca/nadawca", "opis", "obciazenia", "uznania"],
    map(r, c) {
      const date = parseDate(c.get(r, "data transakcji")) || parseDate(c.get(r, "data rozliczenia"));
      const cr = parseAmount(c.get(r, "uznania"));
      const db = parseAmount(c.get(r, "obciazenia"));
      let signed = NaN;
      if (Number.isFinite(cr) && cr !== 0) signed = Math.abs(cr);
      else if (Number.isFinite(db) && db !== 0) signed = -Math.abs(db);
      if (!date || !Number.isFinite(signed)) return [];
      return [{
        date, signed, currency: clean(c.get(r, "waluta")) || "PLN",
        title: clean(c.get(r, "opis")), counterparty: clean(c.get(r, "odbiorca/nadawca")),
      }];
    },
  },
  {
    id: "pekao",
    required: ["data ksiegowania", "nadawca / odbiorca", "tytulem", "kwota operacji", "waluta"],
    map(r, c) {
      const date = parseDate(c.get(r, "data ksiegowania")) || parseDate(c.get(r, "data waluty"));
      const amt = parseAmount(c.get(r, "kwota operacji"));
      if (!date || !Number.isFinite(amt)) return [];
      return [{
        date, signed: amt, currency: clean(c.get(r, "waluta")) || "PLN",
        title: clean(c.get(r, "tytulem")), counterparty: clean(c.get(r, "nadawca / odbiorca")),
      }];
    },
  },
];

/** Find the header row and format in a decoded file. Returns { fmt, ctx, rows, headerAt } or null. */
function detect(text) {
  for (const delim of [";", ",", "\t"]) {
    const rows = parseCsv(text, delim);
    for (let i = 0; i < Math.min(rows.length, 80); i++) {
      const header = rows[i].map(norm);
      if (header.length < 4) continue;
      const set = new Set(header);
      const fmt = FORMATS.find((f) => f.required.every((n) => set.has(n)));
      if (!fmt) continue;
      const meta = {};
      for (let k = 0; k < i; k++) {
        if (norm(rows[k][0]) === "waluta" && /^[A-Za-z]{3}$/.test(clean(rows[k][1]))) {
          meta.currency = clean(rows[k][1]).toUpperCase();
        }
      }
      const ctx = {
        header, meta,
        get: (r, n) => { const ix = header.indexOf(n); return ix >= 0 ? (r[ix] ?? "") : ""; },
      };
      return { fmt, ctx, rows, headerAt: i };
    }
  }
  return null;
}

function hashId(parts) {
  return crypto.createHash("sha1").update(parts.join("|")).digest("hex").slice(0, 24);
}

/** Parse one file's text into entries (without since filtering). Throws on unknown format. */
function parseFile(text, fileName) {
  const found = detect(text);
  if (!found) {
    throw new Error(
      `Plik \u201E${fileName}\u201D ma nierozpoznany format. Obs\u0142ugiwane eksporty CSV: mBank, PKO BP, ING, Santander, Millennium, Pekao i Revolut.`
    );
  }
  const { fmt, ctx, rows, headerAt } = found;
  const seen = new Map();
  const out = [];
  for (let i = headerAt + 1; i < rows.length; i++) {
    const r = rows[i];
    if (!r || r.every((x) => !String(x).trim())) continue;
    let items;
    try { items = fmt.map(r, ctx); } catch { items = []; }
    for (const it of items) {
      const cents = Math.round(it.signed * 100);
      if (cents === 0) continue;
      // file-independent identity; the occurrence index separates identical rows within a file
      const base = [it.date, cents, it.currency, norm(it.title), norm(it.counterparty), it.isFee ? "fee" : ""].join("\u0001");
      const idx = seen.get(base) || 0;
      seen.set(base, idx + 1);
      out.push({
        extId: hashId([base, idx]) + (it.isFee ? ":fee" : ""),
        date: it.date,
        amount: Math.abs(cents) / 100,
        currency: it.currency,
        kind: cents > 0 ? "income" : "cost",
        title: it.title,
        counterparty: it.counterparty,
      });
    }
  }
  return out;
}

module.exports = {
  name: "bank-csv",
  label: "Wyci\u0105g z banku (CSV)",
  fields: ["folder"],
  isConfigured(config) {
    try { return fs.statSync(folderOf(config)).isDirectory(); } catch { return false; }
  },
  async fetchEntries(config, since, opts = {}) {
    const log = opts.log || (() => {});
    const folder = folderOf(config);
    let names;
    try {
      names = fs.readdirSync(folder, { withFileTypes: true })
        .filter((d) => d.isFile() && /\.csv$/i.test(d.name)).map((d) => d.name).sort();
    } catch {
      throw new Error(`Nie mo\u017Cna odczyta\u0107 folderu z wyci\u0105gami bankowymi: ${folder}. Utw\u00F3rz go i wrzu\u0107 tam pliki CSV.`);
    }
    const from = sinceDay(since);
    const byId = new Map();
    for (const name of names) {
      let buf;
      try { buf = fs.readFileSync(path.join(folder, name)); } catch {
        throw new Error(`Nie mo\u017Cna odczyta\u0107 pliku \u201E${name}\u201D w folderze ${folder}.`);
      }
      const entries = parseFile(decodeBuffer(buf), name);
      log(`bank-csv: ${name}: ${entries.length} pozycji`);
      for (const e of entries) {
        if (e.date >= from && !byId.has(e.extId)) byId.set(e.extId, e);
      }
    }
    return [...byId.values()].sort((a, b) => a.date.localeCompare(b.date)).slice(0, MAX_ITEMS);
  },
  _internal: { parseAmount, parseDate, parseCsv, decodeBuffer, parseFile },
};
