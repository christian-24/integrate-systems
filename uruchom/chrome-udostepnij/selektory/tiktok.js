/* Selektory i napisy TikTok Studio (www.tiktok.com/tiktokstudio/upload): jedyne miejsce do poprawek, gdy TikTok
   zmieni wygląd. Listy to warianty sprawdzane po kolei (pierwszy pasujący wygrywa); napisy bez wielkości liter.
   Niesprawdzone na prawdziwej stronie: tylko na atrapie (dashboard/testy/atrapa_tiktok.html). */
window.PANEL_SEL = {
  // pole pliku na stronie wgrywania (ukryte za przyciskiem „Wybierz film”)
  fileInput: ['input[type="file"][accept*="video"]', 'input[type="file"]'],
  // formularz logowania (strona /login)
  loginForm: ['input[type="password"]', 'input[name="username"]', 'form[action*="login"]'],
  // pole opisu po wybraniu filmu (edytor Draft.js; TikTok wpisuje tam nazwę pliku, rozszerzenie ją zastępuje)
  caption: ['.public-DraftEditor-content[contenteditable="true"]', '[contenteditable="true"][role="combobox"]',
            '[contenteditable="true"][role="textbox"]', 'div[contenteditable="true"]'],
  // zalogowane konto: zapytanie strony (nazwa profilu), inaczej nazwa widoczna na ekranie
  currentUser: '/passport/web/account/info/?aid=1988&app_language=en',
  button: '[role="button"], button',
  // przycisk publikacji: rozszerzenie go NIE klika (safeClick odmawia), tylko wyróżnia
  publishText: ['Post', 'Opublikuj', 'Publikuj', 'Post now', 'Schedule', 'Zaplanuj']
};
