/**
 * 1011 Media Asset Manager — Tag Input Component
 * 
 * Usage:
 *   const ti = new TagInput(containerEl, {
 *     initialTags: ['persija', 'match'],
 *     suggestions: ['persija', 'liga-1', 'match', ...],
 *     onAdd: (tag) => {},
 *     onRemove: (tag) => {},
 *     placeholder: 'Add a tag...',
 *     category: 'event',   // optional — for color class
 *   });
 *   ti.getTags()  // returns array of current tags
 *   ti.setTags([...])
 *   ti.destroy()
 */

class TagInput {
  constructor(container, opts = {}) {
    this.container = typeof container === 'string' ? document.querySelector(container) : container;
    if (!this.container) return;

    this.tags = new Set(opts.initialTags || []);
    this.suggestions = opts.suggestions || [];
    this.onAdd = opts.onAdd || (() => {});
    this.onRemove = opts.onRemove || (() => {});
    this.placeholder = opts.placeholder || 'Add a tag...';
    this.category = opts.category || null; // 'event' | 'team' | 'player' | 'year' | 'league' | null

    this._dropdownVisible = false;
    this._render();
  }

  _tagClass() {
    return this.category ? `tag tag-${this.category}` : 'tag';
  }

  _normalize(raw) {
    return raw.trim().toLowerCase().replace(/[^a-z0-9-_]/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '');
  }

  _render() {
    this.container.classList.add('tag-input-root');
    this.container.innerHTML = '';

    // Pills wrapper
    this.pillsEl = document.createElement('div');
    this.pillsEl.className = 'tag-pills';

    // Input wrapper
    this.inputWrapper = document.createElement('div');
    this.inputWrapper.className = 'tag-input-wrapper';
    this.inputWrapper.style.position = 'relative';

    this.input = document.createElement('input');
    this.input.type = 'text';
    this.input.className = 'form-input';
    this.input.placeholder = this.placeholder;
    this.input.setAttribute('autocomplete', 'off');

    // Dropdown
    this.dropdown = document.createElement('ul');
    this.dropdown.className = 'tag-autocomplete';
    this.dropdown.style.display = 'none';

    this.inputWrapper.appendChild(this.input);
    this.inputWrapper.appendChild(this.dropdown);

    this.container.appendChild(this.pillsEl);
    this.container.appendChild(this.inputWrapper);

    this._renderPills();
    this._attachEvents();
  }

  _renderPills() {
    this.pillsEl.innerHTML = '';
    this.tags.forEach(tag => {
      const pill = document.createElement('span');
      pill.className = this._tagClass();
      pill.innerHTML = `${tag} <button class="tag-remove-btn" aria-label="Remove tag ${tag}" data-tag="${tag}"><i data-lucide="x" style="width:12px;height:12px;pointer-events:none;"></i></button>`;
      this.pillsEl.appendChild(pill);
    });

    // Re-render lucide icons
    if (window.lucide) lucide.createIcons({ nodes: [this.pillsEl] });

    // Bind remove buttons
    this.pillsEl.querySelectorAll('.tag-remove-btn').forEach(btn => {
      btn.addEventListener('click', () => this._removeTag(btn.dataset.tag));
    });
  }

  _addTag(raw) {
    const tag = this._normalize(raw);
    if (!tag || this.tags.has(tag)) { this.input.value = ''; return; }
    this.tags.add(tag);
    this.onAdd(tag);
    this._renderPills();
    this.input.value = '';
    this._updateDropdown('');
  }

  _removeTag(tag) {
    this.tags.delete(tag);
    this.onRemove(tag);
    this._renderPills();
  }

  _updateDropdown(query) {
    const q = query.trim().toLowerCase();
    const matches = q
      ? this.suggestions.filter(s => s.includes(q) && !this.tags.has(s)).slice(0, 8)
      : [];

    if (!matches.length) {
      this.dropdown.style.display = 'none';
      return;
    }

    this.dropdown.innerHTML = matches.map(s =>
      `<li class="tag-autocomplete-item" tabindex="-1">${s}</li>`
    ).join('');
    this.dropdown.style.display = 'block';

    this.dropdown.querySelectorAll('li').forEach(li => {
      li.addEventListener('mousedown', (e) => {
        e.preventDefault();
        this._addTag(li.textContent);
        this.input.focus();
      });
    });
  }

  _attachEvents() {
    this.input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ',') {
        e.preventDefault();
        const val = this.input.value.replace(/,$/, '').trim();
        if (val) this._addTag(val);
      }
      if (e.key === 'Backspace' && !this.input.value && this.tags.size > 0) {
        const last = [...this.tags].pop();
        this._removeTag(last);
      }
      // Arrow navigation in dropdown
      if (e.key === 'ArrowDown') {
        const first = this.dropdown.querySelector('li');
        if (first) { e.preventDefault(); first.focus(); }
      }
    });

    this.input.addEventListener('input', () => this._updateDropdown(this.input.value));
    this.input.addEventListener('blur', () => {
      setTimeout(() => { this.dropdown.style.display = 'none'; }, 150);
    });
    this.input.addEventListener('focus', () => this._updateDropdown(this.input.value));

    // Arrow nav inside dropdown
    this.dropdown.addEventListener('keydown', (e) => {
      const items = [...this.dropdown.querySelectorAll('li')];
      const idx = items.indexOf(document.activeElement);
      if (e.key === 'ArrowDown' && idx < items.length - 1) { e.preventDefault(); items[idx + 1].focus(); }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (idx > 0) items[idx - 1].focus(); else this.input.focus();
      }
      if (e.key === 'Enter') { e.preventDefault(); this._addTag(items[idx].textContent); this.input.focus(); }
      if (e.key === 'Escape') { this.dropdown.style.display = 'none'; this.input.focus(); }
    });
  }

  getTags() { return [...this.tags]; }

  setTags(tagArray) {
    this.tags = new Set(tagArray);
    this._renderPills();
  }

  destroy() {
    this.container.innerHTML = '';
    this.container.classList.remove('tag-input-root');
  }
}

window.TagInput = TagInput;
