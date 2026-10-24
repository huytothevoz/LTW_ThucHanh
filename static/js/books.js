/* Real SQLite book browsing with server-side filters and pagination. */
(function () {
  'use strict';
  const { fetchJSON, toast, pounds, t, locale } = window.CrawlInsight;
  const $ = (id) => document.getElementById(id);
  let currentPage = 1;
  let currentFilters = { q: '', category: '', min_price: '', max_price: '' };
  let lastRequestController = null;
  const pricePattern = /^(?:0|[1-9]\d{0,3})(?:\.\d{1,2})?$/;
  let bookmarkedIds = new Set();
  function safeSourceURL(url) {
    try {
      const parsed = new URL(url);
      return parsed.protocol === 'https:' && parsed.hostname === 'books.toscrape.com' && !parsed.username
        ? parsed.href : null;
    } catch { return null; }
  }

  function textElement(tag, className, content) {
    const element = document.createElement(tag);
    element.className = className;
    element.textContent = String(content);
    return element;
  }

  function createBookCard(book) {
    const card = document.createElement('article');
    card.className = 'book-card';
    const cover = document.createElement('div');
    cover.className = 'book-cover no-image';
    const imageURL = safeSourceURL(book.image_url);
    if (imageURL) {
      const image = document.createElement('img');
      image.src = imageURL;
      image.alt = `Cover artwork for ${book.title}`;
      image.loading = 'lazy';
      image.decoding = 'async';
      image.referrerPolicy = 'no-referrer';
      image.addEventListener('load', () => cover.classList.remove('no-image'));
      image.addEventListener('error', () => { image.remove(); cover.classList.add('no-image'); });
      cover.append(image);
    }
    const availability = String(book.availability || 'Unknown');
    const stock = textElement('span', `book-availability${availability === 'In stock' ? '' : ' out'}`, availability);
    cover.append(stock);
    const body = document.createElement('div');
    body.className = 'book-body';
    body.append(textElement('span', 'book-category', book.category || 'Uncategorized'));
    const title = textElement('h4', 'book-title', book.title);
    title.title = book.title;
    body.append(title);
    const priceRow = document.createElement('div');
    priceRow.className = 'book-price-row';
    priceRow.append(textElement('strong', 'book-price', pounds(book.price_pence)));
    const rating = textElement('span', 'book-rating', '★'.repeat(book.rating) + '☆'.repeat(Math.max(0, 5 - book.rating)));
    rating.setAttribute('aria-label', `Rating ${book.rating} of 5 stars`);
    priceRow.append(rating);
    body.append(priceRow);
    const link = document.createElement('a');
    link.className = 'book-link';
    link.textContent = t('source') + ' ↗';
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    const approved = safeSourceURL(book.source_url);
    if (approved) link.href = approved;
    else { link.removeAttribute('href'); link.textContent = 'Source not available'; }
    body.append(link);
    const actions = document.createElement('div'); actions.className = 'book-quick-actions';
    const save = document.createElement('button'); save.type = 'button'; save.className = 'bookmark-button';
    save.textContent = bookmarkedIds.has(book.id) ? '♥ ' + t('saved') : '♡ ' + t('save');
    if (bookmarkedIds.has(book.id)) save.classList.add('saved');
    save.addEventListener('click', async () => {
      const had = bookmarkedIds.has(book.id);
      save.disabled = true;
      try {
        await fetchJSON(`/api/bookmarks/${book.id}`, { method: had ? 'DELETE' : 'POST', body: had ? undefined : '{}' });
        if (had) bookmarkedIds.delete(book.id); else bookmarkedIds.add(book.id);
        save.classList.toggle('saved', !had); save.textContent = !had ? '♥ ' + t('saved') : '♡ ' + t('save');
      } catch (error) { toast(error.message, 'error'); } finally { save.disabled = false; }
    });
    const detail = document.createElement('button'); detail.type = 'button'; detail.className = 'detail-button'; detail.textContent = t('details') + ' →';
    detail.addEventListener('click', () => showBookDetail(book.id));
    actions.append(save, detail); body.append(actions);
    card.append(cover, body);
    return card;
  }

  function renderBooks(data) {
    const items = data.items || [];
    $('books-loading').hidden = true;
    $('book-grid').hidden = items.length === 0;
    $('books-empty').hidden = items.length !== 0;
    bookmarkedIds = new Set(data.bookmarked_ids || []);
    $('result-count').textContent = `${data.total} ${t('records')}`;
    const from = data.total ? (data.page - 1) * data.page_size + 1 : 0;
    const to = Math.min(data.total, data.page * data.page_size);
    $('results-summary').textContent = locale === 'vi' ? `Đang xem ${from}–${to} / ${data.total} sách` : `Showing ${from}–${to} of ${data.total} books`;
    const grid = $('book-grid');
    grid.replaceChildren();
    for (const book of items) grid.append(createBookCard(book));
    if (!items.length) {
      const isFiltered = Boolean(currentFilters.q || currentFilters.category || currentFilters.min_price || currentFilters.max_price);
      $('books-empty-description').textContent = isFiltered
        ? t('emptyBooks')
        : data.total ? 'This page is empty. Go to the previous page.'
          : t('emptyCollection');
    }
    $('pagination').hidden = data.total_pages <= 1;
    $('page-label').textContent = locale === 'vi' ? `Trang ${data.page}/${data.total_pages}` : `Page ${data.page} of ${data.total_pages}`;
    $('prev-page').disabled = data.page <= 1;
    $('next-page').disabled = data.page >= data.total_pages;
  }

  function renderError(error) {
    $('books-loading').hidden = true;
    $('book-grid').hidden = true;
    $('books-empty').hidden = true;
    const banner = $('books-error');
    banner.textContent = `${error.message}. Use Apply filters to retry.`;
    banner.hidden = false;
    toast(t('error'), 'error');
  }

  async function loadBooks() {
    lastRequestController?.abort();
    const controller = new AbortController();
    lastRequestController = controller;
    $('books-error').hidden = true;
    $('books-loading').hidden = false;
    $('books-empty').hidden = true;
    $('book-grid').hidden = true;
    $('pagination').hidden = true;
    const params = new URLSearchParams({ page: String(currentPage) });
    for (const [key, value] of Object.entries(currentFilters)) if (value) params.set(key, value);
    const url = `/api/books?${params}`;
    try {
      const data = await fetchJSON(url, { signal: controller.signal });
      if (lastRequestController !== controller) return;
      renderBooks(data);
      const newAddress = new URL(window.location.href);
      newAddress.search = params.toString();
      window.history.replaceState(null, '', newAddress.pathname + newAddress.search);
    } catch (error) {
      if (error.name !== 'AbortError') renderError(error);
    }
  }

  function validatePrice(input) {
    const value = input.trim();
    return value === '' || pricePattern.test(value);
  }
  function submitFilters() {
    const min = $('min-price').value.trim();
    const max = $('max-price').value.trim();
    const cat = $('category-filter') ? $('category-filter').value.trim() : '';
    if (!validatePrice(min) || !validatePrice(max)) {
      toast(t('invalidPrice'), 'error');
      return;
    }
    if (min && max && Number(min) > Number(max)) {
      toast(t('invalidRange'), 'error');
      return;
    }
    currentFilters = { q: $('search-query').value.trim(), category: cat, min_price: min, max_price: max };
    currentPage = 1;
    loadBooks();
  }

  $('filter-form').addEventListener('submit', (event) => { event.preventDefault(); submitFilters(); });
  $('reset-filters').addEventListener('click', () => {
    $('filter-form').reset();
    currentFilters = { q: '', category: '', min_price: '', max_price: '' };
    currentPage = 1;
    loadBooks();
  });
  $('prev-page').addEventListener('click', () => { if (currentPage > 1) { currentPage--; loadBooks(); } });
  $('next-page').addEventListener('click', () => { currentPage++; loadBooks(); });
  const initialQuery = new URLSearchParams(location.search);
  const savedPage = initialQuery.get('page');
  if (savedPage && /^\d{1,6}$/.test(savedPage) && Number(savedPage) >= 1 && Number(savedPage) <= 100000) currentPage = Number(savedPage);
  for (const key of Object.keys(currentFilters)) {
    const value = initialQuery.get(key) || '';
    if (value && value.length <= 100) currentFilters[key] = value;
  }
  $('search-query').value = currentFilters.q;
  if ($('category-filter')) $('category-filter').value = currentFilters.category;
  $('min-price').value = currentFilters.min_price;
  $('max-price').value = currentFilters.max_price;

  async function loadCategories() {
    const select = $('category-filter');
    if (!select) return;
    try {
      const data = await fetchJSON('/api/categories');
      const items = data.items || [];
      for (const item of items) {
        const opt = document.createElement('option');
        opt.value = item.name;
        opt.textContent = item.name;
        if (item.name.toLowerCase() === currentFilters.category.toLowerCase()) {
          opt.selected = true;
        }
        select.append(opt);
      }
    } catch (_) { }
  }
  const detailDialog = $('book-detail-dialog');
  async function showBookDetail(bookId) {
    detailDialog.showModal(); const content = $('book-detail-content'); content.replaceChildren();
    content.append(textElement('p', '', t('loading')));
    try {
      const data = await fetchJSON(`/api/books/${bookId}`); content.replaceChildren();
      const b = data.book;
      content.append(textElement('span', 'book-category', b.category), textElement('h2', '', b.title));
      content.append(textElement('p', '', `${pounds(b.price_pence)} · ${b.rating} ★ · ${b.availability}`));
      content.append(textElement('p', '', `UPC: ${b.upc || '—'}`));
      if (data.price_history.length) {
        content.append(textElement('h3', '', locale === 'vi' ? 'Lịch sử giá' : 'Price history'));
        data.price_history.forEach(p => content.append(textElement('p', '', `${pounds(p.old_price_pence)} → ${pounds(p.new_price_pence)} · ${p.changed_at}`)));
      }
      const src = safeSourceURL(b.source_url); if (src) { const link = document.createElement('a'); link.className = 'outlined-action'; link.href = src; link.target = '_blank'; link.rel = 'noopener noreferrer'; link.textContent = t('source') + ' ↗'; content.append(link); }
    } catch (e) { content.replaceChildren(textElement('p', '', e.message)); }
  }
  document.querySelectorAll('[data-close-dialog]').forEach(button => button.addEventListener('click', () => document.getElementById(button.dataset.closeDialog)?.close()));
  const filterDialog = $('save-filter-dialog');
  $('save-filter')?.addEventListener('click', () => { filterDialog.showModal(); $('saved-filter-name').focus(); });
  $('save-filter-form')?.addEventListener('submit', async e => {
    e.preventDefault(); const name = $('saved-filter-name').value.trim(); if (!name) return;
    try {
      await fetchJSON('/api/saved-searches', { method: 'POST', body: JSON.stringify({ name, ...currentFilters }) });
      filterDialog.close(); $('save-filter-form').reset(); toast(t('filterSaved'), 'success'); loadSavedSearches();
    } catch (error) { toast(error.message, 'error'); }
  });
  async function loadSavedSearches() {
    const bar = $('saved-search-bar'), list = $('saved-search-list'); if (!bar || !list) return;
    try {
      const data = await fetchJSON('/api/saved-searches'); bar.hidden = data.items.length === 0; list.replaceChildren();
      data.items.forEach(item => {
        const wrapper = document.createElement('span'); wrapper.className = 'saved-search-pill';
        const apply = document.createElement('button'); apply.textContent = item.name; apply.addEventListener('click', () => {
          currentFilters = { q: item.query, min_price: item.min_price, max_price: item.max_price };
          $('search-query').value = currentFilters.q; $('min-price').value = currentFilters.min_price; $('max-price').value = currentFilters.max_price; currentPage = 1; loadBooks();
        });
        const del = document.createElement('button'); del.textContent = '×'; del.className = 'delete-chip'; del.title = t('remove');
        del.addEventListener('click', async () => { try { await fetchJSON(`/api/saved-searches/${item.id}`, { method: 'DELETE' }); loadSavedSearches(); } catch (e) { toast(e.message, 'error'); } });
        wrapper.append(apply, del); list.append(wrapper);
      });
    } catch (error) { toast(error.message, 'error'); }
  }
  fetchJSON('/api/auth/me').then(data => { if (data.preferences.book_layout === 'list') $('book-grid').classList.add('list-view'); }).catch(() => { });
  loadCategories();
  loadSavedSearches();
  loadBooks();
  const resetBooksBtn = $('reset-books-btn');
  if (resetBooksBtn) {
    resetBooksBtn.addEventListener('click', async () => {
      const confirmMsg = t('resetConfirm') || 'Bạn có chắc chắn muốn xóa toàn bộ sách đã crawl? Thao tác này sẽ xóa tất cả sách và lịch sử crawl của bạn.';
      if (!confirm(confirmMsg)) return;
      resetBooksBtn.disabled = true;
      try {
        const res = await fetchJSON('/api/books/reset', { method: 'POST' });
        toast(t('resetSuccess') || `Đã đặt lại dữ liệu sách (${res.deleted_books || 0} sách).`, 'success');
        currentPage = 1;
        await loadBooks();
        await loadCategories();
      } catch (err) {
        toast(err.message || 'Không thể reset sách.', 'error');
      } finally {
        resetBooksBtn.disabled = false;
      }
    });
  }

  $('category-filter')?.addEventListener('change', () => submitFilters());
})();
