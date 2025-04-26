import discord
from discord.ext import commands, tasks
import json
import csv
import os
from datetime import datetime

# --- INTENTS -----------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

# --- BOT ---------------------------------------------------------
bot = commands.Bot(command_prefix="-", intents=intents)

DATA_FILE = "kontrakty.json"
PREMIA = 15000  # Stała premia dla TZM i MET

# --- POMOCNICY ---------------------------------------------------
def wczytaj_kontrakty():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def zapisz_kontrakty(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# --- INICJALIZACJA -----------------------------------------------
kontrakty = wczytaj_kontrakty()

# --- CODZIENNE PODSUMOWANIE --------------------------------------
@tasks.loop(time=datetime.strptime("00:00", "%H:%M").time())
async def daily_summary():
    channel = discord.utils.get(bot.get_all_channels(), name="zrobione-kontrakty")
    if not channel:
        return
    embed = discord.Embed(title="📊 Codzienne podsumowanie", color=discord.Color.blue())
    for uid, d in kontrakty.items():
        member = channel.guild.get_member(int(uid))
        if member:
            embed.add_field(
                name=member.display_name,
                value=f"TZM: {d.get('TZM',0)}  MET: {d.get('MET',0)}  💰 {d.get('kasa',0)}$",
                inline=False
            )
    await channel.send(embed=embed)

@bot.event
async def on_ready():
    print(f'Zalogowano jako {bot.user}')
    daily_summary.start()

# --- KOMENDY -----------------------------------------------------
@bot.command()
async def tzm(ctx):
    """Rejestruje kontrakt TZM."""
    uid = str(ctx.author.id)
    kontrakty.setdefault(uid, {"TZM": 0, "MET": 0, "kasa": 0})
    kontrakty[uid]["TZM"] += 1
    kontrakty[uid]["kasa"] += PREMIA
    zapisz_kontrakty(kontrakty)
    await ctx.send(f"{ctx.author.mention}, premia za TZM: **{PREMIA}**$")

@bot.command()
async def met(ctx):
    """Rejestruje kontrakt MET."""
    uid = str(ctx.author.id)
    kontrakty.setdefault(uid, {"TZM": 0, "MET": 0, "kasa": 0})
    kontrakty[uid]["MET"] += 1
    kontrakty[uid]["kasa"] += PREMIA
    zapisz_kontrakty(kontrakty)
    await ctx.send(f"{ctx.author.mention}, premia za MET: **{PREMIA}**$")

@bot.command()
async def podsumowanie(ctx):
    """Wyświetla podsumowanie wszystkich kontraktów."""
    if not kontrakty:
        return await ctx.send("Brak zapisanych kontraktów.")
    embed = discord.Embed(title="📊 Podsumowanie", color=discord.Color.green())
    for uid, d in kontrakty.items():
        member = ctx.guild.get_member(int(uid))
        if member:
            embed.add_field(
                name=member.display_name,
                value=f"TZM: {d.get('TZM',0)}  MET: {d.get('MET',0)}  💰 {d.get('kasa',0)}$",
                inline=False
            )
    await ctx.send(embed=embed)

@bot.command()
async def ranking(ctx):
    """Top 5 wykonawców według premii."""
    top = sorted(kontrakty.items(), key=lambda x: x[1].get("kasa", 0), reverse=True)[:5]
    lines = []
    for i, (uid, d) in enumerate(top, 1):
        member = ctx.guild.get_member(int(uid))
        name = member.display_name if member else uid
        lines.append(f"{i}. {name} – {d.get('kasa',0)}$")
    await ctx.send("🏆 Ranking:\n" + "\n".join(lines))

@bot.command()
async def eksport(ctx):
    """Eksportuje dane do CSV."""
    with open("kontrakty.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["UserID", "Name", "TZM", "MET", "Total"])
        for uid, d in kontrakty.items():
            member = ctx.guild.get_member(int(uid))
            name = member.name if member else uid
            w.writerow([uid, name, d.get("TZM", 0), d.get("MET", 0), d.get("kasa", 0)])
    await ctx.send("✅ Wyeksportowano do `kontrakty.csv`")

@bot.command()
async def moje(ctx):
    """Pokazuje Twoje statystyki."""
    uid = str(ctx.author.id)
    d = kontrakty.get(uid)
    if not d:
        return await ctx.send(f"{ctx.author.mention}, nie masz jeszcze kontraktów.")
    await ctx.send(
        f"{ctx.author.mention} – TZM: {d['TZM']} | MET: {d['MET']} | 💰 {d['kasa']}$"
    )

@bot.command()
@commands.has_permissions(administrator=True)
async def reset(ctx):
    """(Admin) Resetuje wszystkie dane."""
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
    kontrakty.clear()
    zapisz_kontrakty(kontrakty)
    await ctx.send("🔄 Dane zostały zresetowane.")

# --- REAKCJE -----------------------------------------------------
@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return
    member = guild.get_member(payload.user_id)
    if not member:
        return

    emoji = payload.emoji.name
    if emoji == '🟢':
        kontrakt_typ = 'TZM'
    elif emoji == '🔴':
        kontrakt_typ = 'MET'
    else:
        return

    uid = str(member.id)
    kontrakty.setdefault(uid, {"TZM": 0, "MET": 0, "kasa": 0})
    kontrakty[uid][kontrakt_typ] += 1
    kontrakty[uid]["kasa"] += PREMIA
    zapisz_kontrakty(kontrakty)

    await member.send(f"{member.mention}, Twoja premia za kontrakt {kontrakt_typ} to **{PREMIA}**$")

# --- RUN ---------------------------------------------------------
TOKEN = os.getenv("TOKEN")
bot.run(TOKEN)
