from data import data
import discord
from discord.ext import commands
import datetime as dt
from fuzzywuzzy import fuzz
import cachetools
import random
import interactor
import asyncio
import os
from typing import Optional, List

from filters import Filters

class BotMessagesEvents(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.Filters = Filters(bot)
        super().__init__()
    

    @commands.Cog.listener()
    async def on_message(self, ctx):
        rows = interactor.read_data(data.afkConn, "*", "afk")
        
        for row in rows:
            if ctx.author.id in row:
                embed = discord.Embed(title="", color=0x3498eb)
                embed.add_field(name="Unmarked as afk", value="You are no longer marked as afk")
                message = await ctx.channel.send(embed=embed)
                await message.delete(delay=5)
                interactor.delete_data(data.afkConn, "afk", "user_id", str(ctx.author.id))

        task = asyncio.create_task(self.Filters.filter(ctx))
        spamTask = asyncio.create_task(self.Filters.spamFilter(ctx))
        sProcCommands = await spamTask

        mentions = ctx.mentions
        for member in mentions:
            for row in rows:
                if member.id in row:
                    embed = discord.Embed(title="", color=0x3498eb)
                    reason = interactor.read_data(data.afkConn, "*", "afk", "user_id", str(member.id))[0][2]
                    embed.add_field(name=f"Marked as afk", value=f"<@{member.id}> is marked as afk", inline=False)
                    embed.add_field(name="Reason", value=f"{reason}")
                    message = await ctx.channel.send(embed=embed, allowed_mentions=discord.AllowedMentions(everyone=False, users=False, roles=False))
                    await message.delete(delay=30)

        procCommands = await task

        if procCommands and sProcCommands:
            await self.bot.process_commands(ctx)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if (before.author.id == self.bot.user.id) or (before.author.bot):
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

        channel = data.getLoggingChannel()
        await channel.send(embed=embed, files=files)

        if os.path.exists(f"{before.author.name}BeforeMessage.txt"):
            os.remove(f"{before.author.name}BeforeMessage.txt")
        if os.path.exists(f"{after.author.name}BeforeMessage.txt"):
            os.remove(f"{after.author.name}BeforeMessage.txt")

        asyncio.create_task(self.Filters.filter(after))

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):  # sourcery no-metrics
        try:
            guildId = payload.guild_id
        except AttributeError:
            return
        else:
            if payload.channel_id == data.getLoggingChannel():
                return
        try:
            if (payload.cached_message.author.id == self.bot.user.id) or (payload.cached_message.author.bot):
                return
        except AttributeError:
            pass


        if payload.cached_message is None:
            guild = self.bot.get_guild(payload.guild_id)
            embed = discord.Embed(title=f"{guild.name}", color=0xdb2421)
            embed.add_field(name=f":wastebasket:", value=f"Message sent in <#{payload.channel_id}> deleted.")
            embed.timestamp = dt.datetime.utcnow()
            embed.set_footer(text=f"Message ID:{payload.message_id}")
            channel = data.getLoggingChannel()
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
            channel = data.getLoggingChannel()
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
            channel = data.getLoggingChannel()
            if len(files) > 10:
                await channel.send(embed=embed, files=files[0:10])
                await channel.send(files=files[10:])
            else:
                await channel.send(embed=embed, files=files)

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload:discord.RawBulkMessageDeleteEvent): # sourcery no-metrics
        try:
            guild:Optional[discord.Guild] = self.bot.get_guild(payload.guild_id)
        except AttributeError:
            return
        if guild is None:
            return
        if payload.cached_messages is None:
            embed = discord.Embed(title=f"{guild.name}", color=0xdb2421)
            embed.add_field(name=f":wastebasket:", value=f"Messages sent in <#{payload.channel_id}> deleted.")
            embed.timestamp = dt.datetime.utcnow()
            embed.set_footer(text=f"Message ID:{payload.message_id}")
            channel = data.getLoggingChannel()
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
                channel = data.getLoggingChannel()
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
                channel = data.getLoggingChannel()
                if len(files) > 10:
                    await channel.send(embed=embed, files=files[0:10])
                    await channel.send(files=files[10:])
                else:
                    await channel.send(embed=embed, files=files)


