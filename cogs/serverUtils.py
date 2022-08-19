import discord
from discord import app_commands
from discord.ext import commands

class serverUtils(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.__class__.__name__} Cog has been loaded\n-----")
    
    
    @app_commands.command(name="ping", description="Ping pong! 🏓")
    @app_commands.checks.cooldown(1, 30, key=lambda i:(i.guild_id, i.user.id))
    async def ping(self, interaction:  discord.Interaction):
        
        await interaction.response.defer()

        await interaction.followup.send("Pong! 🏓")
        
        await interaction.edit_original_response(
            content=f"Pong! **`{round(self.bot.latency * 1000)}ms`**",
        )

    @ping.error
    async def ping_error(self, interaction, error):
        if isinstance(error, app_commands.CommandOnCooldown):
            # If the command is currently on cooldown trip this
            m, s = divmod(error.retry_after, 60)
            h, m = divmod(m, 60)
            if int(h) == 0 and int(m) == 0:
                await interaction.response.send_message(f"The command is under a cooldown of **{int(s)} seconds** to prevent abuse!")
            elif int(h) == 0 and int(m) != 0:
                await interaction.response.send_message(
                    f"The command is under a cooldown of **{int(m)} minutes and {int(s)} seconds** to prevent abuse!"
                )
            else:
                await interaction.response.send_message(
                    f"The command is under a cooldown of **{int(h)} hours, {int(m)} minutes and {int(s)} seconds** to prevent abuse!"
                )
        else:
            #raise error
            embed = discord.Embed(color=0xE74C3C, 
                description=f"<:tgk_warning:840638147838738432> | Error: `{error}`")
            await interaction.response.send_message(embed=embed)
        
async def setup(bot):
    await bot.add_cog(serverUtils(bot))