/* Selektory i napisy strony instagram.com: jedyne miejsce do poprawek, gdy Instagram zmieni wygląd.
   Każda lista to warianty sprawdzane po kolei (pierwszy pasujący wygrywa); napisy porównywane bez wielkości liter,
   po polsku i po angielsku. Opis w README.md. */
window.IS_SEL = {
  // przycisk tworzenia posta w menu bocznym (ikona z etykietą); klikany jest najbliższy link albo przycisk
  create: ['svg[aria-label="New post"]', 'svg[aria-label="Nowy post"]', 'svg[aria-label="Nowa publikacja"]',
           'svg[aria-label="Create"]', 'svg[aria-label="Utwórz"]', '[aria-label="New post"]', '[aria-label="Nowy post"]'],
  // podmenu po „Utwórz” (gdy jest): pozycja z samym napisem
  postMenuText: ['Post', 'Publikacja', 'Posty'],
  menuItem: 'a, [role="link"], [role="button"], [role="menuitem"], button',
  // okno tworzenia posta
  dialog: '[role="dialog"]',
  fileInput: ['[role="dialog"] input[type="file"]', 'form[enctype="multipart/form-data"] input[type="file"]',
              'input[type="file"][accept*="image"]'],
  // przyciski kroków (szukane w oknie po napisie)
  button: '[role="button"], button',
  nextText: ['Next', 'Dalej'],
  okText: ['OK'],                                   // komunikat „filmy są publikowane jako rolki”
  // pole opisu (edytor contenteditable albo textarea)
  caption: ['[role="dialog"] div[contenteditable="true"][aria-label]', '[role="dialog"] [contenteditable="true"]',
            '[role="dialog"] textarea'],
  // przycisk publikacji: rozszerzenie go NIE klika, tylko wyróżnia
  shareText: ['Share', 'Udostępnij', 'Opublikuj', 'Publish'],
  // zalogowany profil: najpierw zapytanie strony (z nagłówkiem aplikacji webowej), potem obrazek profilu w menu
  currentUser: '/api/v1/accounts/current_user/?edit=true',
  appId: '936619743392459',
  profileImg: 'img[alt]',
  profileAlt: [/^(.+?)'s profile picture$/i, /^Zdjęcie profilowe (?:użytkownika )?(.+)$/i],
  loginForm: 'input[name="username"]',
  // przełączanie kont: menu „Więcej” i pozycja w nim (wybór konta robi właściciel)
  moreMenu: ['svg[aria-label="Settings"]', 'svg[aria-label="Ustawienia"]', 'svg[aria-label="More"]', 'svg[aria-label="Więcej"]'],
  switchText: ['Switch accounts', 'Przełącz konta', 'Przełącz konto']
};
