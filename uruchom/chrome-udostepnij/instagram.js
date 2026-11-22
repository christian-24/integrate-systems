/* Panel projektów: udostępnij post na Instagramie (https://www.instagram.com/#us=<adres pakietu>; dawniej #is=).
   Sprawdza zalogowany profil (inny niż w karcie: zatrzymuje się i proponuje przełączenie konta), otwiera tworzenie
   posta, wgrywa pliki, przechodzi kroki „Dalej” (film: komunikat „OK” o rolkach), wkleja opis. „Udostępnij” klika
   właściciel. Wspólna część: wspolne.js, selektory: selektory/instagram.js. */
(function () {
  'use strict';
  const S = window.PANEL_SEL, U = window.PanelUd;
  if (!S || !U || window.__panelUdIg) return;
  window.__panelUdIg = true;
  const { q, byText, waitFor, clickable, safeClick } = U;

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
    U.bar('konto', 'Nie otworzyłem przełączania kont. Otwórz menu „Więcej” → „Przełącz konta” i wybierz właściwy profil.');
  }
  /* okno tworzenia posta: „Nowy post” w menu, potem (gdy jest) podmenu „Post”; czeka na pole pliku */
  async function openCreate() {
    if (q(S.fileInput)) return;
    const btn = await waitFor(() => q(S.create), 15000);
    if (!btn) throw new Error('nie znaleziono przycisku tworzenia posta');
    safeClick(clickable(btn));
    const next = await waitFor(() => q(S.fileInput) || byText(S.postMenuText, S.menuItem), 8000);
    if (next && next.tagName !== 'INPUT') safeClick(clickable(next));
    if (!await waitFor(() => q(S.fileInput), 10000)) throw new Error('nie otworzyło się okno tworzenia posta');
  }

  U.start({
    id: 'instagram', name: 'Instagram', publishName: 'Udostępnij', sel: S, filesRequired: true,
    at: x => '@' + x,
    ready: () => q(S.create) || q(S.fileInput),
    login: () => q(S.loginForm),
    user: currentUser,
    switcher: openSwitcher,
    root: () => U.lastDialog(S.dialog),
    open: openCreate
  });
})();
