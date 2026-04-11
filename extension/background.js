// ============================================================
// Capsule Save — Background Service Worker v1.2.2
// Handles fetch on behalf of content script (avoids page CSP)
// ============================================================

const DEFAULT_URL = 'http://localhost:8000';
const MIN_HITS = 1;

chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: false });

chrome.alarms.create('keepAlive', { periodInMinutes: 0.4 });
chrome.alarms.onAlarm.addListener(() => {});

async function getCapsuleUrl() {
  return new Promise(resolve => {
    chrome.storage.local.get(['capsuleUrl'], result => {
      resolve(result.capsuleUrl || DEFAULT_URL);
    });
  });
}

function extractKeywords(text) {
  const stopwords = new Set([
    'the','a','an','and','or','but','in','on','at','to','for','of','with',
    'is','are','was','were','be','been','have','has','had','do','does','did',
    'will','would','could','should','may','might','i','you','he','she','it',
    'we','they','me','him','her','us','them','my','your','his','its','our',
    'their','this','that','these','those','what','how','why','when','where',
    'who','which','can','just','about','so','if','then','than','too','very',
    'also','from','up','out','more','get','got','im','dont','into','want',
    'like','know','think','need','make','going','have','been','some','they'
  ]);
  return [...new Set(
    text.toLowerCase()
      .replace(/[^a-z0-9\s]/g, ' ')
      .split(/\s+/)
      .filter(w => w.length > 3 && !stopwords.has(w))
  )];
}

function scoreEntry(entry, keywords) {
  const titleLower = (entry.title || '').toLowerCase();
  const summaryLower = (entry.summary || '').toLowerCase();
  const tagsText = Array.isArray(entry.tags) ? entry.tags.join(' ').toLowerCase() : '';

  let hits = 0, score = 0;
  keywords.forEach(kw => {
    if (titleLower.includes(kw))   { hits++; score += 3; }
    if (tagsText.includes(kw))     { hits++; score += 2; }
    if (summaryLower.includes(kw)) { hits++; score += 1; }
  });
  return { hits, score };
}

async function localSearch(query) {
  const CAPSULE_URL = await getCapsuleUrl();
  const keywords = extractKeywords(query);
  console.log('Capsule: keywords:', keywords);
  if (!keywords.length) return [];

  const res = await fetch(`${CAPSULE_URL}/entries?limit=500`);
  if (!res.ok) throw new Error('Entries fetch failed: ' + res.status);
  const entries = await res.json();

  const scored = entries
    .map(entry => {
      const { hits, score } = scoreEntry(entry, keywords);
      return { ...entry, _hits: hits, _score: score };
    })
    .filter(e => e._hits >= MIN_HITS)
    .sort((a, b) => b._score - a._score)
    .slice(0, 5);

  console.log('Capsule: results:', scored.map(r => `[${r._score}] ${r.title}`));
  return scored;
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'capsule_search') {
    localSearch(message.query || '')
      .then(results => sendResponse({ results }))
      .catch(err => { console.error(err); sendResponse({ results: [] }); });
    return true;
  }
});
