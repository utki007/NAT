import asyncio
import datetime
from itertools import islice

import discord
from discord import Interaction
from discord.ui import RoleSelect, UserSelect
import asyncio

import pytz

from utils.embeds import (get_error_embed, get_invisible_embed,
						  get_success_embed, get_warning_embed)
from utils.views.modal import General_Modal
from utils.views.paginator import Paginator
from utils.views.selects import Select_General
from utils.views.ui import Dropdown_Channel

utc = datetime.timezone.utc

def chunk(it, size):
	it = iter(it)
	return iter(lambda: tuple(islice(it, size)), ())

async def update_changelogs_embed(interaction: Interaction, data: dict):

	embed = discord.Embed(
		color=3092790,
		title="Nat Changelogs",
		description= 	f"- In case you own multiple servers: \n - Settings will sync across all servers.\n - Will be dm'ed once per patch note.\n"
						f"- Join our bot's [`support server`](https://discord.gg/C44Hgr9nDQ) for latest patch notes!"
	)
	if data['changelog_dms']:
		value = f'<:tgk_active:1082676793342951475> Enabled'
	else:
		value = f'<:tgk_deactivated:1082676877468119110> Disabled'
	embed.add_field(name="Current Status:", value=f"> {value}", inline=False)

	return embed

async def update_fish_embed(interaction: Interaction, data: dict):

	embed = discord.Embed(
		color=3092790,
		title="Dank Reminders",
		description= f"Want to be dm'ed for dank-related events?"
	)
	if data['fish_events']:
		label = f'<:tgk_active:1082676793342951475> Enabled'
	else:
		label = f'<:tgk_deactivated:1082676877468119110> Disabled'
	embed.add_field(name="Fish Event:", value=f"> {label}", inline=True)

	if data['gboost']:
		label = f'<:tgk_active:1082676793342951475> Enabled'
	else:
		label = f'<:tgk_deactivated:1082676877468119110> Disabled'
	embed.add_field(name="Global Boost:", value=f"> {label}", inline=True)
	embed.add_field(name="\u200b", value='\u200b', inline=True)
	return embed

async def update_cric_embed(interaction: Interaction, data: dict):

	embed = discord.Embed(
		color=3092790,
		title="Cricket Reminders",
		description= f"Want to be dm'ed for cricket-related events?"
	)
	if data['cric_drop_events']:
		label = f'Status: <:tgk_active:1082676793342951475>'
	else:
		label = f'Status: <:tgk_deactivated:1082676877468119110>'
	embed.add_field(name="<:cg_drop:1291242737215082537> Drop:", value=f"> {label}", inline=False)

	if data['cric_daily']:
		label = f'Status: <:tgk_active:1082676793342951475>'
	else:
		label = f'Status: <:tgk_deactivated:1082676877468119110>'
	embed.add_field(name="<:cg_daily:1291240470705602662> Daily:", value=f"> {label}", inline=False)

	if data['cric_vote']:
		label = f'Status: <:tgk_active:1082676793342951475>'
	else:
		label = f'Status: <:tgk_deactivated:1082676877468119110>'
	embed.add_field(name="<:cg_vote:1291240797286432889> Vote:", value=f"> {label}", inline=False)

	if data['cric_weekly']:
		label = f'Status: <:tgk_active:1082676793342951475>'
	else:
		label = f'Status: <:tgk_deactivated:1082676877468119110>'
	embed.add_field(name="<:cg_weekly:1291240548040179742> Weekly:", value=f"> {label}", inline=False)

	if data['cric_monthly']:
		label = f'Status: <:tgk_active:1082676793342951475>'
	else:
		label = f'Status: <:tgk_deactivated:1082676877468119110>'
	embed.add_field(name="<:cg_monthly:1291240620353912864> Monthly:", value=f"> {label}", inline=False)
	return embed

async def update_timestamp_embed(interaction: Interaction, data: dict):

	if data['timezone'] is None:
		timezone = "**None**"
	else:
		timezone = f"**{data['timezone']}**"

	embed = discord.Embed(
		color=3092790,
		title="Select your timezone",
		description= 	f"Your current timezone is {timezone}.\n"
	)
	return embed


