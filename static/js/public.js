/* ================================================================
   public.js — FakeNews Detector public site
================================================================ */
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    document.body.classList.add('loaded');
    initNavbarScroll();
    initHeroSlider();
    initCountUp();
    initFlashDismiss();
    initPasswordStrength();
    initPasswordToggle();
  });

  /* ──────────────────────────────────────────────────────────
     1. Navbar shadow on scroll
  ────────────────────────────────────────────────────────── */
  function initNavbarScroll() {
    var navbar = document.querySelector('.public-navbar');
    if (!navbar) return;
    function check() {
      if (window.scrollY > 20) navbar.classList.add('scrolled');
      else                     navbar.classList.remove('scrolled');
    }
    window.addEventListener('scroll', check, { passive: true });
    check();
  }

  /* ──────────────────────────────────────────────────────────
     2. Hero Slider (fade, auto 5s, dots, pause on hover)
  ────────────────────────────────────────────────────────── */
  function initHeroSlider() {
    var slides = document.querySelectorAll('.hero-slide');
    var dots   = document.querySelectorAll('.hero-dot');
    if (!slides.length) return;

    var current = 0;
    var total   = slides.length;
    var timer   = null;
    var paused  = false;
    var section = document.querySelector('.hero-section');

    function goTo(n) {
      slides[current].classList.remove('active');
      if (dots[current]) dots[current].classList.remove('active');
      current = ((n % total) + total) % total;
      slides[current].classList.add('active');
      if (dots[current]) dots[current].classList.add('active');
    }

    function startAuto() {
      clearInterval(timer);
      timer = setInterval(function () {
        if (!paused) goTo(current + 1);
      }, 5000);
    }

    // Init first active
    goTo(0);
    startAuto();

    // Dot clicks
    dots.forEach(function (dot, i) {
      dot.addEventListener('click', function () { goTo(i); startAuto(); });
    });

    // Arrows (optional)
    var prev = document.querySelector('.hero-prev');
    var next = document.querySelector('.hero-next');
    if (prev) prev.addEventListener('click', function () { goTo(current - 1); startAuto(); });
    if (next) next.addEventListener('click', function () { goTo(current + 1); startAuto(); });

    // Pause on hover
    if (section) {
      section.addEventListener('mouseenter', function () { paused = true; });
      section.addEventListener('mouseleave', function () { paused = false; });
    }
  }

  /* ──────────────────────────────────────────────────────────
     3. Count-up via IntersectionObserver
  ────────────────────────────────────────────────────────── */
  function initCountUp() {
    var els = document.querySelectorAll('.count-num');
    if (!els.length) return;

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var el     = entry.target;
        var target = parseInt(el.getAttribute('data-target') || el.textContent, 10);
        if (isNaN(target)) return;
        observer.unobserve(el);
        animateCount(el, target, 2000);
      });
    }, { threshold: 0.4 });

    els.forEach(function (el) { observer.observe(el); });
  }

  function animateCount(el, target, duration) {
    var start = 0, startTime = null;
    function step(ts) {
      if (!startTime) startTime = ts;
      var progress = Math.min((ts - startTime) / duration, 1);
      var value    = Math.floor((1 - Math.pow(1 - progress, 3)) * target);
      el.textContent = value.toLocaleString();
      if (progress < 1) requestAnimationFrame(step);
      else el.textContent = target.toLocaleString();
    }
    requestAnimationFrame(step);
  }

  /* ──────────────────────────────────────────────────────────
     4. Flash message auto-dismiss (5s)
  ────────────────────────────────────────────────────────── */
  function initFlashDismiss() {
    document.querySelectorAll('.flash-message, .alert').forEach(function (el) {
      setTimeout(function () { dismiss(el); }, 5000);
      var btn = el.querySelector('.flash-close, .btn-close, [data-bs-dismiss="alert"]');
      if (btn) btn.addEventListener('click', function () { dismiss(el); });
    });
  }

  function dismiss(el) {
    el.style.transition = 'opacity 0.4s ease, margin-top 0.4s ease';
    el.style.opacity    = '0';
    el.style.marginTop  = '-' + el.offsetHeight + 'px';
    setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 420);
  }

  /* ──────────────────────────────────────────────────────────
     5. Password strength meter (4 segments)
  ────────────────────────────────────────────────────────── */
  function initPasswordStrength() {
    var input    = document.getElementById('password');
    var segments = document.querySelectorAll('.strength-seg');
    var label    = document.getElementById('strength-label');
    if (!input || !segments.length) return;

    var colors = ['#e74c3c', '#e67e22', '#f1c40f', '#27ae60'];
    var labels = ['Weak', 'Fair', 'Good', 'Strong'];

    input.addEventListener('input', function () {
      var score = calcStrength(input.value);
      segments.forEach(function (seg, i) {
        seg.style.background = (i < score) ? colors[score - 1] : '#e0e0e0';
      });
      if (label) {
        label.textContent = input.value ? labels[score - 1] : '';
        label.style.color = input.value ? colors[score - 1] : 'transparent';
      }
    });
  }

  function calcStrength(pw) {
    if (!pw) return 0;
    var s = 0;
    if (pw.length >= 8)             s++;
    if (/[A-Z]/.test(pw))          s++;
    if (/[0-9]/.test(pw))          s++;
    if (/[^A-Za-z0-9]/.test(pw))   s++;
    return Math.max(s, 1);
  }

  /* ──────────────────────────────────────────────────────────
     6. Password show/hide toggle
  ────────────────────────────────────────────────────────── */
  function initPasswordToggle() {
    document.querySelectorAll('[data-toggle-pw]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var input = document.getElementById(btn.getAttribute('data-toggle-pw'));
        if (!input) return;
        var icon = btn.querySelector('i');
        if (input.type === 'password') {
          input.type = 'text';
          if (icon) { icon.classList.remove('bi-eye'); icon.classList.add('bi-eye-slash'); }
        } else {
          input.type = 'password';
          if (icon) { icon.classList.remove('bi-eye-slash'); icon.classList.add('bi-eye'); }
        }
      });
    });
  }

})();

