# VERSION 1.0.11
"""
This is the source code for Ninja Bot.
You are free to use it if you like.
Please dont make fun of me .-.
For legal reasons, I am not responsible for any bots that use this code or their actions.
"""


from functools import cache
from typing import Callable, List, Optional
import cachetools
import discord
from discord.errors import Forbidden
from discord.ext import commands, tasks
import datetime as dt
import time
from discord.ext.commands.core import check
from fuzzywuzzy import fuzz
import asyncio
import os
import random
import interactor
import json
from cache import AsyncTTL
import traceback
import aiohttp
import re

intents = discord.Intents(guilds = True, members = True, bans = True, emojis = True, integrations = True, webhooks = True, invites = True, voice_states = True, presences = True, guild_messages = True, dm_messages = False, guild_reactions = True, dm_reactions = False, guild_typing = False, dm_typing = False)

client = commands.Bot(command_prefix = "?", owner_id=300669365563424770, intents=intents, max_messages=5000)
client.remove_command("help")

version = "1.0.11"

with open("devConfig.json", "r") as f:

    data = json.load(f)

    TOKEN = data["TOKEN"]
    HYPIXEL_API_KEY = data["HYPIXEL_API_KEY"]
    allowedChannels = data["allowedChannels"]
    linkFilter = data["linkFilter"]
    blacklist0 = data["blacklist0"]
    blacklist1 = data["blacklist1"]
    names = data["names"]
    logging_channel = data["logging_channel"]
    ignoredCategories = data["ignoredCategories"]
    nickChannel = data["nickChannel"]
    reportChannel = data["reportChannel"]
    mutedRole = data["mutedRole"]
    tradeBanRole = data["tradeBanRole"]
    guild_id = data["guild_id"]
    silentVcRole = data["silentVcRole"]
    verifiedRole = data["verifiedRole"]
    modRole = data["modRole"]
    owner = data["owner"]
    confidenceThreshold = data["confidenceThreshold"]
    botCmdChannels = data["botCmdChannels"]
    sbBotCmdChannels = data["sbBotCmdChannels"]
    allowedWords = data["allowedWords"]
    hyRequestsMade = 0

allCogs = set({})
loadedCogs = []

@client.event
async def on_connect():
    global startTime
    startTime = dt.datetime.now()
    print("Connecting to Discord...")
    


@client.event
async def on_ready():
    print("Bot ready")
    print(f"Logged in as {client.user}")
    print(f"Watching {len(client.guilds)} server(s)")
    print("-------------------------------------------------")
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="The ThirtyVirus BotNet", large_image_url="https://media.discordapp.net/attachments/836634458114883585/840995791367438336/thirtyPFP.gif"))
    



def isBotCmdChannel():
    async def predicate(ctx):
        return ctx.channel.id in botCmdChannels
    return commands.check(predicate)

def isSbBotCmdChannel():
    async def predicate(ctx):
        return ctx.channel.id in sbBotCmdChannels
    return commands.check(predicate)

def getLoggingChannel(guildId):
    return client.get_channel(logging_channel)

def errorLogger(error):
    errorMessage = str(traceback.format_exc())
    with open("errorLog.txt", "a") as f:
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{'*'*10}Logged on {now}{'*'*10}\n{errorMessage}\n")
    return errorMessage

def human_format(num):
    num = float('{:.3g}'.format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T'][magnitude])
    

@client.command(hidden=True)
async def dev(ctx):
    
    
    isOwner = await client.is_owner(ctx.author)
    if isOwner:
        await ctx.channel.send("aaron this command works now shut up")
        await ctx.channel.send(ctx.message.content)
        return
    raise commands.CommandNotFound

@client.command(hidden=True)
async def errorlog(ctx):
    isOwner = await client.is_owner(ctx.author)
    if isOwner:
        await ctx.author.send("Error Log", file=discord.File("errorLog.txt"))
        return

def rateLimited():
    global hyRequestsMade
    hyRequestsMade += 1
    return hyRequestsMade > 100

class Moderation(commands.Cog, name="Moderation"):
    def __init__(self, bot):
        self.bot = bot
        allCogs.add(self.qualified_name)
        loadedCogs.append(self.qualified_name)

    def cog_unload(self):
        loadedCogs.pop(loadedCogs.index(self.qualified_name))
        return super().cog_unload()


    @commands.has_role(modRole)
    @commands.guild_only()
    @commands.command(brief="Bans a member from verifying", usage="[member]", help="Prevents a member from verifying")
    async def tradeban(self, ctx, member:discord.Member=None):
        if member is None:
            await ctx.channel.send("You need to choose a member", delete_after=5)
        await ctx.message.delete()
        role = ctx.message.guild.get_role(tradeBanRole)

        rows = interactor.read_data(tradeBanConn, "*", "tradeBanned")
        if member.id in rows:
            try:
                member.remove_roles(role, reason="Untrade banned")
            except Forbidden:
                await ctx.channel.send("I do not have the permissions to remove roles from that user!", delete_after=20)
                return
            interactor.delete_data(tradeBanConn, "tradeBanned", "user_id", member.id)
            await ctx.channel.send(f"Member ``{member}`` has been untrade banned", delete_after=5)
            return

        
        try:
            await member.add_roles(role, reason="Trade banned")
        except Forbidden:
            await ctx.channel.send("I do not have the permissions to add roles to that user!", delete_after=20)
            return
        interactor.add_data(tradeBanConn, "tradeBanned", user_id=member.id)
        await ctx.channel.send(f"Member ``{member}`` has been trade banned.", delete_after=5)


    
    async def purgeFunc(self, channel:discord.TextChannel, limit, check:Callable) -> List[discord.Message]:
        messages = await channel.purge(limit=limit, check=check, bulk=True)
        return messages

    async def clearFunc(self, ctx, limit, check):
        purgeTask = asyncio.create_task(self.purgeFunc(ctx.channel, limit=limit, check=check))
        messages = await purgeTask
        channel = client.get_channel(getLoggingChannel(ctx.guild.id))
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
            task = asyncio.create_task(self.clearFunc(ctx, limit, check))
            
        

    @commands.has_role(modRole)
    @commands.command(brief="Clears a user's message from all channels the bot can see", help="Effective to running clear command in every channel with the given amount.", usage="[member] (amount)")
    async def massclear(self, ctx, member:discord.User=None, limit=1):
        channels:List = ctx.guild.channels
        channel = client.get_channel(getLoggingChannel(ctx.guild.id))
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
            
        await loadingMsg.edit(content=f"Deleted {delMessages} message(s) in {totalChannels} channels", delete_after=15)
    

    @commands.has_role(modRole)
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

class Fun(commands.Cog, name="Fun"):
    def __init__(self, bot):
        self.bot = bot
        allCogs.add(self.qualified_name)
        loadedCogs.append(self.qualified_name)

    def cog_unload(self):
        loadedCogs.pop(loadedCogs.index(self.qualified_name))
        return super().cog_unload()  

    @commands.cooldown(1, 30, type=commands.BucketType(4))
    @isBotCmdChannel()
    @commands.guild_only()
    @commands.command(brief="Marks you as afk", usage="(reason) {30}", help="Use this command to mark you ask afk and supply the reason to whoever mentions you")
    async def afk(self, ctx, *, reason="None"):
        if len(reason) > 200:
            message = await ctx.channel.send("The reason must be at most 200 characters!")
            await message.delete(delay=10)
            return

        task = asyncio.create_task(filter(ctx.message, checkAll=True))
        passed = await task


        if not passed:
            return
        
        interactor.add_data(afkConn, "afk", user_id=int(ctx.author.id), reason=reason)
        embed = discord.Embed(title="", color=0x3498eb)
        embed.set_author(name="Marked as afk")
        embed.add_field(name="Reason", value=f"{reason}")
        await ctx.channel.send(embed=embed, reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))


    @commands.cooldown(1, 0.5, type=commands.BucketType(4))
    @isBotCmdChannel()
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
    @isBotCmdChannel()
    @commands.guild_only()
    @commands.command(brief="Flips a coin", usage="{10}", aliases=["cf"], help="Flips a coin and give heads or tails")
    async def coinflip(self, ctx):
        choices = ["Heads", "Tails"]
        message = f"It landed on {random.choice(choices)}."
        await ctx.channel.send(message, reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))

    @commands.cooldown(1, 5, type=commands.BucketType(4))
    @isBotCmdChannel()
    @commands.guild_only()
    @commands.command(brief="A ping command!", usage="{15}", help="Use this command to find the ping ")
    async def ping(self, ctx):
        sentAt = ctx.message.created_at.timestamp()
        timeNow = dt.datetime.utcnow().timestamp()
        cmdLatency = round(timeNow - sentAt, 6) * 1000
        clientLatency = round(client.latency, 6) * 1000
        embed = discord.Embed(title="Pong!", color=0x6beb34)
        embed.add_field(name="Command Latency", value=f"{round(cmdLatency, 2)} ms", inline=False)
        embed.add_field(name="Client Latency", value=f"{round(clientLatency, 2)} ms")
        await ctx.channel.send(embed=embed, reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))

