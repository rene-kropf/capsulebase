// ============================================================
// Capsule Save — Content Script
// Runs on claude.ai, extracts conversation on request
// ============================================================

function extractConversation() {
  try {
    // Get title
    const titleEl = document.querySelector('[data-testid="chat-title-button"]');
    const title = titleEl?.innerText?.trim() || 'Untitled Conversation';

    // Navigate to turn container
    const scrollEl = document.querySelector('.overflow-y-auto');
    if (!scrollEl) return { error: 'Could not find conversation container' };

    const turnsContainer = scrollEl
      ?.children[2]
      ?.children[0]
      ?.children[0]
      ?.children[1]
      ?.children[0]
      ?.children[0]
      ?.children[0];

    if (!turnsContainer) return { error: 'Could not find turns container' };

    const turns = [...turnsContainer.children];
    if (!turns.length) return { error: 'No conversation turns found' };

    // Build conversation text
    const lines = [];
    turns.forEach(turn => {
      const isUser = !!turn.querySelector('[data-testid="user-message"]');

      let text = '';
      if (isUser) {
        // Grab just the user message div — clean, no timestamps
        const userMsg = turn.querySelector('[data-testid="user-message"]');
        text = userMsg?.innerText?.trim() || '';
      } else {
        // Grab assistant response — row-start-2 is the actual response, row-start-1 is thinking block
        const responseEl = turn.querySelector('[class*="font-claude-response"]');
        if (responseEl) {
          // Try to get just the response content, skipping thinking blocks
          const actualResponse = responseEl.querySelector('.row-start-2');
          text = (actualResponse || responseEl).innerText?.trim() || '';
        }
      }

      if (!text) return;
      lines.push(`${isUser ? 'HUMAN' : 'ASSISTANT'}: ${text}`);
    });

    if (!lines.length) return { error: 'No content extracted' };

    return {
      title,
      content: lines.join('\n\n'),
      turnCount: turns.length,
      url: window.location.href
    };

  } catch (e) {
    return { error: e.message };
  }
}

// Listen for message from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'extract') {
    sendResponse(extractConversation());
  }
  return true;
});
