import logging
import discord
from discord.ext import commands, tasks

import config

log = logging.getLogger("say")


def is_admin(ctx: commands.Context) -> bool:
    """True αν ο χρήστης έχει το ADMIN_ROLE_ID ή δικαίωμα administrator."""
    if ctx.author.guild_permissions.administrator:
        return True
    admin_role = ctx.guild.get_role(config.ADMIN_ROLE_ID) if ctx.guild else None
    return admin_role is not None and admin_role in ctx.author.roles


class Say(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.status_index = 0
        self.status_loop.start()

    def cog_unload(self):
        self.status_loop.cancel()

    # ---------- !say ----------

    @commands.command(name="say")
    @commands.check(is_admin)
    async def say(self, ctx: commands.Context, *, message: str):
        """Στέλνει μήνυμα σαν να μιλάει το bot. Μόνο για διοίκηση."""
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        except discord.NotFound:
            pass

        await ctx.send(message)

    @say.error
    async def say_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CheckFailure):
            await ctx.send("❌ Δεν έχεις δικαίωμα να χρησιμοποιήσεις αυτή την εντολή.", delete_after=5)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("⚠️ Χρήση: `!say <μήνυμα>`", delete_after=5)
        else:
            log.error(f"Σφάλμα στο !say: {error}")

    # ---------- Live status ----------

    @tasks.loop(seconds=30)
    async def status_loop(self):
        guild = self.bot.get_guild(config.GUILD_ID)
        if guild is None:
            return

        role1 = guild.get_role(config.STATUS_ROLE_ID_1)
        role2 = guild.get_role(config.STATUS_ROLE_ID_2)

        count1 = len(role1.members) if role1 else 0
        count2 = len(role2.members) if role2 else 0

        if self.status_index == 0:
            name1 = role1.name if role1 else "Role 1"
            text = f"{name1}: {count1} άτομα"
        else:
            name2 = role2.name if role2 else "Role 2"
            text = f"{name2}: {count2} άτομα"

        self.status_index = 1 - self.status_index

        try:
            await self.bot.change_presence(
                activity=discord.CustomActivity(name=text)
            )
        except Exception as e:
            log.error(f"Σφάλμα στο status_loop: {e}")

    @status_loop.before_loop
    async def before_status_loop(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Say(bot))
