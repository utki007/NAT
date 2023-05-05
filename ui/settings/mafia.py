import asyncio

import discord
from discord import Interaction
from discord.ui import RoleSelect, UserSelect
import asyncio

from utils.embeds import (get_error_embed, get_invisible_embed,
                          get_success_embed, get_warning_embed)
from utils.views.ui import Dropdown_Channel

async def update_mafia_embed(interaction: Interaction, data: dict):

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

	await interaction.message.edit(embed=embed)

class Mafia_Panel(discord.ui.View):
	def __init__(self, interaction: discord.Interaction, data: dict):
		super().__init__(timeout=180)
		self.interaction = interaction
		self.message = None # req for disabling buttons after timeout
		self.data = data

	@discord.ui.button(label='toggle_button_label' ,row=1)
	async def toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.mafiaConfig.find(interaction.guild.id)
		if data['enable_logging']:
			data['enable_logging'] = False
			await interaction.client.mafiaConfig.upsert(data)
			await update_mafia_embed(interaction, data)
			button.style = discord.ButtonStyle.red
			button.label = 'Logging Disabled'
			button.emoji = "<:tgk_deactivated:1082676877468119110>"
			await interaction.response.edit_message(view=self)
		else:
			data['enable_logging'] = True
			await interaction.client.mafiaConfig.upsert(data)
			await update_mafia_embed(interaction, data)
			button.style = discord.ButtonStyle.green
			button.label = 'Logging Enabled'
			button.emoji = "<:tgk_active:1082676793342951475>"
			await interaction.response.edit_message(view=self)
	
	@discord.ui.button(label="Add/Edit Logs Channel", style=discord.ButtonStyle.gray, emoji="<:tgk_channel:1073908465405268029>",row=1)
	async def add_logs(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.mafiaConfig.find(interaction.guild.id)
		view = Dropdown_Channel(interaction)
		await interaction.response.send_message(view=view, ephemeral=True)
		await view.wait()
		if view.value is None:
			embed = await get_warning_embed(f'Dropdown timed out, please retry.')
			return await interaction.edit_original_response(
				content = None, embed = embed, view = None
			)
		else:
			channel = data['logs_channel']
			if channel is None:
				channel = f"**`None`**"
			else:
				channel = f'<#{channel}>'
			if data['logs_channel'] is None or data['logs_channel'] != view.value.id:
				data['logs_channel'] = view.value.id
				await interaction.client.mafiaConfig.upsert(data)
				embed = await get_success_embed(f'Logging Chaneel changed from {channel} to {view.value.mention}')
				await interaction.edit_original_response(
					content = None, embed = embed, view = None
				)
				await update_mafia_embed(self.interaction, data)
			else:
				embed = await get_error_embed(f"Logging Chaneel was already set to {channel}")
				return await interaction.edit_original_response(
					content = None, embed = embed, view = None
				)

	async def interaction_check(self, interaction: discord.Interaction):
		if interaction.user.id != self.interaction.user.id:
			warning = await get_invisible_embed(f"This is not for you")
			return await interaction.response.send_message(embed=warning, ephemeral=True)	
		return True

	async def on_timeout(self):
		for button in self.children:
			button.disabled = True
		
		await self.message.edit(view=self)

