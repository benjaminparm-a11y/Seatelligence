(function(){
  const modal = document.getElementById('createBookingModal');
  if (!modal) return;

  const openButtons = [
    document.getElementById('openCreateBookingModalHeader')
  ].filter(Boolean);

  const closeButton = document.getElementById('closeCreateBookingModal');
  const cancelButton = document.getElementById('cancelCreateBooking');
  const backdrop = modal.querySelector('.st-modal-backdrop');
  const form = document.getElementById('createBookingForm');

  function openCreateBookingModal(){
    modal.classList.remove('st-modal-hidden');
    modal.classList.add('st-modal-open');
    const firstInput = modal.querySelector('input, textarea, select');
    if (firstInput) firstInput.focus();
  }

  function closeCreateBookingModal(){
    modal.classList.remove('st-modal-open');
    modal.classList.add('st-modal-hidden');
    if (form) form.reset();
    
    // Clear time slots
    const slotsContainer = document.getElementById('time-slots');
    if (slotsContainer) {
      slotsContainer.innerHTML = "<div class='st-time-help'>Select a date and number of people first.</div>";
    }
  }

  // When opening the modal, prefill date/time from sidebar filters if available
  openButtons.forEach(btn => {
    btn.addEventListener("click", function (e) {
      e.preventDefault();

      const sidebarDate = document.getElementById("date-input")?.value;
      const sidebarTime = document.getElementById("time-filter")?.value;

      const cbDate = document.getElementById("cb_date");
      const cbStart = document.getElementById("cb_start_time");

      if (cbDate && sidebarDate) {
        cbDate.value = sidebarDate;
        // Trigger change event to load time slots
        cbDate.dispatchEvent(new Event('change'));
      }
      
      // Note: We no longer prefill start time directly - user must select from slots

      openCreateBookingModal();
    });
  });

  [closeButton, cancelButton, backdrop].forEach(el => {
    if (!el) return;
    el.addEventListener('click', function(e){
      e.preventDefault();
      closeCreateBookingModal();
    });
  });

  document.addEventListener('keydown', function(e){
    if (e.key === 'Escape' && modal.classList.contains('st-modal-open')){
      closeCreateBookingModal();
    }
  });

  const saveButton = document.getElementById("saveBookingButton");

  async function createBookingFromModal() {
    const firstName = document.getElementById("cb_first_name")?.value?.trim() || "";
    const lastName = document.getElementById("cb_last_name")?.value?.trim() || "";
    const date = document.getElementById("cb_date")?.value || "";
    const startTime = document.getElementById("cb_start_time")?.value || "";
    const people = document.getElementById("cb_people")?.value || "";
    const notes = document.getElementById("cb_notes")?.value || "";

    if (!date || !firstName || !lastName || !people || !startTime) {
      if (typeof window.showStatus === "function") {
        window.showStatus("Please fill out all required fields", "error");
      } else {
        alert("Please fill out all required fields");
      }
      return;
    }

    // Title-case names
    const firstNameTitle = firstName.charAt(0).toUpperCase() + firstName.slice(1).toLowerCase();
    const lastNameTitle = lastName.charAt(0).toUpperCase() + lastName.slice(1).toLowerCase();
    const fullName = `${firstNameTitle} ${lastNameTitle}`;

    try {
      const res = await fetch("/bookings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          date: date,
          name: fullName,
          party_size: Number(people),
          start_time: startTime,
          // end_time omitted – backend will compute +2.5h
          // table_id omitted – backend auto-assigns
          notes: notes || null
        })
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        const msg = data.error || res.statusText || "Failed to create booking";
        if (typeof window.showStatus === "function") {
          window.showStatus("Error: " + msg, "error");
        } else {
          alert("Error: " + msg);
        }
        return;
      }

      // Success: close modal, show message, refresh bookings
      closeCreateBookingModal();

      if (typeof window.showStatus === "function") {
        window.showStatus(
          `Booking created for ${fullName}, party of ${people}`,
          "success"
        );
      }

      if (typeof window.loadBookings === "function") {
        window.loadBookings();
      }
    } catch (err) {
      console.error("Create booking error:", err);
      if (typeof window.showStatus === "function") {
        window.showStatus("Failed to create booking: " + err.message, "error");
      } else {
        alert("Failed to create booking: " + err.message);
      }
    }
  }

  if (saveButton) {
    saveButton.addEventListener("click", function (e) {
      e.preventDefault();
      createBookingFromModal();
    });
  }
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
