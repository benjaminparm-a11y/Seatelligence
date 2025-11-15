/**
 * Booking Edit Modal
 * Handles opening and populating the edit booking modal from both the bookings table and calendar view.
 */

document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("editBookingModal");
  const backdrop = document.getElementById("editBookingModalBackdrop");
  const form = document.getElementById("editBookingForm");

  if (!modal || !backdrop || !form) {
    console.warn("Edit booking modal elements not found");
    return;
  }

  // Form field references
  const bookingIndexInput = document.getElementById("edit-booking-index");
  const originalDateInput = document.getElementById("edit-original-date");
  const nameInput = document.getElementById("edit-name");
  const partySizeInput = document.getElementById("edit-party-size");
  const dateInput = document.getElementById("edit-date");
  const startTimeInput = document.getElementById("edit-start-time");
  const endTimeInput = document.getElementById("edit-end-time");
  const tableSelect = document.getElementById("edit-table-id");
  const notesInput = document.getElementById("edit-notes");

  // Button references
  const closeBtn = document.getElementById("closeEditBookingModal");
  const cancelBtn = document.getElementById("cancelEditBooking");

  /**
   * Open the modal and populate with booking data
   * @param {Object} data - Booking data with keys: bookingIndex, name, partySize, date, startTime, endTime, tableId, notes
   */
  function openModalWithData(data) {
    // Populate hidden fields
    bookingIndexInput.value = data.bookingIndex || "";
    originalDateInput.value = data.date || "";

    // Populate form fields
    nameInput.value = data.name || "";
    partySizeInput.value = data.partySize || "";
    dateInput.value = data.date || "";
    startTimeInput.value = data.startTime || "";
    endTimeInput.value = data.endTime || "";
    notesInput.value = data.notes || "";

    // Set table selection
    if (data.tableId && tableSelect) {
      tableSelect.value = data.tableId;
    }

    // Build form action URL: /bookings/{date_as_number}/{index}/edit
    // Convert date "2025-11-13" to "20251113"
    const dateNumber = (data.date || "").replace(/-/g, "");
    form.action = `/bookings/${dateNumber}/${data.bookingIndex}/edit`;

    // Show modal
    modal.classList.remove("st-modal-hidden");
    modal.style.display = "flex";
    modal.setAttribute("aria-hidden", "false");
    backdrop.style.display = "block";
    document.body.classList.add("st-modal-open");

    // Focus on name field
    nameInput.focus();
  }

  /**
   * Close the modal
   */
  function closeModal() {
    modal.classList.add("st-modal-hidden");
    modal.style.display = "none";
    modal.setAttribute("aria-hidden", "true");
    backdrop.style.display = "none";
    document.body.classList.remove("st-modal-open");
  }

  // Event listeners for close buttons
  if (closeBtn) {
    closeBtn.addEventListener("click", closeModal);
  }

  if (cancelBtn) {
    cancelBtn.addEventListener("click", closeModal);
  }

  // Close on backdrop click
  if (backdrop) {
    backdrop.addEventListener("click", closeModal);
  }

  // Close on Escape key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !modal.classList.contains("st-modal-hidden")) {
      closeModal();
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
});
