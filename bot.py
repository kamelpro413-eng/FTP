import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime

# ─────────────────────────────────────────────
#  CONFIG  –  edit these before running
# ─────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GUILD_ID    = None          # Set to your server ID (int) for instant slash-command sync
DATA_FILE   = "data.json"
ACCENT      = 0x00BFFF     # Embed accent colour (DeepSkyBlue)
# ─────────────────────────────────────────────

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


# ══════════════════════════════════════════════
#  DATA HELPERS
# ══════════════════════════════════════════════

def load_data() -> dict:
    if not os.path.exists(DATA_FILE):
        return {"users": {}}
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data: dict):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_user_entry(data: dict, user: discord.Member) -> dict:
    uid = str(user.id)
    if uid not in data["users"]:
        data["users"][uid] = {
            "name":     user.display_name,
            "tag":      str(user),
            "tryouts":  0,
            "notes":    "",
            "added_at": datetime.utcnow().isoformat()
        }
    else:
        # Keep display name fresh
        data["users"][uid]["name"] = user.display_name
        data["users"][uid]["tag"]  = str(user)
    return data["users"][uid]


def sorted_leaderboard(data: dict):
    """Returns list of (uid, entry) sorted by tryouts desc."""
    return sorted(
        data["users"].items(),
        key=lambda x: x[1]["tryouts"],
        reverse=True
    )


def medal(pos: int) -> str:
    return ["🥇", "🥈", "🥉"].get(pos, f"`#{pos + 1}`") if pos < 3 else f"`#{pos + 1}`"


# ══════════════════════════════════════════════
#  BOT EVENTS
# ══════════════════════════════════════════════

@bot.event
async def on_ready():
    print(f"✅  Logged in as {bot.user} ({bot.user.id})")
    if GUILD_ID:
        guild = discord.Object(id=GUILD_ID)
        tree.copy_global_to(guild=guild)
        await tree.sync(guild=guild)
        print(f"⚡  Slash commands synced to guild {GUILD_ID}")
    else:
        await tree.sync()
        print("⚡  Slash commands synced globally (may take up to 1 hour)")


# ══════════════════════════════════════════════
#  SLASH COMMANDS
# ══════════════════════════════════════════════

# ── /adduser ──────────────────────────────────
@tree.command(name="adduser", description="Add a member to the FTP panel")
@app_commands.describe(member="The Discord member to add")
@app_commands.checks.has_permissions(manage_guild=True)
async def adduser(interaction: discord.Interaction, member: discord.Member):
    data = load_data()
    uid  = str(member.id)
    if uid in data["users"]:
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"⚠️  **{member.display_name}** is already in the panel.",
                color=0xFFAA00
            ), ephemeral=True
        )
        return
    get_user_entry(data, member)       # creates the entry
    save_data(data)

    embed = discord.Embed(
        title="✅  User Added",
        description=f"**{member.mention}** has been added to the FTP Admin Panel.",
        color=0x00FF88,
        timestamp=datetime.utcnow()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Username", value=str(member), inline=True)
    embed.add_field(name="Tryouts",  value="0",          inline=True)
    embed.set_footer(text=f"Added by {interaction.user}")
    await interaction.response.send_message(embed=embed)


# ── /removeuser ───────────────────────────────
@tree.command(name="removeuser", description="Remove a member from the FTP panel")
@app_commands.describe(member="The Discord member to remove")
@app_commands.checks.has_permissions(manage_guild=True)
async def removeuser(interaction: discord.Interaction, member: discord.Member):
    data = load_data()
    uid  = str(member.id)
    if uid not in data["users"]:
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"❌  **{member.display_name}** is not in the panel.",
                color=0xFF4444
            ), ephemeral=True
        )
        return
    del data["users"][uid]
    save_data(data)

    embed = discord.Embed(
        title="🗑️  User Removed",
        description=f"**{member.display_name}** has been removed from the FTP Admin Panel.",
        color=0xFF4444,
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text=f"Removed by {interaction.user}")
    await interaction.response.send_message(embed=embed)


