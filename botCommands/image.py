import discord
from discord.errors import Forbidden
from discord.ext import commands, tasks
import interactor
import data
from typing import Callable, List, Optional
import datetime as dt
from . import commandChecks

import os

class Image(commands.Cog, name="Image"):
    def __init__(self, bot, loadedCogs, allCogs):
        self.bot = bot
        self.allCogs = allCogs
        self.loadedCogs = loadedCogs

        allCogs.add(self.qualified_name)
        loadedCogs.append(self.qualified_name)

    def cog_unload(self):
        self.loadedCogs.pop(self.loadedCogs.index(self.qualified_name))
        return super().cog_unload()

    @commands.cooldown(1, 10, type=commands.BucketType(4)) 
    @commandChecks.isBotCmdChannel()  
    @commands.guild_only()
    @commands.command(brief="Gets the avatar of the user", usage="(id)/(mention) {30}", aliases=["av"], help="Use this command to get the avatar of a user. Leave blank to get your own avatar.")
    async def avatar(self, ctx, user:discord.User=None):
        if user is None:
            user = ctx.author
        embed = discord.Embed(title=f"Avatar of {user}", color=0x34a4eb)
        embed.set_footer(text=f"Requested by {ctx.author}")
        embed.set_image(url=str(user.avatar_url))
        await ctx.channel.send(embed=embed, reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))

    @commands.cooldown(1, 10, type=commands.BucketType(4))
    @commandChecks.isBotCmdChannel()
    @commands.guild_only()
    @commands.command(brief="Enlarges an emote", usage="[emote] {30}", help="Use this command to scale up a custom emote")
    async def enlarge(self, ctx, emoji:discord.PartialEmoji=None):

        if emoji is None:
            await ctx.channel.send("You need to choose an emoji to enlarge!", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
            return
        
        suffix = ".png"
        if emoji.animated:
            suffix = ".gif"
        await emoji.url.save(f"{ctx.author.name}ReqEmoji{suffix}")
        await ctx.channel.send(file=discord.File(f"{ctx.author.name}ReqEmoji{suffix}", filename=f"{emoji.name}{suffix}"), reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
        os.remove(f"{ctx.author.name}ReqEmoji{suffix}")