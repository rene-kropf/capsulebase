// ============================================================
// Capsule Save — Content Script v1.2.1
// Monitors conversation, injects drawer UI for related memory
// ============================================================

const TRIGGER_EXCHANGES = 3;
const CHECK_INTERVAL_MS = 8000;

let lastCheckedExchangeCount = 0;
let suggestionFired = false;
let monitorPaused = false;
let drawerInjected = false;

// ============================================================
// EXTRACT CONVERSATION
// ============================================================
function extractConversation() {
  try {
    const titleEl = document.querySelector('[data-testid="chat-title-button"]');
    const title = titleEl?.innerText?.trim() || 'Untitled Conversation';

    const scrollEl = document.querySelector('.overflow-y-auto');
    if (!scrollEl) return { error: 'Could not find conversation container' };

    const turnsContainer = scrollEl
      ?.children[2]?.children[0]?.children[0]
      ?.children[1]?.children[0]?.children[0]?.children[0];

    if (!turnsContainer) return { error: 'Could not find turns container' };

    const turns = [...turnsContainer.children];
    if (!turns.length) return { error: 'No conversation turns found' };

    const lines = [];
    turns.forEach(turn => {
      const isUser = !!turn.querySelector('[data-testid="user-message"]');
      let text = '';
      if (isUser) {
        const userMsg = turn.querySelector('[data-testid="user-message"]');
        text = userMsg?.innerText?.trim() || '';
      } else {
        const responseEl = turn.querySelector('[class*="font-claude-response"]');
        if (responseEl) {
          const actualResponse = responseEl.querySelector('.row-start-2');
          text = (actualResponse || responseEl).innerText?.trim() || '';
        }
      }
      if (!text) return;
      lines.push(`${isUser ? 'HUMAN' : 'ASSISTANT'}: ${text}`);
    });

    if (!lines.length) return { error: 'No content extracted' };
    return { title, content: lines.join('\n\n'), turnCount: turns.length, url: window.location.href };
  } catch (e) {
    return { error: e.message };
  }
}

// ============================================================
// COUNT EXCHANGES
// ============================================================
function countExchanges() {
  try {
    const scrollEl = document.querySelector('.overflow-y-auto');
    if (!scrollEl) return 0;
    const turnsContainer = scrollEl
      ?.children[2]?.children[0]?.children[0]
      ?.children[1]?.children[0]?.children[0]?.children[0];
    if (!turnsContainer) return 0;
    return [...turnsContainer.children]
      .filter(t => t.querySelector('[data-testid="user-message"]')).length;
  } catch { return 0; }
}

