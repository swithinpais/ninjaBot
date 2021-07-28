import discord
from discord.errors import Forbidden
from discord.ext import commands, tasks
import interactor
from data import data as botData
from typing import Callable, List, Optional
import datetime as dt
from . import commandChecks

import aiohttp
import json
from cache import AsyncTTL
import asyncio
import time
import re
from fuzzywuzzy import fuzz

class Skyblock(commands.Cog, name="Skyblock"):
    def __init__(self, bot, loadedCogs, allCogs):
        self.bot = bot
        self.allCogs = allCogs
        self.loadedCogs = loadedCogs

        allCogs.add(self.qualified_name)
        loadedCogs.append(self.qualified_name)

    def cog_unload(self):
        self.loadedCogs.pop(self.loadedCogs.index(self.qualified_name))
        return super().cog_unload()  

    def rateLimited(self):
        botData.addHyRequestsMade()
        return botData.hyRequestsMade > 100
    
    def human_format(self, num):
        num = float('{:.3g}'.format(num))
        magnitude = 0
        while abs(num) >= 1000:
            magnitude += 1
            num /= 1000.0
        return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T'][magnitude])

    @commands.cooldown(1, 0.5, type=commands.BucketType(4)) 
    @commands.guild_only()
    @commandChecks.isSbBotCmdChannel()
    @commands.command(brief="Verifies you", usage="[IGN]", help="Verifies you on the server and gives you the Verified role")
    async def verify(self, ctx, ign=None):
        role = ctx.guild.get_role(botData.getVerifiedRole())
        if ign is None:
            await ctx.channel.send("You need to provide an ign", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
            return

        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.mojang.com/users/profiles/minecraft/{ign}") as r:
                if r.status == 204:
                    await ctx.channel.send(f"Could not find a user with the username {ign}", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False, everyone=False, roles=False, users=False))
                    return
                r = (await r.json())
                uuid = r["id"]
        if self.rateLimited():
            await ctx.channel.send("API rate limit exceeded, please try again soon.")
            return

        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.hypixel.net/player?key={botData.HYPIXEL_API_KEY}&uuid={uuid}") as r:
                rh = (await r.json())

        
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
                    channel = botData.getLoggingChannel(ctx.guild.id)
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
            await ctx.author.remove_roles(role, reason="Incorrect Link")
            return
        else:
            await ctx.author.add_roles(role, reason="Verified")
            await ctx.channel.send("Successfully verified", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
            rows = interactor.read_data(botData.linkedAccountsConn, "user_id", "linkedAccounts", "user_id", ctx.author.id)
            for row in rows:
                if ctx.author.id in row:
                    interactor.delete_data(data.linkedAccountsConn, "linkedAccounts", "user_id", ctx.author.id)
            interactor.add_data(botData.linkedAccountsConn, "linkedAccounts", user_id=int(ctx.author.id), ign=ign)

    @AsyncTTL(time_to_live=300, maxsize=250)
    async def weightApiRequest(self, uuid, profile=None):
        if self.rateLimited():
            return False, False
        if profile is None:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://127.0.0.1:9281/v1/profiles/{uuid}/weight?key={botData.HYPIXEL_API_KEY}") as r:
                    try:
                        data = (await r.json())["data"]
                    except KeyError:
                        data = (await r.json())
                    code = r.status
        else:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://127.0.0.1:9281/v1/profiles/{uuid}/{profile}?key={botData.HYPIXEL_API_KEY}") as r:
                    try:
                        data = (await r.json())["data"]
                    except KeyError:
                        data = (await r.json())
                    code = r.status

        return data, code


    #@commands.cooldown(1, 2, type=commands.BucketType(4)) 
    @commands.guild_only()
    @commandChecks.isSbBotCmdChannel()
    @commands.command(brief="Retrieves the weight data for a user", usage="[user] (profile)", help="Retrieves the weight data for a user and caches it. It updates every 5 minutes.")
    async def weight(self, ctx, user=None, profile=None, aliases=["w"]):
        # sourcery no-metrics
        if user is None:
            rows = interactor.read_data(botData.linkedAccountsConn, "*", "linkedAccounts", "user_id", ctx.author.id)
            if rows == []:
                await ctx.channel.send("You must specify a user", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
                return
            user = rows[0][2]
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.mojang.com/users/profiles/minecraft/{user}") as mr:
                if mr.status == 204:
                    await ctx.channel.send(f"Could not find a user with the username {user}", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False, everyone=False, users=False, roles=False))
                    return
                mr = await mr.json()
                uuid = mr["id"]


        loadingMessage = await ctx.channel.send("Fetching data <a:loading:860077892611080200>", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
        data, code = await self.weightApiRequest(uuid, profile)
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
                    reaction, user = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
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
        if self.rateLimited():
            return None, 429


        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.hypixel.net/skyblock/auction?player={uuid}&key={botData.HYPIXEL_API_KEY}") as r:
                if r.status != 200:
                    return None, r.status

                data = (await r.json())
                return data, r.status
    
    @AsyncTTL(time_to_live=1800, maxsize=1000)
    async def getProfileData(self, uuid):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.hypixel.net/skyblock/profiles?uuid={uuid}&key={botData.HYPIXEL_API_KEY}") as r:
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
    @commandChecks.isSbBotCmdChannel()
    @commands.guild_only()
    @commands.command(brief="Shows ah offers for a user.", usage="[user]", help="Shows all the auction house offers that a user has.")
    async def ah(self, ctx, user=None):  # sourcery no-metrics
        if user is None:
            rows = interactor.read_data(botData.linkedAccountsConn, "*", "linkedAccounts", "user_id", ctx.author.id)
            if rows == []:
                await ctx.channel.send("You must specify a user", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
                return
            user = rows[0][2]
        
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
            if self.rateLimited():
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
                                text += f"This auction has **ended at {self.human_format(auction['highest_bid_amount'])}** coins"
                            
                        else:
                            try:
                                _ = auction["bin"]
                                text += f"Current BIN: **{self.human_format(auction['starting_bid'])}**"
                            except KeyError:
                                text += f"Current Bid: **{self.human_format(max(auction['highest_bid_amount'], auction['starting_bid']))}**"
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
                        embed.description = f"**[{name}](https://sky.shiiyu.moe/stats/{name}) has {self.human_format(unClaimedTotal)} coins that are unclaimed.**\n"
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
                        reaction, u = await self.bot.wait_for("reaction_add", timeout=30, check=check)
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
            async with session.get(f"https://api.hypixel.net/skyblock/bazaar?key={botData.HYPIXEL_API_KEY}") as r:
                return (await r.json()), r.status

    @commands.cooldown(1, 5, type=commands.BucketType(4))
    @commandChecks.isSbBotCmdChannel()
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