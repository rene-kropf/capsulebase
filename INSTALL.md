# CapsuleBase — Installation Guide

This guide walks through every step from a clean Mac to a fully running CapsuleBase. Nothing is assumed to be already installed.

**Platform:** Mac (Apple Silicon or Intel)  
**Time:** 30–45 minutes on a fresh machine

---

## What you'll end up with

- A local PostgreSQL database storing your conversations
- A FastAPI backend running on your machine
- A Chrome extension to save conversations in one click
- A side panel in Chrome that surfaces related memory while you work
- An MCP server that connects your history to Claude Desktop
- A Cloudflare tunnel so the Chrome extension can reach your local backend

---

## Step 1 — Homebrew

Homebrew is the package manager for Mac. If you already have it, skip this.

Open Terminal and run:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the prompts. When it finishes, verify:

```bash
brew --version
```

If you're on Apple Silicon and it says `brew not found`, add it to your PATH:

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
eval "$(/opt/homebrew/bin/brew shellenv)"
```

---

## Step 2 — Python 3.11+

Check what you have:

```bash
python3 --version
```

If it's 3.11 or higher, skip to Step 3. If not:

```bash
brew install python@3.11
```

---

## Step 3 — PostgreSQL 17

The setup script handles this, but if you want to do it manually:

```bash
brew install postgresql@17
brew services start postgresql@17
```

Add to your PATH — Apple Silicon:

```bash
echo 'export PATH="/opt/homebrew/opt/postgresql@17/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Intel Mac:

```bash
echo 'export PATH="/usr/local/opt/postgresql@17/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Verify:

```bash
psql --version
```

---

## Step 4 — pgvector

```bash
brew install pgvector
```

---

## Step 5 — Cloudflare Account (free)

The Chrome extension needs to reach your local backend from any browser tab. A Cloudflare tunnel provides a stable URL without opening ports on your router.

1. Go to [cloudflare.com](https://cloudflare.com) and create a free account — no credit card required
2. You don't need to add a domain for local use

The setup script installs `cloudflared` automatically. You'll configure the tunnel after the backend is running.

---

## Step 6 — Clone the repo

```bash
git clone https://github.com/rene-kropf/capsulebase.git
cd capsulebase
```

---

## Step 7 — Run the setup script

```bash
bash setup.sh
```

This handles everything automatically:
- Detects Apple Silicon vs Intel
- Installs PostgreSQL 17 if not present
- Installs pgvector
- Installs cloudflared
- Optionally installs Ollama (for fully local AI — recommended on M1/M2)
- Creates the `capsule` database and enables pgvector
- Installs Python dependencies
- Creates your `.env` file
- Sets up launchd so Capsule starts automatically on login

**If the script asks about Ollama:** Choose `y` on Apple Silicon for a fully local setup. Choose `n` on Intel (too slow) and use the Claude or OpenAI API instead.

---

## Step 8 — Add your API keys

Open the `.env` file the setup script created:

```bash
nano .env
```

Fill in your keys:

```
ANTHROPIC_API_KEY=your_key_here    # for AI summaries
OPENAI_API_KEY=your_key_here       # for embeddings
```

You need at least one. Both is fine. If you chose Ollama in setup, you can skip both and set `AI_PROVIDER=ollama`.

**Get an Anthropic API key:** [console.anthropic.com](https://console.anthropic.com)  
**Get an OpenAI API key:** [platform.openai.com](https://platform.openai.com)

Save and close (`Ctrl+X`, `Y`, `Enter` in nano).

---

## Step 9 — Start the backend

```bash
launchctl start com.capsule.app
```

Or start it manually in the foreground (useful for seeing logs):

```bash
python3 -m uvicorn main:app --reload --port 8000
```

Test it:

```bash
curl http://localhost:8000/health
```

Should return: `{"status":"ok","service":"Capsule","version":"2.1.0"}`

Open the UI in your browser: [http://localhost:8000](http://localhost:8000)

---

## Step 10 — Cloudflare Tunnel

The tunnel lets the Chrome extension reach your backend.

**Authenticate cloudflared:**

```bash
cloudflared tunnel login
```

This opens a browser window. Log in to your Cloudflare account and authorize.

**Quick tunnel for testing (no domain needed):**

```bash
cloudflared tunnel --url http://localhost:8000
```

This gives you a temporary public URL like `https://some-random-name.trycloudflare.com`. Copy it — you'll need it when configuring the Chrome extension.

