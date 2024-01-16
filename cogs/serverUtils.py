import asyncio
import time as t
import datetime
import discord
from discord import app_commands, Interaction
from discord.ext import commands
import humanfriendly
from ui.settings.mafia import Mafia_Panel
from ui.settings.payouts import Payouts_Panel
from ui.settings.userConfig import Changelogs_Panel, Fish_Panel
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
from utils.views.paginator import Paginator
from itertools import islice
from ui.settings.voiceView import Voice_config

def chunk(it, size):
	it = iter(it)
	return iter(lambda: tuple(islice(it, size)), ())

class serverUtils(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@commands.hybrid_command(name='ping', description='Check the bot\'s latency! 🏓')
	@commands.cooldown(1, 10, commands.BucketType.user)
	@app_commands.guild_only()
	async def ping(self, ctx):
		msg = await ctx.send("Pong! 🏓")

		await msg.edit(
			content=f"Pong! **`{round(self.bot.latency * 1000)}ms`**"			
		)

	@commands.hybrid_command(name="calculate", description="Do math! 🧮", extras={'example': '/calculate query: 2m+40k'})
	@app_commands.guild_only()
	@app_commands.checks.cooldown(1, 2, key=lambda i: (i.guild_id, i.user.id))
	@app_commands.describe(query = "5 Mil -> 5e6 or 5m")
	async def calculate(self, ctx, *, query: str):

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
		calc_embed.set_footer(text=f"{ctx.guild.name} • Calculated in: {round((end - start) * 1000, 2)} ms",icon_url=ctx.guild.icon)
		calc_embed.set_author(name=f"{ctx.author.display_name}'s calculation ...", icon_url=ctx.author.avatar)

		await ctx.send(
			embed=calc_embed
		)

	@app_commands.command(name="serversettings", description="Adjust server-specific settings! ⚙️")
	@app_commands.guild_only()
	@app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
	@app_commands.checks.has_permissions(administrator=True)
	async def serversettings(self, interaction:  discord.Interaction):
		embed = discord.Embed(
			color=3092790,
			title="Server Settings",
			description=f"Adjust server-specific settings! ⚙️"
		)
		view = discord.ui.View()
		view.add_item(Serversettings_Dropdown())
		await interaction.response.send_message(embed=embed, view=view)

	@app_commands.command(name="settings", description="Adjust user-specific settings! ⚙️")
	@app_commands.guild_only()
	@app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
	async def serversettings(self, interaction:  discord.Interaction):
		embed = discord.Embed(
			color=3092790,
			title="User Settings",
			description=f"Adjust user-specific settings! ⚙️"
		)
		view = discord.ui.View()
		view.add_item(Usersettings_Dropdown())
		await interaction.response.send_message(embed=embed, view=view)
	

class Serversettings_Dropdown(discord.ui.Select):
	def __init__(self, default = -1):

		options = [
			discord.SelectOption(label="Dank's Grinder Manager", description='Manage Dank Grinders', emoji='<:tgk_cc:1150394902585290854>'),
			discord.SelectOption(label='Dank Payout Management', description='Manage Dank Payouts', emoji='<:level_roles:1123938667212312637>'),
			discord.SelectOption(label='Dank Pool Access', description="Who all can access Server's Donation Pool", emoji='<:tgk_bank:1073920882130558987>'),
			discord.SelectOption(label='Mafia Logs Setup', description='Log entire game', emoji='<:tgk_amongUs:1103542462628253726>'),
			discord.SelectOption(label='Server Lockdown', description='Configure Lockdown Profiles', emoji='<:tgk_lock:1072851190213259375>'),
			discord.SelectOption(label="Private Voice", description='Create a private voice channel', emoji='<:tgk_voice:1156454028109168650>')
		]
		if default != -1:
			options[default].default = True
		super().__init__(placeholder='What would you like to configure today?', min_values=1, max_values=1, options=options, row=0)

	async def callback(self, interaction: discord.Interaction):
		
		match self.values[0]:
			
			case "Dank Pool Access":
				data = await interaction.client.dankSecurity.find(interaction.guild.id)
				if data is None:
					data = { 
						"_id": interaction.guild.id, 
						"event_manager": None, 
						"whitelist": [], 
						"quarantine": None, 
						"enable_logging":False, 
						"logs_channel": None,
						"enabled": False
					}
					await interaction.client.dankSecurity.upsert(data)
				if not (interaction.user.id == interaction.guild.owner.id or interaction.user.id in interaction.client.owner_ids):
					embed = discord.Embed(
						color=3092790,
						title="Dank Pool Access",
						description=f"- Only the server owner can configure this! \n- Contact {interaction.guild.owner.mention} if you need this changed."
					)
					self.view.stop()
					nat_changelog_view = discord.ui.View()
					nat_changelog_view.add_item(Serversettings_Dropdown(2))
					await interaction.response.edit_message(embed=embed, view=nat_changelog_view)
					nat_changelog_view.message = await interaction.original_response()
				else:
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
					
					event_manager_error = ''
					if event_manager is None:
						event_manager = f"**`None`**"
					else:
						event_manager = interaction.guild.get_role(int(event_manager))
						if event_manager is not None:
							if event_manager.position > interaction.guild.me.top_role.position:
								event_manager_error = f"> The {event_manager.mention} role is higher than my top role. \n > I cannot remove it from **raiders**."
							event_manager = f"**{event_manager.mention} (`{event_manager.id}`)**"
						else:
							data['event_manager'] = None
							await interaction.client.dankSecurity.upsert(data)
							event_manager = f"**`None`**"

						
					quarantine = data['quarantine']

					if quarantine is None:
						quarantine = f"**`None`**"
					else:
						quarantine = interaction.guild.get_role(int(quarantine))
						if quarantine is not None:
							quarantine = f"**{quarantine.mention} (`{quarantine.id}`)**"
						else:
							data['quarantine'] = None
							await interaction.client.dankSecurity.upsert(data)
							quarantine = f"**`None`**"
					
					channel = data['logs_channel']

					if channel is None:
						channel = f"**`None`**"
					else:
						channel = interaction.guild.get_channel(int(channel))
						if channel is not None:
							channel = f"**{channel.mention} (`{channel.name}`)**"
						else:
							data['logs_channel'] = None
							await interaction.client.mafiaConfig.upsert(data)
							channel = f"**`None`**"

					embed = discord.Embed(
						color=3092790,
						title="Dank Pool Access"
					)
					embed.add_field(name="Following users are whitelisted:", value=f"{users}", inline=False)
					embed.add_field(name="Event Manager Role:", value=f"{event_manager}", inline=False)
					embed.add_field(name="Quarantine Role:", value=f"{quarantine}", inline=False)
					embed.add_field(name="Logging Channel:", value=f"{channel}", inline=False)
					if event_manager_error != '':
						embed.add_field(name="<a:nat_warning:1062998119899484190> Warning: <a:nat_warning:1062998119899484190>", value=f"{event_manager_error}", inline=False)

					self.view.stop()
					nat_changelog_view =  Dank_Pool_Panel(interaction, data)

					nat_changelog_view.add_item(Serversettings_Dropdown(2))
					
					await interaction.response.edit_message(embed=embed, view=nat_changelog_view)
					nat_changelog_view.message = await interaction.original_response()

			case "Mafia Logs Setup":

				data = await interaction.client.mafiaConfig.find(interaction.guild.id)
				if data is None:
					data = {"_id": interaction.guild.id, "enable_logging":False, "logs_channel": None, "message_logs": []}
					await interaction.client.mafiaConfig.upsert(data)

				channel = data['logs_channel']

				if channel is None:
					channel = f"**`None`**"
				else:
					channel = interaction.guild.get_channel(int(channel))
					if channel is not None:
						channel = f"**{channel.mention} (`{channel.name}`)**"
					else:
						data['logs_channel'] = None
						await interaction.client.mafiaConfig.upsert(data)
						channel = f"**`None`**"

				embed = discord.Embed(
					color=3092790,
					title="Mafia Logs Setup"
				)
				embed.add_field(name="Logging Channel:", value=f"{channel}", inline=False)

				self.view.stop()
				mafia_view = Mafia_Panel(interaction , data)

				# Initialize the button
				if data['enable_logging']:
					mafia_view.children[0].style = discord.ButtonStyle.gray
					mafia_view.children[0].label = 'Logging Enabled'
					mafia_view.children[0].emoji = "<:toggle_on:1123932825956134912>"
				else:
					mafia_view.children[0].style = discord.ButtonStyle.gray
					mafia_view.children[0].label = 'Logging Disabled'
					mafia_view.children[0].emoji = "<:toggle_off:1123932890993020928>"

				mafia_view.add_item(Serversettings_Dropdown(3))

				await interaction.response.edit_message(embed=embed, view=mafia_view)
				mafia_view.message = await interaction.original_response()
		
			case "Dank Payout Management":
				data = await interaction.client.payouts.get_config(interaction.guild.id)
				
				embed = discord.Embed(title="Dank Payout Management", color=3092790)
				
				if isinstance(data['claim_channel'], discord.Webhook):
					try:
						channel = f"{data['claim_channel'].channel.mention}"
					except:
						channel = f"`None`"
				else:
					channel = f"`None`"
				embed.add_field(name="Claim Channel:", value=f"> {channel}", inline=True)

				if isinstance(data['claimed_channel'], discord.Webhook):
					try:
						channel = f"{data['claimed_channel'].channel.mention}"
					except:
						channel = f"`None`"
				else:
					channel = f"`None`"
				embed.add_field(name="Queue Channel:", value=f"> {channel}", inline=True)

				channel = interaction.guild.get_channel(data['log_channel'])
				if channel is None:
					channel = f"`None`"
				else:
					channel = f"{channel.mention}"
				embed.add_field(name="Payouts Channel:", value=f"> {channel}", inline=True)

				embed.add_field(name="Claim Time:", value=f"> **{humanfriendly.format_timespan(data['default_claim_time'])}**", inline=True)

				roles = data['manager_roles']
				roles = [interaction.guild.get_role(role) for role in roles if interaction.guild.get_role(role) is not None]
				roles = [role.mention for role in roles]
				role = ", ".join(roles)
				if len(roles) == 0 :
					role = f"`None`"
				embed.add_field(name="Payout Managers (Admin):", value=f"> {role}", inline=False)

				roles = data['event_manager_roles']
				roles = [interaction.guild.get_role(role) for role in roles if interaction.guild.get_role(role) is not None]
				roles = [role.mention for role in roles]
				role = ", ".join(roles)
				if len(roles) == 0:
					role = f"`None`"
				embed.add_field(name="Staff Roles (Queue Payouts):", value=f"> {role}", inline=False)
				
				self.view.stop()
				payouts_view = Payouts_Panel(interaction , data)

				# Initialize the button
				if data['enable_payouts']:
					payouts_view.children[0].style = discord.ButtonStyle.gray
					payouts_view.children[0].label = 'Module Enabled'
					payouts_view.children[0].emoji = "<:toggle_on:1123932825956134912>"
				else:
					payouts_view.children[0].style = discord.ButtonStyle.gray
					payouts_view.children[0].label = 'Module Disabled'
					payouts_view.children[0].emoji = "<:toggle_off:1123932890993020928>"

				payouts_view.add_item(Serversettings_Dropdown(1))

				await interaction.response.edit_message(embed=embed, view=payouts_view)
				payouts_view.message = await interaction.original_response()
  
			case "Server Lockdown":

				data = await interaction.client.lockdown.find(interaction.guild.id)
				if not data:
					data = {"_id": interaction.guild.id, "lockdown_profiles": []}
					await interaction.client.lockdown.upsert(data)

				if data['lockdown_profiles'] is None or len(data['lockdown_profiles']) == 0:
					profiles = f"` - ` **Add lockdown protocols when?**\n"
				else:
					profiles = ""
					for profile in data['lockdown_profiles']:
						profiles += f"` - ` **{profile.title()}**\n"

				embed = discord.Embed(
					color=3092790,
					title="Configure Server Lockdown"
				)
				embed.add_field(name="Declared protocols are:", value=f"{profiles}", inline=False)
				
				self.view.stop()
				lockdown_profile_view =  Lockdown_Profile_Panel(interaction)			
				lockdown_profile_view.add_item(Serversettings_Dropdown(4))
				await interaction.response.edit_message(embed=embed, view=lockdown_profile_view)
				lockdown_profile_view.message = await interaction.original_response()

				await interaction.message.edit(embed=embed, view=lockdown_profile_view)
				lockdown_profile_view.message = await interaction.original_response()

			case "Private Voice":
				data = await interaction.client.vc_config.find(interaction.guild.id)
				if not data:
					data = {
						'_id': interaction.guild.id,
						'join_create': None,
						'enabled': False,
					}
					await interaction.client.vc_config.insert(data)
				embed = discord.Embed(
					color=3092790,
					title="Private Voice"
				)
				channel = interaction.guild.get_channel(data['join_create'])
				if channel is None:
					channel = f"`None`"
				else:
					channel = f"{channel.mention}"
				embed.add_field(name="Join to create:", value=f"{channel}", inline=False)
				self.view.stop()
				voice_view = Voice_config(interaction.user , data)
				voice_view.add_item(Serversettings_Dropdown(5))

				await interaction.response.edit_message(embed=embed, view=voice_view)
				voice_view.message = await interaction.original_response()

				pass
			
			case _:
				self.view.stop()
				nat_changelog_view = discord.ui.View()
				nat_changelog_view.add_item(Serversettings_Dropdown(0))
				embed = await get_invisible_embed(f"<:tgk_activeDevelopment:1088434070666612806> **|** This module is under development...")
				await interaction.response.edit_message( 
					embed=embed, 
					view=nat_changelog_view
				)
				nat_changelog_view.message = await interaction.original_response()

class Usersettings_Dropdown(discord.ui.Select):
	def __init__(self, default = -1):

		options = [
			discord.SelectOption(label='Fish Events', description='Get DMs for active events', emoji='<:tgk_fishing:1196665275794325504>'),
			discord.SelectOption(label='Nat Changelogs', description='Get DMs for patch notes', emoji='<:tgk_entries:1124995375548338176>'),
		]
		if default != -1:
			options[default].default = True
		super().__init__(placeholder='What would you like to configure today?', min_values=1, max_values=1, options=options, row=0)

	async def callback(self, interaction: discord.Interaction):
		
		match self.values[0]:

			case "Fish Events":

				data = await interaction.client.userSettings.find(interaction.user.id)
				if data is None:
					data = {"_id": interaction.user.id, "fish_events": False}
					await interaction.client.userSettings.upsert(data)
				if 'fish_events' not in data:
					data['fish_events'] = False
					await interaction.client.userSettings.upsert(data)

				embed = discord.Embed(
					color=3092790,
					title="Fish Events",
					description= 	f"Want to be reminded of active dank fish events?"
				)

				self.view.stop()
				nat_changelogs_view =  Fish_Panel(interaction, data)

				# Initialize the button
				if data['fish_events']:
					nat_changelogs_view.children[0].style = discord.ButtonStyle.green
					nat_changelogs_view.children[0].label = "Yes, I would love to know!"
					nat_changelogs_view.children[0].emoji = "<:tgk_active:1082676793342951475>"
					label = f'<:tgk_active:1082676793342951475> Enabled'
				else:
					nat_changelogs_view.children[0].style = discord.ButtonStyle.red
					nat_changelogs_view.children[0].label = "No, I don't fish."
					nat_changelogs_view.children[0].emoji = "<:tgk_deactivated:1082676877468119110>"
					label = f'<:tgk_deactivated:1082676877468119110> Disabled'
				embed.add_field(name="Current Status:", value=f"> {label}", inline=False)

				nat_changelogs_view.add_item(Usersettings_Dropdown(0))

				await interaction.response.edit_message(embed=embed, view=nat_changelogs_view)
				nat_changelogs_view.message = await interaction.original_response()

			case "Nat Changelogs":

				data = await interaction.client.userSettings.find(interaction.user.id)
				if data is None:
					data = {"_id": interaction.user.id, "changelog_dms": False}
					await interaction.client.userSettings.upsert(data)
				if 'changelog_dms' not in data:
					data['changelog_dms'] = False
					await interaction.client.userSettings.upsert(data)

				embed = discord.Embed(
					color=3092790,
					title="Nat Changelogs",
					description= 	f"- In case you own multiple servers: \n - Settings will sync across all servers.\n - Will be dm'ed once per patch note.\n"
									f"- Join our bot's [`support server`](https://discord.gg/C44Hgr9nDQ) for latest patch notes!"
				)

				self.view.stop()
				nat_changelogs_view =  Changelogs_Panel(interaction, data)

				# Initialize the button
				if data['changelog_dms']:
					nat_changelogs_view.children[0].style = discord.ButtonStyle.green
					nat_changelogs_view.children[0].label = "Yes, I would love to know what's new!"
					nat_changelogs_view.children[0].emoji = "<:tgk_active:1082676793342951475>"
					label = f'<:tgk_active:1082676793342951475> Enabled'
				else:
					nat_changelogs_view.children[0].style = discord.ButtonStyle.red
					nat_changelogs_view.children[0].label = 'No, I follow the changelogs channel.'
					nat_changelogs_view.children[0].emoji = "<:tgk_deactivated:1082676877468119110>"
					label = f'<:tgk_deactivated:1082676877468119110> Disabled'
				embed.add_field(name="Current Status:", value=f"> {label}", inline=False)

				nat_changelogs_view.add_item(Usersettings_Dropdown(1))

				await interaction.response.edit_message(embed=embed, view=nat_changelogs_view)
				nat_changelogs_view.message = await interaction.original_response()

			case _:
				self.view.stop()
				nat_changelog_view = discord.ui.View()
				nat_changelog_view.add_item(Usersettings_Dropdown(0))
				embed = await get_invisible_embed(f"<:tgk_activeDevelopment:1088434070666612806> **|** This module is under development...")
				await interaction.response.edit_message( 
					embed=embed, 
					view=nat_changelog_view
				)
				nat_changelog_view.message = await interaction.original_response()

async def setup(bot):
	await bot.add_cog(serverUtils(bot))
	print(f"loaded serverUtils cog")