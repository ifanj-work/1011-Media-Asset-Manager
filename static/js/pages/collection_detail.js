/**
 * 1011 Media Asset Manager — Collection Detail Page
 * Loads items for a specific collection and handles presentation/removal.
 */

document.addEventListener('DOMContentLoaded', () => {

    const colId = window.COLLECTION_ID;
    if (!colId) return;
  
    // Elements
    const grid = document.getElementById('asset-grid');
    const resultCount = document.getElementById('result-count');
    const sortSelect = document.getElementById('sort-select');
    const summaryCount = document.getElementById('col-item-count');
  
    // Modal Elements
    const modalImg = document.getElementById('modal-preview-img');
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
  
    // State
    const state = {
        assets: [],
        total: 0,
        page: 1,
        perPage: 50,
        sort: sortSelect ? sortSelect.value : 'newest',
        loading: false,
        hasMore: true,
        previewIdx: 0
    };
  
    async function fetchItems() {
        if (state.loading || !state.hasMore) return;
        state.loading = true;
        showLoading();
  
        try {
            // fetch assets
            const res = await fetch(`/api/collections/${colId}/items?page=${state.page}&per_page=${state.perPage}`);
            if (!res.ok) throw new Error("API error");
            const data = await res.json();
            
            // Apply client-side sorting since the endpoint doesn't support complex sorts natively yet.
            // Items are mostly appended, so 'newest' means later added (or we can just sort by id/added_at if available)
            // The items come sorted by added to collection natively, newest first usually.
            // For now, we'll just handle basic data loading.
  
            if (state.page === 1) {
                state.assets = data.items;
                state.total = data.total;
                grid.innerHTML = '';
            } else {
                state.assets = state.assets.concat(data.items);
            }
  
            state.hasMore = state.assets.length < state.total;
            
            if (resultCount) resultCount.textContent = `Showing ${state.assets.length} of ${formatNumber(state.total)}`;
            if (summaryCount) summaryCount.textContent = formatNumber(state.total);
            
            renderAssets(data.items);
        } catch (e) {
            console.error(e);
            Toast.error("Failed to load collection items.");
        } finally {
            state.loading = false;
            removeLoading();
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
        grid.querySelectorAll('.skeleton-card').forEach(el => el.remove());
    }
  
    function renderAssets(items) {
        if (!grid) return;
        
        if (state.total === 0) {
            grid.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; padding: var(--space-8); color: var(--text-tertiary);">
                    <i data-lucide="folder-open" style="width: 48px; height: 48px; margin-bottom: var(--space-2); opacity: 0.5;"></i>
                    <p class="font-medium font-poppins">This collection is empty</p>
                    <p class="text-sm">Search and add assets to this collection to see them here.</p>
                </div>
            `;
            if (window.lucide) lucide.createIcons({ nodes: [grid] });
            return;
        }
  
        const fragment = document.createDocumentFragment();
        const baseIdx = state.assets.length - items.length;
        
        items.forEach((asset, i) => {
            const ext = (asset.ext || '').toUpperCase();
            const icon = getFileIcon(ext);
            const globalIdx = baseIdx + i;
            
            const card = document.createElement('div');
            card.className = 'asset-card';
            card.dataset.idx = globalIdx;
            
            card.innerHTML = `
                <div class="asset-card-thumb">
                    <div style="width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; position: absolute; inset: 0;">
                        <img src="/api/thumb/${asset.id}" style="width: 100%; height: 100%; object-fit: contain;">
                    </div>
                    <div class="asset-card-badge">${ext}</div>
                </div>
                <div class="asset-card-info">
                    <p class="asset-card-name" title="${asset.filename}">${asset.filename}</p>
                    <div style="font-size: var(--text-xs); color: var(--text-tertiary); margin-top: 4px; margin-bottom: 8px;">
                        ${formatBytes(asset.size)} • ${asset.added_at ? asset.added_at.substring(0, 10) : ''}
                    </div>
                </div>
            `;
            
            card.addEventListener('click', () => openPreview(globalIdx));
            fragment.appendChild(card);
        });
        
        grid.appendChild(fragment);
        if (window.lucide) lucide.createIcons({ nodes: [grid] });
    }
  
    function getFileIcon(ext) {
        ext = (ext || '').toLowerCase();
        if (['mp4', 'mov', 'avi', 'mkv'].includes(ext)) return 'video';
        if (['psd', 'ai', 'eps'].includes(ext)) return 'layers';
        return 'image';
    }
  
    function formatBytes(bytes) {
        if (bytes === 0 || !bytes) return '0 B';
        const k = 1024, sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }
    function formatNumber(num) {
        return new Intl.NumberFormat().format(num || 0);
    }
  
    // Preview logic
    function openPreview(idx) {
        if (idx < 0 || idx >= state.assets.length) return;
        state.previewIdx = idx;
        const asset = state.assets[idx];
        
        // Show modal image
        modalImg.style.display = 'block';
        modalImg.src = `/api/thumb/${asset.id}`;
        modalIcon.style.display = 'none'; // hide the placeholder icon
        
        // Meta
        modalFilename.textContent = asset.filename;
        modalFilesize.textContent = `${formatBytes(asset.size)}`;
        modalDate.textContent = asset.added_at ? asset.added_at.substring(0, 10) : 'Unknown';
        modalType.textContent = `${(asset.ext || '').toUpperCase()} File`;
        modalPath.textContent = asset.path;
        
        updatePreviewNav();
        ModalManager.open('detail-modal');
    }
    
    function updatePreviewNav() {
        if (btnPrev) btnPrev.style.visibility = (state.previewIdx > 0) ? 'visible' : 'hidden';
        if (btnNext) btnNext.style.visibility = (state.previewIdx < state.assets.length - 1) ? 'visible' : 'hidden';
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
    
    // Download
    if (btnDownload) {
        btnDownload.addEventListener('click', () => {
            const asset = state.assets[state.previewIdx];
            if (!asset) return;
            window.open(`/api/download/${asset.id}`, '_blank');
        });
    }
  
    // Remove from collection
    if (btnRemove) {
        btnRemove.addEventListener('click', async () => {
            const asset = state.assets[state.previewIdx];
            if (!asset) return;
            
            btnRemove.disabled = true;
            try {
                const res = await fetch(`/api/collections/${colId}/items/${asset.file_id}`, { method: 'DELETE' });
                if (!res.ok) throw new Error("API error");
                
                Toast.success(`Removed from collection`);
                ModalManager.close('detail-modal');
                
                // Refresh list
                state.page = 1;
                grid.innerHTML = '';
                fetchItems();
            } catch (e) {
                console.error(e);
                Toast.error(`Could not remove file`);
            } finally {
                btnRemove.disabled = false;
            }
        });
    }
    
    // Sort change
    if (sortSelect) {
        sortSelect.addEventListener('change', () => {
            state.sort = sortSelect.value;
            // Native sorting not supported by collection items endpoint yet, but UI is primed.
            Toast.info("Sort not fully implemented yet");
        });
    }
  
    // Infinite roll
    if (grid) {
        grid.addEventListener('scroll', () => {
            if (grid.scrollHeight - grid.scrollTop - grid.clientHeight < 100) {
                fetchItems();
            }
        });
    }
  
    // Kick off
    fetchItems();
});
