import discord
from discord.ext import commands
from typing import List, Dict, Union, TypedDict
from discord import app_commands, Interaction
from utils.db import Document
from ui.settings.grinder import GrinderConfigPanel
from utils.types import GrinderConfig, GrinderProfile
from utils.embeds import get_formated_embed
from utils.dank import DonationsInfo, get_doantion_from_message

class GrinderDB:
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.mongo['Grinder']
        self.config: Document = Document(self.db, "config")
        self.payments: Document = Document(self.db, "payments")
    
    async def get_config(self, guild: int) -> GrinderConfig:
        config: GrinderConfig = await self.config.find(guild)
        if not config:
            config = {
                "_id": guild,
                "payment_channel": 0,
                "manager_roles": [],
                "max_profiles": 5,
                "profile": {}
            }
            await self.config.insert(config)
        return config
    
    async def update_config(self, guild: int, data: GrinderConfig):
        await self.config.update(guild, data)

    
    async def get_payment(self, guild: int, user: int):
        payment: int = await self.payments.find({"guild": guild, "user": user})
        return payment

    async def get_config_embed(self, guild: discord.Guild, config: GrinderConfig) -> discord.Embed:
        embed = discord.Embed(color=0x2b2d31, description="")
        arguments = ["Payment Channel", "Manager Roles", "Max Profiles", "Profiles"]
        formated_args = await get_formated_embed(arguments)
        
        embed.description += "<:tgk_cc:1150394902585290854> `Grinder System`"
        embed.description += "\n\n"
        embed.description += f"{formated_args['Payment Channel']}" + f"{'<#' + str(config['payment_channel']) + '>' if config['payment_channel'] else 'None'}\n"
        embed.description += f"{formated_args['Manager Roles']}" + f"{','.join([f'<@&{role}>' for role in config['manager_roles']]) if len(config['manager_roles']) > 1 else 'None'}\n"
        embed.description += f"{formated_args['Max Profiles']}" + str(config['max_profiles']) + "\n"
        embed.description += f"{formated_args['Profiles']}" + f"{len(config['profile'])}/{config['max_profiles']}\n\n"
        embed.description += "<:tgk_hint:1206282482744561744> Use buttons below to changes the settings"
        return embed

class Grinders(commands.GroupCog, name="grinders"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.backend = GrinderDB(bot)
        self.bot.grinder = self.backend

    @app_commands.command(name="setup", description="Setup the grinder system")
    async def setup(self, interaction: Interaction):
        config: GrinderConfig = await self.backend.get_config(interaction.guild.id)
        view = GrinderConfigPanel(config, interaction.user, interaction.message)
        await interaction.response.send_message(embed=await self.backend.get_config_embed(interaction.guild, config), view=view)
        view.message = await interaction.original_response()

    @app_commands.command(name="check-dono", description="Check the donation of a user")
    @app_commands.describe(message="The message that contains the donation")
    async def check_dono(self, interaction: Interaction, message: str):
        try:
            message = await interaction.channel.fetch_message(int(message))
        except discord.HTTPException:
            await interaction.response.send_message("Message not found", ephemeral=True)
            return
        
        donations = await get_doantion_from_message(message)
        await interaction.response.send_message(str(donations), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Grinders(bot), guilds=[discord.Object(999551299286732871)])
