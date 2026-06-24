/**
 * Dashboard — loads recent assets from API and renders mini-cards
 */
document.addEventListener('DOMContentLoaded', async () => {
  const grid = document.getElementById('dashboard-recent-grid');
  if (!grid) return;

  try {
    const res  = await fetch('/api/search?sort=newest&per_page=6');
    const data = await res.json();

    if (!data.results || !data.results.length) {
      grid.innerHTML = `
        <div style="grid-column:1/-1;text-align:center;padding:var(--space-8);color:var(--text-tertiary);">
          <i data-lucide="image-off" style="width:40px;height:40px;opacity:0.3;margin-bottom:8px;"></i>
          <p>No assets indexed yet.</p>
        </div>`;
      if (window.lucide) lucide.createIcons({ nodes: [grid] });
      return;
    }

    grid.innerHTML = data.results.map(f => {
      const ext = (f.ext || '').toLowerCase();
      const isVideo = ['mp4','mov','avi','mkv','mxf'].includes(ext);
      const isPsd   = ['psd','psb','ai'].includes(ext);
      const badgeColor = isVideo ? 'rgba(6,182,212,0.9)' : isPsd ? 'rgba(168,85,247,0.9)' : '';
      const badge = `${ext.toUpperCase()}${isVideo && f.duration ? ' · ' + formatDur(f.duration) : ''}`;
      const tagPills = (f.tags || []).slice(0, 2).map(t =>
        `<span class="tag tag-custom" style="font-size:10px;padding:1px 5px;">${esc(t)}</span>`
      ).join('');

      return `
        <a href="/search" class="asset-card" style="text-decoration:none;">
          <div class="asset-card-thumb">
            <img src="/api/thumb/${esc(f.id)}" alt="${esc(f.filename)}"
                 loading="lazy"
                 style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;">
            <div class="asset-card-badge"${badgeColor ? ` style="background:${badgeColor};"` : ''}>${badge}</div>
          </div>
          <div class="asset-card-info">
            <p class="asset-card-name" title="${esc(f.filename)}">${esc(f.filename)}</p>
            <div class="asset-card-meta">${tagPills}</div>
          </div>
        </a>`;
    }).join('');

    if (window.lucide) lucide.createIcons({ nodes: [grid] });

  } catch (e) {
    grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;
      padding:var(--space-6);color:var(--text-tertiary);font-size:var(--text-sm);">
      Could not load recent assets.</div>`;
  }

  function esc(s) {
    return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  function formatDur(s) {
    s = Math.round(s);
    return `${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`;
  }

  // ── Scanner Logic ────────────────────────────────────────────────────────
  const pathInput = document.getElementById('library-path-input');
  const btnSave   = document.getElementById('btn-save-path');
  const btnScan   = document.getElementById('btn-rescan');
  const statusIcon = document.getElementById('scan-status-icon');
  const resultMsg = document.getElementById('scan-result-msg');

  if (pathInput && btnScan) {
    // 1. Load current config
    try {
      const cRes = await fetch('/api/config');
      const config = await cRes.json();
      if (config.library_path) {
        pathInput.value = config.library_path;
      }
      if (config.last_scan) {
        showResult(`Last scan: ${new Date(config.last_scan).toLocaleString()}`, 'text-tertiary');
      }
    } catch (e) { console.error("Failed to load config", e); }

    // 2. Save Path
    btnSave.addEventListener('click', async () => {
      const path = pathInput.value.trim();
      if (!path) return;
      
      btnSave.disabled = true;
      try {
        await fetch('/api/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ library_path: path })
        });
        Toast.success('Path saved');
      } catch (e) {
        Toast.error('Failed to save path');
      } finally {
        btnSave.disabled = false;
      }
    });

    // 3. Trigger Scan
    btnScan.addEventListener('click', async () => {
      const path = pathInput.value.trim();
      if (!path) {
        Toast.warning('Please enter at least one directory path first');
        return;
      }

      setScanning(true);
      showResult("Scanning configured directories... This may take a minute.", "text-accent");

      try {
        const sRes = await fetch('/api/scan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path })
        });
        const report = await sRes.json();

        if (report.error) {
          showResult(`Error: ${report.error}`, "text-error");
          Toast.error(report.error);
        } else {
          const scannedCount = (report.scanned_paths || []).length;
          const invalidCount = (report.invalid_paths || []).length;
          let msg = `Scan complete across ${scannedCount} path(s). Found: ${report.found}, New: ${report.new}, Updated: ${report.updated}.`;
          if (invalidCount > 0) {
            msg += ` Skipped ${invalidCount} invalid path(s).`;
          }
          showResult(msg, "text-success");
          Toast.success('Scan completed');
          
          // Refresh stats/grid after short delay
          setTimeout(() => window.location.reload(), 2000);
        }
      } catch (e) {
        showResult("Scanning failed. Check server logs.", "text-error");
        Toast.error('Scan failed');
      } finally {
        setScanning(false);
      }
    });
  }

  function setScanning(active) {
    btnScan.disabled = active;
    const progressContainer = document.getElementById('scan-progress-container');
    if (active) {
      statusIcon.classList.add('animate-spin');
      statusIcon.style.color = 'var(--color-accent)';
      btnScan.innerHTML = '<i data-lucide="loader" class="animate-spin" style="width:16px;height:16px;"></i> <span>Scanning...</span>';
      if(progressContainer) progressContainer.classList.remove('hidden');
    } else {
      statusIcon.classList.remove('animate-spin');
      statusIcon.style.color = 'var(--text-tertiary)';
      btnScan.innerHTML = '<i data-lucide="search" style="width:16px;height:16px;"></i> <span>Start Rescan</span>';
      if(progressContainer) progressContainer.classList.add('hidden');
    }
    if (window.lucide) lucide.createIcons({ nodes: [btnScan] });
  }

  function showResult(text, className) {
    resultMsg.innerHTML = text;
    resultMsg.className = `text-xs mt-3 ${className}`;
    resultMsg.style.display = 'block';
  }
});
