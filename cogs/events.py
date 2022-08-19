import discord
from discord import app_commands
from discord.ext import commands

class events(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.__class__.__name__} Cog has been loaded\n-----")
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):

        if isinstance(error, commands.CommandOnCooldown):
            # If the command is currently on cooldown trip this
            m, s = divmod(error.retry_after, 60)
            h, m = divmod(m, 60)
            if int(h) == 0 and int(m) == 0:
                await ctx.send(f"The command is under a cooldown of **{int(s)} seconds** to prevent abuse!")
            elif int(h) == 0 and int(m) != 0:
                await ctx.send(
                    f"The command is under a cooldown of **{int(m)} minutes and {int(s)} seconds** to prevent abuse!"
                )
            else:
                await ctx.send(
                    f"The command is under a cooldown of **{int(h)} hours, {int(m)} minutes and {int(s)} seconds** to prevent abuse!"
                )
        elif isinstance(error, commands.CheckFailure):
            # If the command has failed a check, trip this
            await ctx.send("Hey! You lack permission to use this command.")

        elif isinstance(error, commands.CommandInvokeError):
            return
            
        elif isinstance(error, commands.CommandNotFound):
            return

        else:
            #raise error
            embed = discord.Embed(color=0xE74C3C, 
                description=f"<:tgk_warning:840638147838738432> | Error: `{error}`")
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(events(bot))