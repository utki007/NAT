import time as t
import discord
from discord import app_commands, Interaction
from discord.ext import commands
from utils.convertor import *
from typing import Union, List
from ui.channel import *
from utils.views.paginator import Paginator

class settings(commands.GroupCog, name="settings"):
	
	def __init__(self, bot):
		self.bot = bot

	lockdown_command = app_commands.Group(name="lockdown", description="Manage the antinuke role settings")
	
	async def is_me(interaction: discord.Interaction) -> bool:
		return interaction.user.id in [301657045248114690, 488614633670967307]
	
	async def is_admin(interaction: discord.Interaction) -> bool:
		return interaction.user.guild_permissions.administrator

	async def lockdown_profiles_list(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
		current_panel = await self.bot.lockdown.find(interaction.guild.id)
		if not current_panel:
			return []
		
		choice = [
			app_commands.Choice(name=name, value=name)
			for name in current_panel['lockdown_profiles'] if current.lower() in name.lower()
		]
		return choice
	
	async def lockdown_operation_list(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
				
		choice = [
			app_commands.Choice(name='edit', value='edit'),
			app_commands.Choice(name='delete', value='delete')
		]
		return choice

	@lockdown_command.command(name="create", description="Create lockdown profile", extras={'example': '/lockdown create'})
	@app_commands.check(is_admin)
	@app_commands.describe(name = "Enter Lockdown Profile Name")
	async def create(self, interaction: discord.Interaction, name: str):
		data = await self.bot.lockdown.find(interaction.guild.id)
		if not data:
			data = {"_id": interaction.guild.id, "lockdown_profiles": []}

		data['lockdown_profiles'].append(name)
		data[name] = {
			'creator': interaction.user.id, 
			'channel_and_role': {}, 
			'lock_embed':{
				'title':'Server Lockdown 🔒', 
				'description':f"This channel has been locked.\nRefrain from dm'ing staff, **__you are not muted.__**", 
				'thumbnail':'https://cdn.discordapp.com/emojis/830548561329782815.gif?v=1'
			}, 
			'unlock_embed':{
				'title':'Server Unlock 🔓', 
				'description':f"Channel has been unlocked.\nRefrain from asking us why it was previously locked.", 
				'thumbnail':'https://cdn.discordapp.com/emojis/802121702384730112.gif?v=1'
			}
		}

		await self.bot.lockdown.upsert(data)
		embed = discord.Embed(
				color=0x43b581, description=f'<a:nat_check:1010969401379536958> | Successfully created lockdown profile named: **`{name}`**!')
		await interaction.response.send_message(embed = embed)

	@lockdown_command.command(name="modify", description="Modify lockdown profile")
	@app_commands.check(is_admin)
	@app_commands.autocomplete(name=lockdown_profiles_list, operation=lockdown_operation_list)
	@app_commands.describe(name="Profile name", operation="Do you want to edit or delete?")
	async def modify(self, interaction: discord.Interaction,operation:str, name:str):
		if operation == 'edit':
			data = await self.bot.lockdown.find(interaction.guild.id)
			if not data and name not in data['lockdown_profiles']:
				warning = discord.Embed(
					color=0xffd300,
					title=f"> The profile named **`{name}`** does not exist. Are you trying to Create a profile? \n> Use </lockdown create:1062965049913778296> .")
				warning.set_thumbnail(url=f"https://cdn.discordapp.com/emojis/845404773360205854.gif?size=128&quality=lossless")
				return await interaction.response.send_message(embed=warning, ephemeral=True)
			try:
				panel = data[name]
			except KeyError:
				warning = discord.Embed(
					color=0xffd300,
					title=f"> The profile named **`{name}`** does not exist. Are you trying to Create a profile? \n> Use </lockdown create:1062965049913778296> .")
				warning.set_thumbnail(url=f"https://cdn.discordapp.com/emojis/845404773360205854.gif?size=128&quality=lossless")
				return await interaction.response.send_message(embed=warning, ephemeral=True)

			embed = discord.Embed(title=f"Lockdown Settings for Profile: {name}", color=discord.Color.blurple())
			
			lockdown_config = ""
			if len(panel['channel_and_role']) > 0:
				for channel_id in panel['channel_and_role']:
					channel = interaction.guild.get_channel(int(channel_id))
					roleIds = [int(role_ids) for role_ids in panel['channel_and_role'][channel_id].split(" ") if role_ids != '' and role_ids not in ["everyone"]]
					roleIds = [discord.utils.get(interaction.guild.roles, id=id) for id in roleIds]
					role = [role for role in roleIds if role != None]
					if channel:
						lockdown_config += f'{channel.mention} | {" + ".join([role.mention for role in role])}\n'
				if lockdown_config == "":
					lockdown_config = "None"
			else:
				lockdown_config = "None"

			embed.add_field(name="Channel Settings", value=f"{lockdown_config}", inline=False)

			lockmsg_config = f"**Title:** {panel['lock_embed']['title']}\n"
			lockmsg_config += f"**Thumbnail:** [**Click here**]({panel['lock_embed']['thumbnail']})\n" 
			lockmsg_config += f"**Description:**\n```{panel['lock_embed']['description']}```\n"
			
			embed.add_field(name="Embed Message for Lockdown", value=f"{lockmsg_config}", inline=False)

			unlockmsg_config = f"**Title:** {panel['unlock_embed']['title']}\n"
			unlockmsg_config += f"**Thumbnail:** [**Click here**]({panel['unlock_embed']['thumbnail']})\n"
			unlockmsg_config += f"**Description:**\n```{panel['unlock_embed']['description']}```\n"
			
			embed.add_field(name="Embed Message for Unlockdown", value=f"{unlockmsg_config}", inline=False)

			
			view = Lockdown_Config_Panel(interaction, data, name)
			await interaction.response.send_message(embed=embed, view=view)
			view.message = await interaction.original_response()
		elif operation == 'delete':
			data = await self.bot.lockdown.find(interaction.guild.id)
			if not data and name not in data['lockdown_profiles']:
				warning = discord.Embed(
					color=0xffd300,
					title=f"> The profile named **`{name}`** does not exist. Are you trying to Create a profile? \n> Use </lockdown create:1062965049913778296> .")
				warning.set_thumbnail(url=f"https://cdn.discordapp.com/emojis/845404773360205854.gif?size=128&quality=lossless")
				return await interaction.response.send_message(embed=warning, ephemeral=True)
			data['lockdown_profiles'].remove(name)
			await self.bot.lockdown.upsert(data)
			await self.bot.lockdown.unset({"_id":interaction.guild.id}, name)
			embed = discord.Embed(
					color=0x43b581, description=f'<a:nat_check:1010969401379536958> | Successfully deleted lockdown profile named **`{name}`**!')
			await interaction.response.send_message(embed=embed)
		else:
			warning = discord.Embed(
				color=0xffd300,
				description=f"<a:nat_warning:1062998119899484190> **|** The operation named **`{operation}`** does not exist. Please try again.")
			return await interaction.response.send_message(embed=warning, ephemeral=True)

	async def on_error(self, interaction: Interaction, error):
		try:
			await interaction.response.send_message(f"Error: {error}")
		except discord.InteractionResponded:
			await interaction.followup.send(f"Error: {error}", ephemeral=True)

async def setup(bot):
	await bot.add_cog(settings(bot))
	print(f"loaded channel cog")