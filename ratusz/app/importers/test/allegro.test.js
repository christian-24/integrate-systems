"use strict";
const test = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const path = require("path");
const imp = require("../allegro.js");

const fx = (n) => JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures", "marketplaces", n), "utf8"));
const res = (status, body) => ({ ok: status >= 200 && status < 300, status, text: async () => JSON.stringify(body) });
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
const std = () => [
  ["/auth/oauth/token", res(200, fx("allegro-token.json"))],
  ["/payments/payment-operations", res(200, fx("allegro-payment-operations.json"))],
  ["/billing/billing-entries", res(200, fx("allegro-billing-entries.json"))],
];

test("isConfigured", () => {
  assert.ok(imp.isConfigured(cfg));
  assert.ok(!imp.isConfigured({ clientId: "a" }));
});

test("token refresh call, rotated token saved, kinds, fees, since", async () => {
  const f = makeFetch(std());
  const saved = [];
  const out = await imp.fetchEntries(cfg, since, { fetch: f, log() {}, saveConfig: async (p) => saved.push(p) });
  const tok = f.calls[0];
  assert.strictEqual(tok.url, "https://allegro.pl/auth/oauth/token");
  assert.strictEqual(tok.init.method, "POST");
  assert.strictEqual(tok.init.headers.Authorization, "Basic " + Buffer.from("cid:csecret").toString("base64"));
  assert.match(tok.init.body, /grant_type=refresh_token/);
  assert.match(tok.init.body, /refresh_token=RT-OLD/);
  assert.deepStrictEqual(saved, [{ refreshToken: "RT-NEW" }]);

  const api = f.calls[1];
  assert.match(api.url, /^https:\/\/api\.allegro\.pl\/payments\/payment-operations\?/);
  assert.strictEqual(api.init.headers.Accept, "application/vnd.allegro.public.v1+json");
  assert.strictEqual(api.init.headers.Authorization, "Bearer AT-1");
  assert.match(decodeURIComponent(api.url), /occurredAt\.gte=2026-03-01T00:00:00\.000Z/);

  const byId = Object.fromEntries(out.map((e) => [e.extId, e]));
  assert.deepStrictEqual(Object.keys(byId).sort(), ["bill:bill-1", "pay:op-1", "pay:op-3"]);
  assert.strictEqual(byId["pay:op-1"].kind, "income");
  assert.strictEqual(byId["pay:op-1"].amount, 249.9);
  assert.strictEqual(byId["pay:op-1"].date, "2026-03-10");
  assert.strictEqual(byId["pay:op-1"].counterparty, "kupujacy_1");
  assert.strictEqual(byId["pay:op-3"].kind, "cost");
  assert.strictEqual(byId["pay:op-3"].amount, 50);
  assert.strictEqual(byId["bill:bill-1"].kind, "cost");
  assert.strictEqual(byId["bill:bill-1"].amount, 18.45);
  assert.match(byId["bill:bill-1"].title, /Stolik/);
  for (const e of out) assert.ok(e.amount > 0 && e.currency === "PLN");
});

test("no saveConfig is fine; sandbox hosts", async () => {
  const f = makeFetch(std());
  await imp.fetchEntries({ ...cfg, sandbox: true }, since, { fetch: f, log() {} });
  assert.ok(f.calls[0].url.startsWith("https://allegro.pl.allegrosandbox.pl/auth/oauth/token"));
  assert.ok(f.calls[1].url.startsWith("https://api.allegro.pl.allegrosandbox.pl/"));
});

test("pagination follows offset until a short page", async () => {
  const mk = (i) => ({ id: "p" + i, type: "CONTRIBUTION", group: "INCOME", value: { amount: "1.00", currency: "PLN" }, occurredAt: "2026-03-10T10:00:00.000Z" });
  const page1 = Array.from({ length: 50 }, (_, i) => mk(i));
  const page2 = [mk(50), mk(51)];
  const offsets = [];
  const f = makeFetch([
    ["/auth/oauth/token", res(200, fx("allegro-token.json"))],
    ["/payments/payment-operations", (url) => {
      const o = new URL(url).searchParams.get("offset");
      offsets.push(o);
      return res(200, { paymentOperations: o === "0" ? page1 : page2 });
    }],
    ["/billing/billing-entries", res(200, { billingEntries: [] })],
  ]);
  const out = await imp.fetchEntries(cfg, since, { fetch: f, log() {} });
  assert.deepStrictEqual(offsets, ["0", "50"]);
  assert.strictEqual(out.length, 52);
});

test("expired refresh token gives a Polish error without secrets", async () => {
  const f = makeFetch([["/auth/oauth/token", res(400, { error: "invalid_grant" })]]);
  await assert.rejects(imp.fetchEntries(cfg, since, { fetch: f, log() {} }), (e) => {
    assert.match(e.message, /Allegro/);
    assert.match(e.message, /refresh token/);
    for (const s of ["csecret", "RT-OLD"]) assert.ok(!e.message.includes(s));
    return true;
  });
});

test("403 on API names the scope", async () => {
  const f = makeFetch([["/auth/oauth/token", res(200, fx("allegro-token.json"))], ["/payments/", res(403, {})]]);
  await assert.rejects(imp.fetchEntries(cfg, since, { fetch: f, log() {} }), /allegro:api:payments:read/);
});
