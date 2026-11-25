// Atrapa środowiska skryptów Google Ads (AdsApp, Utilities, UrlFetchApp, Logger) do testu skryptu z panelu.
// Użycie: node atrapa_google_ads.js <skrypt.js> <dane.json>; wypisuje JSON z wysłanymi żądaniami (bez sieci).
const fs = require('fs'), vm = require('vm');
const [, , scriptPath, dataPath] = process.argv;
const D = JSON.parse(fs.readFileSync(dataPath, 'utf8'));
const sent = [], logs = [], queries = [];
const it = rows => { let i = 0; return {hasNext: () => i < rows.length, next: () => rows[i++]}; };
const ctx = {
  AdsApp: {
    currentAccount: () => ({getTimeZone: () => 'Europe/Warsaw', getCustomerId: () => D.konto}),
    search: q => { queries.push(q);
      if (/FROM search_term_view/.test(q)) return it(D.hasla);
      if (/conversion_action/.test(q)) return it(D.konwersje);
      return it(D.grupy); },
  },
  Utilities: {formatDate: (d, tz, f) => d.toISOString().slice(0, 10)},
  UrlFetchApp: {fetch: (url, o) => { sent.push({url, headers: o.headers, method: o.method, contentType: o.contentType, body: JSON.parse(o.payload)});
    return {getResponseCode: () => 200, getContentText: () => 'ok'}; }},
  Logger: {log: m => logs.push(String(m))},
  Date, JSON, Number, String, Error,
};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(scriptPath, 'utf8') + '\nmain();', ctx);
const mutating = queries.filter(q => !/^\s*SELECT\b/i.test(q));
process.stdout.write(JSON.stringify({sent, logs, queries, mutating}));