async def update_grinder_embed(interaction: Interaction, time: int):

	date = datetime.datetime.now(tz=utc)
	timestamp = f"<t:{int(datetime.datetime(date.year, date.month, date.day, time, tzinfo = datetime.timezone.utc).timestamp())}:t>"
	embed = discord.Embed(
		color=3092790,
		title="Grinder Reminder",
		description= 	f"Your current reminder time is **{timestamp}**."
	)
	return embed

class Changelogs_Panel(discord.ui.View):
	def __init__(self, interaction: discord.Interaction, data: dict):
		super().__init__(timeout=180)
		self.interaction = interaction
		self.message = None # req for disabling buttons after timeout
		self.data = data

	@discord.ui.button(label='toggle_button_label' ,row=1)
	async def toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.userSettings.find(interaction.user.id)
		if data['changelog_dms']:
			data['changelog_dms'] = False
			await interaction.client.userSettings.upsert(data)
			embed = await update_changelogs_embed(interaction, data)
			button.style = discord.ButtonStyle.green
			button.label = "Yes, I would love to know what's new!"
			button.emoji = "<:tgk_active:1082676793342951475>"
			await interaction.response.edit_message(embed=embed,view=self)
		else:
			data['changelog_dms'] = True
			await interaction.client.userSettings.upsert(data)
			embed = await update_changelogs_embed(interaction, data)
			button.style = discord.ButtonStyle.red
			button.label = 'No, I follow the changelogs channel.'
			button.emoji = "<:tgk_deactivated:1082676877468119110>"
			await interaction.response.edit_message(view=self, embed=embed)
	
	async def interaction_check(self, interaction: discord.Interaction):
		if interaction.user.id != self.interaction.user.id:
			warning = await get_invisible_embed(f"This is not for you")
			return await interaction.response.send_message(embed=warning, ephemeral=True)	
		return True

	async def on_timeout(self):
		for button in self.children:
			button.disabled = True
		
		try:
			await self.message.edit(view=self)
		except:
			pass


