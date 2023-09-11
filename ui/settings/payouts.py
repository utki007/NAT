import asyncio

import discord
from discord import Interaction
from discord.ui import RoleSelect, UserSelect
import asyncio

import humanfriendly
from utils.convertor import TimeConverter

from utils.embeds import (get_error_embed, get_invisible_embed,
						  get_success_embed, get_warning_embed)
from utils.views.modal import General_Modal
from utils.views.selects import Role_select
from utils.views.ui import Dropdown_Channel

async def update_payouts_embed(interaction: Interaction, data: dict):

	embed = discord.Embed(title="Dank Payout Management", color=3092790)
			
	channel = interaction.guild.get_channel(data['queue_channel'])
	if channel is None:
		channel = f"`None`"
	else:
		channel = f"{channel.mention}"
	embed.add_field(name="Claim Channel:", value=f"> {channel}", inline=True)

	channel = interaction.guild.get_channel(data['pending_channel'])
	if channel is None:
		channel = f"`None`"
	else:
		channel = f"{channel.mention}"
	embed.add_field(name="Queue Channel:", value=f"> {channel}", inline=True)

	channel = interaction.guild.get_channel(data['payout_channel'])
	if channel is None:
		channel = f"`None`"
	else:
		channel = f"{channel.mention}"
	embed.add_field(name="Payouts Channel:", value=f"> {channel}", inline=True)

	channel = interaction.guild.get_channel(data['log_channel'])
	if channel is None:
		channel = f"`None`"
	else:
		channel = f"{channel.mention}"
	embed.add_field(name="Log Channel:", value=f"> {channel}", inline=True)

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
	# await interaction.message.edit(embed=embed)
	return embed

