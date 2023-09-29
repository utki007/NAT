import asyncio
import discord
from discord import Interaction
from utils.embeds import get_error_embed, get_invisible_embed, get_warning_embed, get_success_embed
from discord.ui import UserSelect, RoleSelect

from utils.views.ui import Dropdown_Channel

async def update_pool_embed(interaction: Interaction, data: dict):

	desc = f""
	
	if data['whitelist'] is None or len(data['whitelist']) == 0:
				desc += f"` - ` Add users when?\n"
	else:
		for member_id in data['whitelist']:
			try: 
				member = interaction.guild.get_member(int(member_id))
				desc += f"` - ` {member.mention}\n"
			except:
				pass
	
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

	event_manager = data['event_manager']

	event_manager_error = ''
	if event_manager is None:
		event_manager = f"**`None`**"
	else:
		event_manager = interaction.guild.get_role(int(event_manager))
		if event_manager is not None:
			if event_manager.position > interaction.guild.me.top_role.position:
				event_manager_error = f"> The {event_manager.mention} role is higher than my top role.\n > I cannot remove it from **raiders**."
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
	
	embed = discord.Embed(
		color=3092790,
		title="Dank Pool Access"
	)
	embed.add_field(name="Following users are whitelisted:", value=f"{desc}", inline=False)
	embed.add_field(name="Event Manager Role:", value=f"{event_manager}", inline=False)
	embed.add_field(name="Quarantine Role:", value=f"{quarantine}", inline=False)
	embed.add_field(name="Logging Channel:", value=f"{channel}", inline=False)
	if event_manager_error != '':
		embed.add_field(name="<a:nat_warning:1062998119899484190> Warning: <a:nat_warning:1062998119899484190>",
		                value=f"{event_manager_error}", inline=False)

	await interaction.message.edit(embed=embed)

