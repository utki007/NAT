import asyncio
import re
import discord
from discord import Interaction, app_commands
from discord.ui import RoleSelect, UserSelect
import asyncio

import humanfriendly
from utils.convertor import TimeConverter

from utils.embeds import (get_error_embed, get_invisible_embed,
						  get_success_embed, get_warning_embed)
from utils.views.modal import General_Modal
from utils.views.selects import Role_select
from utils.views.ui import Dropdown_Channel
from utils.views.confirm import Confirm


class ButtonCooldown(app_commands.CommandOnCooldown):
	def __init__(self, retry_after: float):
		self.retry_after = retry_after

	def key(interaction: discord.Interaction):
		return interaction.user


async def update_payouts_embed(interaction: Interaction, data: dict):

	embed = discord.Embed(title="Dank Payout Management", color=3092790)
			
	channel = interaction.guild.get_channel(data['pending_channel'])
	if channel is None:
		channel = f"`None`"
	else:
		channel = f"{channel.mention}"
	embed.add_field(name="Claim Channel:", value=f"> {channel}", inline=True)

	channel = interaction.guild.get_channel(data['queue_channel'])
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
			channel = data['pending_channel']
			if channel is None:
				channel = f"`None`"
			else:
				channel = f'<#{channel}>'
			if data['pending_channel'] is None or data['pending_channel'] != view.value.id:
				data['pending_channel'] = view.value.id
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
			channel = data['queue_channel']
			if channel is None:
				channel = f"`None`"
			else:
				channel = f'<#{channel}>'
			if data['queue_channel'] is None or data['queue_channel'] != view.value.id:
				data['queue_channel'] = view.value.id
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


class Payout_claim(discord.ui.View):
	def __init__(self):
		super().__init__(timeout=None)
		self.cd = app_commands.Cooldown(1, 15)

	async def interaction_check(self, interaction: discord.Interaction):
		retry_after = self.cd.update_rate_limit()
		if retry_after:
			raise ButtonCooldown(retry_after)
		return True
	
	async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
		if isinstance(error, ButtonCooldown):
			seconds = int(error.retry_after)
			unit = 'second' if seconds == 1 else 'seconds'
			await interaction.response.send_message(f"You're on cooldown for {seconds} {unit}!", ephemeral=True)
		else:
			await super().on_error(interaction, error, item)
	
	@discord.ui.button(label="Claim", style=discord.ButtonStyle.green, custom_id="payout:claim")
	async def payout_claim(self, interaction: discord.Interaction, button: discord.ui.Button):
		loading_embed = discord.Embed(description="<a:loading:998834454292344842> | Processing claim...", color=discord.Color.yellow())
		await interaction.response.send_message(embed=loading_embed, ephemeral=True)

		data = await interaction.client.payout_queue.find(interaction.message.id)
		if not data: return await interaction.edit_original_response(embed=discord.Embed(description="<:octane_no:1019957208466862120> | This payout has already been claimed or invalid", color=discord.Color.red()))

		if interaction.user.id != data['winner']:
			await interaction.edit_original_response(embed=discord.Embed(description="<:octane_no:1019957208466862120> | You are not the winner of this payout", color=discord.Color.red()))
			return
		
		data['claimed'] = True
		await interaction.client.payout_queue.update(data)

		payout_config = await interaction.client.payout_config.find(interaction.guild.id)
		queue_channel = interaction.guild.get_channel(payout_config['queue_channel'])

		queue_embed = interaction.message.embeds[0]
		queue_embed.description = queue_embed.description.replace("`Pending`", "`Awaiting Payment`")
		queue_embed_description = queue_embed.description.split("\n")
		queue_embed_description.pop(5)
		queue_embed.description = "\n".join(queue_embed_description)

		current_embed = interaction.message.embeds[0]
		current_embed.description = current_embed.description.replace("`Pending`", "`Claimed`")
		current_embed_description = current_embed.description.split("\n")
		current_embed_description[5] = f"~~{current_embed_description[5]}~~"


		await interaction.edit_original_response(embed=discord.Embed(description="<:octane_yes:1019957051721535618> | Sucessfully claimed payout, you will be paid in 24hrs", color=0x2b2d31))

		view = Payout_Buttton()
		msg = await queue_channel.send(embed=queue_embed, view=view)
		pending_data = data
		pending_data['_id'] = msg.id
		await interaction.client.payout_pending.insert(pending_data)
		await interaction.client.payout_queue.delete(interaction.message.id)

		button.label = "Claimed Successfully"
		button.style = discord.ButtonStyle.gray
		button.emoji = "<a:nat_check:1010969401379536958>"
		button.disabled = True
		self.children[1].disabled = True
		self.add_item(discord.ui.Button(label=f'Queue Message', style=discord.ButtonStyle.url, disabled=False, url=msg.jump_url))

		await interaction.message.edit(embed=current_embed, view=self)
		interaction.client.dispatch("payout_claim", interaction.message, interaction.user)
		interaction.client.dispatch("payout_pending", msg)


	@discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="payout:cancel")
	async def payout_cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
		payout_data = await interaction.client.payout_queue.find(interaction.message.id)
		if not payout_data: return await interaction.edit_original_response(embed=discord.Embed(description="<:octane_no:1019957208466862120> | This payout has already been claimed or invalid", color=discord.Color.red()))
		if payout_data['set_by'] != interaction.user.id:
			config = await interaction.client.payout_config.find(interaction.guild.id)
			user_roles = [role.id for role in interaction.user.roles]
			authorized_roles = set(config['event_manager_roles']) | set(config['manager_roles'])
			if not set(user_roles) & authorized_roles:
				return
				  
		modal = General_Modal("Reason for cancelling payout?", interaction)
		modal.reason = discord.ui.TextInput(label="Reason", placeholder="Reason for cancelling payout", min_length=3, max_length=100, required=True)
		modal.add_item(modal.reason)
		await interaction.response.send_modal(modal)

		await modal.wait()
		if modal.value:
			loading_embed = discord.Embed(description="<a:loading:998834454292344842> | Processing claim...", color=discord.Color.yellow())
			await modal.interaction.response.send_message(embed=loading_embed, ephemeral=True)

			embed = interaction.message.embeds[0]
			embed.title = "Payout Cancelled"
			embed.description = embed.description.replace("`Pending`", "`Cancelled`")
			embed.description += f"\n**Cancelled by:** {interaction.user.mention}\n**Reason:** {modal.reason.value}"

			temp_view = discord.ui.View()
			temp_view.add_item(discord.ui.Button(label="Payout Cancelled", style=discord.ButtonStyle.gray, emoji="<a:nat_cross:1010969491347357717>",disabled=True))
			await interaction.message.edit(embed=embed, view=temp_view, content=None)
			await interaction.client.payout_queue.delete(interaction.message.id)
			
			await modal.interaction.edit_original_response(embed=discord.Embed(description="Sucessfully cancelled payout", color=discord.Color.green()))


