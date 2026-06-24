/**
 * 1011 Media Asset Manager — Collection Detail Page
 * Loads collection items from the stabilized collection API.
 */

document.addEventListener('DOMContentLoaded', () => {
  const colId = window.COLLECTION_ID;
  if (!colId) return;

  const grid = document.getElementById('asset-grid');
  const resultCount = document.getElementById('result-count');
  const sortSelect = document.getElementById('sort-select');
  const summaryCount = document.getElementById('col-item-count');

  const modalImg = document.getElementById('modal-preview-img');
  const modalVideo = document.getElementById('modal-preview-video');
  const modalIcon = document.getElementById('modal-preview-icon');
  const modalFilename = document.getElementById('modal-filename');
  const modalFilesize = document.getElementById('modal-filesize');
  const modalDate = document.getElementById('modal-date');
  const modalType = document.getElementById('modal-type');
  const modalPath = document.getElementById('modal-path');
  const btnPrev = document.getElementById('modal-prev');
  const btnNext = document.getElementById('modal-next');
  const btnDownload = document.getElementById('modal-download-btn');
  const btnRemove = document.getElementById('modal-remove-collection-btn');

  function isImageExt(ext) {
    return ['jpg', 'jpeg', 'png', 'gif', 'webp', 'heic', 'tiff'].includes((ext || '').toLowerCase());
  }

  function isVideoExt(ext) {
    return ['mp4', 'mov', 'avi', 'mkv', 'mxf', 'r3d', 'braw'].includes((ext || '').toLowerCase());
  }

  function getVideoMimeType(ext) {
    const mimeTypes = {
      'mp4': 'video/mp4',
      'mov': 'video/quicktime',
      'avi': 'video/x-msvideo',
      'mkv': 'video/x-matroska',
      'mxf': 'video/mxf',
      'r3d': 'video/x-r3d',
      'braw': 'video/x-braw',
    };
    return mimeTypes[ext.toLowerCase()] || 'video/mp4';
  }

  const state = {
    assets: [],
    total: 0,
    page: 1,
    perPage: 50,
    sort: sortSelect ? sortSelect.value : 'newest',
    loading: false,
    hasMore: true,
    previewIdx: 0,
  };

  async function fetchItems(reset = false) {
    if (!grid || state.loading) return;
    if (!reset && !state.hasMore) return;

    if (reset) {
      state.page = 1;
      state.assets = [];
      state.total = 0;
      state.hasMore = true;
      grid.innerHTML = '';
    }

    state.loading = true;
    showLoading();

    const params = new URLSearchParams({
      page: state.page,
      per_page: state.perPage,
      sort: state.sort,
    });

    try {
      const res = await fetch(`/api/collections/${colId}/items?${params.toString()}`);
      if (!res.ok) throw new Error('API error');
      const data = await res.json();
      const items = data.results || [];

      if (reset) {
        state.assets = items;
      } else {
        state.assets = state.assets.concat(items);
      }
      state.total = data.total || 0;
      state.hasMore = state.assets.length < state.total;

      if (!state.assets.length) {
        renderEmptyState();
      } else {
        renderAssets(items, reset);
      }

      updateCounts();
    } catch (err) {
      console.error(err);
      Toast.error('Failed to load collection items.');
      if (!state.assets.length) renderEmptyState('Could not load collection items.');
    } finally {
      state.loading = false;
      removeLoading();
    }
  }

  function updateCounts() {
    if (resultCount) {
      resultCount.textContent = `Showing ${formatNumber(state.assets.length)} of ${formatNumber(state.total)}`;
    }
    if (summaryCount) {
      summaryCount.textContent = formatNumber(state.total);
    }
  }

  function showLoading() {
    if (!grid) return;
    const skeletons = Array.from({ length: 4 }).map(() => `
      <div class="asset-card skeleton-card">
        <div class="asset-card-thumb">
          <div class="skeleton-shimmer" style="width: 100%; height: 100%; position: absolute; inset: 0;"></div>
        </div>
        <div class="asset-card-info">
          <div class="skeleton-shimmer" style="height: 14px; width: 70%; border-radius: 4px; margin-bottom: 6px;"></div>
          <div class="skeleton-shimmer" style="height: 10px; width: 40%; border-radius: 4px;"></div>
        </div>
      </div>
    `).join('');
    grid.insertAdjacentHTML('beforeend', skeletons);
  }

  function removeLoading() {
    if (!grid) return;
    grid.querySelectorAll('.skeleton-card').forEach((el) => el.remove());
  }

  function renderEmptyState(message = 'This collection is empty.') {
    if (!grid) return;
    grid.innerHTML = `
      <div style="grid-column:1/-1;text-align:center;padding:var(--space-8);color:var(--text-tertiary);">
        <i data-lucide="folder-open" style="width:48px;height:48px;margin-bottom:var(--space-2);opacity:0.5;"></i>
        <p class="font-medium font-poppins">${message}</p>
        <p class="text-sm">Search and add assets to this collection to see them here.</p>
      </div>
    `;
    if (window.lucide) lucide.createIcons({ nodes: [grid] });
  }

  function renderAssets(items, reset) {
    if (!grid) return;
    if (reset) grid.innerHTML = '';

    const fragment = document.createDocumentFragment();
    const baseIdx = state.assets.length - items.length;

    items.forEach((asset, offset) => {
      const ext = (asset.ext || '').toUpperCase();
      const globalIdx = baseIdx + offset;
      const card = document.createElement('div');
      card.className = 'asset-card';
      card.dataset.idx = globalIdx;
      card.innerHTML = `
        <div class="asset-card-thumb">
          <img src="/api/thumb/${asset.id}" alt="${escHtml(asset.filename)}" style="position:absolute;inset:0;width:100%;height:100%;object-fit:contain;">
          <div class="asset-card-badge">${ext}</div>
        </div>
        <div class="asset-card-info">
          <p class="asset-card-name" title="${escHtml(asset.filename)}">${escHtml(asset.filename)}</p>
          <div style="font-size:var(--text-xs);color:var(--text-tertiary);margin-top:4px;margin-bottom:8px;">
            ${asset.size_human || formatBytes(asset.size)} • ${(asset.added_at || '').substring(0, 10)}
          </div>
        </div>
      `;
      card.addEventListener('click', () => openPreview(globalIdx));
      fragment.appendChild(card);
    });

    grid.appendChild(fragment);
    if (window.lucide) lucide.createIcons({ nodes: [grid] });
  }

  function openPreview(idx) {
    if (idx < 0 || idx >= state.assets.length) return;
    state.previewIdx = idx;
    const asset = state.assets[idx];
    const ext = (asset.ext || '').toLowerCase();

    if (isImageExt(ext)) {
      if (modalImg) {
        modalImg.style.display = 'block';
        modalImg.src = `/api/thumb/${asset.id}`;
      }
      if (modalVideo) modalVideo.style.display = 'none';
    } else if (isVideoExt(ext)) {
      if (modalVideo) {
        const source = modalVideo.querySelector('source');
        source.src = `/api/file/${asset.id}/raw`;
        source.type = getVideoMimeType(ext);
        modalVideo.style.display = 'block';
      }
      if (modalImg) modalImg.style.display = 'none';
    } else {
      if (modalImg) modalImg.style.display = 'none';
      if (modalVideo) modalVideo.style.display = 'none';
    }
    if (modalIcon) modalIcon.style.display = 'none';
    if (modalFilename) modalFilename.textContent = asset.filename;
    if (modalFilesize) modalFilesize.textContent = asset.size_human || formatBytes(asset.size);
    if (modalDate) modalDate.textContent = (asset.added_at || asset.date || 'Unknown').substring(0, 10);
    if (modalType) modalType.textContent = `${(asset.ext || '').toUpperCase()} File`;
    if (modalPath) modalPath.textContent = asset.path || '';

    updatePreviewNav();
    ModalManager.open('detail-modal');
  }

  function updatePreviewNav() {
    if (btnPrev) btnPrev.style.visibility = state.previewIdx > 0 ? 'visible' : 'hidden';
    if (btnNext) btnNext.style.visibility = state.previewIdx < state.assets.length - 1 ? 'visible' : 'hidden';
  }

  async function downloadAsset(asset) {
    try {
      const res = await fetch(`/api/download/${asset.id}`);
      if (!res.ok) {
        const err = await safeJson(res);
        throw new Error(err?.error || 'Original file is unavailable in demo mode.');
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = asset.filename || 'asset';
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      Toast.info(err.message || 'Original file is unavailable in demo mode.');
    }
  }

  if (btnPrev) {
    btnPrev.addEventListener('click', (e) => {
      e.stopPropagation();
      if (state.previewIdx > 0) openPreview(state.previewIdx - 1);
    });
  }

  if (btnNext) {
    btnNext.addEventListener('click', (e) => {
      e.stopPropagation();
      if (state.previewIdx < state.assets.length - 1) openPreview(state.previewIdx + 1);
    });
  }

  if (btnDownload) {
    btnDownload.addEventListener('click', async () => {
      const asset = state.assets[state.previewIdx];
      if (!asset) return;
      await downloadAsset(asset);
    });
  }

  if (btnRemove) {
    btnRemove.addEventListener('click', async () => {
      const asset = state.assets[state.previewIdx];
      if (!asset) return;

      btnRemove.disabled = true;
      try {
        const res = await fetch(`/api/collections/${colId}/items/${asset.id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error('API error');

        Toast.success('Removed from collection');
        ModalManager.close('detail-modal');
        await fetchItems(true);
      } catch (err) {
        console.error(err);
        Toast.error('Could not remove file');
      } finally {
        btnRemove.disabled = false;
      }
    });
  }

  if (sortSelect) {
    sortSelect.addEventListener('change', async () => {
      state.sort = sortSelect.value;
      await fetchItems(true);
    });
  }

  if (grid) {
    grid.addEventListener('scroll', () => {
      if (
        !state.loading &&
        state.hasMore &&
        grid.scrollHeight - grid.scrollTop - grid.clientHeight < 100
      ) {
        state.page += 1;
        fetchItems();
      }
    });
  }

  function formatBytes(bytes) {
    if (bytes === 0 || !bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  function formatNumber(num) {
    return new Intl.NumberFormat().format(num || 0);
  }

  function escHtml(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  async function safeJson(response) {
    try {
      return await response.json();
    } catch (_) {
      return null;
    }
  }

  fetchItems(true);
});
