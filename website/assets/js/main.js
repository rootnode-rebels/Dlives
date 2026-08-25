/**
 * DLives - Website Interactive Script
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Mobile Menu Toggle
  const hamburger = document.getElementById('nav-hamburger');
  const mobileMenu = document.getElementById('nav-mobile');
  
  if (hamburger && mobileMenu) {
    hamburger.addEventListener('click', () => {
      mobileMenu.classList.toggle('open');
      const expanded = mobileMenu.classList.contains('open');
      hamburger.setAttribute('aria-expanded', expanded);
    });

    // Close mobile menu on link click
    const mobileLinks = mobileMenu.querySelectorAll('a');
    mobileLinks.forEach(link => {
      link.addEventListener('click', () => {
        mobileMenu.classList.remove('open');
        hamburger.setAttribute('aria-expanded', 'false');
      });
    });
  }

  // 2. Sticky Navbar Glass Effect on Scroll
  const nav = document.getElementById('main-nav');
  if (nav) {
    window.addEventListener('scroll', () => {
      if (window.scrollY > 20) {
        nav.classList.add('scrolled');
      } else {
        nav.classList.remove('scrolled');
      }
    });
  }

  // 3. Scroll Reveal Animation for Sections
  const revealElements = document.querySelectorAll('.feature-row, .step-card, .req-card, .configurator-inner, .notif-inner');
  revealElements.forEach(el => el.classList.add('reveal'));

  const observerOptions = {
    threshold: 0.15,
    rootMargin: '0px 0px -40px 0px'
  };

  const revealObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, observerOptions);

  revealElements.forEach(el => revealObserver.observe(el));

  // 4. Hero Pill Live Clock & Interactive Simulation
  const pillClock = document.querySelector('.pill-clock');
  if (pillClock) {
    function updateClock() {
      const now = new Date();
      let hours = now.getHours();
      const minutes = String(now.getMinutes()).padStart(2, '0');
      const ampm = hours >= 12 ? 'PM' : 'AM';
      hours = hours % 12;
      hours = hours ? hours : 12;
      pillClock.textContent = `${hours}:${minutes} ${ampm}`;
    }
    updateClock();
    setInterval(updateClock, 1000);
  }

  // 5. FAQ Accordion Handler (for FAQ page and landing page if present)
  const faqItems = document.querySelectorAll('.faq-item');
  faqItems.forEach(item => {
    const question = item.querySelector('.faq-question');
    if (question) {
      question.addEventListener('click', () => {
        const isOpen = item.classList.contains('open');
        // Optional: close other open items in the same list
        const parentList = item.closest('.faq-list');
        if (parentList) {
          parentList.querySelectorAll('.faq-item').forEach(sibling => {
            if (sibling !== item) sibling.classList.remove('open');
          });
        }
        item.classList.toggle('open', !isOpen);
      });
    }
  });

  // 6. Smooth Scrolling for Internal Anchor Links
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      const href = this.getAttribute('href');
      if (href === '#DOWNLOAD_URL_PLACEHOLDER') {
        // Show gentle modal or alert if clicked before actual URL is configured
        e.preventDefault();
        alert('DLives v1.0 Installer download URL is currently being configured. Check back soon or contact support at suhashoskere@gmail.com.');
        return;
      }
      if (href && href.startsWith('#') && href.length > 1) {
        const targetElement = document.querySelector(href);
        if (targetElement) {
          e.preventDefault();
          targetElement.scrollIntoView({
            behavior: 'smooth'
          });
        }
      }
    });
  });

  // 7. Docs Sidebar Active Link Switching & Smooth Scrolling
  const sidebarLinks = document.querySelectorAll('.docs-sidebar .sidebar-link');
  sidebarLinks.forEach(link => {
    link.addEventListener('click', function(e) {
      const href = this.getAttribute('href');
      if (href && href.startsWith('#') && href.length > 1) {
        const target = document.querySelector(href);
        if (target) {
          e.preventDefault();
          sidebarLinks.forEach(l => l.classList.remove('active'));
          this.classList.add('active');
          target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }
    });
  });

  // 8. Support Page Interactive Actions (Copy Email, Bug Report, Feature Request)
  const copyEmailBtn = document.getElementById('copy-email-btn');
  const copyToast = document.getElementById('copy-toast');
  if (copyEmailBtn) {
    copyEmailBtn.addEventListener('click', () => {
      navigator.clipboard.writeText('suhashoskere@gmail.com').then(() => {
        if (copyToast) {
          copyToast.style.display = 'block';
          setTimeout(() => { copyToast.style.display = 'none'; }, 3000);
        }
      });
    });
  }

  // Bug Report Actions
  const sendBugBtn = document.getElementById('send-bug-btn');
  const copyBugBtn = document.getElementById('copy-bug-btn');
  const bugToast = document.getElementById('bug-toast');

  if (sendBugBtn) {
    sendBugBtn.addEventListener('click', () => {
      const sys = document.getElementById('bug-sys')?.value || 'Windows 11 / DLives v1.0';
      const msg = document.getElementById('bug-msg')?.value || '';
      const subject = `[DLives v1.0] Bug Report`;
      const body = `Category: Bug Report\nSystem Info: ${sys}\n\nDescription & Steps to Reproduce:\n${msg}`;
      const gmailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=suhashoskere@gmail.com&su=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
      const mailtoUrl = `mailto:suhashoskere@gmail.com?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
      
      const newWin = window.open(gmailUrl, '_blank');
      if (!newWin || newWin.closed || typeof newWin.closed === 'undefined') {
        window.location.href = mailtoUrl;
      }
    });
  }

  if (copyBugBtn) {
    copyBugBtn.addEventListener('click', () => {
      const sys = document.getElementById('bug-sys')?.value || 'Windows 11 / DLives v1.0';
      const msg = document.getElementById('bug-msg')?.value || '';
      const draft = `To: suhashoskere@gmail.com\nSubject: [DLives v1.0] Bug Report\n\nSystem: ${sys}\n\nDescription & Steps:\n${msg}`;
      navigator.clipboard.writeText(draft).then(() => {
        if (bugToast) {
          bugToast.style.display = 'inline-block';
          setTimeout(() => { bugToast.style.display = 'none'; }, 3000);
        }
      });
    });
  }

  // Feature Request Actions
  const sendFeatBtn = document.getElementById('send-feat-btn');
  const copyFeatBtn = document.getElementById('copy-feat-btn');
  const featToast = document.getElementById('feat-toast');

  if (sendFeatBtn) {
    sendFeatBtn.addEventListener('click', () => {
      const title = document.getElementById('feat-title')?.value || 'New Feature Idea';
      const msg = document.getElementById('feat-msg')?.value || '';
      const subject = `[DLives v1.0] Feature Request: ${title}`;
      const body = `Feature Name: ${title}\n\nConcept & Workflow Details:\n${msg}`;
      const gmailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=suhashoskere@gmail.com&su=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
      const mailtoUrl = `mailto:suhashoskere@gmail.com?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
      
      const newWin = window.open(gmailUrl, '_blank');
      if (!newWin || newWin.closed || typeof newWin.closed === 'undefined') {
        window.location.href = mailtoUrl;
      }
    });
  }

  if (copyFeatBtn) {
    copyFeatBtn.addEventListener('click', () => {
      const title = document.getElementById('feat-title')?.value || 'New Feature Idea';
      const msg = document.getElementById('feat-msg')?.value || '';
      const draft = `To: suhashoskere@gmail.com\nSubject: [DLives v1.0] Feature Request: ${title}\n\nConcept & Details:\n${msg}`;
      navigator.clipboard.writeText(draft).then(() => {
        if (featToast) {
          featToast.style.display = 'inline-block';
          setTimeout(() => { featToast.style.display = 'none'; }, 3000);
        }
      });
    });
  }
});