class User_Reminders_Panel(discord.ui.View):
	def __init__(self, interaction: discord.Interaction):
		super().__init__(timeout=180)
		self.interaction = interaction
		self.message = None # req for disabling buttons after timeout

	@discord.ui.button(label="Dank Memer", style=discord.ButtonStyle.gray, emoji="<a:dankmemeravatar:1260877621429010472>",row=1)
	async def dankReminder(self, interaction: discord.Interaction, button: discord.ui.Button):
		# disable all buttons
		for button in self.children:
			button.disabled = True
		await interaction.response.edit_message(view=self)

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

		dank_reminder_view =  Dank_Reminder_Panel(interaction, data)

		# Initialize the button
		if data['fish_events']:
			dank_reminder_view.children[0].style = discord.ButtonStyle.red
			dank_reminder_view.children[0].label = "Disable Fish Events."
			dank_reminder_view.children[0].emoji = "<:tgk_deactivated:1082676877468119110>"
			label = f'<:tgk_active:1082676793342951475> Enabled'
		else:
			dank_reminder_view.children[0].style = discord.ButtonStyle.green
			dank_reminder_view.children[0].label = "Enable Fish Events."
			dank_reminder_view.children[0].emoji = "<:tgk_active:1082676793342951475>"
			label = f'<:tgk_deactivated:1082676877468119110> Disabled'
		embed.add_field(name="Fish Event:", value=f"> {label}", inline=True)

		if data['gboost']:
			dank_reminder_view.children[1].style = discord.ButtonStyle.red
			dank_reminder_view.children[1].label = "Disable Global Boost."
			dank_reminder_view.children[1].emoji = "<:tgk_deactivated:1082676877468119110>"
			label = f'<:tgk_active:1082676793342951475> Enabled'
		else:
			dank_reminder_view.children[1].style = discord.ButtonStyle.green
			dank_reminder_view.children[1].label = "Enable Global Boost."
			dank_reminder_view.children[1].emoji = "<:tgk_active:1082676793342951475>"
			label = f'<:tgk_deactivated:1082676877468119110> Disabled'
		embed.add_field(name="Global Boost:", value=f"> {label}", inline=True)
		embed.add_field(name="\u200b", value='\u200b', inline=True)

		await interaction.followup.send(embed=embed, view=dank_reminder_view, ephemeral=False)
		dank_reminder_view.message = await interaction.original_response()
	
	@discord.ui.button(label="Cricket Guru", style=discord.ButtonStyle.gray, emoji="<:cricketguruavatar:1260884903139217429>",row=1)
	async def cricketReminder(self, interaction: discord.Interaction, button: discord.ui.Button):
		
		# disable all buttons
		for button in self.children:
			button.disabled = True
		await interaction.response.edit_message(view=self)

		data = await interaction.client.userSettings.find(interaction.user.id)
		flag = 0
		if data is None:
			data = {"_id": interaction.user.id, "cric_drop_events": False, "cric_daily": False}
			flag = 1
		if 'cric_drop_events' not in data.keys():
			data['cric_drop_events'] = False
			flag = 1
		if 'cric_daily' not in data.keys():
			data['cric_daily'] = False
			flag = 1
		if 'cric_vote' not in data.keys():
			data['cric_vote'] = False
			flag = 1
		if 'cric_weekly' not in data.keys():
			data['cric_weekly'] = False
			flag = 1
		if 'cric_monthly' not in data.keys():
			data['cric_monthly'] = False
			flag = 1

		if flag == 1:
			await interaction.client.userSettings.upsert(data)
		
		embed = discord.Embed(
			color=3092790,
			title="Cricket Reminders",
			description= f"Want to be dm'ed for cricket-related events?"
		)

		cricket_reminder_view =  Cricket_Reminder_Panel(interaction, data)

		# Initialize the button
		if data['cric_drop_events']:
			cricket_reminder_view.children[0].style = discord.ButtonStyle.green
			cricket_reminder_view.children[0].emoji = "<:cg_drop:1291242737215082537>"
			label = f'Status: <:tgk_active:1082676793342951475>'
		else:
			cricket_reminder_view.children[0].style = discord.ButtonStyle.red
			cricket_reminder_view.children[0].emoji = "<:cg_drop:1291242737215082537>"
			label = f'Status: <:tgk_deactivated:1082676877468119110>'
		embed.add_field(name="<:cg_drop:1291242737215082537> Drop:", value=f"> {label}", inline=False)

		if data['cric_daily']:
			cricket_reminder_view.children[1].style = discord.ButtonStyle.green
			cricket_reminder_view.children[1].emoji = "<:cg_daily:1291240470705602662>"
			label = f'Status: <:tgk_active:1082676793342951475>'
		else:
			cricket_reminder_view.children[1].style = discord.ButtonStyle.red
			cricket_reminder_view.children[1].emoji = "<:cg_daily:1291240470705602662>"
			label = f'Status: <:tgk_deactivated:1082676877468119110>'
		embed.add_field(name="<:cg_daily:1291240470705602662> Daily:", value=f"> {label}", inline=False)

		if data['cric_vote']:
			cricket_reminder_view.children[2].style = discord.ButtonStyle.green
			cricket_reminder_view.children[2].emoji = "<:cg_vote:1291240797286432889>"
			label = f'Status: <:tgk_active:1082676793342951475>'
		else:
			cricket_reminder_view.children[2].style = discord.ButtonStyle.red
			cricket_reminder_view.children[2].emoji = "<:cg_vote:1291240797286432889>"
			label = f'Status: <:tgk_deactivated:1082676877468119110>'
		embed.add_field(name="<:cg_vote:1291240797286432889> Vote:", value=f"> {label}", inline=False)

		if data['cric_weekly']:
			cricket_reminder_view.children[3].style = discord.ButtonStyle.green
			cricket_reminder_view.children[3].emoji = "<:cg_weekly:1291240548040179742>"
			label = f'Status: <:tgk_active:1082676793342951475>'
		else:
			cricket_reminder_view.children[3].style = discord.ButtonStyle.red
			cricket_reminder_view.children[3].emoji = "<:cg_weekly:1291240548040179742>"
			label = f'Status: <:tgk_deactivated:1082676877468119110>'
		embed.add_field(name="<:cg_weekly:1291240548040179742> Weekly:", value=f"> {label}", inline=False)

		if data['cric_monthly']:
			cricket_reminder_view.children[4].style = discord.ButtonStyle.green
			cricket_reminder_view.children[4].emoji = "<:cg_monthly:1291240620353912864>"
			label = f'Status: <:tgk_active:1082676793342951475>'
		else:
			cricket_reminder_view.children[4].style = discord.ButtonStyle.red
			cricket_reminder_view.children[4].emoji = "<:cg_monthly:1291240620353912864>"
			label = f'Status: <:tgk_deactivated:1082676877468119110>'
		embed.add_field(name="<:cg_monthly:1291240620353912864> Monthly:", value=f"> {label}", inline=False)

		await interaction.followup.send(embed=embed, view=cricket_reminder_view, ephemeral=False)
		cricket_reminder_view.message = await interaction.original_response()

	async def interaction_check(self, interaction: discord.Interaction):
		if interaction.user.id != self.interaction.user.id:
			warning = await get_invisible_embed(f"This is not for you")
			return await interaction.response.send_message(embed=warning, ephemeral=True)	
		return True

	async def on_timeout(self):
		for button in self.children:
			button.disabled = True
		try:
			await self.message.edit(view=self)
		except:
			pass

