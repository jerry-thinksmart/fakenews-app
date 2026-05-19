/* ================================================================
   dashboard.js — FakeNews Detector dashboard
   NOTE: detect, records, analytics, and index charts all have
   inline <script> in their templates. This file handles:
     - Page load fade-in
     - Sidebar toggle (mobile hamburger)
     - Flash message dismiss
     - Reports page: type toggle + date range sync
================================================================ */
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    document.body.classList.add('loaded');
    initSidebar();
    initFlashDismiss();
    initReportsPage();
  });

  /* ──────────────────────────────────────────────────────────
     Sidebar toggle for mobile
     Template IDs: sidebarToggle, dashSidebar, sidebarOverlay
  ────────────────────────────────────────────────────────── */
  function initSidebar() {
    var toggleBtn = document.getElementById('sidebarToggle');
    var sidebar   = document.getElementById('dashSidebar');     // ← correct ID
    var overlay   = document.getElementById('sidebarOverlay');
    if (!sidebar) return;

    function openSidebar() {
      sidebar.classList.add('open');
      if (overlay) overlay.classList.add('show');
    }
    function closeSidebar() {
      sidebar.classList.remove('open');
      if (overlay) overlay.classList.remove('show');
    }

    if (toggleBtn) {
      toggleBtn.addEventListener('click', function () {
        sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
      });
    }
    if (overlay) {
      overlay.addEventListener('click', closeSidebar);
    }
  }

  /* ──────────────────────────────────────────────────────────
     Flash message auto-dismiss (5s) + X button
  ────────────────────────────────────────────────────────── */
  function initFlashDismiss() {
    document.querySelectorAll('.flash-message, .alert').forEach(function (el) {
      setTimeout(function () { fadeOut(el); }, 5000);
      var btn = el.querySelector('.flash-close, .btn-close, [data-bs-dismiss="alert"]');
      if (btn) btn.addEventListener('click', function () { fadeOut(el); });
    });
  }

  function fadeOut(el) {
    el.style.transition = 'opacity 0.4s ease';
    el.style.opacity    = '0';
    setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 420);
  }

  /* ──────────────────────────────────────────────────────────
     Reports page:
       - .report-type-btn  active toggle
       - #dateFrom / #dateTo  sync into hidden #csvRange / #pdfRange
       - #csvType reflects active type
  ────────────────────────────────────────────────────────── */
  function initReportsPage() {
    var typeBtns  = document.querySelectorAll('.report-type-btn');
    var csvType   = document.getElementById('csvType');
    var csvRange  = document.getElementById('csvRange');
    var pdfRange  = document.getElementById('pdfRange');
    var dateFrom  = document.getElementById('dateFrom');
    var dateTo    = document.getElementById('dateTo');

    // Type toggle
    typeBtns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        typeBtns.forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        if (csvType) csvType.value = btn.getAttribute('data-type') || 'detection';
      });
    });

    // Date range: sync to hidden form fields on any change
    function syncRange() {
      var from = dateFrom ? dateFrom.value : '';
      var to   = dateTo   ? dateTo.value   : '';
      var range = (from && to) ? (from + ' to ' + to) : '';
      if (csvRange) csvRange.value = range;
      if (pdfRange) pdfRange.value = range;
    }
    if (dateFrom) dateFrom.addEventListener('change', syncRange);
    if (dateTo)   dateTo.addEventListener('change',   syncRange);

    // Preview button
    var previewBtn     = document.getElementById('previewBtn');
    var previewSection = document.getElementById('previewSection');
    if (previewBtn && previewSection) {
      previewBtn.addEventListener('click', function () {
        syncRange();
        var from = dateFrom ? dateFrom.value : '';
        var to   = dateTo   ? dateTo.value   : '';
        var url  = '/dashboard/history?';
        if (from) url += 'start=' + encodeURIComponent(from) + '&';
        if (to)   url += 'end='   + encodeURIComponent(to);
        // Show section with a note (full preview would require a dedicated API endpoint)
        previewSection.style.display = 'block';
        var body = previewSection.querySelector('.dash-card-body');
        if (body) {
          body.innerHTML =
            '<p class="text-muted p-3" style="font-size:1.3rem">' +
            'Date range set: <strong>' + (from || 'all') + ' to ' + (to || 'today') + '</strong>. ' +
            'Use <em>Export CSV</em> or <em>Export PDF</em> below to download your report.' +
            '</p>';
        }
      });
    }
  }

})();

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    document.body.classList.add('loaded');
    initSidebar();
    initFlashDismiss();
    initDetectPage();
    initAnalyticsPage();
    initRecordsPage();
    initReportsPage();
    initIndexCharts();
  });

  /* ── Sidebar toggle (mobile) ─────────────────────────────── */
  function initSidebar() {
    var toggleBtn = document.getElementById('sidebarToggle');
    var sidebar   = document.getElementById('dashboardSidebar');
    var overlay   = document.getElementById('sidebarOverlay');
    if (!sidebar) return;

    function open()  { sidebar.classList.add('open');  if (overlay) overlay.classList.add('show'); }
    function close() { sidebar.classList.remove('open'); if (overlay) overlay.classList.remove('show'); }

    if (toggleBtn) toggleBtn.addEventListener('click', function () {
      sidebar.classList.contains('open') ? close() : open();
    });
    if (overlay) overlay.addEventListener('click', close);

    // Mark active sidebar item
    var path = window.location.pathname;
    document.querySelectorAll('.sidebar-item[href]').forEach(function (a) {
      if (a.getAttribute('href') === path || path.startsWith(a.getAttribute('href') + '/')) {
        a.classList.add('active');
      }
    });
  }

  /* ── Flash Dismiss ───────────────────────────────────────── */
  function initFlashDismiss() {
    document.querySelectorAll('.flash-message, .alert').forEach(function (el) {
      setTimeout(function () { fadeOut(el); }, 5000);
      var btn = el.querySelector('.flash-close, .btn-close, [data-bs-dismiss="alert"]');
      if (btn) btn.addEventListener('click', function () { fadeOut(el); });
    });
    function fadeOut(el) {
      el.style.transition = 'opacity 0.4s ease';
      el.style.opacity    = '0';
      setTimeout(function () { el.remove(); }, 420);
    }
  }

  /* ── Detect Page ─────────────────────────────────────────── */
  function initDetectPage() {
    var form        = document.getElementById('detectForm');
    if (!form) return;

    var textarea    = document.getElementById('articleText');
    var wordCount   = document.getElementById('wordCount');
    var charCount   = document.getElementById('charCount');
    var submitBtn   = document.getElementById('detectBtn');
    var resultArea  = document.getElementById('resultArea');
    var spinner     = document.getElementById('detectSpinner');

    // Word / char counter
    if (textarea) {
      textarea.addEventListener('input', function () {
        var text  = textarea.value.trim();
        var words = text ? text.split(/\s+/).filter(Boolean).length : 0;
        if (wordCount) wordCount.textContent = words;
        if (charCount) charCount.textContent = textarea.value.length;
      });
    }

    // Form submit via fetch
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (submitBtn)   submitBtn.disabled = true;
      if (spinner)     spinner.style.display = 'inline-block';
      if (resultArea)  resultArea.style.display = 'none';

      var csrfToken = document.querySelector('meta[name="csrf-token"]');
      var formData  = new FormData(form);

      fetch(form.getAttribute('action') || window.location.href, {
        method:  'POST',
        headers: {
          'X-CSRFToken':  csrfToken ? csrfToken.content : '',
          'X-Requested-With': 'XMLHttpRequest',
          'Accept': 'application/json'
        },
        body: formData
      })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        showResult(data);
      })
      .catch(function (err) {
        showResult({ error: true, message: 'Network error. Please try again.', prediction: 'Error' });
        console.error(err);
      })
      .finally(function () {
        if (submitBtn)  submitBtn.disabled = false;
        if (spinner)    spinner.style.display = 'none';
      });
    });

    // "Analyze Another" button
    var analyzeAnotherBtn = document.getElementById('analyzeAnotherBtn');
    if (analyzeAnotherBtn) {
      analyzeAnotherBtn.addEventListener('click', function () {
        if (textarea) textarea.value = '';
        if (wordCount) wordCount.textContent = '0';
        if (charCount) charCount.textContent = '0';
        if (resultArea) resultArea.style.display = 'none';
      });
    }

    function showResult(data) {
      if (!resultArea) return;
      resultArea.style.display = 'block';

      var badgeEl    = resultArea.querySelector('#resultBadge');
      var msgEl      = resultArea.querySelector('#resultMessage');
      var confEl     = resultArea.querySelector('#resultConfidence');
      var confBarEl  = resultArea.querySelector('#resultConfBar');

      var pred = (data.prediction || 'Error').toLowerCase();
      var badgeClass = 'result-' + pred.replace(/\s+/g, '-');

      if (badgeEl) {
        badgeEl.className = 'result-badge ' + badgeClass;
        badgeEl.textContent = data.prediction || 'Error';
      }
      if (msgEl) msgEl.textContent = data.message || '';
      if (confEl && data.confidence != null) {
        var pct = Math.round(data.confidence * 100);
        confEl.textContent = pct + '%';
      }
      if (confBarEl && data.confidence != null) {
        confBarEl.style.width = Math.round(data.confidence * 100) + '%';
      }

      // Animate in
      resultArea.style.animation = 'none';
      resultArea.offsetHeight;   // reflow
      resultArea.style.animation = '';
    }
  }

  /* ── Analytics Page ──────────────────────────────────────── */
  function initAnalyticsPage() {
    var page = document.getElementById('analyticsPage');
    if (!page) return;

    fetch('/dashboard/api/analytics')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        buildDoughnut(data);
        buildWeeklyBar(data);
        buildDailyLine(data);
        buildConfBar(data);
      })
      .catch(function (e) { console.error('Analytics fetch error', e); });
  }

  function buildDoughnut(data) {
    var el = document.getElementById('chartDoughnut');
    if (!el || typeof Chart === 'undefined') return;
    new Chart(el, {
      type: 'doughnut',
      data: {
        labels: ['Fake', 'Real', 'Uncertain', 'Invalid'],
        datasets: [{ data: [data.fake || 0, data.real || 0, data.uncertain || 0, data.invalid || 0],
          backgroundColor: ['#e74c3c','#27ae60','#f1c40f','#95a5a6'],
          borderWidth: 2, borderColor: '#fff' }]
      },
      options: { cutout: '65%', plugins: { legend: { position: 'bottom', labels: { font: { size:11 } } } } }
    });
  }

  function buildWeeklyBar(data) {
    var el = document.getElementById('chartWeeklyBar');
    if (!el || typeof Chart === 'undefined' || !data.weekly) return;
    var labels = data.weekly.map(function (d) { return d.label; });
    var vals   = data.weekly.map(function (d) { return d.count; });
    new Chart(el, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{ label: 'Detections', data: vals,
          backgroundColor: 'rgba(255,102,0,0.75)',
          borderColor: '#Ff6600',
          borderWidth: 2, borderRadius: 6 }]
      },
      options: { plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } }
    });
  }

  function buildDailyLine(data) {
    var el = document.getElementById('chartDailyLine');
    if (!el || typeof Chart === 'undefined' || !data.daily) return;
    var labels = data.daily.map(function (d) { return d.date; });
    var vals   = data.daily.map(function (d) { return d.count; });
    new Chart(el, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{ label: 'Daily Detections', data: vals,
          borderColor: '#274665',
          backgroundColor: 'rgba(39,70,101,0.1)',
          fill: true, tension: 0.4, pointRadius: 3 }]
      },
      options: { plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true } } }
    });
  }

  function buildConfBar(data) {
    var el = document.getElementById('chartConfBar');
    if (!el || typeof Chart === 'undefined' || !data.confidence_buckets) return;
    var labels = Object.keys(data.confidence_buckets);
    var vals   = Object.values(data.confidence_buckets);
    new Chart(el, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{ label: 'Count', data: vals,
          backgroundColor: 'rgba(39,70,101,0.75)',
          borderColor: '#274665',
          borderWidth: 2, borderRadius: 6 }]
      },
      options: {
        indexAxis: 'y',
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true, ticks: { stepSize: 1 } } }
      }
    });
  }

  /* ── Dashboard Index: mini charts ────────────────────────── */
  function initIndexCharts() {
    var doughnutEl = document.getElementById('indexDoughnut');
    var barEl      = document.getElementById('indexBar');
    if (!doughnutEl && !barEl) return;
    if (typeof Chart === 'undefined') return;

    fetch('/dashboard/api/analytics')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (doughnutEl) buildDoughnut(data);
        if (barEl && data.weekly)     buildWeeklyBar(data);
      })
      .catch(function (e) { console.warn('Index chart fetch', e); });
  }

  /* ── Records Page: DELETE ────────────────────────────────── */
  function initRecordsPage() {
    document.querySelectorAll('.delete-record-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = btn.getAttribute('data-id');
        if (!id) return;
        if (!confirm('Delete this record? This action cannot be undone.')) return;

        var csrfToken = document.querySelector('meta[name="csrf-token"]');
        fetch('/dashboard/records/delete/' + id, {
          method:  'DELETE',
          headers: {
            'X-CSRFToken': csrfToken ? csrfToken.content : '',
            'X-Requested-With': 'XMLHttpRequest'
          }
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.success) {
            var card = btn.closest('[data-record-id="' + id + '"]');
            if (card) { card.style.opacity = '0'; setTimeout(function () { card.remove(); }, 300); }
          } else {
            alert(data.message || 'Could not delete record.');
          }
        })
        .catch(function () { alert('Network error. Please try again.'); });
      });
    });
  }

  /* ── Reports Page ────────────────────────────────────────── */
  function initReportsPage() {
    var page = document.getElementById('reportsPage');
    if (!page) return;

    // Type toggle buttons
    var typeBtns    = document.querySelectorAll('.report-type-btn');
    var typeHidden  = document.getElementById('reportTypeInput');
    typeBtns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        typeBtns.forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        if (typeHidden) typeHidden.value = btn.getAttribute('data-type');
      });
    });

    // Sync date range fields between preview and export forms
    var startA = document.getElementById('startDate');
    var endA   = document.getElementById('endDate');
    var startB = document.getElementById('exportStartDate');
    var endB   = document.getElementById('exportEndDate');

    function syncDates() {
      if (startB && startA) startB.value = startA.value;
      if (endB   && endA)   endB.value   = endA.value;
    }
    if (startA) startA.addEventListener('change', syncDates);
    if (endA)   endA.addEventListener('change',   syncDates);
  }

})();