**Persistent tunnel (recommended for daily use):**

```bash
cloudflared tunnel create capsule
cloudflared tunnel run capsule
```

---

## Step 11 — Chrome Extension

1. Open Chrome and go to `chrome://extensions`
2. Enable **Developer mode** (toggle in the top right corner)
3. Click **Load unpacked**
4. Navigate to the `extension` folder inside the repo and select it
5. The Capsule icon appears in your Chrome toolbar

**Configure the extension URL:**
- Click the Capsule icon in Chrome
- In the **Capsule URL** field at the bottom, enter your Cloudflare tunnel URL
- Click **Save**

> **Note:** If you're only using Capsule on your local machine (not from other devices), `http://localhost:8000` works without a tunnel.

---

## Step 12 — Claude Desktop MCP Integration

This connects Capsule to Claude Desktop so Claude automatically searches your history before answering.

Find your Claude Desktop config:

```bash
open ~/Library/Application\ Support/Claude/
```

Open `claude_desktop_config.json` and add:

```json
{
  "mcpServers": {
    "capsule": {
      "command": "python3",
      "args": ["/full/path/to/capsulebase/capsule_mcp.py"],
      "env": {
        "CAPSULEBASE_URL": "http://localhost:8000"
      }
    }
  }
}
```

Replace `/full/path/to/capsulebase/` with your actual path. To find it:

```bash
cd capsulebase && pwd
```

Restart Claude Desktop (Cmd+Q, then reopen — don't just close the window). Capsule should appear in Claude's available tools.

---

## Step 13 — Load sample data

The repo includes sample conversations so you can verify everything is working before saving your own.

Make sure the backend is running, then:

```bash
python3 seed_data.py
```

Open [http://localhost:8000](http://localhost:8000) and search for something — try `"local-first"` or `"FileMaker"`. If results come back, you're fully set up.

---

## Importing your existing conversations

**From Claude:**

Export your history at [claude.ai/settings](https://claude.ai/settings) → Export Data. Then:

```bash
python3 import_claude.py conversations.json
# Preview first without importing:
python3 import_claude.py conversations.json --dry-run
# Import only first 50:
python3 import_claude.py conversations.json --limit 50
```

**From ChatGPT:**

Export at [chat.openai.com](https://chat.openai.com) → Settings → Data Controls → Export. Then:

```bash
python3 import_chatgpt.py conversations.json
```

---

## Troubleshooting

**Backend won't start**
```bash
brew services list | grep postgresql
brew services restart postgresql@17
```

**pgvector error on startup**
```bash
psql capsule -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**Chrome extension can't connect**
- Confirm the backend is running: `curl http://localhost:8000/health`
- Confirm the Cloudflare tunnel is running
- Check the URL in the extension settings matches your tunnel URL exactly (no trailing slash)

**Claude Desktop doesn't show Capsule**
- Double-check the full path in `claude_desktop_config.json`
- Fully quit Claude Desktop with Cmd+Q before restarting
- Check for JSON syntax errors in the config file

**Re-process all entries with fresh AI summaries**
```bash
python3 resummary.py
```

---

## Uninstall

```bash
launchctl remove com.capsule.app
brew services stop postgresql@17
dropdb capsule
cd .. && rm -rf capsulebase
```

Remove the Chrome extension at `chrome://extensions`.  
Remove the `capsule` block from `claude_desktop_config.json`.

---

## Questions

Open an issue on GitHub or reach out at [emmausdev.com](https://emmausdev.com).
