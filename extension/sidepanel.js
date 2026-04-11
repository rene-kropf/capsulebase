// ============================================================
// Capsule Save — Side Panel Script v1.1.0
// ============================================================

let currentResults = [];
let currentTabId = null;

function formatDate(dateStr) {
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  } catch {
    return '';
  }
}

function formatScore(score) {
  return Math.round(score * 100) + '% match';
}

function renderResults(results, currentTitle) {
  currentResults = results;

  const content = document.getElementById('content');
  const footer = document.getElementById('footer');
  const badge = document.getElementById('badge');

  badge.textContent = results.length;
  badge.style.display = 'block';

  let html = '';

  if (currentTitle) {
    html += `
      <div class="context-label">Current Conversation</div>
      <div class="current-title">${currentTitle}</div>
    `;
  }

  html += `<div class="section-label">Related Memory (${results.length})</div>`;

  results.forEach((r, i) => {
    const tags = Array.isArray(r.tags) ? r.tags.slice(0, 3) : [];
    const tagHtml = tags.map(t => `<span class="result-tag">${t}</span>`).join('');
    const summary = r.summary ? r.summary.slice(0, 160) + (r.summary.length > 160 ? '…' : '') : '';

    html += `
      <div class="result-card" id="card-${i}">
        <div class="result-title">${r.title}</div>
        ${summary ? `<div class="result-summary">${summary}</div>` : ''}
        <div class="result-meta">
          <span class="result-score">${formatScore(r.similarity || r.score || 0)}</span>
          <span class="result-date">${formatDate(r.created_at)}</span>
          ${tagHtml}
        </div>
        <div class="result-check">
          <input type="checkbox" id="check-${i}" data-index="${i}">
          <label for="check-${i}">Include in conversation</label>
        </div>
      </div>
    `;
  });

  content.innerHTML = html;
  footer.style.display = 'block';

  // Wire up checkboxes
  document.querySelectorAll('input[type="checkbox"]').forEach(cb => {
    cb.addEventListener('change', updateInjectButton);
  });
}

function updateInjectButton() {
  const checked = document.querySelectorAll('input[type="checkbox"]:checked');
  const btn = document.getElementById('injectBtn');
  btn.disabled = checked.length === 0;
  btn.textContent = checked.length > 0
    ? `Add ${checked.length} to Conversation`
    : 'Add Selected to Conversation';
}

function buildInjectionText(selectedResults) {
  const lines = ['[Capsule Memory — Related Conversations]\n'];
  selectedResults.forEach((r, i) => {
    lines.push(`${i + 1}. ${r.title}`);
    if (r.summary) lines.push(`   ${r.summary}`);
    if (Array.isArray(r.tags) && r.tags.length) {
      lines.push(`   Tags: ${r.tags.join(', ')}`);
    }
    lines.push('');
  });
  lines.push('[End of Capsule Memory]');
  return lines.join('\n');
}

async function injectSelected() {
  const checked = [...document.querySelectorAll('input[type="checkbox"]:checked')];
  if (!checked.length) return;

  const selected = checked.map(cb => currentResults[parseInt(cb.dataset.index)]);
  const text = buildInjectionText(selected);

  const status = document.getElementById('injectStatus');
  const btn = document.getElementById('injectBtn');
  btn.disabled = true;
  btn.textContent = 'Adding...';

  try {
    // Get active tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const tabId = currentTabId || tab?.id;

    if (!tabId) throw new Error('No active tab');

    const response = await chrome.tabs.sendMessage(tabId, {
      action: 'inject',
      text
    });

    if (response?.ok) {
      status.textContent = `✓ ${selected.length} memory block${selected.length > 1 ? 's' : ''} added`;
      btn.textContent = '✓ Done';
      // Uncheck all
      document.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
    } else {
      throw new Error(response?.error || 'Injection failed');
    }
  } catch (e) {
    status.textContent = '✗ Could not inject — try refreshing Claude';
    btn.disabled = false;
    btn.textContent = 'Add Selected to Conversation';
    console.error('Capsule inject error:', e);
  }
}

function dismiss() {
  const content = document.getElementById('content');
  const footer = document.getElementById('footer');
  const badge = document.getElementById('badge');

  content.innerHTML = `
    <div class="waiting">
      <div class="icon">✓</div>
      Dismissed. Capsule will surface<br>new related memory if the<br>conversation shifts topic.
    </div>
  `;
  footer.style.display = 'none';
  badge.style.display = 'none';
}

// ============================================================
// LISTEN FOR MESSAGES FROM BACKGROUND
// ============================================================
chrome.runtime.onMessage.addListener((message) => {
  if (message.action === 'show_related') {
    currentTabId = message.tabId;
    renderResults(message.results, message.currentTitle);
  }
});

// ============================================================
// CHECK FOR PENDING RESULTS (side panel opened after message sent)
// ============================================================
async function checkPending() {
  try {
    const data = await chrome.storage.session.get(['pendingResults', 'pendingTitle', 'pendingTabId']);
    if (data.pendingResults?.length) {
      currentTabId = data.pendingTabId;
      renderResults(data.pendingResults, data.pendingTitle);
      // Clear so it doesn't re-render on next open
      await chrome.storage.session.remove(['pendingResults', 'pendingTitle', 'pendingTabId']);
    }
  } catch {
    // session storage may not be available
  }
}

// Wire buttons
document.getElementById('injectBtn').addEventListener('click', injectSelected);
document.getElementById('dismissBtn').addEventListener('click', dismiss);

// Check for pending results on load
checkPending();
