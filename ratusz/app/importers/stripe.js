"use strict";
// Stripe importer: reads balance transactions (read only).
const API = "https://api.stripe.com/v1/balance_transactions";
const MAX_ITEMS = 5000;
const MAX_MS = 60000;
const INCOME_TYPES = new Set(["charge", "payment"]);
const REFUND_TYPES = new Set(["refund", "payment_refund"]);
const FEE_TYPES = new Set(["stripe_fee", "stripe_fx_fee", "tax_fee"]);
// payout, transfer, topup etc. are movements between Stripe and the bank: skipped.

function day(unix) { return new Date(unix * 1000).toISOString().slice(0, 10); }

module.exports = {
  name: "stripe",
  label: "Stripe",
  fields: ["secretKey"],
  fieldHints: { secretKey: "Użyj klucza z ograniczeniami (restricted key, rk_live_...) z uprawnieniem tylko do odczytu: Balance transaction sources -> Read." },
  isConfigured(config) { return Boolean(config?.secretKey); },

  async fetchEntries(config, since, opts = {}) {
    const doFetch = opts.fetch ?? fetch;
    const log = opts.log ?? (() => {});
    if (!this.isConfigured(config)) throw new Error("Stripe: brak klucza secretKey w konfiguracji.");
    const out = [];
    const started = Date.now();
    const gte = Math.floor(new Date(since).getTime() / 1000);
    let after = null;
    let seen = 0;
    for (;;) {
      const qs = new URLSearchParams({ limit: "100", "created[gte]": String(gte) });
      if (after) qs.set("starting_after", after);
      let res;
      try {
        res = await doFetch(`${API}?${qs}`, { headers: { Authorization: "Bearer " + config.secretKey } });
      } catch (e) {
        throw new Error("Stripe: nie udało się połączyć z api.stripe.com.");
      }
      if (res.status === 401) throw new Error("Stripe: klucz API jest nieprawidłowy lub wygasł (401).");
      if (res.status === 403) throw new Error("Stripe: klucz nie ma uprawnień do odczytu transakcji salda (403).");
      if (res.status === 429) throw new Error("Stripe: przekroczono limit zapytań, spróbuj później.");
      if (!res.ok) throw new Error(`Stripe: API zwróciło błąd HTTP ${res.status}.`);
      let body;
      try { body = await res.json(); } catch { throw new Error("Stripe: nieprawidłowa odpowiedź API."); }
      const data = Array.isArray(body?.data) ? body.data : [];
      for (const t of data) {
        seen++;
        after = t?.id ?? after;
        if (!t || !t.id || typeof t.amount !== "number" || !t.currency || typeof t.created !== "number") continue;
        if (t.created < gte) continue;
        const currency = String(t.currency).toUpperCase();
        const date = day(t.created);
        const title = t.description || `${t.type} ${t.id}`;
        if (INCOME_TYPES.has(t.type) && t.amount > 0) {
          out.push({ extId: t.id, date, amount: t.amount / 100, currency, kind: "income", title, counterparty: "" });
        } else if (REFUND_TYPES.has(t.type) && t.amount !== 0) {
          out.push({ extId: t.id, date, amount: Math.abs(t.amount) / 100, currency, kind: "cost", title: "Zwrot: " + title, counterparty: "" });
        } else if (FEE_TYPES.has(t.type) && t.amount < 0) {
          out.push({ extId: t.id, date, amount: Math.abs(t.amount) / 100, currency, kind: "cost", title, counterparty: "" });
        }
        // Fee deducted from a payment: separate cost entry.
        if (INCOME_TYPES.has(t.type) && t.amount > 0 && typeof t.fee === "number" && t.fee > 0) {
          out.push({ extId: t.id + ":fee", date, amount: t.fee / 100, currency, kind: "cost", title: "Opłata Stripe: " + title, counterparty: "Stripe" });
        }
      }
      if (!body.has_more || !data.length || !after) break;
      if (seen >= MAX_ITEMS || Date.now() - started > MAX_MS) { log("Stripe: osiągnięto limit importu."); break; }
    }
    return out;
  },
};
