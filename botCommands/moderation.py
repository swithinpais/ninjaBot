import discord
from discord.errors import Forbidden
from discord.ext import commands, tasks
import interactor
from data import data
from typing import Callable, List, Optional
import datetime as dt
from . import commandChecks

class Moderation(commands.Cog, name="Moderation"):
    def __init__(self, bot, loadedCogs, allCogs):
        self.bot = bot
        self.allCogs = allCogs
        self.loadedCogs = loadedCogs

        allCogs.add(self.qualified_name)
        loadedCogs.append(self.qualified_name)

    def cog_unload(self):
        self.loadedCogs.pop(self.loadedCogs.index(self.qualified_name))
        return super().cog_unload()


    @commands.has_role(data.getModRole())
    @commands.guild_only()
    @commands.command(brief="Bans a member from verifying", usage="[member]", help="Prevents a member from verifying")
    async def tradeban(self, ctx, member:discord.Member=None):
        if member is None:
            await ctx.channel.send("You need to choose a member", delete_after=5)
        await ctx.message.delete()
        role = ctx.message.guild.get_role(data.getTradeBanRole())

        rows = interactor.read_data(data.tradeBanConn, "*", "tradeBanned")
        if member.id in rows:
            try:
                member.remove_roles(role, reason="Untrade banned")
            except Forbidden:
                await ctx.channel.send("I do not have the permissions to remove roles from that user!", delete_after=20)
                return
            interactor.delete_data(data.tradeBanConn, "tradeBanned", "user_id", member.id)
            await ctx.channel.send(f"Member ``{member}`` has been untrade banned", delete_after=5)
            return

        
        try:
            await member.add_roles(role, reason="Trade banned")
        except Forbidden:
            await ctx.channel.send("I do not have the permissions to add roles to that user!", delete_after=20)
            return
        interactor.add_data(data.tradeBanConn, "tradeBanned", user_id=member.id)
        await ctx.channel.send(f"Member ``{member}`` has been trade banned.", delete_after=5)


    
    async def purgeFunc(self, channel:discord.TextChannel, limit, check:Callable) -> List[discord.Message]:
        messages = await channel.purge(limit=limit, check=check, bulk=True)
        return messages

    async def clearFunc(self, ctx, limit, check):
        messages = await self.purgeFunc(ctx.channel, limit=limit, check=check)
        
        channel = self.bot.get_channel(data.getLoggingChannel())
        embed = discord.Embed(title=f"{len(messages)} deleted")
        embed.add_field(name=f" ", value=f"{len(messages)} purged in {ctx.channel}")
        embed.set_author(name=f"{ctx.author}", url=ctx.author.avatar_url)
        embed.timestamp = dt.datetime.now()
        await channel.send(embed=embed)

        await ctx.channel.send(f"Deleted {len(messages)} messages")

    #@commands.has_role(modRole)
    #@commands.command(brief="Deletes a")
    async def clear(self, ctx, member=None, limit=None): # work in progress
        
        await ctx.message.delete()

        if limit is None and member is None:
            await ctx.channel.send("You must provide arguments")
            return

        if limit is None:
            limit = 2000
            member = member.replace("<@","").replace("!","").replace(">","")
            try:
                member = int(member)
            except ValueError:
                await ctx.channel.send("Invalid mention or id passed")
                return
            
            member = ctx.guild.get_member(member)
            def check(message):
                return message.author == member
            task = await self.clearFunc(ctx, limit, check)
            
        

    @commands.has_role(data.getModRole())
    @commands.command(brief="Clears a user's message from all channels the bot can see", help="Effective to running clear command in every channel with the given amount.", usage="[member] (amount)")
    async def massclear(self, ctx, member:discord.User=None, limit=1):
        channels:List = ctx.guild.channels
        channel = self.bot.get_channel(data.getLoggingChannel())
        await ctx.message.delete()

        if member is None:
            await ctx.channel.send("A member must be specified")
            return

        loadingMsg = await ctx.channel.send("Deleting messages <a:loading:860077892611080200>")
        delMessages = 0
        totalChannels = 0
        for channel in channels:
            if not(isinstance(channel, discord.TextChannel)):
                continue
            totalChannels += 1
            messages = []
            async for message in channel.history():
                messages.append(message)
                if message.author == member:
                    await message.delete()
                    delMessages += 1
                    break
            
        await loadingMsg.edit(content=f"Deleted {delMessages} message(s) across {totalChannels} channels", delete_after=15)
    

    @commands.has_role(data.getModRole())
    @commands.guild_only()
    @commands.command(brief="Locks a channel", usage="", help="Locks a channel and prevents members from sending messages in the channel.", enabled=False)
    async def lockchannel(self, ctx):
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        if overwrite.send_messages == False:
            embed = discord.Embed(title="", color=0x34a4eb)
            embed.add_field(name="Channel Unlocked", value=f"This channel has been unlocked by {ctx.author.mention}")
            embed.timestamp = dt.datetime.now()
            await ctx.channel.send(embed=embed)

            await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=None)
            

        elif overwrite.send_messages is None:
            embed = discord.Embed(title="", color=0x34a4eb)
            embed.add_field(name="Channel Locked", value=f"This channel has been locked by {ctx.author.mention}")
            embed.timestamp = dt.datetime.now()
            await ctx.channel.send(embed=embed)

            await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)