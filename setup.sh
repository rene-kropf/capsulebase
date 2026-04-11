#!/bin/bash
# ============================================================
# Capsule - Local Knowledge OS
# File: setup.sh
# Version: 2.0.0
# Date: 2026-04-10
# Changes: M1 + Intel support, PG17, Cloudflare tunnel,
#          launchd auto-start, Ollama optional
# ============================================================

set -e

echo ""
echo "🚀 Capsule Setup"
echo "================================================"

# Detect architecture
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    BREW_PREFIX="/opt/homebrew"
    echo "ℹ️  Detected Apple Silicon (M1/M2/M3)"
else
    BREW_PREFIX="/usr/local"
    echo "ℹ️  Detected Intel Mac"
fi

# Homebrew
if ! command -v brew &> /dev/null; then
    echo "📦 Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    if [ "$ARCH" = "arm64" ]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
fi
echo "✅ Homebrew ready"

# PostgreSQL 17
if ! command -v psql &> /dev/null; then
    echo "📦 Installing PostgreSQL 17..."
    brew install postgresql@17
    echo "export PATH=\"$BREW_PREFIX/opt/postgresql@17/bin:\$PATH\"" >> ~/.zshrc
    export PATH="$BREW_PREFIX/opt/postgresql@17/bin:$PATH"
fi
brew services start postgresql@17 2>/dev/null || true
echo "✅ PostgreSQL ready"

# pgvector
echo "📦 Installing pgvector..."
brew install pgvector
echo "✅ pgvector ready"

# Cloudflare tunnel
if ! command -v cloudflared &> /dev/null; then
    echo "📦 Installing cloudflared..."
    brew install cloudflared
fi
echo "✅ cloudflared ready"

# Ollama (optional — recommended on M1/M2 for fully local setup)
echo ""
read -p "Install Ollama for local AI? Recommended on M1/M2, slow on Intel (y/n): " install_ollama
if [ "$install_ollama" = "y" ]; then
    if ! command -v ollama &> /dev/null; then
        echo "📦 Installing Ollama..."
        brew install ollama
    fi
    echo "📦 Pulling embedding model (nomic-embed-text)..."
    ollama pull nomic-embed-text
    echo "📦 Pulling chat model (llama3.2)..."
    ollama pull llama3.2
    echo "✅ Ollama ready"
else
    echo "⏭  Skipping Ollama — use Claude or OpenAI API instead"
fi

# Create database
echo ""
echo "📦 Creating Capsule database..."
createdb capsule 2>/dev/null || echo "   Database already exists, skipping"
psql capsule -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null
psql capsule -c "ALTER TABLE entries ADD COLUMN IF NOT EXISTS source_url TEXT;" 2>/dev/null || true
echo "✅ Database ready"

# Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt
echo "✅ Python dependencies ready"

# Create .env
if [ ! -f .env ]; then
    cat > .env << 'EOF'
DATABASE_URL=postgresql://localhost/capsule

# AI Provider: claude | openai | ollama
AI_PROVIDER=claude

# Anthropic (recommended for best summaries)
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-haiku-4-5-20251001

# OpenAI (needed for embeddings — even if using Claude for AI)
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

# Ollama (fully local — set AI_PROVIDER=ollama to use)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_EMBED_MODEL=nomic-embed-text

MAILGUN_WEBHOOK_KEY=
EOF
    echo "✅ .env created — add your API keys before starting"
else
    echo "✅ .env already exists"
fi

# launchd auto-start
PLIST="$HOME/Library/LaunchAgents/com.capsule.app.plist"
CAPSULE_DIR="$(pwd)"
PYTHON_PATH="$(which python3)"

python3 -c "
content = '''<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">
<plist version=\"1.0\">
<dict>
    <key>Label</key>
    <string>com.capsule.app</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON_PATH}</string>
        <string>-m</string>
        <string>uvicorn</string>
        <string>main:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>8000</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${CAPSULE_DIR}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${CAPSULE_DIR}/capsule.log</string>
    <key>StandardErrorPath</key>
    <string>${CAPSULE_DIR}/capsule.log</string>
</dict>
</plist>'''
open('${PLIST}', 'w').write(content)
"

launchctl load "$PLIST" 2>/dev/null || true
echo "✅ Capsule set to auto-start on login"

echo ""
echo "================================================"
echo "✅ Setup complete"
echo ""
echo "Next steps:"
echo "  1. Edit .env and add your API keys"
echo "     - ANTHROPIC_API_KEY (for AI summaries)"
echo "     - OPENAI_API_KEY (for embeddings)"
echo "  2. Start Capsule:"
echo "     launchctl start com.capsule.app"
echo "  3. Open http://localhost:8000"
echo "  4. Optional tunnel for remote access:"
echo "     cloudflared tunnel --url http://localhost:8000"
echo ""
