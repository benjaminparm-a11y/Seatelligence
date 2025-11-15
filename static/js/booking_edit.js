/**
 * Booking Edit Modal
 * Handles opening and populating the edit booking modal from both the bookings table and calendar view.
 */

document.addEventListener("DOMContentLoaded", () => {
  const overlay = document.getElementById("editBookingOverlay");
  const modal = document.getElementById("editBookingModal");
  const form = document.getElementById("editBookingForm");

  if (!overlay || !modal || !form) {
    console.warn("Edit booking modal elements not found");
    return;
  }

  // Form field references
  const bookingIdInput = document.getElementById("edit-booking-id");
  const nameInput = document.getElementById("edit-name");
  const partySizeInput = document.getElementById("edit-party-size");
  const dateInput = document.getElementById("edit-date");
  const startTimeInput = document.getElementById("edit-start-time");
  const endTimeInput = document.getElementById("edit-end-time");
  const tableCheckboxes = document.querySelectorAll('.table-checkbox');  // Changed to checkboxes
  const notesInput = document.getElementById("edit-notes");

  // Button references
  const closeBtn = document.getElementById("closeEditBookingModal");
  const cancelBtn = document.getElementById("cancelEditBooking");

  /**
   * Open the modal and populate with booking data
   * @param {Object} data - Booking data with keys: bookingIndex, name, partySize, date, startTime, endTime, tables, notes
   */
  function openModalWithData(data) {
    // Populate hidden fields
    bookingIdInput.value = data.bookingIndex || "";

    // Populate form fields
    nameInput.value = data.name || "";
    partySizeInput.value = data.partySize || "";
    dateInput.value = data.date || "";
    startTimeInput.value = data.startTime || "";
    endTimeInput.value = data.endTime || "";
    notesInput.value = data.notes || "";

    // Set table selections (checkboxes)
    const tablesToSelect = data.tables || (data.tableId ? [data.tableId] : []);
    tableCheckboxes.forEach(cb => {
      const value = parseInt(cb.value, 10);
      cb.checked = Array.isArray(tablesToSelect) && tablesToSelect.includes(value);
    });

    // Build form action URL: /bookings/{date_as_number}/{index}/edit
    // Convert date "2025-11-13" to "20251113"
    const dateNumber = (data.date || "").replace(/-/g, "");
    form.action = `/bookings/${dateNumber}/${data.bookingIndex}/edit`;

    // Show overlay/modal
    overlay.classList.add("is-visible");
    overlay.style.display = "flex";
    overlay.setAttribute("aria-hidden", "false");

    // Focus on name field
    setTimeout(() => nameInput.focus(), 100);
  }

  /**
   * Close the modal
   */
  function closeModal() {
    overlay.classList.remove("is-visible");
    overlay.style.display = "none";
    overlay.setAttribute("aria-hidden", "true");
  }

  function openEditModal() {
    overlay.classList.add("is-visible");
    setTimeout(() => {
      const nameInput = document.getElementById("edit-name");
      if (nameInput) nameInput.focus();
    }, 100);
  }

  function closeEditModal() {
    overlay.classList.remove("is-visible");
  }

  // Event listeners for close buttons
  if (closeBtn) {
    closeBtn.addEventListener("click", closeEditModal);
  }

  if (cancelBtn) {
    cancelBtn.addEventListener("click", closeEditModal);
  }

  // Close when clicking the overlay itself (not inside modal)
  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) {
      closeEditModal();
    }
  });

  // Close on Escape key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && overlay.classList.contains("is-visible")) {
      closeEditModal();
    }
  });

  /**
   * Attach event listeners to Edit buttons in bookings table
   */
  function attachBookingsTableListeners() {
    const buttons = document.querySelectorAll(".booking-edit-btn");
    console.log("Found", buttons.length, "edit buttons");
    
    buttons.forEach(btn => {
      btn.addEventListener("click", (e) => {
        console.log("Edit button clicked!");
        e.stopPropagation(); // Prevent any parent handlers

        // Get table data - support both single table_id and multiple tables
        const tableIdAttr = btn.getAttribute("data-table-id");
        const tablesAttr = btn.getAttribute("data-tables");
        
        let tables = [];
        if (tablesAttr) {
          // Parse tables array (could be JSON or comma-separated)
          try {
            tables = JSON.parse(tablesAttr);
          } catch (e) {
            tables = tablesAttr.split(",").map(t => parseInt(t.trim(), 10)).filter(t => !isNaN(t));
          }
        } else if (tableIdAttr) {
          // Fall back to single table_id
          tables = [parseInt(tableIdAttr, 10)];
        }

        openModalWithData({
          bookingIndex: btn.getAttribute("data-booking-index"),
          name: btn.getAttribute("data-name"),
          partySize: btn.getAttribute("data-party-size"),
          date: btn.getAttribute("data-date"),
          startTime: btn.getAttribute("data-start-time"),
          endTime: btn.getAttribute("data-end-time"),
          tables: tables,
          tableId: tableIdAttr ? parseInt(tableIdAttr, 10) : null,  // For backward compatibility
          notes: btn.getAttribute("data-notes") || "",
        });
      });
    });
  }

  /**
   * Attach event listeners to Delete buttons
   */
  function attachDeleteListeners() {
    document.querySelectorAll(".booking-delete-btn").forEach(btn => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const name = btn.getAttribute("data-booking-name");
        const date = btn.getAttribute("data-booking-date");
        const index = btn.getAttribute("data-booking-index");
        
        if (confirm(`Delete booking for ${name}?`)) {
          try {
            await fetch(`/bookings?date=${encodeURIComponent(date)}&index=${index}`, {
              method: 'DELETE'
            });
            location.reload();
          } catch (err) {
            alert("Failed to delete booking");
          }
        }
      });
    });
  }

  /**
   * Attach event listeners to Notes buttons
   */
  function attachNotesListeners() {
    document.querySelectorAll(".booking-notes-btn").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const notes = btn.getAttribute("data-notes") || '';
        if (notes.trim()) {
          alert(notes);
        }
      });
    });
  }

  /**
   * Attach event listeners to Edit buttons in calendar view
   */
  function attachCalendarListeners() {
    document.querySelectorAll(".calendar-edit-btn").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation(); // Prevent drag/drop or parent handlers
        e.preventDefault(); // Prevent any default button behavior

        openModalWithData({
          bookingIndex: btn.getAttribute("data-booking-index"),
          name: btn.getAttribute("data-name"),
          partySize: btn.getAttribute("data-party-size"),
          date: btn.getAttribute("data-date"),
          startTime: btn.getAttribute("data-start-time"),
          endTime: btn.getAttribute("data-end-time"),
          tableId: btn.getAttribute("data-table-id"),
          notes: btn.getAttribute("data-notes") || "",
        });
      });
    });
  }

  // Initialize listeners
  attachBookingsTableListeners();
  attachDeleteListeners();
  attachNotesListeners();
  attachCalendarListeners();

  // Re-attach listeners when bookings table is dynamically updated
  // (in case the bookings table is re-rendered via JavaScript)
  const observer = new MutationObserver(() => {
    attachBookingsTableListeners();
    attachDeleteListeners();
    attachNotesListeners();
  });

  const bookingsBody = document.getElementById("bookings-body");
  if (bookingsBody) {
    observer.observe(bookingsBody, { childList: true, subtree: true });
  }

  // Handle form submit via fetch to ensure POST and handle redirect/reload
  form.addEventListener("submit", function(event) {
    event.preventDefault();
    const formData = new FormData(form);
    const actionUrl = form.action;
    fetch(actionUrl, {
      method: "POST",
      body: formData,
    }).then(response => {
      if (response.redirected) {
        window.location.href = response.url;
      } else {
        closeEditModal();
        window.location.reload();
      }
    }).catch(() => {
      alert("Failed to update booking");
    });
  });

  // Expose openEditModal for use by edit buttons
  window.openEditModal = openEditModal;
});
