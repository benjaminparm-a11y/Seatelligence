// Time slot picker for Seatelligence booking modal
document.addEventListener("DOMContentLoaded", () => {
  const dateInput = document.getElementById("cb_date");
  const guestsInput = document.getElementById("cb_people");
  const slotsContainer = document.getElementById("time-slots");
  const hiddenTimeInput = document.getElementById("cb_start_time");

  if (!dateInput || !guestsInput || !slotsContainer || !hiddenTimeInput) return;

  let selectedButton = null;

  async function loadSlots() {
    const dateVal = dateInput.value;
    const guestsVal = guestsInput.value;

    // Clear previous selection
    hiddenTimeInput.value = "";
    if (selectedButton) {
      selectedButton.classList.remove("is-selected");
      selectedButton = null;
    }

    if (!dateVal || !guestsVal) {
      slotsContainer.innerHTML = "<div class='st-time-help'>Select a date and number of people first.</div>";
      return;
    }

    slotsContainer.innerHTML = "<div class='st-time-help'>Loading available times…</div>";

    try {
      const resp = await fetch(`/api/available-times?date=${encodeURIComponent(dateVal)}&guests=${encodeURIComponent(guestsVal)}`);
      
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`);
      }
      
      const data = await resp.json();

      slotsContainer.innerHTML = "";

      data.forEach(slot => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = slot.time;
        btn.className = "st-time-slot";

        if (!slot.available) {
          btn.classList.add("is-disabled");
          btn.disabled = true;
        } else {
          btn.addEventListener("click", () => {
            if (selectedButton) {
              selectedButton.classList.remove("is-selected");
            }
            selectedButton = btn;
            btn.classList.add("is-selected");
            hiddenTimeInput.value = slot.time;
          });
        }

        slotsContainer.appendChild(btn);
      });

    } catch (err) {
      console.error("Error loading time slots:", err);
      slotsContainer.innerHTML = "<div class='st-time-help'>Couldn't load times. Please try again.</div>";
    }
  }

  dateInput.addEventListener("change", loadSlots);
  guestsInput.addEventListener("change", loadSlots);
});
