(() => {
  'use strict';
  const app = window.CrawlInsight;
  const form = document.getElementById('auth-form');
  if (!form) return;

  const mode = form.dataset.mode;
  const error = document.getElementById('auth-error');
  const success = document.getElementById('auth-success');
  const value = (id) => {
    const el = document.getElementById(id);
    return el ? el.value.trim() : '';
  };

  const isVi = app.locale === 'vi';

  // Eye reveal buttons (password toggle)
  document.querySelectorAll('.reveal').forEach((button) => {
    button.addEventListener('click', () => {
      const targetId = button.dataset.reveal;
      const input = document.getElementById(targetId);
      if (!input) return;
      const isPassword = input.type === 'password';
      input.type = isPassword ? 'text' : 'password';
      const eyeOn = button.querySelector('.icon-eye');
      const eyeOff = button.querySelector('.icon-eye-off');
      if (eyeOn) eyeOn.hidden = isPassword;
      if (eyeOff) eyeOff.hidden = !isPassword;
    });
  });

  // Common error / success helpers
  const showError = (msg) => {
    if (success) success.hidden = true;
    if (error) {
      error.textContent = msg;
      error.hidden = false;
    }
  };

  const showSuccess = (msg) => {
    if (error) error.hidden = true;
    if (success) {
      success.textContent = msg;
      success.hidden = false;
    }
  };

  const clearMessages = () => {
    if (error) {
      error.hidden = true;
      error.textContent = '';
    }
    if (success) {
      success.hidden = true;
      success.textContent = '';
    }
  };

  // -------------------------------------------------------------
  // Handle Login & Register (Single step standard flow)
  // -------------------------------------------------------------
  if (['login', 'register'].includes(mode)) {
    const submitBtn = document.getElementById('auth-submit');
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      clearMessages();
      if (submitBtn) submitBtn.disabled = true;

      const payload = {};
      let path = '';
      if (mode === 'login') {
        path = '/api/auth/login';
        payload.email = value('auth-email');
        payload.password = value('auth-password');
        if (!payload.email || !payload.password) {
          showError(isVi ? 'Vui lòng điền đầy đủ email và mật khẩu.' : 'Please enter email and password.');
          if (submitBtn) submitBtn.disabled = false;
          return;
        }
      } else {
        path = '/api/auth/register';
        payload.full_name = value('full-name');
        payload.email = value('auth-email');
        payload.password = value('auth-password');
        const confirm = value('confirm-password');

        if (!payload.full_name || !payload.email || !payload.password) {
          showError(isVi ? 'Vui lòng điền đầy đủ thông tin.' : 'Please fill in all fields.');
          if (submitBtn) submitBtn.disabled = false;
          return;
        }
        if (payload.password !== confirm) {
          showError(isVi ? 'Xác nhận mật khẩu không trùng khớp.' : 'Passwords do not match.');
          if (submitBtn) submitBtn.disabled = false;
          return;
        }
        if (!/\d/.test(payload.password) || !/[A-Za-z]/.test(payload.password) || payload.password.length < 10) {
          showError(isVi ? 'Mật khẩu cần từ 10 ký tự, gồm chữ và số.' : 'Password needs 10+ characters, letters and numbers.');
          if (submitBtn) submitBtn.disabled = false;
          return;
        }
      }

      try {
        await app.fetchJSON(path, { method: 'POST', body: JSON.stringify(payload) });
        location.assign('/workspace');
      } catch (exception) {
        showError(exception.message);
      } finally {
        if (submitBtn) submitBtn.disabled = false;
      }
    });
    return;
  }

  // -------------------------------------------------------------
  // Multi-step Password Recovery (Forgot & Reset)
  // Step 1: Request OTP (Email)
  // Step 2: Verify OTP (6 digits, auto-check, exception handling)
  // Step 3: New Password (Set & redirect)
  // -------------------------------------------------------------
  const titleEl = document.getElementById('auth-title');
  const introEl = document.getElementById('auth-intro');
  const symbolMail = document.getElementById('symbol-mail');
  const symbolShield = document.getElementById('symbol-shield');
  const symbolLock = document.getElementById('symbol-lock');

  const stepEmailPane = document.getElementById('step-email');
  const stepOtpPane = document.getElementById('step-otp');
  const stepPasswordPane = document.getElementById('step-password');

  const emailInput = document.getElementById('auth-email');
  const emailSubmitBtn = document.getElementById('auth-submit');
  const otpSentEmail = document.getElementById('otp-sent-email');
  const hiddenOtpInput = document.getElementById('auth-otp');
  const otpBoxesContainer = document.getElementById('otp-boxes');
  const otpDigits = Array.from(document.querySelectorAll('.otp-digit'));
  const otpCheckingBadge = document.getElementById('otp-checking');
  const resendBtn = document.getElementById('btn-resend-otp');
  const resendCountdown = document.getElementById('resend-countdown');
  const changeEmailBtn = document.getElementById('btn-change-email');

  const newPasswordInput = document.getElementById('auth-password');
  const confirmPasswordInput = document.getElementById('confirm-password');
  const updatePasswordBtn = document.getElementById('btn-update-password');

  // Recovery state
  const state = {
    email: '',
    token: form.dataset.resetToken || '',
    otp: '',
    step: 1, // 1: email, 2: otp, 3: password
    isVerifying: false,
    resendTimer: null,
    cooldownSeconds: 0,
  };

  const setSymbol = (type) => {
    if (symbolMail) symbolMail.hidden = type !== 'mail';
    if (symbolShield) symbolShield.hidden = type !== 'shield';
    if (symbolLock) symbolLock.hidden = type !== 'lock';
  };

  const goToStep = (stepNumber) => {
    state.step = stepNumber;
    clearMessages();

    if (stepEmailPane) stepEmailPane.hidden = stepNumber !== 1;
    if (stepOtpPane) stepOtpPane.hidden = stepNumber !== 2;
    if (stepPasswordPane) stepPasswordPane.hidden = stepNumber !== 3;

    if (stepNumber === 1) {
      setSymbol('mail');
      if (titleEl) titleEl.textContent = isVi ? 'Khôi phục tài khoản' : 'Recover your account';
      if (introEl) introEl.textContent = isVi ? 'Nhập email để nhận mã xác thực OTP (hiệu lực 20 phút).' : 'Enter your email to receive a 6-digit OTP code (valid for 20 minutes).';
      if (emailInput) setTimeout(() => emailInput.focus(), 80);
    } else if (stepNumber === 2) {
      setSymbol('shield');
      if (titleEl) titleEl.textContent = isVi ? 'Xác thực mã OTP' : 'Verify OTP Code';
      if (introEl) introEl.textContent = isVi ? 'Vui lòng nhập mã OTP gồm 6 chữ số đã được gửi đến email của bạn.' : 'Please enter the 6-digit verification code sent to your email.';
      if (otpSentEmail) otpSentEmail.textContent = state.email || '';
      clearOtpBoxes();
      setTimeout(() => {
        if (otpDigits[0]) otpDigits[0].focus();
      }, 80);
    } else if (stepNumber === 3) {
      setSymbol('lock');
      if (titleEl) titleEl.textContent = isVi ? 'Tạo mật khẩu mới' : 'Choose a new password';
      if (introEl) introEl.textContent = isVi ? 'Mật khẩu mới phải có tối thiểu 10 ký tự, gồm cả chữ và số.' : 'Use at least 10 characters, including letters and numbers.';
      if (newPasswordInput) setTimeout(() => newPasswordInput.focus(), 80);
    }
  };

  // Cooldown countdown for resend
  const startResendCooldown = (seconds = 60) => {
    if (state.resendTimer) clearInterval(state.resendTimer);
    state.cooldownSeconds = seconds;
    if (resendBtn) resendBtn.hidden = true;
    if (resendCountdown) {
      resendCountdown.hidden = false;
      resendCountdown.textContent = isVi ? `Gửi lại sau ${state.cooldownSeconds}s` : `Resend in ${state.cooldownSeconds}s`;
    }

    state.resendTimer = setInterval(() => {
      state.cooldownSeconds -= 1;
      if (state.cooldownSeconds <= 0) {
        clearInterval(state.resendTimer);
        state.resendTimer = null;
        if (resendCountdown) resendCountdown.hidden = true;
        if (resendBtn) {
          resendBtn.hidden = false;
          resendBtn.disabled = false;
        }
      } else if (resendCountdown) {
        resendCountdown.textContent = isVi ? `Gửi lại sau ${state.cooldownSeconds}s` : `Resend in ${state.cooldownSeconds}s`;
      }
    }, 1000);
  };

  // OTP digit manipulation
  const clearOtpBoxes = () => {
    otpDigits.forEach((input) => {
      input.value = '';
      input.classList.remove('error', 'success');
      input.disabled = false;
    });
    if (hiddenOtpInput) hiddenOtpInput.value = '';
    state.otp = '';
  };

  const getEnteredOtp = () => {
    return otpDigits.map((input) => input.value).join('');
  };

  const shakeOtpBoxes = () => {
    if (otpBoxesContainer) {
      otpBoxesContainer.classList.add('shake');
      setTimeout(() => otpBoxesContainer.classList.remove('shake'), 450);
    }
    otpDigits.forEach((box) => box.classList.add('error'));
  };

  // Automatic verification of OTP when 6 digits are typed
  const verifyCurrentOtp = async () => {
    const otp = getEnteredOtp();
    if (otp.length !== 6 || !/^\d{6}$/.test(otp)) {
      showError(isVi ? 'Mã OTP phải gồm đủ 6 chữ số.' : 'OTP code must be 6 digits.');
      shakeOtpBoxes();
      return;
    }

    if (state.isVerifying) return;
    state.isVerifying = true;
    clearMessages();

    // Show checking indicator and disable inputs
    if (otpCheckingBadge) otpCheckingBadge.hidden = false;
    otpDigits.forEach((input) => {
      input.disabled = true;
      input.classList.remove('error');
    });

    try {
      const payload = {
        otp,
        email: state.email,
        token: state.token || form.dataset.resetToken || '',
      };
      const res = await app.fetchJSON('/api/auth/verify-otp', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      if (res.reset_token) {
        state.token = res.reset_token;
      }
      state.otp = otp;
      if (hiddenOtpInput) hiddenOtpInput.value = otp;

      // Highlight success
      otpDigits.forEach((input) => input.classList.add('success'));

      setTimeout(() => {
        goToStep(3);
      }, 350);
    } catch (exception) {
      shakeOtpBoxes();
      let msg = exception.message || (isVi ? 'Mã OTP không chính xác. Vui lòng kiểm tra lại.' : 'Invalid OTP code.');
      if (exception.code === 'INVALID_OTP') {
        msg = isVi ? 'Mã OTP không chính xác. Vui lòng kiểm tra lại.' : 'Invalid OTP code. Please try again.';
      } else if (exception.code === 'OTP_EXPIRED') {
        msg = isVi ? 'Mã OTP đã hết hạn sau 20 phút. Vui lòng gửi lại mã mới.' : 'OTP has expired. Please request a new one.';
      } else if (exception.code === 'OTP_ALREADY_USED') {
        msg = isVi ? 'Mã OTP này đã được sử dụng. Vui lòng yêu cầu mã mới.' : 'This OTP has already been used.';
      } else if (exception.code === 'TOO_MANY_ATTEMPTS') {
        msg = isVi ? 'Bạn đã nhập sai mã OTP quá nhiều lần. Vui lòng thử lại sau 30 phút.' : 'Too many incorrect attempts. Please try again in 30 minutes.';
      }
      showError(msg);
      // Clear values and refocus digit 1 for immediate retry
      setTimeout(() => {
        clearOtpBoxes();
        if (otpDigits[0]) otpDigits[0].focus();
      }, 300);
    } finally {
      state.isVerifying = false;
      if (otpCheckingBadge) otpCheckingBadge.hidden = true;
      otpDigits.forEach((input) => {
        input.disabled = false;
      });
    }
  };

  // Wire up the 6 OTP input boxes
  otpDigits.forEach((input, index) => {
    // Only allow single digit 0-9
    input.addEventListener('input', () => {
      const val = input.value.replace(/\D/g, '');
      input.value = val ? val[val.length - 1] : '';
      input.classList.remove('error');

      const fullOtp = getEnteredOtp();
      if (hiddenOtpInput) hiddenOtpInput.value = fullOtp;

      if (input.value && index < 5) {
        otpDigits[index + 1].focus();
      }

      // When all 6 digits are filled: AUTOMATIC CHECK WITHOUT BUTTON!
      if (fullOtp.length === 6) {
        verifyCurrentOtp();
      }
    });

    input.addEventListener('keydown', (event) => {
      if (event.key === 'Backspace') {
        if (!input.value && index > 0) {
          otpDigits[index - 1].focus();
          otpDigits[index - 1].value = '';
          if (hiddenOtpInput) hiddenOtpInput.value = getEnteredOtp();
        } else {
          input.value = '';
          if (hiddenOtpInput) hiddenOtpInput.value = getEnteredOtp();
        }
      } else if (event.key === 'ArrowLeft' && index > 0) {
        otpDigits[index - 1].focus();
      } else if (event.key === 'ArrowRight' && index < 5) {
        otpDigits[index + 1].focus();
      }
    });

    input.addEventListener('paste', (event) => {
      event.preventDefault();
      const pasteData = (event.clipboardData || window.clipboardData).getData('text');
      const digitsOnly = pasteData.replace(/\D/g, '').slice(0, 6);
      if (!digitsOnly) return;

      digitsOnly.split('').forEach((char, i) => {
        if (otpDigits[i]) {
          otpDigits[i].value = char;
          otpDigits[i].classList.remove('error');
        }
      });

      const fullOtp = getEnteredOtp();
      if (hiddenOtpInput) hiddenOtpInput.value = fullOtp;

      const nextFocus = Math.min(digitsOnly.length, 5);
      if (otpDigits[nextFocus]) otpDigits[nextFocus].focus();

      if (fullOtp.length === 6) {
        verifyCurrentOtp();
      }
    });
  });

  // Step 1: Submit email to request OTP
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (state.step === 1) {
      clearMessages();
      const email = value('auth-email');
      if (!email || !email.includes('@')) {
        showError(isVi ? 'Vui lòng nhập địa chỉ email hợp lệ.' : 'Please enter a valid email address.');
        return;
      }

      if (emailSubmitBtn) emailSubmitBtn.disabled = true;
      try {
        const res = await app.fetchJSON('/api/auth/request-reset', {
          method: 'POST',
          body: JSON.stringify({ email }),
        });

        state.email = email;
        if (res.reset_token) {
          state.token = res.reset_token;
        }

        if (res.local_test_otp) {
          console.info('[Dev] Local test OTP:', res.local_test_otp);
        }

        goToStep(2);
        startResendCooldown(60);
      } catch (exception) {
        showError(exception.message);
      } finally {
        if (emailSubmitBtn) emailSubmitBtn.disabled = false;
      }
    }
  });

  // Resend OTP button
  if (resendBtn) {
    resendBtn.addEventListener('click', async () => {
      if (state.cooldownSeconds > 0 || !state.email) return;
      clearMessages();
      resendBtn.disabled = true;

      try {
        const res = await app.fetchJSON('/api/auth/request-reset', {
          method: 'POST',
          body: JSON.stringify({ email: state.email }),
        });
        if (res.reset_token) {
          state.token = res.reset_token;
        }
        showSuccess(isVi ? 'Đã gửi lại mã OTP mới. Vui lòng kiểm tra email!' : 'New OTP code sent. Please check your email!');
        clearOtpBoxes();
        if (otpDigits[0]) otpDigits[0].focus();
        startResendCooldown(60);
      } catch (exception) {
        showError(exception.message);
        resendBtn.disabled = false;
      }
    });
  }

  // Change email button
  if (changeEmailBtn) {
    changeEmailBtn.addEventListener('click', () => {
      if (state.resendTimer) clearInterval(state.resendTimer);
      goToStep(1);
    });
  }

  // Step 3: Submit new password
  if (updatePasswordBtn) {
    updatePasswordBtn.addEventListener('click', async () => {
      clearMessages();
      const password = value('auth-password');
      const confirm = value('confirm-password');

      if (!password || !confirm) {
        showError(isVi ? 'Vui lòng nhập đầy đủ mật khẩu mới và xác nhận mật khẩu.' : 'Please enter new password and confirmation.');
        return;
      }

      if (password !== confirm) {
        showError(isVi ? 'Xác nhận mật khẩu không trùng khớp.' : 'Passwords do not match.');
        return;
      }

      if (password.length < 10 || !/\d/.test(password) || !/[A-Za-z]/.test(password)) {
        showError(isVi ? 'Mật khẩu cần từ 10 ký tự, gồm cả chữ và số.' : 'Password needs 10+ characters, letters and numbers.');
        return;
      }

      updatePasswordBtn.disabled = true;
      try {
        const payload = {
          token: state.token || form.dataset.resetToken || '',
          otp: state.otp || getEnteredOtp() || (hiddenOtpInput ? hiddenOtpInput.value : ''),
          password,
          email: state.email || '',
        };

        await app.fetchJSON('/api/auth/reset-password', {
          method: 'POST',
          body: JSON.stringify(payload),
        });

        showSuccess(isVi ? 'Đặt lại mật khẩu thành công! Đang chuyển hướng về đăng nhập...' : 'Password reset successfully! Redirecting to sign-in...');
        setTimeout(() => {
          location.assign('/login');
        }, 1400);
      } catch (exception) {
        showError(exception.message);
        updatePasswordBtn.disabled = false;
      }
    });
  }

  // Initialize view based on initial mode
  if (mode === 'reset' && form.dataset.resetToken) {
    state.token = form.dataset.resetToken;
    goToStep(2);
  } else {
    goToStep(1);
  }
})();
