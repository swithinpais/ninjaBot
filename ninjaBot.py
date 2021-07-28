# VERSION 1.0.11
"""
This is the source code for Ninja Bot.
You are free to use it if you like.
Please dont make fun of me .-.
For legal reasons, I am not responsible for any bots that use this code or their actions.
"""

import discord
from discord.ext import commands

from data import data

from botCommands import fun, image, miscellaneous, moderation, skyblock

from botEvents import errorEvents, memberEvents, messageEvents, startup, voiceEvents

from botTasks import botTasks

intents = discord.Intents(guilds = True, members = True, bans = True, emojis = True, integrations = True, webhooks = True, invites = True, voice_states = True, presences = True, guild_messages = True, dm_messages = False, guild_reactions = True, dm_reactions = False, guild_typing = False, dm_typing = False)

client = commands.Bot(command_prefix = "?", owner_id=300669365563424770, intents=intents, max_messages=5000, case_insensitive=True)
client.remove_command("help")

allCogs = set({})
loadedCogs = []




@client.command(hidden=True)
async def dev(ctx): 
    isOwner = await client.is_owner(ctx.author)
    if isOwner:
        await ctx.channel.send("aaron this command works now shut up")
        return
    raise commands.CommandNotFound

@client.command(hidden=True)
async def errorlog(ctx):
    isOwner = await client.is_owner(ctx.author)
    if isOwner:
        await ctx.author.send("Error Log", file=discord.File("errorLog.txt"))
        return
    raise commands.CommandNotFound

@client.command(hidden=True)
async def close(ctx):
    if ctx.author.id == client.owner_id:
        await client.logout()
        return
    raise commands.CommandNotFound



# Commands
client.add_cog(moderation.Moderation(client, loadedCogs, allCogs))
client.add_cog(fun.Fun(client, loadedCogs, allCogs))
client.add_cog(image.Image(client, loadedCogs, allCogs))
client.add_cog(miscellaneous.Miscellaneous(client, loadedCogs, allCogs))
client.add_cog(skyblock.Skyblock(client, loadedCogs, allCogs))

# Events
client.add_cog(errorEvents.BotErrorEvents(client))
client.add_cog(memberEvents.BotMemberEvents(client))
client.add_cog(messageEvents.BotMessagesEvents(client))
client.add_cog(startup.Startup(client))
client.add_cog(voiceEvents.BotVoiceEvents(client))

Tasks = botTasks.BotTasks()
Tasks.start_all_tasks()


client.run(data.TOKEN)