class Payout_Buttton(discord.ui.View):
	def __init__(self):
		super().__init__(timeout=None)
		self.cd = app_commands.Cooldown(5, 10)
	
	@discord.ui.button(label="Reject", style=discord.ButtonStyle.gray, emoji="<a:nat_cross:1010969491347357717>", custom_id="reject")
	async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
		view = Confirm(interaction.user, 30)
		await interaction.response.send_message("Are you sure you want to reject this payout?", view=view, ephemeral=True)
		await view.wait()
		if not view.value: return await interaction.delete_original_response()
		data = await interaction.client.payout_pending.find(interaction.message.id)
		if not data: return await view.interaction.response.edit_message(embed=discord.Embed(description="<:dynoError:1000351802702692442> | Payout not found in Database", color=discord.Color.red()))

		embed = interaction.message.embeds[0]
		embed.description = embed.description.replace("`Awaiting Payment`", "`Payout Rejected`")
		embed.title = "Payout Rejected"
		embed.description += f"\n**Rejected By:** {interaction.user.mention}"

		edit_view = discord.ui.View()
		edit_view.add_item(discord.ui.Button(label=f'Payout Denied', style=discord.ButtonStyle.gray, disabled=True, emoji="<a:nat_cross:1010969491347357717>"))

		await view.interaction.response.edit_message(embed=discord.Embed(description="<:octane_yes:1019957051721535618> | Payout Rejected Successfully!", color=0x2b2d31), view=None)
		await interaction.message.edit(view=edit_view, embed=embed, content=None)
		await interaction.client.payout_pending.delete(data['_id'])
	
	@discord.ui.button(label="Manual Verification", style=discord.ButtonStyle.gray, emoji="<:caution:1122473257338151003>", custom_id="manual_verification", disabled=False)
	async def manual_verification(self, interaction: discord.Interaction, button: discord.ui.Button):
		view = General_Modal(title="Manual Verification", interaction=interaction)
		view.msg = discord.ui.TextInput(label="Message Link", placeholder="Enter the message link of te confirmation message", max_length=100, required=True, style=discord.TextStyle.long)
		view.add_item(view.msg)

		await interaction.response.send_modal(view)
		await view.wait()
		if not view.value: return
		msg_link = view.msg.value
		await view.interaction.response.send_message("Verifying...", ephemeral=True)
		data = await interaction.client.payout_pending.find(interaction.message.id)
		try:
			msg_id = int(msg_link.split("/")[-1])
			msg_channel = int(msg_link.split("/")[-2])
			channel = interaction.guild.get_channel(msg_channel)
			message = await channel.fetch_message(msg_id)

			if message.author.id != 270904126974590976: raise Exception("Invalid Message Link")
			if len(message.embeds) <= 0: raise Exception("Invalid Message Link")

			embed = message.embeds[0]
			if not embed.description.startswith("Successfully paid"): raise Exception("Invalid Message Link")

			winner = message.guild.get_member(int(embed.description.split(" ")[2].replace("<", "").replace(">", "").replace("!", "").replace("@", ""))) 
			if not winner: raise Exception("Invalid Message Link")
			if winner.id != data['winner']: return await view.interaction.edit_original_response(content="The winner of the provided message is not the winner of this payout")

			items = re.findall(r"\*\*(.*?)\*\*", embed.description)[0]
			if "⏣" in items:
				items = int(items.replace("⏣", "").replace(",", ""))
				if items == data['prize']:
					await view.interaction.edit_original_response(content="Verified Successfully")
				else:
					return await view.interaction.edit_original_response(content="The prize of the provided message is not the prize of this payout")
			else:
				emojis = list(set(re.findall(":\w*:\d*", items)))
				for emoji in emojis :items = items.replace(emoji,"",100); items = items.replace("<>","",100);items = items.replace("<a>","",100);items = items.replace("  "," ",100)
				mathc = re.search(r"(\d+)x (.+)", items)
				item_found = mathc.group(2)
				quantity_found = int(mathc.group(1))
				if item_found == data['item'] and quantity_found == data['prize']:
					await view.interaction.edit_original_response(content="Verified Successfully")
				else:
					return await view.interaction.edit_original_response(content="The prize of the provided message is not the prize of this payout")
			
			payot_embed = interaction.message.embeds[0]
			payot_embed.description += f"\n**Payout Location:** {message.jump_url}"
			payot_embed.description = payot_embed.description.replace("`Initiated`", "`Successfuly Paid`")
			payot_embed.description = payot_embed.description.replace("`Awaiting Payment`", "`Successfuly Paid`")
			payot_embed.description += f"\n**Santioned By:** {interaction.user.mention}"
			payot_embed.title = "Successfully Paid"
			view = discord.ui.View()
			view.add_item(discord.ui.Button(label=f"Paid at", style=discord.ButtonStyle.url, url=message.jump_url, emoji="<:tgk_link:1105189183523401828>"))
			await interaction.message.edit(embed=payot_embed, view=view)   
			await interaction.client.payout_pending.delete(data['_id'])             
		except Exception as e:
			print(e)
			return await view.interaction.edit_original_response(content="Invalid Message Link")

	async def on_error(self, interaction: Interaction, error: Exception, item: discord.ui.Item):
		if isinstance(error, ButtonCooldown):
			seconds = int(error.retry_after)
			unit = 'second' if seconds == 1 else 'seconds'
			return await interaction.response.send_message(f"You're on cooldown for {seconds} {unit}!", ephemeral=True)
		try:
			await interaction.response.send_message(f"Error: {error}", ephemeral=True)
		except Exception as e:
			print(e)
			await interaction.edit_original_response(content=f"Error: {error}")

	async def interaction_check(self, interaction: Interaction):
		config = await interaction.client.payout_config.find(interaction.guild.id)
		roles = [role.id for role in interaction.user.roles]
		if (set(roles) & set(config['manager_roles'])): 
			retry_after = self.cd.update_rate_limit()
			if retry_after:
				raise ButtonCooldown(retry_after)
			return True
		else:
			embed = discord.Embed(title="Error", description="You don't have permission to use this button", color=discord.Color.red())
			await interaction.response.send_message(embed=embed, ephemeral=True)
			return False