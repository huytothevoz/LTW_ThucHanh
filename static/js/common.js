/* Shared UI primitives. Remote data is always inserted using textContent. */
(function () {
  'use strict';
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('mobile-overlay');
  const menu = document.getElementById('mobile-menu');

  function toggleMenu(isOpen) {
    if (!sidebar || !overlay || !menu) return;
    sidebar.classList.toggle('open', isOpen);
    overlay.hidden = !isOpen;
    menu.setAttribute('aria-expanded', String(isOpen));
  }
  menu?.addEventListener('click', () => toggleMenu(!sidebar.classList.contains('open')));
  overlay?.addEventListener('click', () => toggleMenu(false));
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') toggleMenu(false);
  });

  async function fetchJSON(path, options = {}) {
    const response = await fetch(path, {
      headers: { Accept: 'application/json', ...(options.body ? { 'Content-Type': 'application/json' } : {}) },
      cache: 'no-store',
      ...options,
    });
    let data;
    try {
      data = await response.json();
    } catch {
      throw new Error('The server returned an invalid response.');
    }
    if (!response.ok) {
      const error = new Error(data?.error?.message || `Request failed (${response.status})`);
      error.code = data?.error?.code || 'UNKNOWN_ERROR';
      error.status = response.status;
      throw error;
    }
    return data;
  }

  function toast(message, type = 'info') {
    const container = document.getElementById('toast-region');
    if (!container) return;
    const item = document.createElement('div');
    item.className = `toast ${type}`;
    item.textContent = message;
    container.append(item);
    setTimeout(() => item.remove(), 4800);
  }

  function formatDate(value, withTime = true) {
    if (!value) return 'Not available';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Unknown date';
    const settings = withTime
      ? { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }
      : { year: 'numeric', month: 'short', day: 'numeric' };
    return new Intl.DateTimeFormat('en-GB', settings).format(date);
  }
  window.CrawlInsight = { fetchJSON, toast, formatDate };
})();
