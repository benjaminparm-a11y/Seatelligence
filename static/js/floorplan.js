// static/js/floorplan.js

(function () {
  const GRID = 10;

  function qs(sel, root = document) {
    return root.querySelector(sel);
  }
  function qsa(sel, root = document) {
    return Array.from(root.querySelectorAll(sel));
  }

  function initFloorplan() {
    const canvas = qs('#fpCanvas');
    const overlay = qs('#fpOverlay');
    const serviceBtn = qs('#floorplanModeService');
    const editBtn = qs('#floorplanModeEdit');

    if (!canvas || !overlay) return;

    // Mode handling
    let mode = 'service';
    function setMode(newMode) {
      mode = newMode;
      canvas.classList.toggle('edit-mode', newMode === 'edit');
      canvas.classList.toggle('service-mode', newMode === 'service');
      if (serviceBtn && editBtn) {
        serviceBtn.classList.toggle('is-active', newMode === 'service');
        editBtn.classList.toggle('is-active', newMode === 'edit');
      }
    }
    serviceBtn && serviceBtn.addEventListener('click', () => setMode('service'));
    editBtn && editBtn.addEventListener('click', () => setMode('edit'));
    setMode('service');

    // Drag/resize state
    let activeTable = null;
    let dragging = false;
    let resizing = false;
    let layoutDirty = false;
    let dragStartX = 0;
    let dragStartY = 0;
    let dragStartLeft = 0;
    let dragStartTop = 0;
    let resizeStartX = 0;
    let resizeStartY = 0;
    let resizeStartW = 0;
    let resizeStartH = 0;

    // Details panel
    const detailsForm = qs('#fpDetailsForm');
    const detailsEmpty = qs('#fpDetailsEmpty');
    const idInput = qs('#fp-detail-id');
    const nameInput = qs('#fp-detail-name');
    const capInput = qs('#fp-detail-capacity');
    const sectionInput = qs('#fp-detail-section');
    const shapeRound = qs('#fp-detail-shape-round');
    const shapeSquare = qs('#fp-detail-shape-square');
    const applyBtn = qs('#fp-detail-apply');
    const cancelBtn = qs('#fp-detail-cancel');

    let selectedTable = null;

    function showDetails(el) {
      selectedTable = el;
      if (!detailsForm || !idInput) return;
      const isLandmark = el.dataset.isLandmark === 'true';

      idInput.value = el.dataset.id || '';
      if (nameInput) nameInput.value = el.dataset.name || '';
      if (capInput) {
        capInput.value = el.dataset.capacity || '0';
        capInput.disabled = isLandmark; // landmarks stay capacity 0
      }
      if (sectionInput) sectionInput.value = el.dataset.section || 'Main';

      const shape = el.dataset.shape || 'square';
      if (shapeRound && shapeSquare) {
        shapeRound.checked = shape === 'round';
        shapeSquare.checked = shape !== 'round';
      }

      detailsEmpty && (detailsEmpty.hidden = true);
      detailsForm && (detailsForm.hidden = false);
    }

    function clearDetails() {
      selectedTable = null;
      detailsForm && (detailsForm.hidden = true);
      detailsEmpty && (detailsEmpty.hidden = false);
    }

    // Attach handlers to each table
    qsa('.fp-table', overlay).forEach((el) => {
      // click → select (edit only)
      el.addEventListener('click', (e) => {
        if (mode !== 'edit') return;
        if (e.target.classList.contains('fp-table-resize')) return;
        e.stopPropagation();
        showDetails(el);
      });

      // drag
      el.addEventListener('mousedown', (e) => {
        if (mode !== 'edit') return;
        if (e.target.classList.contains('fp-table-resize')) return;

        activeTable = el;
        dragging = true;
        dragStartX = e.clientX;
        dragStartY = e.clientY;
        dragStartLeft = parseFloat(el.style.left) || 0;
        dragStartTop = parseFloat(el.style.top) || 0;
        e.preventDefault();
      });

      // resize
      const h = el.querySelector('.fp-table-resize');
      if (h) {
        h.addEventListener('mousedown', (e) => {
          if (mode !== 'edit') return;
          activeTable = el;
          resizing = true;
          resizeStartX = e.clientX;
          resizeStartY = e.clientY;
          resizeStartW = el.offsetWidth;
          resizeStartH = el.offsetHeight;
          e.preventDefault();
          e.stopPropagation();
        });
      }
    });

    document.addEventListener('mousemove', (e) => {
      if (mode !== 'edit' || !activeTable) return;

      if (dragging) {
        const dx = e.clientX - dragStartX;
        const dy = e.clientY - dragStartY;
        let left = dragStartLeft + dx;
        let top = dragStartTop + dy;

        const maxLeft = canvas.clientWidth - activeTable.offsetWidth;
        const maxTop = canvas.clientHeight - activeTable.offsetHeight;

        left = Math.max(0, Math.min(maxLeft, left));
        top = Math.max(0, Math.min(maxTop, top));

        left = Math.round(left / GRID) * GRID;
        top = Math.round(top / GRID) * GRID;

        activeTable.style.left = left + 'px';
        activeTable.style.top = top + 'px';
        layoutDirty = true;
      } else if (resizing) {
        const dx = e.clientX - resizeStartX;
        const dy = e.clientY - resizeStartY;
        let w = resizeStartW + dx;
        let h = resizeStartH + dy;

        w = Math.max(30, Math.round(w / GRID) * GRID);
        h = Math.max(30, Math.round(h / GRID) * GRID);

        activeTable.style.width = w + 'px';
        activeTable.style.height = h + 'px';
        activeTable.dataset.width = String(w);
        activeTable.dataset.height = String(h);
        layoutDirty = true;
      }
    });

    // Save layout function
    function collectTablesPayload() {
      const result = [];
      qsa('.fp-table', overlay).forEach((el) => {
        result.push({
          id: parseInt(el.dataset.id, 10),
          name: el.dataset.name || '',
          capacity: parseInt(el.dataset.capacity || '0', 10),
          section: el.dataset.section || 'Main',
          shape: el.dataset.shape || 'square',
          bookable: el.dataset.bookable !== 'false',
          is_landmark: el.dataset.isLandmark === 'true',
          x: parseFloat(el.style.left) || 0,
          y: parseFloat(el.style.top) || 0,
          width: parseFloat(el.dataset.width || el.offsetWidth),
          height: parseFloat(el.dataset.height || el.offsetHeight)
        });
      });
      return result;
    }

    function saveLayout() {
      const tables = collectTablesPayload();
      if (!tables || tables.length === 0) return;

      fetch('/api/save_table_layout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tables })
      })
        .then((r) => r.json())
        .then((data) => {
          if (!data || !data.success) {
            console.error('Failed to save layout', data);
          }
        })
        .catch((err) => {
          console.error('Error saving layout', err);
        });
    }

    document.addEventListener('mouseup', () => {
      const wasDraggingOrResizing = dragging || resizing;
      dragging = false;
      resizing = false;
      activeTable = null;

      // Auto-save only if something changed and we're in edit mode
      if (wasDraggingOrResizing && layoutDirty && mode === 'edit') {
        layoutDirty = false;
        saveLayout();
      }
    });

    // Empty space click → clear selection
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        clearDetails();
      }
    });

    // Apply details to selected table
    applyBtn && applyBtn.addEventListener('click', () => {
      if (!selectedTable) return;
      const isLandmark = selectedTable.dataset.isLandmark === 'true';

      const name = nameInput ? nameInput.value : selectedTable.dataset.name;
      let capacity = capInput ? parseInt(capInput.value || '0', 10) : 0;
      if (isLandmark) capacity = 0;

      const section = sectionInput ? sectionInput.value : 'Main';
      let shape = 'square';
      if (shapeRound && shapeRound.checked) shape = 'round';
      if (shapeSquare && shapeSquare.checked) shape = 'square';

      selectedTable.dataset.name = name;
      selectedTable.dataset.capacity = String(capacity);
      selectedTable.dataset.section = section;
      selectedTable.dataset.shape = shape;

      const label = selectedTable.querySelector('.fp-table-label');
      if (label) label.textContent = name;

      selectedTable.classList.toggle('fp-table--round', shape === 'round');
      selectedTable.classList.toggle('fp-table--square', shape !== 'round');
    });

    cancelBtn && cancelBtn.addEventListener('click', () => {
      if (selectedTable) showDetails(selectedTable);
      else clearDetails();
    });
  }

  document.addEventListener('DOMContentLoaded', initFloorplan);
})();
