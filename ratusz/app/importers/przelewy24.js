"use strict";
// Przelewy24 importer. The REST API v1 documents no endpoint listing transactions for a date
// range (only register, verify, get-by-sessionId, refund, methods, testAccess). This importer
// therefore (1) checks the credentials with testAccess and (2) reads the transactions whose
// sessionIds are given in config.sessionIds. Without sessionIds it explains the limitation.
const MAX_ITEMS = 5000;
const MAX_MS = 60000;

function parseDate(s) {
  // P24 returns "YYYYMMDDHHmm" (also tolerate ISO dates)
  const m = /^(\d{4})(\d{2})(\d{2})/.exec(String(s ?? ""));
  if (m) return `${m[1]}-${m[2]}-${m[3]}`;
  const i = /^(\d{4}-\d{2}-\d{2})/.exec(String(s ?? ""));
  return i ? i[1] : null;
}

module.exports = {
  name: "przelewy24",
  label: "Przelewy24",
  fields: ["merchantId", "posId", "apiKey", "sandbox", "sessionIds"],
  fieldHints: {
    merchantId: "Numer sprzedawcy z panelu Przelewy24.",
    posId: "Zwykle taki sam jak merchantId.",
    apiKey: "Klucz do raportów (reports key) z panelu: Moje dane -> Dane konta. Daje tylko odczyt.",
    sandbox: "true = sandbox.przelewy24.pl",
    sessionIds: "Opcjonalnie: lista sessionId transakcji do pobrania. API Przelewy24 nie udostępnia listy transakcji z zakresu dat, więc bez tego pola użyj eksportu CSV z panelu.",
  },
  isConfigured(config) { return Boolean(config?.merchantId && config?.posId && config?.apiKey); },

  async fetchEntries(config, since, opts = {}) {
    const doFetch = opts.fetch ?? fetch;
    const log = opts.log ?? (() => {});
    if (!this.isConfigured(config)) throw new Error("Przelewy24: brak merchantId, posId lub apiKey w konfiguracji.");
    const base = (config.sandbox ? "https://sandbox.przelewy24.pl" : "https://secure.przelewy24.pl") + "/api/v1";
    const auth = "Basic " + Buffer.from(`${config.posId}:${config.apiKey}`).toString("base64");
    const headers = { Authorization: auth, Accept: "application/json" };

    async function get(path) {
      let res;
      try { res = await doFetch(base + path, { headers }); } catch { throw new Error("Przelewy24: nie udało się połączyć z API."); }
      if (res.status === 401) throw new Error("Przelewy24: posId lub klucz do raportów są nieprawidłowe (401).");
      return res;
    }

    const t = await get("/testAccess");
    if (!t.ok) throw new Error(`Przelewy24: test dostępu nie powiódł się (HTTP ${t.status}).`);

    const ids = Array.isArray(config.sessionIds) ? config.sessionIds.filter((s) => typeof s === "string" && s) : [];
    if (!ids.length) {
      throw new Error(
        "Przelewy24: dostęp działa, ale API REST Przelewy24 nie udostępnia listy transakcji z zakresu dat. " +
        "Dodaj w konfiguracji pole sessionIds (lista sessionId do pobrania) albo zaimportuj eksport CSV z panelu Przelewy24."
      );
    }

    const out = [];
    const started = Date.now();
    const sinceDay = new Date(since).toISOString().slice(0, 10);
    for (const sid of ids.slice(0, MAX_ITEMS)) {
      if (Date.now() - started > MAX_MS) { log("Przelewy24: osiągnięto limit czasu."); break; }
      const res = await get("/transaction/by/sessionId/" + encodeURIComponent(sid));
      if (res.status === 404) continue;
      if (!res.ok) throw new Error(`Przelewy24: API zwróciło błąd HTTP ${res.status}.`);
      let body;
      try { body = await res.json(); } catch { continue; }
      const d = body?.data;
      if (!d || d.orderId == null || typeof d.amount !== "number" || !d.currency) continue;
      if (d.status !== 1 && d.status !== 2) continue; // 1 = paid, 2 = paid and verified
      const date = parseDate(d.dateOfTransaction || d.date);
      if (!date || date < sinceDay) continue;
      out.push({
        extId: String(d.orderId), date, amount: d.amount / 100, currency: String(d.currency).toUpperCase(),
        kind: "income", title: d.description || `Zamówienie ${d.sessionId || sid}`, counterparty: d.clientEmail || "",
      });
    }
    return out;
  },
};