class Dank_Pool_Panel(discord.ui.View):
	def __init__(self, interaction: discord.Interaction, data: dict, message: discord.Message=None):
		super().__init__(timeout=180)
		self.interaction = interaction
		self.message = None #req for disabling buttons after timeout
		self.data = data
		if self.data['enabled'] is True:
			self.children[0].label = 'Module Enabled'
			self.children[0].style = discord.ButtonStyle.gray
			self.children[0].emoji = "<:toggle_on:1123932825956134912>"
		else:
			self.children[0].label = 'Module Disabled'
			self.children[0].style = discord.ButtonStyle.gray
			self.children[0].emoji = "<:toggle_off:1123932890993020928>"

	
	@discord.ui.button(label='Module' ,row=1)
	async def toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.dankSecurity.find(interaction.guild.id)
		if data['enabled'] is True:
			data['enabled'] = False
			button.label = 'Module Disabled'
			button.style = discord.ButtonStyle.gray
			button.emoji = "<:toggle_off:1123932890993020928>"
		else:
			data['enabled'] = True
			button.label = 'Module Enabled'
			button.style = discord.ButtonStyle.gray
			button.emoji = "<:toggle_on:1123932825956134912>"
		await interaction.client.dankSecurity.upsert(data)
		await update_pool_embed(self.interaction, data)
		await interaction.response.edit_message(view=self)
	
	@discord.ui.button(label="Logging Channel", style=discord.ButtonStyle.gray, emoji="<:tgk_channel:1073908465405268029>",row=1)
	async def add_logs(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.dankSecurity.find(interaction.guild.id)
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
				await interaction.client.dankSecurity.upsert(data)
				embed = await get_success_embed(f'Logging Channel changed from {channel} to {view.value.mention}')
				await interaction.edit_original_response(
					content = None, embed = embed, view = None
				)
				await update_pool_embed(self.interaction, data)
			else:
				embed = await get_error_embed(f"Logging Channel was already set to {channel}")
				return await interaction.edit_original_response(
					content = None, embed = embed, view = None
				)


	@discord.ui.button(label="Whitelist User", style=discord.ButtonStyle.gray, emoji="<:tgk_addPerson:1132590758831079454>",row=2)
	async def whitelist_user(self, interaction: discord.Interaction, button: discord.ui.Button):
		view = Dank_Pool_Whitelist_User(self.interaction)
		await interaction.response.send_message(ephemeral=True, view=view)
		view.message = await interaction.original_response()

	@discord.ui.button(label="Unwhitelist User", style=discord.ButtonStyle.gray, emoji="<:tgk_removePerson:1132593125588733983>",row=2)
	async def delete_user(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.dankSecurity.find(interaction.guild.id)
		users = [interaction.guild.get_member(int(user_id)) for user_id in data['whitelist']]
		options = []

		for user in users:
			options.append(discord.SelectOption(label=f"{user.name} {user.name}#{user.discriminator}", value=user.id, emoji="<:tgk_removePerson:1132593125588733983>"))
		# create ui.Select instance and add it to a new view

		if len(options) == 0:
			embed = await get_warning_embed(f'None of the users are whitelisted!')
			return await interaction.response.send_message(embed=embed, ephemeral=True)
		select = Dank_Pool_Remove_Whitelist_User(interaction, options)
		view_select = discord.ui.View()
		view_select.add_item(select)

		# edit the message with the new view
		await interaction.response.send_message(view=view_select, ephemeral=True)
		select.message = await interaction.original_response()

	@discord.ui.button(label="Event Manager", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>",row=3)
	async def modify_role(self, interaction: discord.Interaction, button: discord.ui.Button):
		await interaction.response.send_message(content="*Open `Events Manager` from <@270904126974590976>'s </serversettings:1011560371041095691> command to automatically modify it.*",ephemeral=True)

	@discord.ui.button(label="Quarantine Role", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>",row=3)
	async def modify_quarantine(self, interaction: discord.Interaction, button: discord.ui.Button):
		view = Dank_Pool_Quarantine_Role(self.interaction)
		await interaction.response.send_message(ephemeral=True, view=view)
		view.message = await interaction.original_response()

	async def interaction_check(self, interaction: discord.Interaction):
		if interaction.user.id != self.interaction.user.id:
			warning = await get_invisible_embed(f"This is not for you")
			return await interaction.response.send_message(embed=warning, ephemeral=True)	
		return True

	async def on_timeout(self):
		for button in self.children:button.disabled = True
		try:await self.message.edit(view=self)
		except:pass

class Dank_Pool_Whitelist_User(discord.ui.View): 
	def __init__(self, interaction: discord.Interaction):
		super().__init__(timeout=180)
		self.interaction = interaction
		self.message = None #req for disabling buttons after timeout

	@discord.ui.select(cls=UserSelect,placeholder='Whom do you wish to whitelist?', min_values=1, max_values=1)
	async def select_channels(self, interaction: discord.Interaction, select: UserSelect):

		user = select.values[0]
		data = await interaction.client.dankSecurity.find(interaction.guild.id)
		if user.id not in data['whitelist']:
			data['whitelist'].append(user.id)
			await interaction.client.dankSecurity.upsert(data)
			embed = await get_success_embed(f"{user.mention} has complete access to Dank Server Pool.")
			await update_pool_embed(self.interaction, data)
			await interaction.response.edit_message(
				content = None, embed = embed, view = None, 
				allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False)
			)
			await asyncio.sleep(30)
			await interaction.delete_original_response()
		else:
			embed = await get_error_embed(f"{user.mention} already has access to Dank Server Pool.")
			await interaction.response.edit_message(
				content = None, embed = embed, view = None, 
				allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False)
			)
			await asyncio.sleep(30)
			await interaction.delete_original_response()

	async def on_timeout(self):
		for button in self.children:
			button.disabled = True
		
		try:
			await self.message.edit(view=self)
		except:
			pass

class Dank_Pool_Remove_Whitelist_User(discord.ui.Select):
	def __init__(self, interaction: discord.Interaction, options):
		super().__init__(placeholder="Whom do you wish to unwhitelist?", custom_id="REMOVE:WHITELISTED:USER", options=options)
		self.interaction = interaction
		self.message = None

	# This function is called when the user has chosen an option
	async def callback(self, interaction: discord.Interaction):

		data = await interaction.client.dankSecurity.find(interaction.guild.id)
		user = interaction.guild.get_member(int(self.values[0]))
		if user.id in data['whitelist']:
			data['whitelist'].remove(user.id)
		await interaction.client.dankSecurity.upsert(data)
		await update_pool_embed(self.interaction, data)
		embed = await get_success_embed(f"Revoked {user.mention}'s access to Dank Server Pool.")
		await interaction.response.edit_message(
			content = None, embed = embed, view = None, 
			allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False)
		)

class Dank_Pool_Quarantine_Role(discord.ui.View):
	def __init__(self, interaction: discord.Interaction):
		super().__init__(timeout=180)
		self.interaction = interaction
		self.message = None #req for disabling buttons after timeout

	@discord.ui.select(cls=RoleSelect,placeholder='Select quarantine role for this server...', min_values=1, max_values=1)
	async def select_channels(self, interaction: discord.Interaction, select: UserSelect):

		role = select.values[0]
		data = await interaction.client.dankSecurity.find(interaction.guild.id)
		if role.position >= interaction.guild.me.top_role.position:
			embed = await get_error_embed(f"Quarantine role cannot be higher than my highest role {interaction.guild.me.top_role.mention}.")
			await interaction.response.edit_message(
				content = None, embed = embed, view = None, 
				allowed_mentions=discord.AllowedMentions.none()
			)
			await asyncio.sleep(30)
			await interaction.delete_original_response()
			return
		if data['quarantine'] is None or role.id != int(data['quarantine']):
			embed = await get_success_embed(f"Updated quarantine role from <@&{data['quarantine']}> to {role.mention}")
			data['quarantine'] = role.id
			await interaction.client.dankSecurity.upsert(data)
			await update_pool_embed(self.interaction, data)
			await interaction.response.edit_message(
				content = None, embed = embed, view = None, 
				allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False)
			)
			await asyncio.sleep(30)
			await interaction.delete_original_response()
		else:
			embed = await get_error_embed(f"Quarantine role was already set to {role.mention}")
			await interaction.response.edit_message(
				content = None, embed = embed, view = None, 
				allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False)
			)
			await asyncio.sleep(30)
			await interaction.delete_original_response()

	async def on_timeout(self):
		for button in self.children:
			button.disabled = True
		
		try:
			await self.message.edit(view=self)
		except:
			pass
