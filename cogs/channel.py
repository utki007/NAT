import time as t
import discord
from discord import app_commands, Interaction
from discord.ext import commands
from utils.convertor import *
from utils.transformers import TimeConverter
from typing import Union, List
from ui.channel import *

class channel(commands.GroupCog, name="channel"):
	def __init__(self, bot):
		self.bot = bot

	lockdown_command = app_commands.Group(name="lockdown", description="Manage Server Lockdown Status")

	async def lockdown_profiles_list(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
		current_panel = await self.bot.lockdown.find(interaction.guild.id)
		if not current_panel:
			return []
		
		choice = [
			app_commands.Choice(name=name, value=name)
			for name in current_panel['lockdown_profiles'] if current.lower() in name.lower()
		]
		return choice
	
	@app_commands.command(name="slowmode", description="Set cooldown for chat ⏰")
	@app_commands.describe(time="Enter time. Ex: '1h5m4s'")
	async def slowmode(self, interaction: discord.Interaction, time: str="0s"):
		if interaction.user.id == 685705841264820247:
			await interaction.response.defer(ephemeral = True)
			await interaction.edit_original_response(
				content="slowmode will be set shortly..."
			)
		else:
			await interaction.response.defer(ephemeral = False)
		
		channel = interaction.channel

		try:
			time = await convert_to_time(time)
			cd = int(await calculate(time))
		except:
			warning = discord.Embed(
				color=0xDA2A2A,
				description=f"<a:nat_cross:1010969491347357717> **|** Incorrect time format, please use `h|m|s`")
			return await interaction.edit_original_response(embed=warning)

		if cd > 21600:
			warning = discord.Embed(
				color=0xDA2A2A,
				description=f"<a:nat_cross:1010969491347357717> **|** Slowmode interval can't be greater than 6 hours.")
			return await interaction.edit_original_response(embed=warning)
		elif cd == 0:
			await channel.edit(slowmode_delay=cd)
			await interaction.edit_original_response(content=f"Slowmode has been removed!! 🎉")
		else:
			await channel.edit(slowmode_delay=cd)
			timer = datetime.datetime.strptime(str(datetime.timedelta(seconds=cd)), '%H:%M:%S')
			cd = int(cd)
			desc = f''
			if timer.hour>0:
				if timer.hour == 1:
					desc = desc + f'{timer.hour} hour '
				else:
					desc = desc + f'{timer.hour} hours '
			if timer.minute>0:
				if timer.minute == 1:
					desc = desc + f'{timer.minute} minute '
				else:
					desc = desc + f'{timer.minute} minutes '
			if timer.second>0:
				if timer.second == 1:
					desc = desc + f'{timer.second} second '
				else:
					desc = desc + f'{timer.second} seconds '

			await interaction.edit_original_response(content=f'Slowmode for {channel.mention} has been set to **{desc}**.')

	@app_commands.command(name="lock", description="Lock channel 🙊", extras={'example': '/lock'})
	@app_commands.describe(role = "Provide role", user = "Input user 👤")
	async def lock(self, interaction:  discord.Interaction, role: discord.Role = None, user: discord.User = None):
		if interaction.user.id == 685705841264820247:
			await interaction.response.defer(ephemeral = True)
			await interaction.edit_original_response(
				content="channel will be locked shortly..."
			)
		else:
			await interaction.response.defer(ephemeral = False)


		unlockFor = ""
		channel = interaction.channel

		if interaction.channel.type == discord.ChannelType.text:
			if role == None:
				if user == None:
					role = interaction.guild.default_role
					unlockFor = "role"
				else:
					unlockFor = "user"
			else:
				unlockFor = "role"

			if unlockFor == "role":
				overwrite = channel.overwrites_for(role)
				overwrite.send_messages = False

				await channel.set_permissions(role, overwrite=overwrite)
				if role == interaction.guild.default_role:
					embed = discord.Embed(
					color=0x43b581, description=f'<a:nat_check:1010969401379536958> **|** Locked **{channel.mention}** for {role}')
				else:
					embed = discord.Embed(
					color=0x43b581, description=f'<a:nat_check:1010969401379536958> **|** Locked **{channel.mention}** for {role.mention}')
			elif unlockFor == "user":
				overwrite = channel.overwrites_for(user)
				overwrite.send_messages = False

				await channel.set_permissions(user, overwrite=overwrite)
				embed = discord.Embed(
				color=0x43b581, description=f'<a:nat_check:1010969401379536958> **|** Locked **{channel.mention}** for {user.mention}')
			else:
				return await interaction.edit_original_response(f"Ran into some problem ...", hidden= True)

			if interaction.user.id == 685705841264820247:
				await interaction.channel.send(embed=embed)
			else:
				await interaction.edit_original_response(
					embed=embed
				)

		else:
			embed = discord.Embed(
				color=0x43b581, description=f'<a:nat_check:1010969401379536958> **|** Locked **{channel.mention}** for {interaction.guild.default_role}')
			if interaction.user.id == 685705841264820247:
				await interaction.channel.send(embed=embed)
			else:
				await interaction.edit_original_response(
					embed=embed
				)
			await channel.edit(archived=True, locked=True)

	@app_commands.command(name="unlock", description="Unlock channel 🗣️", extras={'example': '/unlock'})
	@app_commands.describe(role = "Provide role", user = "Input user 👤", state = "False for deafult perm, True for override perms")
	async def unlock(self, interaction:  discord.Interaction, state: bool = True, role: discord.Role = None, user: discord.User = None):
		
		unlockFor = ""
		channel = interaction.channel        
		if role == None:
			if user == None:
				role = interaction.guild.default_role
				unlockFor = "role"
			else:
				unlockFor = "user"
		else:
			unlockFor = "role"

		if interaction.channel.type == discord.ChannelType.text:
			if unlockFor == "role":
				overwrite = channel.overwrites_for(role)
				
				if state == True:
					overwrite.send_messages = True
				elif state == False:
					overwrite.send_messages = None

				msg = ''
				
				if role == interaction.guild.default_role :
					if state:
						msg = f'<a:nat_check:1010969401379536958> **|** Unlocked **{channel.mention}** for {role} with state `True`'
					else:
						msg = f'<a:nat_check:1010969401379536958> **|** Unlocked **{channel.mention}** for {role}'
				else:
					if state:
						msg = f'<a:nat_check:1010969401379536958> **|** Unlocked **{channel.mention}** for {role.mention} with state `True`'
					else:
						msg = f'<a:nat_check:1010969401379536958> **|** Unlocked **{channel.mention}** for {role.mention}'
			
				await channel.set_permissions(role, overwrite=overwrite)

				embed = discord.Embed(
					color=0x43b581, description=f'{msg}')
			elif unlockFor == "user":
				overwrite = channel.overwrites_for(user)
				
				if state == True:
					overwrite.send_messages = True
				elif state == False:
					overwrite.send_messages = None

				msg = ''
				
				if state:
					msg = f'<a:nat_check:1010969401379536958> **|** Unlocked **{channel}** for {user.mention} with state `True`'
				else:
					msg = f'<a:nat_check:1010969401379536958> **|** Unlocked **{channel}** for {user.mention}'
			
				await channel.set_permissions(user, overwrite=overwrite)

				embed = discord.Embed(
					color=0x43b581, description=f'{msg}')
			else:
				return await interaction.response.send_message(f"Ran into some problem ...", ephemeral=True)
			
			if interaction.user.id == 685705841264820247:
				await interaction.response.send_message(content="Unlocking ...", ephemeral=True)
				return await interaction.channel.send(embed=embed)
			else:
				await interaction.response.send_message(embed=embed, ephemeral=False)
		else:
			warning = discord.Embed(
				color=0xDA2A2A,
				title=f"<a:nat_cross:1010969491347357717> **|** It's already unlocked dum dum")
			return await interaction.response.send_message(embed=warning, ephemeral=True)

	@app_commands.command(name="viewlock", description="viewloock channel 🙈", extras={'example': '/viewlock'})
	@app_commands.describe(role = "Provide role")
	async def viewlock(self, interaction:  discord.Interaction, role: discord.Role = None):
		
		channel = interaction.channel

		if interaction.channel.type == discord.ChannelType.text:
			if role == None:
				role = interaction.guild.default_role

			overwrite = channel.overwrites_for(role)
			overwrite.view_channel = False

			await channel.set_permissions(role, overwrite=overwrite)
			if role == interaction.guild.default_role:
				embed = discord.Embed(
				color=0x43b581, description=f'<a:nat_check:1010969401379536958> **|** Viewlocked **{channel.mention}** for {role}')
			else:
				embed = discord.Embed(
				color=0x43b581, description=f'<a:nat_check:1010969401379536958> **|** Viewlocked **{channel.mention}** for {role.mention}')
			
			if interaction.user.id == 685705841264820247:
				await interaction.response.send_message(content="Viewlocking ...", ephemeral=True)
				await interaction.channel.send(embed=embed)
			else:
				await interaction.response.send_message(
					embed=embed, ephemeral=False
				)

		else:
			warning = discord.Embed(
				color=0xDA2A2A,
				title=f"<a:nat_warning:1062998119899484190> **|** It cant be view-locked dum dum")
			return await interaction.response.send_message(embed=warning, ephemeral=True)

	@app_commands.command(name="unviewlock", description="Unviewlock channel 🗣️", extras={'example': '/unviewlock'})
	@app_commands.describe(role = "Provide role", state = "Input state.")
	async def unviewlock(self, interaction:  discord.Interaction, state: bool = True, role: discord.Role = None):
		
		channel = interaction.channel        
		if role == None:
			role = interaction.guild.default_role

		if interaction.channel.type == discord.ChannelType.text:
			overwrite = channel.overwrites_for(role)
			
			if state == True:
				overwrite.view_channel = True
			elif state == False:
				overwrite.view_channel = None

			msg = ''
			
			if role == interaction.guild.default_role :
				if state:
					msg = f'<a:nat_check:1010969401379536958> **|** Unviewlocked **{channel.mention}** for {role} with state `True`'
				else:
					msg = f'<a:nat_check:1010969401379536958> **|** Unviewlocked **{channel.mention}** for {role}'
			else:
				if state:
					msg = f'<a:nat_check:1010969401379536958> **|** Unviewlocked **{channel.mention}** for {role.mention} with state `True`'
				else:
					msg = f'<a:nat_check:1010969401379536958> **|** Unviewlocked **{channel.mention}** for {role.mention}'
		
			await channel.set_permissions(role, overwrite=overwrite)

			embed = discord.Embed(
				color=0x43b581, description=f'{msg}')
			
			
			if interaction.user.id == 685705841264820247:
				await interaction.response.send_message(content="Unlocking ...", ephemeral=True)
				return await interaction.channel.send(embed=embed)
			else:
				await interaction.response.send_message(embed=embed, ephemeral=False)
		else:
			warning = discord.Embed(
				color=0xDA2A2A,
				title=f"<a:nat_warning:1062998119899484190> **|** It's already unviewlocked dum dum")
			return await interaction.response.send_message(embed=warning, ephemeral=True)

	@app_commands.command(name="sync", description="sync channel 🔄️", extras={'example': '/sync'})
	async def sync(self, interaction:  discord.Interaction):
		
		channel = interaction.channel

		if interaction.channel.type == discord.ChannelType.text:

			embed = discord.Embed(
			color=0x43b581, description=f'<a:nat_check:1010969401379536958> **|** Synced **{channel.mention}** with channel category.')
			
			await interaction.channel.edit(sync_permissions=True)

			if interaction.user.id == 685705841264820247:
				await interaction.response.send_message(content="Syncing ...", ephemeral=True)
				await interaction.channel.send(embed=embed)
			else:
				await interaction.response.send_message(
					embed=embed, ephemeral=False
				)

		else:
			warning = discord.Embed(
				color=0xDA2A2A,
				title=f"<a:nat_warning:1062998119899484190> **|** It cant be synced dum dum")
			return await interaction.response.send_message(embed=warning, ephemeral=True)

	@lockdown_command.command(name="start", description="Begin lockdown", extras={'example': '/'})
	@app_commands.autocomplete(name=lockdown_profiles_list)
	@app_commands.describe(name = "Name of Lockdown profile")
	async def lockdown_start(self, interaction:  discord.Interaction, name: str):
		data = await self.bot.lockdown.find(interaction.guild.id)
		if not data and name not in data['lockdown_profiles']:
			warning = discord.Embed(
				color=0xffd300,
				title=f"> The profile named **`{name}`** does not exist. Are you trying to Create a profile? \n> Use </settings lockdown create:1063097729426919507>.")
			warning.set_thumbnail(url=f"https://cdn.discordapp.com/emojis/845404773360205854.gif?size=128&quality=lossless")
			return await interaction.response.send_message(embed=warning, ephemeral=True)
		
		profile = data[name]
		channel_and_role = profile['channel_and_role']
		embed = profile['lock_embed']

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
				color=0xDA2A2A,
				timestamp=datetime.datetime.utcnow()
		)
		lockdown_embed.set_footer(text=f"{interaction.guild.name}", icon_url=interaction.guild.icon.url)
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
			color=0x43b581, description=f'<a:nat_check:1010969401379536958> **|** Locked down profile `{name}` in: {round((end - start), 2)} s.')
			
		await interaction.edit_original_response(
			embed=embed
		)

	@lockdown_command.command(name="end", description="end lockdown", extras={'example': '/'})
	@app_commands.autocomplete(name=lockdown_profiles_list)
	@app_commands.describe(name = "Name of Lockdown profile")
	async def lockdown_end(self, interaction:  discord.Interaction, name: str):
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
		lockdown_embed.set_footer(text=f"{interaction.guild.name}", icon_url=interaction.guild.icon.url)
		lockdown_embed.set_thumbnail(url=embed['thumbnail'])
			
		for channel_id in channel_and_role:
			channel = interaction.guild.get_channel(int(channel_id))
			roleIds = [int(role_ids) for role_ids in channel_and_role[channel_id].split(" ") if role_ids != '' and role_ids not in ["everyone"]]
			roleIds = [discord.utils.get(interaction.guild.roles, id=id) for id in roleIds]
			roles = [role for role in roleIds if role != None]
			if channel and roles:
				for role in roles:
					overwrite = channel.overwrites_for(role)
					overwrite.send_messages = None

					await channel.set_permissions(role, overwrite=overwrite)
				await channel.send(embed=lockdown_embed)
		end = t.time()
		embed = discord.Embed(
			color=0x43b581, description=f'<a:nat_check:1010969401379536958> **|** Unlocked  profile `{name}` in: {round((end - start), 2)} s.')
			
		await interaction.edit_original_response(
			embed=embed
		)


async def setup(bot):
	await bot.add_cog(channel(bot))
	print(f"loaded channel cog")