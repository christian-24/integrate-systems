"use strict";
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const imp = require("../wfirma.js");

const fx = (n) => JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures", "invoices", n), "utf8"));
const since = new Date("2026-09-01T00:00:00Z");
const cfg = { accessKey: "AK-SECRET", secretKey: "SK-SECRET", appKey: "APP-SECRET", companyId: 4242 };
const ok = (body) => ({ ok: true, status: 200, json: async () => body });

test("isConfigured", () => {
  assert.equal(imp.isConfigured(cfg), true);
  assert.equal(imp.isConfigured({ accessKey: "a", secretKey: "b" }), false);
});

test("maps invoices and expenses, sends auth headers and conditions", async () => {
  const calls = [];
  const fetch = async (url, init) => {
    calls.push({ url: new URL(url), init });
    return ok(url.includes("/expenses/") ? fx("wfirma-expenses.json") : fx("wfirma-invoices.json"));
  };
  const out = await imp.fetchEntries(cfg, since, { log() {}, fetch });
  assert.equal(calls[0].url.origin + calls[0].url.pathname, "https://api2.wfirma.pl/invoices/find");
  assert.equal(calls[1].url.pathname, "/expenses/find");
  assert.equal(calls[0].url.searchParams.get("company_id"), "4242");
  assert.equal(calls[0].url.searchParams.get("outputFormat"), "json");
  assert.equal(calls[0].init.method, "POST");
  assert.equal(calls[0].init.headers.accessKey, "AK-SECRET");
  assert.equal(calls[0].init.headers.secretKey, "SK-SECRET");
  assert.equal(calls[0].init.headers.appKey, "APP-SECRET");
  const body = JSON.parse(calls[0].init.body);
  assert.deepEqual(body.invoices.parameters.conditions.condition, { field: "date", operator: "ge", value: "2026-09-01" });
  assert.equal(body.invoices.parameters.page, 1);
  assert.deepEqual(out.map((e) => e.extId), ["5001", "5003", "6001:cost"]);
  assert.deepEqual(out[0], {
    extId: "5001", date: "2026-10-06", amount: 615, currency: "PLN", kind: "income",
    title: "Faktura FV 1/2026 — Klient Pierwszy", counterparty: "Klient Pierwszy",
  });
  assert.equal(out[1].currency, "USD");
  assert.equal(out[2].kind, "cost");
  assert.equal(out[2].amount, 123);
});

test("pagination advances page and stops at since", async () => {
  const mk = (i, d) => ({ invoice: { id: String(i), fullnumber: "N" + i, type: "normal", date: d, total: "10.00", currency: "PLN", contractor: { name: "K" } } });
  const pages = [];
  const fetch = async (url, init) => {
    if (url.includes("/expenses/")) return ok({ expenses: {}, status: { code: "OK" } });
    const page = JSON.parse(init.body).invoices.parameters.page;
    pages.push(page);
    const bag = {};
    const rows = page === 1 ? Array.from({ length: 100 }, (_, i) => mk(i + 1, "2026-10-01")) : [mk(200, "2026-09-10"), mk(201, "2026-05-01")];
    rows.forEach((r, i) => { bag[String(i)] = r; });
    return ok({ invoices: bag, status: { code: "OK" } });
  };
  const out = await imp.fetchEntries(cfg, since, { log() {}, fetch });
  assert.deepEqual(pages, [1, 2]);
  assert.equal(out.length, 101);
});

test("HTTP 401 and AUTH status give Polish errors without secrets", async () => {
  const check = (e) => /wFirma odrzuciła klucze API/.test(e.message) &&
    !/AK-SECRET|SK-SECRET|APP-SECRET/.test(e.message);
  await assert.rejects(imp.fetchEntries(cfg, since, { log() {}, fetch: async () => ({ ok: false, status: 401, json: async () => ({}) }) }), check);
  await assert.rejects(imp.fetchEntries(cfg, since, { log() {}, fetch: async () => ok(fx("wfirma-auth-error.json")) }), check);
});
