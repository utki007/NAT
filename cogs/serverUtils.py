import asyncio
import time as t
import datetime
import discord
from discord import app_commands, Interaction
from discord.ext import commands
import humanfriendly
import pytz
from modules.afk.View import AFKView, AFKViewUser
from ui.settings.grinder import GrinderConfigPanel
from ui.settings.mafia import Mafia_Panel
from ui.settings.payouts import Payouts_Panel
from ui.settings.userConfig import Changelogs_Panel, Fish_Panel, Grinder_Reminder_Panel, Timestamp_Panel
from utils.embeds import *
from utils.convertor import *
from utils.checks import App_commands_Checks
from io import BytesIO
from typing import List, Union
from ui.settings import *
from ui.settings.dankPool import *
from utils.functions import *
from utils.init import init_dankSecurity
from utils.views.confirm import Confirm
from utils.views.ui import *
from ui.settings.lockdown import *
from utils.views.paginator import Paginator
from itertools import islice
from ui.settings.voiceView import Voice_config

from modules.giveaways.views import GiveawayConfigView

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

	@commands.hybrid_command(name="calculate", description="Do math! 🧮", extras={'example': '/calculate query: 2m+40k'}, aliases = ['calc'])
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

	# check users current time in their timezone
	@commands.hybrid_command(name="time", description="Check your current time! ⏰")
	@app_commands.guild_only()
	@app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
	async def time(self, ctx, user: discord.Member = None):
		
		if user is None:
			user = ctx.author
		data = await self.bot.userSettings.find(user.id)
		if data is None or 'timezone' not in data.keys() or data['timezone'] is None:
			if user == ctx.author:
				return await ctx.send(embed = await get_warning_embed(f'Set your timezone first using </settings:1196688324207853590>.'))
			else:
				return await ctx.send(embed = await get_warning_embed(f'{user.mention} has not set their timezone yet.'))
		
		time = datetime.datetime.now(pytz.timezone(data['timezone'])).strftime('%I:%M %p')
		date = datetime.datetime.now(pytz.timezone(data['timezone'])).strftime('%d %B, %Y')
		timezone_name = datetime.datetime.now(pytz.timezone(data['timezone'])).strftime('%Z')
		utc_diff = datetime.datetime.now(pytz.timezone(data['timezone'])).strftime('%z')
		embed = discord.Embed(
			color=3092790
		)
		embed.add_field(name="Date:", value=f"> **{date}**", inline=True)
		embed.add_field(name="Time:", value=f"> **{time} {timezone_name} (UTC {utc_diff})**", inline=True)
		embed.set_footer(text=f"{ctx.guild.name} • {data['timezone']}",icon_url=ctx.guild.icon)
		embed.set_author(name=f"{user.display_name}'s time ...", icon_url=user.avatar)
		await ctx.reply(embed=embed, mention_author=False)

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
	@app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
	async def usersettings(self, interaction:  discord.Interaction):
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
			discord.SelectOption(label='Giveaways', description='Configure Giveaways', emoji='<:tgk_tada:1237994553932251199>'),
			discord.SelectOption(label='Mafia Logs Setup', description='Log entire game', emoji='<:tgk_amongUs:1103542462628253726>'),
			discord.SelectOption(label='Server Lockdown', description='Configure Lockdown Profiles', emoji='<:tgk_lock:1072851190213259375>'),
			discord.SelectOption(label='AFK', description='Configure AFK', emoji='<:tgk_rocket:1238009442193375304>'),
			discord.SelectOption(label="Private Voice", description='Create a private voice channel', emoji='<:tgk_voice:1156454028109168650>')
		]
		if default != -1:
			options[default].default = True
		super().__init__(placeholder='What would you like to configure today?', min_values=1, max_values=1, options=options, row=0)

	async def callback(self, interaction: discord.Interaction):
		
		match self.values[0]:
						
			case "Dank's Grinder Manager":

				data = await interaction.client.grinderSettings.find(interaction.guild.id)
				if not data:
					data = {
						"_id": interaction.guild.id,
						"payment_channel" : None,
						"grinder_logs" : None,
						"trial" : {
							"duration"	: 0,
							"role" : None
						},
						"grinder" : {
							'demotion_in' : 0,
							'role' : None
						},
						"manager_roles" : [],
						"max_profiles" : 3,
						"grinder_profiles" : {},
						"appoint_embed" : {
							'description' : f"We're excited to inform you that you've been appointed as one of our newest trial grinders! If you have any questions or need further information, feel free to reach out to us anytime. Let's make this journey memorable and enjoyable together! ",
							'thumbnail' : 'https://cdn.discordapp.com/emojis/814161045966553138.webp?size=128&quality=lossless',
						},
						"dismiss_embed" : {
							'description' : f"We understand that this may come as a disappointment, and we want to express our gratitude for your contributions during your time with us. Feel free to apply later if you're still interested.",
							'thumbnail' : 'https://cdn.discordapp.com/emojis/830548561329782815.gif?v=1',
						},
						"vacation_embed" : {
							'description' : f"We understand that you're taking a well-deserved break, and we wanted to acknowledge and support your decision. While you're away, your role as a Dank Memer grinder will be put on hold. We'll look forward to having you back on the team soon! In case of any queries, please feel free to reach out to us anytime.",
							'thumbnail' : 'https://cdn.discordapp.com/emojis/1109396272382759043.webp?size=128&quality=lossless',
						}
					}
					await interaction.client.grinderSettings.upsert(data)

				embed = discord.Embed(
					color=3092790,
					title="Configure Dank's Grinder Manager"
				)

				channel = interaction.guild.get_channel(data['payment_channel'])
				if channel is None:
					channel = f"`None`"
				else:
					channel = f"{channel.mention}"
				embed.add_field(name="Payment Channel:", value=f"<:nat_reply:1146498277068517386> {channel}", inline=True)

				channel = interaction.guild.get_channel(data['grinder_logs'])
				if channel is None:
					channel = f"`None`"
				else:
					channel = f"{channel.mention}"
				embed.add_field(name="Logs Channel:", value=f"<:nat_reply:1146498277068517386> {channel}", inline=True)
				embed.add_field(name="\u200b", value='\u200b', inline=True)

				duration = data['grinder']['demotion_in']
				role = interaction.guild.get_role(data['grinder']['role'])
				if duration == 0:
					grinder_duration = f"**Demote in:** `None`"
					kick = f"**Kicked in:** `None`"
				else:
					grinder_duration = f"**Demote in:** {format_timespan(duration)}"
					kick = f"**Kicked in:** {format_timespan(duration*2)}"
				if role is None:
					role = f"**Role:** `None`"
				else:
					role = f"**Role:** {role.mention}"
				embed.add_field(name="Grinder Config:", value=f"<:nat_replycont:1146496789361479741> {role} \n <:nat_replycont:1146496789361479741> {grinder_duration} \n<:nat_reply:1146498277068517386> {kick} ", inline=True)
				
				trial_duration = data['trial']['duration']
				trial_role = interaction.guild.get_role(data['trial']['role'])
				if trial_duration == 0:
					trial_duration = f"**Promote in:** `None`"
				else:
					trial_duration = f"**Promote in:** {format_timespan(trial_duration)}"
				if trial_role is None:
					trial_role = f"**Role:** `None`"
				else:
					trial_role = f"**Role:** {trial_role.mention}"
				embed.add_field(name="Trial Config:", value=f"<:nat_replycont:1146496789361479741> {trial_role} \n <:nat_reply:1146498277068517386> {trial_duration}", inline=True)
				embed.add_field(name="\u200b", value='\u200b', inline=True)

				roles = data['manager_roles']
				roles = [interaction.guild.get_role(role) for role in roles if interaction.guild.get_role(role) is not None]
				roles = [f'1. {role.mention}' for role in roles]
				role = "\n".join(roles)
				if len(roles) == 0 :
					role = f"` - ` Add grinder mangers when?"
				embed.add_field(name="Manager Roles:", value=f">>> {role}", inline=False)

				if len(data['grinder_profiles']) == 0:
					profiles = f"` - ` **Add profiles when?**\n"
				else:
					profiles = ""
					for key in data['grinder_profiles'].keys():
						profiles += f"1. **{data['grinder_profiles'][key]['name'].title()}** : <@&{key}>\n"
				embed.add_field(name='Grinder Profiles:', value=f">>> {profiles}", inline=False)

				self.view.stop()
				grinder_config_view =  GrinderConfigPanel(interaction)
		
				grinder_config_view.add_item(Serversettings_Dropdown(0))
				await interaction.response.edit_message(embed=embed, view=grinder_config_view)
				grinder_config_view.message = await interaction.original_response()

				await interaction.message.edit(embed=embed, view=grinder_config_view)
				grinder_config_view.message = await interaction.original_response()
		
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
				embed.add_field(name="Claim Channel:", value=f"<:nat_reply:1146498277068517386> {channel}", inline=True)

				if isinstance(data['claimed_channel'], discord.Webhook):
					try:
						channel = f"{data['claimed_channel'].channel.mention}"
					except:
						channel = f"`None`"
				else:
					channel = f"`None`"
				embed.add_field(name="Queue Channel:", value=f"<:nat_reply:1146498277068517386> {channel}", inline=True)

				channel = interaction.guild.get_channel(data['payout_channel'])
				if channel is None:
					channel = f"`None`"
				else:
					channel = f"{channel.mention}"
				embed.add_field(name="Payout Channel:", value=f"<:nat_reply:1146498277068517386> {channel}", inline=True)

				channel = interaction.guild.get_channel(data['log_channel'])
				if channel is None:
					channel = f"`None`"
				else:
					channel = f"{channel.mention}"
				embed.add_field(name="Log Payouts:", value=f"<:nat_reply:1146498277068517386> {channel}", inline=True)
				embed.add_field(name="Claim Time:", value=f"<:nat_reply:1146498277068517386> **{humanfriendly.format_timespan(data['default_claim_time'])}**", inline=True)

				roles = data['manager_roles']
				roles = [interaction.guild.get_role(role) for role in roles if interaction.guild.get_role(role) is not None]
				roles = [f'1. {role.mention}' for role in roles]
				role = "\n".join(roles)
				if len(roles) == 0 :
					role = f"`None`"
				embed.add_field(name="Payout Managers (Admin):", value=f">>> {role}", inline=False)

				roles = data['event_manager_roles']
				roles = [interaction.guild.get_role(role) for role in roles if interaction.guild.get_role(role) is not None]
				roles = [f'1. {role.mention}' for role in roles]
				role = "\n".join(roles)
				if len(roles) == 0:
					role = f"`None`"
				embed.add_field(name="Staff Roles (Queue Payouts):", value=f">>> {role}", inline=False)
				
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
  
			case "Dank Pool Access":
				data = await interaction.client.dankSecurity.find(interaction.guild.id)
				if data is None:
					data = await init_dankSecurity(interaction)
				owner_list = [interaction.guild.owner.id]
				owner = interaction.guild.owner
				if 'psuedo_owner' in data.keys():
					owner = interaction.guild.get_member(data['psuedo_owner'])
					owner_list.append(data['psuedo_owner'])
				if owner is None:
					owner = interaction.guild.owner
				if not (interaction.user.id in owner_list or interaction.user.id in interaction.client.owner_ids):
					owners = [interaction.guild.get_member(owner_id) for owner_id in owner_list if interaction.guild.get_member(owner_id) is not None]
					if len(owners) == 0:
						owners = f'{interaction.guild.owner.mention}'
					elif len(owners) == 1:
						owners = f'{owners[0].mention}'
					elif len(owners) == 2:
						owners = f'{owners[0].mention} or {owners[1].mention}'
					embed = discord.Embed(
						color=3092790,
						title="Dank Pool Access",
						description=f"- Only the server owner can configure this! \n- Contact {owners} if you need this changed."
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
					
					if 'logs_channel' not in data.keys():
						data['logs_channel'] = None
						await interaction.client.dankSecurity.upsert(data)
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

			case "Giveaways":

				self.view.stop()
				data = await interaction.client.giveaway.get_config(interaction.guild)
				embed = await interaction.client.giveaway.get_config_embed(config=data, guild=interaction.guild)
				view = GiveawayConfigView(data=data, user=interaction.user, dropdown=Serversettings_Dropdown(3))
				await interaction.response.edit_message(embed=embed, view=view)
				view.message = await interaction.original_response()

			case "Mafia Logs Setup":

				data = await interaction.client.mafiaConfig.find(interaction.guild.id)
				if data is None:
					data = {"_id": interaction.guild.id, "enable_logging":False, "logs_channel": None, "minimum_messages": 3, 'game_count': 0}
					await interaction.client.mafiaConfig.insert(data)

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
				embed.add_field(name="Minimum Messages:", value=f"{data['minimum_messages']}", inline=False)

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

				mafia_view.add_item(Serversettings_Dropdown(4))

				await interaction.response.edit_message(embed=embed, view=mafia_view)
				mafia_view.message = await interaction.original_response()

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
				grinder_config_view =  Lockdown_Profile_Panel(interaction)			
				grinder_config_view.add_item(Serversettings_Dropdown(5))
				await interaction.response.edit_message(embed=embed, view=grinder_config_view)
				grinder_config_view.message = await interaction.original_response()

				await interaction.message.edit(embed=embed, view=grinder_config_view)
				grinder_config_view.message = await interaction.original_response()

			case "AFK":
				if interaction.guild.id not in [999551299286732871, 785839283847954433]:
					self.view.stop()
					nat_changelog_view = discord.ui.View()
					nat_changelog_view.add_item(Serversettings_Dropdown(0))
					embed = await get_invisible_embed(f"<:tgk_activeDevelopment:1088434070666612806> **|** This module is under development...")
					await interaction.response.edit_message( 
						embed=embed, 
						view=nat_changelog_view
					)
					nat_changelog_view.message = await interaction.original_response()
				else:
					data = await interaction.client.afk_config.find(interaction.guild.id)
					if not data:
						data = {
							'_id': interaction.guild.id,
							'roles': [],
							'enabled': False,
						}
						await interaction.client.afk_config.insert(data)
					embed = discord.Embed(
						color=3092790,
						title="Configure AFK"
					)
					roles = data['roles']
					roles = [interaction.guild.get_role(role) for role in roles if interaction.guild.get_role(role) is not None]
					if len([role.id for role in roles]) != len(data['roles']):
						data['roles'] = [role.id for role in roles]
						await interaction.client.afk_config.upsert(data)
					if len(roles) == 0:
						roles = f"` - ` **Add roles when?**\n"
						embed.add_field(name="Roles with AFK access:", value=f"> {roles}", inline=False)
					else:
						roles = [f'1. {role.mention}' for role in roles]
						roles = "\n".join(roles)
						embed.add_field(name="Roles with AFK access:", value=f">>> {roles}", inline=False)

					self.view.stop()
					afk_view = AFKView(data=data, member=interaction.user)

					afk_view.add_item(Serversettings_Dropdown(6))

					await interaction.response.edit_message(embed=embed, view=afk_view)
					afk_view.message = await interaction.original_response()
				
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
				voice_view.add_item(Serversettings_Dropdown(7))

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
			discord.SelectOption(label='Dank Reminders', description='Get DMs for dank-related events!', emoji='<:tgk_announce:1123919566427406437>'),
			discord.SelectOption(label='Nat Changelogs', description='Get DMs for patch notes', emoji='<:tgk_entries:1124995375548338176>'),
			discord.SelectOption(label='Timezone', description='Set your timezone', emoji='<:tgk_clock:1198684272446414928>'),
			discord.SelectOption(label='Grinder Reminder', description='What time will you love to be reminded?', emoji='<:tgk_cc:1150394902585290854>'),
			discord.SelectOption(label='AFK', description='Configure AFK', emoji='<:tgk_rocket:1238009442193375304>'),
		]
		if default != -1:
			options[default].default = True
		super().__init__(placeholder='What would you like to configure today?', min_values=1, max_values=1, options=options, row=0)

	async def callback(self, interaction: discord.Interaction):
		
		match self.values[0]:

			case "Dank Reminders":

				data = await interaction.client.userSettings.find(interaction.user.id)
				flag = 0
				if data is None:
					data = {"_id": interaction.user.id, "fish_events": False, "gboost": False}
					flag = 1
				if 'fish_events' not in data.keys():
					data['fish_events'] = False
					flag = 1
				if 'gboost' not in data.keys():
					data['gboost'] = False
					flag = 1
				
				if flag == 1:
					await interaction.client.userSettings.upsert(data)

				embed = discord.Embed(
					color=3092790,
					title="Dank Reminders",
					description= f"Want to be dm'ed for dank-related events?"
				)

				self.view.stop()
				grinder_reminder_view =  Fish_Panel(interaction, data)

				# Initialize the button
				if data['fish_events']:
					grinder_reminder_view.children[0].style = discord.ButtonStyle.red
					grinder_reminder_view.children[0].label = "Disable Fish Events."
					grinder_reminder_view.children[0].emoji = "<:tgk_deactivated:1082676877468119110>"
					label = f'<:tgk_active:1082676793342951475> Enabled'
				else:
					grinder_reminder_view.children[0].style = discord.ButtonStyle.green
					grinder_reminder_view.children[0].label = "Enable Fish Events."
					grinder_reminder_view.children[0].emoji = "<:tgk_active:1082676793342951475>"
					label = f'<:tgk_deactivated:1082676877468119110> Disabled'
				embed.add_field(name="Fish Event:", value=f"> {label}", inline=True)

				if data['gboost']:
					grinder_reminder_view.children[1].style = discord.ButtonStyle.red
					grinder_reminder_view.children[1].label = "Disable Global Boost."
					grinder_reminder_view.children[1].emoji = "<:tgk_deactivated:1082676877468119110>"
					label = f'<:tgk_active:1082676793342951475> Enabled'
				else:
					grinder_reminder_view.children[1].style = discord.ButtonStyle.green
					grinder_reminder_view.children[1].label = "Enable Global Boost."
					grinder_reminder_view.children[1].emoji = "<:tgk_active:1082676793342951475>"
					label = f'<:tgk_deactivated:1082676877468119110> Disabled'
				embed.add_field(name="Global Boost:", value=f"> {label}", inline=True)
				embed.add_field(name="\u200b", value='\u200b', inline=True)

				grinder_reminder_view.add_item(Usersettings_Dropdown(0))

				await interaction.response.edit_message(embed=embed, view=grinder_reminder_view)
				grinder_reminder_view.message = await interaction.original_response()

			case "Nat Changelogs":

				data = await interaction.client.userSettings.find(interaction.user.id)
				if data is None:
					data = {"_id": interaction.user.id, "changelog_dms": False}
					await interaction.client.userSettings.upsert(data)
				if 'changelog_dms' not in data.keys():
					data['changelog_dms'] = False
					await interaction.client.userSettings.upsert(data)

				embed = discord.Embed(
					color=3092790,
					title="Nat Changelogs",
					description= 	f"- In case you own multiple servers: \n - Settings will sync across all servers.\n - Will be dm'ed once per patch note.\n"
									f"- Join our bot's [`support server`](https://discord.gg/C44Hgr9nDQ) for latest patch notes!"
				)

				self.view.stop()
				grinder_reminder_view =  Changelogs_Panel(interaction, data)

				# Initialize the button
				if data['changelog_dms']:
					grinder_reminder_view.children[0].style = discord.ButtonStyle.red
					grinder_reminder_view.children[0].label = 'No, I follow the changelogs channel.'
					grinder_reminder_view.children[0].emoji = "<:tgk_deactivated:1082676877468119110>"
					label = f'<:tgk_active:1082676793342951475> Enabled'
				else:
					grinder_reminder_view.children[0].style = discord.ButtonStyle.green
					grinder_reminder_view.children[0].label = "Yes, I would love to know what's new!"
					grinder_reminder_view.children[0].emoji = "<:tgk_active:1082676793342951475>"
					label = f'<:tgk_deactivated:1082676877468119110> Disabled'
				embed.add_field(name="Current Status:", value=f"> {label}", inline=False)

				grinder_reminder_view.add_item(Usersettings_Dropdown(1))

				await interaction.response.edit_message(embed=embed, view=grinder_reminder_view)
				grinder_reminder_view.message = await interaction.original_response()

			case "Timezone":

				data = await interaction.client.userSettings.find(interaction.user.id)
				if data is None:
					data = {"_id": interaction.user.id, "timezone": None}
					await interaction.client.userSettings.upsert(data)
				if 'timezone' not in data.keys():
					data['timezone'] = None
					await interaction.client.userSettings.upsert(data)
				
				if data['timezone'] is None:
					timezone = f"**None**"
				else:
					timezone = f"**{data['timezone']}**"

				embed = discord.Embed(
					color=3092790,
					title="Select your timezone",
					description= 	f"Your current timezone is {timezone}.\n"
				)

				self.view.stop()
				grinder_reminder_view =  Timestamp_Panel(interaction, data)

				grinder_reminder_view.add_item(Usersettings_Dropdown(2))

				await interaction.response.edit_message(embed=embed, view=grinder_reminder_view)
				grinder_reminder_view.message = await interaction.original_response()

			case "Grinder Reminder":

				datas = await interaction.client.grinderUsers.find_many_by_custom({"user":interaction.user.id})
				if len(datas) == 0:
					embed = discord.Embed(
						color=3092790,
						title="Grinder Reminder",
						description= 	f"Not an active grinder!"
					)
					return await interaction.response.edit_message(embed=embed)

				date = datetime.date.today()
				time = datetime.time.fromisoformat(datas[0]['reminder_time'])
				timestamp = f"<t:{int(datetime.datetime.combine(date, time).timestamp())}:t>"
				embed = discord.Embed(
					color=3092790,
					title="Grinder Reminder",
					description= 	f"Your current reminder time is **{timestamp}**."
				)

				self.view.stop()
				grinder_reminder_view =  Grinder_Reminder_Panel(interaction, datas[0])

				grinder_reminder_view.add_item(Usersettings_Dropdown(3))

				await interaction.response.edit_message(embed=embed, view=grinder_reminder_view)
				grinder_reminder_view.message = await interaction.original_response()

			case "AFK":
				data = await interaction.client.afk_users.find({'user_id': interaction.user.id, 'guild_id': interaction.guild.id})
				if not data:
					data = {
						'user_id': interaction.user.id,
						'guild_id': interaction.guild.id,
						'reason': None,
						'last_nick': None,
						'pings': [],
						'afk_at': None,
						'ignored_channels': [],
						'afk': False,
						'summary': False
					}
					await interaction.client.afk_users.insert(data)
				embed = discord.Embed(
					color=3092790,
					title="AFK Settings",
				)
				embed.add_field(name="Get dm'ed for pings received while afk?", value=f"You will be dm'ed for pings in **{interaction.guild.name}**.")
				self.view.stop()
				afk_view = AFKViewUser(data=data, member=interaction.user)
				afk_view.add_item(Usersettings_Dropdown(4))
				await interaction.response.edit_message(embed=embed, view=afk_view)
				afk_view.message = await interaction.original_response()

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