class Image(commands.Cog, name="Image"):
    def __init__(self, bot):
        self.bot = bot
        allCogs.add(self.qualified_name)
        loadedCogs.append(self.qualified_name)

    def cog_unload(self):
        loadedCogs.pop(loadedCogs.index(self.qualified_name))
        return super().cog_unload()

    @commands.cooldown(1, 10, type=commands.BucketType(4)) 
    @isBotCmdChannel()  
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
    @isBotCmdChannel()
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

class Miscellaneous(commands.Cog, name="Miscellaneous"):
    def __init__(self, bot):
        self.bot = bot
        allCogs.add(self.qualified_name)
        loadedCogs.append(self.qualified_name)

    def cog_unload(self):
        loadedCogs.pop(loadedCogs.index(self.qualified_name))
        return super().cog_unload()  
    
    @commands.cooldown(1, 0.5, type=commands.BucketType(4)) 
    @isBotCmdChannel()
    @commands.command(brief="Brings up this command", usage="(command)", help="Use this command to get detailed info on any command or general info if left blank.")
    async def help(self, ctx, cmd=None):  # sourcery no-metrics
        embed = discord.Embed(title="Help Command", color=0x34a4eb)
        embed.add_field(name="Key", value="() - Optional\n[] - Required\n{} - Cooldown", inline=False)
        prfx = await client.get_prefix(ctx)

        if cmd is None:
            counter = 0
            cog = client.get_cog(loadedCogs[counter])
            cogCommands = cog.get_commands()
            embed.add_field(name=f"Category:", value=f"{loadedCogs[counter]}")
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
                    reaction, user = await client.wait_for("reaction_add", check=check, timeout=30.0)
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
                    counter = len(loadedCogs) - 1

                if counter >= len(loadedCogs):
                    counter = len(loadedCogs) - 1
                elif counter < 0:
                    counter = 0

                cog = client.get_cog(loadedCogs[counter])
                cogCommands = cog.get_commands()
                embed.add_field(name=f"Category:", value=f"{loadedCogs[counter]}")
                for c in cogCommands:
                    if c.hidden:
                        continue
                    embed.add_field(name=f"{prfx}{c.name} {c.usage}", value=c.brief, inline=False)
                await helpMessage.edit(content="", embed=embed)


        

        for command in client.commands:
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
    @isBotCmdChannel()
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
        channel = client.get_channel(nickChannel)
        nickMessage = await channel.send(embed=embed)

        await nickMessage.add_reaction("✅")
        await nickMessage.add_reaction("❌")
        
        def check(reaction, user):
            return (
                user.id != client.user.id
                and str(reaction.emoji) in ["✅", "❌"]
                and reaction.message.author.id == client.user.id
            )

        reaction, user = await client.wait_for("reaction_add", check=check)

        if reaction.emoji == "✅":
            try:
                await ctx.author.edit(reason="Nick Request Change", nick=nick)
            except Exception:
                channel = getLoggingChannel(ctx.guild.id)
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
            reason = await client.wait_for("message", timeout=60.0, check=check)
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
            evidence = await client.wait_for("message",timeout=60.0, check=check)
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

        channel = client.get_channel(reportChannel)
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
                user.id != client.user.id
                and str(reaction.emoji) in ["✅", "❌"]
                and reaction.message.author.id == client.user.id
            )
        reaction, user = await client.wait_for("reaction_add", check=check)

        if reaction.emoji == "✅":
            reportingUser = ctx.author
            
            try:
                await reportingUser.send("Thank you for reporting. Your report was reviewed and approved.")
            except:
                pass
            await reportMessage.delete()
        if reaction.emoji == "❌":
            await reportMessage.delete()

    @isBotCmdChannel()
    @commands.guild_only()
    @commands.cooldown(1, 0.5, type=commands.BucketType(4))
    @commands.command(brief="Shows information about the bot", usage="", help="Shows information such as versoin, uptime and latency regarding the bot.")
    async def info(self, ctx):
        embed = discord.Embed(title="Bot Info")
        embed.add_field(name="Version", value=version, inline=False)
        timeTaken = dt.datetime.now() - startTime
        totalSeconds = timeTaken.seconds
        hours, remainder = divmod(totalSeconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        embed.add_field(name="Uptime", value=f"{timeTaken.days} days {hours}:{minutes}:{seconds}.{timeTaken.microseconds/1_000_000:.2f}", inline=False)
        embed.add_field(name="Bot Latency", value=f"{client.latency*1000:.2f} ms", inline=False)
        embed.set_thumbnail(url=client.user.avatar_url)
        embed.timestamp = dt.datetime.now()
        await ctx.channel.send(embed=embed, reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))

