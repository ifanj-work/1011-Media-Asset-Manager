/**
 * 1011 Media Asset Manager — Search/Library Page
 * All data fetched from real API endpoints.
 */

document.addEventListener('DOMContentLoaded', () => {

  // ─── State ──────────────────────────────────────────────────────────────────
  const state = {
    selected: new Set(),       // file IDs (strings)
    lastClickedFileId: null,
    currentFile: null,         // full file object currently in modal
    allFiles: [],              // current page results from API
    focusedIndex: null,
    query: '',
    filter: 'all',
    sort: 'newest',
    dateFrom: '',
    dateTo: '',
    page: 1,
    total: 0,
    loading: false,
    tagSuggestions: [],
    tagInput: null,
  };

  // ─── Elements ─────────────────────────────────────────────────────────────
  const grid          = document.querySelector('.asset-grid');
  const searchInput   = document.getElementById('library-search');
  const selectionBar  = document.getElementById('selection-bar');
  const selCountEl    = document.getElementById('sel-count');
  const clearSelBtn   = document.getElementById('sel-clear');
  const batchTagBtn   = document.getElementById('sel-batch-tag');
  const batchColBtn   = document.getElementById('sel-batch-collection');
  const batchDlBtn    = document.getElementById('sel-download');
  const filterChips   = document.querySelectorAll('.filter-chip');
  const viewBtns      = document.querySelectorAll('[data-view]');
  const sortSelect    = document.getElementById('sort-select');
  const detailModal   = document.getElementById('detail-modal');
  const prevBtn       = document.getElementById('modal-prev');
  const nextBtn       = document.getElementById('modal-next');
  const resultCount   = document.getElementById('result-count');

  if (!grid) return;

  // ─── API helpers ──────────────────────────────────────────────────────────
  async function apiFetch(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`API error ${res.status}: ${url}`);
    return res.json();
  }

  async function apiPost(url, body) {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`API error ${res.status}: ${url}`);
    return res.json();
  }

  async function apiDelete(url) {
    const res = await fetch(url, { method: 'DELETE' });
    if (!res.ok) throw new Error(`API error ${res.status}`);
    return res.json();
  }

  // ─── Load tag suggestions from API ────────────────────────────────────────
  async function loadTagSuggestions() {
    try {
      const data = await apiFetch('/api/tags?sort=count');
      state.tagSuggestions = data.tags.map(t => t.tag);
    } catch (e) {
      state.tagSuggestions = [];
    }
  }

  // ─── Search / load assets from API ────────────────────────────────────────
  async function loadAssets(resetPage = true) {
    if (state.loading) return;
    if (resetPage) {
      state.page = 1;
      state.focusedIndex = null;
    }

    state.loading = true;
    showGridSkeleton();

    const params = new URLSearchParams({
      q:        state.query,
      type:     state.filter,
      sort:     state.sort,
      page:     state.page,
      per_page: 50,
    });
    if (state.dateFrom) params.append('date_from', state.dateFrom);
    if (state.dateTo) params.append('date_to', state.dateTo);

    try {
      const data = await apiFetch(`/api/search?${params}`);
      state.allFiles = data.results;
      state.total = data.total;
      renderGrid(data.results, data.total);
    } catch (e) {
      Toast.error('Failed to load assets. Is the server running?');
      clearGrid();
    } finally {
      state.loading = false;
    }
  }

  // ─── Grid rendering ───────────────────────────────────────────────────────
  function showGridSkeleton() {
    const skeletons = Array.from({ length: 12 }).map(() => `
      <div class="asset-card">
        <div class="asset-card-thumb">
          <div class="skeleton-shimmer" style="position:absolute;inset:0;"></div>
        </div>
        <div class="asset-card-info">
          <div class="skeleton-shimmer" style="height:14px;width:70%;border-radius:4px;margin-bottom:6px;"></div>
          <div class="skeleton-shimmer" style="height:10px;width:40%;border-radius:4px;"></div>
        </div>
      </div>`).join('');
    grid.innerHTML = skeletons;
  }

  function clearGrid() {
    if (resultCount) resultCount.textContent = 'Showing 0 of 0';
    grid.innerHTML = `
      <div style="grid-column:1/-1;text-align:center;padding:var(--space-16);color:var(--text-tertiary);">
        <i data-lucide="search-x" style="width:48px;height:48px;margin-bottom:var(--space-4);opacity:0.4;"></i>
        <p>No assets found. Try a different search.</p>
      </div>`;
    if (window.lucide) lucide.createIcons({ nodes: [grid] });
  }

  function renderGrid(files, total) {
    if (!files.length) { clearGrid(); return; }

    if (resultCount) {
      resultCount.textContent = `Showing ${files.length} of ${total.toLocaleString()}`;
    }

    grid.innerHTML = files.map((f, i) => cardHTML(f, i)).join('') + `
      ${total > state.page * 50 ? `
        <div style="grid-column:1/-1;display:flex;justify-content:center;padding:var(--space-6) 0;">
          <button id="load-more-btn" class="btn btn-secondary">Load More</button>
        </div>` : ''}`;

    if (window.lucide) lucide.createIcons({ nodes: [grid] });

    // Re-attach events
    attachCardEvents();

    // Re-render selection state
    renderSelection();

    // Load more handler
    const loadMoreBtn = document.getElementById('load-more-btn');
    if (loadMoreBtn) {
      loadMoreBtn.addEventListener('click', () => {
        state.page++;
        loadAssetsMore();
      });
    }
  }

  async function loadAssetsMore() {
    if (state.loading) return;
    const loadMoreBtn = document.getElementById('load-more-btn');
    if (loadMoreBtn) loadMoreBtn.textContent = 'Loading...';
    state.loading = true;

    const params = new URLSearchParams({
      q: state.query, type: state.filter, sort: state.sort,
      page: state.page, per_page: 50,
    });
    if (state.dateFrom) params.append('date_from', state.dateFrom);
    if (state.dateTo) params.append('date_to', state.dateTo);
    try {
      const data = await apiFetch(`/api/search?${params}`);
      const newFiles = data.results;
      state.allFiles.push(...newFiles);

      // Remove "load more" + append new cards
      if (loadMoreBtn) loadMoreBtn.parentElement.remove();
      const temp = document.createElement('div');
      temp.innerHTML = newFiles.map((f, i) => cardHTML(f, state.allFiles.length - newFiles.length + i)).join('');
      while (temp.firstChild) grid.insertBefore(temp.firstChild, null);

      if (state.allFiles.length < data.total) {
        const wrapper = document.createElement('div');
        wrapper.style.cssText = 'grid-column:1/-1;display:flex;justify-content:center;padding:var(--space-6) 0;';
        wrapper.innerHTML = '<button id="load-more-btn" class="btn btn-secondary">Load More</button>';
        grid.appendChild(wrapper);
        wrapper.querySelector('button').addEventListener('click', () => { state.page++; loadAssetsMore(); });
      }

      if (window.lucide) lucide.createIcons({ nodes: [grid] });
      attachCardEvents();
      renderSelection();
      if (resultCount) {
        resultCount.textContent = `Showing ${state.allFiles.length} of ${data.total.toLocaleString()}`;
      }
    } catch (e) {
      Toast.error('Failed to load more.');
      if (loadMoreBtn) loadMoreBtn.textContent = 'Load More';
    } finally {
      state.loading = false;
    }
  }

  function cardHTML(file, i) {
    const ext = (file.ext || 'jpg').toLowerCase();
    const isVideo = ['mp4','mov','avi','mkv','mxf'].includes(ext);
    const isPsd   = ['psd','psb','ai'].includes(ext);

    const badgeColor = isVideo ? 'rgba(6,182,212,0.9)' : isPsd ? 'rgba(168,85,247,0.9)' : '';
    const badgeStyle = badgeColor ? `style="background:${badgeColor};"` : '';
    const badgeLabel = isVideo ? (file.duration ? formatDuration(file.duration) : 'VIDEO') : ext.toUpperCase();

    const tagPills = (file.tags || []).slice(0, 3).map(tag =>
      `<span class="tag tag-custom" style="font-size:10px;padding:2px 6px;">${escHtml(tag)}</span>`
    ).join('');

    const isSelected = state.selected.has(file.id);

    return `
      <div class="asset-card${isSelected ? ' selected' : ''}"
           data-file-id="${escHtml(file.id)}"
           data-idx="${i}"
           data-type="${isVideo ? 'video' : isPsd ? 'psd' : 'image'}"
           tabindex="0">
        <label class="asset-card-check">
          <input type="checkbox" ${isSelected ? 'checked' : ''}
                 style="opacity:0;position:absolute;width:100%;height:100%;cursor:pointer;">
          <i data-lucide="check" style="width:14px;height:14px;color:white;"></i>
        </label>
        <div class="asset-card-thumb">
          <img src="/api/thumb/${escHtml(file.id)}" alt="${escHtml(file.filename)}"
               loading="lazy" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;">
          <div class="asset-card-badge" ${badgeStyle}>${badgeLabel}</div>
        </div>
        <div class="asset-card-info">
          <p class="asset-card-name" title="${escHtml(file.filename)}">${escHtml(file.filename)}</p>
          <div style="font-size:var(--text-xs);color:var(--text-tertiary);margin:4px 0 8px;">
            ${file.size_human} · ${file.date || ''}
          </div>
          <div class="asset-card-meta">${tagPills}</div>
        </div>
      </div>`;
  }

  // ─── Card events ──────────────────────────────────────────────────────────
  function attachCardEvents() {
    grid.querySelectorAll('.asset-card[data-file-id]').forEach(card => {
      const fileId = card.dataset.fileId;
      const idx    = parseInt(card.dataset.idx);
      const thumb  = card.querySelector('.asset-card-thumb');
      const check  = card.querySelector('.asset-card-check');

      if (check) {
        check.addEventListener('click', e => {
          e.preventDefault();
          e.stopPropagation();
          toggleSelect(fileId, idx, e.shiftKey);
        });
      }

      if (thumb) {
        thumb.addEventListener('click', e => {
          e.stopPropagation();
          if (e.target.closest('.asset-card-check')) return;
          openDetailModal(fileId);
        });
      }

      card.addEventListener('click', e => {
        if (e.target.closest('.asset-card-thumb') || e.target.closest('.asset-card-check')) return;
        if (state.selected.size > 0 || e.shiftKey) toggleSelect(fileId, idx, e.shiftKey);
      });

      card.addEventListener('focus', () => {
        state.focusedIndex = idx;
      });
    });
  }

  // ─── Selection ────────────────────────────────────────────────────────────
  function toggleSelect(fileId, idx, shiftHeld) {
    if (shiftHeld && state.lastClickedFileId) {
      // Range by visible card index
      const cards = [...grid.querySelectorAll('.asset-card[data-file-id]')];
      const lastIdx = parseInt(
        cards.find(c => c.dataset.fileId === state.lastClickedFileId)?.dataset.idx ?? '-1'
      );
      if (lastIdx >= 0) {
        const lo = Math.min(lastIdx, idx);
        const hi = Math.max(lastIdx, idx);
        cards.forEach(c => {
          const ci = parseInt(c.dataset.idx);
          if (ci >= lo && ci <= hi) state.selected.add(c.dataset.fileId);
        });
      }
    } else {
      if (state.selected.has(fileId)) state.selected.delete(fileId);
      else state.selected.add(fileId);
      state.lastClickedFileId = fileId;
    }
    renderSelection();
  }

  function clearSelection() {
    state.selected.clear();
    state.lastClickedFileId = null;
    renderSelection();
  }

  function renderSelection() {
    grid.querySelectorAll('.asset-card[data-file-id]').forEach(card => {
      const sel = state.selected.has(card.dataset.fileId);
      card.classList.toggle('selected', sel);
      const cb = card.querySelector('input[type=checkbox]');
      if (cb) cb.checked = sel;
    });
    const count = state.selected.size;
    if (selCountEl) selCountEl.textContent = `${count} item${count !== 1 ? 's' : ''} selected`;
    if (selectionBar) selectionBar.classList.toggle('visible', count > 0);
  }

  // ─── Selection bar buttons ────────────────────────────────────────────────
  if (clearSelBtn) clearSelBtn.addEventListener('click', clearSelection);

  if (batchTagBtn) batchTagBtn.addEventListener('click', openBatchTagModal);

  if (batchDlBtn) {
    batchDlBtn.addEventListener('click', async () => {
      if (state.selected.size === 0) return;
      const fileIds = [...state.selected];
      Toast.info(`Starting download of ${fileIds.length} file(s)...`);
      
      try {
        const res = await fetch('/api/batch/download', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ file_ids: fileIds })
        });
        if (!res.ok) {
          const err = await safeJson(res);
          throw new Error(err?.error || 'Batch download failed.');
        }
        
        // Trigger download via blob
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `1011_Media_Batch_${new Date().getTime()}.zip`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        
        clearSelection();
      } catch (e) {
        Toast.error(e.message || 'Batch download failed.');
      }
    });
  }

  if (batchColBtn) {
    batchColBtn.addEventListener('click', () => {
      if (state.selected.size > 0) openCollectionPicker([...state.selected]);
    });
  }

  // ─── Filter chips ─────────────────────────────────────────────────────────
  filterChips.forEach(chip => {
    chip.addEventListener('click', () => {
      filterChips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      state.filter = chip.dataset.filter || 'all';
      loadAssets();
    });
  });

  // ─── Date Range Picker ───────────────────────────────────────────────────
  const dateBtn     = document.getElementById('date-range-btn');
  const datePopover = document.getElementById('date-range-popover');
  const dateApply   = document.getElementById('date-range-apply');
  const dateClear   = document.getElementById('date-range-clear');
  const dateFromInp = document.getElementById('date-from-input');
  const dateToInp   = document.getElementById('date-to-input');

  if (dateBtn && datePopover) {
    dateBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const isVisible = datePopover.style.display === 'block';
      datePopover.style.display = isVisible ? 'none' : 'block';
    });
    
    document.addEventListener('click', (e) => {
      if (!datePopover.contains(e.target) && !dateBtn.contains(e.target)) {
        datePopover.style.display = 'none';
      }
    });

    dateApply.addEventListener('click', () => {
      state.dateFrom = dateFromInp.value;
      state.dateTo = dateToInp.value;
      
      if (state.dateFrom || state.dateTo) {
        dateBtn.classList.replace('btn-secondary', 'btn-primary');
        dateBtn.innerHTML = `<i data-lucide="calendar"></i> ${state.dateFrom||'Start'} – ${state.dateTo||'End'}`;
      } else {
        dateBtn.classList.replace('btn-primary', 'btn-secondary');
        dateBtn.innerHTML = `<i data-lucide="calendar"></i> Date Range`;
      }
      if (window.lucide) lucide.createIcons({nodes: [dateBtn]});
      datePopover.style.display = 'none';
      loadAssets();
    });

    dateClear.addEventListener('click', () => {
      dateFromInp.value = '';
      dateToInp.value = '';
      state.dateFrom = '';
      state.dateTo = '';
      dateBtn.classList.replace('btn-primary', 'btn-secondary');
      dateBtn.innerHTML = `<i data-lucide="calendar"></i> Date Range`;
      if (window.lucide) lucide.createIcons({nodes: [dateBtn]});
      datePopover.style.display = 'none';
      loadAssets();
    });
  }

  // ─── Sort ─────────────────────────────────────────────────────────────────
  if (sortSelect) {
    sortSelect.addEventListener('change', () => {
      state.sort = sortSelect.value;
      loadAssets();
    });
  }

  // ─── View toggle ──────────────────────────────────────────────────────────
  viewBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      viewBtns.forEach(b => b.classList.toggle('active', b === btn));
      grid.classList.toggle('asset-list', btn.dataset.view === 'list');
      grid.classList.toggle('asset-grid', btn.dataset.view === 'grid');
    });
  });

  // ─── Search input ─────────────────────────────────────────────────────────
  let searchDebounce;
  if (searchInput) {
    searchInput.addEventListener('input', () => {
      clearTimeout(searchDebounce);
      searchDebounce = setTimeout(() => {
        state.query = searchInput.value.trim();
        loadAssets();
      }, 300);
    });
  }

  // ─── Keyboard shortcuts ───────────────────────────────────────────────────
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && !document.querySelector('.modal-open')) clearSelection();
    if (detailModal?.classList.contains('modal-open')) {
      if (e.key === 'ArrowLeft')  navigateModal(-1);
      if (e.key === 'ArrowRight') navigateModal(1);
      return;
    }

    if (isEditableTarget(e.target)) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        searchInput?.focus();
      }
      return;
    }

    if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(e.key)) {
      e.preventDefault();
      if (e.key === 'ArrowLeft') moveGridFocus(-1);
      if (e.key === 'ArrowRight') moveGridFocus(1);
      if (e.key === 'ArrowUp') moveGridFocus(-estimateGridColumns());
      if (e.key === 'ArrowDown') moveGridFocus(estimateGridColumns());
    }

    if (e.key === 'Enter') {
      const card = document.activeElement?.closest?.('.asset-card[data-file-id]');
      if (card) {
        e.preventDefault();
        openDetailModal(card.dataset.fileId);
      }
    }

    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      searchInput?.focus();
    }
  });

  // ─── Detail modal ─────────────────────────────────────────────────────────
  async function openDetailModal(fileId) {
    ModalManager.open('detail-modal');
    setModalLoading(true);
    try {
      const file = await apiFetch(`/api/file/${fileId}`);
      state.currentFile = file;
      renderDetailModal(file);
    } catch (e) {
      Toast.error('Could not load file details.');
      ModalManager.close('detail-modal');
    } finally {
      setModalLoading(false);
    }
  }

  function setModalLoading(loading) {
    const body = detailModal?.querySelector('.metadata-sidebar');
    if (body) body.style.opacity = loading ? '0.5' : '1';
  }

  function renderDetailModal(file) {
    const nameEl   = detailModal.querySelector('#modal-filename');
    const metaEl   = detailModal.querySelector('#modal-meta');
    const pathEl   = detailModal.querySelector('#modal-path');
    const exifBody = detailModal.querySelector('#modal-exif-body');
    const preview  = detailModal.querySelector('#modal-preview-img');
    const icon     = detailModal.querySelector('#modal-preview-icon');

    if (nameEl) nameEl.textContent = file.filename;
    if (metaEl) {
      const dims = (file.width && file.height) ? ` · ${file.width}×${file.height}` : '';
      const dur  = file.duration ? ` · ${formatDuration(file.duration)}` : '';
      metaEl.textContent = `${file.size_human}${dims}${dur} · ${file.type_label}`;
    }
    if (pathEl) pathEl.textContent = file.path;

    // EXIF-style metadata table
    if (exifBody) {
      const rows = {
        'Date': file.date,
        'Folder': file.folder,
        'Extension': file.type_label,
      };
      if (file.width)    rows['Dimensions'] = `${file.width} × ${file.height} px`;
      if (file.duration) rows['Duration']   = formatDuration(file.duration);

      exifBody.innerHTML = Object.entries(rows).filter(([,v]) => v).map(([k, v]) =>
        `<tr>
          <td style="color:var(--text-secondary);width:40%;font-size:var(--text-xs);padding:4px 0;">${k}</td>
          <td style="font-size:var(--text-sm);padding:4px 0;text-align:right;">${escHtml(String(v))}</td>
        </tr>`
      ).join('');
    }

    // Preview image
    if (preview) {
        preview.style.display = 'block';
        preview.src = `/api/thumb/${file.id}`;
    }
    if (icon) {
        icon.style.display = 'none';
    }

    // Connect detail modal meta actions
    const dlBtn = detailModal.querySelector('#modal-download-btn');
    if (dlBtn) {
        const newDlBtn = dlBtn.cloneNode(true);
        dlBtn.parentNode.replaceChild(newDlBtn, dlBtn);
        if (file.available) {
          newDlBtn.innerHTML = '<i data-lucide="download"></i> Download Original';
        } else {
          newDlBtn.innerHTML = '<i data-lucide="download"></i> Original Unavailable';
        }
        newDlBtn.addEventListener('click', async () => {
          if (!file.available) {
            Toast.info('Original file is unavailable in demo mode.');
            return;
          }
          await downloadOriginal(file.id, file.filename);
        });
        if (window.lucide) lucide.createIcons({ nodes: [newDlBtn] });
    }

    const addColBtn = detailModal.querySelector('#modal-add-collection-btn');
    if (addColBtn) {
        const newColBtn = addColBtn.cloneNode(true);
        addColBtn.parentNode.replaceChild(newColBtn, addColBtn);
        newColBtn.addEventListener('click', () => openCollectionPicker([file.id]));
    }

    // Tag input (destroy previous instance first)
    const tagContainer = detailModal.querySelector('#modal-tag-input-container');
    if (tagContainer) {
      if (state.tagInput) state.tagInput.destroy();

      const initialTags = (file.tags || []).map(t =>
        typeof t === 'string' ? t : t.tag
      );

      state.tagInput = new TagInput(tagContainer, {
        initialTags,
        suggestions: state.tagSuggestions,
        placeholder: 'Add tag…',
        onAdd: async (tag) => {
          try {
            await apiPost(`/api/file/${file.id}/tags`, { tag });
            Toast.success(`Tag "${tag}" added`);
            // Update local cache
            if (!state.tagSuggestions.includes(tag)) state.tagSuggestions.push(tag);
          } catch (e) {
            Toast.error(`Could not add tag "${tag}"`);
          }
        },
        onRemove: async (tag) => {
          try {
            await apiDelete(`/api/file/${file.id}/tags/${encodeURIComponent(tag)}`);
            Toast.info(`Tag "${tag}" removed`);
          } catch (e) {
            Toast.error(`Could not remove tag "${tag}"`);
          }
        },
      });
    }
  }

  function navigateModal(dir) {
    if (!state.currentFile) return;
    const idx = state.allFiles.findIndex(f => f.id === state.currentFile.id);
    const nextIdx = idx + dir;
    if (nextIdx < 0 || nextIdx >= state.allFiles.length) return;
    const nextFile = state.allFiles[nextIdx];
    openDetailModal(nextFile.id);
  }

  if (prevBtn) prevBtn.addEventListener('click', () => navigateModal(-1));
  if (nextBtn) nextBtn.addEventListener('click', () => navigateModal(1));

  // ─── Batch Tag Modal ──────────────────────────────────────────────────────
  function openBatchTagModal() {
    if (!document.getElementById('batch-tag-modal')) {
      Toast.info('Batch tag modal not in DOM');
      return;
    }

    const container = document.getElementById('batch-tag-input-container');
    if (!container) return;
    container.innerHTML = '';

    const bti = new TagInput(container, {
      suggestions: state.tagSuggestions,
      placeholder: 'Add tags to all selected…',
    });

    const applyBtn = document.querySelector('[data-batch-apply]');
    if (applyBtn) {
      applyBtn.onclick = async () => {
        const tags = bti.getTags();
        if (!tags.length) { Toast.warning('Add at least one tag first.'); return; }

        applyBtn.disabled = true;
        applyBtn.textContent = 'Applying…';
        try {
          const result = await apiPost('/api/batch/tags', {
            file_ids: [...state.selected],
            tags,
          });
          Toast.success(`Applied ${tags.length} tag(s) to ${result.tagged_files} files`);
          clearSelection();
          ModalManager.close('batch-tag-modal');
          loadAssets();
        } catch (e) {
          Toast.error('Batch tag failed. Please try again.');
        } finally {
          applyBtn.disabled = false;
          applyBtn.innerHTML = '<i data-lucide="tag"></i> Apply Tags';
          if (window.lucide) lucide.createIcons({ nodes: [applyBtn] });
        }
      };
    }

    ModalManager.open('batch-tag-modal');
  }

  // ─── Collection Picker Modal ──────────────────────────────────────────────
  async function openCollectionPicker(fileIds) {
    const listEl = document.getElementById('collection-picker-list');
    if (!listEl) return;
    
    listEl.innerHTML = `
        <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
            <div class="skeleton-shimmer" style="width: 100%; height: 60px; border-radius: var(--radius-md);"></div>
        </div>`;
    
    ModalManager.open('collection-picker-modal');
    
    try {
        const data = await apiFetch('/api/collections');
        const cols = data.collections || [];
        
        if (cols.length === 0) {
            listEl.innerHTML = `<p class="text-tertiary" style="text-align:center; margin-top:20px;">No collections found.</p>`;
        } else {
            listEl.innerHTML = cols.map(c => `
                <div class="collection-picker-item" data-col-id="${c.id}" 
                     style="display:flex; align-items:center; padding:var(--space-3); margin-bottom:var(--space-2); border:1px solid var(--border-default); border-radius:var(--radius-md); cursor:pointer; background:var(--bg-elevated); transition:background 0.2s;">
                    <i data-lucide="folder" class="text-accent" style="margin-right:var(--space-3);"></i>
                    <div style="flex:1;">
                        <div class="font-poppins font-medium text-primary">${escHtml(c.name)}</div>
                        <div class="text-tertiary" style="font-size:var(--text-xs);">${c.item_count || 0} items</div>
                    </div>
                </div>
            `).join('');
            
            if (window.lucide) lucide.createIcons({nodes: [listEl]});
            
            listEl.querySelectorAll('.collection-picker-item').forEach(item => {
                item.addEventListener('click', async () => {
                    const colId = item.dataset.colId;
                    item.style.opacity = '0.5';
                    try {
                        const result = await apiPost(`/api/collections/${colId}/items`, { file_ids: fileIds });
                        if (result.added > 0) {
                          Toast.success(`Added ${result.added} new item(s) to collection`);
                        } else {
                          Toast.info('All selected items are already in this collection.');
                        }
                        ModalManager.close('collection-picker-modal');
                        clearSelection();
                    } catch(e) {
                        Toast.error("Failed to add to collection.");
                        item.style.opacity = '1';
                    }
                });
            });
        }
    } catch(e) {
        listEl.innerHTML = `<p class="text-error" style="text-align:center; margin-top:20px;">Failed to load collections.</p>`;
    }
  }

  const pickerNewBtn = document.getElementById('collection-picker-create-new');
  if (pickerNewBtn) {
      pickerNewBtn.addEventListener('click', () => {
          ModalManager.close('collection-picker-modal');
          window.location.href = '/collections';
      });
  }

  // ─── Utilities ────────────────────────────────────────────────────────────
  function escHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function formatDuration(seconds) {
    seconds = Math.round(seconds);
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${String(s).padStart(2, '0')}`;
  }

  function getVisibleCards() {
    return [...grid.querySelectorAll('.asset-card[data-file-id]')];
  }

  function estimateGridColumns() {
    const cards = getVisibleCards();
    if (cards.length <= 1) return 1;
    const firstTop = cards[0].offsetTop;
    let cols = 0;
    for (const card of cards) {
      if (card.offsetTop !== firstTop) break;
      cols += 1;
    }
    return Math.max(cols, 1);
  }

  function moveGridFocus(delta) {
    const cards = getVisibleCards();
    if (!cards.length) return;

    const activeCard = document.activeElement?.closest?.('.asset-card[data-file-id]');
    let currentIdx = activeCard ? Number(activeCard.dataset.idx) : state.focusedIndex;
    if (!Number.isInteger(currentIdx)) currentIdx = 0;

    const nextIdx = Math.max(0, Math.min(cards.length - 1, currentIdx + delta));
    const nextCard = cards.find(card => Number(card.dataset.idx) === nextIdx) || cards[nextIdx];
    if (nextCard) {
      nextCard.focus();
      state.focusedIndex = Number(nextCard.dataset.idx);
    }
  }

  function isEditableTarget(target) {
    return Boolean(
      target?.closest?.('input, textarea, select, button, [contenteditable="true"], .tag-autocomplete')
    );
  }

  async function downloadOriginal(fileId, filename) {
    try {
      const res = await fetch(`/api/download/${fileId}`);
      if (!res.ok) {
        const err = await safeJson(res);
        throw new Error(err?.error || 'Original file is unavailable in demo mode.');
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename || 'asset';
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      Toast.info(e.message || 'Original file is unavailable in demo mode.');
    }
  }

  async function safeJson(response) {
    try {
      return await response.json();
    } catch (_) {
      return null;
    }
  }

  // ─── Init ─────────────────────────────────────────────────────────────────
  async function init() {
    await loadTagSuggestions();
    await loadAssets();
  }

  init();
  window._searchState = state;
});
