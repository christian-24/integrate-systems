/* Panel projektów: udostępnij film na TikToku (TikTok Studio).
   Panel otwiera https://www.tiktok.com/tiktokstudio/upload#us=<adres pakietu>. Rozszerzenie sprawdza zalogowany
   profil (inny niż w karcie, pole tiktok:, zatrzymuje się), wgrywa film, zastępuje opis (TikTok wpisuje nazwę pliku)
   i zatrzymuje się przed „Opublikuj”. Selektory: selektory/tiktok.js. */
(function () {
  'use strict';
  const S = window.PANEL_SEL, U = window.PanelUd;
  if (!S || !U || window.__panelUdTt) return;
  window.__panelUdTt = true;
  const { q, qv } = U;

  async function currentUser() {
    try {
      const r = await fetch(S.currentUser, { credentials: 'include' });
      if (r.ok) {
        const j = await r.json();
        const u = j && j.data && (j.data.username || j.data.unique_id);
        if (u) return String(u).replace(/^@/, '').toLowerCase();
      }
    } catch (e) { /* bez nazwy: sprawdzenie po napisie na ekranie */ }
    return '';
  }

  U.start({
    id: 'tiktok', name: 'TikTok', publishName: 'Opublikuj', sel: S, filesRequired: true, clearCaption: true,
    captionWait: 30000,
    at: x => '@' + x,
    ready: () => q(S.fileInput) || qv(S.caption),
    login: () => /^\/login/.test(location.pathname) || q(S.loginForm),
    user: currentUser,
    pageText: () => (document.body && document.body.innerText || '').slice(0, 20000)
  });
})();
