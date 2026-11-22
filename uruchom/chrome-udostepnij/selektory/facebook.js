/* Selektory i napisy Meta Business Suite (business.facebook.com: tworzenie posta /latest/composer i rolki
   /latest/reels_composer) oraz www.facebook.com: jedyne miejsce do poprawek, gdy Meta zmieni wygląd.
   Listy to warianty sprawdzane po kolei (pierwszy pasujący wygrywa); napisy bez wielkości liter, po polsku i angielsku.
   Niesprawdzone na prawdziwej stronie: tylko na atrapie (dashboard/testy/atrapa_facebook.html). */
window.PANEL_SEL = {
  // strona tworzenia posta jest gotowa, gdy widać pole opisu albo pole pliku (albo przycisk dodawania: mediaText)
  ready: ['[contenteditable="true"][role="textbox"]', 'input[type="file"]', 'textarea'],
  // formularz logowania
  loginForm: ['input[name="pass"]', 'form[action*="login"] input[type="password"]', '#loginform input[type="password"]'],
  // okno (gdy edytor jest w oknie, np. na www.facebook.com)
  dialog: '[role="dialog"]',
  // pole pliku: zdjęcia i film (wybierane według typu plików)
  fileInput: ['input[type="file"][accept*="video"]', 'input[type="file"][accept*="image"]', 'input[type="file"]'],
  // przycisk dodawania zdjęć albo filmu i pozycja „z komputera” w jego menu
  mediaButton: ['[aria-label="Add photo/video"]', '[aria-label="Dodaj zdjęcie/film"]', '[aria-label="Add video"]',
                '[aria-label="Dodaj film"]', '[aria-label="Add photo"]', '[aria-label="Dodaj zdjęcie"]'],
  mediaText: ['Add photo/video', 'Dodaj zdjęcie/film', 'Add photos/videos', 'Dodaj zdjęcia/filmy', 'Add video',
              'Dodaj film', 'Add photo', 'Dodaj zdjęcie'],
  uploadText: ['Upload from desktop', 'Prześlij z komputera', 'Upload from computer', 'Prześlij z pulpitu'],
  menuItem: '[role="menuitem"], [role="button"], button',
  // strefa upuszczania plików (gdy nie ma pola pliku)
  dropZone: ['[aria-label*="drag" i]', '[aria-label*="przeciągnij" i]'],
  // pole opisu
  caption: ['[role="dialog"] [contenteditable="true"][role="textbox"]', '[contenteditable="true"][role="textbox"][aria-label]',
            '[contenteditable="true"][role="textbox"]', '[contenteditable="true"]', 'textarea'],
  // przyciski kroków (rolka: „Dalej”)
  button: '[role="button"], button',
  nextText: ['Next', 'Dalej'],
  // przycisk publikacji: rozszerzenie go NIE klika (safeClick odmawia), tylko wyróżnia
  publishText: ['Publish', 'Opublikuj', 'Share', 'Udostępnij', 'Post', 'Opublikuj teraz', 'Share now', 'Schedule', 'Zaplanuj']
};
