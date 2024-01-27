import discord
import contextlib
import io
import datetime
from traceback import format_exception
import textwrap

from humanfriendly import format_timespan
from utils.embeds import get_error_embed, get_success_embed
from utils.views.paginator import Contex_Paginator
from discord import app_commands
from discord.ext import commands
from utils.functions import clean_code
from utils.checks import App_commands_Checks
from utils.db import Document
from utils.views.confirm import Confirm
from utils.transformers import TimeConverter
from typing import List
import os

class owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.alerts = Document(bot.db, "alerts")
    
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

    dev = app_commands.Group(name="dev", description="Developer commands")
    alert = app_commands.Group(name="alert", description="Alert commands", parent=dev)

    async def alert_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        current_alert = await interaction.client.alerts.get_all({"active": True})
        # if current_alert is None:
        #     return
        # ids = [current_alert['_id'] for current_alert in current_alert]
        return [
            app_commands.Choice(name=alert['_id'], value=alert['_id'])
            for alert in current_alert if current.lower() in alert['_id'].lower()
        ]

    @commands.Cog.listener()
    async def on_ready(self):
        alert = await self.bot.alerts.find({"active": True})
        if alert is not None:
            self.bot.current_alert = alert

        print(f"{self.__class__.__name__} Cog has been loaded\n-----")

    @dev.command(name="get-logs", description="Get the logs of bot")
    @App_commands_Checks.is_owner()
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
    
    @dev.command(name="reload", description="Reload a cog")
    @app_commands.default_permissions(administrator=True)
    @app_commands.autocomplete(cog=cog_autocomplete)
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
    
    @dev.command(name="add-premium", description="Add premium to a guild")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(guild_id="The guild id to add premium to", time="The time to add premium for")
    async def add_premium(self, interaction: discord.Interaction, guild_id: str, time: app_commands.Transform[int | str, TimeConverter]="permanent"):
        if interaction.user.id not in self.bot.owner_ids:
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return
        
        try:
            guild = await interaction.client.fetch_guild(int(guild_id))
        except:
            await interaction.response.send_message("Invalid guild id/I am not in that guild", ephemeral=True)
            return

        guild_data = await self.bot.premium.find({'_id': int(guild_id)})
        if not guild_data:
            guild_data = {
                '_id': int(guild.id),
                'premium': True,
                'duration': (datetime.datetime.now(pytz.utc) + datetime.timedelta(seconds=time)) if time != "permanent" else "permeant",
                'premium_by': interaction.user.id,
                'payout_limit': 40
            }
            await self.bot.premium.insert(guild_data)
        else:
            if guild_data['duration'] == 'permeant':
                await interaction.response.send_message("This guild is permanently premium!", ephemeral=True)
                return

            guild_data['premium'] = True
            guild_data['duration'] += datetime.timedelta(seconds=time)
            guild_data['premium_by'] = interaction.user.id
            guild_data['payout_limit'] = 40
            await self.bot.premium.update(guild_data)
        
        preimin_duration = (guild_data['duration'] - datetime.datetime.now(pytz.utc)).total_seconds() if guild_data['duration'] != 'permeant' else "permeant"

        await interaction.response.send_message(f"{guild.name} is now premium for duration of {format_timespan(preimin_duration) if guild_data['duration'] != 'permeant' else 'permeant'}", ephemeral=True)

    @dev.command(name="sync", description="Syncs a guild/gobal command")
    async def sync(self, interaction: discord.Interaction, guild_id: str=None):
        if interaction.user.id not in self.bot.owner_ids:
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return
        if guild_id is None:
            await interaction.response.send_message(embed=discord.Embed(description="Syncing global commands...", color=2829617))
            await interaction.client.tree.sync()
            await interaction.edit_original_response(embed=discord.Embed(description="Successfully synced global commands", color=2829617))
        else:
            if guild_id == "*":
                guild = interaction.guild
            else:
                guild = await interaction.client.fetch_guild(int(guild_id))
                if guild is None:
                    return await interaction.response.send_message(embed=discord.Embed(description="Invalid guild id", color=2829617))
            await interaction.response.send_message(embed=discord.Embed(description=f"Syncing guild commands for `{guild.name}`...", color=2829617))
            await interaction.client.tree.sync(guild=guild)
            await interaction.edit_original_response(embed=discord.Embed(description=f"Successfully synced guild commands for `{guild.name}`", color=2829617))

    @dev.command(name="member_lock_bypass", description="Bypass member lock")
    @app_commands.default_permissions(administrator=True)
    async def member_lock_bypass(self, interaction: discord.Interaction, guild_id: str):
        if interaction.user.id not in self.bot.owner_ids:
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return
        try:
            guild_id  = int(guild_id)
        except: 
            return await interaction.response.send_message(embed=discord.Embed(description="Invalid guild id", color=2829617))
        data = await self.bot.config.find(interaction.client.user.id)
        if not data:
            await interaction.response.send_message("Db error", ephemeral=True)
            return
        if guild_id in data['member_lock_bypass']:
            await interaction.response.send_message(embed=discord.Embed(description="This guild is already bypassed", color=2829617))
            return
        data['member_lock_bypass'].append(guild_id)
        await self.bot.config.update(data)
        await interaction.response.send_message(embed=discord.Embed(description="Successfully bypassed", color=2829617))
    #Note: This is a test command

    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction: discord.Interaction, command: app_commands.Command | app_commands.ContextMenu):
        current_alert = await self.bot.alerts.find({"active": True})
        if current_alert is None:
            return
        if command.parent is not None:
            if command.parent.name == "dev" or "alert":
                return
            
        if interaction.user.id in current_alert['viewed_by']:
            return
        current_alert['viewed_by'].append(interaction.user.id)
        current_alert['view_count'] += 1

        embed = discord.Embed(title=current_alert['_id'], description=current_alert['message'], color=discord.Color.red())
        embed.set_footer(text=f"Viewed by {current_alert['view_count']} users")

        await self.bot.alerts.update(current_alert)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @alert.command(name="add", description="Add an alert")
    @app_commands.describe(message="The message to send when the alert is triggered", title="title of the alert")
    async def _add(self, interaction: discord.Interaction, title: str,message: str):
        if interaction.user.id not in interaction.client.owner_ids:
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return
        
        embed = discord.Embed(title=title, description=message, color=discord.Color.red())
        view = Confirm(interaction.user, 60)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

        await view.wait()
        if view.value is None or view.value is False:
            await interaction.delete_original_response()
            return
        old_alert = await self.bot.alerts.find({"active": True})
        if old_alert is not None:
            old_alert['active'] = False
            await self.bot.alerts.update(old_alert)

        data = {
            "_id": title,
            "message": message,
            "view_count": 0,
            "made_by": interaction.user.id, 
            "viewed_by": [],
            "active": True,
        }
        
        await self.bot.alerts.insert(data)
        await interaction.edit_original_response(content="Alert has been added.")

    @alert.command(name="remove", description="Add an alert")
    @app_commands.describe(alert="The alert to remove")
    @app_commands.autocomplete(alert=alert_autocomplete)
    async def _remove(self, interaction: discord.Interaction, alert: str):
        if interaction.user.id not in interaction.client.owner_ids:
            return await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        
        old_alert = await self.bot.alerts.find({"_id": alert})
        if old_alert is not None:
            old_alert['active'] = False
            await interaction.client.alerts.upsert(old_alert)
            await interaction.response.send_message(embed = await get_success_embed("Alert has been removed."))
        else:
            await interaction.response.send_message(embed = await get_error_embed("Alert not found in db."))

async def setup(bot):
    await bot.add_cog(
        owner(bot),
        guilds = [discord.Object(785839283847954433), discord.Object(999551299286732871)]
    )