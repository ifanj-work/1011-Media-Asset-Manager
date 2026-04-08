/**
 * 1011 Media Asset Manager — Modal Manager
 * Shared modal open/close with focus trap, Escape key, backdrop click.
 * Supports multiple stacked modals.
 */

const ModalManager = (() => {
  const FOCUSABLE = 'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';
  const stack = []; // stack of open modal IDs

  function getFocusable(modal) {
    return [...modal.querySelectorAll(FOCUSABLE)].filter(
      el => !el.closest('[hidden]') && window.getComputedStyle(el).display !== 'none'
    );
  }

  function trapFocus(e, modal) {
    const focusable = getFocusable(modal);
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (e.key === 'Tab') {
      if (e.shiftKey) {
        if (document.activeElement === first) { e.preventDefault(); last.focus(); }
      } else {
        if (document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    }
  }

  function open(modalId, opts = {}) {
    const modal = document.getElementById(modalId);
    if (!modal) return;

    // Store previously focused element for restoration
    modal._prevFocus = document.activeElement;
    modal._onClose = opts.onClose || null;

    // Animate in
    modal.style.display = 'flex';
    requestAnimationFrame(() => modal.classList.add('modal-open'));

    // Focus first focusable element
    const focusable = getFocusable(modal);
    if (focusable.length) setTimeout(() => focusable[0].focus(), 50);

    // Tab trap
    modal._trapHandler = (e) => trapFocus(e, modal);
    modal.addEventListener('keydown', modal._trapHandler);

    // Escape key
    modal._escHandler = (e) => {
      if (e.key === 'Escape' && stack[stack.length - 1] === modalId) close(modalId);
    };
    document.addEventListener('keydown', modal._escHandler);

    // Backdrop click
    modal._backdropHandler = (e) => {
      if (e.target === modal) close(modalId);
    };
    modal.addEventListener('click', modal._backdropHandler);

    stack.push(modalId);
    document.body.classList.add('modal-is-open');
  }

  function close(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;

    modal.classList.remove('modal-open');
    setTimeout(() => { modal.style.display = 'none'; }, 200);

    // Cleanup
    if (modal._trapHandler) modal.removeEventListener('keydown', modal._trapHandler);
    if (modal._escHandler) document.removeEventListener('keydown', modal._escHandler);
    if (modal._backdropHandler) modal.removeEventListener('click', modal._backdropHandler);

    // Restore focus
    if (modal._prevFocus) modal._prevFocus.focus();

    // Run callback
    if (modal._onClose) modal._onClose();

    const idx = stack.indexOf(modalId);
    if (idx > -1) stack.splice(idx, 1);
    if (!stack.length) document.body.classList.remove('modal-is-open');
  }

  function closeAll() {
    [...stack].reverse().forEach(id => close(id));
  }

  // Wire up all modal-close buttons automatically
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-modal-close]').forEach(btn => {
      btn.addEventListener('click', () => close(btn.dataset.modalClose));
    });
    document.querySelectorAll('[data-modal-open]').forEach(btn => {
      btn.addEventListener('click', () => open(btn.dataset.modalOpen));
    });
  });

  return { open, close, closeAll };
})();

window.ModalManager = ModalManager;
