from discord.ext import commands
import discord
from data import data
import datetime as dt

class Startup(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        super().__init__()
    
    @commands.Cog.listener()
    async def on_connect(self):
        data.setStartTime(dt.datetime.now())
        print("Connecting to Discord...")
        
    @commands.Cog.listener()
    async def on_ready(self):
        print("Bot ready")
        print(f"Logged in as {self.bot.user}")
        print(f"Watching {len(self.bot.guilds)} server(s)")
        print("-------------------------------------------------")
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="The ThirtyVirus BotNet", large_image_url="https://media.discordapp.net/attachments/836634458114883585/840995791367438336/thirtyPFP.gif"))