class Payouts_Panel(discord.ui.View):
	def __init__(self, interaction: discord.Interaction, data: dict):
		super().__init__(timeout=180)
		self.interaction = interaction
		self.message = None # req for disabling buttons after timeout
		self.data = data

	@discord.ui.button(label='toggle_button_label' ,row=1)
	async def toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.payout_config.find(interaction.guild.id)
		if data['enable_payouts']:
			data['enable_payouts'] = False
			await interaction.client.payout_config.upsert(data)
			button.style = discord.ButtonStyle.red
			button.label = 'Module Disabled'
			button.emoji = "<:tgk_deactivated:1082676877468119110>"
			await interaction.response.edit_message(view=self)
		else:
			data['enable_payouts'] = True
			await interaction.client.payout_config.upsert(data)
			button.style = discord.ButtonStyle.green
			button.label = 'Module Enabled'
			button.emoji = "<:tgk_active:1082676793342951475>"
			await interaction.response.edit_message(view=self)
	
	@discord.ui.button(label="Claim Channel", style=discord.ButtonStyle.gray, emoji="<:tgk_channel:1073908465405268029>",row=1)
	async def modify_claim_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.payout_config.find(interaction.guild.id)
		view = Dropdown_Channel(interaction)
		await interaction.response.send_message(view=view, ephemeral=True)
		await view.wait()
		if view.value is None:
			embed = await get_warning_embed(f'Dropdown timed out, please retry.')
			return await interaction.edit_original_response(
				content = None, embed = embed, view = None
			)
		else:
			channel = data['queue_channel']
			if channel is None:
				channel = f"`None`"
			else:
				channel = f'<#{channel}>'
			if data['queue_channel'] is None or data['queue_channel'] != view.value.id:
				data['queue_channel'] = view.value.id
				await interaction.client.payout_config.upsert(data)
				embed = await get_success_embed(f'Payouts Claim Channel changed from {channel} to {view.value.mention}')
				await interaction.edit_original_response(
					content = None, embed = embed, view = None
				)
				embed = await update_payouts_embed(self.interaction, data)
				await interaction.message.edit(embed=embed)
			else:
				embed = await get_error_embed(f"Payouts Claim Channel was already set to {channel}")
				return await interaction.edit_original_response(
					content = None, embed = embed, view = None
				)
			
	@discord.ui.button(label="Queue Channel", style=discord.ButtonStyle.gray, emoji="<:tgk_channel:1073908465405268029>",row=2)
	async def modify_queue_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.payout_config.find(interaction.guild.id)
		view = Dropdown_Channel(interaction)
		await interaction.response.send_message(view=view, ephemeral=True)
		await view.wait()
		if view.value is None:
			embed = await get_warning_embed(f'Dropdown timed out, please retry.')
			return await interaction.edit_original_response(
				content = None, embed = embed, view = None
			)
		else:
			channel = data['pending_channel']
			if channel is None:
				channel = f"`None`"
			else:
				channel = f'<#{channel}>'
			if data['pending_channel'] is None or data['pending_channel'] != view.value.id:
				data['pending_channel'] = view.value.id
				await interaction.client.payout_config.upsert(data)
				embed = await get_success_embed(f'Payouts Queue Channel changed from {channel} to {view.value.mention}')
				await interaction.edit_original_response(
					content = None, embed = embed, view = None
				)
				embed = await update_payouts_embed(self.interaction, data)
				await interaction.message.edit(embed=embed)
			else:
				embed = await get_error_embed(f"Payouts Queue Channel was already set to {channel}")
				return await interaction.edit_original_response(
					content = None, embed = embed, view = None
				)

	@discord.ui.button(label="Payouts Channel", style=discord.ButtonStyle.gray, emoji="<:tgk_channel:1073908465405268029>",row=2)
	async def payouts_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.payout_config.find(interaction.guild.id)
		view = Dropdown_Channel(interaction)
		await interaction.response.send_message(view=view, ephemeral=True)
		await view.wait()
		if view.value is None:
			embed = await get_warning_embed(f'Dropdown timed out, please retry.')
			return await interaction.edit_original_response(
				content = None, embed = embed, view = None
			)
		else:
			channel = data['payout_channel']
			if channel is None:
				channel = f"`None`"
			else:
				channel = f'<#{channel}>'
			if data['payout_channel'] is None or data['payout_channel'] != view.value.id:
				data['payout_channel'] = view.value.id
				await interaction.client.payout_config.upsert(data)
				embed = await get_success_embed(f'Payouts Channel changed from {channel} to {view.value.mention}')
				await interaction.edit_original_response(
					content = None, embed = embed, view = None
				)
				embed = await update_payouts_embed(self.interaction, data)
				await interaction.message.edit(embed=embed)
			else:
				embed = await get_error_embed(f"Payouts Channel was already set to {channel}")
				return await interaction.edit_original_response(
					content = None, embed = embed, view = None
				)

	@discord.ui.button(label="Logs Channel", style=discord.ButtonStyle.gray, emoji="<:tgk_channel:1073908465405268029>",row=3)
	async def logs_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.payout_config.find(interaction.guild.id)
		view = Dropdown_Channel(interaction)
		await interaction.response.send_message(view=view, ephemeral=True)
		await view.wait()
		if view.value is None:
			embed = await get_warning_embed(f'Dropdown timed out, please retry.')
			return await interaction.edit_original_response(
				content = None, embed = embed, view = None
			)
		else:
			channel = data['log_channel']
			if channel is None:
				channel = f"`None`"
			else:
				channel = f'<#{channel}>'
			if data['log_channel'] is None or data['log_channel'] != view.value.id:
				data['log_channel'] = view.value.id
				await interaction.client.payout_config.upsert(data)
				embed = await get_success_embed(f'Logs Channel changed from {channel} to {view.value.mention}')
				await interaction.edit_original_response(
					content = None, embed = embed, view = None
				)
				embed = await update_payouts_embed(self.interaction, data)
				await interaction.message.edit(embed=embed)
			else:
				embed = await get_error_embed(f"Logs Channel was already set to {channel}")
				return await interaction.edit_original_response(
					content = None, embed = embed, view = None
				)

	@discord.ui.button(label="Claim Time", style=discord.ButtonStyle.gray, emoji="<:tgk_clock:1150836621890031697>", row=3)
	async def claim_time(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.payout_config.find(interaction.guild.id)
		modal = General_Modal("Claim Time Modal", interaction=interaction)
		modal.question = discord.ui.TextInput(label="Enter New Claim Time", placeholder="Enter New Claim Time like 1h45m", min_length=1, max_length=10)    
		modal.value = None
		modal.add_item(modal.question)
		await interaction.response.send_modal(modal)

		await modal.wait()
		if modal.value:
			time = await TimeConverter().convert(modal.interaction, modal.question.value)
			if time < 3600: 
				return await modal.interaction.response.send_message(embed = await get_error_embed('Claim time must be greater than 1 hour'), ephemeral=True)
			data['default_claim_time'] = time
			await interaction.client.payout_config.update(data)

			embed = await get_success_embed(f"Successfully updated claim time to : **`{humanfriendly.format_timespan(data['default_claim_time'])}`**!")
			embed = await update_payouts_embed(self.interaction, data)
			await modal.interaction.response.edit_message(embed=embed, view=self)
	
	@discord.ui.button(label="Payout Manager", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>", row=4)
	async def manager_role(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.payout_config.find(interaction.guild.id)
		view = discord.ui.View()
		view.value = False
		view.select = Role_select("select new manager role", max_values=10, min_values=1, disabled=False)
		view.add_item(view.select)

		await interaction.response.send_message(content="Select a new role from the dropdown menu below", view=view, ephemeral=True)
		await view.wait()

		if view.value:
				added = []
				removed = []
				for ids in view.select.values:
					if ids.id not in data["manager_roles"]:
						data["manager_roles"].append(ids.id)
						added.append(ids.mention)
					else:
						data["manager_roles"].remove(ids.id)
						removed.append(ids.mention)
				await view.select.interaction.response.edit_message(content=f"Suscessfully updated manager roles\nAdded: {', '.join(added)}\nRemoved: {', '.join(removed)}", view=None)

				await interaction.client.payout_config.update(data)
				embed = await update_payouts_embed(self.interaction, data)
				await interaction.message.edit(embed=embed)
		else:
			await interaction.edit_original_response(content="No role selected", view=None)
	
	@discord.ui.button(label="Staff Roles", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>", row=4)
	async def event_managers(self, interaction: discord.Interaction, button: discord.ui.Button):
		
		data = await interaction.client.payout_config.find(interaction.guild.id)
		view = discord.ui.View()
		view.value = False
		view.select = Role_select("select new event manager role", max_values=10, min_values=1, disabled=False)
		view.add_item(view.select)

		await interaction.response.send_message(content="Select a new role from the dropdown menu below", view=view, ephemeral=True)
		await view.wait()

		if view.value:
				added = []
				removed = []
				for ids in view.select.values:
					if ids.id not in data["event_manager_roles"]:
						data["event_manager_roles"].append(ids.id)
						added.append(ids.mention)
					else:
						data["event_manager_roles"].remove(ids.id)
						removed.append(ids.mention)
				await view.select.interaction.response.edit_message(content=f"Suscessfully updated event manager roles\nAdded: {', '.join(added)}\nRemoved: {', '.join(removed)}", view=None)

				await interaction.client.payout_config.update(data)
				embed = await update_payouts_embed(self.interaction, data)
				await interaction.message.edit(embed=embed)
		else:
			await interaction.edit_original_response(content="No role selected", view=None)

	async def interaction_check(self, interaction: discord.Interaction):
		if interaction.user.id != self.interaction.user.id:
			warning = await get_invisible_embed(f"This is not for you")
			return await interaction.response.send_message(embed=warning, ephemeral=True)	
		return True

	async def on_timeout(self):
		for button in self.children:
			button.disabled = True
		
		await self.message.edit(view=self)

