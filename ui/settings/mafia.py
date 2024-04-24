import discord
from discord import Interaction

from utils.embeds import (get_error_embed, get_invisible_embed,
                          get_success_embed, get_warning_embed)
from utils.views.ui import Dropdown_Channel
from utils.views.selects import Select_General

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
	embed.add_field(name="Minimum Messages:", value=f"{data['minimum_messages']}", inline=False)

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
			button.style = discord.ButtonStyle.gray
			button.label = 'Logging Disabled'
			button.emoji = "<:toggle_off:1123932890993020928>"
			await interaction.response.edit_message(view=self)
		else:
			data['enable_logging'] = True
			await interaction.client.mafiaConfig.upsert(data)
			await update_mafia_embed(interaction, data)
			button.style = discord.ButtonStyle.gray
			button.label = 'Logging Enabled'
			button.emoji = "<:toggle_on:1123932825956134912>"
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
				embed = await get_success_embed(f'Logging Channel changed from {channel} to {view.value.mention}')
				await interaction.edit_original_response(
					content = None, embed = embed, view = None
				)
				await update_mafia_embed(self.interaction, data)
			else:
				embed = await get_error_embed(f"Logging Channel was already set to {channel}")
				return await interaction.edit_original_response(
					content = None, embed = embed, view = None
				)
	
	@discord.ui.button(label="Minimum Messages", style=discord.ButtonStyle.gray, emoji="<:tgk_message:1073908465405268029>",row=1)
	async def min_messages(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.mafiaConfig.find(interaction.guild.id)
		view = discord.ui.View()
		view.value = None
		view.select = Select_General(interaction=interaction, options=[
			discord.SelectOption(label=str(i), value=str(i))
			for i in range(1, 11)
		])
		view.add_item(view.select)

		await interaction.response.send_message(view=view, ephemeral=True)

		await view.wait()
		if view.value != True:
			await interaction.delete_original_response()
			return
		data['minimum_messages'] = int(view.select.values[0])
		await interaction.client.mafiaConfig.upsert(data)
		await view.select.interaction.response.edit_message(embed=await get_success_embed(f"Minimum Messages set to {data['minimum_messages']}"), view=None)
		await update_mafia_embed(interaction, data)


	async def interaction_check(self, interaction: discord.Interaction):
		if interaction.user.id != self.interaction.user.id:
			warning = await get_invisible_embed(f"This is not for you")
			return await interaction.response.send_message(embed=warning, ephemeral=True)	
		return True

	async def on_timeout(self):
		for button in self.children:
			button.disabled = True
		
		await self.message.edit(view=self)

