/**
 * 1011 Media Asset Manager - Search/Library Page
 * URL-driven search, indexed folder browser, saved searches,
 * virtualized results, and metadata preview.
 */

document.addEventListener('DOMContentLoaded', () => {
  const state = {
    selected: new Set(),
    lastClickedIndex: null,
    currentFile: null,
    currentIndex: null,
    allFiles: [],
    total: 0,
    page: 1,
    perPage: 50,
    hasMore: true,
    loading: false,
    focusedIndex: null,
    query: '',
    filter: 'all',
    sort: 'newest',
    dateFrom: '',
    dateTo: '',
    folderPrefix: '',
    view: 'grid',
    savedSearchId: null,
    tagSuggestions: [],
    folders: [],
    savedSearches: [],
    modalTagInput: null,
    batchTagInput: null,
    batchTagRemoveInput: null,
    visibleRangeKey: '',
    preview: {
      scale: 1,
      x: 0,
      y: 0,
      dragging: false,
      startX: 0,
      startY: 0,
      enabled: false,
    },
  };

  const searchInput = document.getElementById('library-search');
  const sortSelect = document.getElementById('sort-select');
  const filterChips = [...document.querySelectorAll('.filter-chip')];
  const viewBtns = [...document.querySelectorAll('[data-view]')];
  const resultCount = document.getElementById('result-count');
  const assetScroll = document.getElementById('asset-scroll');
  const stage = document.getElementById('asset-grid');
  const emptyState = document.getElementById('asset-empty');
  const selectionBar = document.getElementById('selection-bar');
  const selCountEl = document.getElementById('sel-count');
  const clearSelBtn = document.getElementById('sel-clear');
  const batchTagBtn = document.getElementById('sel-batch-tag');
  const batchColBtn = document.getElementById('sel-batch-collection');
  const batchDlBtn = document.getElementById('sel-download');
  const folderTree = document.getElementById('folder-tree');
  const clearFolderBtn = document.getElementById('clear-folder-filter-btn');
  const activeFolderLabel = document.getElementById('active-folder-label');
  const saveSearchBtn = document.getElementById('save-search-btn');
  const savedSearchList = document.getElementById('saved-search-list');
  const dateRangeBtn = document.getElementById('date-range-btn');
  const datePopover = document.getElementById('date-range-popover');
  const dateFromInput = document.getElementById('date-from-input');
  const dateToInput = document.getElementById('date-to-input');
  const dateApplyBtn = document.getElementById('date-range-apply');
  const dateClearBtn = document.getElementById('date-range-clear');

  const detailModal = document.getElementById('detail-modal');
  const modalPreviewArea = document.getElementById('modal-preview-area');
  const modalPreviewImg = document.getElementById('modal-preview-img');
  const modalPreviewVideo = document.getElementById('modal-preview-video');
  const modalPreviewEmpty = document.getElementById('modal-preview-empty');
  const modalPreviewLabel = document.getElementById('modal-preview-label');
  const modalPreviewIcon = document.getElementById('modal-preview-icon');
  const modalFilename = document.getElementById('modal-filename');
  const modalMeta = document.getElementById('modal-meta');
  const modalPath = document.getElementById('modal-path');
  const modalExifBody = document.getElementById('modal-exif-body');
  const modalTagContainer = document.getElementById('modal-tag-input-container');
  const modalPrevBtn = document.getElementById('modal-prev');
  const modalNextBtn = document.getElementById('modal-next');
  const modalDownloadBtn = document.getElementById('modal-download-btn');
  const modalCopyPathBtn = document.getElementById('modal-copy-path-btn');
  const modalAddCollectionBtn = document.getElementById('modal-add-collection-btn');
  const zoomInBtn = document.getElementById('zoom-in-btn');
  const zoomOutBtn = document.getElementById('zoom-out-btn');
  const zoomResetBtn = document.getElementById('zoom-reset-btn');
  const previewToolbar = document.querySelector('.preview-toolbar');

  const collectionPickerList = document.getElementById('collection-picker-list');
  const collectionPickerSubtitle = document.getElementById('collection-picker-subtitle');
  const collectionPickerCreateBtn = document.getElementById('collection-picker-create-new');

  const batchTagContainer = document.getElementById('batch-tag-input-container');
  const batchApplyBtn = document.querySelector('[data-batch-apply]');
  const batchRemoveBtn = document.getElementById('sel-batch-remove-tag');
  const batchRemoveContainer = document.getElementById('batch-tag-remove-input-container');
  const batchRemoveApplyBtn = document.querySelector('[data-batch-remove-apply]');

  if (!assetScroll || !stage) return;

  function escHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function formatBytes(bytes) {
    if (!bytes) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let size = Number(bytes);
    let unitIndex = 0;
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex += 1;
    }
    return `${size.toFixed(size >= 10 ? 0 : 1)} ${units[unitIndex]}`;
  }

  function formatDuration(seconds) {
    const total = Math.max(0, Math.round(Number(seconds) || 0));
    const mins = Math.floor(total / 60);
    const secs = String(total % 60).padStart(2, '0');
    return `${mins}:${secs}`;
  }

  function isImageExt(ext) {
    return ['jpg', 'jpeg', 'png', 'gif', 'webp', 'heic', 'tiff'].includes((ext || '').toLowerCase());
  }

  function isVideoExt(ext) {
    return ['mp4', 'mov', 'avi', 'mkv', 'mxf', 'r3d', 'braw'].includes((ext || '').toLowerCase());
  }

  function isDesignExt(ext) {
    return ['psd', 'psb', 'ai', 'eps'].includes((ext || '').toLowerCase());
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

  async function apiFetch(url, options = {}) {
    const response = await fetch(url, options);
    if (!response.ok) {
      let errorMessage = `API ${response.status}`;
      try {
        const data = await response.json();
        errorMessage = data.error || errorMessage;
      } catch (_) {}
      throw new Error(errorMessage);
    }
    return response.json();
  }

  async function apiSendJson(url, method, body) {
    return apiFetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  }

  function parseUrlState() {
    const params = new URLSearchParams(window.location.search);
    state.query = params.get('q') || '';
    state.filter = params.get('type') || 'all';
    state.sort = params.get('sort') || 'newest';
    state.dateFrom = params.get('date_from') || '';
    state.dateTo = params.get('date_to') || '';
    state.folderPrefix = params.get('folder_prefix') || '';
    state.view = params.get('view') || 'grid';
    state.savedSearchId = params.get('saved_search_id') || null;
  }

  function syncControlsFromState() {
    searchInput.value = state.query;
    sortSelect.value = state.sort;
    dateFromInput.value = state.dateFrom;
    dateToInput.value = state.dateTo;
    filterChips.forEach((chip) => chip.classList.toggle('active', chip.dataset.filter === state.filter));
    viewBtns.forEach((btn) => {
      const active = btn.dataset.view === state.view;
      btn.classList.toggle('active', active);
      btn.classList.toggle('btn-ghost', !active);
      btn.style.background = active ? 'var(--bg-hover)' : '';
    });
    if (state.folderPrefix) {
      activeFolderLabel.textContent = `Folder: ${state.folderPrefix}`;
      activeFolderLabel.style.display = '';
    } else {
      activeFolderLabel.style.display = 'none';
    }
  }

  function syncUrl() {
    const params = new URLSearchParams();
    if (state.query) params.set('q', state.query);
    if (state.filter !== 'all') params.set('type', state.filter);
    if (state.sort !== 'newest') params.set('sort', state.sort);
    if (state.dateFrom) params.set('date_from', state.dateFrom);
    if (state.dateTo) params.set('date_to', state.dateTo);
    if (state.folderPrefix) params.set('folder_prefix', state.folderPrefix);
    if (state.view !== 'grid') params.set('view', state.view);
    if (state.savedSearchId && page === 1) params.set('saved_search_id', state.savedSearchId);
    const query = params.toString();
    const nextUrl = `${window.location.pathname}${query ? `?${query}` : ''}`;
    window.history.replaceState({}, '', nextUrl);
  }

  function buildSearchParams(page) {
    const params = new URLSearchParams({
      q: state.query,
      type: state.filter,
      sort: state.sort,
      page: String(page),
      per_page: String(state.perPage),
    });
    if (state.dateFrom) params.set('date_from', state.dateFrom);
    if (state.dateTo) params.set('date_to', state.dateTo);
    if (state.folderPrefix) params.set('folder_prefix', state.folderPrefix);
    if (state.savedSearchId) params.set('saved_search_id', state.savedSearchId);
    return params;
  }

  async function loadTagSuggestions() {
    try {
      const data = await apiFetch('/api/tags?sort=count');
      state.tagSuggestions = data.tags.map((tag) => tag.tag);
    } catch (_) {
      state.tagSuggestions = [];
    }
  }

  async function loadFolders() {
    if (!folderTree) return;
    try {
      const data = await apiFetch('/api/folders');
      state.folders = data.folders || [];
      renderFolderTree();
    } catch (_) {
      if (folderTree) folderTree.innerHTML = '<p class="text-tertiary" style="font-size:var(--text-sm);">Could not load folders.</p>';
    }
  }

  function renderFolderTree() {
    if (!folderTree) return;
    if (!state.folders.length) {
      folderTree.innerHTML = '<p class="text-tertiary" style="font-size:var(--text-sm);">No indexed folders yet.</p>';
      return;
    }

    function renderNodes(nodes) {
      return nodes.map((node) => `
        <div class="folder-tree-node">
          <button class="search-panel-item ${state.folderPrefix === node.path ? 'active' : ''}" data-folder-path="${escHtml(node.path)}">
            <span style="display:flex;align-items:center;gap:8px;min-width:0;">
              <i data-lucide="folder-tree" style="width:14px;height:14px;"></i>
              <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escHtml(node.name)}</span>
            </span>
            <span class="text-tertiary" style="font-size:var(--text-xs);">${Number(node.count || 0).toLocaleString()}</span>
          </button>
          ${node.children && node.children.length ? `<div class="folder-tree-children">${renderNodes(node.children)}</div>` : ''}
        </div>
      `).join('');
    }

    folderTree.innerHTML = renderNodes(state.folders);
    if (window.lucide) lucide.createIcons({ nodes: [folderTree] });

    folderTree.querySelectorAll('[data-folder-path]').forEach((button) => {
      button.addEventListener('click', () => {
        state.folderPrefix = button.dataset.folderPath || '';
        state.savedSearchId = null;
        syncControlsFromState();
        renderFolderTree();
        resetAndLoadAssets();
      });
    });
  }

  async function loadSavedSearches() {
    if (!savedSearchList) return;
    try {
      const data = await apiFetch('/api/saved-searches');
      state.savedSearches = data.saved_searches || [];
      renderSavedSearches();
    } catch (_) {
      if (savedSearchList) savedSearchList.innerHTML = '<p class="text-tertiary" style="font-size:var(--text-sm);">Could not load saved searches.</p>';
    }
  }

  function renderSavedSearches() {
    if (!savedSearchList) return;
    if (!state.savedSearches.length) {
      savedSearchList.innerHTML = '<p class="text-tertiary" style="font-size:var(--text-sm);">No saved searches yet.</p>';
      return;
    }

    savedSearchList.innerHTML = state.savedSearches.map((saved) => `
      <div class="search-panel-item ${String(saved.id) === String(state.savedSearchId) ? 'active' : ''}" data-saved-search-id="${saved.id}">
        <button class="search-panel-item" data-apply-search="${saved.id}" style="padding:0;border:0;background:transparent;flex:1;">
          <span style="min-width:0;">
            <span style="display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escHtml(saved.name)}</span>
            <span class="text-tertiary" style="font-size:var(--text-xs);display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
              ${escHtml(saved.query || saved.folder_prefix || 'All assets')}
            </span>
          </span>
        </button>
        <div class="search-panel-item-actions">
          <button class="btn btn-icon btn-ghost btn-sm" data-rename-search="${saved.id}" aria-label="Rename saved search">
            <i data-lucide="pencil"></i>
          </button>
          <button class="btn btn-icon btn-ghost btn-sm" data-delete-search="${saved.id}" aria-label="Delete saved search">
            <i data-lucide="trash-2"></i>
          </button>
        </div>
      </div>
    `).join('');

    if (window.lucide) lucide.createIcons({ nodes: [savedSearchList] });

    savedSearchList.querySelectorAll('[data-apply-search]').forEach((button) => {
      button.addEventListener('click', async () => {
        const savedId = button.dataset.applySearch;
        const saved = state.savedSearches.find((item) => String(item.id) === String(savedId));
        if (!saved) return;
        state.query = saved.query || '';
        state.filter = saved.file_type || 'all';
        state.sort = saved.sort || 'newest';
        state.dateFrom = saved.date_from || '';
        state.dateTo = saved.date_to || '';
        state.folderPrefix = saved.folder_prefix || '';
        state.savedSearchId = String(saved.id);
        syncControlsFromState();
        renderSavedSearches();
        renderFolderTree();
        await resetAndLoadAssets();
      });
    });

    savedSearchList.querySelectorAll('[data-rename-search]').forEach((button) => {
      button.addEventListener('click', async (event) => {
        event.stopPropagation();
        const savedId = button.dataset.renameSearch;
        const saved = state.savedSearches.find((item) => String(item.id) === String(savedId));
        if (!saved) return;
        const name = window.prompt('Rename saved search', saved.name);
        if (!name || name.trim() === saved.name) return;
        try {
          await apiSendJson(`/api/saved-searches/${saved.id}`, 'PATCH', { name: name.trim() });
          Toast.success('Saved search updated');
          await loadSavedSearches();
        } catch (error) {
          Toast.error(error.message || 'Could not update saved search');
        }
      });
    });

    savedSearchList.querySelectorAll('[data-delete-search]').forEach((button) => {
      button.addEventListener('click', async (event) => {
        event.stopPropagation();
        const savedId = button.dataset.deleteSearch;
        const saved = state.savedSearches.find((item) => String(item.id) === String(savedId));
        if (!saved) return;
        if (!window.confirm(`Delete saved search "${saved.name}"?`)) return;
        try {
          const response = await fetch(`/api/saved-searches/${saved.id}`, { method: 'DELETE' });
          if (!response.ok) throw new Error('Could not delete saved search');
          if (String(state.savedSearchId) === String(saved.id)) {
            state.savedSearchId = null;
            syncUrl();
          }
          Toast.success('Saved search deleted');
          await loadSavedSearches();
        } catch (error) {
          Toast.error(error.message || 'Could not delete saved search');
        }
      });
    });
  }

  function getLayout() {
    const viewportWidth = assetScroll.clientWidth;
    const padding = 12;
    const gap = 16;
    if (state.view === 'list') {
      return {
        columns: 1,
        cardWidth: Math.max(240, viewportWidth - (padding * 2)),
        rowHeight: 112,
        gap: 12,
        padding,
      };
    }

    const minCardWidth = window.matchMedia('(max-width: 768px)').matches ? 150 : 200;
    const usableWidth = Math.max(1, viewportWidth - (padding * 2));
    const columns = Math.max(1, Math.floor((usableWidth + gap) / (minCardWidth + gap)));
    const cardWidth = Math.floor((usableWidth - ((columns - 1) * gap)) / columns);
    const infoHeight = 92;
    const rowHeight = Math.ceil((cardWidth * 0.75) + infoHeight);
    return { columns, cardWidth, rowHeight, gap, padding };
  }

  function cardHtml(file, index) {
    const ext = (file.ext || 'jpg').toLowerCase();
    const badgeLabel = isVideoExt(ext)
      ? (file.duration ? formatDuration(file.duration) : 'VIDEO')
      : ext.toUpperCase();
    const badgeColor = isVideoExt(ext) ? 'rgba(6,182,212,0.9)' : isDesignExt(ext) ? 'rgba(168,85,247,0.9)' : '';
    const tagPills = (file.tags || []).slice(0, 3).map((tag) =>
      `<span class="tag tag-custom" style="font-size:10px;padding:2px 6px;">${escHtml(tag)}</span>`
    ).join('');
    const selected = state.selected.has(file.id);
    const classNames = ['asset-card', 'virtualized'];
    if (selected) classNames.push('selected');

    return `
      <div class="${classNames.join(' ')}" data-file-id="${escHtml(file.id)}" data-index="${index}" tabindex="0">
        <label class="asset-card-check">
          <input type="checkbox" ${selected ? 'checked' : ''} style="opacity:0;position:absolute;width:100%;height:100%;cursor:pointer;">
          <i data-lucide="check" style="width:14px;height:14px;color:white;"></i>
        </label>
        <div class="asset-card-thumb">
          <img src="/api/thumb/${escHtml(file.id)}" alt="${escHtml(file.filename)}" loading="lazy" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;">
          <div class="asset-card-badge" ${badgeColor ? `style="background:${badgeColor};"` : ''}>${badgeLabel}</div>
        </div>
        <div class="asset-card-info">
          <p class="asset-card-name" title="${escHtml(file.filename)}">${escHtml(file.filename)}</p>
          <div style="font-size:var(--text-xs);color:var(--text-tertiary);margin:4px 0 8px;">
            ${escHtml(file.size_human || formatBytes(file.size))} · ${escHtml(file.date || '')}
          </div>
          <div class="asset-card-meta">${tagPills}</div>
        </div>
      </div>
    `;
  }

  function attachVisibleCardEvents() {
    stage.querySelectorAll('.asset-card[data-file-id]').forEach((card) => {
      const index = Number(card.dataset.index);
      const thumb = card.querySelector('.asset-card-thumb');
      const checkbox = card.querySelector('.asset-card-check');

      card.addEventListener('focus', () => {
        state.focusedIndex = index;
      });

      card.addEventListener('click', (event) => {
        if (event.target.closest('.asset-card-check')) return;
        if (event.target.closest('.asset-card-thumb')) {
          openDetailModal(index);
          return;
        }
        if (state.selected.size > 0 || event.shiftKey) {
          toggleSelection(index, event.shiftKey);
        }
      });

      checkbox.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        toggleSelection(index, event.shiftKey);
      });

      thumb.addEventListener('click', (event) => {
        if (event.target.closest('.asset-card-check')) return;
        openDetailModal(index);
      });
    });
  }

  function renderSelectionState() {
    stage.querySelectorAll('.asset-card[data-file-id]').forEach((card) => {
      const selected = state.selected.has(card.dataset.fileId);
      card.classList.toggle('selected', selected);
      const checkbox = card.querySelector('input[type="checkbox"]');
      if (checkbox) checkbox.checked = selected;
    });
    const count = state.selected.size;
    selCountEl.textContent = `${count} item${count === 1 ? '' : 's'} selected`;
    selectionBar.classList.toggle('visible', count > 0);
  }

  function renderVirtualWindow(force = false) {
    const layout = getLayout();
    const rowStep = layout.rowHeight + layout.gap;
    const totalRows = Math.max(1, Math.ceil(state.allFiles.length / layout.columns));
    stage.style.height = `${(layout.padding * 2) + (Math.max(0, totalRows - 1) * rowStep) + layout.rowHeight}px`;

    if (!state.allFiles.length) {
      stage.innerHTML = '';
      emptyState.hidden = false;
      if (window.lucide) lucide.createIcons({ nodes: [emptyState] });
      if (resultCount) resultCount.textContent = 'Showing 0 of 0';
      return;
    }

    emptyState.hidden = true;
    const scrollTop = assetScroll.scrollTop;
    const viewportHeight = assetScroll.clientHeight;
    const startRow = Math.max(0, Math.floor(scrollTop / rowStep) - 2);
    const endRow = Math.max(startRow, Math.floor((scrollTop + viewportHeight) / rowStep) + 2);
    const startIndex = startRow * layout.columns;
    const endIndex = Math.min(state.allFiles.length, (endRow + 1) * layout.columns);
    const rangeKey = `${state.view}:${startIndex}:${endIndex}:${layout.columns}:${layout.cardWidth}`;

    if (!force && rangeKey === state.visibleRangeKey) {
      renderSelectionState();
      return;
    }
    state.visibleRangeKey = rangeKey;

    const cards = [];
    for (let index = startIndex; index < endIndex; index += 1) {
      const file = state.allFiles[index];
      const row = Math.floor(index / layout.columns);
      const column = index % layout.columns;
      const top = layout.padding + (row * rowStep);
      const left = state.view === 'list'
        ? layout.padding
        : layout.padding + (column * (layout.cardWidth + layout.gap));
      cards.push(`
        <div class="virtual-card ${state.view === 'list' ? 'virtual-list-card' : ''}" style="top:${top}px;left:${left}px;width:${layout.cardWidth}px;">
          ${cardHtml(file, index)}
        </div>
      `);
    }

    stage.innerHTML = cards.join('');
    if (window.lucide) lucide.createIcons({ nodes: [stage] });
    attachVisibleCardEvents();
    renderSelectionState();

    if (resultCount) {
      resultCount.textContent = `Showing ${state.allFiles.length.toLocaleString()} of ${state.total.toLocaleString()}`;
    }

    if (state.focusedIndex !== null) {
      const focused = stage.querySelector(`[data-index="${state.focusedIndex}"]`);
      if (focused && document.activeElement !== focused) focused.focus();
    }
  }

  function toggleSelection(index, shiftHeld) {
    if (index < 0 || index >= state.allFiles.length) return;
    if (shiftHeld && state.lastClickedIndex !== null) {
      const start = Math.min(index, state.lastClickedIndex);
      const end = Math.max(index, state.lastClickedIndex);
      for (let cursor = start; cursor <= end; cursor += 1) {
        const file = state.allFiles[cursor];
        if (file) state.selected.add(file.id);
      }
    } else {
      const fileId = state.allFiles[index].id;
      if (state.selected.has(fileId)) state.selected.delete(fileId);
      else state.selected.add(fileId);
      state.lastClickedIndex = index;
    }
    renderSelectionState();
  }

  function clearSelection() {
    state.selected.clear();
    state.lastClickedIndex = null;
    renderSelectionState();
  }

  function ensureIndexVisible(index) {
    if (index < 0 || index >= state.allFiles.length) return;
    const layout = getLayout();
    const row = Math.floor(index / layout.columns);
    const rowStep = layout.rowHeight + layout.gap;
    const top = layout.padding + (row * rowStep);
    const bottom = top + layout.rowHeight;
    if (top < assetScroll.scrollTop) {
      assetScroll.scrollTop = Math.max(0, top - layout.gap);
    } else if (bottom > assetScroll.scrollTop + assetScroll.clientHeight) {
      assetScroll.scrollTop = bottom - assetScroll.clientHeight + layout.gap;
    }
  }

  function focusIndex(index) {
    if (index < 0 || index >= state.allFiles.length) return;
    state.focusedIndex = index;
    ensureIndexVisible(index);
    renderVirtualWindow(true);
  }

  async function loadAssets(reset = false) {
    if (state.loading) return;
    if (!reset && !state.hasMore) return;

    state.loading = true;
    if (reset) {
      state.page = 1;
      state.hasMore = true;
      state.total = 0;
      state.allFiles = [];
      state.focusedIndex = null;
      stage.innerHTML = '';
      emptyState.hidden = true;
      resultCount.textContent = 'Loading...';
      state.visibleRangeKey = '';
    }

    try {
      syncUrl();
      const data = await apiFetch(`/api/search?${buildSearchParams(state.page).toString()}`);
      state.total = data.total || 0;
      if (reset) state.allFiles = data.results || [];
      else state.allFiles = state.allFiles.concat(data.results || []);
      state.hasMore = state.allFiles.length < state.total;
      renderVirtualWindow(true);
    } catch (error) {
      Toast.error(error.message || 'Failed to load assets');
      state.allFiles = [];
      state.total = 0;
      renderVirtualWindow(true);
    } finally {
      state.loading = false;
    }
  }

  async function resetAndLoadAssets() {
    await loadAssets(true);
  }

  async function maybeLoadNextPage() {
    if (state.loading || !state.hasMore) return;
    const remaining = assetScroll.scrollHeight - assetScroll.scrollTop - assetScroll.clientHeight;
    if (remaining < 600) {
      state.page += 1;
      await loadAssets(false);
    }
  }

  function renderMetadataTable(file) {
    const metadata = file.metadata || {};
    const rows = [
      ['Camera', [metadata.make, metadata.model].filter(Boolean).join(' ') || null],
      ['Lens', metadata.lens || null],
      ['ISO', metadata.iso || null],
      ['Focal Length', metadata.focal_length ? `${metadata.focal_length} mm` : null],
      ['Aperture', metadata.aperture ? `f/${metadata.aperture}` : null],
      ['Shutter', metadata.shutter_speed || null],
      ['Captured', metadata.captured_at || file.date || null],
      ['GPS', metadata.gps_latitude && metadata.gps_longitude
        ? `${metadata.gps_latitude}, ${metadata.gps_longitude}`
        : null],
    ].filter((row) => row[1]);

    if (!rows.length) {
      modalExifBody.innerHTML = `
        <tr>
          <td colspan="2" style="color:var(--text-tertiary);font-size:var(--text-sm);padding:4px 0;">
            No embedded metadata available for this file.
          </td>
        </tr>
      `;
      return;
    }

    modalExifBody.innerHTML = rows.map(([label, value]) => `
      <tr>
        <td>${escHtml(label)}</td>
        <td style="text-align:right;">${escHtml(value)}</td>
      </tr>
    `).join('');
  }

  function syncPreviewTransform() {
    modalPreviewImg.style.transform = `translate(${state.preview.x}px, ${state.preview.y}px) scale(${state.preview.scale})`;
  }

  function resetPreviewTransform() {
    state.preview.scale = 1;
    state.preview.x = 0;
    state.preview.y = 0;
    state.preview.dragging = false;
    syncPreviewTransform();
  }

  function setPreviewEnabled(enabled) {
    state.preview.enabled = enabled;
    zoomInBtn.disabled = !enabled;
    zoomOutBtn.disabled = !enabled;
    zoomResetBtn.disabled = !enabled;
  }

  function renderPreview(file) {
    const ext = (file.ext || '').toLowerCase();
    if (isImageExt(ext)) {
      modalPreviewImg.src = `/api/thumb/${file.id}`;
      modalPreviewImg.style.display = 'block';
      modalPreviewVideo.style.display = 'none';
      modalPreviewEmpty.style.display = 'none';
      setPreviewEnabled(true);
      previewToolbar.style.display = 'flex';
      resetPreviewTransform();
      return;
    }

    if (isVideoExt(ext)) {
      const source = modalPreviewVideo.querySelector('source');
      source.src = `/api/file/${file.id}/raw`;
      source.type = getVideoMimeType(ext);
      modalPreviewVideo.style.display = 'block';
      modalPreviewImg.style.display = 'none';
      modalPreviewEmpty.style.display = 'none';
      setPreviewEnabled(false);
      previewToolbar.style.display = 'none';
      resetPreviewTransform();
      return;
    }

    modalPreviewImg.style.display = 'none';
    modalPreviewVideo.style.display = 'none';
    modalPreviewEmpty.style.display = 'flex';
    modalPreviewLabel.textContent = 'Preview unavailable for this file type';
    modalPreviewIcon.setAttribute('data-lucide', 'file-image');
    if (window.lucide) lucide.createIcons({ nodes: [modalPreviewEmpty] });
    setPreviewEnabled(false);
    previewToolbar.style.display = 'none';
    resetPreviewTransform();
  }

  function updateModalNav() {
    modalPrevBtn.style.visibility = state.currentIndex > 0 ? 'visible' : 'hidden';
    modalNextBtn.style.visibility = state.currentIndex < state.total - 1 ? 'visible' : 'hidden';
  }

  function updateFileCardTags(fileId, tags) {
    const file = state.allFiles.find((item) => item.id === fileId);
    if (file) file.tags = tags;
    renderVirtualWindow(true);
  }

  async function renderModalTagInput(file) {
    if (state.modalTagInput) state.modalTagInput.destroy();
    const tagNames = (file.tags || []).map((tag) => tag.tag);
    state.modalTagInput = new TagInput(modalTagContainer, {
      initialTags: tagNames,
      suggestions: state.tagSuggestions,
      placeholder: 'Add a tag...',
      onAdd: async (tag) => {
        try {
          await apiSendJson(`/api/file/${file.id}/tags`, 'POST', { tag });
          const tags = await apiFetch(`/api/file/${file.id}/tags`);
          file.tags = tags.tags;
          updateFileCardTags(file.id, tags.tags.map((item) => item.tag));
          await loadTagSuggestions();
        } catch (error) {
          Toast.error(error.message || 'Could not add tag');
          state.modalTagInput.setTags((file.tags || []).map((item) => item.tag));
        }
      },
      onRemove: async (tag) => {
        try {
          const response = await fetch(`/api/file/${file.id}/tags/${encodeURIComponent(tag)}`, { method: 'DELETE' });
          if (!response.ok) throw new Error('Could not remove tag');
          const tags = await apiFetch(`/api/file/${file.id}/tags`);
          file.tags = tags.tags;
          updateFileCardTags(file.id, tags.tags.map((item) => item.tag));
        } catch (error) {
          Toast.error(error.message || 'Could not remove tag');
          state.modalTagInput.setTags((file.tags || []).map((item) => item.tag));
        }
      },
    });
  }

  async function openDetailModal(index) {
    if (index < 0) return;
    if (index >= state.allFiles.length && state.hasMore) {
      state.page += 1;
      await loadAssets(false);
    }
    if (index < 0 || index >= state.allFiles.length) return;

    state.currentIndex = index;
    const baseFile = state.allFiles[index];
    try {
      const file = await apiFetch(`/api/file/${baseFile.id}`);
      state.currentFile = file;
      modalFilename.textContent = file.filename || '';
      modalMeta.textContent = `${file.size_human || formatBytes(file.size)} · ${file.width || 0}x${file.height || 0} · ${(file.ext || '').toUpperCase()}`;
      modalPath.value = file.path || '';
      renderMetadataTable(file);
      renderPreview(file);
      await renderModalTagInput(file);
      updateModalNav();
      ModalManager.open('detail-modal');
    } catch (error) {
      Toast.error(error.message || 'Could not load file details');
    }
  }

  async function stepModal(direction) {
    const nextIndex = (state.currentIndex || 0) + direction;
    if (nextIndex < 0 || nextIndex >= state.total) return;
    if (nextIndex >= state.allFiles.length && state.hasMore) {
      state.page += 1;
      await loadAssets(false);
    }
    if (nextIndex < state.allFiles.length) openDetailModal(nextIndex);
  }

  async function copyPathToClipboard() {
    const path = modalPath.value || (state.currentFile && state.currentFile.path) || '';
    if (!path) {
      Toast.info('No file path available');
      return;
    }

    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(path);
      } else {
        modalPath.removeAttribute('readonly');
        modalPath.select();
        document.execCommand('copy');
        modalPath.setAttribute('readonly', 'readonly');
      }
      Toast.success('File path copied');
    } catch (_) {
      Toast.info('Clipboard access is unavailable. Select and copy the path manually.');
      modalPath.focus();
      modalPath.select();
    }
  }

  async function downloadOriginal(file) {
    try {
      const response = await fetch(`/api/download/${file.id}`);
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error((errorData && errorData.error) || 'Original file is unavailable');
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = file.filename || 'asset';
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      Toast.info(error.message || 'Original file is unavailable');
    }
  }

  async function openCollectionPicker(mode) {
    const targetIds = mode === 'selected'
      ? [...state.selected]
      : state.currentFile
        ? [state.currentFile.id]
        : [];
    if (!targetIds.length) return;

    collectionPickerSubtitle.textContent = mode === 'selected'
      ? `Add ${targetIds.length} selected item(s) to a collection.`
      : 'Add this file to a collection.';

    try {
      const data = await apiFetch('/api/collections');
      const collections = data.collections || [];
      if (!collections.length) {
        collectionPickerList.innerHTML = '<p class="text-tertiary" style="font-size:var(--text-sm);">No collections yet.</p>';
      } else {
        collectionPickerList.innerHTML = collections.map((collection) => `
          <button class="search-panel-item" data-collection-id="${collection.id}">
            <span>${escHtml(collection.name)}</span>
            <span class="text-tertiary" style="font-size:var(--text-xs);">${Number(collection.item_count || 0).toLocaleString()} items</span>
          </button>
        `).join('');
      }
      collectionPickerList.querySelectorAll('[data-collection-id]').forEach((button) => {
        button.addEventListener('click', async () => {
          try {
            const result = await apiSendJson(`/api/collections/${button.dataset.collectionId}/items`, 'POST', { file_ids: targetIds });
            Toast.success(`Added ${result.added} item(s) to collection`);
            ModalManager.close('collection-picker-modal');
          } catch (error) {
            Toast.error(error.message || 'Could not add to collection');
          }
        });
      });
      ModalManager.open('collection-picker-modal');
    } catch (error) {
      Toast.error(error.message || 'Could not load collections');
    }
  }

  async function createCollectionFromPicker() {
    const name = window.prompt('Collection name');
    if (!name || !name.trim()) return;
    try {
      await apiSendJson('/api/collections', 'POST', { name: name.trim(), description: '' });
      Toast.success('Collection created');
      await openCollectionPicker(state.selected.size ? 'selected' : 'single');
    } catch (error) {
      Toast.error(error.message || 'Could not create collection');
    }
  }

  function initBatchTagInput() {
    if (state.batchTagInput) state.batchTagInput.destroy();
    state.batchTagInput = new TagInput(batchTagContainer, {
      initialTags: [],
      suggestions: state.tagSuggestions,
      placeholder: 'Add batch tags...',
    });
  }

  async function applyBatchTags() {
    const fileIds = [...state.selected];
    const tags = state.batchTagInput ? state.batchTagInput.getTags() : [];
    if (!fileIds.length || !tags.length) {
      Toast.info('Select files and add at least one tag');
      return;
    }
    batchApplyBtn.disabled = true;
    try {
      const result = await apiSendJson('/api/batch/tags', 'POST', { file_ids: fileIds, tags });
      Toast.success(`Applied ${result.tags_applied} new tag assignment(s)`);
      ModalManager.close('batch-tag-modal');
      clearSelection();
      await loadTagSuggestions();
      await resetAndLoadAssets();
    } catch (error) {
      Toast.error(error.message || 'Batch tag failed');
    } finally {
      batchApplyBtn.disabled = false;
    }
  }

  function initBatchTagRemoveInput() {
    if (state.batchTagRemoveInput) state.batchTagRemoveInput.destroy();
    state.batchTagRemoveInput = new TagInput(batchRemoveContainer, {
      initialTags: [],
      suggestions: state.tagSuggestions,
      placeholder: 'Type tag to remove...',
    });
  }

  async function applyBatchRemoveTags() {
    const fileIds = [...state.selected];
    const tags = state.batchTagRemoveInput ? state.batchTagRemoveInput.getTags() : [];
    if (!fileIds.length || !tags.length) {
      Toast.info('Select files and add at least one tag to remove');
      return;
    }
    if (batchRemoveApplyBtn) batchRemoveApplyBtn.disabled = true;
    try {
      const result = await apiSendJson('/api/batch/tags/remove', 'POST', { file_ids: fileIds, tags });
      Toast.success(`Removed ${result.tags_removed} tag assignment(s)`);
      ModalManager.close('batch-tag-remove-modal');
      clearSelection();
      await loadTagSuggestions();
      await resetAndLoadAssets();
    } catch (error) {
      Toast.error(error.message || 'Batch tag remove failed');
    } finally {
      if (batchRemoveApplyBtn) batchRemoveApplyBtn.disabled = false;
    }
  }

  async function batchDownloadSelected() {
    const fileIds = [...state.selected];
    if (!fileIds.length) return;
    try {
      const response = await fetch('/api/batch/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_ids: fileIds }),
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error((errorData && errorData.error) || 'Batch download failed');
      }
      const included = Number(response.headers.get('X-Archive-Included') || 0);
      const missing = Number(response.headers.get('X-Archive-Missing') || 0);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `1011_Media_Batch_${Date.now()}.zip`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      Toast.success(`Archive ready: ${included} included${missing ? `, ${missing} skipped` : ''}`);
    } catch (error) {
      Toast.error(error.message || 'Batch download failed');
    }
  }

  function handleKeyboardNavigation(event) {
    const modalOpen = detailModal && detailModal.style.display !== 'none';
    if (modalOpen) {
      if (event.key === 'ArrowLeft') {
        event.preventDefault();
        stepModal(-1);
      } else if (event.key === 'ArrowRight') {
        event.preventDefault();
        stepModal(1);
      }
      return;
    }

    if (event.key === 'Escape' && state.selected.size) {
      clearSelection();
      return;
    }

    if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) {
      if (document.activeElement && document.activeElement.tagName === 'INPUT' && document.activeElement !== searchInput) return;
      event.preventDefault();
      const layout = getLayout();
      const current = state.focusedIndex === null ? 0 : state.focusedIndex;
      let nextIndex = current;
      if (event.key === 'ArrowLeft') nextIndex = current - 1;
      if (event.key === 'ArrowRight') nextIndex = current + 1;
      if (event.key === 'ArrowUp') nextIndex = current - layout.columns;
      if (event.key === 'ArrowDown') nextIndex = current + layout.columns;
      nextIndex = Math.max(0, Math.min(state.allFiles.length - 1, nextIndex));
      focusIndex(nextIndex);
    }

    if (event.key === 'Enter' && state.focusedIndex !== null && document.activeElement !== searchInput) {
      event.preventDefault();
      openDetailModal(state.focusedIndex);
    }
  }

  function bindPreviewInteractions() {
    modalPreviewArea.addEventListener('wheel', (event) => {
      if (!state.preview.enabled) return;
      event.preventDefault();
      state.preview.scale = Math.max(1, Math.min(5, state.preview.scale + (event.deltaY < 0 ? 0.2 : -0.2)));
      syncPreviewTransform();
    }, { passive: false });

    modalPreviewImg.addEventListener('pointerdown', (event) => {
      if (!state.preview.enabled || state.preview.scale <= 1) return;
      state.preview.dragging = true;
      state.preview.startX = event.clientX - state.preview.x;
      state.preview.startY = event.clientY - state.preview.y;
      modalPreviewImg.classList.add('dragging');
      modalPreviewImg.setPointerCapture(event.pointerId);
    });

    modalPreviewImg.addEventListener('pointermove', (event) => {
      if (!state.preview.dragging) return;
      state.preview.x = event.clientX - state.preview.startX;
      state.preview.y = event.clientY - state.preview.startY;
      syncPreviewTransform();
    });

    modalPreviewImg.addEventListener('pointerup', (event) => {
      state.preview.dragging = false;
      modalPreviewImg.classList.remove('dragging');
      modalPreviewImg.releasePointerCapture(event.pointerId);
    });
  }

  function bindEvents() {
    let searchDebounce = null;
    searchInput.addEventListener('input', () => {
      clearTimeout(searchDebounce);
      searchDebounce = setTimeout(() => {
        state.query = searchInput.value.trim();
        state.savedSearchId = null;
        resetAndLoadAssets();
      }, 200);
    });

    sortSelect.addEventListener('change', () => {
      state.sort = sortSelect.value;
      state.savedSearchId = null;
      resetAndLoadAssets();
    });

    filterChips.forEach((chip) => {
      chip.addEventListener('click', () => {
        state.filter = chip.dataset.filter;
        state.savedSearchId = null;
        syncControlsFromState();
        resetAndLoadAssets();
      });
    });

    viewBtns.forEach((button) => {
      button.addEventListener('click', () => {
        state.view = button.dataset.view;
        syncControlsFromState();
        syncUrl();
        state.visibleRangeKey = '';
        renderVirtualWindow(true);
      });
    });

    clearSelBtn.addEventListener('click', clearSelection);
    batchTagBtn.addEventListener('click', () => {
      if (!state.selected.size) return;
      initBatchTagInput();
      ModalManager.open('batch-tag-modal');
    });
    if (batchRemoveBtn) {
      batchRemoveBtn.addEventListener('click', () => {
        if (!state.selected.size) return;
        initBatchTagRemoveInput();
        ModalManager.open('batch-tag-remove-modal');
      });
    }
    batchColBtn.addEventListener('click', () => openCollectionPicker('selected'));
    batchDlBtn.addEventListener('click', batchDownloadSelected);
    batchApplyBtn.addEventListener('click', applyBatchTags);
    if (batchRemoveApplyBtn) {
      batchRemoveApplyBtn.addEventListener('click', applyBatchRemoveTags);
    }

    if (saveSearchBtn) {
      saveSearchBtn.addEventListener('click', async () => {
        const name = window.prompt('Save current search as');
        if (!name || !name.trim()) return;
        try {
          const payload = {
            name: name.trim(),
            query: state.query,
            file_type: state.filter,
            sort: state.sort,
            date_from: state.dateFrom || null,
            date_to: state.dateTo || null,
            folder_prefix: state.folderPrefix || null,
          };
          const saved = await apiSendJson('/api/saved-searches', 'POST', payload);
          state.savedSearchId = String(saved.id);
          Toast.success('Saved search created');
          await loadSavedSearches();
          syncUrl();
        } catch (error) {
          Toast.error(error.message || 'Could not save search');
        }
      });
    }

    if (clearFolderBtn) {
      clearFolderBtn.addEventListener('click', () => {
        if (!state.folderPrefix) return;
        state.folderPrefix = '';
        state.savedSearchId = null;
        syncControlsFromState();
        renderFolderTree();
        resetAndLoadAssets();
      });
    }

    dateRangeBtn.addEventListener('click', () => {
      datePopover.style.display = datePopover.style.display === 'block' ? 'none' : 'block';
    });
    dateApplyBtn.addEventListener('click', () => {
      state.dateFrom = dateFromInput.value;
      state.dateTo = dateToInput.value;
      state.savedSearchId = null;
      datePopover.style.display = 'none';
      resetAndLoadAssets();
    });
    dateClearBtn.addEventListener('click', () => {
      state.dateFrom = '';
      state.dateTo = '';
      dateFromInput.value = '';
      dateToInput.value = '';
      state.savedSearchId = null;
      datePopover.style.display = 'none';
      resetAndLoadAssets();
    });
    document.addEventListener('click', (event) => {
      if (!datePopover.contains(event.target) && !dateRangeBtn.contains(event.target)) {
        datePopover.style.display = 'none';
      }
    });

    assetScroll.addEventListener('scroll', async () => {
      renderVirtualWindow();
      await maybeLoadNextPage();
    });
    window.addEventListener('resize', () => {
      state.visibleRangeKey = '';
      renderVirtualWindow(true);
    });
    document.addEventListener('keydown', handleKeyboardNavigation);

    modalPrevBtn.addEventListener('click', (event) => {
      event.stopPropagation();
      stepModal(-1);
    });
    modalNextBtn.addEventListener('click', (event) => {
      event.stopPropagation();
      stepModal(1);
    });
    modalDownloadBtn.addEventListener('click', () => {
      if (state.currentFile) downloadOriginal(state.currentFile);
    });
    modalCopyPathBtn.addEventListener('click', copyPathToClipboard);
    modalAddCollectionBtn.addEventListener('click', () => openCollectionPicker('single'));
    collectionPickerCreateBtn.addEventListener('click', createCollectionFromPicker);

    zoomInBtn.addEventListener('click', () => {
      if (!state.preview.enabled) return;
      state.preview.scale = Math.min(5, state.preview.scale + 0.25);
      syncPreviewTransform();
    });
    zoomOutBtn.addEventListener('click', () => {
      if (!state.preview.enabled) return;
      state.preview.scale = Math.max(1, state.preview.scale - 0.25);
      if (state.preview.scale === 1) {
        state.preview.x = 0;
        state.preview.y = 0;
      }
      syncPreviewTransform();
    });
    zoomResetBtn.addEventListener('click', resetPreviewTransform);

    bindPreviewInteractions();
  }

  async function init() {
    parseUrlState();
    syncControlsFromState();
    bindEvents();
    await Promise.all([loadTagSuggestions(), loadFolders(), loadSavedSearches()]);
    await resetAndLoadAssets();
  }

  init();
});
