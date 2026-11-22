/* Panel projektów: udostępnij post na Instagramie.
   Panel otwiera https://www.instagram.com/#is=<adres pakietu>. Skrypt zapamiętuje adres w tej karcie, pobiera pakiet
   (opis, pliki, profil), sprawdza zalogowany profil, otwiera tworzenie posta, wgrywa pliki, przechodzi kroki „Dalej”,
   wkleja opis i zatrzymuje się. Przycisku „Udostępnij” nigdy nie klika: publikuje właściciel.
   Stan dla testów: atrybut data-panel-is na <html> (wczytuje, konto, logowanie, gotowe, blad) i data-panel-is-text. */
(function () {
  'use strict';
  const S = window.IS_SEL;
  if (!S || window.__panelIs) return;
  window.__panelIs = true;
  const KEY = 'panel-udostepnij', TTL = 30 * 60 * 1000;
  const PKG = /^https?:\/\/[^/?#]+\/udostepnij\/[0-9a-f]{32}$/;
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const norm = s => String(s || '').replace(/\s+/g, ' ').trim().toLowerCase();
  const list = v => Array.isArray(v) ? v : [v];

  /* ---------- stan w tej karcie (sessionStorage: przetrwa przełączenie konta i przeładowanie) ---------- */
  function load() { try { return JSON.parse(sessionStorage.getItem(KEY) || 'null'); } catch (e) { return null; } }
  function save(st) { try { sessionStorage.setItem(KEY, JSON.stringify(st)); } catch (e) { /* bez pamięci karty */ } }
  function takeHash() {
    const m = /[#&]is=([^&]+)/.exec(location.hash || '');
    if (!m) return;
    let url = '';
    try { url = decodeURIComponent(m[1]); } catch (e) { url = ''; }
    if (PKG.test(url)) save({ url: url, at: Date.now(), state: 'start' });
    try { history.replaceState(null, '', location.pathname + location.search); } catch (e) { /* adres zostaje */ }
  }

  /* ---------- pasek na górze strony ---------- */
  let barHost = null;
  function mark(state, text) {
    document.documentElement.setAttribute('data-panel-is', state);
    document.documentElement.setAttribute('data-panel-is-text', text);
  }
  function bar(state, text, buttons) {
    mark(state, text);
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
  function q(sels, root) {
    for (const s of list(sels)) {
      const el = (root || document).querySelector(s);
      if (el) return el;
    }
    return null;
  }
  function label(el) { return norm(el.getAttribute('aria-label') || el.innerText || el.textContent); }
  function byText(texts, sel, root) {
    const want = list(texts).map(norm);
    for (const el of (root || document).querySelectorAll(sel)) {
      if (want.includes(label(el)) && el.getClientRects().length) return el;
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
  /* jedyne miejsce kliknięć: odmawia kliknięcia w przycisk publikacji */
  function safeClick(el) {
    if (!el) return false;
    if (list(S.shareText).map(norm).includes(label(el))) throw new Error('próba kliknięcia przycisku publikacji');
    el.click();
    return true;
  }
  const dialog = () => {
    const all = document.querySelectorAll(S.dialog);
    return all.length ? all[all.length - 1] : null;
  };

  /* ---------- zalogowany profil ---------- */
  async function currentUser() {
    try {
      const r = await fetch(S.currentUser, { credentials: 'include',
        headers: { 'X-IG-App-ID': S.appId, 'X-Requested-With': 'XMLHttpRequest' } });
      if (r.ok) {
        const j = await r.json();
        const u = j && j.user && j.user.username;
        if (u) return String(u).toLowerCase();
      }
    } catch (e) { /* niżej: obrazek profilu */ }
    for (const img of document.querySelectorAll(S.profileImg)) {
      for (const re of S.profileAlt) {
        const m = re.exec(img.getAttribute('alt') || '');
        if (m) return m[1].trim().replace(/^@/, '').toLowerCase();
      }
    }
    return '';
  }
  async function openSwitcher() {
    const more = q(S.moreMenu);
    if (more) {
      safeClick(clickable(more));
      const item = await waitFor(() => byText(S.switchText, S.menuItem), 4000);
      if (item) { safeClick(clickable(item)); return; }
    }
    bar('konto', 'Nie otworzyłem przełączania kont. Otwórz menu „Więcej” → „Przełącz konta” i wybierz właściwy profil.');
  }

  /* ---------- kroki ---------- */
  async function files(pkg, base) {
    const out = [];
    for (const f of pkg.files) {
      const r = await fetch(new URL(f.url, base).href, { credentials: 'omit', cache: 'no-store' });
      if (!r.ok) throw new Error('plik ' + f.name + ': błąd ' + r.status);
      const b = await r.blob();
      out.push(new File([b], f.name, { type: f.type || b.type }));
    }
    return out;
  }
  async function openCreate() {
    if (q(S.fileInput)) return q(S.fileInput);
    const btn = await waitFor(() => q(S.create), 15000);
    if (!btn) throw new Error('nie znaleziono przycisku tworzenia posta');
    safeClick(clickable(btn));
    const next = await waitFor(() => q(S.fileInput) || byText(S.postMenuText, S.menuItem), 8000);
    if (next && next.tagName !== 'INPUT') safeClick(clickable(next));
    const input = await waitFor(() => q(S.fileInput), 10000);
    if (!input) throw new Error('nie otworzyło się okno tworzenia posta');
    return input;
  }
  function putFiles(input, list) {
    const dt = new DataTransfer();
    list.forEach(f => dt.items.add(f));
    input.files = dt.files;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }
  async function toCaption() {
    for (let i = 0; i < 40; i++) {
      const cap = q(S.caption);
      if (cap) return cap;
      const d = dialog();
      const ok = d && byText(S.okText, S.button, d);
      const nx = d && byText(S.nextText, S.button, d);
      if (ok) safeClick(ok);
      else if (nx) safeClick(nx);
      await sleep(ok || nx ? 900 : 400);
    }
    throw new Error('nie doszedłem do pola opisu');
  }
  async function putCaption(el, text) {
    el.focus();
    const has = () => norm(el.value != null && el.tagName === 'TEXTAREA' ? el.value : el.innerText).includes(norm(text).slice(0, 40));
    if (el.tagName === 'TEXTAREA') {
      const set = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
      set.call(el, text);
      el.dispatchEvent(new Event('input', { bubbles: true }));
      return has();
    }
    const dt = new DataTransfer();                  // edytor Instagrama przyjmuje wklejenie (z akapitami)
    dt.setData('text/plain', text);
    el.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }));
    await sleep(300);
    if (!has()) {
      document.execCommand('selectAll', false, null);
      document.execCommand('insertText', false, text);
      await sleep(300);
    }
    return has();
  }
  function showShare() {
    const d = dialog();
    const b = d && byText(S.shareText, S.button, d);
    if (b) {
      b.style.outline = '3px solid #f5b400';
      b.style.outlineOffset = '3px';
      b.scrollIntoView({ block: 'nearest' });
    }
  }

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
    const want = String(pkg.handle || '').toLowerCase();
    await waitFor(() => q(S.create) || q(S.loginForm), 15000);
    if (q(S.loginForm) && !q(S.create)) {
      bar('logowanie', 'Zaloguj się' + (want ? ' na profil @' + want : '') + '. Po zalogowaniu panel dokończy przygotowanie posta.');
      return;
    }
    const who = await currentUser();
    if (want && who && who !== want) {
      bar('konto', 'Zalogowany: @' + who + ', a post jest dla @' + want + '. Przełącz konto; po przełączeniu panel dokończy przygotowanie posta.',
          [['Przełącz konto', () => openSwitcher().catch(() => {})]]);
      return;
    }
    try {
      bar('wczytuje', 'Pobieram pliki posta…');
      const fl = await files(pkg, st.url);
      bar('wczytuje', 'Otwieram tworzenie posta…');
      putFiles(await openCreate(), fl);
      bar('wczytuje', 'Wgrywam pliki i przechodzę do opisu…');
      const cap = await toCaption();
      const ok = pkg.caption ? await putCaption(cap, pkg.caption) : true;
      save(Object.assign(st, { state: 'gotowe' }));
      showShare();
      const prof = !want ? ' Karta projektu nie ma profilu Instagram: sprawdź sam, czy to właściwe konto' + (who ? ' (zalogowany: @' + who + ')' : '') + '.'
        : !who ? ' Nie rozpoznałem zalogowanego profilu: sprawdź, czy to @' + want + '.' : ' Profil: @' + who + '.';
      bar('gotowe', (ok ? 'Pliki i opis są gotowe.' : 'Pliki są gotowe, opisu nie wkleiłem: wklej go sam (jest w panelu).') +
          prof + ' Sprawdź post i sam kliknij „Udostępnij”.');
    } catch (e) {
      save(Object.assign(st, { state: 'gotowe' }));
      bar('blad', 'Nie dokończyłem: ' + (e.message || e) + '. Dokończ ręcznie albo udostępnij post z panelu jeszcze raz.');
    }
  }

  takeHash();
  run();
})();
