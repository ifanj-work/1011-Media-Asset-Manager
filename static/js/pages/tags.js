/**
 * 1011 Media Asset Manager — Tag Management Page
 * All data fetched from /api/tags and /api/tags/categories
 */

document.addEventListener('DOMContentLoaded', () => {

  // ─── Elements ─────────────────────────────────────────────────────────────
  const tableBody     = document.querySelector('#tags-table tbody');
  const filterInput   = document.getElementById('tag-filter-input');
  const categoryLinks = document.querySelectorAll('[data-category-filter]');
  const addTagBtn     = document.getElementById('add-tag-btn');
  const mergeTagBtn   = document.getElementById('merge-tags-btn');
  const addTagModal   = document.getElementById('add-tag-modal');
  const mergeTagModal = document.getElementById('merge-tag-modal');
  const countDisplay  = document.getElementById('tag-count-display');
  const analyticsMostUsed = document.getElementById('tag-analytics-most-used');
  const analyticsUnused = document.getElementById('tag-analytics-unused');

  if (!tableBody) return;

  // ─── State ────────────────────────────────────────────────────────────────
  const state = {
    allTags: [],
    activeCategory: 'all',
    sort: 'count',
  };

  // ─── API ──────────────────────────────────────────────────────────────────
  async function apiFetch(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`API ${res.status}`);
    return res.json();
  }
  async function apiPost(url, body) {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`API ${res.status}`);
    return res.json();
  }
  async function apiDelete(url) {
    const res = await fetch(url, { method: 'DELETE' });
    if (!res.ok) throw new Error(`API ${res.status}`);
    return res.json();
  }

  // ─── Load & render tags ───────────────────────────────────────────────────
  async function loadTags() {
    showSkeleton();
    try {
      const params = new URLSearchParams({ sort: state.sort });
      if (state.activeCategory !== 'all') params.set('category', state.activeCategory);
      const data = await apiFetch(`/api/tags?${params}`);
      state.allTags = data.tags;
      renderTagTable(data.tags);
      updateCategoryCounts();
      loadTagAnalytics();
    } catch (e) {
      Toast.error('Failed to load tags from server.');
    }
  }

  async function loadTagAnalytics() {
    if (!analyticsMostUsed || !analyticsUnused) return;
    try {
      const data = await apiFetch('/api/tags/analytics');
      analyticsMostUsed.innerHTML = (data.most_used || []).slice(0, 5).map(tag => `
        <div style="display:flex;justify-content:space-between;align-items:center;gap:var(--space-2);">
          <span class="tag tag-${escHtml(tag.category)}">${escHtml(tag.tag)}</span>
          <span class="text-tertiary" style="font-size:var(--text-xs);">${Number(tag.count || 0).toLocaleString()}</span>
        </div>
      `).join('') || '<p class="text-tertiary" style="font-size:var(--text-sm);">No tag usage yet.</p>';

      analyticsUnused.innerHTML = (data.unused || []).slice(0, 5).map(tag => `
        <div style="display:flex;justify-content:space-between;align-items:center;gap:var(--space-2);">
          <span class="tag tag-${escHtml(tag.category)}">${escHtml(tag.tag)}</span>
          <span class="text-tertiary" style="font-size:var(--text-xs);">unused</span>
        </div>
      `).join('') || '<p class="text-tertiary" style="font-size:var(--text-sm);">No unused vocabulary tags.</p>';
    } catch (_) {
      analyticsMostUsed.innerHTML = '<p class="text-tertiary" style="font-size:var(--text-sm);">Could not load analytics.</p>';
      analyticsUnused.innerHTML = '<p class="text-tertiary" style="font-size:var(--text-sm);">Could not load analytics.</p>';
    }
  }

  function showSkeleton() {
    tableBody.innerHTML = Array.from({ length: 8 }).map(() => `
      <tr>
        <td><div class="skeleton-shimmer" style="height:22px;width:80px;border-radius:var(--radius-pill);"></div></td>
        <td><div class="skeleton-shimmer" style="height:14px;width:60px;border-radius:4px;"></div></td>
        <td><div class="skeleton-shimmer" style="height:14px;width:80px;border-radius:4px;"></div></td>
        <td></td>
      </tr>`).join('');
  }

  function renderTagTable(tags) {
    const query = filterInput ? filterInput.value.trim().toLowerCase() : '';
    const filtered = query ? tags.filter(t => t.tag.includes(query)) : tags;

    if (!filtered.length) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="4" style="text-align:center;padding:var(--space-10);color:var(--text-tertiary);">
            No tags found.
          </td>
        </tr>`;
      updateCount(0, 0);
      return;
    }

    const maxCount = Math.max(...filtered.map(t => t.count), 1);
    tableBody.innerHTML = filtered.map(t => {
      const pct = Math.round((t.count / maxCount) * 100);
      return `
        <tr data-tag="${escHtml(t.tag)}" data-category="${escHtml(t.category)}">
          <td><span class="tag tag-${escHtml(t.category)}">${escHtml(t.tag)}</span></td>
          <td><span class="text-secondary" style="font-size:var(--text-sm);">${capitalize(t.category)}</span></td>
          <td>
            <div style="display:flex;align-items:center;gap:var(--space-3);">
              <span class="font-mono" style="font-size:var(--text-sm);min-width:40px;">${t.count.toLocaleString()}</span>
              <div style="flex:1;height:4px;background:var(--bg-hover);border-radius:2px;max-width:120px;">
                <div style="height:100%;background:var(--color-accent);border-radius:2px;width:${pct}%;transition:width 0.4s;"></div>
              </div>
            </div>
          </td>
          <td style="text-align:right;">
            <button class="btn btn-icon btn-ghost btn-sm" data-edit-tag="${escHtml(t.tag)}" aria-label="Edit ${escHtml(t.tag)}">
              <i data-lucide="edit-2"></i>
            </button>
            <button class="btn btn-icon btn-ghost btn-sm" style="color:var(--color-error);" data-delete-tag="${escHtml(t.tag)}" aria-label="Delete ${escHtml(t.tag)}">
              <i data-lucide="trash-2"></i>
            </button>
          </td>
        </tr>`;
    }).join('');

    if (window.lucide) lucide.createIcons({ nodes: [tableBody] });
    updateCount(filtered.length, tags.length);
    attachRowActions();
  }

  function updateCount(visible, total) {
    if (countDisplay) {
      countDisplay.textContent = visible === total
        ? `${total} tag${total !== 1 ? 's' : ''}`
        : `Showing ${visible} of ${total} tags`;
    }
  }

  async function updateCategoryCounts() {
    try {
      const data = await apiFetch('/api/tags/categories');
      const totals = {};
      data.categories.forEach(c => { totals[c.name] = c.count; });
      const allTotal = Object.values(totals).reduce((a, b) => a + b, 0);

      categoryLinks.forEach(link => {
        const cat = link.dataset.categoryFilter;
        const countEl = link.querySelector('.cat-count');
        if (countEl) {
          countEl.textContent = cat === 'all' ? allTotal : (totals[cat] ?? 0);
        }
      });
    } catch (e) { /* non-critical */ }
  }

  // ─── Row actions: delete / edit ───────────────────────────────────────────
  function attachRowActions() {
    tableBody.querySelectorAll('[data-delete-tag]').forEach(btn => {
      btn.addEventListener('click', e => {
        e.stopPropagation();
        const tag = btn.dataset.deleteTag;
        const confirmed = btn.dataset.confirming === 'true';

        if (!confirmed) {
          btn.dataset.confirming = 'true';
          btn.title = 'Click again to confirm';
          btn.style.background = 'var(--color-error-subtle)';
          setTimeout(() => {
            btn.dataset.confirming = '';
            btn.style.background = '';
          }, 2500);
        } else {
          deleteTag(tag, btn.closest('tr'));
        }
      });
    });

    tableBody.querySelectorAll('[data-edit-tag]').forEach(btn => {
      btn.addEventListener('click', () => {
        Toast.info(`Inline rename coming in Phase 3 — use Merge Tags for now.`);
      });
    });
  }

  async function deleteTag(tag, row) {
    row.style.transition = 'opacity 0.2s';
    row.style.opacity = '0';
    try {
      const res = await apiDelete(`/api/tags/${encodeURIComponent(tag)}`);
      Toast.success(`Tag "${tag}" deleted — ${res.files_affected} file(s) updated`);
      setTimeout(() => { loadTags(); }, 200);
    } catch (e) {
      row.style.opacity = '1';
      Toast.error(`Could not delete tag "${tag}"`);
    }
  }

  // ─── Category sidebar filter ──────────────────────────────────────────────
  categoryLinks.forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      categoryLinks.forEach(l => l.classList.remove('active'));
      link.classList.add('active');
      state.activeCategory = link.dataset.categoryFilter;
      loadTags();
    });
  });

  // ─── Live search filter ───────────────────────────────────────────────────
  let filterDebounce;
  if (filterInput) {
    filterInput.addEventListener('input', () => {
      clearTimeout(filterDebounce);
      filterDebounce = setTimeout(() => renderTagTable(state.allTags), 200);
    });
  }

  // ─── Sort ─────────────────────────────────────────────────────────────────
  const sortSelect = document.getElementById('tags-sort-select');
  if (sortSelect) {
    sortSelect.addEventListener('change', () => {
      state.sort = sortSelect.value;
      loadTags();
    });
  }

  // ─── Add Tag Modal ────────────────────────────────────────────────────────
  if (addTagBtn) addTagBtn.addEventListener('click', () => ModalManager.open('add-tag-modal'));

  if (addTagModal) {
    const saveBtn       = addTagModal.querySelector('[data-save-tag]');
    const tagNameInput  = addTagModal.querySelector('#new-tag-name');
    const catSelect     = addTagModal.querySelector('#new-tag-category');

    if (saveBtn) {
      saveBtn.addEventListener('click', async () => {
        const name = (tagNameInput?.value || '').trim().toLowerCase().replace(/\s+/g, '-');
        const category = catSelect?.value || 'custom';
        if (!name) { Toast.warning('Enter a tag name.'); return; }

        saveBtn.disabled = true;
        saveBtn.textContent = 'Saving...';
        try {
          const res = await apiPost('/api/tags', { tag: name, category });
          Toast.success(
            res.created
              ? `Tag "${name}" added to vocabulary`
              : `Tag "${name}" already exists in the vocabulary`
          );
          if (tagNameInput) tagNameInput.value = '';
          ModalManager.close('add-tag-modal');
          await loadTags();
        } catch (e) {
          Toast.error('Could not create tag. Please try again.');
        } finally {
          saveBtn.disabled = false;
          saveBtn.innerHTML = '<i data-lucide="plus"></i> Create Tag';
          if (window.lucide) lucide.createIcons({ nodes: [saveBtn] });
        }
      });
    }
  }

  // ─── Merge Tags Modal ─────────────────────────────────────────────────────
  if (mergeTagBtn) mergeTagBtn.addEventListener('click', () => ModalManager.open('merge-tag-modal'));

  if (mergeTagModal) {
    const confirmBtn = mergeTagModal.querySelector('[data-confirm-merge]');
    const sourceIn   = mergeTagModal.querySelector('#merge-source');
    const targetIn   = mergeTagModal.querySelector('#merge-target');

    if (confirmBtn) {
      confirmBtn.addEventListener('click', async () => {
        const source = (sourceIn?.value || '').trim();
        const target = (targetIn?.value || '').trim();
        if (!source || !target) { Toast.warning('Both source and target are required.'); return; }
        if (source === target) { Toast.warning('Source and target must be different.'); return; }

        confirmBtn.disabled = true;
        confirmBtn.textContent = 'Merging…';
        try {
          const res = await apiPost('/api/tags/merge', { source, target });
          Toast.success(`Merged "${source}" → "${target}" across ${res.files_affected} file(s)`);
          if (sourceIn) sourceIn.value = '';
          if (targetIn) targetIn.value = '';
          ModalManager.close('merge-tag-modal');
          await loadTags();
        } catch (e) {
          Toast.error('Merge failed. Please try again.');
        } finally {
          confirmBtn.disabled = false;
          confirmBtn.innerHTML = '<i data-lucide="merge"></i> Confirm Merge';
          if (window.lucide) lucide.createIcons({ nodes: [confirmBtn] });
        }
      });
    }
  }

  // ─── Utilities ────────────────────────────────────────────────────────────
  function escHtml(str) {
    return String(str || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function capitalize(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : s; }

  // ─── Init ─────────────────────────────────────────────────────────────────
  loadTags();
});
