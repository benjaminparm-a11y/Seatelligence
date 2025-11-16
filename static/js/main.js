
(function(){
  // Create booking modal using overlay pattern (matches Edit modal behavior)
  const createOverlay = document.getElementById('createBookingOverlay');
  const createModalCloseBtn = document.getElementById('createModalCloseBtn');
  const newBookingButton = document.getElementById('newBookingButton');
  const cancelButton = document.getElementById('createCancelButton');
  const form = document.getElementById('createBookingForm');

  if (!createOverlay || !form) return;

  function openCreateModal() {
    createOverlay.classList.add('is-visible');
    const firstInput = createOverlay.querySelector('input, textarea, select');
    if (firstInput) firstInput.focus();
  }

  function closeCreateModal() {
    createOverlay.classList.remove('is-visible');
    if (form) form.reset();

    // Reset time slots helper
    const slotsContainer = document.getElementById('time-slots');
    if (slotsContainer) {
      slotsContainer.innerHTML = "<div class='st-time-help'>Select a date and number of people first.</div>";
    }
  }

  // Open button handler
  if (newBookingButton) {
    newBookingButton.addEventListener('click', (event) => {
      event.preventDefault();
      // Prefill date from sidebar if available and trigger slot load
      const sidebarDate = document.getElementById('date-input')?.value;
      const cbDate = document.getElementById('cb_date');
      if (cbDate && sidebarDate) {
        cbDate.value = sidebarDate;
        cbDate.dispatchEvent(new Event('change'));
      }
      openCreateModal();
    });
  }

  // Close buttons
  if (createModalCloseBtn) {
    createModalCloseBtn.addEventListener('click', () => closeCreateModal());
  }
  if (cancelButton) {
    cancelButton.addEventListener('click', (e) => { e.preventDefault(); closeCreateModal(); });
  }

  // Only close when clicking the dark background
  createOverlay.addEventListener('click', (event) => {
    if (event.target === createOverlay) {
      closeCreateModal();
    }
  });

  // Close on Escape when visible
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && createOverlay.classList.contains('is-visible')) {
      closeCreateModal();
    }
  });
})();

// ============================================================
// THEME TOGGLE (Light/Dark)
// Always runs, independent of modal presence
// ============================================================
(function(){
  const STORAGE_KEY = 'st-theme'; // 'light' | 'dark'
  const toggle = document.getElementById('themeToggle');

  function applyTheme(theme) {
    if (theme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
    if (toggle) toggle.checked = theme === 'dark';
  }

  function getInitialTheme() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved === 'light' || saved === 'dark') return saved;
    } catch (e) { /* ignore */ }
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
    return 'light';
  }

  const initial = getInitialTheme();
  applyTheme(initial);

  if (toggle) {
    toggle.addEventListener('change', function(e){
      const next = e.target.checked ? 'dark' : 'light';
      try { localStorage.setItem(STORAGE_KEY, next); } catch (e) { /* ignore */ }
      applyTheme(next);
    });
  }

  // Respond to system changes only if user hasn't explicitly chosen
  const mql = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)');
  if (mql) {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (!saved) {
        mql.addEventListener('change', (e) => applyTheme(e.matches ? 'dark' : 'light'));
      }
    } catch (e) { /* ignore */ }
  }
})();