class Dank_Reminder_Panel(discord.ui.View):
	def __init__(self, interaction: discord.Interaction, data: dict):
		super().__init__(timeout=180)
		self.interaction = interaction
		self.message = None # req for disabling buttons after timeout
		self.data = data

	@discord.ui.button(label='toggle_button_label' ,row=1)
	async def fishEvent(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.userSettings.find(interaction.user.id)
		if data['fish_events']:
			data['fish_events'] = False
			await interaction.client.userSettings.upsert(data)
			embed = await update_fish_embed(interaction, data)
			button.style = discord.ButtonStyle.green
			button.label = "Enable Fish Event."
			button.emoji = "<:tgk_active:1082676793342951475>"
			await interaction.response.edit_message(embed=embed,view=self)
		else:
			data['fish_events'] = True
			await interaction.client.userSettings.upsert(data)
			embed = await update_fish_embed(interaction, data)
			button.style = discord.ButtonStyle.red
			button.label = "Disable Fish Event."
			button.emoji = "<:tgk_deactivated:1082676877468119110>"
			await interaction.response.edit_message(view=self, embed=embed)
	
	@discord.ui.button(label='toggle_button_label' ,row=1)
	async def gboost(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.userSettings.find(interaction.user.id)
		if data['gboost']:
			data['gboost'] = False
			await interaction.client.userSettings.upsert(data)
			embed = await update_fish_embed(interaction, data)
			button.style = discord.ButtonStyle.green
			button.label = "Enable Global Boost."
			button.emoji = "<:tgk_active:1082676793342951475>"
			await interaction.response.edit_message(embed=embed,view=self)
		else:
			data['gboost'] = True
			await interaction.client.userSettings.upsert(data)
			embed = await update_fish_embed(interaction, data)
			button.style = discord.ButtonStyle.red
			button.label = "Disable Global Boost."
			button.emoji = "<:tgk_deactivated:1082676877468119110>"
			await interaction.response.edit_message(view=self, embed=embed)
	
	
	async def interaction_check(self, interaction: discord.Interaction):
		if interaction.user.id != self.interaction.user.id:
			warning = await get_invisible_embed(f"This is not for you")
			return await interaction.response.send_message(embed=warning, ephemeral=True)	
		return True

	async def on_timeout(self):
		for button in self.children:
			button.disabled = True
		
		try:
			await self.message.edit(view=self)
		except:
			pass

class Cricket_Reminder_Panel(discord.ui.View):
	def __init__(self, interaction: discord.Interaction, data: dict):
		super().__init__(timeout=180)
		self.interaction = interaction
		self.message = None # req for disabling buttons after timeout
		self.data = data

	@discord.ui.button(emoji = "<:cg_drop:1291242737215082537>", row=1)
	async def dropEvent(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.userSettings.find(interaction.user.id)
		if data['cric_drop_events']:
			data['cric_drop_events'] = False
			await interaction.client.userSettings.upsert(data)
			embed = await update_cric_embed(interaction, data)
			button.style = discord.ButtonStyle.red
			await interaction.response.edit_message(embed=embed,view=self)
		else:
			data['cric_drop_events'] = True
			await interaction.client.userSettings.upsert(data)
			embed = await update_cric_embed(interaction, data)
			button.style = discord.ButtonStyle.green
			await interaction.response.edit_message(view=self, embed=embed)
	
	@discord.ui.button(emoji = "<:cg_daily:1291240470705602662>", row=1)
	async def dailyEvent(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.userSettings.find(interaction.user.id)
		if data['cric_daily']:
			data['cric_daily'] = False
			await interaction.client.userSettings.upsert(data)
			embed = await update_cric_embed(interaction, data)
			button.style = discord.ButtonStyle.red
			await interaction.response.edit_message(embed=embed,view=self)
		else:
			data['cric_daily'] = True
			await interaction.client.userSettings.upsert(data)
			embed = await update_cric_embed(interaction, data)
			button.style = discord.ButtonStyle.green
			await interaction.response.edit_message(view=self, embed=embed)
	
	@discord.ui.button(emoji = "<:cg_vote:1291240797286432889>", row=1)
	async def voteEvent(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.userSettings.find(interaction.user.id)
		if data['cric_vote']:
			data['cric_vote'] = False
			await interaction.client.userSettings.upsert(data)
			embed = await update_cric_embed(interaction, data)
			button.style = discord.ButtonStyle.red
			await interaction.response.edit_message(embed=embed,view=self)
		else:
			data['cric_vote'] = True
			await interaction.client.userSettings.upsert(data)
			embed = await update_cric_embed(interaction, data)
			button.style = discord.ButtonStyle.green
			await interaction.response.edit_message(view=self, embed=embed)

	@discord.ui.button(emoji = "<:cg_weekly:1291240548040179742>", row=1)
	async def weeklyEvent(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.userSettings.find(interaction.user.id)
		if data['cric_weekly']:
			data['cric_weekly'] = False
			await interaction.client.userSettings.upsert(data)
			embed = await update_cric_embed(interaction, data)
			button.style = discord.ButtonStyle.red
			await interaction.response.edit_message(embed=embed,view=self)
		else:
			data['cric_weekly'] = True
			await interaction.client.userSettings.upsert(data)
			embed = await update_cric_embed(interaction, data)
			button.style = discord.ButtonStyle.green
			await interaction.response.edit_message(view=self, embed=embed)
	
	@discord.ui.button(emoji = "<:cg_monthly:1291240620353912864>", row=1)
	async def monthlyEvent(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.userSettings.find(interaction.user.id)
		if data['cric_monthly']:
			data['cric_monthly'] = False
			await interaction.client.userSettings.upsert(data)
			embed = await update_cric_embed(interaction, data)
			button.style = discord.ButtonStyle.red
			await interaction.response.edit_message(embed=embed,view=self)
		else:
			data['cric_monthly'] = True
			await interaction.client.userSettings.upsert(data)
			embed = await update_cric_embed(interaction, data)
			button.style = discord.ButtonStyle.green
			await interaction.response.edit_message(view=self, embed=embed)

	async def interaction_check(self, interaction: discord.Interaction):
		if interaction.user.id != self.interaction.user.id:
			warning = await get_invisible_embed(f"This is not for you")
			return await interaction.response.send_message(embed=warning, ephemeral=True)	
		return True

	async def on_timeout(self):
		for button in self.children:
			button.disabled = True
		
		try:
			await self.message.edit(view=self)
		except:
			pass


class Timestamp_Panel(discord.ui.View):
	def __init__(self, interaction: discord.Interaction, data: dict):
		super().__init__(timeout=180)
		self.interaction = interaction
		self.message = None # req for disabling buttons after timeout
		self.data = data

	@discord.ui.button(label="Set Timezone", style=discord.ButtonStyle.gray, emoji="<:tgk_clock:1198684272446414928>",row=1)
	async def setTimezone(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.userSettings.find(interaction.user.id)
		if data is None:
			data = {"_id": interaction.user.id, "timezone": None}
			await interaction.client.userSettings.upsert(data)
		if 'timezone' not in data.keys():
			data['timezone'] = None
			await interaction.client.userSettings.upsert(data)
		
		modal = General_Modal("Set your timezone!", interaction=interaction)
		modal.question = discord.ui.TextInput(label="Enter your timezone:", placeholder="Enter timezone like Asia/Kolkata", min_length=4, max_length=100)    
		modal.value = None
		modal.add_item(modal.question)
		await interaction.response.send_modal(modal)

		await modal.wait()
		if modal.value:
			currentTimezone = modal.question.value
			if currentTimezone not in pytz.all_timezones:
				return await modal.interaction.response.send_message(embed = await get_error_embed('Invalid timezone! Search for your timezone [here](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) .'), ephemeral=True)
			data['timezone'] = currentTimezone
			await interaction.client.userSettings.upsert(data)
			embed = await update_timestamp_embed(self.interaction, data)
			await modal.interaction.response.edit_message(embed=embed, view=self)

	@discord.ui.button(label="Reset Timezone", style=discord.ButtonStyle.red, emoji="<:tgk_delete:1113517803203461222>",row=1)
	async def resetTimezone(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.userSettings.find(interaction.user.id)
		if 'timezone' not in data.keys():
			data['timezone'] = None
			await interaction.client.userSettings.upsert(data)
		if data['timezone'] is None:
			return await interaction.response.send_message(embed = await get_error_embed('Set your timezone first.'), ephemeral=True)
		data['timezone'] = None
		await interaction.client.userSettings.upsert(data)
		embed = await update_timestamp_embed(self.interaction, data)
		await interaction.response.edit_message(embed=embed, view=self)

	async def interaction_check(self, interaction: discord.Interaction):
		if interaction.user.id != self.interaction.user.id:
			warning = await get_invisible_embed(f"This is not for you")
			return await interaction.response.send_message(embed=warning, ephemeral=True)	
		return True

	async def on_timeout(self):
		for button in self.children:
			button.disabled = True
		
		try:
			await self.message.edit(view=self)
		except:
			pass

class Grinder_Reminder_Panel(discord.ui.View):
	def __init__(self, interaction: discord.Interaction, data: dict):
		super().__init__(timeout=180)
		self.interaction = interaction
		self.message = None # req for disabling buttons after timeout
		self.data = data

	@discord.ui.button(label="Set Time", style=discord.ButtonStyle.gray, emoji="<:tgk_clock:1198684272446414928>",row=1)
	async def setTimezone(self, interaction: discord.Interaction, button: discord.ui.Button):

		view = discord.ui.View()
		view.value = None
		view.select = Select_General(interaction=interaction, options=[
			discord.SelectOption(label=f"{i if i>9 else f'0{i}'}:00 (UTC)", value=int(i))
			for i in range(0, 24)
		], placeholder = "Choose a time to get grinder reminders.", min_values=1, max_values=1, disabled=False)
		view.add_item(view.select)

		await interaction.response.send_message(view=view, ephemeral=True)

		await view.wait()
		if view.value != True:
			return await interaction.delete_original_response()
		
		try:
			time = int(view.select.values[0])
			if time > 23 or time < 0:
				return await view.select.interaction.response.edit_message(embed = await get_error_embed('Invalid time chosen! '), view=None, ephemeral=True)
		except:
			return await view.select.interaction.response.edit_message(embed = await get_error_embed('Invalid time chosen! Please choose a number between 0 to 23.'), view=None, ephemeral=True)
		utc = datetime.timezone.utc
		reminder_time = str(datetime.time(hour=int(time), tzinfo=utc))
		await interaction.client.grinderUsers.update_many_by_custom({'user': interaction.user.id}, {'reminder_time': reminder_time})
		date = datetime.datetime.now(tz=utc)
		timestamp = f"<t:{int(datetime.datetime(date.year, date.month, date.day, time, tzinfo = datetime.timezone.utc).timestamp())}>"
	
		await view.select.interaction.response.edit_message(embed = await get_success_embed(f"Reminder time set to **{time}:00 UTC** ({timestamp})."), view=None)
		embed = await update_grinder_embed(self.interaction, time)
		await self.interaction.edit_original_response(embed=embed)

	@discord.ui.button(label="Reset Grinder Reminder", style=discord.ButtonStyle.red, emoji="<:tgk_delete:1113517803203461222>",row=1)
	async def resetTimezone(self, interaction: discord.Interaction, button: discord.ui.Button):
		time = 12
		utc = datetime.timezone.utc
		reminder_time = str(datetime.time(hour=int(time), tzinfo=utc))
		await interaction.client.grinderUsers.update_many_by_custom({'user': interaction.user.id}, {'reminder_time': reminder_time})	
		embed = await update_grinder_embed(self.interaction, time)
		await interaction.response.edit_message(embed=embed, view=self)

	async def interaction_check(self, interaction: discord.Interaction):
		if interaction.user.id != self.interaction.user.id:
			warning = await get_invisible_embed(f"This is not for you")
			return await interaction.response.send_message(embed=warning, ephemeral=True)	
		return True

	async def on_timeout(self):
		for button in self.children:
			button.disabled = True
		
		try:
			await self.message.edit(view=self)
		except:
			pass
