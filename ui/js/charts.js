/**
 * ui/js/charts.js
 * Offline-first, lightweight Canvas & SVG charting utilities.
 * Designed for high contrast, clean presentation typography, and projector readability.
 */

export class ChartRenderer {
  /**
   * Renders the 50,000-reference timeline comparison chart on a canvas.
   */
  static renderTimeline(canvas, data, options = {}) {
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    const isDark = options.isDark || false;

    // High DPI scaling
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    if (canvas.width !== rect.width * dpr || canvas.height !== rect.height * dpr) {
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
    }
    ctx.resetTransform();
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = rect.height;
    ctx.clearRect(0, 0, w, h);

    const padding = { top: 28, right: 48, bottom: 36, left: 60 };
    const chartW = w - padding.left - padding.right;
    const chartH = h - padding.top - padding.bottom;

    const rawBaseline = data.baselineTimeline || [];
    const rawCurrent = data.currentTimeline || [];
    const rawK = data.kTimeline || null;

    const chunkSize = options.chunkSize || 50000;
    const totalRefs = options.totalRefs || 3780309;
    const fullCount = Math.floor(totalRefs / chunkSize);

    const baseline = rawBaseline.slice(0, fullCount);
    const current = rawCurrent.slice(0, fullCount);
    const kTimeline = rawK ? rawK.slice(0, fullCount) : null;

    if (baseline.length === 0 && current.length === 0) {
      ctx.fillStyle = isDark ? '#9ca3af' : '#6b7280';
      ctx.font = '14px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('No simulation data available yet. Run a simulation to display timeline.', w / 2, h / 2);
      return;
    }

    const nPoints = Math.max(baseline.length, current.length);

    // Compute max fault count
    let maxFault = 100;
    for (let i = 0; i < nPoints; i++) {
      if (baseline[i] !== undefined && baseline[i] > maxFault) maxFault = baseline[i];
      if (current[i] !== undefined && current[i] > maxFault) maxFault = current[i];
    }
    maxFault = Math.ceil(maxFault * 1.1);

    // Styling
    const axisColor = isDark ? '#4b5563' : '#d1d5db';
    const gridColor = isDark ? 'rgba(75, 85, 99, 0.3)' : 'rgba(209, 213, 219, 0.5)';
    const textColor = isDark ? '#9ca3af' : '#64748b';

    // Draw grid & Y-ticks
    ctx.strokeStyle = gridColor;
    ctx.lineWidth = 1;
    ctx.fillStyle = textColor;
    ctx.font = '11px monospace';
    ctx.textAlign = 'right';

    const ySteps = 4;
    for (let i = 0; i <= ySteps; i++) {
      const val = Math.round((maxFault / ySteps) * i);
      const y = padding.top + chartH - (chartH / ySteps) * i;

      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(padding.left + chartW, y);
      ctx.stroke();

      ctx.fillText(val.toLocaleString('en-US'), padding.left - 8, y + 4);
    }

    // Draw X-axis ticks (accesses in millions)
    ctx.textAlign = 'center';
    const xSteps = 5;
    for (let i = 0; i <= xSteps; i++) {
      const x = padding.left + (chartW / xSteps) * i;
      const refMillions = ((3.78 / xSteps) * i).toFixed(1);

      ctx.beginPath();
      ctx.moveTo(x, padding.top + chartH);
      ctx.lineTo(x, padding.top + chartH + 4);
      ctx.stroke();

      ctx.fillText(`${refMillions}M`, x, padding.top + chartH + 18);
    }

    // X-axis label
    ctx.fillStyle = textColor;
    ctx.font = '12px Inter, sans-serif';
    ctx.fillText('References processed (y = faults per 50,000-reference window)', padding.left + chartW / 2, h - 6);

    // Helper to map (index, val) to canvas (x, y)
    const getX = (i) => padding.left + chartW * ((i + 1) * chunkSize) / totalRefs;
    const getY = (val) => padding.top + chartH - (val / maxFault) * chartH;

    // Draw Baseline Line (Gray)
    if (baseline.length > 0) {
      ctx.beginPath();
      ctx.strokeStyle = isDark ? '#9ca3af' : '#64748b';
      ctx.lineWidth = 2;
      ctx.setLineDash([4, 3]);

      for (let i = 0; i < baseline.length; i++) {
        const x = getX(i);
        const y = getY(baseline[i]);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Draw Current Run Line (Blue = better, Orange = worse)
    if (current.length > 0) {
      const isHarmful = options.isHarmful || false;
      const lineColor = isHarmful ? '#eb6834' : '#2a78d6';

      // Area fill
      ctx.beginPath();
      for (let i = 0; i < current.length; i++) {
        const x = getX(i);
        const y = getY(current[i]);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.lineTo(getX(current.length - 1), padding.top + chartH);
      ctx.lineTo(getX(0), padding.top + chartH);
      ctx.closePath();
      ctx.fillStyle = isHarmful ? 'rgba(235, 104, 52, 0.12)' : 'rgba(42, 120, 214, 0.12)';
      ctx.fill();

      // Stroke
      ctx.beginPath();
      ctx.strokeStyle = lineColor;
      ctx.lineWidth = 2.5;
      for (let i = 0; i < current.length; i++) {
        const x = getX(i);
        const y = getY(current[i]);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }

    // Draw k over time (secondary axis if adaptive)
    if (kTimeline && kTimeline.length > 0) {
      const kGetY = (val) => padding.top + chartH - (val / 5) * chartH;

      ctx.beginPath();
      ctx.strokeStyle = '#10b981'; // Green accent for controller
      ctx.lineWidth = 1.8;
      ctx.setLineDash([2, 2]);

      for (let i = 0; i < kTimeline.length; i++) {
        const x = getX(i);
        const y = kGetY(kTimeline[i]);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
      ctx.setLineDash([]);

      // Right axis ticks for k
      ctx.fillStyle = '#10b981';
      ctx.font = '10px monospace';
      ctx.textAlign = 'left';
      for (let kVal = 0; kVal <= 5; kVal += 1) {
        const y = kGetY(kVal);
        ctx.fillText(`k=${kVal}`, padding.left + chartW + 6, y + 4);
      }
    }

    // Legend
    const legendX = padding.left + 10;
    const legendY = 16;
    ctx.font = '12px Inter, sans-serif';
    ctx.textAlign = 'left';

    // Baseline item
    let curX = legendX + 180;
    if (baseline.length > 0) {
      ctx.strokeStyle = isDark ? '#9ca3af' : '#64748b';
      ctx.setLineDash([4, 3]);
      ctx.beginPath();
      ctx.moveTo(legendX, legendY - 4);
      ctx.lineTo(legendX + 24, legendY - 4);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = textColor;
      ctx.fillText('Baseline LRU (Demand)', legendX + 30, legendY);
    } else {
      const noBaseNote = 'Baseline: run k=0 at this frame count to show it';
      ctx.fillStyle = textColor;
      ctx.fillText(noBaseNote, legendX, legendY);
      curX = legendX + Math.ceil(ctx.measureText(noBaseNote).width) + 20;
    }

    // Current run item
    ctx.strokeStyle = options.isHarmful ? '#eb6834' : '#2a78d6';
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.moveTo(curX, legendY - 4);
    ctx.lineTo(curX + 24, legendY - 4);
    ctx.stroke();
    ctx.fillStyle = textColor;
    ctx.fillText(options.runLabel || 'Current Run', curX + 30, legendY);

    if (kTimeline) {
      const kX = curX + 160;
      ctx.strokeStyle = '#10b981';
      ctx.setLineDash([2, 2]);
      ctx.beginPath();
      ctx.moveTo(kX, legendY - 4);
      ctx.lineTo(kX + 24, legendY - 4);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = '#10b981';
      ctx.fillText('Adaptive Degree k', kX + 30, legendY);
    }
  }

  /**
   * Renders a clean horizontal bar comparison chart for experiments.
   */
  static renderBarChart(canvas, items, options = {}) {
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const isDark = options.isDark || false;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    if (canvas.width !== rect.width * dpr || canvas.height !== rect.height * dpr) {
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
    }
    ctx.resetTransform();
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = rect.height;
    ctx.clearRect(0, 0, w, h);

    if (!items || items.length === 0) return;

    let labelFont = '12px Inter, sans-serif';
    ctx.font = labelFont;
    let maxLabelW = 0;
    for (const it of items) {
      const lw = ctx.measureText(it.label).width;
      if (lw > maxLabelW) maxLabelW = lw;
    }

    ctx.font = 'bold 12px monospace';
    let maxValW = 0;
    for (const it of items) {
      const valText = it.displayValue || it.value.toLocaleString('en-US');
      const vw = ctx.measureText(valText).width;
      if (vw > maxValW) maxValW = vw;
    }

    const padding = {
      top: 20,
      right: Math.max(80, Math.ceil(maxValW) + 16),
      bottom: 20,
      left: Math.max(140, Math.ceil(maxLabelW) + 24)
    };
    let chartW = w - padding.left - padding.right;
    if (chartW < 120) {
      chartW = 120;
      labelFont = '11px Inter, sans-serif';
      ctx.font = labelFont;
      let maxLabel11 = 0;
      for (const it of items) {
        const lw = ctx.measureText(it.label).width;
        if (lw > maxLabel11) maxLabel11 = lw;
      }
      padding.left = Math.max(140, Math.ceil(maxLabel11) + 24);
      if (padding.left + chartW + padding.right > w) {
        padding.left = Math.max(0, w - chartW - padding.right);
      }
    }
    const barCount = items.length;
    const barHeight = Math.min(28, (h - padding.top - padding.bottom) / barCount - 10);
    const step = (h - padding.top - padding.bottom) / barCount;

    // Find max value
    const maxVal = Math.max(...items.map(it => Math.abs(it.value)), 1);

    const textColor = isDark ? '#e5e7eb' : '#1f2937';
    const subTextColor = isDark ? '#9ca3af' : '#6b7280';

    for (let i = 0; i < barCount; i++) {
      const item = items[i];
      const y = padding.top + i * step + (step - barHeight) / 2;
      const barW = Math.max(4, (Math.abs(item.value) / maxVal) * chartW);

      // Label
      ctx.fillStyle = textColor;
      ctx.font = labelFont;
      ctx.textAlign = 'right';
      ctx.fillText(item.label, padding.left - 12, y + barHeight / 2 + 4);

      // Color selection
      let color = '#2a78d6'; // Default blue (prefetch / good)
      if (item.type === 'baseline') {
        color = isDark ? '#6b7280' : '#9ca3af'; // Gray
      } else if (item.value < 0 || item.isHarmful) {
        color = '#eb6834'; // Orange (harmful / worse)
      }

      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.roundRect ? ctx.roundRect(padding.left, y, barW, barHeight, 4) : ctx.rect(padding.left, y, barW, barHeight);
      ctx.fill();

      // Value label on right
      ctx.fillStyle = textColor;
      ctx.font = 'bold 12px monospace';
      ctx.textAlign = 'left';
      ctx.fillText(item.displayValue || item.value.toLocaleString('en-US'), padding.left + barW + 8, y + barHeight / 2 + 4);
    }
  }
}

