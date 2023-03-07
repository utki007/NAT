import asyncio
import time as t
import datetime
import discord
from discord import app_commands, Interaction
from discord.ext import commands
from utils.embeds import *
from utils.convertor import *
from utils.checks import App_commands_Checks
from io import BytesIO
from typing import List, Union
from ui.settings import *
from ui.settings.dankPool import *
from utils.functions import *
from utils.views.confirm import Confirm
from utils.views.ui import *
from ui.settings.lockdown import *

class Dump(commands.GroupCog, name="dump"):
	def __init__(self, bot):
		self.bot = bot
	
	@app_commands.command(name="role", description="Dump a role", extras={'examples': '/dump role [role]'})
	@app_commands.describe(role='Role to dump')
	async def dump_role(self, interaction: Interaction, role:discord.Role):
		msg = f"{role.name} has {len(role.members)} members"
		
		if len(role.members) > 20:
			await interaction.response.send_message("Role has more than 20 members, sending as file", ephemeral=False)
			members = [f"{member.name}#{member.discriminator} **|** {member.id}" for member in role.members]

			buffer = BytesIO("\n".join(members).encode('utf-8'))
			file = discord.File(buffer, filename=f"{role.name}.txt")
			buffer.close()
			await interaction.edit_original_response(content=msg, attachments=[file])
		else:
			embed = discord.Embed(title=f"{role.name} dump", description="\n".join([f"{member.name}#{member.discriminator} **|** {member.id}" for member in role.members]), color=role.color)
			await interaction.response.send_message(content=msg, embeds=[embed])
	
	@app_commands.command(name="channel", description="Dump a channel", extras={'example': '/dump channel [channel]'})
	@app_commands.describe(channel='Channel to dump')
	async def dump_channel(self, interaction: Interaction, channel:discord.TextChannel):
		msg = f"{channel.name} has {len(channel.members)} members"

		if len(channel.members) > 20:
			await interaction.response.send_message("Channel has more than 20 members, sending as file", ephemeral=False)
			members = [f"{member.name}#{member.discriminator} **|** {member.id}" for member in channel.members]

			buffer = BytesIO("\n".join(members).encode('utf-8'))
			file = discord.File(buffer, filename=f"{channel.name}.txt")
			buffer.close()
			await interaction.edit_original_response(content=msg, attachments=[file])
		
		else:
			embed = discord.Embed(title=f"{channel.name} dump", description="\n".join([f"{member.mention} **|** `{member.id}`" for member in channel.members]), color=self.bot.color['default'])
			await interaction.response.send_message(content=msg, embeds=[embed])

