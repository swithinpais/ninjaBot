from discord.ext import commands
from data import data

def isBotCmdChannel():
    async def predicate(ctx):
        return ctx.channel.id in data.getBotCmdChannels()
    return commands.check(predicate)

def isSbBotCmdChannel():
    async def predicate(ctx):
        return ctx.channel.id in data.getSbBotCmdChannels()
    return commands.check(predicate)