(function () {
  'use strict';

  /* ── Page load ────────────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', function () {
    document.body.classList.add('loaded');
    initNavbarScroll();
    initHeroSlider();
    initCountUp();
    initFlashDismiss();
    initPasswordStrength();
    initPasswordToggle();
  });

  /* ── Navbar: add shadow/background on scroll ─────────────── */
  function initNavbarScroll() {
    var navbar = document.querySelector('.navbar');
    if (!navbar) return;
    function onScroll() {
      if (window.scrollY > 20) {
        navbar.classList.add('scrolled');
      } else {
        navbar.classList.remove('scrolled');
      }
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  /* ── Hero Slider ─────────────────────────────────────────── */
  function initHeroSlider() {
    var slides = document.querySelectorAll('.hero-slide');
    var dots   = document.querySelectorAll('.hero-dot');
    if (!slides.length) return;

    var current  = 0;
    var total    = slides.length;
    var timer    = null;
    var paused   = false;
    var hero     = document.querySelector('.hero-section');

    function goTo(n) {
      slides[current].classList.remove('active');
      if (dots[current]) dots[current].classList.remove('active');
      current = (n + total) % total;
      slides[current].classList.add('active');
      if (dots[current]) dots[current].classList.add('active');
    }

    function startAuto() {
      clearInterval(timer);
      timer = setInterval(function () {
        if (!paused) goTo(current + 1);
      }, 5000);
    }

    dots.forEach(function (dot, i) {
      dot.addEventListener('click', function () {
        goTo(i);
        startAuto();
      });
    });

    var prevBtn = document.querySelector('.hero-prev');
    var nextBtn = document.querySelector('.hero-next');
    if (prevBtn) prevBtn.addEventListener('click', function () { goTo(current - 1); startAuto(); });
    if (nextBtn) nextBtn.addEventListener('click', function () { goTo(current + 1); startAuto(); });

    if (hero) {
      hero.addEventListener('mouseenter', function () { paused = true; });
      hero.addEventListener('mouseleave', function () { paused = false; });
    }

    // Ensure first slide is active
    slides[0].classList.add('active');
    if (dots[0]) dots[0].classList.add('active');
    startAuto();
  }

  /* ── Count-up on scroll into view ───────────────────────── */
  function initCountUp() {
    var counters = document.querySelectorAll('.count-num');
    if (!counters.length) return;

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var el     = entry.target;
        var target = parseInt(el.getAttribute('data-target') || el.textContent, 10);
        if (isNaN(target)) return;
        observer.unobserve(el);
        animateCount(el, 0, target, 1200);
      });
    }, { threshold: 0.3 });

    counters.forEach(function (el) { observer.observe(el); });

    function animateCount(el, start, end, duration) {
      var startTime = null;
      function step(ts) {
        if (!startTime) startTime = ts;
        var progress = Math.min((ts - startTime) / duration, 1);
        var eased    = 1 - Math.pow(1 - progress, 3); // ease-out cubic
        el.textContent = Math.floor(eased * (end - start) + start).toLocaleString();
        if (progress < 1) requestAnimationFrame(step);
        else el.textContent = end.toLocaleString();
      }
      requestAnimationFrame(step);
    }
  }

  /* ── Flash Auto-dismiss ──────────────────────────────────── */
  function initFlashDismiss() {
    var alerts = document.querySelectorAll('.flash-message, .alert');
    alerts.forEach(function (el) {
      // Auto-dismiss after 5s
      setTimeout(function () { dismiss(el); }, 5000);
      // Close button
      var closeBtn = el.querySelector('[data-bs-dismiss="alert"], .flash-close, .btn-close');
      if (closeBtn) {
        closeBtn.addEventListener('click', function () { dismiss(el); });
      }
    });

    function dismiss(el) {
      el.style.transition = 'opacity 0.4s ease, margin-top 0.4s ease';
      el.style.opacity    = '0';
      el.style.marginTop  = '-' + el.offsetHeight + 'px';
      setTimeout(function () { el.remove(); }, 450);
    }
  }

  /* ── Password Strength Meter ─────────────────────────────── */
  function initPasswordStrength() {
    var input    = document.getElementById('password');
    var segments = document.querySelectorAll('.strength-seg');
    var label    = document.getElementById('strength-label');
    if (!input || !segments.length) return;

    input.addEventListener('input', function () {
      var score  = calcStrength(input.value);
      var colors = ['#e74c3c', '#e67e22', '#f1c40f', '#27ae60'];
      var labels = ['Weak', 'Fair', 'Good', 'Strong'];

      segments.forEach(function (seg, i) {
        seg.style.background = i < score ? colors[score - 1] : '#ddd';
      });
      if (label) {
        label.textContent = input.value.length ? labels[score - 1] : '';
        label.style.color = input.value.length ? colors[score - 1] : 'transparent';
      }
    });

    function calcStrength(pw) {
      var score = 0;
      if (pw.length >= 8)              score++;
      if (/[A-Z]/.test(pw))           score++;
      if (/[0-9]/.test(pw))           score++;
      if (/[^A-Za-z0-9]/.test(pw))    score++;
      return Math.max(score, pw.length ? 1 : 0);
    }
  }

  /* ── Password Show/Hide Toggle ───────────────────────────── */
  function initPasswordToggle() {
    document.querySelectorAll('[data-toggle-pw]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var targetId = btn.getAttribute('data-toggle-pw');
        var input    = document.getElementById(targetId);
        if (!input) return;
        var icon = btn.querySelector('i');
        if (input.type === 'password') {
          input.type = 'text';
          if (icon) { icon.classList.remove('bi-eye'); icon.classList.add('bi-eye-slash'); }
        } else {
          input.type = 'password';
          if (icon) { icon.classList.remove('bi-eye-slash'); icon.classList.add('bi-eye'); }
        }
      });
    });
  }

})();
