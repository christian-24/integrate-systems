"use strict";
const test = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const path = require("path");
const imp = require("../ebay.js");

const fx = (n) => JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures", "marketplaces", n), "utf8"));
const res = (status, body) => ({ ok: status >= 200 && status < 300, status, text: async () => (body === undefined ? "" : JSON.stringify(body)) });
const cfg = { clientId: "cid", clientSecret: "csecret", refreshToken: "RT-OLD" };
const since = new Date("2026-03-01T00:00:00Z");

function makeFetch(handlers) {
  const calls = [];
  const fn = async (url, init) => {
    calls.push({ url: String(url), init });
    for (const [frag, h] of handlers) if (String(url).includes(frag)) return typeof h === "function" ? h(url, init) : h;
    throw new Error("unexpected " + url);
  };
  fn.calls = calls;
  return fn;
}

test("isConfigured", () => {
  assert.ok(imp.isConfigured(cfg));
  assert.ok(!imp.isConfigured({}));
});

test("token refresh, filter, kinds, fees, since", async () => {
  const f = makeFetch([
    ["/identity/v1/oauth2/token", res(200, fx("ebay-token.json"))],
    ["/sell/finances/v1/transaction", res(200, fx("ebay-transactions.json"))],
  ]);
  const out = await imp.fetchEntries(cfg, since, { fetch: f, log() {} });
  const tok = f.calls[0];
  assert.strictEqual(tok.url, "https://api.ebay.com/identity/v1/oauth2/token");
  assert.strictEqual(tok.init.headers.Authorization, "Basic " + Buffer.from("cid:csecret").toString("base64"));
  assert.match(tok.init.body, /grant_type=refresh_token/);
  assert.match(tok.init.body, /refresh_token=RT-OLD/);
  assert.match(decodeURIComponent(tok.init.body), /scope=https:\/\/api\.ebay\.com\/oauth\/api_scope\/sell\.finances/);

  const api = f.calls[1];
  assert.ok(api.url.startsWith("https://apiz.ebay.com/sell/finances/v1/transaction?"));
  assert.match(decodeURIComponent(api.url), /filter=transactionDate:\[2026-03-01T00:00:00\.000Z\.\./);
  assert.strictEqual(api.init.headers.Authorization, "Bearer v1.FAKE-ACCESS-TOKEN");

  const byId = Object.fromEntries(out.map((e) => [e.extId, e]));
  assert.deepStrictEqual(Object.keys(byId).sort(), ["tx-1", "tx-1:fee", "tx-2", "tx-3"]);
  assert.strictEqual(byId["tx-1"].kind, "income");
  assert.strictEqual(byId["tx-1"].amount, 120);
  assert.strictEqual(byId["tx-1"].currency, "EUR");
  assert.strictEqual(byId["tx-1"].date, "2026-03-10");
  assert.strictEqual(byId["tx-1"].counterparty, "buyer_a");
  assert.strictEqual(byId["tx-1:fee"].kind, "cost");
  assert.strictEqual(byId["tx-1:fee"].amount, 15.6);
  assert.strictEqual(byId["tx-2"].kind, "cost");
  assert.strictEqual(byId["tx-3"].kind, "cost");
  assert.strictEqual(byId["tx-3"].amount, 2.5);
});

test("pagination by offset", async () => {
  const mk = (i) => ({ transactionId: "t" + i, transactionType: "SALE", transactionDate: "2026-03-10T10:00:00.000Z", amount: { value: "1.00", currency: "USD" } });
  const offsets = [];
  const f = makeFetch([
    ["/identity/", res(200, fx("ebay-token.json"))],
    ["/transaction", (url) => {
      const o = Number(new URL(url).searchParams.get("offset"));
      offsets.push(o);
      return res(200, { total: 5, transactions: o >= 4 ? [mk(o)] : [mk(o), mk(o + 1)] });
    }],
  ]);
  const out = await imp.fetchEntries(cfg, since, { fetch: f, log() {}, pageSize: 2 });
  assert.deepStrictEqual(offsets, [0, 2, 4]);
  assert.strictEqual(out.length, 5);
});

test("204 means no transactions", async () => {
  const f = makeFetch([["/identity/", res(200, fx("ebay-token.json"))], ["/transaction", res(204)]]);
  assert.deepStrictEqual(await imp.fetchEntries(cfg, since, { fetch: f, log() {} }), []);
});

test("sandbox hosts", async () => {
  const f = makeFetch([["/identity/", res(200, fx("ebay-token.json"))], ["/transaction", res(204)]]);
  await imp.fetchEntries({ ...cfg, sandbox: true }, since, { fetch: f, log() {} });
  assert.ok(f.calls[0].url.startsWith("https://api.sandbox.ebay.com/"));
  assert.ok(f.calls[1].url.startsWith("https://apiz.sandbox.ebay.com/"));
});

test("expired refresh token gives a Polish error without secrets", async () => {
  const f = makeFetch([["/identity/", res(400, { error: "invalid_grant" })]]);
  await assert.rejects(imp.fetchEntries(cfg, since, { fetch: f, log() {} }), (e) => {
    assert.match(e.message, /eBay/);
    assert.match(e.message, /refresh token/);
    for (const s of ["csecret", "RT-OLD"]) assert.ok(!e.message.includes(s));
    return true;
  });
});
