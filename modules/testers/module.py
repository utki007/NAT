import discord
from discord.ext import commands
from discord import app_commands
from utils.db import Document
from utils.views.paginator import Paginator
from typing import TypedDict


class Testers(TypedDict):
    _id: int
    guild: int
    added_by: int
    bug_reported: int
    bug_approved: int    

class Testers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.release_type = "private"
        self.testers = Document(bot.db, "testers")

    testers = app_commands.Group(name="testers", description="Testers commands")
    admin = app_commands.Group(name="admin", description="Admin commands", parent=testers)

    @admin.command(name="add", description="Add a tester")
    @app_commands.describe(user='User to add', guild='Users test server')
    async def add_tester(self, interaction: discord.Interaction, user: discord.Member, guild: str):
        user_data = await self.testers.find(user.id)
        if user_data:
            await interaction.response.send_message("User is already a tester to change guild use /tester guild", ephemeral=True)
            return
        try:
            guild = await self.bot.fetch_guild(guild)   
        except discord.errors.NotFound:
            await interaction.response.send_message("Guild not found", ephemeral=True)
            return
        
        user_data = {
            '_id': user.id,
            'guild': guild.id,
            'added_by': interaction.user.id,
            'bug_reported': 0,
            'bug_approved': 0
        }
        await self.testers.insert(user_data)
        await interaction.response.send_message(f"Added {user.mention} as a tester with guild {guild.name}", ephemeral=True)
        await interaction.channel.send(f"Welcome {user.mention} to the testers team new your guild {guild.name} will soon have a new test commands if they are available.")

    @admin.command(name="remove", description="Remove a tester")
    @app_commands.describe(user='User to remove')
    async def remove_tester(self, interaction: discord.Interaction, user: discord.Member):
        user_data = await self.testers.find(user.id)
        if not user_data:
            await interaction.response.send_message("User is not a tester", ephemeral=True)
            return
        await self.testers.delete(user.id)
        await interaction.response.send_message(f"Removed {user.mention} as a tester", ephemeral=True)

    @admin.command(name="guild", description="Change the guild of a tester")
    @app_commands.describe(user='User to change', guild='Users test server')
    async def change_guild(self, interaction: discord.Interaction, user: discord.Member, guild: str):
        user_data = await self.testers.find(user.id)
        if not user_data:
            await interaction.response.send_message("User is not a tester", ephemeral=True)
            return
        try:
            guild: discord.Guild = await self.bot.fetch_guild(guild)   
        except discord.errors.NotFound:
            await interaction.response.send_message("Guild not found", ephemeral=True)
            return
        await self.testers.update(user.id, {'guild': guild.id})
        await interaction.response.send_message(f"Changed {user.mention} guild to {guild.name}", ephemeral=True)

    @admin.command(name="sync-guilds", description="Sync all testers guilds")
    async def sync_guilds(self, interaction: discord.Interaction):
        testers = await self.testers.find_all()
        guilds: list[discord.Guild] = []
        for tester in testers:
            guild = self.bot.get_guild(tester['guild'])
            if guild:
                guilds.append(guild)

        embed = discord.Embed(title="Syncing Testers Guilds", color=discord.Color.blurple(), description="")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        for guild in guilds:
            await self.bot.tree.sync(guild=guild)
            embed.description += f"<a:nat_check:1010969401379536958> Synced {guild.name}\n"
            await interaction.edit_original_response(content=None, embed=embed)
        embed = discord.Embed(title="Syncing Testers Guilds", color=discord.Color.blurple(), description=f"All guilds synced {len(guilds)}")

    @testers.command(name="list", description="List all testers")
    async def list_testers(self, interaction: discord.Interaction):
        testers = await self.testers.find_all()
        if not testers:
            await interaction.response.send_message("No testers found", ephemeral=True)
            return
        chunks = [testers[i:i+10] for i in range(0, len(testers), 10)]
        pages = []
        for chunk in chunks:
            embed = discord.Embed(title="Testers", color=discord.Color.blurple())
            for tester in chunk:
                user = self.bot.get_user(tester['_id'])
                guild = self.bot.get_guild(tester['guild'])
                embed.description += f"{user.mention} - {guild.name}\n"
            pages.append(embed)
        
        await Paginator(interaction=interaction, pages=pages,ephemeral=False).start(embeded=True, quick_navigation=False)

async def setup(bot):
    await bot.add_cog(Testers(bot), guilds=[discord.Object(999551299286732871)])