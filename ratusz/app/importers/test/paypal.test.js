"use strict";
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const imp = require("../paypal.js");
const fx = (n) => JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures", "payments", n), "utf8"));
const resp = (status, body) => ({ status, ok: status < 300, json: async () => body });
const config = { clientId: "cid", clientSecret: "TOPSECRET" };
const DAY = 24 * 3600 * 1000;

// First search window returns fixture pages 1 and 2; later windows return nothing.
function makeFetch(calls) {
  let windowStart = null;
  return async (url, init = {}) => {
    calls.push({ url: String(url), init });
    const u = new URL(url);
    if (u.pathname === "/v1/oauth2/token") return resp(200, fx("paypal-token.json"));
    const start = u.searchParams.get("start_date");
    if (windowStart === null) windowStart = start;
    if (start === windowStart) {
      return resp(200, fx(u.searchParams.get("page") === "2" ? "paypal-page2.json" : "paypal-page1.json"));
    }
    return resp(200, { transaction_details: [], total_pages: 1, page: 1 });
  };
}

test("isConfigured", () => {
  assert.equal(imp.isConfigured({ clientId: "a" }), false);
  assert.equal(imp.isConfigured(config), true);
});

test("OAuth, windows of at most 31 days, pagination", async () => {
  const calls = [];
  const since = new Date(Date.now() - 70 * DAY);
  const out = await imp.fetchEntries(config, since, { log() {}, fetch: makeFetch(calls) });
  const tok = calls[0];
  assert.equal(tok.url, "https://api-m.paypal.com/v1/oauth2/token");
  assert.equal(tok.init.headers.Authorization, "Basic " + Buffer.from("cid:TOPSECRET").toString("base64"));
  assert.equal(tok.init.body, "grant_type=client_credentials");
  const searches = calls.slice(1);
  for (const c of searches) {
    const u = new URL(c.url);
    assert.equal(u.origin + u.pathname, "https://api-m.paypal.com/v1/reporting/transactions");
    assert.equal(u.searchParams.get("fields"), "all");
    assert.equal(c.init.headers.Authorization, "Bearer A21-test-token");
    const span = Date.parse(u.searchParams.get("end_date")) - Date.parse(u.searchParams.get("start_date"));
    assert.ok(span <= 31 * DAY && span > 0);
  }
  const windows = new Set(searches.map((c) => new URL(c.url).searchParams.get("start_date")));
  assert.ok(windows.size >= 3, "70 days need at least 3 windows");
  assert.ok(searches.some((c) => new URL(c.url).searchParams.get("page") === "2"));
  assert.ok(out.some((e) => e.extId === "TX006"));
});

test("sandbox host", async () => {
  const calls = [];
  await imp.fetchEntries({ ...config, sandbox: true }, new Date(Date.now() - DAY), { log() {}, fetch: makeFetch(calls) });
  assert.ok(calls.every((c) => c.url.startsWith("https://api-m.sandbox.paypal.com/")));
});

test("income, fees, refunds, skipping withdrawals and pending", async () => {
  const out = await imp.fetchEntries(config, new Date(Date.now() - 10 * DAY), { log() {}, fetch: makeFetch([]) });
  const by = Object.fromEntries(out.map((e) => [e.extId, e]));
  assert.deepEqual(by.TX001, { extId: "TX001", date: "2024-03-02", amount: 100, currency: "EUR", kind: "income", title: "Order 77", counterparty: "Jan Testowy" });
  assert.equal(by["TX001:fee"].kind, "cost");
  assert.equal(by["TX001:fee"].amount, 3.5);
  assert.equal(by.TX002.kind, "cost");
  assert.equal(by.TX002.amount, 20);
  assert.match(by.TX002.title, /^Zwrot/);
  assert.equal(by["TX002:fee"], undefined, "positive fee reversal is not a cost");
  assert.equal(by.TX003, undefined, "withdrawal skipped");
  assert.equal(by.TX004, undefined, "pending skipped");
  assert.equal(by.TX005.kind, "cost");
  assert.equal(by.TX005.currency, "USD");
  assert.equal(by["TX006:fee"].amount, 2);
  assert.ok(out.every((e) => e.amount > 0));
});

test("errors are Polish and do not leak the secret", async () => {
  await assert.rejects(
    imp.fetchEntries(config, new Date(), { log() {}, fetch: async () => resp(401, {}) }),
    (e) => /^PayPal:/.test(e.message) && !e.message.includes("TOPSECRET")
  );
  const f = async (url) => (new URL(url).pathname.includes("oauth2") ? resp(200, fx("paypal-token.json")) : resp(403, {}));
  await assert.rejects(imp.fetchEntries(config, new Date(Date.now() - DAY), { log() {}, fetch: f }), /PayPal: .*Transaction Search/);
});
