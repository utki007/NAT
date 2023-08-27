import datetime
from typing import List, Union

import discord
import time as t
from discord import Interaction, app_commands
from discord.ext import commands

from utils.embeds import get_invisible_embed

@app_commands.guild_only()
class server(commands.GroupCog, name="server", description="Run server based commands"):
	def __init__(self, bot):
		self.bot = bot
		
	lockdown_command = app_commands.Group(name="lockdown", description="Manage Server Lockdown Protocols 🔒")

	async def lockdown_profiles_list(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
		current_panel = await self.bot.lockdown.find(interaction.guild.id)
		if not current_panel:
			return []
		
		choice = [
			app_commands.Choice(name=name, value=name)
			for name in current_panel['lockdown_profiles'] if current.lower() in name.lower()
		]
		return choice

	@lockdown_command.command(name="start", description="Begin lockdown", extras={'example': '/'})
	@app_commands.autocomplete(name=lockdown_profiles_list)
	@app_commands.describe(name = "Which Lockdown Protocol to start?")
	@app_commands.checks.has_permissions(manage_messages=True)
	async def lockdown_start(self, interaction:  discord.Interaction, name: str):
		# progress = await get_invisible_embed(content = f"<:tgk_activeDevelopment:1088434070666612806> **|** This command is under development...")
		# return await interaction.response.send_message(embed=progress, ephemeral=False)
		data = await self.bot.lockdown.find(interaction.guild.id)

		if data is None:
			return await interaction.response.send_message(embed=await get_invisible_embed(f'You have not created any lockdown profiles yet!'), ephemeral=True)

		if not data and name not in data['lockdown_profiles']:
			warning = discord.Embed(
				color=0xffd300,
				title=f"> Lockdown Protocol: **`{name}`** does not exist. \n> Use </serversettings:1068960308800008253> to create it.")
			warning.set_thumbnail(url=f"https://cdn.discordapp.com/emojis/845404773360205854.gif?size=128&quality=lossless")
			return await interaction.response.send_message(embed=warning, ephemeral=True)
		
		profile = data[name]
		channel_and_role = profile['channel_and_role']
		embed = profile['lock_embed']

		if len(channel_and_role.keys())<1:
			warning = discord.Embed(
				color=0xffd300,
				title=f"> Channel list is empty.\n> Use </serversettings:1068960308800008253> to add them.")
			warning.set_thumbnail(url=f"https://cdn.discordapp.com/emojis/845404773360205854.gif?size=128&quality=lossless")
			return await interaction.response.send_message(embed=warning, ephemeral=True)

		await interaction.response.defer(ephemeral = False)
		start = t.time()
		lockdown_embed = discord.Embed(
				title=f"{embed['title']}",
				description=embed['description'],
				color=0xDA2A2A,
				timestamp=datetime.datetime.utcnow()
		)
		if interaction.guild.icon:
			lockdown_embed.set_footer(text=f"{interaction.guild.name}", icon_url=interaction.guild.icon.url)
		else:
			lockdown_embed.set_thumbnail(text=f"{interaction.guild.name}")
		if embed['thumbnail']:
			lockdown_embed.set_thumbnail(url=embed['thumbnail'])
			
		for channel_id in channel_and_role:
			channel = interaction.guild.get_channel(int(channel_id))
			roleIds = [int(role_ids) for role_ids in channel_and_role[channel_id].split(" ") if role_ids != '' and role_ids not in ["everyone"]]
			roleIds = [discord.utils.get(interaction.guild.roles, id=id) for id in roleIds]
			roles = [role for role in roleIds if role != None]
			if channel and roles:
				for role in roles:
					overwrite = channel.overwrites_for(role)
					overwrite.send_messages = False

					await channel.set_permissions(role, overwrite=overwrite)
				await channel.send(embed=lockdown_embed)
		end = t.time()
		embed = discord.Embed(
			color=0x43b581, description=f'<a:nat_check:1010969401379536958> **|** Lockdown protocol `{name}` completed in: {round((end - start), 2)} s.')
			
		await interaction.edit_original_response(
			embed=embed
		)

	@lockdown_command.command(name="end", description="end lockdown", extras={'example': '/'})
	@app_commands.autocomplete(name=lockdown_profiles_list)
	@app_commands.describe(name = "Which Lockdown Protocol to end?")
	@app_commands.checks.has_permissions(manage_messages=True)
	async def lockdown_end(self, interaction:  discord.Interaction, name: str):
		# progress = await get_invisible_embed(content = f"<:tgk_activeDevelopment:1088434070666612806> **|** This command is under development...")
		# return await interaction.response.send_message(embed=progress, ephemeral=False)
		data = await self.bot.lockdown.find(interaction.guild.id)
		if not data and name not in data['lockdown_profiles']:
			warning = discord.Embed(
				color=0xffd300,
				title=f"> The profile named **`{name}`** does not exist. Are you trying to Create a profile? \n> Use </settings lockdown create:1063097729426919507>.")
			warning.set_thumbnail(url=f"https://cdn.discordapp.com/emojis/845404773360205854.gif?size=128&quality=lossless")
			return await interaction.response.send_message(embed=warning, ephemeral=True)
		
		profile = data[name]
		channel_and_role = profile['channel_and_role']
		embed = profile['unlock_embed']

		if len(channel_and_role.keys())<1:
			warning = discord.Embed(
				color=0xffd300,
				title=f"> Channel list is empty.\n> Use </settings lockdown modify:1063097729426919507> to add them.")
			warning.set_thumbnail(url=f"https://cdn.discordapp.com/emojis/845404773360205854.gif?size=128&quality=lossless")
			return await interaction.response.send_message(embed=warning, ephemeral=True)

		await interaction.response.defer(ephemeral = False)
		start = t.time()
		lockdown_embed = discord.Embed(
				title=f"{embed['title']}",
				description=embed['description'],
				color=0x78AB46,
				timestamp=datetime.datetime.utcnow()
		)
		if interaction.guild.icon:
			lockdown_embed.set_footer(text=f"{interaction.guild.name}", icon_url=interaction.guild.icon.url)
		else:
			lockdown_embed.set_thumbnail(text=f"{interaction.guild.name}")
		if embed['thumbnail']:
			lockdown_embed.set_thumbnail(url=embed['thumbnail'])
			
		for channel_id in channel_and_role:
			channel = interaction.guild.get_channel(int(channel_id))
			roleIds = [int(role_ids) for role_ids in channel_and_role[channel_id].split(" ") if role_ids != '' and role_ids not in ["everyone"]]
			roleIds = [discord.utils.get(interaction.guild.roles, id=id) for id in roleIds]
			roles = [role for role in roleIds if role != None]
			if channel and roles:
				overwrite = channel.overwrites_for(interaction.guild.default_role)
				for role in roles:
					overwrite = channel.overwrites_for(role)
					overwrite.send_messages = None

					await channel.set_permissions(role, overwrite=overwrite)
				await channel.send(embed=lockdown_embed)
		end = t.time()
		embed = discord.Embed(
			color=0x43b581, description=f'<a:nat_check:1010969401379536958> **|** Unlocked  protocol   `{name}` in: {round((end - start), 2)} s.')
			
		await interaction.edit_original_response(
			embed=embed
		)


async def setup(bot):
	await bot.add_cog(
		server(bot),
		# guilds=[discord.Object(999551299286732871)]
	)
	print(f"loaded server cog")
