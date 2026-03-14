/* IssuePilot – frontend logic
   Calls the existing API endpoints: POST /sync, POST /triage, GET /list
   No external dependencies – vanilla JS only.
*/

// ── Tab switching ────────────────────────────────────────
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => {
      t.classList.remove('active');
      t.setAttribute('aria-selected', 'false');
    });
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));

    tab.classList.add('active');
    tab.setAttribute('aria-selected', 'true');
    document.getElementById(`panel-${tab.dataset.tab}`).classList.add('active');
  });
});

// ── Helpers ──────────────────────────────────────────────
function showResult(el, html) {
  el.innerHTML = html;
  el.classList.remove('hidden');
}

function loadingHTML(msg) {
  return `<p><span class="spinner"></span>${escHtml(msg)}</p>`;
}

function escHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function classificationBadge(cls) {
  const labels = { bug: '🐛 Bug', feature: '✨ Feature', docs: '📄 Docs' };
  return `<span class="badge badge-${escHtml(cls)}">${labels[cls] || escHtml(cls)}</span>`;
}

const priorityLabels = { 5: 'Critical', 4: 'High', 3: 'Medium', 2: 'Low', 1: 'Trivial' };
const priorityDots   = { 5: '●●●●●', 4: '●●●●○', 3: '●●●○○', 2: '●●○○○', 1: '●○○○○' };

function priorityBadge(p) {
  return `<span class="priority priority-${p}" title="Priority ${p}">${priorityDots[p] || p} ${priorityLabels[p] || p}</span>`;
}

function fmtDate(str) {
  if (!str) return '—';
  try {
    return new Date(str).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
  } catch (_) {
    return escHtml(str);
  }
}

function issueCard(issue) {
  const titleHtml = issue.url
    ? `<a href="${escHtml(issue.url)}" target="_blank" rel="noopener noreferrer">${escHtml(issue.title)}</a>`
    : escHtml(issue.title);

  return `
    <div class="issue-card">
      <span class="issue-num">#${issue.number}</span>
      <div class="issue-content">
        <div class="issue-title">${titleHtml}</div>
        <div class="issue-meta">
          ${classificationBadge(issue.classification)}
          ${priorityBadge(issue.priority)}
          <span class="issue-date">Triaged ${fmtDate(issue.triaged_at)}</span>
        </div>
      </div>
    </div>`;
}

// ── Sync Form ────────────────────────────────────────────
document.getElementById('form-sync').addEventListener('submit', async e => {
  e.preventDefault();

  const owner   = document.getElementById('sync-owner').value.trim();
  const repo    = document.getElementById('sync-repo').value.trim();
  const state   = document.getElementById('sync-state').value;
  const resultEl = document.getElementById('sync-result');
  const btn      = e.target.querySelector('button[type="submit"]');

  if (!owner || !repo) {
    showResult(resultEl, '<div class="alert alert-error">⚠️ Owner and Repository are required.</div>');
    return;
  }

  btn.disabled = true;
  showResult(resultEl, loadingHTML('Fetching and triaging issues…'));

  try {
    const url = `/sync?owner=${encodeURIComponent(owner)}&repo=${encodeURIComponent(repo)}&state=${encodeURIComponent(state)}`;
    const res  = await fetch(url, { method: 'POST' });
    const data = await res.json();

    if (!res.ok) {
      showResult(resultEl, `<div class="alert alert-error">⚠️ ${escHtml(data.detail || 'An error occurred.')}</div>`);
      return;
    }

    const previewHTML = (data.new_issues && data.new_issues.length > 0)
      ? `<div class="issues-header" style="margin-top:20px">
           <h3>Preview (first ${data.new_issues.length})</h3>
         </div>
         ${data.new_issues.map(issueCard).join('')}`
      : '';

    showResult(resultEl, `
      <div class="sync-summary">
        <div class="stat-row">
          <div class="stat">
            <div class="num">${data.triaged_count}</div>
            <div class="lbl">New Triaged</div>
          </div>
          <div class="stat">
            <div class="num">${data.total_issues}</div>
            <div class="lbl">Total Stored</div>
          </div>
        </div>
        <div class="alert alert-success">✅ ${escHtml(data.message)}</div>
      </div>
      ${previewHTML}
    `);
  } catch (err) {
    showResult(resultEl, `<div class="alert alert-error">⚠️ Network error: ${escHtml(err.message)}</div>`);
  } finally {
    btn.disabled = false;
  }
});

