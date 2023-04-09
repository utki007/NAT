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

		dankSecurity = await interaction.client.dankSecurity.find(user.guild.id)
		if dankSecurity is not None:
			if dankSecurity['quarantine'] is None:
				embed = await get_warning_embed("Quarantine role not set. Please set it using </serversettings:1068960308800008253> command.")
				embed.title = "Failed to quarantine."
				embed.description = f'<:tgk_redarrow:1005361235715424296> Quarantine role is not set or does not exist.\n'
				embed.description += f'<:tgk_redarrow:1005361235715424296> Please set it using </serversettings:1068960308800008253> command.'
				return await interaction.edit_original_response(embed = embed)
			else:
				role = user.guild.get_role(dankSecurity['quarantine'])
				
				# check if role exists
				if role is None:
					embed = await get_warning_embed("Quarantine role not set. Please set it using </serversettings:1068960308800008253> command.")
					embed.title = "Failed to quarantine."
					embed.description = f'<:tgk_redarrow:1005361235715424296> Quarantine role is not set or does not exist.\n'
					embed.description += f'<:tgk_redarrow:1005361235715424296> Please set it using </serversettings:1068960308800008253> command.'
					return await interaction.edit_original_response(embed = embed)
				
				# check if bot can handout role
				if role.position >= user.guild.me.top_role.position:
					embed = await get_error_embed(f"I cannot quarantine this user!")
					embed.title = "Failed to quarantine."
					embed.description = f"<:tgk_redarrow:1005361235715424296> Role {role.mention}(`{role.name}`) is above my higest role.\n"
					embed.description += f"<:tgk_redarrow:1005361235715424296> Please move my role above {role.mention}(`{role.name}`) role and try again."
					return await interaction.edit_original_response(embed = embed)

				# quarantine user
				quarantined = await quarantineUser(interaction.client, user, role, f'Quarantined by {interaction.user.name}#{interaction.user.discriminator} (ID: {interaction.user.id})')
				if quarantined: 
					embed = await get_success_embed(f"Successfully quarantined {user.mention}!")
					return await interaction.edit_original_response(embed = embed)
				else:
					embed = await get_error_embed(f"Failed to quarantine {user.mention}!")
					embed.title = "Failed to quarantine."
					embed.description = f'<:tgk_redarrow:1005361235715424296> {user.mention} is already quarantined.\n'
					return await interaction.edit_original_response(embed = embed)
		else:
			embed = await get_warning_embed("Quarantine role not set. Please set it using </serversettings:1068960308800008253> command.")
			embed.title = "Failed to quarantine."
			embed.description = f'<:tgk_redarrow:1005361235715424296> Quarantine role is not set or does not exist.\n'
			embed.description += f'<:tgk_redarrow:1005361235715424296> Please set it using </serversettings:1068960308800008253> command.'
			return await interaction.edit_original_response(embed = embed)
 
	@app_commands.command(name="unquarantine", description="Unquarantine a user! 🦠")
	@app_commands.checks.has_permissions(administrator=True)
	async def unquarantine(self, interaction:  discord.Interaction, user: discord.Member):
		await interaction.response.defer()

		dankSecurity = await interaction.client.dankSecurity.find(user.guild.id)
		if dankSecurity is not None:
			if dankSecurity['quarantine'] is None:
				embed = await get_warning_embed("Quarantine role not set. Please set it using </serversettings:1068960308800008253> command.")
				embed.title = "Failed to unquarantine."
				embed.description = f'<:tgk_redarrow:1005361235715424296> Quarantine role is not set or does not exist.\n'
				embed.description += f'<:tgk_redarrow:1005361235715424296> Please set it using </serversettings:1068960308800008253> command.'
				return await interaction.edit_original_response(embed = embed)
			else:
				role = user.guild.get_role(dankSecurity['quarantine'])
				
				# check if role exists
				if role is None:
					embed = await get_warning_embed("Quarantine role not set. Please set it using </serversettings:1068960308800008253> command.")
					embed.title = "Failed to unquarantine."
					embed.description = f'<:tgk_redarrow:1005361235715424296> Quarantine role is not set or does not exist.\n'
					embed.description += f'<:tgk_redarrow:1005361235715424296> Please set it using </serversettings:1068960308800008253> command.'
					return await interaction.edit_original_response(embed = embed)
				
				# check if bot can handout role
				if role.position >= user.guild.me.top_role.position:
					embed = await get_error_embed(f"I cannot quarantine this user!")
					embed.title = "Failed to unquarantine."
					embed.description = f"<:tgk_redarrow:1005361235715424296> Role {role.mention}(`{role.name}`) is above my higest role.\n"
					embed.description += f"<:tgk_redarrow:1005361235715424296> Please move my role above {role.mention}(`{role.name}`) role and try again."
					return await interaction.edit_original_response(embed = embed)

				# unquarantine user
				unquarantined = await unquarantineUser(interaction.client, user, role, f'Unquarantined by {interaction.user.name}#{interaction.user.discriminator} (ID: {interaction.user.id})')
				if unquarantined:
					embed = await get_success_embed(f"Successfully unquarantined {user.mention}.")
					return await interaction.edit_original_response(embed = embed)
				else:
					embed = await get_error_embed(f"{user.mention} is not quarantined.")
					embed.title = "Failed to unquarantine."
					embed.description = f'<:tgk_redarrow:1005361235715424296> {user.mention} is not quarantined by {interaction.client.user.mention}.\n'
					return await interaction.edit_original_response(embed = embed)
		else:
			embed = await get_warning_embed("Quarantine role not set. Please set it using </serversettings:1068960308800008253> command.")
			embed.title = "Failed to quarantine."
			embed.description = f'<:tgk_redarrow:1005361235715424296> Quarantine role is not set or does not exist.\n'
			embed.description += f'<:tgk_redarrow:1005361235715424296> Please set it using </serversettings:1068960308800008253> command.'
			return await interaction.edit_original_response(embed = embed)

async def setup(bot):
	await bot.add_cog(moderation(bot))
	print(f"loaded moderation cog")