#!/usr/bin/env python3
# ============================================================
# Capsule - Local Knowledge OS
# File: seed_data.py
# Version: 1.0.0
# Date: 2026-03-05
# Changes: Initial build - sample data for testing
# ============================================================

import httpx
import asyncio

API = "http://localhost:8000"

SAMPLE_CONVERSATIONS = [
    {
        "platform": "claude",
        "title": "Local-First Architecture for SimpleSuite",
        "content": """Me: I'm building a suite of local-first apps for small businesses. 
Thinking about how to handle data sync between devices without going full cloud.

Claude: Local-first is the right call for your audience. The key principle is 
that the app works fully offline and syncs opportunistically rather than requiring 
a connection to function. For SimpleSuite specifically I'd think about it in layers.

The local data layer is SQLite per device — fast, reliable, zero infrastructure. 
Above that you have a sync layer that only fires when connectivity is available. 
CRDTs (conflict-free replicated data types) are the cleanest approach for sync 
because they handle conflicts automatically without a central authority.

For your use case a simpler approach might be a last-write-wins strategy with 
timestamps, combined with a lightweight relay on Cloudflare Workers. The relay 
never stores data — it just routes sync packets between devices. Your data never 
actually lives in the cloud, it just passes through.

Me: That relay idea is interesting. So the Cloudflare Worker is stateless?

Claude: Exactly. Think of it as a post office that never opens the letters. 
Device A sends an encrypted sync packet to the Worker, the Worker holds it 
briefly (KV store with a short TTL), Device B picks it up. The Worker sees 
only encrypted bytes. No data at rest in the cloud.

This is actually how the AOTE crew schedule Kanban you built works — 
push-based via Cloudflare KV. Same pattern scales to SimpleSuite sync.""",
        "conversation_date": "2026-01-15T10:30:00"
    },
    {
        "platform": "chatgpt",
        "title": "FileMaker Performance — Unstored Calculations Strategy",
        "content": """Me: I have a FileMaker solution with 165 unstored calculations 
in a table with 180,000 records. Performance is killing us on reports. 
What's the right strategy?

GPT: With 180K records and that many unstored calcs, you're essentially 
recalculating the entire table on every find and sort. Here's the priority order:

1. Identify which unstored calcs are used in finds, sorts, or reports — 
those are your highest pain points. Convert those first.

2. For calcs that reference related records, storing them is tricky because 
FileMaker won't let you store a calc that looks across a relationship. 
The workaround is a script trigger on commit that writes the calculated 
value to a regular number or text field.

3. For date-based calcs like "days since" — these can never be stored 
because they change daily. Handle these in the report script itself 
using variables rather than table fields.

Me: The biggest offender is a profit margin calc that joins to three 
related tables. Any way to store that?

GPT: Yes — script trigger approach. On record commit, run a script that:
- Fetches the related values explicitly
- Calculates the margin in a script variable  
- Sets a stored number field with the result

The stored field is then findable, sortable, and blazing fast. 
The trade-off is the value is only updated on commit, not real-time. 
For a margin field that's almost always acceptable.""",
        "conversation_date": "2026-02-01T14:15:00"
    },
    {
        "platform": "claude",
        "title": "Capsule Architecture — Email Intake Pipeline",
        "content": """Me: I want to build a personal knowledge base where I can forward 
emails and web pages to a dedicated address and have AI automatically 
classify and tag them. Everything local.

Claude: That's a clean problem with a clean solution. The architecture 
breaks into four pieces.

Email intake — Mailgun catches anything sent to save@yourdomain.com 
and fires a webhook. That webhook hits a local FastAPI listener running 
on your machine via a Cloudflare Tunnel. The tunnel is the only thing 
touching the internet — everything after it is local.

AI processing — the listener hands the email content to an Ollama 
instance running locally. A simple prompt extracts title, summary, 
tags, and category from the subject and body. No data leaves your machine.

Storage — Postgres with pgvector. The processed record goes in with 
its vector embedding alongside it. The embedding is what makes 
semantic search possible — you find things by meaning, not just keywords.

UI — a clean three-panel HTML app. Projects on the left, entry list 
in the middle, detail on the right. Search bar at the top toggles 
between semantic and text search.

Me: What about importing old conversations from ChatGPT and Claude?

Claude: Both platforms offer full JSON exports. A simple import endpoint 
on the FastAPI listener accepts a conversation payload — platform, title, 
content — runs it through the same AI processing pipeline, and stores it 
with a conversations record that includes a branch_of field for when 
a single topic spanned multiple chat sessions.

Suddenly your entire knowledge history, regardless of which LLM you 
used, is in one local searchable database you own completely.""",
        "conversation_date": "2026-02-20T09:00:00"
    },
    {
        "platform": "manual",
        "title": "SimpleSuite Pricing Strategy Notes",
        "content": """Notes from thinking session - March 2026

Pricing tiers that feel right:
- Mini apps / single purpose: $29-39
- Core apps (Contacts, JobTracker): $49-79  
- BusinessPro flagship: $99-129
- Modules (AI, Sharing, Stripe): $29-49 each

One-time. No surprises. That's the whole promise.

Key insight from today: the persona isn't buying "no subscription."
They're buying NO SURPRISES and NO HOSTAGE SITUATIONS.

The fee they can budget. The surprise they can't tolerate.

Data ownership angle lands hardest as EXIT FREEDOM.
"Try to export your data from that other tool. Go ahead. I'll wait."

Customization funnel:
- Someone buys BusinessPro for $99
- Loves it, outgrows it, needs it shaped to their workflow
- That conversation is easy — they already trust the work
- Custom project comes through the door warm

The product line is the sales tool. No cold outreach needed.

Modules to build:
1. AI/LLM connector (Ollama local + cloud API)
2. Sharing/sync (the toaster — just works)
3. Stripe payments
4. Webhook/API connector (pipeline ready)

Stripe is #1 priority after core apps. 
Moment someone customizes BusinessPro the next question is always 
"can it take payments."
""",
        "conversation_date": "2026-03-01T16:45:00"
    },
    {
        "platform": "claude",
        "title": "Clarity Signal — Content Strategy Deep Dive",
        "content": """Me: I'm building a content channel called Clarity Signal. 
The core philosophy is that clarity brings rest even when answers 
are incomplete. I want to write about civilizational cycles and 
practical responses to systemic instability. Where do I start?

Claude: The channel name does a lot of work. Clarity Signal implies 
there's noise everywhere and you're offering a cleaner signal — 
that's a strong implicit promise.

The civilizational cycles angle is rich but can feel academic. 
The practical responses piece is what makes it land for real people. 
Every piece should have that structure: here's the pattern I'm seeing 
in history, here's what it means for how you live and work right now.

For the first five pieces I'd think about:
1. The piece that defines your worldview — what are you seeing that 
   others aren't naming clearly
2. A historical parallel that's viscerally relevant right now
3. The local-first / data sovereignty piece — this connects directly 
   to your work and is timely
4. Something about the pace of change and why most frameworks for 
   coping with it are wrong
5. A practical piece — what does a person actually do with all this

The tagline "clarity brings rest even when answers are incomplete" 
is your north star editorially. Every piece should leave the reader 
calmer and clearer, not more anxious. That's a real differentiator 
from most commentary which leaves people activated but directionless.

Me: The audience I'm thinking about is people who sense something 
is shifting but don't have language for it yet.

Claude: That's exactly the right audience and it's underserved. 
The people who are already deep in the discourse don't need you. 
The people who feel the shift but haven't found their footing — 
they need someone to name it without catastrophizing.

Your job is to be the calm voice in the room who says 
"yes, this is real, here's what I see, here's what I'd do." 
Not a prophet. Not an alarmist. Just someone who's been paying 
attention and is willing to say it plainly.""",
        "conversation_date": "2026-02-10T11:20:00"
    }
]


async def seed():
    print("🌱 Seeding Capsule with sample data...")
    print(f"   Connecting to {API}")
    print()

    async with httpx.AsyncClient(timeout=120.0) as client:

        # Health check first
        try:
            res = await client.get(f"{API}/health")
            res.raise_for_status()
            print("✅ Backend is running")
        except Exception:
            print("❌ Cannot connect to backend.")
            print("   Start it first: python3 -m uvicorn main:app --reload --port 8000")
            return

        # Import each conversation
        success = 0
        for i, conv in enumerate(SAMPLE_CONVERSATIONS, 1):
            try:
                res = await client.post(
                    f"{API}/import/conversation",
                    json=conv
                )
                res.raise_for_status()
                data = res.json()
                print(f"✅ [{i}/{len(SAMPLE_CONVERSATIONS)}] {conv['title'][:60]}")
                success += 1
            except Exception as e:
                print(f"❌ [{i}] Failed: {conv['title'][:50]} — {e}")

        print()
        print(f"🎉 Done — {success}/{len(SAMPLE_CONVERSATIONS)} entries imported")
        print("   Open capsule.html in your browser to see them")


if __name__ == "__main__":
    asyncio.run(seed())
