"use strict";
// Fakturownia importer. API: https://github.com/fakturownia/API (GET /invoices.json, api_token query param).

const MAX_ITEMS = 5000;
const MAX_MS = 60000;
const PER_PAGE = 100;
const SERVICE = "Fakturownia";
const SKIP_KINDS = /^(proforma|estimate|offer|order|canceled|cancelled|correction|corrective|bill|accounting_note|wdt_proforma|import_proforma)/i;
const SKIP_STATUS = /^(draft|canceled|cancelled|rejected|szkic|anulowan)/i;

function ymd(d) { return d.toISOString().slice(0, 10); }

function normalizeDomain(domain) {
  let d = String(domain || "").trim().replace(/^https?:\/\//i, "").replace(/\/.*$/, "");
  if (d && !d.includes(".")) d += ".fakturownia.pl";
  return d;
}

function mapInvoice(inv, kind) {
  if (!inv || typeof inv !== "object" || inv.id == null) return null;
  if (inv.deleted || inv.canceled || inv.cancelled) return null;
  if (inv.kind && SKIP_KINDS.test(String(inv.kind))) return null;
  if (inv.status && SKIP_STATUS.test(String(inv.status))) return null;
  const amount = Number(inv.price_gross);
  const date = String(inv.issue_date || "").slice(0, 10);
  if (!Number.isFinite(amount) || amount <= 0 || !/^\d{4}-\d{2}-\d{2}$/.test(date)) return null;
  const who = String((kind === "income" ? inv.buyer_name : inv.seller_name) || "").trim();
  const number = String(inv.number || inv.id);
  return {
    extId: String(inv.id) + (kind === "cost" ? ":cost" : ""),
    date,
    amount,
    currency: String(inv.currency || "PLN").toUpperCase(),
    kind,
    title: `Faktura ${number}${who ? " — " + who : ""}`,
    counterparty: who,
  };
}

function httpError(status) {
  if (status === 401 || status === 403) {
    return new Error(`${SERVICE} odrzuciła token API (${status}). Sprawdź apiToken w treasury-sources.json.`);
  }
  if (status === 404) return new Error(`${SERVICE}: nie znaleziono konta (404). Sprawdź domain w treasury-sources.json.`);
  if (status === 429) return new Error(`${SERVICE}: zbyt wiele zapytań (429). Spróbuj ponownie za chwilę.`);
  return new Error(`${SERVICE} zwróciła błąd HTTP ${status}.`);
}

module.exports = {
  name: "fakturownia",
  label: "Fakturownia",
  fields: ["domain", "apiToken"],
  isConfigured(config) { return Boolean(config?.domain && config?.apiToken); },
  async fetchEntries(config, since, opts = {}) {
    const f = opts.fetch ?? fetch;
    const log = opts.log ?? (() => {});
    const host = normalizeDomain(config.domain);
    const from = ymd(since);
    const to = ymd(new Date());
    const started = Date.now();
    const out = [];
    for (const kind of ["income", "cost"]) {
      let page = 1, done = false;
      while (!done) {
        if (out.length >= MAX_ITEMS || Date.now() - started > MAX_MS) break;
        const q = new URLSearchParams({
          api_token: String(config.apiToken), period: "more", date_from: from, date_to: to,
          search_date_type: "issue_date", order: "issue_date.desc", page: String(page), per_page: String(PER_PAGE),
        });
        if (kind === "cost") q.set("income", "no");
        let res;
        try {
          res = await f(`https://${host}/invoices.json?${q}`, { headers: { Accept: "application/json" } });
        } catch (e) {
          throw new Error(`${SERVICE}: brak połączenia z serwerem (${host}).`);
        }
        if (!res.ok) throw httpError(res.status);
        const list = await res.json();
        if (!Array.isArray(list)) throw new Error(`${SERVICE} zwróciła nieoczekiwaną odpowiedź.`);
        for (const inv of list) {
          const e = mapInvoice(inv, kind);
          if (!e) continue;
          if (e.date < from) { done = true; continue; }
          out.push(e);
        }
        if (list.length < PER_PAGE) done = true;
        page++;
      }
    }
    log(`Fakturownia: ${out.length} pozycji`);
    return out.slice(0, MAX_ITEMS);
  },
};
