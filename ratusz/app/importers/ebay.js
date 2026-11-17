"use strict";
// eBay Finances API importer. Read only: sell.finances scope.
const MAX_ITEMS = 5000;
const MAX_MS = 60000;
const SCOPE = "https://api.ebay.com/oauth/api_scope/sell.finances";

function hosts(sandbox) {
  return sandbox
    ? { id: "https://api.sandbox.ebay.com", fin: "https://apiz.sandbox.ebay.com" }
    : { id: "https://api.ebay.com", fin: "https://apiz.ebay.com" };
}

async function readJson(res) {
  const t = await res.text();
  try { return t ? JSON.parse(t) : {}; } catch { return {}; }
}

async function getToken(config, f, h) {
  const basic = Buffer.from(`${config.clientId}:${config.clientSecret}`).toString("base64");
  let res;
  try {
    res = await f(`${h.id}/identity/v1/oauth2/token`, {
      method: "POST",
      headers: { Authorization: `Basic ${basic}`, "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ grant_type: "refresh_token", refresh_token: config.refreshToken, scope: SCOPE }).toString(),
    });
  } catch {
    throw new Error("eBay: nie można połączyć się z serwerem autoryzacji. Sprawdź połączenie z internetem.");
  }
  if (!res.ok) {
    if (res.status === 400 || res.status === 401) {
      throw new Error("eBay: refresh token jest nieważny lub wygasł (ważny ok. 18 miesięcy) albo clientId/clientSecret są błędne. " +
        "Uzyskaj nowy token: w eBay Developer Program wygeneruj User Token (Authorization Code) ze scope sell.finances i wpisz nowy refreshToken w konfiguracji.");
    }
    throw new Error(`eBay: serwer autoryzacji zwrócił błąd HTTP ${res.status}.`);
  }
  const j = await readJson(res);
  if (!j.access_token) throw new Error("eBay: odpowiedź autoryzacji nie zawiera access_token.");
  return j.access_token;
}

function amt(a) {
  const n = Number(a?.value);
  if (!Number.isFinite(n)) return null;
  return { amount: Math.abs(n), currency: a.currency || "USD" };
}

module.exports = {
  name: "ebay",
  label: "eBay",
  fields: ["clientId", "clientSecret", "refreshToken", "sandbox"],
  hints: { refreshToken: "scope: sell.finances (tylko odczyt)" },
  isConfigured(config) {
    return Boolean(config?.clientId && config?.clientSecret && config?.refreshToken);
  },
  async fetchEntries(config, since, opts = {}) {
    const f = opts.fetch ?? fetch;
    const h = hosts(config.sandbox);
    const token = await getToken(config, f, h);
    const t0 = Date.now();
    const limit = opts.pageSize ?? 200;
    const filter = `transactionDate:[${since.toISOString()}..${new Date().toISOString()}]`;
    const entries = [];
    let offset = 0, seen = 0;
    for (;;) {
      if (seen >= MAX_ITEMS || Date.now() - t0 > MAX_MS) break;
      const url = `${h.fin}/sell/finances/v1/transaction?filter=${encodeURIComponent(filter)}&limit=${limit}&offset=${offset}`;
      let res;
      try {
        res = await f(url, { headers: { Authorization: `Bearer ${token}`, Accept: "application/json" } });
      } catch {
        throw new Error("eBay: nie można połączyć się z API eBay.");
      }
      if (res.status === 204) break;
      if (res.status === 401) throw new Error("eBay: API odrzuciło token dostępu (401). Uzyskaj nowy refresh token ze scope sell.finances.");
      if (res.status === 403) throw new Error("eBay: brak uprawnień do Finances API. Konto musi być objęte Managed Payments, a token mieć scope sell.finances.");
      if (res.status === 429) throw new Error("eBay: przekroczono limit zapytań API, spróbuj ponownie za chwilę.");
      if (!res.ok) throw new Error(`eBay: API zwróciło błąd HTTP ${res.status}.`);
      const j = await readJson(res);
      const txs = Array.isArray(j.transactions) ? j.transactions : [];
      for (const tx of txs) {
        seen++;
        const id = tx?.transactionId;
        const dt = Date.parse(tx?.transactionDate);
        if (!id || Number.isNaN(dt) || dt < since.getTime()) continue;
        const date = String(tx.transactionDate).slice(0, 10);
        const a = amt(tx.amount);
        const buyer = tx.buyer?.username || "";
        const ref = tx.orderId || tx.salesRecordReference || id;
        if (tx.transactionType === "SALE") {
          if (a && a.amount > 0) entries.push({ extId: String(id), date, amount: a.amount, currency: a.currency,
            kind: "income", title: `eBay zamówienie ${ref}`, counterparty: buyer });
          const fee = amt(tx.totalFeeAmount);
          if (fee && fee.amount > 0) entries.push({ extId: `${id}:fee`, date, amount: fee.amount, currency: fee.currency,
            kind: "cost", title: `eBay opłaty ${ref}`, counterparty: "eBay" });
        } else if (tx.transactionType === "REFUND") {
          if (a && a.amount > 0) entries.push({ extId: String(id), date, amount: a.amount, currency: a.currency,
            kind: "cost", title: `eBay zwrot ${ref}`, counterparty: buyer });
        } else if (tx.transactionType === "NON_SALE_CHARGE") {
          if (a && a.amount > 0) entries.push({ extId: String(id), date, amount: a.amount, currency: a.currency,
            kind: "cost", title: `eBay opłata ${tx.feeType || ref}`, counterparty: "eBay" });
        }
      }
      offset += limit;
      const total = Number(j.total);
      if (txs.length < limit || (Number.isFinite(total) && offset >= total)) break;
    }
    return entries;
  },
};
