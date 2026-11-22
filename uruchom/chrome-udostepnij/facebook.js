/* Panel projektów: udostępnij post na Facebooku (strona firmowa w Meta Business Suite).
   Panel otwiera https://business.facebook.com/latest/composer#us=<adres pakietu> (film z kanałem Reels:
   /latest/reels_composer). Wgrywa zdjęcia albo film, wkleja opis, przechodzi „Dalej” w rolce i zatrzymuje się przed
   „Opublikuj”. Konto: Business Suite nie ma prostego zapytania o wybraną stronę, więc rozszerzenie sprawdza, czy nazwa
   strony z karty (pole facebook:) jest widoczna na ekranie. Logowanie przenosi na inną domenę i gubi pakiet:
   po zalogowaniu udostępnij z panelu jeszcze raz. Selektory: selektory/facebook.js. */
(function () {
  'use strict';
  const S = window.PANEL_SEL, U = window.PanelUd;
  if (!S || !U || window.__panelUdFb) return;
  window.__panelUdFb = true;
  const { q, qv, byText } = U;

  U.start({
    id: 'facebook', name: 'Facebook', publishName: 'Opublikuj', sel: S,
    ready: () => qv(S.ready) || q(S.fileInput) || byText(S.mediaText, S.button),
    login: () => q(S.loginForm),
    root: () => U.lastDialog(S.dialog),
    pageText: () => (document.body && document.body.innerText || '').slice(0, 20000)
  });
})();
