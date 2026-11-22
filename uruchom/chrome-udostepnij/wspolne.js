/* Panel projektów: wspólna część udostępniania posta (Instagram, Facebook, LinkedIn, TikTok).
   Panel otwiera stronę tworzenia posta z adresem pakietu w hashu (#us=<adres>, dawniej #is= dla Instagrama).
   Skrypt zapamiętuje adres w tej karcie (sessionStorage: przetrwa logowanie i przełączenie konta na tej samej
   domenie), pobiera pakiet (platforma, opis, pliki, profil), sprawdza konto, otwiera tworzenie posta, wgrywa pliki,
   wkleja opis i zatrzymuje się. Przycisku publikacji nigdy nie klika: publikuje właściciel.
   Plik platformy (instagram.js, facebook.js, linkedin.js, tiktok.js) wywołuje PanelUd.start({...}).
   Stan dla testów na <html>: data-panel-is (wczytuje, konto, logowanie, gotowe, blad), data-panel-is-text,
   data-panel-is-pliki (tak, nie), data-panel-is-konto (zgodne, nieznane, brak, inne). */
(function () {
  'use strict';
  if (window.PanelUd) return;
  const KEY = 'panel-udostepnij', TTL = 30 * 60 * 1000;
  const PKG = /^https?:\/\/[^/?#]+\/udostepnij\/[0-9a-f]{32}$/;
  const NAMES = { instagram: 'Instagram', facebook: 'Facebook', linkedin: 'LinkedIn', tiktok: 'TikTok' };
  /* przyciski publikacji na każdej platformie: safeClick ich nie kliknie (plus publishText platformy) */
  const PUBLISH = ['share', 'udostępnij', 'udostępnij teraz', 'share now', 'opublikuj', 'opublikuj teraz', 'publish',
                   'publish now', 'publikuj', 'zaplanuj', 'schedule'];
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const norm = s => String(s || '').replace(/\s+/g, ' ').trim().toLowerCase();
  const list = v => Array.isArray(v) ? v : (v ? [v] : []);
  let C = null;                 // konfiguracja platformy

  /* ---------- stan w tej karcie ---------- */
  function load() { try { return JSON.parse(sessionStorage.getItem(KEY) || 'null'); } catch (e) { return null; } }
  function save(st) { try { sessionStorage.setItem(KEY, JSON.stringify(st)); } catch (e) { /* bez pamięci karty */ } }
  function takeHash() {
    const m = /[#&](?:us|is)=([^&]+)/.exec(location.hash || '');
    if (!m) return;
    let url = '';
    try { url = decodeURIComponent(m[1]); } catch (e) { url = ''; }
    if (PKG.test(url)) save({ url: url, at: Date.now(), state: 'start' });
    try { history.replaceState(null, '', location.pathname + location.search); } catch (e) { /* adres zostaje */ }
  }

  /* ---------- pasek na górze strony ---------- */
  let barHost = null;
  const attr = (n, v) => document.documentElement.setAttribute(n, v);
  function bar(state, text, buttons) {
    attr('data-panel-is', state);
    attr('data-panel-is-text', text);
    if (!document.body) return;
    if (!barHost) {
      barHost = document.createElement('div');
      barHost.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:2147483647';
      barHost.attachShadow({ mode: 'open' });
      document.body.appendChild(barHost);
    }
    const bg = { gotowe: '#1d6b3a', konto: '#a8281a', logowanie: '#a8281a', blad: '#a8281a' }[state] || '#1d2433';
    const root = barHost.shadowRoot;
    root.innerHTML = '<style>div{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;padding:10px 16px;' +
      'font:14px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:#fff;background:' + bg + '}' +
      'b{font-weight:600}span{flex:1;min-width:200px}button{font:inherit;padding:5px 12px;border-radius:6px;' +
      'border:1px solid #fff;background:transparent;color:#fff;cursor:pointer}</style>' +
      '<div role="status"><b>Panel</b><span></span></div>';
    root.querySelector('span').textContent = text;
    const box = root.querySelector('div');
    (buttons || []).concat([['Zamknij', () => { barHost.remove(); barHost = null; }]]).forEach(([label, fn]) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.textContent = label;
      b.addEventListener('click', fn);
      box.appendChild(b);
    });
  }

  /* ---------- wyszukiwanie elementów ---------- */
  const visible = el => !!(el && el.getClientRects().length);
  function q(sels, root) {
    for (const s of list(sels)) {
      const el = (root || document).querySelector(s);
      if (el) return el;
    }
    return null;
  }
  /* pierwszy widoczny element z wariantów */
  function qv(sels, root) {
    for (const s of list(sels)) {
      for (const el of (root || document).querySelectorAll(s)) if (visible(el)) return el;
    }
    return null;
  }
  function label(el) { return norm(el.getAttribute('aria-label') || el.innerText || el.textContent); }
  function byText(texts, sel, root) {
    const want = list(texts).map(norm);
    for (const el of (root || document).querySelectorAll(sel)) {
      if (want.includes(label(el)) && visible(el)) return el;
    }
    return null;
  }
  async function waitFor(fn, ms) {
    const end = Date.now() + ms;
    for (;;) {
      const v = fn();
      if (v || Date.now() > end) return v || null;
      await sleep(250);
    }
  }
  const clickable = el => el && (el.closest('a, button, [role="button"], [role="link"], [role="menuitem"]') || el);
  const publishWords = () => PUBLISH.concat(list(C && C.sel.publishText).map(norm));
  /* jedyne miejsce kliknięć: odmawia kliknięcia w przycisk publikacji (sam element i przycisk, w którym leży) */
  function safeClick(el) {
    if (!el) return false;
    const words = publishWords(), host = el.closest('button, [role="button"]');
    if (words.includes(label(el)) || (host && words.includes(label(host)))) {
      throw new Error('próba kliknięcia przycisku publikacji');
    }
    el.click();
    return true;
  }
  const lastDialog = sel => {
    const all = document.querySelectorAll(sel || '[role="dialog"]');
    return all.length ? all[all.length - 1] : null;
  };

  /* ---------- pliki ---------- */
  async function files(pkg, base) {
    const out = [];
    for (const f of pkg.files || []) {
      const r = await fetch(new URL(f.url, base).href, { credentials: 'omit', cache: 'no-store' });
      if (!r.ok) throw new Error('plik ' + f.name + ': błąd ' + r.status);
      const b = await r.blob();
      out.push(new File([b], f.name, { type: f.type || b.type }));
    }
    return out;
  }
  /* pole pliku pasujące do plików (accept: film albo zdjęcie), inaczej pierwsze */
  function pickInput(sels, fl, root) {
    const all = [];
    for (const s of list(sels)) (root || document).querySelectorAll(s).forEach(el => { if (!all.includes(el)) all.push(el); });
    const kind = fl.some(f => (f.type || '').startsWith('video/')) ? 'video' : 'image';
    return all.find(el => !el.disabled && norm(el.accept).includes(kind)) ||
           all.find(el => !el.disabled && !el.accept) || all.find(el => !el.disabled) || null;
  }
  /* szuka pola pliku; gdy go nie ma: przycisk dodawania zdjęć (i pozycja „z komputera”), na końcu strefa upuszczania.
     Kliknięcie skryptu nie otwiera systemowego okna wyboru plików (wymaga gestu użytkownika). */
  async function fileTarget(fl) {
    const S = C.sel, root = () => (C.root ? C.root() : null) || document;
    let input = pickInput(S.fileInput, fl, root()) || pickInput(S.fileInput, fl);
    if (input) return input;
    const btn = qv(S.mediaButton, root()) || (S.mediaText && byText(S.mediaText, S.button || 'button, [role="button"]', root()));
    if (btn) {
      safeClick(clickable(btn));
      const item = await waitFor(() => pickInput(S.fileInput, fl) ||
        (S.uploadText && byText(S.uploadText, S.menuItem || 'button, [role="button"], [role="menuitem"]')), 6000);
      if (item && item.tagName !== 'INPUT') safeClick(clickable(item));
      input = await waitFor(() => pickInput(S.fileInput, fl), 6000);
      if (input) return input;
    }
    const zone = qv(S.dropZone, root());
    if (zone) return zone;
    throw new Error('nie znalazłem pola wyboru plików');
  }
  function putFiles(target, fl) {
    const dt = new DataTransfer();
    fl.forEach(f => dt.items.add(f));
    if (target.tagName === 'INPUT') {
      target.files = dt.files;
      target.dispatchEvent(new Event('input', { bubbles: true }));
      target.dispatchEvent(new Event('change', { bubbles: true }));
      return;
    }
    for (const type of ['dragenter', 'dragover', 'drop']) {          // strefa upuszczania
      target.dispatchEvent(new DragEvent(type, { dataTransfer: dt, bubbles: true, cancelable: true }));
    }
  }

  /* ---------- opis ---------- */
  async function putCaption(el, text, clear) {
    el.focus();
    const isArea = el.tagName === 'TEXTAREA';
    const cur = () => norm(isArea ? el.value : el.innerText);
    const has = () => cur().includes(norm(text).slice(0, 40));
    if (has()) return true;                       // już wpisany (np. LinkedIn z text= w adresie)
    if (isArea) {
      const set = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
      set.call(el, text);
      el.dispatchEvent(new Event('input', { bubbles: true }));
      return has();
    }
    if (clear && cur()) {                          // np. TikTok wpisuje nazwę pliku
      document.execCommand('selectAll', false, null);
      document.execCommand('delete', false, null);
      await sleep(200);
    }
    const dt = new DataTransfer();                  // edytory przyjmują wklejenie (z akapitami)
    dt.setData('text/plain', text);
    el.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }));
    await sleep(300);
    if (!has()) {
      el.focus();
      document.execCommand('selectAll', false, null);
      document.execCommand('insertText', false, text);
      await sleep(300);
    }
    return has();
  }
  /* przechodzi kroki („Dalej”, „OK”) aż do pola opisu */
  async function toCaption() {
    const S = C.sel, end = Date.now() + (C.captionWait || 20000);
    while (Date.now() < end) {
      const root = (C.root ? C.root() : null) || document;
      const cap = qv(S.caption, root);
      if (cap) return cap;
      const ok = S.okText && byText(S.okText, S.button, root);
      const nx = S.nextText && byText(S.nextText, S.button, root);
      if (ok) safeClick(ok);
      else if (nx) safeClick(nx);
      await sleep(ok || nx ? 900 : 400);
    }
    throw new Error('nie doszedłem do pola opisu');
  }
  function showPublish() {
    const root = (C.root ? C.root() : null) || document;
    const b = byText(C.sel.publishText, C.sel.button, root) || byText(C.sel.publishText, C.sel.button);
    if (b) {
      b.style.outline = '3px solid #f5b400';
      b.style.outlineOffset = '3px';
      b.scrollIntoView({ block: 'nearest' });
    }
  }

  /* ---------- przebieg ---------- */
  async function run() {
    const st = load();
    if (!st || st.state === 'gotowe' || Date.now() - st.at > TTL) return;
    if (!document.body) await new Promise(r => document.addEventListener('DOMContentLoaded', r, { once: true }));
    bar('wczytuje', 'Wczytuję post z panelu…');
    let pkg;
    try {
      const r = await fetch(st.url, { credentials: 'omit', cache: 'no-store' });
      pkg = await r.json();
      if (!r.ok || !pkg.ok) throw new Error(pkg.error || 'błąd ' + r.status);
    } catch (e) {
      save(Object.assign(st, { state: 'gotowe' }));
      bar('blad', 'Nie wczytano posta z panelu: ' + (e.message || e) + '.');
      return;
    }
    const plat = pkg.platforma || 'instagram';
    if (plat !== C.id) {
      save(Object.assign(st, { state: 'gotowe' }));
      bar('blad', 'Ten post jest na ' + (NAMES[plat] || plat) + ', a to strona ' + C.name + '. Udostępnij go z panelu jeszcze raz.');
      return;
    }
    const want = String(pkg.handle || '').replace(/^@/, '').trim();
    const at = C.at || (x => '„' + x + '”');
    await waitFor(() => C.ready() || C.login(), 20000);
    if (C.login() && !C.ready()) {
      bar('logowanie', 'Zaloguj się' + (want ? ' na ' + at(want) : '') + '. Po zalogowaniu panel dokończy przygotowanie posta.');
      return;
    }
    let who = '';
    try { who = C.user ? await C.user() : ''; } catch (e) { who = ''; }
    if (want && who && norm(who) !== norm(want)) {
      attr('data-panel-is-konto', 'inne');
      bar('konto', 'Zalogowany: ' + at(who) + ', a post jest dla ' + at(want) + '. Przełącz konto; po przełączeniu panel dokończy przygotowanie posta.',
          C.switcher ? [['Przełącz konto', () => C.switcher().catch(() => {})]] : []);
      return;
    }
    try {
      bar('wczytuje', 'Pobieram pliki posta…');
      const fl = await files(pkg, st.url);
      bar('wczytuje', 'Otwieram tworzenie posta…');
      if (C.open) await C.open(fl);
      let fileErr = '';
      if (fl.length) {
        bar('wczytuje', 'Wgrywam pliki…');
        try {
          putFiles(await fileTarget(fl), fl);
          attr('data-panel-is-pliki', 'tak');
        } catch (e) {
          if (C.filesRequired) throw e;
          fileErr = e.message || String(e);
          attr('data-panel-is-pliki', 'nie');
        }
      }
      bar('wczytuje', 'Wklejam opis…');
      const cap = await toCaption();
      const ok = pkg.caption ? await putCaption(cap, pkg.caption, C.clearCaption) : true;
      save(Object.assign(st, { state: 'gotowe' }));
      showPublish();
      const seen = !who && want && C.pageText && norm(C.pageText()).includes(norm(want));
      const acc = !want ? 'brak' : who ? 'zgodne' : seen ? 'zgodne' : 'nieznane';
      attr('data-panel-is-konto', acc);
      const prof = acc === 'brak' ? ' Karta projektu nie ma pola „' + C.id + ':”: sprawdź sam, czy to właściwe konto' + (who ? ' (zalogowany: ' + at(who) + ')' : '') + '.'
        : who ? ' Konto: ' + at(who) + '.'
        : seen ? ' Na stronie widać ' + at(want) + ': sprawdź, czy to wybrane konto.'
        : ' Nie rozpoznałem konta: sprawdź, czy to ' + at(want) + '.';
      const parts = fileErr ? 'Plików nie wgrałem (' + fileErr + '): dodaj je sam (w panelu „Pobierz pliki”). ' +
                              (ok ? 'Opis jest wklejony.' : 'Opisu też nie wkleiłem: jest w panelu.')
        : ok ? (fl.length ? 'Pliki i opis są gotowe.' : 'Opis jest gotowy.')
        : 'Pliki są gotowe, opisu nie wkleiłem: wklej go sam (jest w panelu).';
      bar('gotowe', parts + prof + ' Sprawdź post i sam kliknij „' + C.publishName + '”.');
    } catch (e) {
      save(Object.assign(st, { state: 'gotowe' }));
      bar('blad', 'Nie dokończyłem: ' + (e.message || e) + '. Dokończ ręcznie albo udostępnij post z panelu jeszcze raz.');
    }
  }

  window.PanelUd = {
    sleep, norm, list, q, qv, byText, waitFor, clickable, safeClick, lastDialog, bar, visible,
    start(cfg) { C = cfg; takeHash(); run(); }
  };
})();
