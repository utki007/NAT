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
from utils.views.ui import Dropdown_Channel

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

	date = datetime.date.today()
	timestamp = f"<t:{int(datetime.datetime(date.year, date.month, date.day, time, tzinfo = datetime.timezone.utc).timestamp())}>"
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

class Fish_Panel(discord.ui.View):
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
				
		modal = General_Modal("Set Grinder Reminder!", interaction=interaction)
		modal.question = discord.ui.TextInput(label="Enter hour (in UTC):", placeholder="Enter hr from 0 to 23", min_length=1, max_length=2)    
		modal.value = None
		modal.add_item(modal.question)
		await interaction.response.send_modal(modal)

		await modal.wait()
		if modal.value:
			try:
				time = int(modal.question.value)
				if time > 23 or time < 0:
					return await modal.interaction.response.send_message(embed = await get_error_embed('Invalid time chosen! Please choose a number between 0 to 23.'), ephemeral=True)
			except:
				return await modal.interaction.response.send_message(embed = await get_error_embed('Invalid time chosen! Please choose a number between 0 to 23.'), ephemeral=True)
			utc = datetime.timezone.utc
			reminder_time = str(datetime.time(hour=int(time), tzinfo=utc))
			await interaction.client.grinderUsers.update_many_by_custom({'user': interaction.user.id}, {'reminder_time': reminder_time})
			embed = await update_grinder_embed(self.interaction, time)
			await modal.interaction.response.edit_message(embed=embed, view=self)

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
