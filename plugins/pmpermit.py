from telethon import events
from telethon.tl.functions.contacts import BlockRequest, UnblockRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import UserStatusOffline, UserStatusRecently, UserStatusOnline
from datetime import datetime, timedelta
from cybernexus import client
import json
import os

print("[PMPermit] Plugin loaded successfully ✅")

APPROVED_USERS_FILE = "approved_users.json"

def load_approved_users():
    try:
        if os.path.exists(APPROVED_USERS_FILE):
            with open(APPROVED_USERS_FILE, "r") as f:
                return set(json.load(f))
    except Exception as e:
        print(f"[PMPermit] Error loading approved_users.json: {e}")
    return set()

def save_approved_users():
    try:
        with open(APPROVED_USERS_FILE, "w") as f:
            json.dump(list(approved_users), f)
    except Exception as e:
        print(f"[PMPermit] Error saving approved_users.json: {e}")

approved_users = load_approved_users()

# ---------------- HELP ----------------
@client.on(events.NewMessage(pattern=r"^\.help_pmpermit$", outgoing=True))
async def pmpermit_help(event):
    try:
        help_message = (
            "💬 **PM Permit Control Panel** 💬\n\n"
            "**Commands:**\n"
            "✅ `.a` – Approve a user\n"
            "❌ `.da` – Disapprove a user\n"
            "🔒 `.block <id>` – Block a user\n"
            "🔓 `.unblock <id>` – Unblock a user\n"
            "📜 `.listapproved` – Show approved users\n\n"
            "**Features:**\n"
            "• No auto-message when you're online\n"
            "• Shows your last seen status\n"
            "• Prevents daily duplicate replies"
        )
        await event.edit(help_message)
    except Exception as e:
        print(f"[PMPermit] Help command error: {e}")

# ---------------- UTIL ----------------
async def get_last_seen_status():
    """Safely get owner's last seen status text."""
    try:
        me = await client(GetFullUserRequest("me"))
        status = me.user.status
        if isinstance(status, UserStatusOnline):
            return "🟢 Online"
        elif isinstance(status, UserStatusRecently):
            return "🕓 Recently active"
        elif isinstance(status, UserStatusOffline):
            delta = datetime.now() - status.was_online
            if delta < timedelta(minutes=1):
                return "🕒 Just now"
            elif delta < timedelta(hours=1):
                return f"⌛ {int(delta.seconds/60)} min ago"
            elif delta < timedelta(days=1):
                return f"🕘 {int(delta.seconds/3600)} hours ago"
            else:
                return f"📅 {status.was_online.strftime('%d %b, %I:%M %p')}"
        return "👀 Last seen a while ago"
    except Exception:
        return "⚙️ Unknown"

# ---------------- COMMANDS ----------------
@client.on(events.NewMessage(pattern=r"^\.a( (.*)|$)", outgoing=True))
async def approve_user(event):
    try:
        reply = await event.get_reply_message()
        user = event.pattern_match.group(2) or (reply.sender_id if reply else None)
        if not user:
            return await event.edit("⚠️ **Reply to a user or specify ID to approve.**")
        user = int(user)
        approved_users.add(user)
        save_approved_users()
        await event.edit(f"✅ **Approved user:** `{user}`")
    except Exception as e:
        print(f"[PMPermit] Approve error: {e}")

@client.on(events.NewMessage(pattern=r"^\.da( (.*)|$)", outgoing=True))
async def disapprove_user(event):
    try:
        reply = await event.get_reply_message()
        user = event.pattern_match.group(2) or (reply.sender_id if reply else None)
        if not user:
            return await event.edit("⚠️ **Reply or specify ID to disapprove.**")
        user = int(user)
        approved_users.discard(user)
        save_approved_users()
        await event.edit(f"🚫 **Disapproved user:** `{user}`")
    except Exception as e:
        print(f"[PMPermit] Disapprove error: {e}")

@client.on(events.NewMessage(pattern=r"^\.listapproved$", outgoing=True))
async def list_approved(event):
    try:
        if not approved_users:
            return await event.edit("🚫 **No approved users found.**")
        users = "\n".join(f"• `{u}`" for u in approved_users)
        await event.edit(f"✅ **Approved Users:**\n{users}")
    except Exception as e:
        print(f"[PMPermit] List error: {e}")

@client.on(events.NewMessage(pattern=r"^\.block( (.*)|$)", outgoing=True))
async def block_user(event):
    try:
        reply = await event.get_reply_message()
        user = event.pattern_match.group(2) or (reply.sender_id if reply else None)
        if not user:
            return await event.edit("❌ **Reply or specify ID to block.**")
        user = int(user)
        await client(BlockRequest(user))
        approved_users.discard(user)
        save_approved_users()
        await event.edit(f"🚫 **Blocked user:** `{user}`")
    except Exception as e:
        print(f"[PMPermit] Block error: {e}")

@client.on(events.NewMessage(pattern=r"^\.unblock( (.*)|$)", outgoing=True))
async def unblock_user(event):
    try:
        reply = await event.get_reply_message()
        user = event.pattern_match.group(2) or (reply.sender_id if reply else None)
        if not user:
            return await event.edit("❌ **Reply or specify ID to unblock.**")
        user = int(user)
        await client(UnblockRequest(user))
        approved_users.add(user)
        save_approved_users()
        await event.edit(f"✅ **Unblocked user:** `{user}`")
    except Exception as e:
        print(f"[PMPermit] Unblock error: {e}")

# ---------------- MAIN HANDLER ----------------
@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def monitor_pm(event):
    try:
        user = event.sender_id
        sender = await event.get_sender()
        if sender.bot or user in approved_users:
            return

        # Skip auto-message if owner is online/recently active
        status = await get_last_seen_status()
        if "Online" in status or "Recently" in status:
            return

        # Prevent repeated daily responses
        async for msg in client.iter_messages(user, from_user="me", limit=1):
            if msg.date.date() == datetime.now().date():
                return

        msg = (
            f"👋 **Hello!**\n\n"
            f"My owner is currently **{status}**.\n"
            f"Your message will be seen soon ⏳\n\n"
            f"Please avoid sending multiple messages — that may lead to a block. 🚫\n\n"
            f"Thank you for your patience 🙏"
        )
        await event.respond(msg)
    except Exception as e:
        print(f"[PMPermit] Monitor error: {e}")
