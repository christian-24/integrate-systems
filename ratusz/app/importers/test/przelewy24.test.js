"use strict";
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const imp = require("../przelewy24.js");
const fx = (n) => JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures", "payments", n), "utf8"));
const resp = (status, body) => ({ status, ok: status < 300, json: async () => body });
const config = { merchantId: 11111, posId: 11111, apiKey: "REPORTSKEY" };
const since = new Date("2024-01-01T00:00:00Z");

function makeFetch(calls) {
  return async (url, init) => {
    calls.push({ url: String(url), init });
    if (url.endsWith("/testAccess")) return resp(200, fx("przelewy24-testaccess.json"));
    if (url.endsWith("/sess-old")) return resp(200, fx("przelewy24-session-old.json"));
    if (url.endsWith("/sess-1")) return resp(200, fx("przelewy24-session.json"));
    return resp(404, {});
  };
}

test("isConfigured", () => {
  assert.equal(imp.isConfigured({ merchantId: 1 }), false);
  assert.equal(imp.isConfigured(config), true);
});

test("basic auth, sandbox host, sessionIds, since filter", async () => {
  const calls = [];
  const out = await imp.fetchEntries({ ...config, sandbox: true, sessionIds: ["sess-1", "sess-old", "missing"] }, since, { log() {}, fetch: makeFetch(calls) });
  assert.equal(calls[0].url, "https://sandbox.przelewy24.pl/api/v1/testAccess");
  assert.equal(calls[0].init.headers.Authorization, "Basic " + Buffer.from("11111:REPORTSKEY").toString("base64"));
  assert.equal(calls[1].url, "https://sandbox.przelewy24.pl/api/v1/transaction/by/sessionId/sess-1");
  assert.deepEqual(out, [{ extId: "300001", date: "2024-03-01", amount: 49, currency: "PLN", kind: "income", title: "Zamowienie 501", counterparty: "klient@example.test" }]);
});

test("production host", async () => {
  const calls = [];
  await imp.fetchEntries({ ...config, sessionIds: ["sess-1"] }, since, { log() {}, fetch: makeFetch(calls) });
  assert.ok(calls.every((c) => c.url.startsWith("https://secure.przelewy24.pl/api/v1/")));
});

test("without sessionIds explains that the API cannot list transactions", async () => {
  await assert.rejects(
    imp.fetchEntries(config, since, { log() {}, fetch: makeFetch([]) }),
    (e) => /^Przelewy24:/.test(e.message) && /CSV/.test(e.message) && !e.message.includes("REPORTSKEY")
  );
});

test("bad credentials: Polish error without secret", async () => {
  await assert.rejects(
    imp.fetchEntries(config, since, { log() {}, fetch: async () => resp(401, {}) }),
    (e) => /^Przelewy24: .*nieprawidłowe/.test(e.message) && !e.message.includes("REPORTSKEY")
  );
});
