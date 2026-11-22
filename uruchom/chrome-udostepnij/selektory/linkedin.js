/* Selektory i napisy linkedin.com (okno tworzenia posta): jedyne miejsce do poprawek, gdy LinkedIn zmieni wygląd.
   Listy to warianty sprawdzane po kolei (pierwszy pasujący wygrywa); napisy bez wielkości liter, po polsku i angielsku.
   Niesprawdzone na prawdziwej stronie: tylko na atrapie (dashboard/testy/atrapa_linkedin.html). */
window.PANEL_SEL = {
  // przycisk „Zacznij publikację” na stronie głównej (gdy okno nie otworzyło się samo z ?shareActive=true)
  start: ['button.share-box-feed-entry__trigger', '.share-box-feed-entry__trigger', '[data-control-name="share.sharebox_focus"]'],
  startText: ['Start a post', 'Zacznij publikację', 'Rozpocznij post', 'Utwórz post', 'Napisz post'],
  // formularz logowania
  loginForm: ['input[name="session_password"]', 'input#password', 'input[name="session_key"]'],
  dialog: '[role="dialog"]',
  // pole opisu w oknie tworzenia posta
  caption: ['[role="dialog"] .ql-editor[contenteditable="true"]', '[role="dialog"] [role="textbox"][contenteditable="true"]',
            '[role="dialog"] [contenteditable="true"]'],
  // pole pliku (edytor multimediów) i przycisk „Dodaj multimedia”
  fileInput: ['input#media-editor-file-selector__file-input', '[role="dialog"] input[type="file"]',
              'input[type="file"][accept*="image"]', 'input[type="file"][accept*="video"]', 'input[type="file"]'],
  mediaButton: ['[role="dialog"] button[aria-label="Add media"]', '[role="dialog"] button[aria-label="Dodaj multimedia"]',
                '[role="dialog"] button[aria-label="Add a photo"]', '[role="dialog"] button[aria-label="Dodaj zdjęcie"]',
                '[role="dialog"] button[aria-label="Add a video"]', '[role="dialog"] button[aria-label="Dodaj film"]'],
  uploadText: ['Upload from computer', 'Prześlij z komputera'],
  menuItem: '[role="menuitem"], [role="button"], button',
  dropZone: ['[role="dialog"] .ql-editor[contenteditable="true"]'],
  // kroki edytora multimediów: „Dalej” albo „Gotowe” wraca do okna posta
  button: '[role="button"], button',
  nextText: ['Next', 'Dalej', 'Done', 'Gotowe'],
  // przycisk publikacji: rozszerzenie go NIE klika (safeClick odmawia), tylko wyróżnia
  publishText: ['Post', 'Opublikuj', 'Publikuj', 'Schedule', 'Zaplanuj']
};
