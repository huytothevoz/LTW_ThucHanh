/* Real SQLite book browsing with server-side filters and pagination. */
(function () {
  'use strict';
  const { fetchJSON, toast } = window.CrawlInsight;
  const $ = (id) => document.getElementById(id);
  let currentPage = 1;
  let currentFilters = { q: '', min_price: '', max_price: '' };
  let lastRequestController = null;
  const pricePattern = /^(?:0|[1-9]\d{0,3})(?:\.\d{1,2})?$/;
  const pounds = (pence) => new Intl.NumberFormat('en-GB', {
    style: 'currency', currency: 'GBP', minimumFractionDigits: 2,
  }).format(Number(pence) / 100);

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
    link.textContent = 'View original source ↗';
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    const approved = safeSourceURL(book.source_url);
    if (approved) link.href = approved;
    else { link.removeAttribute('href'); link.textContent = 'Source not available'; }
    body.append(link);
    card.append(cover, body);
    return card;
  }

  function renderBooks(data) {
    const items = data.items || [];
    $('books-loading').hidden = true;
    $('book-grid').hidden = items.length === 0;
    $('books-empty').hidden = items.length !== 0;
    $('result-count').textContent = `${data.total} records`;
    const from = data.total ? (data.page - 1) * data.page_size + 1 : 0;
    const to = Math.min(data.total, data.page * data.page_size);
    $('results-summary').textContent = `Showing ${from}–${to} of ${data.total} book${data.total === 1 ? '' : 's'}`;
    const grid = $('book-grid');
    grid.replaceChildren();
    for (const book of items) grid.append(createBookCard(book));
    if (!items.length) {
      const isFiltered = Boolean(currentFilters.q || currentFilters.min_price || currentFilters.max_price);
      $('books-empty-description').textContent = isFiltered
        ? 'No titles match your current filters. Try a broader search or reset filters.'
        : data.total ? 'This page is empty. Go to the previous page.'
          : 'Your collection is empty. Start a crawl to import real book data.';
    }
    $('pagination').hidden = data.total_pages <= 1;
    $('page-label').textContent = `Page ${data.page} of ${data.total_pages}`;
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
    toast('Could not load book results.', 'error');
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
    if (!validatePrice(min) || !validatePrice(max)) {
      toast('Enter GBP prices from 0 to 9999.99 (up to 2 decimal places).', 'error');
      return;
    }
    if (min && max && Number(min) > Number(max)) {
      toast('Minimum price cannot exceed maximum price.', 'error');
      return;
    }
    currentFilters = { q: $('search-query').value.trim(), min_price: min, max_price: max };
    currentPage = 1;
    loadBooks();
  }

  $('filter-form').addEventListener('submit', (event) => { event.preventDefault(); submitFilters(); });
  $('reset-filters').addEventListener('click', () => {
    $('filter-form').reset();
    currentFilters = { q: '', min_price: '', max_price: '' };
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
  $('min-price').value = currentFilters.min_price;
  $('max-price').value = currentFilters.max_price;
  loadBooks();
})();