// ============================================================
// INJECT DRAWER STYLES
// ============================================================
function injectStyles() {
  if (document.getElementById('capsule-styles')) return;
  const style = document.createElement('style');
  style.id = 'capsule-styles';
  style.textContent = `
    #capsule-drawer {
      position: fixed;
      top: 0;
      right: -420px;
      width: 380px;
      height: 100vh;
      background: #0f1219;
      border-left: 1px solid #2d3548;
      z-index: 999999;
      display: flex;
      flex-direction: column;
      transition: right 0.3s ease;
      font-family: 'DM Sans', -apple-system, sans-serif;
      box-shadow: -4px 0 24px rgba(0,0,0,0.4);
    }
    #capsule-drawer.open { right: 0; }

    #capsule-overlay {
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.3);
      z-index: 999998;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.3s ease;
    }
    #capsule-overlay.open { opacity: 1; pointer-events: all; }

    .cap-header {
      background: #1a1f2e;
      border-bottom: 1px solid #2d3548;
      padding: 14px 16px;
      display: flex;
      align-items: center;
      gap: 10px;
      flex-shrink: 0;
    }
    .cap-logo {
      width: 28px; height: 28px;
      flex-shrink: 0;
    }
    .cap-logo-text { font-size: 12px; font-weight: 700; color: #10b981; letter-spacing: 1px; }
    .cap-logo-sub { font-size: 9px; color: #4a5168; letter-spacing: 1px; }
    .cap-close {
      margin-left: auto;
      background: none;
      border: none;
      color: #4a5168;
      font-size: 18px;
      cursor: pointer;
      padding: 0 4px;
      line-height: 1;
    }
    .cap-close:hover { color: #e4e7ed; }

    .cap-body {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      color: #e4e7ed;
    }

    .cap-context-label {
      font-size: 10px; font-weight: 700; color: #4a5168;
      text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px;
    }
    .cap-current-title {
      font-size: 11px; color: #8b92a5; font-style: italic;
      margin-bottom: 14px; padding-bottom: 12px;
      border-bottom: 1px solid #2d3548; line-height: 1.4;
    }
    .cap-section-label {
      font-size: 10px; font-weight: 700; color: #4a5168;
      text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px;
    }

    .cap-card {
      background: #1a1f2e;
      border: 1px solid #2d3548;
      border-radius: 10px;
      padding: 12px;
      margin-bottom: 10px;
      transition: border-color 0.15s;
    }
    .cap-card:hover { border-color: #3d4a6e; }
    .cap-card.selected { border-color: #10b981; background: #0d1a12; }

    .cap-card-title {
      font-size: 12px; font-weight: 600; color: #e4e7ed;
      margin-bottom: 4px; line-height: 1.4;
    }
    .cap-card-summary {
      font-size: 11px; color: #8b92a5; line-height: 1.5; margin-bottom: 8px;
    }
    .cap-card-meta { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
    .cap-score { font-size: 10px; color: #10b981; font-weight: 600; }
    .cap-date { font-size: 10px; color: #4a5168; }
    .cap-tag {
      font-size: 9px; background: #2d3548; color: #8b92a5;
      padding: 2px 6px; border-radius: 4px;
    }
    .cap-check-row {
      display: flex; align-items: center; gap: 6px;
      margin-top: 8px; padding-top: 8px; border-top: 1px solid #2d3548;
    }
    .cap-check-row input[type="checkbox"] { accent-color: #10b981; width: 14px; height: 14px; cursor: pointer; }
    .cap-check-row label { font-size: 11px; color: #8b92a5; cursor: pointer; user-select: none; }

    .cap-footer {
      padding: 14px 16px;
      border-top: 1px solid #2d3548;
      background: #0f1219;
      flex-shrink: 0;
    }
    .cap-btn {
      width: 100%;
      background: #10b981;
      color: #0f1219;
      border: none;
      border-radius: 8px;
      padding: 11px;
      font-family: inherit;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      transition: background 0.15s;
      letter-spacing: 0.3px;
    }
    .cap-btn:hover { background: #059669; }
    .cap-btn:disabled { background: #2d3548; color: #4a5168; cursor: not-allowed; }
    .cap-btn-dismiss {
      width: 100%; background: transparent; color: #4a5168; border: none;
      padding: 8px; font-family: inherit; font-size: 11px; cursor: pointer;
      margin-top: 6px; transition: color 0.15s;
    }
    .cap-btn-dismiss:hover { color: #8b92a5; }
    .cap-status { font-size: 11px; text-align: center; margin-top: 8px; min-height: 16px; color: #10b981; }
  `;
  document.head.appendChild(style);
}

