/**
 * 1011 Media Asset Manager — Collections Page
 * All data fetched from /api/collections
 */

document.addEventListener('DOMContentLoaded', () => {

  // ─── Elements ─────────────────────────────────────────────────────────────
  const grid          = document.getElementById('collections-grid');
  const newColBtn     = document.getElementById('new-collection-btn');
  const createCard    = document.getElementById('create-collection-card');
  const newColModal   = document.getElementById('new-collection-modal');
  const searchInput   = document.getElementById('collection-search');
  const sortSelect    = document.getElementById('collection-sort');

  // ─── State ────────────────────────────────────────────────────────────────
  const state = { collections: [] };

  // ─── API helpers ──────────────────────────────────────────────────────────
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

  // ─── Load collections ─────────────────────────────────────────────────────
  async function loadCollections() {
    showLoadingState();
    try {
      const data = await apiFetch('/api/collections');
      state.collections = data.collections;
      renderCollections(data.collections);
    } catch (e) {
      Toast.error('Failed to load collections.');
      renderEmptyState();
    }
  }

  function showLoadingState() {
    if (!grid) return;
    // Remove existing cards (keep create placeholder)
    grid.querySelectorAll('.collection-card:not(#create-collection-card)').forEach(c => c.remove());
    // Show skeleton
    const skeletons = Array.from({ length: 3 }).map(() => `
      <div class="card" style="padding:0;overflow:hidden;min-height:280px;">
        <div class="skeleton-shimmer" style="height:160px;"></div>
        <div style="padding:var(--space-4);">
          <div class="skeleton-shimmer" style="height:18px;width:60%;border-radius:4px;margin-bottom:var(--space-2);"></div>
          <div class="skeleton-shimmer" style="height:12px;width:80%;border-radius:4px;margin-bottom:var(--space-2);"></div>
          <div class="skeleton-shimmer" style="height:12px;width:40%;border-radius:4px;"></div>
        </div>
      </div>`).join('');
    const placeholder = document.getElementById('create-collection-card');
    const temp = document.createElement('div');
    temp.innerHTML = skeletons;
    while (temp.firstChild) {
      grid.insertBefore(temp.firstChild, placeholder);
    }
  }

  function renderEmptyState() {
    if (!grid) return;
    grid.querySelectorAll('.skeleton-shimmer, .card:not(#create-collection-card)').forEach(c => c.closest('.card')?.remove());
  }

  function renderCollections(collections) {
    if (!grid) return;
    // Clear skeletons and old cards
    grid.querySelectorAll('.card:not(#create-collection-card), .collection-card:not(#create-collection-card)').forEach(c => c.remove());

    const placeholder = document.getElementById('create-collection-card');

    collections.forEach(col => {
      const card = buildCollectionCard(col);
      grid.insertBefore(card, placeholder);
    });

    if (window.lucide) lucide.createIcons({ nodes: [grid] });
  }

  function buildCollectionCard(col) {
    const card = document.createElement('div');
    card.className = 'card collection-card';
    card.dataset.id   = col.id;
    card.dataset.name = (col.name || '').toLowerCase();
    card.style.cssText = 'padding:0;cursor:pointer;transition:transform var(--duration-fast);';
    card.dataset.collectionName = col.name;

    const updatedLabel = formatRelativeTime(col.updated_at);
    const count = col.item_count ?? 0;

    const cover = col.cover_thumbnail_url || (col.cover_file_id ? `/api/thumb/${col.cover_file_id}` : null);
    card.innerHTML = `
      <div style="height:160px;display:grid;grid-template-columns:2fr 1fr;grid-template-rows:1fr 1fr;
                  gap:2px;padding:2px;border-radius:var(--radius-md) var(--radius-md) 0 0;overflow:hidden;">
        <div style="background:var(--bg-hover);grid-row:1/3;display:flex;align-items:center;
                    justify-content:center;flex-direction:column;gap:8px;">
          ${cover ? `<img src="${escHtml(cover)}" alt="${escHtml(col.name)}" style="width:100%;height:100%;object-fit:cover;">` : `<div style="display:flex;align-items:center;justify-content:center;flex-direction:column;gap:8px;height:100%;width:100%;">
            <i data-lucide="folder-open" style="width:40px;height:40px;color:var(--color-accent);opacity:0.5;"></i>
            <span style="font-size:var(--text-xs);color:var(--text-tertiary);">${count} item${count !== 1 ? 's' : ''}</span>
          </div>`}
        </div>
        <div style="background:var(--bg-surface);display:flex;align-items:center;justify-content:center;">
          <i data-lucide="image" style="opacity:0.2;"></i>
        </div>
        <div style="background:var(--bg-elevated);display:flex;align-items:center;justify-content:center;">
          <i data-lucide="video" style="opacity:0.2;"></i>
        </div>
      </div>
      <div style="padding:var(--space-4);">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:var(--space-1);">
          <h3 class="font-poppins text-primary" style="font-weight:500;font-size:var(--text-base);
              overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:180px;"
              title="${escHtml(col.name)}">${escHtml(col.name)}</h3>
          <button class="btn btn-icon btn-ghost btn-sm text-tertiary collection-menu-btn"
                  style="margin:-6px -6px 0 0;flex-shrink:0;" aria-label="Options">
            <i data-lucide="more-vertical"></i>
          </button>
        </div>
        <p class="text-secondary" style="font-size:var(--text-sm);line-height:1.4;margin-bottom:var(--space-3);
            display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">
          ${escHtml(col.description || 'No description.')}
        </p>
        <div style="display:flex;justify-content:space-between;align-items:center;
                    color:var(--text-tertiary);font-size:var(--text-xs);">
          <div style="display:flex;align-items:center;gap:4px;">
            <i data-lucide="files" style="width:14px;height:14px;"></i> ${count.toLocaleString()} items
          </div>
          <span>${escHtml(updatedLabel)}</span>
        </div>
      </div>`;

    card.addEventListener('click', (e) => {
      // Don't navigate if clicking the menu button
      if (e.target.closest('.collection-menu-btn')) return;
      window.location.href = `/collections/${col.id}`;
    });

    attachMenuBtn(card, col);
    return card;
  }

  // ─── Context menu ─────────────────────────────────────────────────────────
  let activeMenu = null;

  function closeActiveMenu() {
    if (activeMenu) { activeMenu.remove(); activeMenu = null; }
  }

  document.addEventListener('click', closeActiveMenu);

  function attachMenuBtn(card, col) {
    const btn = card.querySelector('.collection-menu-btn');
    if (!btn) return;

    btn.addEventListener('click', e => {
      e.stopPropagation();
      closeActiveMenu();

      const menu = document.createElement('div');
      menu.className = 'context-menu';
      menu.innerHTML = `
        <button class="context-menu-item" data-action="view">
          <i data-lucide="folder-open"></i> Open
        </button>
        <div style="height:1px;background:var(--border-default);margin:4px 0;"></div>
        <button class="context-menu-item" data-action="delete" style="color:var(--color-error);">
          <i data-lucide="trash-2"></i> Delete
        </button>`;

      const rect = btn.getBoundingClientRect();
      menu.style.cssText = `
        position:fixed;
        top:${rect.bottom + 4}px;
        right:${window.innerWidth - rect.right}px;
        background:var(--bg-elevated);
        border:1px solid var(--border-default);
        border-radius:var(--radius-button);
        padding:4px;min-width:160px;
        z-index:var(--z-dropdown);
        box-shadow:var(--shadow-3);`;

      document.body.appendChild(menu);
      activeMenu = menu;
      if (window.lucide) lucide.createIcons({ nodes: [menu] });

      menu.querySelector('[data-action="view"]').addEventListener('click', () => {
        window.location.href = `/collections/${col.id}`;
        closeActiveMenu();
      });

      menu.querySelector('[data-action="delete"]').addEventListener('click', () => {
        deleteCollection(col.id, col.name, card);
        closeActiveMenu();
      });

      // Close on outside click (already handled by document listener)
    });
  }

  async function deleteCollection(id, name, card) {
    card.style.transition = 'opacity 0.2s, transform 0.2s';
    card.style.opacity = '0';
    card.style.transform = 'scale(0.95)';
    try {
      await apiDelete(`/api/collections/${id}`);
      setTimeout(() => {
        card.remove();
        state.collections = state.collections.filter(c => c.id !== id);
      }, 200);
      Toast.success(`Collection "${name}" deleted`);
    } catch (e) {
      card.style.opacity = '1';
      card.style.transform = '';
      Toast.error(`Could not delete "${name}"`);
    }
  }

  // ─── New Collection Modal ─────────────────────────────────────────────────
  function openNewCollectionModal() {
    if (!newColModal) { Toast.error('Modal not found.'); return; }
    ModalManager.open('new-collection-modal');
  }

  if (newColBtn)  newColBtn.addEventListener('click',  openNewCollectionModal);
  if (createCard) createCard.addEventListener('click', openNewCollectionModal);

  if (newColModal) {
    const saveBtn   = newColModal.querySelector('[data-save-collection]');
    const nameInput = newColModal.querySelector('#collection-name-input');
    const descInput = newColModal.querySelector('#collection-desc-input');

    if (saveBtn) {
      saveBtn.addEventListener('click', async () => {
        const name = (nameInput?.value || '').trim();
        const desc = (descInput?.value || '').trim();
        if (!name) { Toast.warning('Enter a collection name.'); return; }

        saveBtn.disabled = true;
        saveBtn.textContent = 'Creating…';
        try {
          const col = await apiPost('/api/collections', { name, description: desc });
          col.item_count = 0;
          col.updated_at = new Date().toISOString();
          state.collections.unshift(col);

          const card = buildCollectionCard(col);
          const placeholder = document.getElementById('create-collection-card');
          grid.insertBefore(card, placeholder);
          if (window.lucide) lucide.createIcons({ nodes: [card] });

          if (nameInput) nameInput.value = '';
          if (descInput) descInput.value = '';
          ModalManager.close('new-collection-modal');
          Toast.success(`Collection "${name}" created!`);
        } catch (e) {
          Toast.error('Could not create collection. Please try again.');
        } finally {
          saveBtn.disabled = false;
          saveBtn.innerHTML = '<i data-lucide="folder-plus"></i> Create Collection';
          if (window.lucide) lucide.createIcons({ nodes: [saveBtn] });
        }
      });
    }
  }

  // ─── Search filter ─────────────────────────────────────────────────────────
  if (searchInput) {
    searchInput.addEventListener('input', () => {
      const q = searchInput.value.trim().toLowerCase();
      document.querySelectorAll('#collections-grid .collection-card:not(#create-collection-card)').forEach(card => {
        card.style.display = (!q || card.dataset.name.includes(q)) ? '' : 'none';
      });
    });
  }

  // ─── Sort ─────────────────────────────────────────────────────────────────
  if (sortSelect) {
    sortSelect.addEventListener('change', () => {
      const val = sortSelect.value;
      let sorted = [...state.collections];
      if (val === 'az')    sorted.sort((a, b) => a.name.localeCompare(b.name));
      if (val === 'items') sorted.sort((a, b) => (b.item_count ?? 0) - (a.item_count ?? 0));
      // 'updated' is default (already sorted by server)
      renderCollections(sorted);
    });
  }

  // ─── Utilities ────────────────────────────────────────────────────────────
  function escHtml(str) {
    return String(str || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function formatRelativeTime(isoString) {
    if (!isoString) return '';
    const now  = Date.now();
    const then = new Date(isoString).getTime();
    const diff = Math.floor((now - then) / 1000);
    if (diff < 60)     return 'Just now';
    if (diff < 3600)   return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400)  return `${Math.floor(diff / 3600)}h ago`;
    if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
    return new Date(isoString).toLocaleDateString();
  }

  // ─── Init ─────────────────────────────────────────────────────────────────
  loadCollections();
});
