import discord
from discord.ext import commands
from data import data

class BotVoiceEvents(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        super().__init__()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, bef, aft):
        if aft.channel is None:
            guild = member.guild
            role = guild.get_role(data.getSilentVcRole())
            if role is not None:
                await member.remove_roles(role, reason="Left VC")

        elif bef.channel is None:
            guild = member.guild
            role = guild.get_role(data.getSilentVcRole())
            if role is not None:
                await member.add_roles(role, reason="Joined VC")