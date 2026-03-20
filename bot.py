import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime

# ─────────────────────────────────────────────
#  CONFIG  –  edit these before running
# ─────────────────────────────────────────────
BOT_TOKEN  = os.environ.get("BOT_TOKEN")
GUILD_ID   = None       # Set to your server ID (int) for instant slash-command sync
DATA_FILE  = "data.json"
ACCENT     = 0x00BFFF  # Embed accent colour (DeepSkyBlue)
# ─────────────────────────────────────────────

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot  = commands.Bot(command_prefix="!", intents=intents)
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


def sorted_leaderboard(data: dict):
    return sorted(
        data["users"].items(),
        key=lambda x: x[1]["tryouts"],
        reverse=True
    )


def medal(pos: int) -> str:
    medals = ["🥇", "🥈", "🥉"]
    return medals[pos] if pos < 3 else f"`#{pos + 1}`"


def find_by_name(data: dict, name: str):
    name_lower = name.strip().lower()
    for key, entry in data["users"].items():
        if entry["name"].lower() == name_lower:
            return key, entry
    return None, None


# ══════════════════════════════════════════════
#  AUTOCOMPLETE
# ══════════════════════════════════════════════

async def name_autocomplete(interaction: discord.Interaction, current: str):
    data  = load_data()
    names = [entry["name"] for entry in data["users"].values()]
    return [
        app_commands.Choice(name=n, value=n)
        for n in names if current.lower() in n.lower()
    ][:25]


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

# ── /adduser  (Discord member) ────────────────
@tree.command(name="adduser", description="Add a Discord member to the FTP panel")
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

    data["users"][uid] = {
        "name":     member.display_name,
        "tag":      str(member),
        "type":     "discord",
        "tryouts":  0,
        "notes":    "",
        "added_at": datetime.utcnow().isoformat()
    }
    save_data(data)

    embed = discord.Embed(
        title="✅  User Added",
        description=f"**{member.mention}** has been added to the FTP Admin Panel.",
        color=0x00FF88,
        timestamp=datetime.utcnow()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Username", value=str(member), inline=True)
    embed.add_field(name="Tryouts",  value="0",         inline=True)
    embed.set_footer(text=f"Added by {interaction.user}")
    await interaction.response.send_message(embed=embed)


# ── /addname  (custom name, no Discord needed) ─
@tree.command(name="addname", description="Add a custom name to the FTP panel (no Discord account needed)")
@app_commands.describe(name="The name to add to the panel")
@app_commands.checks.has_permissions(manage_guild=True)
async def addname(interaction: discord.Interaction, name: str):
    data = load_data()
    name = name.strip()

    existing_key, _ = find_by_name(data, name)
    if existing_key:
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"⚠️  **{name}** is already in the panel.",
                color=0xFFAA00
            ), ephemeral=True
        )
        return

    key = f"custom_{name.lower().replace(' ', '_')}_{int(datetime.utcnow().timestamp())}"
    data["users"][key] = {
        "name":     name,
        "tag":      name,
        "type":     "custom",
        "tryouts":  0,
        "notes":    "",
        "added_at": datetime.utcnow().isoformat()
    }
    save_data(data)

    embed = discord.Embed(
        title="✅  Name Added",
        description=f"**{name}** has been added to the FTP Admin Panel.",
        color=0x00FF88,
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="Name",    value=name, inline=True)
    embed.add_field(name="Tryouts", value="0",  inline=True)
    embed.set_footer(text=f"Added by {interaction.user}")
    await interaction.response.send_message(embed=embed)


# ── /removeuser  (Discord member) ─────────────
@tree.command(name="removeuser", description="Remove a Discord member from the FTP panel")
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


# ── /removename  (any name, autocomplete) ──────
@tree.command(name="removename", description="Remove a name from the FTP panel")
@app_commands.describe(name="Name to remove (start typing to search)")
@app_commands.autocomplete(name=name_autocomplete)
@app_commands.checks.has_permissions(manage_guild=True)
async def removename(interaction: discord.Interaction, name: str):
    data = load_data()
    key, entry = find_by_name(data, name)
    if not key:
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"❌  **{name}** is not in the panel.",
                color=0xFF4444
            ), ephemeral=True
        )
        return
    del data["users"][key]
    save_data(data)

    embed = discord.Embed(
        title="🗑️  Name Removed",
        description=f"**{name}** has been removed from the FTP Admin Panel.",
        color=0xFF4444,
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text=f"Removed by {interaction.user}")
    await interaction.response.send_message(embed=embed)