// ============================================================
// BUILD DRAWER HTML
// ============================================================
function buildDrawer() {
  if (document.getElementById('capsule-drawer')) return;

  injectStyles();

  const overlay = document.createElement('div');
  overlay.id = 'capsule-overlay';
  overlay.addEventListener('click', closeDrawer);

  const drawer = document.createElement('div');
  drawer.id = 'capsule-drawer';
  drawer.innerHTML = `
    <div class="cap-header">
      <div class="cap-logo"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 60" fill="none" width="28" height="28"><path d="M18 30 C18 22 23 16 30 16 L30 44 C23 44 18 38 18 30Z" fill="#10b981"/><path d="M30 16 C37 16 42 22 42 30 C42 38 37 44 30 44 L30 16Z" fill="none" stroke="#10b981" stroke-width="1.5"/><circle cx="38" cy="22" r="3.5" fill="#4ade80"/></svg></div>
      <div>
        <div class="cap-logo-text">CAPSULE</div>
        <div class="cap-logo-sub">RELATED MEMORY</div>
      </div>
      <button class="cap-close" id="cap-close-btn">✕</button>
    </div>
    <div class="cap-body" id="cap-body"></div>
    <div class="cap-footer" id="cap-footer" style="display:none">
      <button class="cap-btn" id="cap-inject-btn" disabled>Add Selected to Conversation</button>
      <button class="cap-btn-dismiss" id="cap-dismiss-btn">Dismiss</button>
      <div class="cap-status" id="cap-status"></div>
    </div>
  `;

  document.body.appendChild(overlay);
  document.body.appendChild(drawer);

  document.getElementById('cap-close-btn').addEventListener('click', closeDrawer);
  document.getElementById('cap-inject-btn').addEventListener('click', injectSelected);
  document.getElementById('cap-dismiss-btn').addEventListener('click', closeDrawer);

  drawerInjected = true;
}

function openDrawer() {
  buildDrawer();
  setTimeout(() => {
    document.getElementById('capsule-drawer')?.classList.add('open');
    document.getElementById('capsule-overlay')?.classList.add('open');
  }, 50);
}

function closeDrawer() {
  document.getElementById('capsule-drawer')?.classList.remove('open');
  document.getElementById('capsule-overlay')?.classList.remove('open');
}

// ============================================================
// RENDER RESULTS IN DRAWER
// ============================================================
let currentResults = [];

function formatDate(str) {
  try {
    return new Date(str).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  } catch { return ''; }
}

function renderResults(results, currentTitle) {
  currentResults = results;
  buildDrawer();

  const body = document.getElementById('cap-body');
  const footer = document.getElementById('cap-footer');

  let html = '';
  if (currentTitle) {
    html += `<div class="cap-context-label">Current Conversation</div>
             <div class="cap-current-title">${currentTitle}</div>`;
  }
  html += `<div class="cap-section-label">Related Memory (${results.length})</div>`;

  results.forEach((r, i) => {
    const tags = Array.isArray(r.tags) ? r.tags.slice(0, 3) : [];
    const summary = r.summary ? r.summary.slice(0, 140) + (r.summary.length > 140 ? '…' : '') : '';
    const score = r._score ? `${r._score}pts` : '';
    html += `
      <div class="cap-card" id="cap-card-${i}">
        <div class="cap-card-title">${r.title}</div>
        ${summary ? `<div class="cap-card-summary">${summary}</div>` : ''}
        <div class="cap-card-meta">
          ${score ? `<span class="cap-score">${score}</span>` : ''}
          <span class="cap-date">${formatDate(r.created_at)}</span>
          ${tags.map(t => `<span class="cap-tag">${t}</span>`).join('')}
        </div>
        <div class="cap-check-row">
          <input type="checkbox" id="cap-chk-${i}" data-index="${i}">
          <label for="cap-chk-${i}">Include in conversation</label>
        </div>
      </div>`;
  });

  body.innerHTML = html;
  footer.style.display = 'block';

  document.querySelectorAll('.cap-check-row input[type="checkbox"]').forEach(cb => {
    cb.addEventListener('change', updateInjectBtn);
  });
}

function updateInjectBtn() {
  const checked = document.querySelectorAll('.cap-check-row input[type="checkbox"]:checked');
  const btn = document.getElementById('cap-inject-btn');
  if (!btn) return;
  btn.disabled = checked.length === 0;
  btn.textContent = checked.length > 0
    ? `Add ${checked.length} to Conversation`
    : 'Add Selected to Conversation';
}

