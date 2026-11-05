/* Dedicated page controllers. DOM building uses textContent for all fetched data. */
(() => {
  'use strict';
  const { fetchJSON, toast, formatDate, pounds, t, locale } = window.CrawlInsight;
  const $ = id => document.getElementById(id);
  const text = (tag, cls, value) => { const el = document.createElement(tag); el.className = cls; el.textContent = String(value); return el; };
  const el = (tag, cls) => { const e = document.createElement(tag); e.className = cls; return e; };
  const APPROVED_HOSTS = new Set(['books.toscrape.com', 'openlibrary.org', 'www.openlibrary.org', 'covers.openlibrary.org', 'archive.org', 'gutenberg.org', 'www.gutenberg.org']); const sourceUrl = value => { try { const u = new URL(value); const isApproved = APPROVED_HOSTS.has(u.hostname) || u.hostname.endsWith('.archive.org'); return u.protocol === 'https:' && isApproved && !u.username && !u.password ? u.href : null; } catch { return null; } };

  async function savedPage() {
    let page = 1, totalPages = 0;
    async function load() {
      try {
        const data = await fetchJSON(`/api/bookmarks?page=${page}`); totalPages = data.total_pages;
        $('saved-loading').hidden = true; $('saved-empty').hidden = data.total > 0; $('saved-result-count').textContent = `${data.total} ${t('records')}`;
        $('saved-grid').replaceChildren();
        for (const book of data.items) {
          const card = el('article', 'saved-card'); const cover = el('div', 'saved-cover');
          const imgUrl = sourceUrl(book.image_url); if (imgUrl) { const img = document.createElement('img'); img.src = imgUrl; img.loading = 'lazy'; img.alt = book.title; img.referrerPolicy = 'no-referrer'; cover.append(img); } else cover.append(text('span', 'saved-placeholder', '📖'));
          const info = el('div', 'saved-info'); info.append(text('span', 'book-category', book.category), text('h3', '', book.title), text('strong', 'book-price', pounds(book.price_pence)));
          const buttons = el('div', 'saved-actions'); const original = document.createElement('a'); original.className = 'outlined-action'; original.textContent = t('source') + ' ↗';
          const u = sourceUrl(book.source_url); if (u) { original.href = u; original.target = '_blank'; original.rel = 'noopener noreferrer'; }
          const remove = document.createElement('button'); remove.className = 'danger-link'; remove.textContent = t('remove'); remove.addEventListener('click', async () => {
            try { await fetchJSON(`/api/bookmarks/${book.id}`, { method: 'DELETE' }); toast(t('confirmed'), 'success'); load(); } catch (e) { toast(e.message, 'error'); }
          }); buttons.append(original, remove); info.append(buttons); card.append(cover, info); $('saved-grid').append(card);
        }
        $('saved-pagination').hidden = data.total_pages <= 1; $('saved-page').textContent = `${page} / ${Math.max(data.total_pages, 1)}`;
        $('saved-prev').disabled = page <= 1; $('saved-next').disabled = page >= totalPages;
      } catch (e) { $('saved-loading').textContent = e.message; toast(e.message, 'error'); }
    }
    $('saved-prev').addEventListener('click', () => { if (page > 1) { page--; load(); } });
    $('saved-next').addEventListener('click', () => { if (page < totalPages) { page++; load(); } });
    load();
  }

  async function historyPage() {
    const tbody = $('history-tbody');

    async function loadHistory() {
      try {
        const data = await fetchJSON('/api/history');
        tbody.replaceChildren();
        if (!data.items.length) {
          const row = document.createElement('tr');
          const td = document.createElement('td');
          td.colSpan = 8;
          td.textContent = locale === 'vi' ? 'Chưa có phiên nào.' : 'No sessions yet.';
          row.append(td);
          tbody.append(row);
          return;
        }

        for (const job of data.items) {
          const row = document.createElement('tr');
          const jobNumber = Number(job.user_job_number || job.id || 0);
          const values = [
            `#${jobNumber}`,
            job.status,
            formatDate(job.created_at),
            `${job.catalogue_pages_done}/${job.max_pages}`,
            job.books_found,
            job.items_saved,
            job.error_count,
          ];
          values.forEach((value, index) => {
            const className = index === 1 ? `status-text s-${String(value).toLowerCase()}` : '';
            row.append(text('td', className, value));
          });

          const details = document.createElement('button');
          details.type = 'button';
          details.className = 'text-action';
          details.textContent = t('details') + ' →';
          details.addEventListener('click', async () => {
            try {
              const result = await fetchJSON(`/api/jobs/${job.id}`);
              const detail = $('history-detail');
              detail.hidden = false;
              detail.replaceChildren();
              const number = Number(result.job.user_job_number || result.job.id || 0);
              detail.append(
                text('h3', '', `Crawl #${number}`),
                text('p', '', `${t('status')}: ${result.job.status} · ${t('found')}: ${result.job.books_found} · ${t('errors')}: ${result.job.error_count}`),
              );
              (result.events || []).forEach(event => {
                detail.append(text('p', 'event-row', `${formatDate(event.created_at)} · ${event.level} · ${event.message}`));
              });
              detail.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            } catch (error) {
              toast(error.message, 'error');
            }
          });

          const remove = document.createElement('button');
          remove.type = 'button';
          remove.className = 'danger-link';
          remove.textContent = t('deleteCrawl');
          remove.disabled = ['PENDING', 'RUNNING'].includes(job.status);
          remove.title = remove.disabled ? t('crawlActiveCannotDelete') : '';
          remove.addEventListener('click', async () => {
            if (!confirm(t('deleteCrawlConfirm').replace('{id}', String(jobNumber)))) return;
            remove.disabled = true;
            try {
              await fetchJSON(`/api/jobs/${job.id}`, { method: 'DELETE' });
              $('history-detail').hidden = true;
              toast(t('crawlDeleted'), 'success');
              await loadHistory();
            } catch (error) {
              toast(error.message, 'error');
              remove.disabled = false;
            }
          });

          const actions = el('div', 'history-actions');
          actions.append(details, remove);
          const cell = document.createElement('td');
          cell.append(actions);
          row.append(cell);
          tbody.append(row);
        }
      } catch (e) { tbody.replaceChildren(); $('history-error').textContent = e.message; $('history-error').hidden = false; }
    }

    await loadHistory();
  }

  async function analyticsPage() {
    try {
      const data = await fetchJSON('/api/analytics'); const p = data.prices;
      $('an-total').textContent = Number(p.total || 0).toLocaleString(locale === 'vi' ? 'vi-VN' : 'en-GB');
      $('an-min').textContent = p.minimum === null ? '—' : pounds(p.minimum);
      $('an-max').textContent = p.maximum === null ? '—' : pounds(p.maximum);
      $('an-avg').textContent = p.average === null ? '—' : pounds(p.average);
      const chart = $('an-ratings'); let ratingTotal = 0; chart.replaceChildren();
      const max = Math.max(...data.rating_distribution.map(x => x.count), 1);
      data.rating_distribution.forEach(item => {
        ratingTotal += item.count; const line = el('div', 'analytics-bar-row');
        line.append(text('span', '', `${item.rating} ★`)); const track = el('div', 'analytics-track'); const fill = el('span', 'analytics-fill'); fill.style.width = `${(item.count / max) * 100}%`; track.append(fill); line.append(track, text('strong', '', item.count)); chart.append(line);
      });
      $('an-rating-empty').hidden = ratingTotal !== 0;
      const cat = $('an-categories'); cat.replaceChildren(); const catMax = Math.max(...data.categories.map(x => x.total_books), 1);
      data.categories.forEach(item => {
        const row = el('div', 'category-row'); const meta = el('div', 'category-meta'); meta.append(text('strong', '', item.category), text('span', '', item.total_books));
        const track = el('div', 'analytics-track'); const fill = el('span', 'analytics-fill'); fill.style.width = `${item.total_books / catMax * 100}%`; track.append(fill); row.append(meta, track); cat.append(row);
      });
      $('an-category-empty').hidden = data.categories.length > 0;
    } catch (e) { toast(e.message, 'error'); }
  }

  function settingsPage() {
    async function submit(form, endpoint, method, values, after) {
      const button = form.querySelector('[type="submit"]'); button.disabled = true;
      try { const data = await fetchJSON(endpoint, { method, body: JSON.stringify(values) }); toast(t('confirmed'), 'success'); after?.(data); } catch (e) { toast(e.message, 'error'); } finally { button.disabled = false; }
    }
    setupAvatarEditor();
    $('profile-form').addEventListener('submit', e => { e.preventDefault(); submit(e.currentTarget, '/api/me/profile', 'PATCH', { full_name: $('profile-name').value }, () => location.reload()); });
    $('preferences-form').addEventListener('submit', e => { e.preventDefault(); submit(e.currentTarget, '/api/me/preferences', 'PATCH', { locale: $('pref-locale').value, theme: $('pref-theme').value, book_layout: $('pref-layout').value }, () => location.reload()); });
    $('change-password-form').addEventListener('submit', e => {
      e.preventDefault(); if ($('next-pass').value !== $('next-pass-confirm').value) { toast(locale === 'vi' ? 'Xác nhận mật khẩu chưa đúng.' : 'Passwords do not match.', 'error'); return; }
      submit(e.currentTarget, '/api/me/password', 'POST', { current_password: $('current-pass').value, new_password: $('next-pass').value }, () => location.assign('/login'));
    });
    $('logout-settings').addEventListener('click', async () => { if (!confirm(t('logout'))) return; try { await fetchJSON('/api/auth/logout', { method: 'POST', body: '{}' }); location.assign('/'); } catch (e) { toast(e.message, 'error'); } });
  }

  function setupAvatarEditor() {
    const canvas = $('avatar-canvas');
    const context = canvas.getContext('2d');
    const input = $('avatar-file');
    const zoomControl = $('avatar-zoom');
    const saveButton = $('save-avatar');
    const placeholder = $('avatar-placeholder');
    const status = $('avatar-status');
    let image = null;
    let zoom = 1;
    let offsetX = 0;
    let offsetY = 0;
    let drag = null;

    const showStatus = message => {
      status.textContent = message;
      status.hidden = !message;
    };
    const clampOffset = () => {
      if (!image) return;
      const scale = Math.max(canvas.width / image.naturalWidth, canvas.height / image.naturalHeight) * zoom;
      const centeredX = (canvas.width - image.naturalWidth * scale) / 2;
      const centeredY = (canvas.height - image.naturalHeight * scale) / 2;
      offsetX = Math.max(canvas.width - image.naturalWidth * scale - centeredX, Math.min(-centeredX, offsetX));
      offsetY = Math.max(canvas.height - image.naturalHeight * scale - centeredY, Math.min(-centeredY, offsetY));
    };
    const render = () => {
      context.clearRect(0, 0, canvas.width, canvas.height);
      if (!image) return;
      clampOffset();
      const scale = Math.max(canvas.width / image.naturalWidth, canvas.height / image.naturalHeight) * zoom;
      const width = image.naturalWidth * scale;
      const height = image.naturalHeight * scale;
      context.drawImage(
        image,
        (canvas.width - width) / 2 + offsetX,
        (canvas.height - height) / 2 + offsetY,
        width,
        height,
      );
    };
    const useImage = nextImage => {
      image = nextImage;
      zoom = 1;
      offsetX = 0;
      offsetY = 0;
      zoomControl.value = '1';
      zoomControl.disabled = false;
      saveButton.disabled = false;
      placeholder.hidden = true;
      render();
    };

    const existing = $('avatar-source');
    if (existing) {
      existing.addEventListener('load', () => useImage(existing));
      existing.addEventListener('error', () => showStatus(t('avatarLoadFailed')));
      if (existing.complete && existing.naturalWidth) useImage(existing);
    }

    input.addEventListener('change', () => {
      const file = input.files?.[0];
      if (!file) return;
      if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type) || file.size > 12 * 1024 * 1024) {
        showStatus(t('avatarInvalidFile'));
        input.value = '';
        return;
      }
      const nextImage = new Image();
      nextImage.onload = () => {
        if (nextImage.naturalWidth > 8192 || nextImage.naturalHeight > 8192
          || nextImage.naturalWidth * nextImage.naturalHeight > 32000000) {
          showStatus(t('avatarInvalidFile'));
          return;
        }
        useImage(nextImage);
        showStatus('');
      };
      nextImage.onerror = () => {
        showStatus(t('avatarInvalidFile'));
      };
      const reader = new FileReader();
      reader.onload = () => {
        if (typeof reader.result === 'string') nextImage.src = reader.result;
        else showStatus(t('avatarInvalidFile'));
      };
      reader.onerror = () => showStatus(t('avatarInvalidFile'));
      reader.readAsDataURL(file);
    });

    zoomControl.addEventListener('input', () => {
      zoom = Number(zoomControl.value);
      render();
    });
    canvas.addEventListener('pointerdown', event => {
      if (!image) return;
      canvas.setPointerCapture(event.pointerId);
      const bounds = canvas.getBoundingClientRect();
      drag = {
        pointerId: event.pointerId,
        x: event.clientX,
        y: event.clientY,
        offsetX,
        offsetY,
        ratioX: canvas.width / bounds.width,
        ratioY: canvas.height / bounds.height,
      };
    });
    canvas.addEventListener('pointermove', event => {
      if (!drag || drag.pointerId !== event.pointerId) return;
      offsetX = drag.offsetX + (event.clientX - drag.x) * drag.ratioX;
      offsetY = drag.offsetY + (event.clientY - drag.y) * drag.ratioY;
      render();
    });
    canvas.addEventListener('pointerup', () => { drag = null; });
    canvas.addEventListener('pointercancel', () => { drag = null; });

    saveButton.addEventListener('click', async () => {
      if (!image) return;
      saveButton.disabled = true;
      showStatus('');
      try {
        const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
        if (!blob || blob.size > 4 * 1024 * 1024) throw new Error(t('avatarInvalidFile'));
        const formData = new FormData();
        formData.append('avatar', blob, 'avatar.png');
        await fetchJSON('/api/me/avatar', { method: 'POST', body: formData });
        const avatarUrl = `/api/me/avatar?v=${Date.now()}`;
        document.querySelectorAll('.user-avatar,.top-avatar').forEach(element => {
          const avatar = document.createElement('img');
          avatar.src = avatarUrl;
          avatar.alt = '';
          element.replaceChildren(avatar);
        });
        showStatus(t('avatarSaved'));
        toast(t('avatarSaved'), 'success');
      } catch (error) {
        showStatus(error.message);
        toast(error.message, 'error');
      } finally {
        saveButton.disabled = false;
      }
    });
  }

  if ($('saved-grid')) savedPage(); if ($('history-tbody')) historyPage(); if ($('an-ratings')) analyticsPage(); if ($('profile-form')) settingsPage();
})();
