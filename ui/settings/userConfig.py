import asyncio

import discord
from discord import Interaction
from discord.ui import RoleSelect, UserSelect
import asyncio

from utils.embeds import (get_error_embed, get_invisible_embed,
						  get_success_embed, get_warning_embed)
from utils.views.ui import Dropdown_Channel

async def update_embed(interaction: Interaction, data: dict):

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
		title="Fish Events",
		description= 	f"Want to be reminded of active dank fish events?"
	)
	if data['fish_events']:
		value = f'<:tgk_active:1082676793342951475> Enabled'
	else:
		value = f'<:tgk_deactivated:1082676877468119110> Disabled'
	embed.add_field(name="Current Status:", value=f"> {value}", inline=False)

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
			embed = await update_embed(interaction, data)
			button.style = discord.ButtonStyle.green
			button.label = "Yes, I would love to know what's new!"
			button.emoji = "<:tgk_active:1082676793342951475>"
			await interaction.response.edit_message(embed=embed,view=self)
		else:
			data['changelog_dms'] = True
			await interaction.client.userSettings.upsert(data)
			embed = await update_embed(interaction, data)
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
		
		await self.message.edit(view=self)


class Fish_Panel(discord.ui.View):
	def __init__(self, interaction: discord.Interaction, data: dict):
		super().__init__(timeout=180)
		self.interaction = interaction
		self.message = None # req for disabling buttons after timeout
		self.data = data

	@discord.ui.button(label='toggle_button_label' ,row=1)
	async def toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.userSettings.find(interaction.user.id)
		if data['fish_events']:
			data['fish_events'] = False
			await interaction.client.userSettings.upsert(data)
			embed = await update_fish_embed(interaction, data)
			button.style = discord.ButtonStyle.green
			button.label = "Yes, I would love to know!"
			button.emoji = "<:tgk_active:1082676793342951475>"
			await interaction.response.edit_message(embed=embed,view=self)
		else:
			data['fish_events'] = True
			await interaction.client.userSettings.upsert(data)
			embed = await update_fish_embed(interaction, data)
			button.style = discord.ButtonStyle.red
			button.label = "No, I don't fish."
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
		
		await self.message.edit(view=self)
