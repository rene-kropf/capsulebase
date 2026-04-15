# CapsuleBase — Local Knowledge OS

**Your AI conversations deserve a memory.**

CapsuleBase saves your Claude, ChatGPT, and Gemini conversations locally — searchable, permanent, and available to Claude as live context during your next conversation.

Free. Open source. Your data stays on your machine.

→ [capsulebase.ai](https://capsulebase.ai)

---

## The problem

Every new AI conversation starts from zero. The research you did last month. The decision you worked through last week. The solution you found after two hours of back-and-forth — gone, unless you remember to go looking for it.

CapsuleBase solves it.

---

## What it does

- **One-click save** — Chrome extension saves any AI conversation to your local knowledge base instantly
- **Bulk import** — Import your entire Claude or ChatGPT conversation history in minutes
- **Hybrid search** — Text and semantic search combined. Find what you mean, not just what you typed
- **Auto summaries** — Every saved conversation gets an auto-generated title, summary, tags, and category. The index builds itself
- **Cross-platform** — Claude and ChatGPT conversations in one searchable local archive
- **Truly local** — PostgreSQL + pgvector on your machine. No cloud sync. No account required

---

## Requirements

- Mac (Apple Silicon or Intel) — Windows and Linux support coming
- Python 3.11+
- PostgreSQL
- An [Anthropic API key](https://console.anthropic.com/) for AI summaries — or run fully local with Ollama (no API key required)

---

## Install

```bash
git clone https://github.com/rene-kropf/capsulebase.git
cd capsulebase
bash setup.sh
```

The setup script handles dependencies, database setup, and configuration.

---

## Tech stack

- **Backend** — Python / FastAPI
- **Database** — PostgreSQL + pgvector
- **Embeddings** — Ollama (fully local) or OpenAI
- **Summaries & tagging** — Claude API or Ollama (fully local)
- **Chrome extension** — saves conversations from Claude, ChatGPT, Gemini

---

## Philosophy

Most tools that claim to protect your privacy still send your data somewhere for processing. CapsuleBase is different. The database is yours. The search index is yours. Everything runs on your machine.

Hosting your thinking on someone else's AI platform is like selling on Amazon while Amazon watches what sells. Local first isn't the alternative to the cloud — it's the grown-up response to what the cloud turned out to be.

No subscription that can disappear. No vendor who can change the terms. Your knowledge, permanently yours.

---

## For teams

**Talon** is the business version of CapsuleBase — shared knowledge bases, role-based access, and institutional memory that stays with the organization, not the individual. Currently in development.

→ [talon-ops.com](https://talon-ops.com) — join the waitlist

---

## Current state & roadmap

CapsuleBase is actively developed and already useful — but here's an honest picture of where things stand.

**What works now**
- Save and search Claude and ChatGPT conversations
- Chrome extension (Claude and ChatGPT)
- Bulk import from Claude and ChatGPT export files
- Summaries, titles, tags, and categories via Claude API or Ollama
- Fully local embeddings via Ollama (no API key required)
- Hybrid text + semantic search

**Coming next**
- Gemini conversation import and Chrome extension support
- Perplexity support
- Email ingestion
- Windows and Linux support

---

## License

MIT — do what you want with it.

---

## Built by

[Rene Kropf](https://emmausdev.com) / [Emmaus Development](https://emmausdev.com) — Bartlesville, Oklahoma

🐾 [Adopt a Pet — Get a Dog](https://www.petfinder.com/)
