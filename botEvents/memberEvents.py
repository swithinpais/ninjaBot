import discord
from discord.ext import commands
import asyncio

from filters import Filters
import interactor
from data import data

class BotMemberEvents(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.Filters = Filters(bot)
        super().__init__()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        asyncio.create_task(self.Filters.nameCheck(member))

        rows = interactor.read_data(data.tradeBanConn, "*", "tradeBanned")
        if member.id in rows:
            role = member.guild.get_role(data.getTradeBanRole())
            await member.add_roles(role, reason="Trade Banned")
    
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        asyncio.create_task(self.Filters.nameCheck(after))