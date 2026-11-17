"use strict";
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const imp = require("../stripe.js");
const fx = (n) => JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures", "payments", n), "utf8"));
const resp = (status, body) => ({ status, ok: status < 300, json: async () => body });

function makeFetch(calls) {
  return async (url, init) => {
    calls.push({ url: String(url), init });
    const u = new URL(url);
    return resp(200, u.searchParams.get("starting_after") ? fx("stripe-page2.json") : fx("stripe-page1.json"));
  };
}
const config = { secretKey: "rk_test_SECRET123" };
const since = new Date("2023-11-01T00:00:00Z");

test("isConfigured", () => {
  assert.equal(imp.isConfigured({}), false);
  assert.equal(imp.isConfigured(config), true);
});

test("auth, pagination and since filter", async () => {
  const calls = [];
  const out = await imp.fetchEntries(config, since, { log() {}, fetch: makeFetch(calls) });
  assert.equal(calls.length, 2);
  assert.equal(calls[0].init.headers.Authorization, "Bearer rk_test_SECRET123");
  const u0 = new URL(calls[0].url);
  assert.equal(u0.origin + u0.pathname, "https://api.stripe.com/v1/balance_transactions");
  assert.equal(u0.searchParams.get("limit"), "100");
  assert.equal(u0.searchParams.get("created[gte]"), String(Math.floor(since.getTime() / 1000)));
  assert.equal(new URL(calls[1].url).searchParams.get("starting_after"), "txn_payout1");
  assert.ok(!out.some((e) => e.extId === "txn_old"));
});

test("income, fees, refunds; payouts skipped", async () => {
  const out = await imp.fetchEntries(config, since, { log() {}, fetch: makeFetch([]) });
  const by = Object.fromEntries(out.map((e) => [e.extId, e]));
  assert.deepEqual(by.txn_charge1, { extId: "txn_charge1", date: "2023-11-14", amount: 149.9, currency: "PLN", kind: "income", title: "Zamowienie 1001", counterparty: "" });
  assert.equal(by["txn_charge1:fee"].kind, "cost");
  assert.equal(by["txn_charge1:fee"].amount, 4.65);
  assert.equal(by.txn_refund1.kind, "cost");
  assert.equal(by.txn_refund1.amount, 20);
  assert.equal(by.txn_payout1, undefined);
  assert.equal(by.txn_payment2.currency, "EUR");
  assert.equal(by["txn_payment2:fee"].amount, 1);
  assert.equal(by.txn_stripefee.kind, "cost");
  assert.equal(by.txn_stripefee.amount, 0.5);
  assert.ok(out.every((e) => e.amount > 0));
});

test("errors are Polish and do not leak the key", async () => {
  for (const status of [401, 403, 500]) {
    await assert.rejects(
      imp.fetchEntries(config, since, { log() {}, fetch: async () => resp(status, {}) }),
      (e) => /^Stripe:/.test(e.message) && !e.message.includes("SECRET123")
    );
  }
  await assert.rejects(imp.fetchEntries({}, since, { log() {} }), /Stripe:/);
});
