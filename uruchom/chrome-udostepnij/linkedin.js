/* Panel projektów: udostępnij post na LinkedInie.
   Panel otwiera https://www.linkedin.com/feed/?shareActive=true&text=<opis>#us=<adres pakietu>. Gdy okno tworzenia
   posta się nie otworzy, rozszerzenie klika „Zacznij publikację”. Wgrywa zdjęcia albo film (edytor multimediów,
   „Dalej”), wkleja opis (gdy LinkedIn nie wpisał go sam z adresu) i zatrzymuje się przed „Opublikuj”.
   Konto: sprawdza, czy nazwa z karty (pole linkedin:) jest widoczna w oknie posta (publikujesz jako …).
   Selektory: selektory/linkedin.js. */
(function () {
  'use strict';
  const S = window.PANEL_SEL, U = window.PanelUd;
  if (!S || !U || window.__panelUdLi) return;
  window.__panelUdLi = true;
  const { q, qv, byText, waitFor, clickable, safeClick } = U;
  const editor = () => qv(S.caption);
  const starter = () => qv(S.start) || byText(S.startText, 'button, [role="button"]');

  async function open() {
    if (await waitFor(editor, 4000)) return;
    const b = await waitFor(starter, 10000);
    if (!b) throw new Error('nie znalazłem przycisku „Zacznij publikację”');
    safeClick(clickable(b));
    if (!await waitFor(editor, 8000)) throw new Error('nie otworzyło się okno tworzenia posta');
  }

  U.start({
    id: 'linkedin', name: 'LinkedIn', publishName: 'Opublikuj', sel: S,
    ready: () => editor() || starter(),
    login: () => q(S.loginForm),
    root: () => U.lastDialog(S.dialog),
    open: open,
    pageText: () => { const d = U.lastDialog(S.dialog) || document.body; return (d && d.innerText || '').slice(0, 20000); }
  });
})();
