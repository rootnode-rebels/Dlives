/**
 * Dlives - Official Website Engine (Minimal & Fast)
 */

document.addEventListener('DOMContentLoaded', () => {
  // ── 1. Microsoft Store Smart Launcher ────────────────────────
  const MS_STORE_APP_ID = '9P2XZRF8RLB2';
  const MS_STORE_WEB_URL = 'https://apps.microsoft.com/detail/9P2XZRF8RLB2?hl=en-us&gl=IN&ocid=pdpshare';
  const MS_STORE_URI = `ms-windows-store://pdp/?productid=${MS_STORE_APP_ID}`;

  function openMicrosoftStore(e) {
    if (e) e.preventDefault();
    const isWindows = /windows/i.test(navigator.userAgent);

    if (isWindows) {
      const fallbackTimer = setTimeout(() => {
        window.open(MS_STORE_WEB_URL, '_blank');
      }, 1200);

      window.location.href = MS_STORE_URI;

      window.addEventListener('blur', () => {
        clearTimeout(fallbackTimer);
      }, { once: true });
    } else {
      window.open(MS_STORE_WEB_URL, '_blank');
    }
  }

  document.querySelectorAll('.ms-store-trigger').forEach(btn => {
    btn.addEventListener('click', openMicrosoftStore);
  });

  // ── 2. Mobile Menu ───────────────────────────────────────────
  const hamburger = document.getElementById('nav-hamburger');
  const mobileMenu = document.getElementById('nav-mobile');
  
  if (hamburger && mobileMenu) {
    hamburger.addEventListener('click', () => {
      mobileMenu.classList.toggle('open');
    });

    mobileMenu.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        mobileMenu.classList.remove('open');
      });
    });
  }

  // ── 3. Real Dlives Bar Live Clock ─────────────────────────────
  const barClock = document.getElementById('bar-live-clock');
  const barDate = document.getElementById('bar-live-date');
  const barBattery = document.getElementById('bar-battery');
  const barMute = document.getElementById('bar-mute-toggle');
  const barCaps = document.getElementById('bar-caps');
  const barNum = document.getElementById('bar-num');

  const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  function updateBarClock() {
    const now = new Date();
    const h = String(now.getHours()).padStart(2, '0');
    const m = String(now.getMinutes()).padStart(2, '0');
    const s = String(now.getSeconds()).padStart(2, '0');
    if (barClock) barClock.textContent = `${h}:${m}:${s}`;
    
    if (barDate) {
      const dayName = DAYS[now.getDay()];
      const monName = MONTHS[now.getMonth()];
      const dayNum = String(now.getDate()).padStart(2, '0');
      barDate.textContent = `${dayName}, ${monName} ${dayNum}`;
    }
  }

  updateBarClock();
  setInterval(updateBarClock, 1000);

  if (barMute) {
    let muted = false;
    barMute.addEventListener('click', (e) => {
      e.stopPropagation();
      muted = !muted;
      barMute.style.opacity = muted ? '0.4' : '1';
    });
  }

  if (barCaps) {
    barCaps.addEventListener('click', (e) => {
      e.stopPropagation();
      barCaps.classList.toggle('active');
    });
  }

  if (barNum) {
    barNum.addEventListener('click', (e) => {
      e.stopPropagation();
      barNum.classList.toggle('active');
    });
  }

  // ── 4. Hero Tab Switcher ─────────────────────────────────────
  const tabButtons = document.querySelectorAll('.pill-tab-btn');
  const previewImg = document.getElementById('hero-preview-img');
  const previewTitle = document.getElementById('preview-active-title');

  const tabScreenshots = {
    'home': { src: 'assets/screenshots/home-tab.png', title: 'Home Dashboard' },
    'media': { src: 'assets/screenshots/control-media.png', title: 'Media & Tap-to-Seek' },
    'system': { src: 'assets/screenshots/system-diagnostics.png', title: 'System Telemetry' },
    'shelf': { src: 'assets/screenshots/clipboard-shelf.png', title: 'Clipboard & File Shelf' },
    'calendar': { src: 'assets/screenshots/calendar.png', title: 'Calendar & Events' },
    'alarms': { src: 'assets/screenshots/alarms.png', title: 'Alarms & Timetable' },
    'notes': { src: 'assets/screenshots/notes.png', title: 'Notes Scratchpad' },
    'settings': { src: 'assets/screenshots/settings.png', title: 'Island Preferences' }
  };

  if (tabButtons.length && previewImg) {
    tabButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const key = btn.getAttribute('data-tab');
        if (tabScreenshots[key]) {
          tabButtons.forEach(b => b.classList.remove('active'));
          btn.classList.add('active');

          previewImg.style.opacity = '0.3';
          setTimeout(() => {
            previewImg.src = tabScreenshots[key].src;
            if (previewTitle) previewTitle.textContent = tabScreenshots[key].title;
            previewImg.style.opacity = '1';
          }, 120);
        }
      });
    });
  }

  // Clicking the native Dlives bar cycles the preview tab
  const dlivesBar = document.getElementById('dlives-real-bar');
  if (dlivesBar && tabButtons.length) {
    let currentIdx = 0;
    dlivesBar.addEventListener('click', () => {
      currentIdx = (currentIdx + 1) % tabButtons.length;
      tabButtons[currentIdx].click();
    });
  }

  // ── 5. Lightbox Modal ────────────────────────────────────────
  const galleryItems = document.querySelectorAll('.gallery-item-clean');
  const lightboxModal = document.getElementById('lightbox-modal');
  const lightboxImg = document.getElementById('lightbox-img');
  const lightboxTitle = document.getElementById('lightbox-title');
  const lightboxClose = document.getElementById('lightbox-close');
  const lightboxOverlay = document.getElementById('lightbox-overlay');

  if (galleryItems.length && lightboxModal && lightboxImg) {
    galleryItems.forEach(item => {
      item.addEventListener('click', () => {
        const src = item.getAttribute('data-src');
        const title = item.getAttribute('data-title') || 'Screenshot';
        if (src) {
          lightboxImg.src = src;
          if (lightboxTitle) lightboxTitle.textContent = title;
          lightboxModal.classList.add('active');
          document.body.style.overflow = 'hidden';
        }
      });
    });

    function closeLightbox() {
      lightboxModal.classList.remove('active');
      document.body.style.overflow = '';
    }

    if (lightboxClose) lightboxClose.addEventListener('click', closeLightbox);
    if (lightboxOverlay) lightboxOverlay.addEventListener('click', closeLightbox);
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && lightboxModal.classList.contains('active')) {
        closeLightbox();
      }
    });
  }
});
