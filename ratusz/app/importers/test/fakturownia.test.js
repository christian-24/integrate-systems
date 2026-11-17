"use strict";
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const imp = require("../fakturownia.js");

const fx = (n) => JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures", "invoices", n), "utf8"));
const since = new Date("2026-09-01T00:00:00Z");
const cfg = { domain: "moja", apiToken: "SECRET-TOKEN-123" };
const ok = (body) => ({ ok: true, status: 200, json: async () => body });

test("isConfigured", () => {
  assert.equal(imp.isConfigured(cfg), true);
  assert.equal(imp.isConfigured({ domain: "x" }), false);
});

test("maps income and cost, skips proforma/rejected/old/no amount", async () => {
  const calls = [];
  const fetch = async (url, init) => {
    calls.push(new URL(url));
    return ok(new URL(url).searchParams.get("income") === "no" ? fx("fakturownia-cost.json") : fx("fakturownia-income.json"));
  };
  const out = await imp.fetchEntries(cfg, since, { log() {}, fetch });
  assert.equal(calls.length, 2);
  assert.equal(calls[0].host, "moja.fakturownia.pl");
  assert.equal(calls[0].pathname, "/invoices.json");
  assert.equal(calls[0].searchParams.get("api_token"), "SECRET-TOKEN-123");
  assert.equal(calls[0].searchParams.get("period"), "more");
  assert.equal(calls[0].searchParams.get("date_from"), "2026-09-01");
  assert.equal(calls[1].searchParams.get("income"), "no");
  assert.deepEqual(out.map((e) => e.extId), ["1001", "1002", "2001:cost"]);
  assert.deepEqual(out[0], {
    extId: "1001", date: "2026-10-05", amount: 1230, currency: "PLN", kind: "income",
    title: "Faktura FV 1/10/2026 — Przykładowa Sp. z o.o.", counterparty: "Przykładowa Sp. z o.o.",
  });
  assert.equal(out[1].currency, "EUR");
  assert.equal(out[1].amount, 100.5);
  assert.equal(out[2].kind, "cost");
  assert.equal(out[2].amount, 246);
  assert.equal(out[2].counterparty, "Dostawca Hosting SA");
});

test("pagination continues until since is reached", async () => {
  const mk = (i, date) => ({ id: i, number: "N" + i, kind: "vat", issue_date: date, price_gross: "10.00", currency: "PLN", buyer_name: "B" });
  const page1 = Array.from({ length: 100 }, (_, i) => mk(i + 1, "2026-10-01"));
  const page2 = [mk(101, "2026-09-15"), mk(102, "2026-08-01")];
  const pages = [];
  const fetch = async (url) => {
    const u = new URL(url);
    if (u.searchParams.get("income") === "no") return ok([]);
    pages.push(u.searchParams.get("page"));
    return ok(u.searchParams.get("page") === "1" ? page1 : page2);
  };
  const out = await imp.fetchEntries(cfg, since, { log() {}, fetch });
  assert.deepEqual(pages, ["1", "2"]);
  assert.equal(out.length, 101);
});

test("401 gives a Polish error without the token", async () => {
  const fetch = async () => ({ ok: false, status: 401, json: async () => ({}) });
  await assert.rejects(
    imp.fetchEntries(cfg, since, { log() {}, fetch }),
    (e) => /Fakturownia odrzuciła token API \(401\)/.test(e.message) && !e.message.includes("SECRET-TOKEN-123")
  );
});

test("network failure does not leak the token", async () => {
  const fetch = async (url) => { throw new Error("boom " + url); };
  await assert.rejects(
    imp.fetchEntries(cfg, since, { log() {}, fetch }),
    (e) => /Fakturownia/.test(e.message) && !e.message.includes("SECRET-TOKEN-123")
  );
});
