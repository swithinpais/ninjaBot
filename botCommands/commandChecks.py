from discord.ext import commands
from data import data

def isBotCmdChannel():
    async def predicate(ctx) -> bool:
        return ctx.channel.id in data.getBotCmdChannels()
    return commands.check(predicate)

def isSbBotCmdChannel():
    async def predicate(ctx) -> bool:
        return ctx.channel.id in data.getSbBotCmdChannels()
    return commands.check(predicate)

def isModerator():
    async def predicate(ctx) -> bool:
        for role in ctx.author.roles:
            if role.id == data.getModRole():
                return True
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)

def isAdministrator():
    async def predicate(ctx) -> bool:
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)