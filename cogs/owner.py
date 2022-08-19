import discord
from discord import app_commands
from discord.ext import commands

class owner(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.__class__.__name__} Cog has been loaded\n-----")
    
    @app_commands.command(name="get-logs", description="Get the logs of bot")
    @app_commands.checks.has_permissions(administrator=True)
    async def get_logs(self, interaction: discord.Interaction):
        if interaction.user.id not in self.bot.owner_ids:
            await interaction.response.send_message("You do not have permission to use this command.")
            return
        await interaction.response.send_message(file=discord.File("./bot.log", filename="discord.log"))
        
async def setup(bot):
    await bot.add_cog(
        owner(bot),
        guilds = [discord.Object(999551299286732871)]
    )