// ── Triage Form ───────────────────────────────────────────
document.getElementById('form-triage').addEventListener('submit', async e => {
  e.preventDefault();

  const number    = document.getElementById('triage-number').value;
  const title     = document.getElementById('triage-title').value.trim();
  const body      = document.getElementById('triage-body').value.trim();
  const createdAt = document.getElementById('triage-created').value;
  const resultEl  = document.getElementById('triage-result');
  const btn       = e.target.querySelector('button[type="submit"]');

  if (!number || !title) {
    showResult(resultEl, '<div class="alert alert-error">⚠️ Issue Number and Title are required.</div>');
    return;
  }

  const params = new URLSearchParams({ number, title });
  if (body)      params.set('body', body);
  if (createdAt) params.set('created_at', new Date(createdAt).toISOString());

  btn.disabled = true;
  showResult(resultEl, loadingHTML('Classifying issue…'));

  try {
    const res  = await fetch(`/triage?${params}`, { method: 'POST' });
    const data = await res.json();

    if (!res.ok) {
      showResult(resultEl, `<div class="alert alert-error">⚠️ ${escHtml(data.detail || 'An error occurred.')}</div>`);
      return;
    }

    const issue = data.issue;
    const bodyRow = issue.body
      ? `<div class="row">
           <span class="label">Body</span>
           <span class="value" style="white-space:pre-wrap;max-height:120px;overflow:auto">${escHtml(issue.body)}</span>
         </div>`
      : '';

    showResult(resultEl, `
      <div class="alert alert-success" style="margin-bottom:16px">✅ Issue #${issue.number} triaged and saved.</div>
      <div class="triage-card">
        <div class="row"><span class="label">Title</span><span class="value">${escHtml(issue.title)}</span></div>
        <div class="row"><span class="label">Classification</span>${classificationBadge(issue.classification)}</div>
        <div class="row"><span class="label">Priority</span>${priorityBadge(issue.priority)}</div>
        <div class="row"><span class="label">Created At</span><span class="value issue-date">${fmtDate(issue.created_at)}</span></div>
        <div class="row"><span class="label">Triaged At</span><span class="value issue-date">${fmtDate(issue.triaged_at)}</span></div>
        ${bodyRow}
      </div>
    `);
  } catch (err) {
    showResult(resultEl, `<div class="alert alert-error">⚠️ Network error: ${escHtml(err.message)}</div>`);
  } finally {
    btn.disabled = false;
  }
});

// ── Browse ────────────────────────────────────────────────
document.getElementById('btn-browse').addEventListener('click', loadIssues);

async function loadIssues() {
  const cls      = document.getElementById('browse-classification').value;
  const pri      = document.getElementById('browse-priority').value;
  const resultEl = document.getElementById('browse-result');
  const btn      = document.getElementById('btn-browse');

  const params = new URLSearchParams({ limit: '100' });
  if (cls) params.set('classification', cls);
  if (pri) params.set('priority', pri);

  btn.disabled = true;
  showResult(resultEl, loadingHTML('Loading issues…'));

  try {
    const res  = await fetch(`/list?${params}`);
    const data = await res.json();

    if (!res.ok) {
      showResult(resultEl, `<div class="alert alert-error">⚠️ ${escHtml(data.detail || 'An error occurred.')}</div>`);
      return;
    }

    if (data.count === 0) {
      showResult(resultEl, `
        <div class="empty">
          <div class="empty-icon">📭</div>
          <p>No triaged issues found. Try syncing or triaging some first.</p>
        </div>`);
      return;
    }

    showResult(resultEl, `
      <div class="issues-header">
        <h3>Triaged Issues</h3>
        <span class="issues-count">${data.count} result${data.count !== 1 ? 's' : ''}</span>
      </div>
      ${data.issues.map(issueCard).join('')}
    `);
  } catch (err) {
    showResult(resultEl, `<div class="alert alert-error">⚠️ Network error: ${escHtml(err.message)}</div>`);
  } finally {
    btn.disabled = false;
  }
}
