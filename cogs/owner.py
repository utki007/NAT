import discord
from discord import app_commands
from discord.ext import commands

class owner(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.__class__.__name__} Cog has been loaded\n-----")
    
    @app_commands.command(name="pingpro", description="Ping pong! 🏓")
    @app_commands.checks.has_permissions(administrator=True)
    async def ping(self, interaction:  discord.Interaction):
        await interaction.response.send_message(
            f"Pong! 🏓 **`{round(self.bot.latency * 1000)}ms`**",
        )
        
async def setup(bot):
    await bot.add_cog(
        owner(bot),
        guilds = [discord.Object(999551299286732871)]
    )