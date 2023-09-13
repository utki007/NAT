import discord
import contextlib
import io
from traceback import format_exception
import textwrap
from utils.views.paginator import Contex_Paginator
from discord import app_commands
from discord.ext import commands
from utils.functions import clean_code
from utils.checks import App_commands_Checks
from utils.db import Document
from typing import List
import os

class owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def cog_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        current_cogs = []
        for file in os.listdir("./cogs"):
            if file.endswith(".py") and not file.startswith("_"):
                current_cogs.append(file[:-3])
        new_options = [app_commands.Choice(name="reload all cogs", value="*")]
        for cog in current_cogs:
            if current.lower() in cog.lower():
                new_options.append(app_commands.Choice(name=cog, value=cog))                
        return new_options[:24]


    @app_commands.command(name="dev-sync", description="Syncs a guild/gobal command")
    async def sync(self, interaction: discord.Interaction, guild_id: str=None):
        if interaction.user.id not in self.bot.owner_ids:
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return
        if guild_id is None:
            await interaction.response.send_message(embed=discord.Embed(description="Syncing global commands...", color=interaction.client.default_color))
            await interaction.client.tree.sync()
            await interaction.edit_original_response(embed=discord.Embed(description="Successfully synced global commands", color=interaction.client.default_color))
        else:
            if guild_id == "*":
                guild = interaction.guild
            else:
                guild = await interaction.client.fetch_guild(int(guild_id))
                if guild is None:
                    return await interaction.response.send_message(embed=discord.Embed(description="Invalid guild id", color=interaction.client.default_color))
            await interaction.response.send_message(embed=discord.Embed(description=f"Syncing guild commands for `{guild.name}`...", color=interaction.client.default_color))
            await interaction.client.tree.sync(guild=guild)
            await interaction.edit_original_response(embed=discord.Embed(description=f"Successfully synced guild commands for `{guild.name}`", color=interaction.client.default_color))

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.__class__.__name__} Cog has been loaded\n-----")

    @app_commands.command(name="get-logs", description="Get the logs of bot")
    @App_commands_Checks.is_owner()
    @app_commands.guilds(999551299286732871)
    async def get_logs(self, interaction: discord.Interaction):
        if interaction.user.id not in self.bot.owner_ids:
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return
        await interaction.response.send_message(file=discord.File("./bot.log", filename="discord.log"))
    
    @commands.command(name="eval", description="Evaluate code")
    async def _eval(self, ctx, *,code):
        if ctx.author.id not in self.bot.owner_ids:
            raise commands.CheckFailure(ctx.message)

        code = clean_code(code)
        local_variables = {
            "discord": discord,
            "commands": commands,
            "bot": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message
        }

        stdout = io.StringIO()

        try:
            with contextlib.redirect_stdout(stdout):

                exec(
                    f"async def func():\n{textwrap.indent(code, '    ')}", local_variables,
                )
                obj = await local_variables["func"]()

                result = f"{stdout.getvalue()}\n-- {obj}\n"
                
        except Exception as e:
            result = "".join(format_exception(e,e,e.__traceback__))
        page = []
        for i in range(0, len(result), 2000):
            page.append(discord.Embed(description=f'```py\n{result[i:i + 2000]}\n```', color=ctx.author.color))
        
        custom_button = [
			discord.ui.Button(label="<", style=discord.ButtonStyle.gray),
			discord.ui.Button(label="◼", style=discord.ButtonStyle.gray),
			discord.ui.Button(label=">", style=discord.ButtonStyle.gray)
		]
        await Contex_Paginator(ctx, page, custom_button).start(embeded=True, quick_navigation=False)
    
    @app_commands.command(name="reload", description="Reload a cog")
    @app_commands.default_permissions(administrator=True)
    @app_commands.autocomplete(cog=cog_autocomplete)
    @app_commands.guilds(785839283847954433, 999551299286732871)
    async def reload(self, interaction: discord.Interaction, cog: str):
        if interaction.user.id not in self.bot.owner_ids:
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return
        if cog != "*":
            try:
                await self.bot.unload_extension(f"cogs.{cog}")
                await self.bot.load_extension(f"cogs.{cog}")
                embed = discord.Embed(description=f"{cog} has been reloaded.", color=discord.Color.green())
                await interaction.response.send_message(embed=embed)
            except Exception as e:
                embed = discord.Embed(description="Error **|** {}".format(e), color=0xFF0000)
                await interaction.response.send_message(embed=embed)
                return
        elif cog == "*":
            embed = discord.Embed(description="Relading Cogs..", color=discord.Color.green())
            await interaction.response.send_message(embed=embed)
            for module in os.listdir("./cogs"):
                if module.endswith(".py") and not module.startswith("_"):
                    try:
                        await self.bot.unload_extension(f"cogs.{module[:-3]}")
                        await self.bot.load_extension(f"cogs.{module[:-3]}")
                        embed.add_field(name=f"{module[:-3]}", value="Reloaded", inline=True)
                        await interaction.edit_original_response(embed=embed)
                    except Exception as e:
                        error = "".join(format_exception(e,e,e.__traceback__))
                        embed.add_field(name=f"{module}", value=f"Failure **|** {error[:100]}", inline=True)
                        await interaction.edit_original_response(embed=embed)
    

    @app_commands.command(name="sync", description="Syncs a guild/gobal command")
    async def sync(self, interaction: discord.Interaction, guild_id: str=None):
        if interaction.user.id not in self.bot.owner_ids:
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return
        if guild_id is None:
            await interaction.response.send_message(embed=discord.Embed(description="Syncing global commands...", color=interaction.client.default_color))
            await interaction.client.tree.sync()
            await interaction.edit_original_response(embed=discord.Embed(description="Successfully synced global commands", color=interaction.client.default_color))
        else:
            if guild_id == "*":
                guild = interaction.guild
            else:
                guild = await interaction.client.fetch_guild(int(guild_id))
                if guild is None:
                    return await interaction.response.send_message(embed=discord.Embed(description="Invalid guild id", color=interaction.client.default_color))
            await interaction.response.send_message(embed=discord.Embed(description=f"Syncing guild commands for `{guild.name}`...", color=interaction.client.default_color))
            await interaction.client.tree.sync(guild=guild)
            await interaction.edit_original_response(embed=discord.Embed(description=f"Successfully synced guild commands for `{guild.name}`", color=interaction.client.default_color))

async def setup(bot):
    await bot.add_cog(
        owner(bot),
        guilds = [discord.Object(785839283847954433), discord.Object(999551299286732871)]
    )