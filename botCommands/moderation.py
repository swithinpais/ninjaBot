import discord
from discord.errors import Forbidden
from discord.ext import commands, tasks
from discord.mentions import AllowedMentions
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


    @commandChecks.isModerator()
    @commands.guild_only()
    @commands.command(brief="Bans a member from verifying", usage="[member]", help="Prevents a member from verifying")
    async def tradeban(self, ctx, member:discord.Member=None):
        if member is None:
            await ctx.channel.send("You need to choose a member", delete_after=5)
        await ctx.message.delete()
        role = ctx.message.guild.get_role(data.getTradeBanRole())
        if role is None:
            await ctx.channel.send("This server has not set up a trade ban role yet.", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))

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

    @commandChecks.isModerator()
    @commands.command(brief="Deletes a specified amount of messages", usage="[amount] (user)")
    async def clear(self, ctx, amount=1, member:discord.User=None):
        await ctx.message.delete()
        def check(message):
            message.author == member
        if member is None:
            def check(message):
                return True
        
        messages = await ctx.channel.purge(limit=amount, check=check)
        await ctx.channel.send(f"Deleted {len(messages)} messages", delete_after=5.0)


            
    @commandChecks.isModerator()
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
    

    @commandChecks.isModerator()
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