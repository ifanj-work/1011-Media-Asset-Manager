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
});
