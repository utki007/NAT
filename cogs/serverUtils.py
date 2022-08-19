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
        messaeg = await interaction.response.send_message("Pong! 🏓")
        
        await interaction.edit_original_response(
            content=f"Pong! **`{round(self.bot.latency * 1000)}ms`**",
        )
        
        await interaction.followup.send(content=messaeg.id)
        
async def setup(bot):
    await bot.add_cog(serverUtils(bot))