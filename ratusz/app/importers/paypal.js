"use strict";
// PayPal importer: OAuth client credentials + Transaction Search API (read only).
const WINDOW_MS = 30 * 24 * 3600 * 1000; // API allows max 31 days per request
const MAX_ITEMS = 5000;
const MAX_MS = 60000;
const PAGE_SIZE = 500;

function iso(d) { return d.toISOString().replace(/\.\d{3}Z$/, "Z"); }
function num(v) { const n = Number(v); return Number.isFinite(n) ? n : null; }

module.exports = {
  name: "paypal",
  label: "PayPal",
  fields: ["clientId", "clientSecret", "sandbox"],
  fieldHints: {
    clientId: "Aplikacja REST w PayPal Developer z włączoną tylko funkcją Transaction Search (odczyt).",
    clientSecret: "Secret tej aplikacji.",
    sandbox: "true = środowisko testowe (api-m.sandbox.paypal.com).",
  },
  isConfigured(config) { return Boolean(config?.clientId && config?.clientSecret); },

  async fetchEntries(config, since, opts = {}) {
    const doFetch = opts.fetch ?? fetch;
    const log = opts.log ?? (() => {});
    if (!this.isConfigured(config)) throw new Error("PayPal: brak clientId lub clientSecret w konfiguracji.");
    const base = config.sandbox ? "https://api-m.sandbox.paypal.com" : "https://api-m.paypal.com";
    const started = Date.now();

    async function call(url, init) {
      try { return await doFetch(url, init); } catch { throw new Error("PayPal: nie udało się połączyć z API PayPal."); }
    }

    const basic = Buffer.from(`${config.clientId}:${config.clientSecret}`).toString("base64");
    const tr = await call(base + "/v1/oauth2/token", {
      method: "POST",
      headers: { Authorization: "Basic " + basic, "Content-Type": "application/x-www-form-urlencoded", Accept: "application/json" },
      body: "grant_type=client_credentials",
    });
    if (tr.status === 401 || tr.status === 400) throw new Error("PayPal: clientId lub clientSecret są nieprawidłowe (logowanie odrzucone).");
    if (!tr.ok) throw new Error(`PayPal: logowanie nie powiodło się (HTTP ${tr.status}).`);
    let tj;
    try { tj = await tr.json(); } catch { tj = null; }
    const token = tj?.access_token;
    if (!token) throw new Error("PayPal: odpowiedź logowania nie zawiera tokenu.");

    const out = [];
    const seenIds = new Set();
    let count = 0;
    const end = new Date();
    let from = new Date(since);
    outer:
    while (from < end) {
      const to = new Date(Math.min(from.getTime() + WINDOW_MS, end.getTime()));
      let page = 1, totalPages = 1;
      while (page <= totalPages) {
        const qs = new URLSearchParams({
          start_date: iso(from), end_date: iso(to), fields: "all",
          page_size: String(PAGE_SIZE), page: String(page),
        });
        const res = await call(`${base}/v1/reporting/transactions?${qs}`, {
          headers: { Authorization: "Bearer " + token, Accept: "application/json" },
        });
        if (res.status === 401) throw new Error("PayPal: token odrzucony (401).");
        if (res.status === 403) throw new Error("PayPal: aplikacja nie ma uprawnienia Transaction Search (403). Włącz je w ustawieniach aplikacji.");
        if (res.status === 429) throw new Error("PayPal: przekroczono limit zapytań, spróbuj później.");
        if (!res.ok) throw new Error(`PayPal: API zwróciło błąd HTTP ${res.status}.`);
        let body;
        try { body = await res.json(); } catch { throw new Error("PayPal: nieprawidłowa odpowiedź API."); }
        totalPages = Number(body?.total_pages) || 1;
        for (const d of Array.isArray(body?.transaction_details) ? body.transaction_details : []) {
          count++;
          const ti = d?.transaction_info;
          if (!ti?.transaction_id) continue;
          const code = String(ti.transaction_event_code || "");
          if (ti.transaction_status && ti.transaction_status !== "S") continue; // only completed
          // T03xx/T04xx: transfers to/from bank and withdrawals, not income or cost
          if (/^T0[34]/.test(code)) continue;
          const val = num(ti.transaction_amount?.value);
          const cur = ti.transaction_amount?.currency_code;
          const when = ti.transaction_initiation_date || ti.transaction_updated_date;
          if (val === null || val === 0 || !cur || !when) continue;
          const date = String(when).slice(0, 10);
          let extId = ti.transaction_id;
          if (seenIds.has(extId)) extId = `${extId}_${code}`;
          if (seenIds.has(extId)) continue;
          seenIds.add(extId);
          const payer = d.payer_info || {};
          const counterparty = payer.payer_name?.alternate_full_name || payer.email_address || "";
          const isRefund = /^T11/.test(code);
          let title = ti.transaction_subject || ti.transaction_note || ti.invoice_id || `PayPal ${code} ${ti.transaction_id}`;
          if (isRefund && val < 0) title = "Zwrot: " + title;
          out.push({
            extId, date, amount: Math.abs(val), currency: String(cur).toUpperCase(),
            kind: val > 0 ? "income" : "cost", title, counterparty,
          });
          const fee = num(ti.fee_amount?.value);
          if (fee !== null && fee < 0) {
            out.push({
              extId: extId + ":fee", date, amount: Math.abs(fee),
              currency: String(ti.fee_amount.currency_code || cur).toUpperCase(),
              kind: "cost", title: "Opłata PayPal: " + title, counterparty: "PayPal",
            });
          }
        }
        if (count >= MAX_ITEMS || Date.now() - started > MAX_MS) { log("PayPal: osiągnięto limit importu."); break outer; }
        page++;
      }
      from = to;
    }
    return out;
  },
};
