"use strict";
// Allegro REST API importer. Read only: payments:read + billing:read scopes.
const MAX_ITEMS = 5000;
const MAX_MS = 60000;
const ACCEPT = "application/vnd.allegro.public.v1+json";

function hosts(sandbox) {
  return sandbox
    ? { auth: "https://allegro.pl.allegrosandbox.pl", api: "https://api.allegro.pl.allegrosandbox.pl" }
    : { auth: "https://allegro.pl", api: "https://api.allegro.pl" };
}

async function readJson(res) {
  const t = await res.text();
  try { return t ? JSON.parse(t) : {}; } catch { return {}; }
}

async function getToken(config, f, h) {
  const basic = Buffer.from(`${config.clientId}:${config.clientSecret}`).toString("base64");
  let res;
  try {
    res = await f(`${h.auth}/auth/oauth/token`, {
      method: "POST",
      headers: { Authorization: `Basic ${basic}`, "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ grant_type: "refresh_token", refresh_token: config.refreshToken }).toString(),
    });
  } catch {
    throw new Error("Allegro: nie można połączyć się z serwerem autoryzacji. Sprawdź połączenie z internetem.");
  }
  if (!res.ok) {
    if (res.status === 400 || res.status === 401) {
      throw new Error("Allegro: refresh token jest nieważny lub wygasł albo clientId/clientSecret są błędne. " +
        "Uzyskaj nowy token: zaloguj się przez autoryzację aplikacji (Authorization Code, scope allegro:api:payments:read i allegro:api:billing:read) i wpisz nowy refreshToken w konfiguracji.");
    }
    throw new Error(`Allegro: serwer autoryzacji zwrócił błąd HTTP ${res.status}.`);
  }
  const j = await readJson(res);
  if (!j.access_token) throw new Error("Allegro: odpowiedź autoryzacji nie zawiera access_token.");
  return j;
}

async function apiGet(f, h, token, path, params) {
  const qs = new URLSearchParams(params).toString();
  let res;
  try {
    res = await f(`${h.api}${path}?${qs}`, { headers: { Authorization: `Bearer ${token}`, Accept: ACCEPT } });
  } catch {
    throw new Error("Allegro: nie można połączyć się z API Allegro.");
  }
  if (res.status === 401) throw new Error("Allegro: API odrzuciło token dostępu (401). Uzyskaj nowy refresh token.");
  if (res.status === 403) throw new Error("Allegro: brak uprawnień do historii płatności/rozliczeń. Autoryzuj aplikację ze scope allegro:api:payments:read i allegro:api:billing:read.");
  if (res.status === 429) throw new Error("Allegro: przekroczono limit zapytań API, spróbuj ponownie za chwilę.");
  if (!res.ok) throw new Error(`Allegro: API zwróciło błąd HTTP ${res.status}.`);
  return readJson(res);
}

function money(v) {
  const n = Number(v?.amount);
  if (!Number.isFinite(n)) return null;
  return { amount: Math.abs(n), sign: Math.sign(n), currency: v.currency || "PLN" };
}

function ts(s) { const t = Date.parse(s); return Number.isNaN(t) ? null : t; }

/** Pages through a newest-first list until `since` is reached. */
async function paginate(fetchPage, listKey, dateKey, since, limit, state, out) {
  let offset = 0;
  for (;;) {
    if (state.count >= MAX_ITEMS || Date.now() - state.t0 > MAX_MS) return;
    const j = await fetchPage(offset);
    const items = Array.isArray(j?.[listKey]) ? j[listKey] : [];
    let reachedOld = false;
    for (const it of items) {
      const t = ts(it?.[dateKey]);
      if (t === null) continue;
      if (t < since.getTime()) { reachedOld = true; continue; }
      state.count++;
      out.push(it);
    }
    if (reachedOld || items.length < limit) return;
    offset += limit;
  }
}

module.exports = {
  name: "allegro",
  label: "Allegro",
  fields: ["clientId", "clientSecret", "refreshToken", "sandbox"],
  hints: { refreshToken: "scope: allegro:api:payments:read, allegro:api:billing:read (tylko odczyt)" },
  isConfigured(config) {
    return Boolean(config?.clientId && config?.clientSecret && config?.refreshToken);
  },
  async fetchEntries(config, since, opts = {}) {
    const f = opts.fetch ?? fetch;
    const log = opts.log ?? (() => {});
    const h = hosts(config.sandbox);
    const tok = await getToken(config, f, h);
    if (tok.refresh_token && tok.refresh_token !== config.refreshToken) {
      try { await opts.saveConfig?.({ refreshToken: tok.refresh_token }); }
      catch { log("Allegro: nie udało się zapisać nowego refresh tokena."); }
    }
    const state = { count: 0, t0: Date.now() };
    const gte = since.toISOString();
    const entries = [];

    // 1. Payment operations: sales income and refunds.
    const ops = [];
    await paginate((offset) => apiGet(f, h, tok.access_token, "/payments/payment-operations",
      { "occurredAt.gte": gte, limit: "50", offset: String(offset) }),
      "paymentOperations", "occurredAt", since, 50, state, ops);
    for (const op of ops) {
      if (!op.id) continue;
      const m = money(op.value);
      if (!m || m.amount === 0) continue;
      const who = op.participant?.login || op.participant?.companyName || "";
      const date = String(op.occurredAt).slice(0, 10);
      if (op.group === "INCOME") {
        entries.push({ extId: `pay:${op.id}`, date, amount: m.amount, currency: m.currency, kind: "income",
          title: `Allegro ${op.type || "wpłata"}${op.payment?.id ? " " + op.payment.id : ""}`, counterparty: who });
      } else if (op.group === "REFUND") {
        entries.push({ extId: `pay:${op.id}`, date, amount: m.amount, currency: m.currency, kind: "cost",
          title: `Allegro zwrot ${op.type || ""}${op.payment?.id ? " " + op.payment.id : ""}`.trim(), counterparty: who });
      }
      // OUTCOME (payouts) and BLOCKADES are not costs: skipped.
    }

    // 2. Billing entries: Allegro commissions and fees (negative values).
    const bills = [];
    await paginate((offset) => apiGet(f, h, tok.access_token, "/billing/billing-entries",
      { "occurredAt.gte": gte, limit: "100", offset: String(offset) }),
      "billingEntries", "occurredAt", since, 100, state, bills);
    for (const b of bills) {
      if (!b.id) continue;
      const m = money(b.value);
      if (!m || m.sign >= 0) continue; // positive = fee returned, not a cost
      entries.push({ extId: `bill:${b.id}`, date: String(b.occurredAt).slice(0, 10), amount: m.amount,
        currency: m.currency, kind: "cost",
        title: `Allegro opłata ${b.type?.name || b.type?.id || ""}${b.offer?.name ? " - " + b.offer.name : ""}`.trim(),
        counterparty: "Allegro" });
    }
    return entries;
  },
};
