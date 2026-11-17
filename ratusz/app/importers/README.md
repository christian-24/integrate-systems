# Treasury importers: the contract

The Treasury (Skarbiec) pulls a project's income and costs from outside sources. Each source is one
CommonJS module in this folder, used by `app/treasury-sync.js`. Node 24, no npm packages: use the
global `fetch`, `fs`, `path`, `crypto`, `Buffer`.

## Module shape

```js
// app/importers/<name>.js
module.exports = {
  name: "stripe",                       // the key used in treasury-sources.json
  label: "Stripe",                      // shown to the person
  /** Which config fields the person must fill in (shown in the Sources tab). */
  fields: ["secretKey"],
  /** True when the config for this source has what it needs to run. */
  isConfigured(config) { return Boolean(config?.secretKey); },
  /**
   * Read transactions since `since` (a Date). Return plain objects, newest or oldest first:
   * { extId, date, amount, currency, kind, title, counterparty }
   * - extId: stable unique id from the source (prefix with nothing; the framework adds the source name)
   * - date: "YYYY-MM-DD" (the day the money moved, or the invoice issue date for invoices)
   * - amount: positive number in `currency` units (e.g. 1499.5), never negative
   * - currency: ISO code, e.g. "PLN", "EUR", "USD"
   * - kind: "income" (money in / sales / issued invoices) or "cost" (money out / fees / cost invoices)
   * - title: a short human text (transfer title, invoice number + buyer, order id + item)
   * - counterparty: who paid or was paid, if known, else ""
   * Throw an Error with a clear Polish message when the source refuses (bad key, no access):
   * the message is shown to the person as is. Never log or include secrets in errors.
   */
  async fetchEntries(config, since, { log }) { return []; },
};
```

`config` is this source's object from `C:\Users\Guest\.claude\agent-quest\treasury-sources.json`,
which the person edits themselves. Never write to that file, never print its secrets.

## Rules for every importer

- Read only. Call only the official API host of the service (or read local files for CSV). No other
  network calls. Use the least privilege the API offers and say which in `fields` hints.
- Paginate until `since` is reached; stop after 5000 items or 60 s, whichever first.
- Fees: when the API reports a fee separately from a payment, return the payment as `income` and
  the fee as its own `cost` entry (`extId` suffixed `:fee`).
- Refunds: return as `cost` with the refund's own `extId`.
- Be defensive: missing fields mean skipping that item, not crashing the whole import.

## Tests

Each importer has `app/importers/test/<name>.test.js`, run with `node --test "app/importers/test/*.test.js"` (Node 24 does not take the bare folder).
Test against recorded sample responses (fixtures in `app/importers/test/fixtures/`, invented data,
no real names or accounts) by passing a fake `fetch` through the third argument:
`fetchEntries(config, since, { log, fetch: fakeFetch })` (importers use `opts.fetch ?? fetch`).