class serverUtils(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@app_commands.command(name="ping", description="Ping pong! 🏓", extras={'example': '/ping'})
	@app_commands.checks.cooldown(1, 30, key=lambda i: (i.guild_id, i.user.id))
	async def ping(self, interaction:  discord.Interaction):
		await interaction.response.send_message("Pong! 🏓")

		await interaction.edit_original_response(
			content=f"Pong! **`{round(self.bot.latency * 1000)}ms`**",
		)

	@app_commands.command(name="calculate", description="Do math! 🧮", extras={'example': '/calculate query: 2m+40k'})
	@app_commands.checks.cooldown(1, 2, key=lambda i: (i.guild_id, i.user.id))
	@app_commands.describe(query = "5 Mil -> 5e6 or 5m", hidden = "Nobody knows how you calculated so accurately 🥂")
	async def calculate(self, interaction:  discord.Interaction, query: str , hidden: bool = False):
		await interaction.response.defer(ephemeral=hidden)

		start = t.time()
		query = await convert_to_numeral(query)
		output = await calculate(query)
		end = t.time()

		calc_embed = discord.Embed(
			color=0x9e3bff,
			title=f"**Value:** `{output:,}`"
		)
		url = f"https://fakeimg.pl/150x40/9e3bff/000000/?retina=1&text={'%20'.join((await millify(output)).split(' '))}&font=lobster&font_size=28"
		calc_embed.set_image(url=url)
		calc_embed.set_footer(text=f"{interaction.guild.name} • Calculated in: {round((end - start) * 1000, 2)} ms",icon_url=interaction.guild.icon)
		calc_embed.set_author(name=f"{interaction.user.display_name}'s calculation ...", icon_url=interaction.user.avatar)

		await interaction.edit_original_response(
			embed=calc_embed
		)

	#quarantine user using quarantineUser
	@app_commands.command(name="quarantine", description="Quarantine a user! 🦠")
	@app_commands.checks.has_permissions(administrator=True)
	async def quarantine(self, interaction:  discord.Interaction, user: discord.Member):
		await interaction.response.defer()

		dankSecurity = await interaction.client.dankSecurity.find(user.guild.id)
		if dankSecurity:
			if dankSecurity['quarantine'] is None:
				embed = await get_warning_embed("Quarantine role not set. Please set it using </serversettings:1068960308800008253> command.")
				return await interaction.edit_original_response(embed = embed)
			else:
				role = user.guild.get_role(dankSecurity['quarantine'])
				if role in user.roles:
					embed = await get_warning_embed("User is already quarantined.")
					return await interaction.edit_original_response(embed = embed)
				else:
					quarantined = await quarantineUser(interaction.client, user, role)
					if quarantined:
						embed = await get_success_embed(f"Successfully quarantined {user.mention}.")
						return await interaction.edit_original_response(embed = embed)
					else:
						embed = await get_error_embed(f"Failed to quarantine {user.mention}. I lack permissions to do so.")
						return await interaction.edit_original_response(embed = embed)
		else:
			embed = await get_warning_embed("Quarantine role not set. Please set it using </serversettings:1068960308800008253> command.")
			return await interaction.edit_original_response(embed = embed)
 
	@app_commands.command(name="unquarantine", description="Unquarantine a user! 🦠")
	@app_commands.checks.has_permissions(administrator=True)
	async def unquarantine(self, interaction:  discord.Interaction, user: discord.Member):
		await interaction.response.defer()
		unquarantined =  await unquarantineUser(interaction.client, user)
		if unquarantined:
			embed = await get_success_embed(f"Unquarantined {user.mention}!")
			await interaction.edit_original_response(embed=embed)
		else:
			embed = await get_error_embed(f"{user.mention} is not quarantined!")
			await interaction.edit_original_response(embed=embed)

	@app_commands.command(name="serversettings", description="Adjust server-specific settings! ⚙️")
	@app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
	@App_commands_Checks.is_owner()
	async def serversettings(self, interaction:  discord.Interaction):
		embed = discord.Embed(
			color=3092790,
			title="Server Settings",
			description=f"Adjust server-specific settings! ⚙️"
		)
		view = discord.ui.View()
		view.add_item(Serversettings_Dropdown())
		await interaction.response.send_message(embed=embed, view=view)
		
class Serversettings_Dropdown(discord.ui.Select):
	def __init__(self, default = -1):

		options = [
			discord.SelectOption(label='Dank Pool Access', description="Who all can access Server's Donation Pool", emoji='<:tgk_bank:1073920882130558987>'),
			discord.SelectOption(label='Server Lockdown', description='Configure Lockdown Profiles', emoji='<:tgk_lock:1072851190213259375>'),
		]
		if default != -1:
			options[default].default = True
		super().__init__(placeholder='What would you like to configure today?', min_values=1, max_values=1, options=options, row=0)

	async def callback(self, interaction: discord.Interaction):
		
		if self.values[0] == "Dank Pool Access":

			data = await interaction.client.dankSecurity.find(interaction.guild.id)
			if data is None:
				data = {"_id": interaction.guild.id, "event_manager": None, "whitelist": [], "quarantine": None}
				await interaction.client.dankSecurity.upsert(data)

			users = f""
			
			if data['whitelist'] is None or len(data['whitelist']) == 0:
				users += f"` - ` **Add users when?**\n"
			else:
				for member_id in data['whitelist']:
					try: 
						member = interaction.guild.get_member(int(member_id))
						users += f"` - ` {member.mention}\n"
					except:
						data['whitelist'].remove(member_id)
						await interaction.client.dankSecurity.upsert(data)
						pass
			event_manager = data['event_manager']

			if event_manager is None:
				event_manager = f"**`None`**"
			else:
				event_manager = interaction.guild.get_role(int(event_manager))
				event_manager = f"**{event_manager.mention} (`{event_manager.id}`)**"

				
			quarantine = data['quarantine']

			if quarantine is None:
				quarantine = f"**`None`**"
			else:
				quarantine = interaction.guild.get_role(int(quarantine))
				if quarantine is not None:
					quarantine = f"**{quarantine.mention} (`{quarantine.id}`)**"
			
			embed = discord.Embed(
				color=3092790,
				title="Dank Pool Access"
			)
			embed.add_field(name="Following users are whitelisted:", value=f"{users}", inline=False)
			embed.add_field(name="Event Manager Role:", value=f"{event_manager}", inline=False)
			embed.add_field(name="Quarantine Role:", value=f"{quarantine}", inline=False)

			self.view.stop()
			dank_pool_view =  Dank_Pool_Panel(interaction)
			dank_pool_view.add_item(Serversettings_Dropdown(0))
			
			await interaction.response.edit_message(embed=embed, view=dank_pool_view)
			dank_pool_view.message = await interaction.original_response()

		elif self.values[0] == "Server Lockdown":

			data = await interaction.client.lockdown.find(interaction.guild.id)
			if not data:
				data = {"_id": interaction.guild.id, "lockdown_profiles": []}
				await interaction.client.lockdown.upsert(data)

			if data['lockdown_profiles'] is None or len(data['lockdown_profiles']) == 0:
				profiles = f"` - ` **Add profiles when?**\n"
			else:
				profiles = ""
				for profile in data['lockdown_profiles']:
					profiles += f"` - ` **{profile.title()}**\n"

			embed = discord.Embed(
				color=3092790,
				title="Server Lockdown <:tgk_lock:1072851190213259375>"
			)
			embed.add_field(name="Lockdown Profiles:", value=f"{profiles}", inline=False)
			
			self.view.stop()
			lockdown_profile_view =  Lockdown_Profile_Panel(interaction)			
			lockdown_profile_view.add_item(Serversettings_Dropdown(1))
			await interaction.response.edit_message(embed=embed, view=lockdown_profile_view)
			lockdown_profile_view.message = await interaction.original_response()

			await interaction.message.edit(embed=embed, view=lockdown_profile_view)
		
		else:
			await interaction.response.send_message(f'Invaid Interaction',ephemeral=True)

async def setup(bot):
	await bot.add_cog(serverUtils(bot))
	await bot.add_cog(Dump(bot))
	print(f"loaded serverUtils cog")