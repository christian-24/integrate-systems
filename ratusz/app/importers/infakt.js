"use strict";
// inFakt importer. API v3: https://docs.infakt.pl (header X-inFakt-ApiKey, offset/limit, q[...] filters).

const MAX_ITEMS = 5000;
const MAX_MS = 60000;
const LIMIT = 100;
const SERVICE = "inFakt";
const BASE = "https://api.infakt.pl/v3";
const SKIP_STATUS = /^(draft|canceled|cancelled|rejected)/i;

function ymd(d) { return d.toISOString().slice(0, 10); }

// inFakt returns amounts in grosze (integers); decimal values are taken as-is.
function money(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return NaN;
  return Number.isInteger(n) ? n / 100 : n;
}

function mapItem(it, kind) {
  if (!it || typeof it !== "object" || it.id == null) return null;
  if (it.status && SKIP_STATUS.test(String(it.status))) return null;
  if (it.kind && /proforma|draft/i.test(String(it.kind))) return null;
  const amount = money(it.gross_price);
  const date = String(it.invoice_date || it.cost_date || it.issue_date || "").slice(0, 10);
  if (!Number.isFinite(amount) || amount <= 0 || !/^\d{4}-\d{2}-\d{2}$/.test(date)) return null;
  const who = String(
    (kind === "income" ? it.client_company_name : (it.seller_name || it.seller_company_name || it.supplier_name)) ||
    [it.client_first_name, it.client_last_name].filter(Boolean).join(" ") || ""
  ).trim();
  return {
    extId: String(it.id) + (kind === "cost" ? ":cost" : ""),
    date,
    amount,
    currency: String(it.currency || "PLN").toUpperCase(),
    kind,
    title: `Faktura ${it.number || it.id}${who ? " — " + who : ""}`,
    counterparty: who,
  };
}

function httpError(status) {
  if (status === 401 || status === 403) {
    return new Error(`${SERVICE} odrzucił klucz API (${status}). Sprawdź apiKey w treasury-sources.json.`);
  }
  if (status === 429) return new Error(`${SERVICE}: zbyt wiele zapytań (429). Spróbuj ponownie za chwilę.`);
  return new Error(`${SERVICE} zwrócił błąd HTTP ${status}.`);
}

module.exports = {
  name: "infakt",
  label: "inFakt",
  fields: ["apiKey"],
  isConfigured(config) { return Boolean(config?.apiKey); },
  async fetchEntries(config, since, opts = {}) {
    const f = opts.fetch ?? fetch;
    const log = opts.log ?? (() => {});
    const from = ymd(since);
    const started = Date.now();
    const out = [];
    const sources = [
      ["income", "invoices.json", "invoice_date"],
      ["cost", "costs.json", "invoice_date"],
    ];
    for (const [kind, path, dateField] of sources) {
      let offset = 0, done = false;
      while (!done) {
        if (out.length >= MAX_ITEMS || Date.now() - started > MAX_MS) break;
        const q = new URLSearchParams({ offset: String(offset), limit: String(LIMIT), order: `${dateField} desc` });
        q.set(`q[${dateField}_gteq]`, from);
        let res;
        try {
          res = await f(`${BASE}/${path}?${q}`, {
            headers: { "X-inFakt-ApiKey": String(config.apiKey), Accept: "application/json" },
          });
        } catch (e) {
          throw new Error(`${SERVICE}: brak połączenia z serwerem.`);
        }
        if (!res.ok) throw httpError(res.status);
        const body = await res.json();
        const list = Array.isArray(body) ? body : body?.entities;
        if (!Array.isArray(list)) throw new Error(`${SERVICE} zwrócił nieoczekiwaną odpowiedź.`);
        for (const it of list) {
          const e = mapItem(it, kind);
          if (!e) continue;
          if (e.date < from) { done = true; continue; }
          out.push(e);
        }
        if (list.length < LIMIT) done = true;
        offset += LIMIT;
      }
    }
    log(`inFakt: ${out.length} pozycji`);
    return out.slice(0, MAX_ITEMS);
  },
};
