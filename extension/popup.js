// ============================================================
// Capsule Save — Popup Script
// ============================================================

const DEFAULT_URL = 'http://localhost:8000';

async function getCapsuleUrl() {
  return new Promise(resolve => {
    chrome.storage.local.get(['capsuleUrl'], result => {
      resolve(result.capsuleUrl || DEFAULT_URL);
    });
  });
}

async function saveCapsuleUrl(url) {
  return new Promise(resolve => {
    chrome.storage.local.set({ capsuleUrl: url }, resolve);
  });
}

async function init() {
  const main = document.getElementById('main');

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const isClaudeTab = tab?.url?.includes('claude.ai/chat');

  if (!isClaudeTab) {
    main.innerHTML = `
      <div class="not-claude">
        Open a Claude conversation<br>to save it to Capsule.
      </div>
    `;
    return;
  }

  const capsuleUrl = await getCapsuleUrl();

  main.innerHTML = `
    <div class="body">
      <div class="title-preview" id="titlePreview">Loading conversation...</div>
      <div class="meta" id="metaPreview"></div>
      <button class="btn-save" id="saveBtn" disabled>Save to Capsule</button>
      <div class="status" id="status"></div>
      <div class="settings">
        <div class="settings-label">Capsule URL</div>
        <div class="settings-row">
          <input class="settings-input" id="urlInput" value="${capsuleUrl}" placeholder="http://localhost:8000">
          <button class="btn-save-url" id="saveUrlBtn">Save</button>
        </div>
      </div>
    </div>
  `;

  const saveBtn = document.getElementById('saveBtn');
  const status = document.getElementById('status');
  const titlePreview = document.getElementById('titlePreview');
  const metaPreview = document.getElementById('metaPreview');
  const urlInput = document.getElementById('urlInput');
  const saveUrlBtn = document.getElementById('saveUrlBtn');

  saveUrlBtn.addEventListener('click', async () => {
    await saveCapsuleUrl(urlInput.value.trim());
    saveUrlBtn.textContent = '✓';
    setTimeout(() => saveUrlBtn.textContent = 'Save', 1500);
  });

  let extracted = null;
  try {
    const response = await chrome.tabs.sendMessage(tab.id, { action: 'extract' });
    if (response?.error) {
      titlePreview.textContent = 'Could not read conversation';
      metaPreview.textContent = response.error;
    } else {
      extracted = response;
      titlePreview.textContent = response.title;
      const turns = Math.floor(response.turnCount / 2);
      metaPreview.textContent = `${turns} exchange${turns !== 1 ? 's' : ''} · claude.ai`;
      saveBtn.disabled = false;
    }
  } catch (e) {
    titlePreview.textContent = 'Could not read conversation';
    metaPreview.textContent = 'Try refreshing the page';
  }

  // Check for pending related results
  chrome.storage.session.get(['pendingResults', 'pendingTitle'], async (data) => {
    if (data.pendingResults?.length) {
      const relatedDiv = document.createElement('div');
      relatedDiv.style.cssText = 'margin-top:10px;padding:10px;background:#111a14;border:1px solid #10b981;border-radius:8px;cursor:pointer;';
      relatedDiv.innerHTML = `<div style="font-size:11px;color:#10b981;font-weight:700;">🧠 ${data.pendingResults.length} related memory found</div><div style="font-size:10px;color:#8b92a5;margin-top:3px;">Click to view in side panel</div>`;
      relatedDiv.addEventListener('click', async () => {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        await chrome.sidePanel.open({ tabId: tab.id });
        chrome.action.setBadgeText({ text: '', tabId: tab.id });
        window.close();
      });
      document.getElementById('main').appendChild(relatedDiv);
    }
  });

  saveBtn.addEventListener('click', async () => {
    if (!extracted) return;

    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving...';
    status.textContent = '';
    status.className = 'status loading';

    const url = urlInput.value.trim() || DEFAULT_URL;

    try {
      const res = await fetch(`${url}/import/conversation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platform: 'claude',
          title: extracted.title,
          content: extracted.content,
          source_url: extracted.url
        })
      });

      if (!res.ok) throw new Error(`Server returned ${res.status}`);

      const data = await res.json();
      const action = data.action === 'updated' ? '✓ Updated in Capsule' : '✓ Saved to Capsule';
      status.textContent = action;
      status.className = 'status success';
      saveBtn.textContent = '✓ Done';

    } catch (e) {
      status.textContent = '✗ Could not reach Capsule — is it running?';
      status.className = 'status error';
      saveBtn.disabled = false;
      saveBtn.textContent = 'Save to Capsule';
    }
  });
}

init();
