/* Dashboard -> Flask JSON APIs. No canned data and no fake progress percentage. */
(function () {
  'use strict';
  const { fetchJSON, toast, formatDate, t, locale } = window.CrawlInsight;
  const $ = (id) => document.getElementById(id);
  const ACTIVE = new Set(['PENDING', 'RUNNING']);
  const TERMINAL = new Set(['COMPLETED', 'FAILED']);
  const STATUS_TEXT = {
    PENDING: t('queued'), RUNNING: t('processing'), COMPLETED: t('done'), FAILED: t('failed'),
  };
  let trackedJobId = null;
  let pollingHandle = null;
  let fetchingJob = false;
  let loadingSummary = false;
  const heading = document.querySelector('.page-heading');

  const today = $('today-label');
  if (today) {
    const date = new Date();
    today.lastChild.textContent = ` ${new Intl.DateTimeFormat(locale==='vi'?'vi-VN':'en-GB', { weekday: 'short', month: 'short', day: 'numeric' }).format(date)}`;
  }

  function setStartDisabled(disabled) {
    const button = $('start-button');
    button.disabled = disabled;
    const content = button.querySelector('.button-content');
    if (content) {
      // Keep the existing SVG icon while updating the label.
      const textNodes = Array.from(content.childNodes).filter((node) => node.nodeType === Node.TEXT_NODE);
      if (textNodes.length) textNodes[textNodes.length - 1].textContent = disabled ? ` ${t('stop')}` : ` ${t('start')}`;
    }
  }

  function renderChart(distribution) {
    const data = Array.isArray(distribution) ? distribution : [];
    const total = data.reduce((sum, rating) => sum + Number(rating.count || 0), 0);
    const empty = $('rating-empty');
    const chart = $('rating-chart');
    empty.hidden = total > 0;
    chart.hidden = total === 0;
    chart.replaceChildren();
    if (total === 0) return;
    const biggest = Math.max(...data.map((bucket) => Number(bucket.count || 0)), 1);
    for (const bucket of data) {
      const count = Number(bucket.count || 0);
      const column = document.createElement('div');
      column.className = 'rating-column';
      column.setAttribute('aria-label', `${bucket.rating} stars: ${count} books`);
      const countLabel = document.createElement('span');
      countLabel.className = 'rating-count';
      countLabel.textContent = String(count);
      const track = document.createElement('div');
      track.className = 'rating-track';
      const bar = document.createElement('div');
      bar.className = 'rating-bar';
      bar.style.height = count ? `${(count / biggest) * 100}%` : '0';
      track.append(bar);
      const tick = document.createElement('span');
      tick.className = 'rating-tick';
      tick.textContent = `${bucket.rating} `;
      const star = document.createElement('span');
      star.className = 'star-symbol';
      star.textContent = '★';
      tick.append(star);
      column.append(countLabel, track, tick);
      chart.append(column);
    }
  }

  function renderHistory(jobs) {
    const list = $('history-list');
    $('history-loading').hidden = true;
    $('history-empty').hidden = jobs.length > 0;
    list.hidden = jobs.length === 0;
    list.replaceChildren();
    for (const job of jobs) {
      const item = document.createElement('div');
      item.className = 'history-item';
      const icon = document.createElement('div');
      icon.className = 'history-item-icon';
      icon.textContent = '#';
      const content = document.createElement('div');
      content.className = 'history-text';
      const displayNumber = Number(job.user_job_number || job.id || 0);
      const title = document.createElement('strong');
      title.textContent = locale==='vi' ? `Phiên thu thập #${displayNumber}` : `Crawl session #${displayNumber}`;
      const subtitle = document.createElement('span');
      subtitle.textContent = `${formatDate(job.created_at)} · ${job.items_saved} ${t('saved')} · ${job.max_pages} ${t('pages')}`;
      content.append(title, subtitle);
      const status = document.createElement('span');
      status.className = `status-badge status-${job.status.toLowerCase()}`;
      status.textContent = STATUS_TEXT[job.status] || job.status;
      item.append(icon, content, status);
      list.append(item);
    }
  }

  function showSummaryError(message) {
    let banner = $('dashboard-error-banner');
    if (!banner) {
      banner = document.createElement('div');
      banner.id = 'dashboard-error-banner';
      banner.className = 'inline-error';
      const action = document.createElement('button');
      action.type = 'button';
      action.textContent = 'Retry connection';
      action.style.cssText = 'margin-left:14px;border:0;background:#fff;padding:7px 11px;border-radius:6px;font-weight:750;color:#9c5155';
      action.addEventListener('click', loadSummary);
      const text = document.createElement('span');
      banner.append(text, action);
      heading.insertAdjacentElement('afterend', banner);
    }
    banner.querySelector('span').textContent = `${message} `;
  }

  function renderSummary(data) {
    $('dashboard-error-banner')?.remove();
    $('total-books').textContent = Number(data.total_books).toLocaleString(locale==='vi'?'vi-VN':'en-GB');
    $('completed-jobs').textContent = Number(data.completed_jobs).toLocaleString(locale==='vi'?'vi-VN':'en-GB');
    if ($('saved-count')) $('saved-count').textContent = Number(data.saved_books || 0).toLocaleString(locale==='vi'?'vi-VN':'en-GB');
    $('last-status').textContent = data.last_job ? (STATUS_TEXT[data.last_job.status] || data.last_job.status) : t('noData');
    const lastJobNumber = data.last_job ? Number(data.last_job.user_job_number || data.last_job.id || 0) : null;
    $('last-job-meta').textContent = data.last_job ? `Job #${lastJobNumber} · ${formatDate(data.last_job.created_at)}` : t('noData');
    renderChart(data.rating_distribution);
    renderHistory(data.recent_jobs || []);
    if (data.last_job && ACTIVE.has(data.last_job.status)) {
      if (trackedJobId !== data.last_job.id) trackJob(data.last_job.id);
    } else if (trackedJobId === null && data.last_job) {
      // Display completed/failed last job without restarting a poll cycle.
      showJob(data.last_job.id);
    }
  }

  async function loadSummary() {
    if (loadingSummary) return;
    loadingSummary = true;
    try {
      const data = await fetchJSON('/api/summary');
      renderSummary(data);
    } catch (error) {
      showSummaryError(`Cannot load dashboard: ${error.message}`);
      toast('Dashboard could not load. Check the local server.', 'error');
    } finally {
      loadingSummary = false;
    }
  }

  function renderJob(job) {
    $('monitor-empty').hidden = true;
    $('monitor-active').hidden = false;
    const displayNumber = Number(job.user_job_number || job.id || 0);
    $('job-title').textContent = `Crawl #${displayNumber}`;
    const badge = $('job-status-badge');
    badge.className = `status-badge status-${job.status.toLowerCase()}`;
    badge.textContent = job.status === 'COMPLETED' && job.error_count > 0
      ? 'Completed with warnings' : STATUS_TEXT[job.status] || job.status;
    $('job-pages').textContent = String(job.catalogue_pages_done);
    $('job-found').textContent = String(job.books_found);
    $('job-saved').textContent = String(job.items_saved);
    $('job-new').textContent = String(job.new_books);
    $('job-existing').textContent = String(job.existing_books);
    $('job-errors').textContent = String(job.error_count);
    const dot = $('monitor-status-dot');
    dot.className = `status-dot is-${job.status.toLowerCase()}`;
    const messages = {
      PENDING: (locale==='vi'?'Đã xếp hàng chờ khởi chạy crawler.':'Queued for crawler startup.'),
      RUNNING: (locale==='vi'?'Đang thu thập từ nguồn cho phép; cập nhật mỗi 2 giây.':'Crawling the approved source; refreshing every 2 seconds.'),
      COMPLETED: job.error_count > 0 ? t('completedWithErrors') : (locale==='vi'?'Đã hoàn tất. Có thể mở kho sách.':'Crawl complete. Books are ready to explore.'),
      FAILED: (locale==='vi'?'Crawler không thể hoàn tất phiên này.':'The crawler failed to finish this job.'),
    };
    $('job-description').textContent = messages[job.status] || (locale==='vi'?'Đang kiểm tra trạng thái...':'Checking job status...');
    const err = $('job-error-text');
    err.hidden = !job.last_error;
    if (job.last_error) err.textContent = job.last_error;
    $('monitor-updated').textContent = ACTIVE.has(job.status)
      ? (locale==='vi'?'Đang cập nhật · mỗi 2 giây':'Live status · every 2 seconds') : `${t('last')} ${formatDate(job.finished_at || job.created_at)}`;
    setStartDisabled(ACTIVE.has(job.status));
  }

  async function showJob(jobId) {
    if (fetchingJob) return;
    fetchingJob = true;
    try {
      const { job } = await fetchJSON(`/api/jobs/${jobId}`);
      renderJob(job);
      if (TERMINAL.has(job.status) && trackedJobId === jobId) {
        stopPolling();
        await loadSummary();
      }
    } catch (error) {
      toast(`Cannot get crawl status: ${error.message}`, 'error');
      // Retry polling instead of inventing a finished state.
    } finally {
      fetchingJob = false;
    }
  }

  function stopPolling() {
    if (pollingHandle) clearInterval(pollingHandle);
    pollingHandle = null;
    trackedJobId = null;
  }

  function trackJob(jobId) {
    stopPolling();
    trackedJobId = jobId;
    setStartDisabled(true);
    showJob(jobId);
    pollingHandle = setInterval(() => showJob(jobId), 2000);
  }

  $('crawl-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const selected = document.querySelector('input[name="max-pages"]:checked');
    const maxPages = selected ? Number(selected.value) : 1;
    if (![1, 2, 3].includes(maxPages)) return;
    const sourceSelect = $('source-select');
    const sourceId = sourceSelect ? Number(sourceSelect.value) || 1 : 1;
    setStartDisabled(true);
    try {
      const { job } = await fetchJSON('/api/jobs', {
        method: 'POST', body: JSON.stringify({ max_pages: maxPages, source_id: sourceId }),
      });
      toast(`Crawl #${job.id} has been queued.`, 'success');
      trackJob(job.id);
      await loadSummary();
    } catch (error) {
      toast(error.message, 'error');
      if (error.status === 409) await loadSummary();
      else setStartDisabled(false);
    }
  });

  window.addEventListener('beforeunload', stopPolling);
  loadSummary();
})();