# ── /addtryout  (by name, autocomplete) ────────
@tree.command(name="addtryout", description="Add tryout(s) to anyone on the panel")
@app_commands.describe(
    name="Name of the person (start typing to search)",
    amount="Number of tryouts to add (default 1)"
)
@app_commands.autocomplete(name=name_autocomplete)
@app_commands.checks.has_permissions(manage_guild=True)
async def addtryout(interaction: discord.Interaction, name: str, amount: int = 1):
    if amount < 1:
        await interaction.response.send_message(
            embed=discord.Embed(description="❌  Amount must be at least 1.", color=0xFF4444),
            ephemeral=True
        )
        return

    data = load_data()
    key, entry = find_by_name(data, name)
    if not key:
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"❌  **{name}** is not in the panel. Add them first with `/addname` or `/adduser`.",
                color=0xFF4444
            ), ephemeral=True
        )
        return

    entry["tryouts"] += amount
    save_data(data)

    embed = discord.Embed(
        title="📋  Tryout Logged",
        color=ACCENT,
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="Member",        value=entry["name"],         inline=True)
    embed.add_field(name="Added",         value=f"+{amount}",          inline=True)
    embed.add_field(name="Total Tryouts", value=str(entry["tryouts"]), inline=True)
    embed.set_footer(text=f"Logged by {interaction.user}")
    await interaction.response.send_message(embed=embed)


# ── /removetryout  (by name, autocomplete) ─────
@tree.command(name="removetryout", description="Remove tryout(s) from anyone on the panel")
@app_commands.describe(
    name="Name of the person (start typing to search)",
    amount="Number of tryouts to remove (default 1)"
)
@app_commands.autocomplete(name=name_autocomplete)
@app_commands.checks.has_permissions(manage_guild=True)
async def removetryout(interaction: discord.Interaction, name: str, amount: int = 1):
    data = load_data()
    key, entry = find_by_name(data, name)
    if not key:
        await interaction.response.send_message(
            embed=discord.Embed(description=f"❌  **{name}** is not in the panel.", color=0xFF4444),
            ephemeral=True
        )
        return

    entry["tryouts"] = max(0, entry["tryouts"] - amount)
    save_data(data)

    embed = discord.Embed(
        title="📋  Tryout Deducted",
        color=0xFF8C00,
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="Member",        value=entry["name"],         inline=True)
    embed.add_field(name="Removed",       value=f"-{amount}",          inline=True)
    embed.add_field(name="Total Tryouts", value=str(entry["tryouts"]), inline=True)
    embed.set_footer(text=f"Updated by {interaction.user}")
    await interaction.response.send_message(embed=embed)


