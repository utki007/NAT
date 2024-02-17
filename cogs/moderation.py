import datetime

import discord
from discord import Interaction, app_commands
from discord.ext import commands

from utils.embeds import get_error_embed, get_invisible_embed, get_success_embed, get_warning_embed
from utils.functions import quarantineUser, unquarantineUser

@app_commands.guild_only()
class moderation(commands.GroupCog, name="moderate", description="Server moderation commands"):
	def __init__(self, bot):
		self.bot = bot
	
	@app_commands.command(name="quarantine", description="Quarantine a user! 🦠")
	@app_commands.checks.has_permissions(administrator=True)
	async def quarantine(self, interaction:  discord.Interaction, user: discord.Member):
		await interaction.response.defer()

		# check if user = author
		if user.id == interaction.user.id:
			embed = await get_error_embed("Incorrect user provided.")
			embed.title = "Failed to quarantine."
			embed.description = f"<:tgk_rightBullet:1208276024996012053> You cannot quarantine yourself.\n"
			return await interaction.edit_original_response(embed = embed)
		
		# check if author top role < user top role
		if interaction.user.top_role.position < user.top_role.position:
			embed = await get_error_embed("I cannot quarantine this user!")
			embed.title = "Failed to quarantine."
			embed.description = f"<:tgk_rightBullet:1208276024996012053> {user.mention}'s role {user.top_role.mention}(`{user.top_role.name}`) is above your higest role.\n"
			return await interaction.edit_original_response(embed = embed)

		dankSecurity = await interaction.client.dankSecurity.find(user.guild.id)
		if dankSecurity is not None:
			if dankSecurity['quarantine'] is None:
				embed = await get_warning_embed("Quarantine role not set. Please set it using </serversettings:1197399871578185748> command.")
				embed.title = "Failed to quarantine."
				embed.description = f'<:tgk_rightBullet:1208276024996012053> Quarantine role is not set or does not exist.\n'
				embed.description += f'<:tgk_rightBullet:1208276024996012053> Please set it using </serversettings:1197399871578185748> command.'
				return await interaction.edit_original_response(embed = embed)
			else:
				role = user.guild.get_role(dankSecurity['quarantine'])
				
				# check if interaction author is whitelisted
				if 'whitelist' in dankSecurity:
					if dankSecurity['whitelist'] is None:
						embed = await get_warning_embed("Whitelist not set. Please set it using </serversettings:1197399871578185748> command.")
						embed.title = "Failed to quarantine."
						embed.description = f'<:tgk_rightBullet:1208276024996012053> Whitelist is not set or does not exist.\n'
						embed.description += f'<:tgk_rightBullet:1208276024996012053> Please set it using </serversettings:1197399871578185748> command.'
						return await interaction.edit_original_response(embed = embed)
					if interaction.user.id not in dankSecurity['whitelist']:
						embed = await get_error_embed(f"You are not whitelisted to quarantine users.")
						embed.title = "Failed to quarantine."
						embed.description = f'<:tgk_rightBullet:1208276024996012053> You are not whitelisted to quarantine users.\n'
						embed.description += f'<:tgk_rightBullet:1208276024996012053> Please set it using </serversettings:1197399871578185748> command.'
						return await interaction.edit_original_response(embed = embed)
				else:
					embed = await get_warning_embed("Whitelist not set. Please set it using </serversettings:1197399871578185748> command.")
					embed.title = "Failed to quarantine."
					embed.description = f'<:tgk_rightBullet:1208276024996012053> Whitelist is not set or does not exist.\n'
					embed.description += f'<:tgk_rightBullet:1208276024996012053> Please set it using </serversettings:1197399871578185748> command.'
					return await interaction.edit_original_response(embed = embed)

				# check if role exists
				if role is None:
					embed = await get_warning_embed("Quarantine role not set. Please set it using </serversettings:1197399871578185748> command.")
					embed.title = "Failed to quarantine."
					embed.description = f'<:tgk_rightBullet:1208276024996012053> Quarantine role is not set or does not exist.\n'
					embed.description += f'<:tgk_rightBullet:1208276024996012053> Please set it using </serversettings:1197399871578185748> command.'
					return await interaction.edit_original_response(embed = embed)
				
				# check if bot can handout role
				if role.position >= user.guild.me.top_role.position:
					embed = await get_error_embed(f"I cannot quarantine this user!")
					embed.title = "Failed to quarantine."
					embed.description = f"<:tgk_rightBullet:1208276024996012053> Role {role.mention}(`{role.name}`) is above my higest role.\n"
					embed.description += f"<:tgk_rightBullet:1208276024996012053> Please move my role above {role.mention}(`{role.name}`) role and try again."
					return await interaction.edit_original_response(embed = embed)

				# quarantine user
				quarantined = await quarantineUser(interaction.client, user, role, f'Quarantined by {interaction.user.name}#{interaction.user.discriminator} (ID: {interaction.user.id})')
				if quarantined: 
					embed = await get_success_embed(f"Successfully quarantined {user.mention}!")
					return await interaction.edit_original_response(embed = embed)
				else:
					embed = await get_error_embed(f"Failed to quarantine {user.mention}!")
					embed.title = "Failed to quarantine."
					embed.description = f'<:tgk_rightBullet:1208276024996012053> {user.mention} is already quarantined.\n'
					return await interaction.edit_original_response(embed = embed)
		else:
			embed = await get_warning_embed("Quarantine role not set. Please set it using </serversettings:1197399871578185748> command.")
			embed.title = "Failed to quarantine."
			embed.description = f'<:tgk_rightBullet:1208276024996012053> Quarantine role is not set or does not exist.\n'
			embed.description += f'<:tgk_rightBullet:1208276024996012053> Please set it using </serversettings:1197399871578185748> command.'
			return await interaction.edit_original_response(embed = embed)
 
	@app_commands.command(name="unquarantine", description="Unquarantine a user! 🦠")
	@app_commands.checks.has_permissions(administrator=True)
	async def unquarantine(self, interaction:  discord.Interaction, user: discord.Member):
		await interaction.response.defer()

		dankSecurity = await interaction.client.dankSecurity.find(user.guild.id)
		if dankSecurity is not None:
			if dankSecurity['quarantine'] is None:
				embed = await get_warning_embed("Quarantine role not set. Please set it using </serversettings:1197399871578185748> command.")
				embed.title = "Failed to unquarantine."
				embed.description = f'<:tgk_rightBullet:1208276024996012053> Quarantine role is not set or does not exist.\n'
				embed.description += f'<:tgk_rightBullet:1208276024996012053> Please set it using </serversettings:1197399871578185748> command.'
				return await interaction.edit_original_response(embed = embed)
			else:
				role = user.guild.get_role(dankSecurity['quarantine'])
				
				# check if role exists
				if role is None:
					embed = await get_warning_embed("Quarantine role not set. Please set it using </serversettings:1197399871578185748> command.")
					embed.title = "Failed to unquarantine."
					embed.description = f'<:tgk_rightBullet:1208276024996012053> Quarantine role is not set or does not exist.\n'
					embed.description += f'<:tgk_rightBullet:1208276024996012053> Please set it using </serversettings:1197399871578185748> command.'
					return await interaction.edit_original_response(embed = embed)
				
				# check if bot can handout role
				if role.position >= user.guild.me.top_role.position:
					embed = await get_error_embed(f"I cannot quarantine this user!")
					embed.title = "Failed to unquarantine."
					embed.description = f"<:tgk_rightBullet:1208276024996012053> Role {role.mention}(`{role.name}`) is above my higest role.\n"
					embed.description += f"<:tgk_rightBullet:1208276024996012053> Please move my role above {role.mention}(`{role.name}`) role and try again."
					return await interaction.edit_original_response(embed = embed)

				# unquarantine user
				unquarantined = await unquarantineUser(interaction.client, user, role, f'Unquarantined by {interaction.user.name}#{interaction.user.discriminator} (ID: {interaction.user.id})')
				if unquarantined:
					embed = await get_success_embed(f"Successfully unquarantined {user.mention}.")
					return await interaction.edit_original_response(embed = embed)
				else:
					embed = await get_error_embed(f"{user.mention} is not quarantined.")
					embed.title = "Failed to unquarantine."
					embed.description = f'<:tgk_rightBullet:1208276024996012053> {user.mention} is not quarantined by {interaction.client.user.mention}.\n'
					return await interaction.edit_original_response(embed = embed)
		else:
			embed = await get_warning_embed("Quarantine role not set. Please set it using </serversettings:1197399871578185748> command.")
			embed.title = "Failed to quarantine."
			embed.description = f'<:tgk_rightBullet:1208276024996012053> Quarantine role is not set or does not exist.\n'
			embed.description += f'<:tgk_rightBullet:1208276024996012053> Please set it using </serversettings:1197399871578185748> command.'
			return await interaction.edit_original_response(embed = embed)

async def setup(bot):
	await bot.add_cog(moderation(bot))
	print(f"loaded moderation cog")