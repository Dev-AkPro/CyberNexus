from telethon import events
from telethon.tl.functions.contacts import BlockRequest, UnblockRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import UserStatusOffline, UserStatusRecently, UserStatusOnline
from datetime import datetime, timedelta
from cybernexus import client
import json
import os

# File to store approved users
APPROVED_USERS_FILE = "approved_users.json"

# Load approved users safely
def load_approved_users():
    if os.path.exists(APPROVED_USERS_FILE):
        try:
            with open(APPROVED_USERS_FILE, "r") as f:
                return set(json.load(f))
        except json.JSONDecodeError:
            return set()
    return set()

# Save approved users
def save_approved_users():
    with open(APPROVED_USERS_FILE, "w") as f:
        json.dump(list(approved_users), f)

approved_users = load_approved_users()

# 📚 Help Command
@client.on(events.NewMessage(pattern=r"^\.help_pmpermit$", outgoing=True))
async def pmpermit_help(event):
    help_message = (
        "💬 **PM Permit Control Panel** 💬\n\n"
        "**Commands:**\n"
        "✅ `.a` – Approve a user (reply or use ID)\n"
        "❌ `.da` – Disapprove a user (reply or use ID)\n"
        "🔒 `.block <id>` – Block a user\n"
        "🔓 `.unblock <id>` – Unblock a user\n"
        "📜 `.listapproved` – List all approved users\n\n"
        "**Features:**\n"
        "• Doesn’t send auto-message when you’re online.\n"
        "• Shows your last seen time automatically.\n"
        "• Avoids duplicate daily replies.\n"
        "• Looks professional & premium."
    )
    await event.edit(help_message)

# ✅ Approve user
@client.on(events.NewMessage(pattern=r"^\.a( (.*)|$)", outgoing=True))
async def approve_user(event):
    global approved_users
    reply = await event.get_reply_message()
    user = event.pattern_match.group(2) or (reply.sender_id if reply else None)

    if not user:
        return await event.edit("⚠️ **Reply to a user or specify their ID to approve.**")

    try:
        user = int(user)
    except ValueError:
        return await event.edit("❌ **Invalid user ID.**")

    approved_users.add(user)
    save_approved_users()
    await event.edit(f"✅ **Approved user:** `{user}`")

# ❌ Disapprove user
@client.on(events.NewMessage(pattern=r"^\.da( (.*)|$)", outgoing=True))
async def disapprove_user(event):
    global approved_users
    reply = await event.get_reply_message()
    user = event.pattern_match.group(2) or (reply.sender_id if reply else None)

    if not user:
        return await event.edit("⚠️ **Reply to a user or specify their ID to disapprove.**")

    try:
        user = int(user)
    except ValueError:
        return await event.edit("❌ **Invalid user ID.**")

    if user in approved_users:
        approved_users.remove(user)
        save_approved_users()
        await event.edit(f"🚫 **Disapproved user:** `{user}`")
    else:
        await event.edit("⚠️ **That user wasn’t approved.**")

# 🚫 Block a User
@client.on(events.NewMessage(pattern=r"^\.block( (.*)|$)", outgoing=True))
async def block_user(event):
    global approved_users
    reply = await event.get_reply_message()
    user = event.pattern_match.group(2) or (reply.sender_id if reply else None)
    
    if not user:
        return await event.edit("❌ **Reply to a user or specify their ID to block.**")
    
    try:
        user = int(user)
    except ValueError:
        return await event.edit("❌ **Invalid user ID.**")

    await client(BlockRequest(user))
    approved_users.discard(user)
    save_approved_users()
    await event.edit(f"🚫 **Blocked user:** `{user}`")

# ✅ Unblock a User
@client.on(events.NewMessage(pattern=r"^\.unblock( (.*)|$)", outgoing=True))
async def unblock_user(event):
    global approved_users
    reply = await event.get_reply_message()
    user = event.pattern_match.group(2) or (reply.sender_id if reply else None)
    
    if not user:
        return await event.edit("❌ **Reply to a user or specify their ID to unblock.**")
    
    try:
        user = int(user)
    except ValueError:
        return await event.edit("❌ **Invalid user ID.**")

    await client(UnblockRequest(user))
    approved_users.add(user)
    save_approved_users()
    await event.edit(f"✅ **Unblocked user:** `{user}`")

# 📜 List Approved Users
@client.on(events.NewMessage(pattern=r"^\.listapproved$", outgoing=True))
async def list_approved(event):
    if not approved_users:
        return await event.edit("🚫 **No approved users found.**")
    
    approved_list = "\n".join(f"• `{user}`" for user in approved_users)
    await event.edit(f"✅ **Approved users:**\n{approved_list}")

# 🕒 Function: Get Last Seen
async def get_last_seen(user_id):
    try:
        user = await client(GetFullUserRequest(user_id))
        status = user.user.status
        if isinstance(status, UserStatusOnline):
            return "🟢 Online"
        elif isinstance(status, UserStatusRecently):
            return "🕓 Recently active"
        elif isinstance(status, UserStatusOffline):
            last_seen = status.was_online
            delta = datetime.now() - last_seen
            if delta < timedelta(minutes=1):
                return "🕒 Just now"
            elif delta < timedelta(hours=1):
                return f"⌛ {int(delta.seconds / 60)} min ago"
            elif delta < timedelta(days=1):
                return f"🕘 {int(delta.seconds / 3600)} hours ago"
            else:
                return f"📅 {last_seen.strftime('%d %b, %I:%M %p')}"
        else:
            return "👀 Last seen a while ago"
    except Exception:
        return "⚙️ Unknown"

# 🚨 Monitor Unapproved Messages
@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def monitor_unapproved_messages(event):
    global approved_users
    approved_users = load_approved_users()
    user = event.sender_id
    sender = await event.get_sender()

    # Ignore bots
    if sender.bot:
        return

    # Allow approved users
    if user in approved_users:
        return

    # Don’t send auto-response if owner is online or recently active
    owner_status = await get_last_seen("me")
    if "Online" in owner_status or "Recently" in owner_status:
        return

    # Build last seen info
    last_seen_text = await get_last_seen("me")

    # 💬 Premium Auto-Reply
    premium_message = (
        f"👋 **Hey there!**\n\n"
        f"My owner is currently **{last_seen_text}**.\n"
        f"Your message has been received and will be viewed soon. ⏳\n\n"
        f"Please avoid sending multiple messages — that may lead to a block. 🚫\n\n"
        f"Thank you for understanding! 🙏"
    )

    # Send only once per day
    async for msg in client.iter_messages(user, from_user="me", limit=1):
        if msg.date.date() == datetime.now().date():
            return  # Already responded today

    await event.respond(premium_message)