// ============================================================
// INJECT SELECTED INTO CLAUDE INPUT
// ============================================================
function injectSelected() {
  const checked = [...document.querySelectorAll('.cap-check-row input[type="checkbox"]:checked')];
  if (!checked.length) return;

  const selected = checked.map(cb => currentResults[parseInt(cb.dataset.index)]);

  const lines = ['[Capsule Memory — Related Conversations]\n'];
  selected.forEach((r, i) => {
    lines.push(`${i + 1}. ${r.title}`);
    if (r.summary) lines.push(`   ${r.summary}`);
    if (Array.isArray(r.tags) && r.tags.length) lines.push(`   Tags: ${r.tags.join(', ')}`);
    lines.push('');
  });
  lines.push('[End of Capsule Memory]');
  const text = lines.join('\n');

  const inputEl = document.querySelector('[data-testid="chat-input"]') ||
                  document.querySelector('div[contenteditable="true"]');

  if (inputEl) {
    inputEl.focus();
    const current = inputEl.innerText.trim();
    const separator = current ? '\n\n---\n' : '';
    document.execCommand('insertText', false, separator + text);
    document.getElementById('cap-status').textContent =
      `✓ ${selected.length} memory block${selected.length > 1 ? 's' : ''} added`;
    document.getElementById('cap-inject-btn').textContent = '✓ Done';
    document.getElementById('cap-inject-btn').disabled = true;
    setTimeout(closeDrawer, 1500);
  } else {
    document.getElementById('cap-status').textContent = '✗ Could not find input box';
  }
}

// ============================================================
// SEARCH VIA BACKGROUND
// ============================================================
async function searchCapsule(query) {
  return new Promise(resolve => {
    try {
      chrome.runtime.sendMessage(
        { action: 'capsule_search', query: query.slice(0, 1000) },
        response => {
          if (chrome.runtime.lastError) { resolve([]); return; }
          resolve(response?.results || []);
        }
      );
    } catch { resolve([]); }
  });
}

// ============================================================
// PROACTIVE MONITOR
// ============================================================
async function checkConversation() {
  if (suggestionFired || monitorPaused) return;

  const exchanges = countExchanges();
  if (exchanges < TRIGGER_EXCHANGES) return;
  if (exchanges === lastCheckedExchangeCount) return;

  lastCheckedExchangeCount = exchanges;

  const extracted = extractConversation();
  if (extracted.error || !extracted.content) return;

  const humanLines = extracted.content
    .split('\n\n')
    .filter(l => l.startsWith('HUMAN:'))
    .map(l => l.replace('HUMAN: ', '').trim());

  const titleQuery = extracted.title !== 'Untitled Conversation' ? extracted.title + ' ' : '';
  const queryText = (titleQuery + humanLines.slice(0, 3).join(' ')).slice(0, 600);

  const results = await searchCapsule(queryText);
  console.log('Capsule: search results', results.length);

  if (results.length > 0) {
    suggestionFired = true;
    renderResults(results, extracted.title);
    openDrawer();
  }
}

setInterval(checkConversation, CHECK_INTERVAL_MS);

// Reset on URL change
let lastUrl = location.href;
const urlObserver = new MutationObserver(() => {
  if (location.href !== lastUrl) {
    lastUrl = location.href;
    lastCheckedExchangeCount = 0;
    suggestionFired = false;
    monitorPaused = true;
    closeDrawer();
    setTimeout(() => { monitorPaused = false; }, 3000);
  }
});
urlObserver.observe(document.body, { childList: true, subtree: true });

// ============================================================
// MESSAGE LISTENER (popup save + inject)
// ============================================================
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'extract') {
    sendResponse(extractConversation());
  }
  if (request.action === 'inject') {
    const inputEl = document.querySelector('[data-testid="chat-input"]') ||
                    document.querySelector('div[contenteditable="true"]');
    if (inputEl) {
      inputEl.focus();
      document.execCommand('insertText', false, request.text);
      sendResponse({ ok: true });
    } else {
      sendResponse({ ok: false, error: 'Input box not found' });
    }
  }
  return true;
});

console.log('Capsule content script loaded v1.2.1');
