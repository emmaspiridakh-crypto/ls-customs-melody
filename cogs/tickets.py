import asyncio
import logging
import discord
from discord import app_commands
from discord.ext import commands

import config
from utils import database as db

log = logging.getLogger("tickets")

TICKET_TYPES = {
    "support": {
        "label": "Support",
        "role_id": config.STAFF_ROLE_ID,
        "emoji": config.EMOJI_SUPPORT,
        "prefix": "support",
    },
    "contact": {
        "label": "Επικοινωνία Διοίκησης",
        "role_id": config.ANOTATH_DIOIKISI_ROLE_ID,
        "emoji": config.EMOJI_CONTACT,
        "prefix": "dioikisi",
    },
}

class TicketPanelView(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

        container = discord.ui.Container(accent_colour=discord.Colour.blurple())
        gallery = discord.ui.MediaGallery()
        gallery.add_item(media=config.TICKET_PANEL_BANNER)
        container.add_item(gallery)

        section = discord.ui.Section(
            discord.ui.TextDisplay(
                "# Ticket Panel\n"
                "Πάτησε το κατάλληλο κουμπί ανάλογα με το λόγο επικοινωνίας σου.\n\n"
                f"{config.EMOJI_SUPPORT} **Support** — για γενικά θέματα/βοήθεια\n"
                f"{config.EMOJI_CONTACT} **Επικοινωνία Διοίκησης** — για σοβαρά θέματα"
            ),
            accessory=discord.ui.Thumbnail(media=config.TICKET_PANEL_THUMBNAIL),
        )
        container.add_item(section)

        row = discord.ui.ActionRow()
        row.add_item(
            discord.ui.Button(
                label="Support",
                style=discord.ButtonStyle.green,
                emoji=config.EMOJI_SUPPORT,
                custom_id="ticket_open:support",
            )
        )
        row.add_item(
            discord.ui.Button(
                label="Επικοινωνία Διοίκησης",
                style=discord.ButtonStyle.blurple,
                emoji=config.EMOJI_CONTACT,
                custom_id="ticket_open:contact",
            )
        )
        container.add_item(row)

        self.add_item(container)

class TicketControlView(discord.ui.LayoutView):
    def __init__(self, mention_text: str | None = None):
        super().__init__(timeout=None)

        container = discord.ui.Container(accent_colour=discord.Colour.blurple())

        header = f"{config.EMOJI_TICKET} **Ticket Controls**"
        if mention_text:
            header = f"{mention_text}\n\n{header}"

        container.add_item(discord.ui.TextDisplay(header))

        row = discord.ui.ActionRow()
        row.add_item(
            discord.ui.Button(
                label="Close Ticket",
                style=discord.ButtonStyle.red,
                emoji=config.EMOJI_CLOSE,
                custom_id="ticket_close",
            )
        )
        row.add_item(
            discord.ui.Button(
                label="Ping User",
                style=discord.ButtonStyle.grey,
                emoji=config.EMOJI_PING,
                custom_id="ticket_ping_user",
            )
        )
        container.add_item(row)

        self.add_item(container)


class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ticketpanel", description="Στέλνει το ticket panel σε αυτό το κανάλι.")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticketpanel(self, interaction: discord.Interaction):
        await interaction.channel.send(view=TicketPanelView())
        await interaction.response.send_message("✅ Το ticket panel στάλθηκε.", ephemeral=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        custom_id = interaction.data.get("custom_id", "")

        if custom_id.startswith("ticket_open:"):
            ticket_type = custom_id.split(":", 1)[1]
            await self._open_ticket(interaction, ticket_type)
        elif custom_id == "ticket_close":
            await self._close_ticket(interaction)
        elif custom_id == "ticket_ping_user":
            await self._ping_user(interaction)

    async def _open_ticket(self, interaction: discord.Interaction, ticket_type: str):
        info = TICKET_TYPES.get(ticket_type)
        if not info:
            return

        guild = interaction.guild
        category = guild.get_channel(config.TICKET_CATEGORY_ID)
        role = guild.get_role(info["role_id"])

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        if role:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        channel = await guild.create_text_channel(
            name=f"{info['prefix']}-{interaction.user.name}",
            category=category,
            overwrites=overwrites,
        )

        await db.create_ticket(channel.id, guild.id, interaction.user.id, ticket_type)

        mention_text = f"{interaction.user.mention}" + (f" | {role.mention}" if role else "")
        await channel.send(view=TicketControlView(mention_text=mention_text))

        await interaction.response.send_message(f"✅ Άνοιξε το ticket σου: {channel.mention}", ephemeral=True)

        self.bot.dispatch("ticket_open", interaction, channel, info["label"])

    async def _close_ticket(self, interaction: discord.Interaction):
        ticket = await db.get_ticket(interaction.channel.id)
        if not ticket or ticket["status"] == "closed":
            await interaction.response.send_message("❌ Αυτό το κανάλι δεν είναι ενεργό ticket.", ephemeral=True)
            return

        await db.close_ticket(interaction.channel.id)
        await interaction.response.send_message("🔒 Το ticket κλείνει σε 5 δευτερόλεπτα...")

        self.bot.dispatch("ticket_close", interaction, ticket)

        await asyncio.sleep(5)
        await interaction.channel.delete()

    async def _ping_user(self, interaction: discord.Interaction):
        ticket = await db.get_ticket(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("❌ Αυτό το κανάλι δεν είναι ticket.", ephemeral=True)
            return

        user = interaction.guild.get_member(ticket["user_id"])
        await interaction.response.send_message(
            f"🔔 {user.mention if user else '`χρήστης δεν βρέθηκε`'}, σε χρειαζόμαστε σε αυτό το ticket!"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
