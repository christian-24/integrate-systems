"use strict";
// wFirma importer. API v2: https://doc.wfirma.pl (api2.wfirma.pl, headers accessKey/secretKey/appKey, find with JSON body).

const MAX_ITEMS = 5000;
const MAX_MS = 60000;
const LIMIT = 100;
const SERVICE = "wFirma";
const BASE = "https://api2.wfirma.pl";
const SKIP_TYPE = /^(proforma|draft|offer|estimate|canceled|cancelled)/i;

function ymd(d) { return d.toISOString().slice(0, 10); }

function mapItem(raw, kind) {
  if (!raw || typeof raw !== "object" || raw.id == null) return null;
  if (raw.type && SKIP_TYPE.test(String(raw.type))) return null;
  if (raw.status && /draft|cancel/i.test(String(raw.status))) return null;
  const amount = Number(raw.total);
  const date = String(raw.date || raw.issue_date || "").slice(0, 10);
  if (!Number.isFinite(amount) || amount <= 0 || !/^\d{4}-\d{2}-\d{2}$/.test(date)) return null;
  const c = raw.contractor?.contractor ?? raw.contractor ?? {};
  const who = String((typeof c === "object" ? (c.altname || c.name) : c) || raw.contractor_name || "").trim();
  const number = raw.fullnumber || raw.number || raw.id;
  return {
    extId: String(raw.id) + (kind === "cost" ? ":cost" : ""),
    date,
    amount,
    currency: String(raw.currency || "PLN").toUpperCase(),
    kind,
    title: `Faktura ${number}${who ? " — " + who : ""}`,
    counterparty: who,
  };
}

function httpError(status) {
  if (status === 401 || status === 403) {
    return new Error(`${SERVICE} odrzuciła klucze API (${status}). Sprawdź accessKey, secretKey i appKey w treasury-sources.json.`);
  }
  if (status === 429) return new Error(`${SERVICE}: zbyt wiele zapytań (429). Spróbuj ponownie za chwilę.`);
  return new Error(`${SERVICE} zwróciła błąd HTTP ${status}.`);
}

module.exports = {
  name: "wfirma",
  label: "wFirma",
  fields: ["accessKey", "secretKey", "appKey", "companyId"],
  isConfigured(config) { return Boolean(config?.accessKey && config?.secretKey && config?.appKey); },
  async fetchEntries(config, since, opts = {}) {
    const f = opts.fetch ?? fetch;
    const log = opts.log ?? (() => {});
    const from = ymd(since);
    const started = Date.now();
    const out = [];
    const headers = {
      accessKey: String(config.accessKey), secretKey: String(config.secretKey), appKey: String(config.appKey),
      "Content-Type": "application/json", Accept: "application/json",
    };
    for (const [kind, plural, singular] of [["income", "invoices", "invoice"], ["cost", "expenses", "expense"]]) {
      let page = 1, done = false;
      while (!done) {
        if (out.length >= MAX_ITEMS || Date.now() - started > MAX_MS) break;
        const q = new URLSearchParams({ inputFormat: "json", outputFormat: "json" });
        if (config.companyId != null && config.companyId !== "") q.set("company_id", String(config.companyId));
        const body = {
          [plural]: {
            parameters: {
              page, limit: LIMIT,
              conditions: { condition: { field: "date", operator: "ge", value: from } },
              order: { desc: "date" },
            },
          },
        };
        let res;
        try {
          res = await f(`${BASE}/${plural}/find?${q}`, { method: "POST", headers, body: JSON.stringify(body) });
        } catch (e) {
          throw new Error(`${SERVICE}: brak połączenia z serwerem.`);
        }
        if (!res.ok) throw httpError(res.status);
        const json = await res.json();
        const code = json?.status?.code;
        if (code && code !== "OK") {
          if (/AUTH|DENIED/i.test(String(code))) throw httpError(401);
          throw new Error(`${SERVICE} zwróciła błąd (${String(code).slice(0, 40)}).`);
        }
        const bag = json?.[plural] ?? {};
        const rows = Object.keys(bag).filter((k) => /^\d+$/.test(k)).map((k) => bag[k]?.[singular]).filter(Boolean);
        for (const raw of rows) {
          const e = mapItem(raw, kind);
          if (!e) continue;
          if (e.date < from) { done = true; continue; }
          out.push(e);
        }
        if (rows.length < LIMIT) done = true;
        page++;
      }
    }
    log(`wFirma: ${out.length} pozycji`);
    return out.slice(0, MAX_ITEMS);
  },
};