class Skyblock(commands.Cog, name="Skyblock"):
    def __init__(self, bot):
        self.bot = bot
        allCogs.add(self.qualified_name)
        loadedCogs.append(self.qualified_name)

    def cog_unload(self):
        loadedCogs.pop(loadedCogs.index(self.qualified_name))
        return super().cog_unload()

    @commands.cooldown(1, 0.5, type=commands.BucketType(4)) 
    @commands.guild_only()
    @isSbBotCmdChannel()
    @commands.command(brief="Verifies you", usage="[IGN]", help="Verifies you on the server and gives you the Verified role")
    async def verify(self, ctx, ign=None):
        role = ctx.guild.get_role(verifiedRole)
        if ign is None:
            await ctx.channel.send("You need to provide an ign", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
            return

        for mrole in ctx.author.roles:
            if mrole == role:
                    await ctx.channel.send("You have been verified", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
                    return
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.mojang.com/users/profiles/minecraft/{ign}") as r:
                if r.status == 204:
                    await ctx.channel.send("Could not find a user with that username", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
                    return
                r = (await r.json())
                uuid = r["id"]
        if rateLimited():
            await ctx.channel.send("API rate limit exceeded, please try again soon.")
            return

        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.hypixel.net/player?key={HYPIXEL_API_KEY}&uuid={uuid}") as r:
                rh = (await r.json())
        global hyRequestsMade
        hyRequestsMade += 1
        
        if not(rh["success"]):
            await ctx.channel.send("Invalid UUID on Hypixel lookup", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
            return

        if rh["player"] is None:
            await ctx.channel.send("This player has not played Hypixel before", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
        

        try:
            hyDisc = rh["player"]["socialMedia"]["links"]["DISCORD"]
        except KeyError:
            hyDisc = "None"


        with open("scammers.json","r") as f:
            data = json.load(f)
            for id in data:
                if id == uuid:
                    channel = getLoggingChannel(ctx.guild.id)
                    embed = discord.Embed(title="", color=0xe0d100)
                    embed.add_field(name=f"{ctx.author} Banned", value="Marked as scammer")
                    scamReason = data[id]
                    embed.add_field(name="Scam", value=scamReason)
                    embed.timestamp = dt.datetime.utcnow()
                    embed.set_thumbnail(url=ctx.author.avatar_url)
                    try:
                        await ctx.author.ban(reason="Marked as scammer", delete_message_days=0)
                    except Forbidden:
                        await channel.send(f"I do not have permissions to ban {ctx.author}")
                        return
                    await channel.send(embed=embed)
                    return

        if hyDisc.lower() != str(ctx.author).lower():
            await ctx.channel.send(f"Your link between Discord and Hypixel is incorrect\nHypixel: {hyDisc}\nDiscord: {ctx.author}", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
            return
        else:
            await ctx.author.add_roles(role, reason="Verified")
            await ctx.channel.send("Successfully verified", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))


    @AsyncTTL(time_to_live=300, maxsize=250)
    async def weightApiRequest(self, uuid, profile=None):
        if rateLimited():
            return False, False
        if profile is None:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://127.0.0.1:9281/v1/profiles/{uuid}/weight?key={HYPIXEL_API_KEY}") as r:
                    try:
                        data = (await r.json())["data"]
                    except KeyError:
                        data = (await r.json())
                    code = r.status
        else:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://127.0.0.1:9281/v1/profiles/{uuid}/{profile}?key={HYPIXEL_API_KEY}") as r:
                    try:
                        data = (await r.json())["data"]
                    except KeyError:
                        data = (await r.json())
                    code = r.status

        return data, code


    @commands.cooldown(1, 2, type=commands.BucketType(4)) 
    @commands.guild_only()
    @isSbBotCmdChannel()
    @commands.command(brief="Retrieves the weight data for a user", usage="[user] (profile)", help="Retrieves the weight data for a user and caches it. It updates every 5 minutes.")
    async def weight(self, ctx, user=None, profile=None, aliases=["w"]):
        # sourcery no-metrics
        if user is None:
            await ctx.channel.send("You must specify a user", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
            return
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.mojang.com/users/profiles/minecraft/{user}") as mr:
                if mr.status == 204:
                    await ctx.channel.send("Could not find a user with that username", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
                    return
                mr = await mr.json()
                uuid = mr["id"]


        loadingMessage = await ctx.channel.send("Fetching data <a:loading:860077892611080200>", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
        wTask = asyncio.create_task(self.weightApiRequest(uuid, profile))
        data, code = await wTask
        if data is False:
            await loadingMessage.edit("API rate limit exceeded, please try again soon.")

        if code == 404:
            if data["reason"] == "Failed to find a profile using the given strategy":
                await loadingMessage.edit(content="Invalid profile entered")
                return
            await loadingMessage.edit(content="There is no player with this name or they have never played Skyblock.", allowed_mentions=discord.AllowedMentions(replied_user=False))
            return
        elif code == 500:
            await loadingMessage.edit(content="There was an error in contacting the API, please try again later.", allowed_mentions=discord.AllowedMentions(replied_user=False))
            return
        elif code == 502:
            await loadingMessage.edit(content="The Hypixel API is experiencing some technical difficulties, please try again later.", allowed_mentions=discord.AllowedMentions(replied_user=False))
            return 
        elif code == 503:
            await loadingMessage.edit(content="The Hypixel API is under maintenance, please try again later.", allowed_mentions=discord.AllowedMentions(replied_user=False))
            return
        elif code == 200:
            
            
            if data["skills"]["apiEnabled"]:
                skillText = f"⛏️ Total Skills Weight - {round(data['skills']['weight'] + data['skills']['weight_overflow'], 2)}\n({round(data['skills']['weight'], 2)} + {round(data['skills']['weight_overflow'], 2)} Overflow)\nSkill Average - {round(data['skills']['average_skills'], 2)}"
                skills = data["skills"]
                skillText += f"\n🌾 Farming - {round(skills['farming']['level'], 2)} | Weight - {round(skills['farming']['weight'], 2)} | Overflow - {round(skills['farming']['weight_overflow'], 2)}"
                skillText += f"\n⛏️ Mining - {round(skills['mining']['level'], 2)} | Weight - {round(skills['mining']['weight'], 2)} | Overflow - {round(skills['mining']['weight_overflow'], 2)}"
                skillText += f"\n⚔️ Combat - {round(skills['combat']['level'], 2)} | Weight - {round(skills['combat']['weight'], 2)} | Overflow - {round(skills['combat']['weight_overflow'], 2)}"
                skillText += f"\n🪓 Foraging - {round(skills['foraging']['level'], 2)} | Weight - {round(skills['foraging']['weight'], 2)} | Overflow - {round(skills['foraging']['weight_overflow'], 2)}"
                skillText += f"\n🎣 Fishing - {round(skills['fishing']['level'], 2)} | Weight - {round(skills['fishing']['weight'], 2)} | Overflow - {round(skills['fishing']['weight_overflow'], 2)}"
                skillText += f"\n🔮 Enchanting - {round(skills['enchanting']['level'], 2)} | Weight - {round(skills['enchanting']['weight'], 2)} | Overflow - {round(skills['enchanting']['weight_overflow'], 2)}"
                skillText += f"\n🧪 Alchemy - {round(skills['alchemy']['level'], 2)} | Weight - {round(skills['alchemy']['weight'], 2)} | Overflow - {round(skills['alchemy']['weight_overflow'], 2)}"
                skillText += f"\n🐾 Taming - {round(skills['taming']['level'], 2)} | Weight - {round(skills['taming']['weight'], 2)} | Overflow - {round(skills['taming']['weight_overflow'], 2)}"
            else:
                skillText = "\n**Skills API Disabled**"

            slayer = data["slayers"]
            if slayer is None:
                slayerText = "**Hasnt Done Slayers**"
            else:
                slayerText = f"⚔️ Total Slayer Weight - {round(slayer['weight'] + slayer['weight_overflow'], 2)}\n({round(slayer['weight'], 2)} + {round(slayer['weight_overflow'], 2)} Overflow)"
                bosses = slayer["bosses"]
                slayerText += f"\n🧟 Revenant - {round(bosses['revenant']['level'], 2)} | Experience - {round(bosses['revenant']['experience'], 2)} | Weight - {round(bosses['revenant']['weight'], 2)} | Overflow - {round(bosses['revenant']['weight_overflow'], 2)}"
                slayerText += f"\n🕷️ Tarantula - {round(bosses['tarantula']['level'], 2)} | Experience - {round(bosses['tarantula']['experience'], 2)} | Weight - {round(bosses['tarantula']['weight'], 2)} | Overflow - {round(bosses['tarantula']['weight_overflow'], 2)}"
                slayerText += f"\n🐺 Sven - {round(bosses['sven']['level'], 2)} | Experience - {round(bosses['sven']['experience'], 2)} | Weight - {round(bosses['sven']['weight'], 2)} | Overflow - {round(bosses['sven']['weight_overflow'], 2)}"
                slayerText += f"\n✨ Enderman - {round(bosses['enderman']['level'], 2)} | Experience - {round(bosses['enderman']['experience'], 2)} | Weight - {round(bosses['enderman']['weight'], 2)} | Overflow - {round(bosses['enderman']['weight_overflow'], 2)}"

            cata = data["dungeons"]
            if cata is None:
                cataText = "**Hasnt Done Dungeons**"
            else:
                cataText = f"🏰 Total Catacombs Weight - {round(cata['weight'] + cata['weight_overflow'], 2)}\n({round(cata['weight'], 2)} + {round(cata['weight_overflow'], 2)} Overflow)\n{cata['secrets_found']} Secrets Found\nCatacombs Level {cata['types']['catacombs']['level']:.2f}"
                classes = cata['classes']
                cataText += f"\n🩹 Healer - {round(classes['healer']['level'], 2)} | Weight - {round(classes['healer']['weight'], 2)} | Overflow - {round(classes['healer']['weight_overflow'], 2)}"
                cataText += f"\n🧙 Mage - {round(classes['mage']['level'], 2)} | Weight - {round(classes['mage']['weight'], 2)} | Overflow - {round(classes['mage']['weight_overflow'], 2)}"
                cataText += f"\n⚔️ Berserker - {round(classes['berserker']['level'], 2)} | Weight - {round(classes['berserker']['weight'], 2)} | Overflow - {round(classes['berserker']['weight_overflow'], 2)}"
                cataText += f"\n🏹 Archer - {round(classes['archer']['level'], 2)} | Weight - {round(classes['archer']['weight'], 2)} | Overflow - {round(classes['archer']['weight_overflow'], 2)}"
                cataText += f"\n🛡️ Tank - {round(classes['tank']['level'], 2)} | Weight - {round(classes['tank']['weight'], 2)} | Overflow - {round(classes['tank']['weight_overflow'], 2)}"
            
            def check(reaction, user):
                return user == ctx.message.author and reaction.emoji in ["⛏️", "⚔️", "🏰"]

            embed = discord.Embed(title=f"Showing weight data for {data['username']}\nProfile: {data['name']}", color=0x7ae607)
            embed.add_field(name="Total Weight:", value=round(data["weight"] + data["weight_overflow"], 2))
            embed.add_field(name="Weight", value=round(data["weight"], 2))
            embed.add_field(name="Overflow", value=round(data["weight_overflow"], 2))
            embed.add_field(name="Skills", value=f"```prolog\n{skillText}\n```", inline=False)
            await loadingMessage.edit(content="", embed=embed, allowed_mentions=discord.AllowedMentions(replied_user=False))
            
            await loadingMessage.add_reaction("⛏️")
            await loadingMessage.add_reaction("⚔️")
            await loadingMessage.add_reaction("🏰")

            while True:
                embed = discord.Embed(title=f"Showing weight data for {data['username']}\nProfile: {data['name']}", color=0x7ae607)
                embed.add_field(name="Total Weight:", value=round(data["weight"] + data["weight_overflow"], 2))
                embed.add_field(name="Weight", value=round(data["weight"], 2))
                embed.add_field(name="Overflow", value=round(data["weight_overflow"], 2))
                try:
                    reaction, user = await client.wait_for("reaction_add", timeout=30.0, check=check)
                except asyncio.TimeoutError:
                    try:
                        await loadingMessage.clear_reaction("⛏️")
                    except discord.NotFound:
                        pass

                    try:
                        await loadingMessage.clear_reaction("⚔️")
                    except discord.NotFound:
                        pass

                    try:
                        await loadingMessage.clear_reaction("🏰")
                    except discord.NotFound:
                        pass
                    return
                
                if reaction.emoji == "⛏️":
                    embed.add_field(name="Skills", value=f"```prolog\n{skillText}\n```", inline=False)
                    try:
                        await loadingMessage.remove_reaction("⛏️", ctx.author)
                    except discord.NotFound:
                        pass

                elif reaction.emoji == "⚔️":
                    embed.add_field(name="Slayer", value=f"```prolog\n{slayerText}\n```", inline=False)
                    try:
                        await loadingMessage.remove_reaction("⚔️", ctx.author)
                    except discord.NotFound:
                        pass

                elif reaction.emoji == "🏰":
                    embed.add_field(name="Catacombs", value=f"```prolog\n{cataText}\n```", inline=False)
                    try:
                        await loadingMessage.remove_reaction("🏰", ctx.author)
                    except discord.NotFound:
                        pass

                else:
                    raise ValueError(f"Reaction {reaction.emoji} not a valid option")


                await loadingMessage.edit(content="", embed=embed, allowed_mentions=discord.AllowedMentions(replied_user=False))
        elif code == 403:
            await loadingMessage.edit(content="There was an error with the API, please wait for a fix.")
        else:
            await loadingMessage.edit(content="There was an error in the return code from the API, please try again later.", allowed_mentions=discord.AllowedMentions(replied_user=False))

    @AsyncTTL(time_to_live=120, maxsize=1000)
    async def getAhData(self, uuid):
        if rateLimited():
            return None, 429


        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.hypixel.net/skyblock/auction?player={uuid}&key={HYPIXEL_API_KEY}") as r:
                if r.status != 200:
                    return None, r.status

                data = (await r.json())
                return data, r.status
    
    @AsyncTTL(time_to_live=1800, maxsize=1000)
    async def getProfileData(self, uuid):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.hypixel.net/skyblock/profiles?uuid={uuid}&key={HYPIXEL_API_KEY}") as r:
                return (await r.json()), r.status        

    def niceTime(self, o):
        s = ""
        if o.days != 0:
            s += f"{o.days}d, "
        hours, rem = divmod(o.seconds, 3600)
        mins, secs = divmod(rem, 60)
        s += f"{hours}h, "
        s += f"{mins}m"
        return s

    @commands.cooldown(1, 5, type=commands.BucketType(4))
    @isSbBotCmdChannel()
    @commands.guild_only()
    @commands.command(brief="Shows ah offers for a user.", usage="[user]", help="Shows all the auction house offers that a user has.")
    async def ah(self, ctx, user=None):  # sourcery no-metrics
        if user is None:
            await ctx.channel.send("You must specify a user", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
            return
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.mojang.com/users/profiles/minecraft/{user}") as r:
                if r.status == 204:
                    await ctx.channel.send("Could not find a user with that username", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
                    return
        
                uuid = (await r.json())["id"]
                name = (await r.json())["name"]
        loadingMessage = await ctx.channel.send("Fetching data <a:loading:860077892611080200>", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
        ahTask = asyncio.create_task(self.getAhData(uuid))
        data, code = await ahTask
        if code == 429:
            await loadingMessage.edit("API rate limit exceeded, please try again soon.", allowed_mentions=discord.AllowedMentions(replied_user=False))
            return
        elif code == 200:
            if rateLimited():
                await loadingMessage.edit("API rate limit exceeded, please try again soon.", allowed_mentions=discord.AllowedMentions(replied_user=False))
                return
            pTask = asyncio.create_task(self.getProfileData(uuid))
            pdata, code = await pTask
            if pdata["profiles"] is None:
                await loadingMessage.edit(content="This user has not played skyblock or doesn't have any profiles.", allowed_mentions=discord.AllowedMentions(replied_user=False))
                return
            if code == 200:
                profiles = {}
                auctions = {}
                reference = {}
                for profile in pdata["profiles"]:
                    profiles[profile["profile_id"]] = profile["cute_name"]
                    auctions[profile["cute_name"]] = []
                    reference[profile["members"][uuid]["last_save"]] = profile["cute_name"]
                
                    
                
                for auction in data["auctions"]:
                    if ((auction["end"]/1000) + 300) <= time.time() and (auction["claimed"]):
                        continue
                    try:
                        auctions[profiles[auction["profile_id"]]].append(auction)
                    except KeyError:
                        pass
                index = 0
                embeds = []
                for i in range(len(auctions)):
                    embed = discord.Embed(title=f"Auctions", color=0x43eb34)
                    embed.description = f"[{name}](https://sky.shiiyu.moe/stats/{name})"
                    unClaimedTotal = 0
                    for auction in auctions[reference[(list(reversed(reference)))[i]]]:
                        ended = ((auction["end"]/1000) <= time.time())
                        text = ""
                        if ended:
                            if not(auction["claimed"]):
                                unClaimedTotal += auction["highest_bid_amount"]
                                text += f"This auction has **ended at {human_format(auction['highest_bid_amount'])}** coins"
                            
                        else:
                            try:
                                _ = auction["bin"]
                                text += f"Current BIN: **{human_format(auction['starting_bid'])}**"
                            except KeyError:
                                text += f"Current Bid: **{human_format(max(auction['highest_bid_amount'], auction['starting_bid']))}**"
                            timeLeft = dt.datetime.fromtimestamp(auction["end"]/1000) - dt.datetime.now()
                            if timeLeft.total_seconds() <= 120:
                                text += " • Ending Soon"
                            else:
                                text += f" • Ends in: **{self.niceTime(timeLeft)}**"
                        embedName = auction["item_name"]
                        if re.match(r"\[Lvl \d*\]", embedName) is not None:
                            embedName += f" - {auction['tier'].capitalize()}"
                        embed.add_field(name=embedName, value=text, inline=False)
                    if auctions[reference[(list(reversed(reference)))[i]]] == []:
                        embed.add_field(name="⠀", value=f"No auctions found for {name} on {reference[(list(reversed(reference)))[i]]}")
                    embed.set_thumbnail(url=f"https://mc-heads.net/head/{uuid}/.png")
                    embed.set_footer(text=f"Profile: {reference[(list(reversed(reference)))[i]]} • Page {i+1}/{len(auctions)}")
                    if unClaimedTotal != 0:
                        embed.description = f"**[{name}](https://sky.shiiyu.moe/stats/{name}) has {human_format(unClaimedTotal)} coins that are unclaimed.**\n"
                    embed.timestamp = dt.datetime.now()
                    embeds.append(embed)
                while True:
                    
                    await loadingMessage.edit(content="", embed=embeds[index], allowed_mentions=discord.AllowedMentions(replied_user=False))
                    reactions = ["⏮️","◀️","▶️","⏭️"]
                    def check(reaction, u):
                        return (reaction.emoji in reactions) and u == ctx.message.author
                    for reaction in reactions:
                        await loadingMessage.add_reaction(reaction)
                    try:
                        reaction, u = await client.wait_for("reaction_add", timeout=30, check=check)
                    except asyncio.TimeoutError:
                        for reaction in reactions:
                            try:
                                await loadingMessage.clear_reaction(reaction)
                            except discord.NotFound:
                                pass
                        return
                    if reaction.emoji == "⏮️":
                        index = 0
                    elif reaction.emoji == "◀️":
                        index -= 1
                    elif reaction.emoji == "▶️":
                        index += 1
                    else:
                        index = len(auctions) - 1
                    if index < 0:
                        index = 0
                    elif index >= len(auctions):
                        index = len(auctions) - 1
                    try:
                        await loadingMessage.remove_reaction(reaction, ctx.author)
                    except discord.NotFound:
                        pass
                    
            elif code == 429:
                await ctx.channel.send("API rate limit exceeded, please try again soon.")
                return
            else:
                await ctx.channel.send("There was an error in talking with the API, please try again later")
        else:
            await ctx.channel.send("There was an error in talking with the API, please try again later")
    

    @AsyncTTL(time_to_live=1800, maxsize=1000)
    async def getBazaarData(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.hypixel.net/skyblock/bazaar?key={HYPIXEL_API_KEY}") as r:
                return (await r.json()), r.status

    @commands.cooldown(1, 5, type=commands.BucketType(4))
    @isSbBotCmdChannel()
    @commands.guild_only()
    @commands.command(usage="[item]", brief="Shows info on an item in the bazaar", help="Shows buy and sell order price, quantity and volume for an item on the bazaar")
    async def bazaar(self, ctx,*,  item=None):  # sourcery no-metrics
        if item is None:
            await ctx.reply("You have to choose an item to display")
            return
        loadingMessage = await ctx.reply("Loading data <a:loading:860077892611080200>", allowed_mentions=discord.AllowedMentions(replied_user=False))
        data, code = await self.getBazaarData()
        if code == 429:
            pass
        elif code == 404:
            await loadingMessage.edit(content="There is no player with this name or they have never played Skyblock.", allowed_mentions=discord.AllowedMentions(replied_user=False))
            return
        elif code == 500:
            await loadingMessage.edit(content="There was an error in contacting the API, please try again later.", allowed_mentions=discord.AllowedMentions(replied_user=False))
            return
        elif code == 502:
            await loadingMessage.edit(content="The Hypixel API is experiencing some technical difficulties, please try again later.", allowed_mentions=discord.AllowedMentions(replied_user=False))
            return 
        elif code == 503:
            await loadingMessage.edit(content="The Hypixel API is under maintenance, please try again later.", allowed_mentions=discord.AllowedMentions(replied_user=False))
            return
        elif code == 200:
            products = data["products"]
            badProductNames = {"OAK LOG":"LOG"}
            try:
                item = badProductNames[item.upper()]
            except KeyError:
                pass
            chosenItem = (0, None)
            for product in products:
                conf = fuzz.token_sort_ratio(product.replace("_"," "), item.upper())
                if conf == 100:
                    chosenItem = (100, product)
                    break
                elif chosenItem[0] < conf:
                    chosenItem = (conf, product)
            if chosenItem[0] < 75:
                await loadingMessage.edit(content=f"Could not find an item matching {item}", allowed_mentions=discord.AllowedMentions(replied_user=False, everyone=False, users=False, roles=False))
                return
            
            product = products[chosenItem[1]]
            quickStats = product["quick_status"]
            embed = discord.Embed(title=f"Bazaar Data For {chosenItem[1].replace('_', ' ').title()}", color=0xcfcc21)
            embed.add_field(name="Instant Buy", value=f'{round(quickStats["buyPrice"], 1):,}')
            embed.add_field(name="Buy Volume", value=f'{round(quickStats["buyVolume"], 1):,}')
            embed.add_field(name="Buy Orders", value=f'{round(quickStats["buyOrders"], 1):,}')
            embed.add_field(name="Instant Sell", value=f'{round(quickStats["sellPrice"], 1):,}')
            embed.add_field(name="Sell Volume", value=f'{round(quickStats["sellVolume"], 1):,}')
            embed.add_field(name="Sell Orders", value=f'{round(quickStats["sellOrders"], 1):,}')
            embed.timestamp = dt.datetime.now()
            await loadingMessage.edit(content="", embed=embed, allowed_mentions=discord.AllowedMentions(replied_user=False))
            return


@tasks.loop(minutes=1)
async def resetRateLimit():
    global hyRequestsMade
    hyRequestsMade = 0

@client.event
async def on_command_error(ctx, error):

    

    if isinstance(error, commands.NoPrivateMessage):
        await ctx.channel.send("This command is only available in a server", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
        return

    if isinstance(error, commands.CommandOnCooldown):
        await ctx.channel.send(f"You cannot use that command for another {round(error.retry_after, 2)} seconds.", reference=ctx.message)
        return

    if isinstance(error, commands.MemberNotFound):
        await ctx.send("No such member found.", delete_after=5, reference=ctx.message)
        return

    if isinstance(error, commands.EmojiNotFound):
        message = await ctx.channel.send(f"Not a valid emoji", delete_after=5, reference=ctx.message)
        await message.delete(delay=5)
        return

    if isinstance(error, commands.PartialEmojiConversionFailure):
        message = await ctx.channel.send(f"You can only use custom emojis", delete_after=5, reference=ctx.message)
        return

    if isinstance(error, commands.MissingRole):
        await ctx.channel.send("You can not use this command", delete_after=5, reference=ctx.message)
        return
    
    if isinstance(error, commands.CheckFailure):
        await ctx.channel.send("This command can not be used here", delete_after=5, reference=ctx.message)
        return
    
    if isinstance(error, commands.DisabledCommand):
        await ctx.channel.send("This command is currently disabled.", delete_after=5, reference=ctx.message)

    if isinstance(error, commands.CommandNotFound):
        return

    raise error








@tasks.loop(seconds=1800)
async def get_json_file():
    async with aiohttp.ClientSession() as session:
            async with session.get("https://raw.githubusercontent.com/skyblockz/pricecheckbot/master/scammer.json") as r:
                r = (await r.json())
                with open("scammers.json", "w") as f:
                    json.dump(r, f)
    

























async def filter(ctx, checkAll=False):  # sourcery no-metrics
    files = []
    if ctx.author.id == client.user.id:
        return False
    if ctx.channel.id == getLoggingChannel(ctx.guild.id):
        return False
    if ctx.channel.category_id in ignoredCategories:
        return True

    linkText = str(ctx.content).replace("https://","").replace("http://","").replace("www.","")
    links = linkText.split(" ")
    text = str(ctx.content).replace(".","").replace(",","").replace("!","").replace("?","").lower()
    words = text.split(" ")



    for word in links:
        for link in linkFilter: #link filter
            try:
                if word[-1] == "/":
                    word = word[0:-1]
            except:
                pass
            if word.replace("https://","").replace("http://","").replace("www.","") == link:
                await ctx.delete()
                try:
                    role = client.get_role(mutedRole)
                    await ctx.user.add_roles(role)
                except Exception:
                    pass


                embed = discord.Embed(title="", color=0xff1c1c)
                if len(ctx.content) >= 900:
                    embed.add_field(name=":wastebasket:", value=f"**Message sent by <@{ctx.author.id}> deleted in <#{ctx.channel.id}>**\nMessage too long, attached as file", inline=False)
                    with open(f"{ctx.author.name}Message.txt","w") as f:
                        f.write(ctx.content)
                    files.append(discord.File(f"{ctx.author.name}Message.txt", filename="message.txt"))
                else:
                    embed.add_field(name=":wastebasket:", value=f"**Message sent by <@{ctx.author.id}> deleted in <#{ctx.channel.id}>**\n{ctx.content}", inline=False)
                embed.set_author(name=f"{ctx.author.name}#{ctx.author.discriminator}", icon_url=ctx.author.avatar_url)
                embed.add_field(name="Link Detected", value=f"{link}")
                embed.timestamp = dt.datetime.utcnow()
                embed.set_footer(text=f"Message ID:{ctx.id} • User ID:{ctx.author.id}")
                channel = getLoggingChannel(ctx.guild.id)
                try:
                    await channel.send(embed=embed)
                except Exception:
                    pass


                messageSent = await ctx.channel.send(f"<@{ctx.author.id}> You cannot send that link! :rage:")
                await messageSent.delete(delay=5)

                return False

    for word in words: #starts the loop to check each word        
        if word in allowedWords or ("http" in word):
            continue

        for swearWord in blacklist0: #starts the loop to check the slurs

            confidence = fuzz.token_set_ratio(word, swearWord) 

            if confidence >= confidenceThreshold:
                await ctx.delete()


                embed = discord.Embed(title="", color=0xff1c1c)
                if len(ctx.content) >= 900:
                    embed.add_field(name=":wastebasket:", value=f"**Message sent by <@{ctx.author.id}> deleted in <#{ctx.channel.id}>**\nMessage too long, attached as file", inline=False)
                    with open(f"{ctx.author.name}Message.txt","w") as f:
                        f.write(ctx.content)
                    files.append(discord.File(f"{ctx.author.name}Message.txt", filename="message.txt"))
                else:
                    embed.add_field(name=":wastebasket:", value=f"**Message sent by <@{ctx.author.id}> deleted in <#{ctx.channel.id}>**\n{ctx.content}", inline=False)
                embed.set_author(name=f"{ctx.author.name}#{ctx.author.discriminator}", icon_url=ctx.author.avatar_url)
                embed.add_field(name="Confidence", value=f"{confidence}% sure")
                embed.add_field(name="Word Detected", value=f"{swearWord}")
                embed.timestamp = dt.datetime.utcnow()
                embed.set_footer(text=f"Message ID:{ctx.id} • User ID:{ctx.author.id}")
                channel = getLoggingChannel(ctx.guild.id)

                await channel.send(embed=embed, files=files)

                messageSent = await ctx.channel.send(f"<@{ctx.author.id}> You cannot say that! :rage:")
                await messageSent.delete(delay=5)
                return False

        if ctx.channel.id in allowedChannels and not(checkAll):
            return True

        for swearWord in blacklist1: #starts the loop to check swears
            confidence = fuzz.token_set_ratio(word, swearWord)
            if swearWord in word or ("http" in word):
                confidence = 100
            if confidence >= confidenceThreshold:

                await ctx.delete()
                try:
                    user = client.get_user_info(ctx.author.id)
                    await client.send_message(user, f"You can not say that word :rage:!")
                except Exception:
                    pass

                embed = discord.Embed(title="", color=0xff1c1c)
                if len(ctx.content) >= 900:
                    embed.add_field(name=":wastebasket:", value=f"**Message sent by <@{ctx.author.id}> deleted in <#{ctx.channel.id}>**\nMessage too long, attached as file", inline=False)
                    with open(f"{ctx.author.name}Message.txt","w") as f:
                        f.write(ctx.content)
                    files.append(discord.File(f"{ctx.author.name}Message.txt", filename="message.txt"))
                else:
                    embed.add_field(name=":wastebasket:", value=f"**Message sent by <@{ctx.author.id}> deleted in <#{ctx.channel.id}>**\n{ctx.content}", inline=False)
                embed.set_author(name=f"{ctx.author.name}#{ctx.author.discriminator}", icon_url=ctx.author.avatar_url)
                embed.add_field(name="Confidence", value=f"{confidence}% sure")
                embed.add_field(name="Word Detected", value=f"{swearWord}")
                embed.timestamp = dt.datetime.utcnow()
                embed.set_footer(text=f"Message ID:{ctx.id} • User ID:{ctx.author.id}")
                channel = getLoggingChannel(ctx.guild.id)

                await channel.send(embed=embed)

                messageSent = await ctx.channel.send(f"<@{ctx.author.id}> You cannot say that! :rage:")
                await messageSent.delete(delay=5)
                return False


    return True

spamCache = cachetools.TTLCache(1000, 3)
warnedUsers = cachetools.TTLCache(1000, 10)
async def spamFilter(message:discord.Message) -> bool:

    if message.author.id == client.user.id:
        return True
    if message.channel.category_id in ignoredCategories:
        return True
    try:
        spamCache[(str(message.author), str(message.content))] = spamCache[(str(message.author), str(message.content))] + 1
    except KeyError:
        spamCache[(str(message.author), str(message.content))] = 1
    if spamCache[(str(message.author), str(message.content))] > 2:
        if message.content != "":
            async for m in message.channel.history(limit=200):
                if (m.author == message.author) and (m.content == message.content):
                    try:
                        await m.delete()
                    except discord.NotFound:
                        pass
            if message.author.id not in warnedUsers:
                warnedUsers[message.author.id] = None
                await message.channel.send(f"{message.author.mention} Do not spam!", delete_after=5)
            return False
        return True
    return True

async def nameCheck(member:discord.Member):
    for mword in member.display_name.split(" "):
        for word in blacklist0:
            if word in allowedWords:
                continue
            if word in mword:
                name = random.choice(names) + random.choice(names)
                await member.edit(reason="Inapropriate Nick", nick=name)
                embed = discord.Embed(title="User Nick Changed", color=0xe0d100)
                embed.add_field(name="Old Nickname", value=f"{member.name}")
                embed.add_field(name="New Nickname", value=f"{member.display_name}")
                embed.add_field(name="User", value=f"<@{member.id}>")
                channel = getLoggingChannel(member.guild.id)
                await channel.send(embed=embed)
                return

        for word in blacklist1:
            if word in allowedWords:
                continue
            if word in mword:
                name = random.choice(names) + random.choice(names)
                await member.edit(reason="Inapropriate Nick", nick=name)
                embed = discord.Embed(title="User Nick Changed", color=0xe0d100)
                embed.add_field(name="Old Nickname", value=f"{member.name}")
                embed.add_field(name="New Nickname", value=f"{member.display_name}")
                embed.add_field(name="User", value=f"<@{member.id}>")
                channel = getLoggingChannel(member.guild.id)
                await channel.send(embed=embed)
                return

@client.event
async def on_message(ctx):
    rows = interactor.read_data(afkConn, "*", "afk")

    for row in rows:
        if ctx.author.id in row:
            embed = discord.Embed(title="", color=0x3498eb)
            embed.add_field(name="Unmarked as afk", value="You are no longer marked as afk")
            message = await ctx.channel.send(embed=embed)
            await message.delete(delay=5)
            interactor.delete_data(afkConn, "afk", "user_id", str(ctx.author.id))

    task = asyncio.create_task(filter(ctx))
    spamTask = asyncio.create_task(spamFilter(ctx))
    sProcCommands = await spamTask

    mentions = ctx.mentions
    for member in mentions:
        for row in rows:
            if member.id in row:
                embed = discord.Embed(title="", color=0x3498eb)
                reason = interactor.read_data(afkConn, "*", "afk", "user_id", str(member.id))[0][2]
                embed.add_field(name=f"Marked as afk", value=f"<@{member.id}> is marked as afk", inline=False)
                embed.add_field(name="Reason", value=f"{reason}")
                message = await ctx.channel.send(embed=embed, allowed_mentions=discord.AllowedMentions(everyone=False, users=False, roles=False))
                await message.delete(delay=30)

    procCommands = await task

    if procCommands and sProcCommands:
        await client.process_commands(ctx)

@client.event
async def on_message_edit(before, after):
    
    if (before.author.id == client.user.id) or (before.author.bot):
        return

    if before.content == after.content:
        return

    files = []
    embed = discord.Embed(title=f"", color=0xe0d100)
    embed.add_field(name=f":pencil:", value=f"**[Message]({before.jump_url}) sent by <@{before.author.id}> edited in <#{before.channel.id}>**", inline=False)
    embed.set_author(name=f"{before.author.name}#{before.author.discriminator}", icon_url=before.author.avatar_url)

    if before.content == "":
        before.content = "None"
    if after.content == "":
        after.content = "None"

    if len(before.content) > 900:
        embed.add_field(name=f"Old Message", value="Message too long, attached as file")
        with open(f"{before.author.name}BeforeMessage.txt", "w") as f:
            f.write(before.content)
        files.append(discord.File(f"{before.author.name}BeforeMessage.txt", filename="message.txt"))
    else:
        embed.add_field(name="Old Message", value=f"{before.content}")

    if len(after.content) > 900:
        embed.add_field(name="New Message", value="Message too long, attached as file", inline=False)
        with open(f"{after.author.name}AfterMessage.txt","w") as f:
            f.write(after.content)
        files.append(discord.File(f"{after.author.name}AfterMessage.txt", filename="message.txt"))
    else:
        embed.add_field(name="New Message", value=f"{after.content}", inline=False)

    attachments = after.attachments
    for attachment in attachments:
        files.append(await attachment.to_file())
    if attachments != []:
        embed.add_field(name="Message Attachments", value="Attached as file")

    embed.set_footer(text=f"Message ID:{before.id} • User ID:{before.author.id}")
    embed.timestamp = dt.datetime.utcnow()

    channel = getLoggingChannel(after.guild.id)
    await channel.send(embed=embed, files=files)

    if os.path.exists(f"{before.author.name}BeforeMessage.txt"):
        os.remove(f"{before.author.name}BeforeMessage.txt")
    if os.path.exists(f"{after.author.name}BeforeMessage.txt"):
        os.remove(f"{after.author.name}BeforeMessage.txt")

    asyncio.create_task(filter(after))

@client.event
async def on_raw_message_delete(payload):  # sourcery no-metrics
    try:
        guildId = payload.guild_id
    except AttributeError:
        return
    else:
        if payload.channel_id == getLoggingChannel(guildId):
            return
    try:
        if (payload.cached_message.author.id == client.user.id) or (payload.cached_message.author.bot):
            return
    except AttributeError:
        pass


    if payload.cached_message is None:
        guild = client.get_guild(payload.guild_id)
        embed = discord.Embed(title=f"{guild.name}", color=0xdb2421)
        embed.add_field(name=f":wastebasket:", value=f"Message sent in <#{payload.channel_id}> deleted.")
        embed.timestamp = dt.datetime.utcnow()
        embed.set_footer(text=f"Message ID:{payload.message_id}")
        channel = getLoggingChannel(guildId)
        await channel.send(embed=embed)
        return

    message = payload.cached_message
    embed = discord.Embed(title=f"", color=0xdb2421)
    embed.set_author(name=f"{message.author.name}#{message.author.discriminator}", icon_url=message.author.avatar_url)
    files = []
    if len(message.content) > 940:
        with open(f"message{message.author}.txt", "w") as f:
            f.write(message.content)
        embed.add_field(name=":wastebasket:", value=f"**Message sent by <@{message.author.id}> deleted in <#{message.channel.id}>**\nMessage too long")
        attachments = message.attachments
        for attachment in attachments:
            files.append(await attachment.to_file())
        if attachments != []:
            embed.add_field(name="Message Attachments", value="Attached as file")
        embed.timestamp = dt.datetime.utcnow()
        embed.set_footer(text=f"Message ID:{message.id} • User ID:{message.author.id}")
        channel = getLoggingChannel(guildId)
        files.append(discord.File(f"message{message.author}.txt", filename="message.txt"))
        if len(files) > 10:
            await channel.send(embed=embed, files=files[0:10])
            await channel.send(files=files[10:])
        else:
            await channel.send(embed=embed, files=files)
        os.remove(f"message{message.author}.txt")
        return
    else:
        embed.add_field(name=f":wastebasket:", value=f"**Message sent by <@{message.author.id}> deleted in <#{message.channel.id}>**\n{message.content}", inline=False)
        attachments = message.attachments
        for attachment in attachments:
            files.append(await attachment.to_file())
        if attachments != []:
            embed.add_field(name="Message Attachments", value="Attached as file")
        embed.timestamp = dt.datetime.utcnow()
        embed.set_footer(text=f"Message ID:{message.id} • User ID:{message.author.id}")
        channel = getLoggingChannel(guildId)
        if len(files) > 10:
            await channel.send(embed=embed, files=files[0:10])
            await channel.send(files=files[10:])
        else:
            await channel.send(embed=embed, files=files)

async def on_raw_bulk_message_delete(payload:discord.RawBulkMessageDeleteEvent): # sourcery no-metrics
    try:
        guild:Optional[discord.Guild] = client.get_guild(payload.guild_id)
    except AttributeError:
        return
    if guild is None:
        return
    if payload.cached_messages is None:
        embed = discord.Embed(title=f"{guild.name}", color=0xdb2421)
        embed.add_field(name=f":wastebasket:", value=f"Messages sent in <#{payload.channel_id}> deleted.")
        embed.timestamp = dt.datetime.utcnow()
        embed.set_footer(text=f"Message ID:{payload.message_id}")
        channel = getLoggingChannel(guild.id)
        await channel.send(embed=embed)
        return

    for message in payload.cached_messages:
        embed = discord.Embed(title=f"", color=0xdb2421)
        embed.set_author(name=f"{message.author.name}#{message.author.discriminator}", icon_url=message.author.avatar_url)
        files = []
        if len(message.content) > 940:
            with open(f"message{message.author}.txt", "w") as f:
                f.write(message.content)
            embed.add_field(name=":wastebasket:", value=f"**Message sent by <@{message.author.id}> deleted in <#{message.channel.id}>**\nMessage too long")
            attachments = message.attachments
            for attachment in attachments:
                files.append(await attachment.to_file())
            if attachments != []:
                embed.add_field(name="Message Attachments", value="Attached as file")
            embed.timestamp = dt.datetime.utcnow()
            embed.set_footer(text=f"Message ID:{message.id} • User ID:{message.author.id}")
            channel = getLoggingChannel(guild.id)
            files.append(discord.File(f"message{message.author}.txt", filename="message.txt"))
            if len(files) > 10:
                await channel.send(embed=embed, files=files[0:10])
                await channel.send(files=files[10:])
            else:
                await channel.send(embed=embed, files=files)
            os.remove(f"message{message.author}.txt")
            return
        else:
            embed.add_field(name=f":wastebasket:", value=f"**Message sent by <@{message.author.id}> deleted in <#{message.channel.id}>**\n{message.content}", inline=False)
            attachments = message.attachments
            for attachment in attachments:
                files.append(await attachment.to_file())
            if attachments != []:
                embed.add_field(name="Message Attachments", value="Attached as file")
            embed.timestamp = dt.datetime.utcnow()
            embed.set_footer(text=f"Message ID:{message.id} • User ID:{message.author.id}")
            channel = getLoggingChannel(guild.id)
            if len(files) > 10:
                await channel.send(embed=embed, files=files[0:10])
                await channel.send(files=files[10:])
            else:
                await channel.send(embed=embed, files=files)


@client.event
async def on_voice_state_update(member, bef, aft):
    
    if aft.channel is None:
        guild = client.get_guild(guild_id)
        role = guild.get_role(silentVcRole)
        await member.remove_roles(role, reason="Left VC")

    elif bef.channel is None:
        guild = client.get_guild(guild_id)
        role = guild.get_role(silentVcRole)
        await member.add_roles(role, reason="Joined VC")


@client.event
async def on_member_join(member):
    
    asyncio.create_task(nameCheck(member))

    rows = interactor.read_data(tradeBanConn, "*", "tradeBanned")
    if member.id in rows:
        role = member.guild.get_role(tradeBanRole)
        await member.add_roles(role, reason="Trade Banned")

    
@client.event
async def on_member_update(before, after):
    asyncio.create_task(nameCheck(after))

@client.event
async def on_error(event, *args, **kwargs):
    errorMessage = errorLogger(event)
    print(errorMessage)
    owner = client.get_user(client.owner_id)

@client.command(hidden=True)
async def logout(ctx):
    if ctx.author.id == client.owner_id:
        await client.logout()
        return
    raise commands.CommandNotFound


afkConn = interactor.create_connection("afkDatabase.db")
tradeBanConn = interactor.create_connection("tradeBanned.db")





client.add_cog(Moderation(client))
client.add_cog(Fun(client))
client.add_cog(Image(client))
client.add_cog(Miscellaneous(client))
client.add_cog(Skyblock(client))

resetRateLimit.start()


client.run(TOKEN)
