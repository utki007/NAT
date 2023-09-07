import time as t
from itertools import islice
from typing import List, Union

import discord
from discord import Interaction, app_commands
from discord.ext import commands

from ui.settings.lockdown import *
from utils.convertor import *
from utils.views.paginator import Paginator


def chunk(it, size):
	it = iter(it)
	return iter(lambda: tuple(islice(it, size)), ())

@app_commands.guild_only()
# @app_commands.default_permissions(manage_messages=True)
# @app_commands.bot_has_permissions(manage_messages=True)
class channel(commands.GroupCog, name="channel", description="Helps you manage channels #️⃣"):
	def __init__(self, bot):
		self.bot = bot
	
	@app_commands.command(name="slowmode", description="Set cooldown for chat ⏰")
	@app_commands.describe(time="Enter time. Ex: '1h5m4s'")
	async def slowmode(self, interaction: discord.Interaction, time: str="0s"):
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
	
		desc = f''
		timer = datetime.datetime.strptime(str(datetime.timedelta(seconds=cd)), '%H:%M:%S')
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

		if channel.slowmode_delay == cd:
			if cd == 0:
				embed = await get_warning_embed(content = f"Slowmode for {channel.mention} is already removed.")
			else:
				embed = await get_warning_embed(content = f"Slowmode for {channel.mention} is already set to {desc}.")
			return await interaction.edit_original_response(embed=embed)
		
		if cd > 21600:
			warning = discord.Embed(
				color=0xDA2A2A,
				description=f"<a:nat_cross:1010969491347357717> **|** Slowmode interval can't be greater than 6 hours.")
			return await interaction.edit_original_response(embed=warning)
		elif cd == 0:
			await channel.edit(slowmode_delay=cd, reason = f'Slowmode removed by {interaction.user} (ID: {interaction.user.id})')
			embed = await get_success_embed(content = f"Removed slowmode for {channel.mention}.")
			await interaction.edit_original_response(embed=embed)
		else:
			cd = int(cd)
			await channel.edit(slowmode_delay=cd, reason = f'Slowmode has been set to {desc} by {interaction.user} (ID: {interaction.user.id})')
			embed = await get_success_embed(content = f"Slowmode for {channel.mention} has been set to {desc}.")
			await interaction.edit_original_response(embed=embed)

	@app_commands.command(name="lock", description="Lock channel 🙊", extras={'example': '/lock'})
	@app_commands.describe(role = "Provide role", user = "Input user 👤")
	async def lock(self, interaction:  discord.Interaction, role: discord.Role = None, user: discord.User = None):
		
		if interaction.user.id == 685705841264820247:
			await interaction.response.defer(ephemeral = True)
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

			role_mention = role.mention if role != interaction.guild.default_role else role

			if unlockFor == "role":
				overwrite = channel.overwrites_for(role)
				if overwrite.send_messages == False:
					embed = await get_warning_embed(content = f"{channel.mention} is already locked for {role_mention}.")
				else:
					overwrite.send_messages = False
					await channel.set_permissions(role, overwrite=overwrite, reason = f'Channel lockdown sanctioned by {interaction.user} (ID: {interaction.user.id}) for {role}')
					embed = await get_success_embed(content = f"Locked {channel.mention} for {role_mention}.")
			elif unlockFor == "user":
				overwrite = channel.overwrites_for(user)
				if overwrite.send_messages == False:
					embed = await get_warning_embed(content = f"{channel.mention} is already locked for {user.mention}.")
				else:		
					overwrite.send_messages = False

					await channel.set_permissions(user, overwrite=overwrite, reason = f'Channel lockdown sanctioned by {interaction.user} (ID: {interaction.user.id}) for {user} ({user.id})')
					embed = await get_success_embed(content = f"Locked {channel.mention} for {user.mention}.")
			else:
				embed = await get_warning_embed(content = f"Ran into some problem ...")

			await interaction.edit_original_response(embed=embed)
			if interaction.user.id == 685705841264820247:
				await interaction.channel.send(embed=embed)

		else:
			embed = discord.Embed(
				color=0x43b581, description=f'<a:nat_check:1010969401379536958> **|** Locked **{channel.mention}** for {interaction.guild.default_role}')
			if interaction.user.id == 685705841264820247:
				await interaction.channel.send(embed=embed)
			else:
				await interaction.edit_original_response(
					embed=embed
				)
				if interaction.user.id == 685705841264820247:
					await interaction.channel.send(embed=embed)
			await channel.edit(archived=True, locked=True)

	@app_commands.command(name="unlock", description="Unlock channel 🗣️", extras={'example': '/unlock'})
	@app_commands.describe(role = "Provide role", user = "Input user 👤", state = "False for deafult perm, True for override perms")
	async def unlock(self, interaction:  discord.Interaction, state: bool = True, role: discord.Role = None, user: discord.User = None):
		
		if interaction.user.id == 685705841264820247:
			await interaction.response.defer(ephemeral = True)
		else:
			await interaction.response.defer(ephemeral = False)

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
				
				msg = ''
				reason = f'Channel lockdown removed by {interaction.user} (ID: {interaction.user.id}) for {role}'

				if state == True:
					overwrite.send_messages = True
					reason += ' with state True'
				elif state == False:
					overwrite.send_messages = None

				
				if role == interaction.guild.default_role :
					if state:
						msg = f'Unlocked **{channel.mention}** for {role} with state `True`'
					else:
						msg = f'Unlocked **{channel.mention}** for {role}'
				else:
					if state:
						msg = f'Unlocked **{channel.mention}** for {role.mention} with state `True`'
					else:
						msg = f'Unlocked **{channel.mention}** for {role.mention}'
			
				await channel.set_permissions(role, overwrite=overwrite, reason = reason)

				embed = await get_success_embed(content = msg)

			elif unlockFor == "user":
				overwrite = channel.overwrites_for(user)
				
				msg = ''
				reason = f'Channel lockdown removed by {interaction.user} (ID: {interaction.user.id}) for {user} (ID: {user.id})'
				if state == True:
					overwrite.send_messages = True
					reason += ' with state True'
				elif state == False:
					overwrite.send_messages = None

				
				if state:
					msg = f'Unlocked **{channel}** for {user.mention} with state `True`'
				else:
					msg = f'Unlocked **{channel}** for {user.mention}'
			
				await channel.set_permissions(user, overwrite=overwrite, reason=reason)

				embed = await get_success_embed(content = msg)
			else:
				embed = await get_error_embed(content = f"Ran into some problem ...")
			
			await interaction.edit_original_response(embed=embed)
			if interaction.user.id == 685705841264820247:
				await interaction.channel.send(embed=embed)
			
		else:
			warning = await get_warning_embed(content = f"It's already unlocked dum dum")
			await interaction.edit_original_response(embed=warning, ephemeral=True)
			if interaction.user.id == 685705841264820247:
				await interaction.channel.send(embed=warning)

	@app_commands.command(name="viewlock", description="viewloock channel 🙈", extras={'example': '/viewlock'})
	@app_commands.checks.has_permissions(administrator=True)
	@app_commands.describe(role = "Provide role")
	async def viewlock(self, interaction:  discord.Interaction, role: discord.Role = None):
		
		channel = interaction.channel
		role = role or interaction.guild.default_role
		role_mention = role.mention if role != interaction.guild.default_role else role

		if interaction.channel.type == discord.ChannelType.text:

			overwrite = channel.overwrites_for(role)
			if overwrite.view_channel == False:
				embed = await get_error_embed(content = f"{role_mention} is already viewlocked")
			else:
				overwrite.view_channel = False

				await channel.set_permissions(role, overwrite=overwrite, reason = f'Channel viewlock sanctioned by {interaction.user} (ID: {interaction.user.id}) for {role}')
				embed = await get_success_embed(content = f"Viewlocked **{channel.mention}** for {role_mention}.")
			
			await interaction.response.send_message(embed=embed, ephemeral=False)

		else:
			warning = await get_error_embed(content = f"It cant be view-locked dum dum")
			return await interaction.response.send_message(embed=warning, ephemeral=True)

	@app_commands.command(name="unviewlock", description="Unviewlock channel 🗣️", extras={'example': '/unviewlock'})
	@app_commands.checks.has_permissions(administrator=True)
	@app_commands.describe(role = "Provide role", state = "Input state.")
	async def unviewlock(self, interaction:  discord.Interaction, state: bool = True, role: discord.Role = None):
		
		channel = interaction.channel        
		if role == None:
			role = interaction.guild.default_role

		if interaction.channel.type == discord.ChannelType.text:
			overwrite = channel.overwrites_for(role)
			
			reason = f'Channel viewlock removed by {interaction.user} (ID: {interaction.user.id}) for {role}'
			if state == True:
				overwrite.view_channel = True
				reason += ' with state True'
			elif state == False:
				overwrite.view_channel = None

			msg = ''
			
			if role == interaction.guild.default_role :
				if state:
					msg = f'Unviewlocked **{channel.mention}** for {role} with state `True`'
				else:
					msg = f'Unviewlocked **{channel.mention}** for {role}'
			else:
				if state:
					msg = f'Unviewlocked **{channel.mention}** for {role.mention} with state `True`'
				else:
					msg = f'Unviewlocked **{channel.mention}** for {role.mention}'
		
			await channel.set_permissions(role, overwrite=overwrite)

			embed = await get_success_embed(content = msg)
			await interaction.response.send_message(embed=embed, ephemeral=False)
		
		else:
			warning = await get_error_embed(content = f"It's already unviewlocked dum dum")
			return await interaction.response.send_message(embed=warning, ephemeral=True)

	@app_commands.command(name="sync", description="sync channel 🔄️", extras={'example': '/sync'})
	@app_commands.checks.has_permissions(manage_messages=True)
	async def sync(self, interaction:  discord.Interaction):

		if interaction.user.id == 685705841264820247:
			await interaction.response.defer(ephemeral=True)
		else:
			await interaction.response.defer(ephemeral=False)

		
		channel = interaction.channel

		if interaction.channel.type == discord.ChannelType.text:
			
			embed = await get_success_embed(content = f"Synced **{channel.mention}** with channel category.")
			
			await interaction.channel.edit(sync_permissions=True, reason=f"Channel synced by {interaction.user} (ID: {interaction.user.id})")

			await interaction.edit_original_response(embed=embed)
			if interaction.user.id == 685705841264820247:
				await interaction.channel.send(embed=embed)

		else:
			error = await get_error_embed(content = f"It cant be synced dum dum")
			await interaction.edit_original_response(embed=error)
			if interaction.user.id == 685705841264820247:
				await interaction.channel.send(embed=error)

	@app_commands.command(name="dump", description="Dump members in a channel or a role 📜", extras={'example': '/dump'})
	async def dump(self, interaction:  discord.Interaction, channel: discord.TextChannel = None, role: discord.Role = None):
		
		type = None
		if channel != None and role != None:
			members = list(set(channel.members).intersection(set(role.members)))
			color = role.color
			title = f"{len(members)} out of {len(role.members)} targetted members have access to {channel.mention}.\n\n"
		elif channel != None:
			members = channel.members
			color = discord.Color.default()
			title = f"**{len(members)} members** have access to {channel.mention}.\n\n"
		elif role != None:
			members = role.members
			color = role.color
			title = f"**{len(members)} members** have {role.mention} role.\n\n"
		else:
			guild = interaction.guild
			members = guild.members
			color = discord.Color.default()
			title = f"The server **{guild.name}** has a total of **{len(members)} members**.\n\n"
				
		member_list = members
		
		pages = []
		ping_group = list(chunk(member_list,10))
		member_count = 0
		for members in ping_group:
			desc = ''
			for member in members:
				member_count += 1
				desc += f'` {member_count}. ` {member.mention} (`{member.id}`)\n'
			desc = f"{title}{desc}"
			embed = discord.Embed(description=desc, color=color)
			pages.append(embed)
		
		custom_button = [discord.ui.Button(label="<<", style=discord.ButtonStyle.gray),discord.ui.Button(label="<", style=discord.ButtonStyle.gray),discord.ui.Button(label=">", style=discord.ButtonStyle.gray),discord.ui.Button(label=">>", style=discord.ButtonStyle.gray)]

		await Paginator(interaction, pages, custom_button).start(embeded=True, quick_navigation=False)

async def setup(bot):
	await bot.add_cog(channel(bot))
	print(f"loaded channel cog")