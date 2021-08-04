from data import data
import discord
from discord.ext import commands
import random
import datetime as dt
from fuzzywuzzy import fuzz
import cachetools
import unicodedata

class Filters():
    def __init__(self, bot) -> None:
        self.bot = bot
        self.spamCache = cachetools.TTLCache(1000, 3)
        self.warnedUsers = cachetools.TTLCache(1000, 10)
    
    async def swearFilter(self, ctx, checkAll=False):  # sourcery no-metrics
        files = []
        if ctx.author.id == self.bot.user.id:
            return False
        if ctx.channel.id == data.getLoggingChannel():
            return False
        if ctx.channel.category_id in data.getSwearIgnoredCategories():
            return False

        linkText = str(ctx.content).replace("https://","").replace("http://","").replace("www.","")
        links = linkText.split(" ")
        replaceWords = {".":"", ",":"", "!":"", "?":"", "¡":"i", "-":""}
        text = "".join(
            c
            for c in unicodedata.normalize("NFKD", str(ctx.content))
            if not unicodedata.combining(c)
        )
        for k in replaceWords:
            text = text.replace(k, replaceWords[k])
        words = text.split(" ")



        for word in links:
            for link in data.getLinkFilter(): #link filter
                try:
                    if word[-1] == "/":
                        word = word[0:-1]
                except:
                    pass
                if word.replace("https://","").replace("http://","").replace("www.","") == link:
                    try:
                        await ctx.delete()
                    except discord.NotFound:
                        pass
                    try:
                        role = self.bot.get_role(data.getMutedRole())
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
                    channel = self.bot.get_channel(data.getLoggingChannel())
                    if channel is not None:
                        await channel.send(embed=embed)


                    messageSent = await ctx.channel.send(f"<@{ctx.author.id}> You cannot send that link! :rage:")
                    await messageSent.delete(delay=5)

                    return False

        for word in words: #starts the loop to check each word        
            if word in data.getAllowedWords() or ("http" in word):
                continue

            for swearWord in data.getBlacklist0(): #starts the loop to check the slurs

                confidence = fuzz.token_set_ratio(word, swearWord) 

                if swearWord in word:
                    confidence = 100


                if confidence >= data.getConfidenceThreshold():
                    try:
                        await ctx.delete()
                    except discord.NotFound:
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
                    channel = self.bot.get_channel(data.getLoggingChannel())
                    if channel is not None:
                        await channel.send(embed=embed, files=files)

                    messageSent = await ctx.channel.send(f"<@{ctx.author.id}> You cannot say that! :rage:")
                    await messageSent.delete(delay=5)
                    return False

            if ctx.channel.id in data.getAllowedChannels() and not(checkAll):
                return True

            for swearWord in data.getBlacklist1(): #starts the loop to check swears
                confidence = fuzz.token_set_ratio(word, swearWord)
                if swearWord in word:
                    confidence = 100
                if confidence >= data.getConfidenceThreshold():

                    await ctx.delete()
                    try:
                        user = self.bot.get_user_info(ctx.author.id)
                        await self.bot.send_message(user, f"You can not say that word :rage:!")
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
                    channel = self.bot.get_channel(data.getLoggingChannel())
                    if channel is not None:
                        await channel.send(embed=embed)

                    messageSent = await ctx.channel.send(f"<@{ctx.author.id}> You cannot say that! :rage:")
                    await messageSent.delete(delay=5)
                    return False


        return True

    async def spamFilter(self, message:discord.Message) -> bool:

        if message.author.id == self.bot.user.id:
            return True
        if message.channel.category_id in data.getSpamIgnoredCategories():
            return True
        try:
            self.spamCache[(str(message.author), str(message.content))] = self.spamCache[(str(message.author), str(message.content))] + 1
        except KeyError:
            self.spamCache[(str(message.author), str(message.content))] = 1
        if self.spamCache[(str(message.author), str(message.content))] > 2:
            if message.content != "":
                async for m in message.channel.history(limit=200):
                    if (m.author == message.author) and (m.content == message.content):
                        try:
                            await m.delete()
                        except discord.NotFound:
                            pass
                if message.author.id not in self.warnedUsers:
                    self.warnedUsers[message.author.id] = None
                    await message.channel.send(f"{message.author.mention} Do not spam!", delete_after=5)
                return False
            return True
        return True

    async def nameCheck(self, member:discord.Member):
        for mword in member.display_name.split(" "):
            for word in data.getBlacklist0():
                if word in data.getAllowedWords():
                    continue
                if word in mword:
                    name = random.choice(data.getNames()) + " " + random.choice(data.getNames())
                    
                    embed = discord.Embed(title="User Nick Changed", color=0xe0d100)
                    embed.add_field(name="Old Nickname", value=f"{member.display_name}")
                    await member.edit(reason="Inapropriate Nick", nick=name)
                    embed.add_field(name="New Nickname", value=f"{member.display_name}")
                    embed.add_field(name="User", value=f"<@{member.id}>")
                    channel = self.bot.get_channel(data.getLoggingChannel())
                    if channel is not None:
                        await channel.send(embed=embed)
                    return

            for word in data.getBlacklist1():
                if word in data.getAllowedWords():
                    continue
                if word in mword:
                    name = random.choice(data.getNames()) + random.choice(data.getNames())
                    await member.edit(reason="Inapropriate Nick", nick=name)
                    embed = discord.Embed(title="User Nick Changed", color=0xe0d100)
                    embed.add_field(name="Old Nickname", value=f"{member.name}")
                    embed.add_field(name="New Nickname", value=f"{member.display_name}")
                    embed.add_field(name="User", value=f"<@{member.id}>")
                    channel = self.bot.get_channel(data.getLoggingChannel())
                    if channel is not None:
                        await channel.send(embed=embed)
                    return
