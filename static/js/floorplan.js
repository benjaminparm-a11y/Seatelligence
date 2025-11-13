(function(){
  window.Seatelligence = window.Seatelligence || {};

  function withDPR(canvas, ctx){
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = Math.max(1, Math.floor(rect.width * dpr));
    canvas.height = Math.max(1, Math.floor(rect.height * dpr));
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { width: rect.width, height: rect.height, dpr };
  }

  function normalizeTables(tables, width, height){
    if (!Array.isArray(tables) || tables.length === 0){
      // generate a simple demo grid if no tables provided
      const cols = 5, rows = 3;
      const gw = width / (cols + 1);
      const gh = height / (rows + 1);
      const out = [];
      let n = 1;
      for (let r = 1; r <= rows; r++){
        for (let c = 1; c <= cols; c++){
          out.push({ x: c * gw, y: r * gh, w: 64, h: 64, number: n++, capacity: 4, shape: 'round' });
        }
      }
      return out;
    }
    return tables.map(t => ({
      x: t.x ?? Math.random() * width * 0.8 + width * 0.1,
      y: t.y ?? Math.random() * height * 0.8 + height * 0.1,
      w: t.w ?? t.width ?? 64,
      h: t.h ?? t.height ?? 64,
      number: t.number ?? t.name ?? t.id ?? '?',
      capacity: t.capacity ?? t.seats ?? 4,
      shape: t.shape ?? ((t.w || t.width) && (t.h || t.height) && (t.w !== t.h) ? 'rect' : 'round')
    }));
  }

  function drawBackground(ctx, w, h){
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#f6f8fa';
    ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = '#e5eaef';
    ctx.lineWidth = 1;
    for (let x = 0; x <= w; x += 40){
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
    }
    for (let y = 0; y <= h; y += 40){
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
    }
  }

  function drawTable(ctx, t){
    ctx.save();
    ctx.fillStyle = '#0d6efd22';
    ctx.strokeStyle = '#0d6efd';
    ctx.lineWidth = 2;
    if (t.shape === 'rect'){
      const x = t.x - t.w/2, y = t.y - t.h/2;
      if (typeof ctx.roundRect === 'function'){
        ctx.beginPath();
        ctx.roundRect(x, y, t.w, t.h, 8);
        ctx.fill(); ctx.stroke();
      } else {
        ctx.beginPath(); ctx.rect(x, y, t.w, t.h); ctx.fill(); ctx.stroke();
      }
    } else {
      const r = Math.min(t.w, t.h) / 2;
      ctx.beginPath(); ctx.arc(t.x, t.y, r, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    }
    // label
    ctx.fillStyle = '#0d1b2a';
    ctx.font = '12px -apple-system, Segoe UI, Roboto, system-ui, sans-serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(String(t.number), t.x, t.y);
    ctx.restore();
  }

  function redraw(canvas, ctx, items){
    const { width, height } = canvas.getBoundingClientRect();
    drawBackground(ctx, width, height);
    items.forEach(t => drawTable(ctx, t));
  }

  window.Seatelligence.initFloorplan = function(canvas, opts){
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const metrics = withDPR(canvas, ctx);
    let items = normalizeTables((opts && opts.tables) || [], metrics.width, metrics.height);

    redraw(canvas, ctx, items);

    // handle resize
    let resizeTimeout = null;
    function onResize(){
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(() => {
        const m = withDPR(canvas, ctx);
        items = normalizeTables(items, m.width, m.height);
        redraw(canvas, ctx, items);
      }, 100);
    }
    window.addEventListener('resize', onResize);

    // expose simple controls
  const resetBtn = document.getElementById('resetLayoutBtn');
  const autoBtn = document.getElementById('autoAssignBtn');
  const saveBtn = document.getElementById('saveLayoutBtn');
    resetBtn && resetBtn.addEventListener('click', () => {
      const m = withDPR(canvas, ctx);
      items = normalizeTables([], m.width, m.height);
      redraw(canvas, ctx, items);
    });
    autoBtn && autoBtn.addEventListener('click', () => {
      // placeholder for auto-assign action
      // For now, just flash a quick outline
      const { width, height } = canvas.getBoundingClientRect();
      ctx.save();
      ctx.strokeStyle = '#198754';
      ctx.lineWidth = 4;
      ctx.strokeRect(2, 2, width - 4, height - 4);
      setTimeout(() => { redraw(canvas, ctx, items); ctx.restore(); }, 250);
    });
    saveBtn && saveBtn.addEventListener('click', () => {
      // Placeholder save action; wire to backend later
      const { width, height } = canvas.getBoundingClientRect();
      ctx.save();
      ctx.strokeStyle = '#0d6efd';
      ctx.setLineDash([8, 6]);
      ctx.lineWidth = 3;
      ctx.strokeRect(6, 6, width - 12, height - 12);
      setTimeout(() => { redraw(canvas, ctx, items); ctx.restore(); }, 300);
    });

    return {
      destroy(){
        window.removeEventListener('resize', onResize);
      }
    };
  };
})();