# ── /setnote  (by name, autocomplete) ──────────
@tree.command(name="setnote", description="Add a note to a panel member's profile")
@app_commands.describe(name="Name of the person", note="The note to save")
@app_commands.autocomplete(name=name_autocomplete)
@app_commands.checks.has_permissions(manage_guild=True)
async def setnote(interaction: discord.Interaction, name: str, note: str):
    data = load_data()
    key, entry = find_by_name(data, name)
    if not key:
        await interaction.response.send_message(
            embed=discord.Embed(description=f"❌  **{name}** is not in the panel.", color=0xFF4444),
            ephemeral=True
        )
        return
    entry["notes"] = note
    save_data(data)
    embed = discord.Embed(
        description=f"📝  Note saved for **{entry['name']}**.",
        color=ACCENT
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ── /userinfo  (by name, autocomplete) ─────────
@tree.command(name="userinfo", description="View a panel member's profile")
@app_commands.describe(name="Name of the person (start typing to search)")
@app_commands.autocomplete(name=name_autocomplete)
async def userinfo(interaction: discord.Interaction, name: str):
    data = load_data()
    key, entry = find_by_name(data, name)
    if not key:
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"❌  **{name}** is not in the panel.",
                color=0xFF4444
            ), ephemeral=True
        )
        return

    board = sorted_leaderboard(data)
    rank  = next((i for i, (k, _) in enumerate(board) if k == key), 0) + 1

    embed = discord.Embed(
        title=f"👤  {entry['name']}",
        color=ACCENT,
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="Tryouts Hosted", value=str(entry["tryouts"]), inline=True)
    embed.add_field(name="Panel Rank",     value=f"#{rank}",            inline=True)
    embed.add_field(name="Type",           value=entry.get("type", "discord").title(), inline=True)
    embed.add_field(name="Added",          value=entry["added_at"][:10], inline=True)
    if entry.get("notes"):
        embed.add_field(name="📝 Notes", value=entry["notes"], inline=False)
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

    max_t = board[0][1]["tryouts"] if board[0][1]["tryouts"] > 0 else 1
    lines = []
    for pos, (key, entry) in enumerate(board[:25]):
        m      = medal(pos)
        filled = round((entry["tryouts"] / max_t) * 10)
        bar    = "█" * filled + "░" * (10 - filled)
        lines.append(
            f"{m} **{entry['name']}**\n"
            f"┗ `{bar}` **{entry['tryouts']}** tryouts"
        )

    embed = discord.Embed(
        title="🏆  FTP Tryout Leaderboard",
        description="Ranked by total tryouts hosted\n\n" + "\n\n".join(lines),
        color=ACCENT,
        timestamp=datetime.utcnow()
    )
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
    embed.add_field(name="👥 Total Members", value=str(len(data["users"])), inline=True)
    embed.add_field(name="📋 Total Tryouts", value=str(total),              inline=True)
    embed.add_field(name="🏆 Top Host",
        value=board[0][1]["name"] if board else "—", inline=True)

    if board:
        rows = [
            f"`{pos+1:>2}.` **{entry['name']}** — {entry['tryouts']} tryouts"
            for pos, (_, entry) in enumerate(board[:10])
        ]
        embed.add_field(name="📊 Top 10 Leaderboard", value="\n".join(rows), inline=False)

    embed.set_footer(text="Use /leaderboard for the full ranked list")
    await interaction.response.send_message(embed=embed)


# ── /resetuser  (by name, autocomplete) ────────
@tree.command(name="resetuser", description="Reset a panel member's tryout count to 0")
@app_commands.describe(name="Name of the person (start typing to search)")
@app_commands.autocomplete(name=name_autocomplete)
@app_commands.checks.has_permissions(administrator=True)
async def resetuser(interaction: discord.Interaction, name: str):
    data = load_data()
    key, entry = find_by_name(data, name)
    if not key:
        await interaction.response.send_message(
            embed=discord.Embed(description=f"❌  **{name}** is not in the panel.", color=0xFF4444),
            ephemeral=True
        )
        return
    entry["tryouts"] = 0
    save_data(data)
    embed = discord.Embed(
        description=f"🔄  **{entry['name']}**'s tryouts have been reset to 0.",
        color=0xFF8C00
    )
    await interaction.response.send_message(embed=embed)


# ── /listmembers ──────────────────────────────
@tree.command(name="listmembers", description="List all members currently in the panel")
@app_commands.checks.has_permissions(manage_guild=True)
async def listmembers(interaction: discord.Interaction):
    data = load_data()
    if not data["users"]:
        await interaction.response.send_message(
            embed=discord.Embed(description="📭  No members in the panel yet.", color=ACCENT),
            ephemeral=True
        )
        return

    lines = []
    for entry in data["users"].values():
        tag  = "🔵" if entry.get("type") == "discord" else "⚪"
        lines.append(f"{tag} **{entry['name']}** — {entry['tryouts']} tryouts")

    embed = discord.Embed(
        title=f"👥  Panel Members ({len(data['users'])})",
        description="\n".join(lines[:30]),
        color=ACCENT,
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text="🔵 Discord member  •  ⚪ Custom name")
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
