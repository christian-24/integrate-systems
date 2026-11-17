"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs");
const os = require("os");
const path = require("path");
const importer = require("../bank-csv.js");

const FIX = path.join(__dirname, "fixtures", "bank");
const EARLY = new Date(2000, 0, 1);

function tmpDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "bank-csv-"));
}
async function run(files, since = EARLY) {
  const dir = tmpDir();
  try {
    for (const f of [].concat(files)) fs.copyFileSync(path.join(FIX, f), path.join(dir, f));
    return await importer.fetchEntries({ folder: dir }, since, { log() {} });
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

test("module shape and isConfigured", () => {
  assert.equal(importer.name, "bank-csv");
  assert.equal(importer.label, "Wyciąg z banku (CSV)");
  assert.deepEqual(importer.fields, ["folder"]);
  assert.equal(importer.isConfigured({ folder: FIX }), true);
  assert.equal(importer.isConfigured({ folder: path.join(FIX, "nie-ma") }), false);
});

test("number and date parsing", () => {
  const { parseAmount, parseDate } = importer._internal;
  assert.equal(parseAmount("1 234,56"), 1234.56);
  assert.equal(parseAmount("1 234,56"), 1234.56);
  assert.equal(parseAmount("-12,00"), -12);
  assert.equal(parseAmount("1234.56"), 1234.56);
  assert.equal(parseAmount("-1.234,56 PLN"), -1234.56);
  assert.equal(parseAmount("+2500.00"), 2500);
  assert.ok(Number.isNaN(parseAmount("abc")));
  assert.equal(parseDate("2026-01-05"), "2026-01-05");
  assert.equal(parseDate("05.01.2026"), "2026-01-05");
  assert.equal(parseDate("05-01-2026"), "2026-01-05");
  assert.equal(parseDate("2026-04-02 10:00:00"), "2026-04-02");
  assert.equal(parseDate("31.02.2026"), null);
});

test("mBank (cp1250, header block, quoted separators)", async () => {
  const buf = fs.readFileSync(path.join(FIX, "mbank.csv"));
  assert.ok(buf.includes(0xb3), "fixture really is cp1250");
  const e = await run("mbank.csv");
  assert.equal(e.length, 4);
  assert.deepEqual(
    { date: e[0].date, amount: e[0].amount, currency: e[0].currency, kind: e[0].kind },
    { date: "2026-01-05", amount: 12.5, currency: "PLN", kind: "cost" }
  );
  assert.match(e[0].title, /SKLEP ŻABKA ŁÓDŹ/);
  assert.ok(e[0].title.includes("; "), "separator inside quotes kept");
  const inc = e.find((x) => x.kind === "income");
  assert.equal(inc.amount, 1234.56);
  assert.equal(inc.date, "2026-01-10");
  // two identical rows get distinct ids
  const coffee = e.filter((x) => x.title.includes("KAWIARNIA"));
  assert.equal(coffee.length, 2);
  assert.notEqual(coffee[0].extId, coffee[1].extId);
});

test("PKO BP", async () => {
  const e = await run("pko.csv");
  assert.equal(e.length, 3);
  assert.equal(e[0].kind, "income");
  assert.equal(e[0].amount, 2500);
  assert.equal(e[0].title, "Faktura 12/2026");
  assert.equal(e[0].counterparty, "FIRMA TESTOWA, SP. Z O.O.");
  assert.equal(e[1].kind, "cost");
  assert.equal(e[1].amount, 49.99);
  assert.equal(e[2].amount, 100);
  assert.equal(e[2].counterparty, "JAN, Kowalski");
});

test("ING (cp1250, header block, duplicate Waluta columns)", async () => {
  const e = await run("ing.csv");
  assert.equal(e.length, 3);
  const inc = e.find((x) => x.kind === "income");
  assert.equal(inc.amount, 3690);
  assert.equal(inc.currency, "PLN");
  assert.equal(inc.date, "2026-03-02");
  assert.equal(inc.title, "Faktura 03/2026; usługi");
  assert.equal(inc.counterparty, "ZAKŁAD TESTOWY SP. Z O.O.");
  const cost = e.find((x) => x.title === "Opłata za prąd");
  assert.equal(cost.kind, "cost");
  assert.equal(cost.amount, 120.4);
});

test("Revolut (BOM, fee as separate cost, skips non-completed)", async () => {
  const e = await run("revolut.csv");
  assert.equal(e.length, 3);
  const pay = e.find((x) => x.title === "Hosting Co");
  assert.deepEqual([pay.kind, pay.amount, pay.currency, pay.date], ["cost", 20, "EUR", "2026-04-02"]);
  const top = e.find((x) => x.kind === "income");
  assert.equal(top.amount, 100);
  assert.equal(top.title, "Payment from Client, Ltd");
  const fee = e.find((x) => x.extId.endsWith(":fee"));
  assert.equal(fee.kind, "cost");
  assert.equal(fee.amount, 1.5);
  assert.equal(fee.date, "2026-04-03");
  assert.notEqual(fee.extId, top.extId);
  assert.ok(!e.some((x) => x.title === "Declined Shop"));
});

test("Santander, Millennium, Pekao", async () => {
  const s = await run("santander.csv");
  assert.equal(s.length, 2);
  assert.equal(s[0].kind, "income");
  assert.equal(s[0].amount, 300);
  assert.equal(s[0].date, "2026-05-04");
  assert.equal(s[0].counterparty, "ANNA TESTOWA");
  assert.equal(s[1].kind, "cost");
  const m = await run("millennium.csv");
  assert.deepEqual(m.map((x) => [x.kind, x.amount]), [["income", 1000], ["cost", 30]]);
  const p = await run("pekao.csv");
  assert.equal(p.length, 1);
  assert.deepEqual([p[0].kind, p[0].amount, p[0].title], ["cost", 99, "Opłata abonamentowa"]);
  assert.equal(p[0].counterparty, "FIRMA ŻÓŁW");
});

test("since filtering (inclusive, by date)", async () => {
  const all = await run("mbank.csv");
  assert.equal(all.length, 4);
  const from10 = await run("mbank.csv", new Date(2026, 0, 10));
  assert.equal(from10.length, 3);
  assert.ok(from10.every((x) => x.date >= "2026-01-10"));
  const none = await run("mbank.csv", new Date(2026, 0, 11));
  assert.equal(none.length, 0);
  const ing = await run("ing.csv", new Date(2026, 2, 1));
  assert.equal(ing.length, 2);
});

test("stable ids across re-export and re-import", async () => {
  const a = await run("mbank.csv");
  const b = await run("mbank.csv");
  assert.deepEqual(a.map((x) => x.extId), b.map((x) => x.extId));
  assert.equal(new Set(a.map((x) => x.extId)).size, a.length);

  // a later export containing only a subset (with different surrounding header) gives the same ids
  const dir = tmpDir();
  try {
    const text = fs.readFileSync(path.join(FIX, "pko.csv"), "utf8");
    fs.writeFileSync(path.join(dir, "a.csv"), text);
    const lines = text.split("\r\n");
    fs.writeFileSync(path.join(dir, "b.csv"), [lines[0], lines[1], lines[2]].join("\r\n") + "\r\n");
    const both = await importer.fetchEntries({ folder: dir }, EARLY, { log() {} });
    assert.equal(both.length, 3, "overlapping exports are not double counted");
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("UTF-8 without BOM and ignoring non-csv and subfolders", async () => {
  const dir = tmpDir();
  try {
    fs.copyFileSync(path.join(FIX, "pko.csv"), path.join(dir, "x.CSV"));
    fs.writeFileSync(path.join(dir, "notes.txt"), "nic");
    fs.mkdirSync(path.join(dir, "sub"));
    fs.copyFileSync(path.join(FIX, "ing.csv"), path.join(dir, "sub", "ing.csv"));
    const e = await importer.fetchEntries({ folder: dir }, EARLY, { log() {} });
    assert.equal(e.length, 3);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("unknown format throws a Polish error naming the file", async () => {
  const dir = tmpDir();
  try {
    fs.writeFileSync(path.join(dir, "dziwny.csv"), "a,b,c\n1,2,3\n");
    await assert.rejects(
      importer.fetchEntries({ folder: dir }, EARLY, { log() {} }),
      (err) => err.message.includes("dziwny.csv") && err.message.includes("nierozpoznany format")
    );
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("missing folder throws a Polish error", async () => {
  await assert.rejects(
    importer.fetchEntries({ folder: path.join(os.tmpdir(), "bank-csv-nie-ma-takiego") }, EARLY, { log() {} }),
    /Nie można odczytać folderu/
  );
});
