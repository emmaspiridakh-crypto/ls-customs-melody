import os
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv

from keep_alive import keep_alive
from utils import database as db
from cogs.tickets import TicketPanelView, TicketControlView
from cogs.duty import DutyPanelView

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("main")

TOKEN = os.environ.get("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

EXTENSIONS = [
    "cogs.tickets",
    "cogs.duty",
    "cogs.autorole",
    "cogs.logging_cog",
    "cogs.say",
]

@bot.event
async def setup_hook():
    await db.init_db()

    for ext in EXTENSIONS:
        try:
            await bot.load_extension(ext)
            log.info(f"Loaded extension: {ext}")
        except Exception as e:
            log.error(f"Failed to load {ext}: {e}")

    bot.add_view(TicketPanelView())
    bot.add_view(TicketControlView())
    bot.add_view(DutyPanelView())

    try:
        synced = await bot.tree.sync()
        log.info(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        log.error(f"Sync error: {e}")


@bot.event
async def on_ready():
    log.info(f"Συνδέθηκε ως {bot.user} ({bot.user.id})")


if __name__ == "__main__":
    keep_alive() 
    if not TOKEN:
        raise RuntimeError("Λείπει το DISCORD_TOKEN από τα environment variables.")
    bot.run(TOKEN)
