import discord
from discord import app_commands, Interaction
from discord.ext import commands
from discord.app_commands import Group
from utils.db import Document
from typing import List
from utils.views import confirm
from utils.views import dono
class ServerSettings(commands.GroupCog, name="serversettings"):
    def __init__(self, bot):
        self.bot = bot
        self.bot.donation_config = Document(self.bot.db, "donation_config")

    async def donation_auto_complete(self, interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
        data = await self.bot.donation_config.find(interaction.guild.id)
        if data is None or len(data['donations'].keys()) == 0:
            return [app_commands.Choice(name="No donation system found", value="no system found")]
        choices = [ 
            app_commands.Choice(name=donation, value=donation)
            for donation in data['donations'].keys() if current.lower() in donation.lower()
        ]
        return choices[:24]
            

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.__class__.__name__} Cog has been loaded")
    
    donation = Group(name="donation", description="Configure donation settings for the server")

    @donation.command(name="create", description="Create new separate donation for event or something")
    @app_commands.describe(name="The name of the donations", loggin_channel='The channel where donation requests will be logged', trade_channel='The channel where donation requests will be traded', manager_role="Role that can accept or decline donation requests")
    @app_commands.checks.has_permissions(administrator=True)
    async def doantion_create(self, interaction: Interaction, name: str, loggin_channel: discord.TextChannel, trade_channel: discord.TextChannel, manager_role: discord.Role):
        data = await self.bot.donation_config.find(interaction.guild.id)
        if data is None:
            data = {
                '_id': interaction.guild.id,
                'guild_id': interaction.guild.id,
                'donations': {},
                'donation_system_limit': 5
            }
            await self.bot.donation_config.insert(data)
        if len(data['donations'].keys()) >= data['donation_system_limit']:
            return await interaction.response.send_message("You have reached the limit of donation systems for this server. Please delete one of the donation systems to create a new one.")
        data['donations'][name] = {'_id': name, 'loggin_channel': loggin_channel.id, 'trade_channel': trade_channel.id, 'manager_role': manager_role.id, 'created_by': interaction.user.id, 'embed': {}}
        await self.bot.donation_config.update(data)
        await interaction.response.send_message(f"Successfully created donation system {name}!")
    
    @donation.command(name="delete", description="Delete donation system")
    @app_commands.describe(name="The name of the donation system")
    @app_commands.autocomplete(name=donation_auto_complete)
    @app_commands.checks.has_permissions(administrator=True)
    async def donation_delete(self, interaction: Interaction, name: str):
        if name =="no system found":
            return await interaction.response.send_message("No donation system found", ephemeral=True)
        data = await self.bot.donation_config.find(interaction.guild.id)
        if data is None:
            return await interaction.response.send_message("No donation system found", ephemeral=True)
        if name not in data['donations'].keys():
            return await interaction.response.send_message("No donation system found", ephemeral=True)
        
        embed = discord.Embed(description=f"Are you sure you want to delete this donation system?\n**Name:** {name}\n**Loggin Channel:** <#{data['donations'][name]['loggin_channel']}>\n**Trade Channel:** <#{data['donations'][name]['trade_channel']}>\n**Manager Role:** <@&{data['donations'][name]['manager_role']}>", color=discord.Color.red())
        view = confirm.Confirm(interaction.user, timeout=60)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_message()
        await view.wait()
        if view.value is True:
            del data['donations'][name]
            await self.bot.donation_config.update(data)
            await view.interaction.response.send_message(f"Successfully deleted donation system {name}!", ephemeral=True)
        if view.value is False:
            await view.interaction.response.send_message(f"Cancelled deletion of donation system {name}!", ephemeral=True)

    @donation.command(name="set-embed", description="Set the embed for donation system")
    @app_commands.describe(name="The name of the donation system")
    @app_commands.autocomplete(name=donation_auto_complete)
    @app_commands.checks.has_permissions(administrator=True)
    async def donation_set_embed(self, interaction: Interaction, name: str):
        data = await self.bot.donation_config.find(interaction.guild.id)
        if data is None:
            return await interaction.response.send_message("No donation system found", ephemeral=True)
        if name not in data['donations'].keys():
            return await interaction.response.send_message("No donation system found", ephemeral=True)
        view = dono.DonationEmbed(interaction, data, name)
        await interaction.response.send_modal(view)


async def setup(bot):
    await bot.add_cog(ServerSettings(bot))