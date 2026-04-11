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

  // Check if we're on claude.ai
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

  // Save URL button
  saveUrlBtn.addEventListener('click', async () => {
    await saveCapsuleUrl(urlInput.value.trim());
    saveUrlBtn.textContent = '✓';
    setTimeout(() => saveUrlBtn.textContent = 'Save', 1500);
  });

  // Extract conversation preview
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

  // Save button
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
          content: extracted.content
        })
      });

      if (!res.ok) throw new Error(`Server returned ${res.status}`);

      status.textContent = '✓ Saved to Capsule';
      status.className = 'status success';
      saveBtn.textContent = '✓ Saved';

    } catch (e) {
      status.textContent = '✗ Could not reach Capsule — is it running?';
      status.className = 'status error';
      saveBtn.disabled = false;
      saveBtn.textContent = 'Save to Capsule';
    }
  });
}

init();
