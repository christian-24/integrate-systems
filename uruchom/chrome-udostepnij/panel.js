/* Panel projektów: znak obecności rozszerzenia na stronie panelu (tylko atrybuty na <html>, nic nie czyta).
   Panel po kliknięciu „Udostępnij na …” od razu wie, czy rozszerzenie jest zainstalowane, i bez niego od razu
   pokazuje „Kopiuj opis” i „Pobierz pliki” zamiast czekać ~25 s. */
(function () {
  'use strict';
  let v = '1';
  try { v = chrome.runtime.getManifest().version; } catch (e) { /* poza rozszerzeniem (test) */ }
  document.documentElement.setAttribute('data-panel-rozszerzenie', v);
  document.documentElement.setAttribute('data-panel-platformy', 'instagram,facebook,linkedin,tiktok');
})();
