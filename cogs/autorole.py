import discord
from discord.ext import commands

import config


class AutoRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        role = member.guild.get_role(config.AUTOROLE_ID)
        if role:
            try:
                await member.add_roles(role, reason="Autorole - νέο μέλος")
            except discord.Forbidden:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoRole(bot))
