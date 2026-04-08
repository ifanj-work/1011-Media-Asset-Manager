/**
 * 1011 Media Asset Manager — Toast Notifications
 * showToast(message, type, duration)
 * Types: 'success' | 'error' | 'info' | 'warning'
 */

const Toast = (() => {
  const ICONS = {
    success: 'check-circle',
    error: 'x-circle',
    warning: 'alert-triangle',
    info: 'info',
  };

  function getContainer() {
    let el = document.getElementById('toast-container');
    if (!el) {
      el = document.createElement('div');
      el.id = 'toast-container';
      el.className = 'toast-container';
      document.body.appendChild(el);
    }
    return el;
  }

  function show(message, type = 'info', duration = 3500) {
    const container = getContainer();

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');

    toast.innerHTML = `
      <i data-lucide="${ICONS[type] || 'info'}" class="toast-icon"></i>
      <span class="toast-message">${message}</span>
      <button class="toast-close" aria-label="Dismiss notification">
        <i data-lucide="x"></i>
      </button>
    `;

    container.appendChild(toast);

    // Re-render lucide icons in this toast
    if (window.lucide) lucide.createIcons({ nodes: [toast] });

    // Trigger enter animation
    requestAnimationFrame(() => {
      requestAnimationFrame(() => toast.classList.add('toast-visible'));
    });

    const dismiss = () => {
      toast.classList.remove('toast-visible');
      toast.classList.add('toast-exit');
      setTimeout(() => toast.remove(), 300);
    };

    toast.querySelector('.toast-close').addEventListener('click', dismiss);

    if (duration > 0) setTimeout(dismiss, duration);

    return { dismiss };
  }

  return {
    success: (msg, dur) => show(msg, 'success', dur),
    error: (msg, dur) => show(msg, 'error', dur),
    warning: (msg, dur) => show(msg, 'warning', dur),
    info: (msg, dur) => show(msg, 'info', dur),
    show,
  };
})();

window.Toast = Toast;
