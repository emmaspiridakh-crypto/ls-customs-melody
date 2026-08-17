import time
import logging
import discord
from discord import app_commands
from discord.ext import commands

import config
from utils import database as db

log = logging.getLogger("duty")


def format_duration(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}ω {m}λ {s}δ"
    if m:
        return f"{m}λ {s}δ"
    return f"{s}δ"


class DutyPanelView(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

        container = discord.ui.Container(accent_colour=discord.Colour.green())

        section = discord.ui.Section(
            discord.ui.TextDisplay(
                "## 🕒 Duty System\n"
                f"{config.EMOJI_DUTY_ON} **ON** — μπαίνεις σε υπηρεσία, ξεκινά μέτρηση χρόνου\n"
                f"{config.EMOJI_DUTY_OFF} **OFF** — βγαίνεις από υπηρεσία, σταματά η μέτρηση\n"
                f"{config.EMOJI_LIST} **On Duty Now** — ποιοι είναι σε υπηρεσία αυτή τη στιγμή\n"
                f"{config.EMOJI_LEADERBOARD} **Leaderboard** — συνολικός χρόνος ανά άτομο"
            ),
            accessory=discord.ui.Thumbnail(media=config.DUTY_PANEL_THUMBNAIL),
        )
        container.add_item(section)

        row1 = discord.ui.ActionRow()
        row1.add_item(
            discord.ui.Button(label="ON", style=discord.ButtonStyle.green, emoji=config.EMOJI_DUTY_ON, custom_id="duty_on")
        )
        row1.add_item(
            discord.ui.Button(label="OFF", style=discord.ButtonStyle.red, emoji=config.EMOJI_DUTY_OFF, custom_id="duty_off")
        )
        container.add_item(row1)

        row2 = discord.ui.ActionRow()
        row2.add_item(
            discord.ui.Button(label="On Duty Now", style=discord.ButtonStyle.grey, emoji=config.EMOJI_LIST, custom_id="duty_list")
        )
        row2.add_item(
            discord.ui.Button(label="Leaderboard", style=discord.ButtonStyle.blurple, emoji=config.EMOJI_LEADERBOARD, custom_id="duty_leaderboard")
        )
        container.add_item(row2)

        self.add_item(container)


class Duty(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="dutypanel", description="Στέλνει το duty panel σε αυτό το κανάλι.")
    @app_commands.checks.has_permissions(administrator=True)
    async def dutypanel(self, interaction: discord.Interaction):
        await interaction.channel.send(view=DutyPanelView())
        await interaction.response.send_message("✅ Το duty panel στάλθηκε.", ephemeral=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        custom_id = interaction.data.get("custom_id", "")

        if custom_id == "duty_on":
            await self._duty_on(interaction)
        elif custom_id == "duty_off":
            await self._duty_off(interaction)
        elif custom_id == "duty_list":
            await self._duty_list(interaction)
        elif custom_id == "duty_leaderboard":
            await self._leaderboard(interaction)

    async def _duty_on(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user

        if await db.is_on_duty(member.id, guild.id):
            await interaction.response.send_message("⚠️ Είσαι ήδη σε υπηρεσία.", ephemeral=True)
            return

        role = guild.get_role(config.ON_DUTY_ROLE_ID)
        if role:
            await member.add_roles(role, reason="Duty ON")

        await db.start_duty(member.id, guild.id)
        await interaction.response.send_message(f"{config.EMOJI_DUTY_ON} Μπήκες σε υπηρεσία!", ephemeral=True)

    async def _duty_off(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user

        if not await db.is_on_duty(member.id, guild.id):
            await interaction.response.send_message("⚠️ Δεν είσαι σε υπηρεσία.", ephemeral=True)
            return

        role = guild.get_role(config.ON_DUTY_ROLE_ID)
        if role:
            await member.remove_roles(role, reason="Duty OFF")

        duration = await db.end_duty(member.id, guild.id)
        await interaction.response.send_message(
            f"{config.EMOJI_DUTY_OFF} Βγήκες από υπηρεσία. Διάρκεια: **{format_duration(duration)}**",
            ephemeral=True,
        )

    async def _duty_list(self, interaction: discord.Interaction):
        active = await db.get_active_duty_users(interaction.guild.id)
        if not active:
            await interaction.response.send_message("📋 Κανείς δεν είναι σε υπηρεσία αυτή τη στιγμή.", ephemeral=True)
            return

        now = int(time.time())
        lines = []
        for user_id, start_time in active:
            member = interaction.guild.get_member(user_id)
            name = member.mention if member else f"`{user_id}`"
            lines.append(f"• {name} — {format_duration(now - start_time)}")

        embed = discord.Embed(
            title=f"{config.EMOJI_LIST} On Duty Now",
            description="\n".join(lines),
            color=config.COLOR_VOICE,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _leaderboard(self, interaction: discord.Interaction):
        top = await db.get_leaderboard(interaction.guild.id, limit=10)
        if not top:
            await interaction.response.send_message("📊 Δεν υπάρχουν ακόμα δεδομένα.", ephemeral=True)
            return

        lines = []
        for i, (user_id, total_seconds) in enumerate(top, start=1):
            member = interaction.guild.get_member(user_id)
            name = member.mention if member else f"`{user_id}`"
            lines.append(f"**{i}.** {name} — {format_duration(total_seconds)}")

        embed = discord.Embed(
            title=f"{config.EMOJI_LEADERBOARD} Duty Leaderboard",
            description="\n".join(lines),
            color=config.COLOR_ROLE,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Duty(bot))
