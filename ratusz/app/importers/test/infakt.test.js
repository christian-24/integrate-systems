"use strict";
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const imp = require("../infakt.js");

const fx = (n) => JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures", "invoices", n), "utf8"));
const since = new Date("2026-09-01T00:00:00Z");
const cfg = { apiKey: "SECRET-KEY-456" };
const ok = (body) => ({ ok: true, status: 200, json: async () => body });

test("isConfigured", () => {
  assert.equal(imp.isConfigured(cfg), true);
  assert.equal(imp.isConfigured({}), false);
});

test("maps invoices and costs, converts grosze, skips draft/canceled/old", async () => {
  const calls = [];
  const fetch = async (url, init) => {
    calls.push({ url: new URL(url), init });
    return ok(url.includes("/costs.json") ? fx("infakt-costs.json") : fx("infakt-invoices.json"));
  };
  const out = await imp.fetchEntries(cfg, since, { log() {}, fetch });
  assert.equal(calls[0].url.origin + calls[0].url.pathname, "https://api.infakt.pl/v3/invoices.json");
  assert.equal(calls[1].url.pathname, "/v3/costs.json");
  assert.equal(calls[0].init.headers["X-inFakt-ApiKey"], "SECRET-KEY-456");
  assert.equal(calls[0].url.searchParams.get("q[invoice_date_gteq]"), "2026-09-01");
  assert.equal(calls[0].url.searchParams.get("offset"), "0");
  assert.deepEqual(out.map((e) => e.extId), ["3001", "3002", "4001:cost"]);
  assert.deepEqual(out[0], {
    extId: "3001", date: "2026-10-06", amount: 1230, currency: "PLN", kind: "income",
    title: "Faktura 2026/10/1 — Testowa Spółka", counterparty: "Testowa Spółka",
  });
  assert.equal(out[1].amount, 50.99);
  assert.equal(out[1].currency, "EUR");
  assert.equal(out[1].counterparty, "Jan Przykładowy");
  assert.equal(out[2].kind, "cost");
  assert.equal(out[2].amount, 369);
  assert.equal(out[2].title, "Faktura K/12/2026 — Biuro Rachunkowe Test");
});

test("pagination advances offset and stops at since", async () => {
  const mk = (i, d) => ({ id: i, number: "N" + i, status: "sent", invoice_date: d, gross_price: 1000, currency: "PLN", client_company_name: "K" });
  const offsets = [];
  const fetch = async (url) => {
    const u = new URL(url);
    if (u.pathname.endsWith("costs.json")) return ok({ entities: [] });
    offsets.push(u.searchParams.get("offset"));
    return ok({ entities: u.searchParams.get("offset") === "0"
      ? Array.from({ length: 100 }, (_, i) => mk(i + 1, "2026-10-01"))
      : [mk(200, "2026-09-10"), mk(201, "2026-05-01")] });
  };
  const out = await imp.fetchEntries(cfg, since, { log() {}, fetch });
  assert.deepEqual(offsets, ["0", "100"]);
  assert.equal(out.length, 101);
});

test("401 gives a Polish error without the key", async () => {
  const fetch = async () => ({ ok: false, status: 401, json: async () => ({}) });
  await assert.rejects(
    imp.fetchEntries(cfg, since, { log() {}, fetch }),
    (e) => /inFakt odrzucił klucz API \(401\)/.test(e.message) && !e.message.includes("SECRET-KEY-456")
  );
});
