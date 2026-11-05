(() => {
  'use strict';

  if (!document.body.classList.contains('is-marketing')) return;

  const AudioContextConstructor = window.AudioContext || window.webkitAudioContext;
  const landingPage = Boolean(document.querySelector('.landing-hero'));
  let audioContext = null;
  let audioUnavailable = false;

  const reportAudioError = error => {
    if (audioUnavailable) return;
    audioUnavailable = true;
    console.error('Public sound effects could not be initialized.', error);
  };

  const resumeAudio = async () => {
    if (audioUnavailable) return false;
    if (!AudioContextConstructor) {
      reportAudioError(new Error('Web Audio API is not supported.'));
      return false;
    }

    try {
      if (!audioContext) audioContext = new AudioContextConstructor();
    } catch (error) {
      reportAudioError(error);
      return false;
    }
    if (audioContext.state === 'suspended') {
      try {
        await audioContext.resume();
      } catch (error) {
        console.warn('The browser has not unlocked public sound effects yet.', error);
        return false;
      }
    }
    if (audioContext.state === 'closed') {
      reportAudioError(new Error('The audio context has been closed.'));
      return false;
    }
    return audioContext.state === 'running';
  };

  const playTone = (frequency, startAt, duration, volume) => {
    const oscillator = audioContext.createOscillator();
    const gain = audioContext.createGain();
    oscillator.type = 'sine';
    oscillator.frequency.setValueAtTime(frequency, startAt);
    oscillator.frequency.exponentialRampToValueAtTime(frequency * 0.94, startAt + duration);
    gain.gain.setValueAtTime(0.0001, startAt);
    gain.gain.exponentialRampToValueAtTime(volume, startAt + 0.014);
    gain.gain.exponentialRampToValueAtTime(0.0001, startAt + duration);
    oscillator.connect(gain);
    gain.connect(audioContext.destination);
    oscillator.start(startAt);
    oscillator.stop(startAt + duration);
  };

  const playClick = async () => {
    if (!await resumeAudio()) return;
    const now = audioContext.currentTime;
    playTone(680, now, 0.075, 0.11);
  };

  const playScrollChime = async direction => {
    if (!await resumeAudio()) return;
    const now = audioContext.currentTime;
    const notes = direction === 'up' ? [990, 660] : [740, 1110];
    playTone(notes[0], now, 0.17, 0.12);
    playTone(notes[1], now + 0.06, 0.21, 0.075);
  };

  const unlockAudio = () => {
    if (audioUnavailable || !AudioContextConstructor) {
      if (!AudioContextConstructor) reportAudioError(new Error('Web Audio API is not supported.'));
      return;
    }
    try {
      if (!audioContext) audioContext = new AudioContextConstructor();
    } catch (error) {
      reportAudioError(error);
      return;
    }
    if (audioContext.state === 'suspended') {
      audioContext.resume().catch(error => {
        console.warn('The browser has not unlocked public sound effects yet.', error);
      });
    }
  };

  document.addEventListener('pointerdown', unlockAudio, { capture: true, passive: true });
  document.addEventListener('keydown', unlockAudio, true);
  document.addEventListener('wheel', unlockAudio, { capture: true, passive: true });

  document.addEventListener('click', event => {
    if (!(event.target instanceof Element)) return;
    const interactive = event.target.closest(
      'main.marketing-main button, main.marketing-main input[type="submit"], main.marketing-main a.btn-hero, main.marketing-main a.btn-outline, .public-header button, .public-header .theme-toggle-button, .public-header a.header-action, .public-header a.public-signin, .public-header .public-links a',
    );
    if (interactive) void playClick();
  }, true);

  if (landingPage) {
    const sections = Array.from(document.querySelectorAll(
      '.landing-hero, .landing-manifesto, .landing-section, .cosmic-section, .landing-cta, .source-disclaimer',
    ));
    const activeSectionAt = () => {
      const marker = window.innerHeight * 0.58;
      return sections.reduce(
        (active, section) => section.getBoundingClientRect().top <= marker ? section : active,
        sections[0],
      );
    };

    let activeSection = activeSectionAt();
    let lastScrollY = window.scrollY;
    let scrollFramePending = false;

    window.addEventListener('scroll', () => {
      if (scrollFramePending) return;
      scrollFramePending = true;
      window.requestAnimationFrame(() => {
        const currentScrollY = window.scrollY;
        const nextSection = activeSectionAt();
        if (Math.abs(currentScrollY - lastScrollY) > 2 && nextSection && nextSection !== activeSection) {
          void playScrollChime(currentScrollY < lastScrollY ? 'up' : 'down');
        }
        activeSection = nextSection;
        lastScrollY = currentScrollY;
        scrollFramePending = false;
      });
    }, { passive: true });
  }
})();