# ── /addtryout ────────────────────────────────
@tree.command(name="addtryout", description="Add tryout(s) for a panel member")
@app_commands.describe(
    member="The member who hosted the tryout(s)",
    amount="Number of tryouts to add (default 1)"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def addtryout(interaction: discord.Interaction, member: discord.Member, amount: int = 1):
    if amount < 1:
        await interaction.response.send_message(
            embed=discord.Embed(description="❌  Amount must be at least 1.", color=0xFF4444),
            ephemeral=True
        )
        return

    data  = load_data()
    entry = get_user_entry(data, member)
    entry["tryouts"] += amount
    save_data(data)

    embed = discord.Embed(
        title="📋  Tryout Logged",
        color=ACCENT,
        timestamp=datetime.utcnow()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Member",        value=member.mention,          inline=True)
    embed.add_field(name="Added",         value=f"+{amount}",            inline=True)
    embed.add_field(name="Total Tryouts", value=str(entry["tryouts"]),   inline=True)
    embed.set_footer(text=f"Logged by {interaction.user}")
    await interaction.response.send_message(embed=embed)


# ── /removetryout ─────────────────────────────
@tree.command(name="removetryout", description="Remove tryout(s) from a panel member")
@app_commands.describe(
    member="The member to deduct from",
    amount="Number of tryouts to remove (default 1)"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def removetryout(interaction: discord.Interaction, member: discord.Member, amount: int = 1):
    data  = load_data()
    uid   = str(member.id)
    if uid not in data["users"]:
        await interaction.response.send_message(
            embed=discord.Embed(description="❌  Member not found in panel.", color=0xFF4444),
            ephemeral=True
        )
        return
    entry = data["users"][uid]
    entry["tryouts"] = max(0, entry["tryouts"] - amount)
    save_data(data)

    embed = discord.Embed(
        title="📋  Tryout Deducted",
        color=0xFF8C00,
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="Member",        value=member.mention,        inline=True)
    embed.add_field(name="Removed",       value=f"-{amount}",          inline=True)
    embed.add_field(name="Total Tryouts", value=str(entry["tryouts"]), inline=True)
    embed.set_footer(text=f"Updated by {interaction.user}")
    await interaction.response.send_message(embed=embed)


# ── /setnote ──────────────────────────────────
@tree.command(name="setnote", description="Add a note to a panel member's profile")
@app_commands.describe(member="Target member", note="The note to save")
@app_commands.checks.has_permissions(manage_guild=True)
async def setnote(interaction: discord.Interaction, member: discord.Member, note: str):
    data  = load_data()
    entry = get_user_entry(data, member)
    entry["notes"] = note
    save_data(data)
    embed = discord.Embed(
        description=f"📝  Note saved for **{member.display_name}**.",
        color=ACCENT
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ── /userinfo ─────────────────────────────────
@tree.command(name="userinfo", description="View a panel member's profile")
@app_commands.describe(member="The member to look up")
async def userinfo(interaction: discord.Interaction, member: discord.Member):
    data = load_data()
    uid  = str(member.id)
    if uid not in data["users"]:
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"❌  **{member.display_name}** is not in the panel.",
                color=0xFF4444
            ), ephemeral=True
        )
        return

    entry = data["users"][uid]

    # Rank on leaderboard
    board = sorted_leaderboard(data)
    rank  = next((i for i, (u, _) in enumerate(board) if u == uid), 0) + 1

    embed = discord.Embed(
        title=f"👤  {entry['name']}",
        color=ACCENT,
        timestamp=datetime.utcnow()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Discord Tag",   value=entry["tag"],                 inline=True)
    embed.add_field(name="Tryouts Hosted",value=str(entry["tryouts"]),        inline=True)
    embed.add_field(name="Panel Rank",    value=f"#{rank}",                   inline=True)
    embed.add_field(name="Added",         value=entry["added_at"][:10],       inline=True)
    if entry.get("notes"):
        embed.add_field(name="📝 Notes",  value=entry["notes"],               inline=False)
    embed.set_footer(text="FTP Admin Panel")
    await interaction.response.send_message(embed=embed)


# ── /leaderboard ──────────────────────────────
@tree.command(name="leaderboard", description="Show the FTP tryout leaderboard")
async def leaderboard(interaction: discord.Interaction):
    data  = load_data()
    board = sorted_leaderboard(data)

    if not board:
        await interaction.response.send_message(
            embed=discord.Embed(description="📭  No members in the panel yet.", color=ACCENT),
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🏆  FTP Tryout Leaderboard",
        description="Ranked by total tryouts hosted",
        color=ACCENT,
        timestamp=datetime.utcnow()
    )

    lines = []
    for pos, (uid, entry) in enumerate(board[:25]):   # Discord field limit
        m_medal = medal(pos)
        bar_len = 10
        max_t   = board[0][1]["tryouts"] if board[0][1]["tryouts"] > 0 else 1
        filled  = round((entry["tryouts"] / max_t) * bar_len)
        bar     = "█" * filled + "░" * (bar_len - filled)
        lines.append(
            f"{m_medal} **{entry['name']}**\n"
            f"┗ `{bar}` **{entry['tryouts']}** tryouts"
        )

    embed.description += "\n\n" + "\n\n".join(lines)
    embed.set_footer(text=f"FTP Admin Panel  •  {len(data['users'])} total members")
    await interaction.response.send_message(embed=embed)


# ── /panel ────────────────────────────────────
@tree.command(name="panel", description="Show the full FTP Admin Panel overview")
@app_commands.checks.has_permissions(manage_guild=True)
async def panel(interaction: discord.Interaction):
    data  = load_data()
    board = sorted_leaderboard(data)
    total = sum(e["tryouts"] for _, e in board)

    embed = discord.Embed(
        title="⚙️  FTP Admin Panel  —  Dashboard",
        color=ACCENT,
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="👥 Total Members",  value=str(len(data["users"])), inline=True)
    embed.add_field(name="📋 Total Tryouts",  value=str(total),              inline=True)
    embed.add_field(name="🏆 Top Host",
        value=board[0][1]["name"] if board else "—", inline=True)

    if board:
        rows = []
        for pos, (uid, entry) in enumerate(board[:10]):
            rows.append(f"`{pos+1:>2}.` **{entry['name']}** — {entry['tryouts']} tryouts")
        embed.add_field(
            name="📊 Top 10 Leaderboard",
            value="\n".join(rows),
            inline=False
        )

    embed.set_footer(text="Use /leaderboard for the full ranked list")
    await interaction.response.send_message(embed=embed)


# ── /resetuser ────────────────────────────────
@tree.command(name="resetuser", description="Reset a member's tryout count to 0")
@app_commands.describe(member="The member to reset")
@app_commands.checks.has_permissions(administrator=True)
async def resetuser(interaction: discord.Interaction, member: discord.Member):
    data = load_data()
    uid  = str(member.id)
    if uid not in data["users"]:
        await interaction.response.send_message(
            embed=discord.Embed(description="❌  Member not in panel.", color=0xFF4444),
            ephemeral=True
        )
        return
    data["users"][uid]["tryouts"] = 0
    save_data(data)
    embed = discord.Embed(
        description=f"🔄  **{member.display_name}**'s tryouts reset to 0.",
        color=0xFF8C00
    )
    await interaction.response.send_message(embed=embed)


# ── Error handler ─────────────────────────────
@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            embed=discord.Embed(
                description="🚫  You don't have permission to use this command.",
                color=0xFF4444
            ), ephemeral=True
        )
    else:
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"⚠️  An error occurred: `{error}`",
                color=0xFF4444
            ), ephemeral=True
        )
        raise error


# ══════════════════════════════════════════════
#  RUN
# ══════════════════════════════════════════════
bot.run(BOT_TOKEN)
