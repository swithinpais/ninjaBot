import discord
from discord.errors import Forbidden
from discord.ext import commands, tasks
import interactor
from data import data
from typing import Callable, List, Optional
import datetime as dt
from . import commandChecks
from filters import Filters


import random

class Fun(commands.Cog, name="Fun"):
    def __init__(self, bot, loadedCogs, allCogs):
        self.bot = bot
        self.allCogs = allCogs
        self.loadedCogs = loadedCogs
        self.Filters = Filters(bot)

        allCogs.add(self.qualified_name)
        loadedCogs.append(self.qualified_name)

    def cog_unload(self):
        self.loadedCogs.pop(self.loadedCogs.index(self.qualified_name))
        return super().cog_unload()  

    @commands.cooldown(1, 30, type=commands.BucketType(4))
    @commandChecks.isBotCmdChannel()
    @commands.guild_only()
    @commands.command(brief="Marks you as afk", usage="(reason) {30}", help="Use this command to mark you ask afk and supply the reason to whoever mentions you")
    async def afk(self, ctx, *, reason="None"):
        if len(reason) > 200:
            message = await ctx.channel.send("The reason must be at most 200 characters!")
            await message.delete(delay=10)
            return

        passed = await self.Filters.swearFilter(ctx.message, checkAll=True)


        if not passed:
            return
        
        interactor.add_data(data.afkConn, "afk", user_id=int(ctx.author.id), reason=reason)
        embed = discord.Embed(title="", color=0x3498eb)
        embed.set_author(name="Marked as afk")
        embed.add_field(name="Reason", value=f"{reason}")
        await ctx.channel.send(embed=embed, reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))


    @commands.cooldown(1, 0.5, type=commands.BucketType(4))
    @commandChecks.isBotCmdChannel()
    @commands.guild_only()
    @commands.command(brief="Rolls a dice", usage="(floor) (ceiling) {10}", aliases=["roll"], help="Rolls a dice with the amount of sides you choose or with 6 sides if left blank.")
    async def dice(self, ctx, floor=None, ceil=None):
        switch = False
        if floor is None:
            floor = 1
        if ceil is None:
            ceil = 6
            switch = True
        try:
            floor = int(str(floor).replace(",",""))
        except ValueError:
            await ctx.channel.send("The floor has to be a whole number", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
            return
        try:
            ceil = int(str(ceil).replace(",",""))
        except ValueError:
            await ctx.channel.send("The ceiling has to be a whole number", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
            return

        if switch:
            ceil, floor = floor, 1

        if ceil <= floor:
            await ctx.channel.send("The ceiling has to be greater than the floor!", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
            return

        if ceil >= 1_000_000_000:
            await ctx.channel.send(f"<@{ctx.author.id}> No dice is that big.", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
            return
        
        chosen = random.randint(floor, ceil)
        await ctx.channel.send(f"<@{ctx.author.id}> You rolled a {chosen} when rolling between {floor} and {ceil}", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))

    @commands.cooldown(1, 0.5, type=commands.BucketType(4))
    @commandChecks.isBotCmdChannel()
    @commands.guild_only()
    @commands.command(brief="Flips a coin", usage="{10}", aliases=["cf"], help="Flips a coin and give heads or tails")
    async def coinflip(self, ctx):
        choices = ["Heads", "Tails"]
        message = f"It landed on {random.choice(choices)}."
        await ctx.channel.send(message, reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))

    @commands.cooldown(1, 5, type=commands.BucketType(4))
    @commandChecks.isBotCmdChannel()
    @commands.guild_only()
    @commands.command(brief="A ping command!", usage="{15}", help="Use this command to find the ping ")
    async def ping(self, ctx):
        sentAt = ctx.message.created_at.timestamp()
        timeNow = dt.datetime.utcnow().timestamp()
        cmdLatency = round(timeNow - sentAt, 6) * 1000
        clientLatency = round(self.bot.latency, 6) * 1000
        embed = discord.Embed(title="Pong!", color=0x6beb34)
        embed.add_field(name="Command Latency", value=f"{round(cmdLatency, 2)} ms", inline=False)
        embed.add_field(name="Client Latency", value=f"{round(clientLatency, 2)} ms")
        await ctx.channel.send(embed=embed, reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))