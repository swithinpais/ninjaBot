import discord
from discord.errors import Forbidden
from discord.ext import commands, tasks
import interactor
from data import data
from typing import Callable, List, Optional
import datetime as dt
from . import commandChecks

import asyncio

class Miscellaneous(commands.Cog, name="Miscellaneous"):
    def __init__(self, bot, loadedCogs, allCogs):
        self.bot = bot
        self.allCogs = allCogs
        self.loadedCogs = loadedCogs

        allCogs.add(self.qualified_name)
        loadedCogs.append(self.qualified_name)

    def cog_unload(self):
        self.loadedCogs.pop(self.loadedCogs.index(self.qualified_name))
        return super().cog_unload()  
    
    @commands.cooldown(1, 0.5, type=commands.BucketType(4)) 
    @commandChecks.isBotCmdChannel()
    @commands.command(brief="Brings up this command", usage="(command)", help="Use this command to get detailed info on any command or general info if left blank.")
    async def help(self, ctx, cmd=None):  # sourcery no-metrics
        embed = discord.Embed(title="Help Command", color=0x34a4eb)
        embed.add_field(name="Key", value="() - Optional\n[] - Required\n{} - Cooldown", inline=False)
        prfx = await self.bot.get_prefix(ctx)

        if cmd is None:
            counter = 0
            cog = self.bot.get_cog(self.loadedCogs[counter])
            cogCommands = cog.get_commands()
            embed.add_field(name=f"Category:", value=f"{self.loadedCogs[counter]}")
            for c in cogCommands:
                if c.hidden:
                    continue
                embed.add_field(name=f"{prfx}{c.name} {c.usage}", value=c.brief, inline=False)
            helpMessage = await ctx.channel.send(embed=embed, reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))

            reactions = ["⏮️","◀️","▶️","⏭️"]
            for reaction in reactions:
                await helpMessage.add_reaction(reaction)

            def check(reaction, user):
                return user == ctx.message.author and (reaction.emoji in reactions)

            while True:
                embed = discord.Embed(title="Help Command", color=0x34a4eb)
                embed.add_field(name="Key", value="() - Optional\n[] - Required\n{} - Cooldown", inline=False)
                try:
                    reaction, user = await self.bot.wait_for("reaction_add", check=check, timeout=30.0)
                except asyncio.TimeoutError:
                    for reaction in reactions:
                        try:
                            await helpMessage.clear_reaction(reaction)
                        except discord.NotFound:
                            pass
                    return
                if reaction.emoji  == "⏮️":
                    try:
                        await helpMessage.remove_reaction("⏮️", ctx.message.author)
                    except discord.NotFound:
                        pass
                    counter = 0
                elif reaction.emoji == "◀️":
                    try:
                        await helpMessage.remove_reaction("◀️", ctx.message.author)
                    except discord.NotFound:
                        pass
                    counter -= 1
                elif reaction.emoji == "▶️":
                    try:
                        await helpMessage.remove_reaction("▶️", ctx.message.author)
                    except discord.NotFound:
                        pass
                    counter += 1
                elif reaction.emoji == "⏭️":
                    try:
                        await helpMessage.remove_reaction("⏭️", ctx.message.author)
                    except discord.NotFound:
                        pass
                    counter = len(self.loadedCogs) - 1

                if counter >= len(self.loadedCogs):
                    counter = len(self.loadedCogs) - 1
                elif counter < 0:
                    counter = 0

                cog = self.bot.get_cog(self.loadedCogs[counter])
                cogCommands = cog.get_commands()
                embed.add_field(name=f"Category:", value=f"{self.loadedCogs[counter]}")
                for c in cogCommands:
                    if c.hidden:
                        continue
                    embed.add_field(name=f"{prfx}{c.name} {c.usage}", value=c.brief, inline=False)
                await helpMessage.edit(content="", embed=embed)


        

        for command in self.bot.commands:
            if cmd == command.name:
                embed = discord.Embed(title=f"", color=0x34a4eb)
                embed.set_author(name="Key: () - Optional | [] - Required")
                embed.add_field(name="Category", value=f"{command.cog_name}")
                embed.add_field(name=f"{prfx}{command.name} {command.usage}", value=f"{command.help}", inline=False)
                if command.aliases != []:
                    als = ""
                    for alias in command.aliases:
                        als += " " + str(alias)
                    embed.add_field(name="Aliases", value=f"{als}")
                await ctx.channel.send(embed=embed, reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
                return

        embed = discord.Embed(title="", color=0x34a4eb)
        embed.set_author(name=f"Error, no command called {cmd} found.")
        
        await ctx.channel.send(embed=embed, reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
        return


    @commands.cooldown(1, 15, type=commands.BucketType(4))
    @commandChecks.isBotCmdChannel()
    @commands.guild_only()
    @commands.command(brief="Sends a request to change you nickname", usage="[nickname] {60}", help="Sends a nickname request to moderators to approve or deny. If approved your nickname changes to what you requested.")
    async def nick(self, ctx, *, nick=""):
        if nick == "":
            message = await ctx.channel.send(f"<@{ctx.author.id}> You need to choose a nick.", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
            await message.delete(delay=20)
            return
        if len(nick) > 32 :
            message = await ctx.channel.send(f"<@{ctx.author.id}> Your nick is too long. Please choose a nick that is 32 characters or fewer.", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
            await message.delete(delay=20)
            return

        embed = discord.Embed(title="", color=0x34a4eb)
        embed.add_field(name="Nick Request Sent", value="Your request was sent, please wait for a moderator to approve.")
        response = await ctx.channel.send(embed=embed, reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))

        embed = discord.Embed(title="Nick Request", color=0x34a4eb)
        embed.add_field(name="User Requesting", value=f"<@{ctx.author.id}>", inline=True)
        embed.add_field(name="Requested Name", value=f"{nick}")
        embed.timestamp = dt.datetime.utcnow()
        embed.set_footer(text=f"User ID: {ctx.author.id}")
        channel = self.bot.get_channel(data.getNickChannel())
        if channel is None:
            await ctx.channel.send("This server has not set up nicks yet.", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
            return
        nickMessage = await channel.send(embed=embed)

        await nickMessage.add_reaction("✅")
        await nickMessage.add_reaction("❌")
        
        def check(reaction, user):
            return (
                user.id != self.bot.user.id
                and str(reaction.emoji) in ["✅", "❌"]
                and reaction.message.author.id == self.bot.user.id
            )

        reaction, user = await self.bot.wait_for("reaction_add", check=check)

        if reaction.emoji == "✅":
            try:
                await ctx.author.edit(reason="Nick Request Change", nick=nick)
            except Exception:
                channel = data.getLoggingChannel()
                embed = discord.Embed(title="Insufficient Permissions", color=0xdb2421)
                embed.add_field(name="Unable to Change Nick for", value=f"{ctx.author.mention}")
                await channel.send(embed=embed)
            else:
                try:
                    await ctx.author.send(f"Your nick has been changed to {nick}")
                except Exception:
                    pass
            await nickMessage.delete()

        if reaction.emoji == "❌":
            await nickMessage.delete()
        
        
        return

    @commands.cooldown(1, 0.5, type=commands.BucketType(4)) 
    @commands.guild_only()
    @commands.command(brief="Reports a user", usage="[member]", help="Sends a report to moderators to review. You can submit a reason as well as evidence for the moderators.")
    async def report(self, ctx, member:discord.Member=None):
        await ctx.message.delete()
        if ctx.message.author == member:
            selfMsg = await ctx.channel.send("You cannot report yourself!")
            await selfMsg.delete(delay=5)
            return
        if member == None:
            noMember = await ctx.channel.send("You need to choose who to report")
            await noMember.delete(delay=5)
            return


        reasonMsg = await ctx.channel.send("Why are you reporting this user?")
        def check(m):
            return m.author == ctx.author
        try:
            reason = await self.bot.wait_for("message", timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await reasonMsg.delete()
            timeOutMsg = await ctx.channel.send("Timed out, report delete.")
            await timeOutMsg.delete(delay=5)
            return
        await reasonMsg.delete()
        await reason.delete()

        if reason.content.lower() == "":
            reason.content = ""
            for attachment in reason.attachments:
                reason.content += attachment.url



        evidenceMsg = await ctx.channel.send("If you have evidence send it now, otherwise type 'No'")
        def check(m):
            return m.author == ctx.author
        try:
            evidence = await self.bot.wait_for("message",timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await evidenceMsg.delete()
            timeOutMsg = await ctx.channel.send("Timed out, report deleted.")
            await timeOutMsg.delete(delay=5)
            return
        await evidenceMsg.delete()
        await evidence.delete()
        if evidence.content.lower() == "no" or evidence.content.lower() == "n":
            evidence.content = "None"

        if evidence.content.lower() == "":
            evidence.content = ""
            for attachment in evidence.attachments:
                evidence.content += attachment.url

        embed = discord.Embed(title="", color=0x34a4eb)
        embed.add_field(name="Report Succesfully Submitted", value="Please wait for a moderator to review it")
        successMsg = await ctx.channel.send(embed=embed)
        await successMsg.delete(delay=10)

        channel = self.bot.get_channel(data.getReportChannel())
        if channel is None:
            await ctx.channel.send("This server has not set up reports yet.", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
        embed = discord.Embed(title="User Report", color=0x34a4eb)
        embed.add_field(name="Reporter", value=f"<@{ctx.author.id}>", inline=True)
        embed.add_field(name="Reporter Nick", value=f"{ctx.author.display_name}")
        embed.add_field(name="Reporter ID", value=f"{ctx.author.id}")
        embed.add_field(name="Reported User", value=f"<@{member.id}>")
        embed.add_field(name="Reported User Nick", value=f"{member.display_name}")
        embed.add_field(name="Reported User ID", value=f"{member.id}")
        embed.add_field(name="Reason For Report", value=f"{reason.content}")
        embed.add_field(name="Evidence For Report", value=f"{evidence.content}")
        embed.add_field(name="Chat Link", value=f"{ctx.message.jump_url}")
        fTime = dt.datetime.utcnow().strftime("%H:%M")
        embed.set_footer(text=f"Reported at {fTime}")
        reportMessage = await channel.send(embed=embed)
        await reportMessage.add_reaction("✅")
        await reportMessage.add_reaction("❌")
        
        def check(reaction, user):
            return (
                user.id != self.bot.user.id
                and str(reaction.emoji) in ["✅", "❌"]
                and reaction.message.author.id == self.bot.user.id
            )
        reaction, user = await self.bot.wait_for("reaction_add", check=check)

        if reaction.emoji == "✅":
            reportingUser = ctx.author
            
            try:
                await reportingUser.send("Thank you for reporting. Your report was reviewed and approved.")
            except:
                pass
            await reportMessage.delete()
        if reaction.emoji == "❌":
            await reportMessage.delete()

    @commandChecks.isBotCmdChannel()
    @commands.guild_only()
    @commands.cooldown(1, 0.5, type=commands.BucketType(4))
    @commands.command(brief="Shows information about the bot", usage="", help="Shows information such as versoin, uptime and latency regarding the bot.")
    async def info(self, ctx):
        embed = discord.Embed(title="Bot Info")
        embed.add_field(name="Version", value=data.version, inline=False)
        timeTaken = dt.datetime.now() - data.startTime
        totalSeconds = timeTaken.seconds
        hours, remainder = divmod(totalSeconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        embed.add_field(name="Uptime", value=f"{timeTaken.days} days {hours}:{minutes}:{seconds}.{timeTaken.microseconds/1_000_000:.2f}", inline=False)
        embed.add_field(name="Bot Latency", value=f"{self.bot.latency*1000:.2f} ms", inline=False)
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.timestamp = dt.datetime.now()
        await ctx.channel.send(embed=embed, reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))