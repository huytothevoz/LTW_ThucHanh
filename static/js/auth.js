(() => {
  'use strict';
  const app = window.CrawlInsight;
  const form = document.getElementById('auth-form');
  if (!form) return;

  const mode = form.dataset.mode;
  const error = document.getElementById('auth-error');
  const success = document.getElementById('auth-success');
  const button = document.getElementById('auth-submit');
  const value = (id) => document.getElementById(id).value;

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    error.hidden = true;
    success.hidden = true;
    button.disabled = true;

    const payload = {};
    let path = '';
    if (mode === 'login') {
      path = '/api/auth/login';
      payload.email = value('auth-email');
      payload.password = value('auth-password');
    }
    if (mode === 'register') {
      path = '/api/auth/register';
      payload.full_name = value('full-name');
      payload.email = value('auth-email');
      payload.password = value('auth-password');
    }
    if (mode === 'forgot') {
      path = '/api/auth/request-reset';
      payload.email = value('auth-email');
    }
    if (mode === 'reset') {
      path = '/api/auth/reset-password';
      payload.token = form.dataset.resetToken;
      payload.otp = value('auth-otp').trim();
      payload.password = value('auth-password');
      if (!/^\d{6}$/.test(payload.otp)) {
        error.textContent = app.locale === 'vi' ? 'Vui lòng nhập mã OTP gồm 6 chữ số.' : 'Enter the 6-digit OTP code.';
        error.hidden = false;
        button.disabled = false;
        return;
      }
    }

    if (['register', 'reset'].includes(mode) && payload.password !== value('confirm-password')) {
      error.textContent = app.locale === 'vi' ? 'Xác nhận mật khẩu không trùng khớp.' : 'Passwords do not match.';
      error.hidden = false;
      button.disabled = false;
      return;
    }
    if (['register', 'reset'].includes(mode) && (!/\d/.test(payload.password) || !/[A-Za-z]/.test(payload.password) || payload.password.length < 10)) {
      error.textContent = app.locale === 'vi' ? 'Mật khẩu cần từ 10 ký tự, gồm chữ và số.' : 'Password needs 10+ characters, letters and numbers.';
      error.hidden = false;
      button.disabled = false;
      return;
    }

    try {
      const data = await app.fetchJSON(path, { method: 'POST', body: JSON.stringify(payload) });
      if (['login', 'register'].includes(mode)) {
        location.assign('/workspace');
        return;
      }
      if (mode === 'reset') {
        success.textContent = app.locale === 'vi' ? 'Đặt lại mật khẩu thành công. Chuyển đến đăng nhập...' : 'Password reset. Redirecting to sign-in...';
        success.hidden = false;
        setTimeout(() => location.assign('/login'), 1400);
        return;
      }

      success.textContent = data.message;
      success.hidden = false;
      if (data.local_test_link) {
        const link = document.createElement('a');
        link.href = data.local_test_link;
        link.textContent = app.locale === 'vi' ? 'Liên kết khôi phục (chỉ để kiểm thử local)' : 'Local testing reset link';
        link.className = 'local-reset-link';
        success.append(document.createElement('br'), link);
      }
    } catch (exception) {
      error.textContent = exception.message;
      error.hidden = false;
    } finally {
      button.disabled = false;
    }
  });
})();
