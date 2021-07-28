import discord
from discord.ext import commands
from mainFuncs import errorLogger

class BotErrorEvents(commands.Cog):

    def __init__(self, bot) -> None:
        self.bot = bot
        super().__init__()

    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        errorMessage = errorLogger(event)
        print(errorMessage)
        owner = self.bot.get_user(self.bot.owner_id)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.channel.send("This command is only available in a server", reference=ctx.message, allowed_mentions=discord.AllowedMentions(replied_user=False))
            return

        if isinstance(error, commands.CommandOnCooldown):
            print(error)
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