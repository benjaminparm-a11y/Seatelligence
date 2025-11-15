/**
 * Calendar Drag & Drop
 * Enables dragging bookings between tables in the calendar view
 */

document.addEventListener("DOMContentLoaded", () => {
  let draggedBookingIndex = null;
  let draggedFromTableId = null;
  let draggedDate = null;

  // 1) Make booking pills draggable
  document.querySelectorAll(".calendar-booking-pill").forEach(pill => {
    pill.addEventListener("dragstart", (e) => {
      draggedBookingIndex = pill.getAttribute("data-booking-index");
      draggedFromTableId = pill.getAttribute("data-table-id");
      draggedDate = pill.getAttribute("data-date");

      e.dataTransfer.effectAllowed = "move";
      pill.classList.add("calendar-dragging");
    });

    pill.addEventListener("dragend", () => {
      pill.classList.remove("calendar-dragging");
      draggedBookingIndex = null;
      draggedFromTableId = null;
      draggedDate = null;
    });
  });

  // 2) Allow dropping on both booking cells and empty cells
  const allCells = document.querySelectorAll(".calendar-booking-cell, .calendar-empty-cell");

  allCells.forEach(cell => {
    cell.addEventListener("dragover", (e) => {
      if (!draggedBookingIndex) return;
      e.preventDefault(); // allow drop
      e.dataTransfer.dropEffect = "move";
      cell.classList.add("calendar-drop-target");
    });

    cell.addEventListener("dragleave", () => {
      cell.classList.remove("calendar-drop-target");
    });

    cell.addEventListener("drop", async (e) => {
      e.preventDefault();
      cell.classList.remove("calendar-drop-target");
      if (!draggedBookingIndex) return;

      const targetTableId = cell.getAttribute("data-table-id");
      const targetDate = cell.getAttribute("data-date");

      // Check if target cell contains another booking pill
      const targetPill = cell.querySelector(".calendar-booking-pill");

      try {
        if (targetPill) {
          // --- Swap tables with the other booking ---
          const targetBookingIndex = targetPill.getAttribute("data-booking-index");
          
          if (targetBookingIndex === draggedBookingIndex) {
            return; // dropped on itself
          }

          const resp = await fetch("/bookings/swap_tables", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              date: draggedDate,
              booking_index_1: parseInt(draggedBookingIndex),
              booking_index_2: parseInt(targetBookingIndex),
            }),
          });

          const data = await resp.json();
          if (resp.ok && data.status === "ok") {
            window.location.reload();
          } else {
            alert(data.error || "Could not swap tables.");
          }
        } else {
          // --- Move booking to this (empty) table cell ---
          const resp = await fetch("/bookings/move_to_table", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              date: draggedDate,
              booking_index: parseInt(draggedBookingIndex),
              new_table_id: parseInt(targetTableId) || targetTableId,
            }),
          });

          const data = await resp.json();
          if (resp.ok && data.status === "ok") {
            window.location.reload();
          } else {
            alert(data.error || "Could not move booking.");
          }
        }
      } catch (err) {
        console.error(err);
        alert("Error updating booking, please try again.");
      }
    });
  });
});
