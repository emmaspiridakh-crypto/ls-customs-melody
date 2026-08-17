from __future__ import annotations

import discord
from discord import ui
from discord.ext import commands

import config
from emojis import emoji


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel = member.guild.get_channel(config.WELCOME_CHANNEL_ID)
        if channel is None:
            return

        member_count = member.guild.member_count

        container = ui.Container(accent_colour=discord.Colour.blue())

        if config.WELCOME_BANNER_URL:
            container.add_item(ui.MediaGallery(discord.MediaGalleryItem(media=config.WELCOME_BANNER_URL)))

        avatar_url = member.display_avatar.url

        section = ui.Section(
            accessory=ui.Thumbnail(media=avatar_url)
        )
        section.add_item(ui.TextDisplay(
            f"## {emoji('welcome', 'welcome') or '👋'} Καλώς ήρθες, {member.mention}!\n"
            f"Χαιρόμαστε που είσαι μαζί μας στο **{member.guild.name}**.\n\n"
            f"{emoji('welcome', 'members') or '👥'} **Μέλη server:** {member_count}"
        ))
        container.add_item(section)

        view = ui.LayoutView(timeout=None)
        view.add_item(container)

        try:
            await channel.send(view=view, allowed_mentions=discord.AllowedMentions(users=True))
        except discord.HTTPException:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
