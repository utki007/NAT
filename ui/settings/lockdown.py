import discord
import datetime
import asyncio
import io
from discord import Interaction
from discord.ui import ChannelSelect, RoleSelect
from utils.views.confirm import Confirm
from utils.views.ui import *
from ui.settings.lockdown import *

class Lockdown_Profile_Panel(discord.ui.View):
	def __init__(self, interaction: discord.Interaction):
		super().__init__()
		self.interaction = interaction
		self.message = None 
	
	@discord.ui.button(label="Create", style=discord.ButtonStyle.gray, emoji="<:tgk_add:1073902485959352362>",row=1)
	async def whitelist_profile(self, interaction: discord.Interaction, button: discord.ui.Button):
		await interaction.response.send_modal(Lockdown_Profile_Add())


	@discord.ui.button(label="Edit", style=discord.ButtonStyle.gray, emoji="<:tgk_edit:1073902428224757850>",row=1)
	async def modify_profile(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.lockdown.find(interaction.guild.id)
		options = []
		for profile in data['lockdown_profiles']:
			options.append(discord.SelectOption(
				label=f"{profile.title()}", description=f"Configure {profile.title()}", emoji='<:nat_profile:1073644967492337786>', value=f"{profile}"))
		if len(options) == 0:
			embed = await get_warning_embed(interaction, "This server has no lockdown protocols yet! Create one using the **Create** button.")
			return await interaction.response.send_message(embed=embed, ephemeral=True)
		
		view = discord.ui.View()
		view.profile = Dropdown_Default(interaction, options, placeholder="Select a lockdown protocol to configure ...")
		view.add_item(view.profile)
		await interaction.response.send_message(view=view, ephemeral=True)
		await view.wait()

		if not view.value:
			embed = await get_warning_embed("Some error occured!")
			await interaction.followup.send(embed=embed, ephemeral=True)
			return await interaction.delete_original_response()

		profile_name = view.profile.values[0]

		if profile_name not in data['lockdown_profiles']:
			warning = discord.Embed(
				color=0xffd300,
				title=f"> The protocol named **`{profile_name}`** does not exist. Are you trying to Create a profile? \n> Use </lockdown create:1062965049913778296> .")
			warning.set_thumbnail(url=f"https://cdn.discordapp.com/emojis/845404773360205854.gif?size=128&quality=lossless")
			return await interaction.response.send_message(embed=warning, ephemeral=True)
		try:
			panel = data[profile_name]
		except KeyError:
			warning = discord.Embed(
				color=0xffd300,
				title=f"> The protocol named **`{profile_name}`** does not exist. Are you trying to Create a profile? \n> Use </lockdown create:1062965049913778296> .")
			warning.set_thumbnail(url=f"https://cdn.discordapp.com/emojis/845404773360205854.gif?size=128&quality=lossless")
			return await interaction.response.send_message(embed=warning, ephemeral=True)

		embed = discord.Embed(title=f"Lockdown Settings for Protocol: {profile_name}", color=discord.Color.blurple())
		
		lockdown_config = ""
		if len(panel['channel_and_role']) > 0:
			for channel_id in panel['channel_and_role']:
				channel = interaction.guild.get_channel(int(channel_id))
				roleIds = [int(role_ids) for role_ids in panel['channel_and_role'][channel_id].split(" ") if role_ids != '' and role_ids not in ["everyone"]]
				roleIds = [discord.utils.get(interaction.guild.roles, id=id) for id in roleIds]
				role = [role for role in roleIds if role != None]
				if channel:
					lockdown_config += f'{channel.mention} **|** {" + ".join([role.mention if role != interaction.guild.default_role else str(role) for role in role])}\n'
			if lockdown_config == "":
				lockdown_config = "None"
		else:
			lockdown_config = "None"

		embed.description = f"**Channel Settings**\n{lockdown_config}\n\n"
		# embed.add_field(name="Channel Settings", value=f"{lockdown_config}", inline=False)

		lockmsg_config = f"**Title:** {panel['lock_embed']['title']}\n"
		lockmsg_config += f"**Thumbnail:** [**Click here**]({panel['lock_embed']['thumbnail']})\n" 
		lockmsg_config += f"**Description:**\n```{panel['lock_embed']['description']}```\n"
		
		embed.add_field(name="Embed Message for Lockdown", value=f"{lockmsg_config}", inline=False)

		unlockmsg_config = f"**Title:** {panel['unlock_embed']['title']}\n"
		unlockmsg_config += f"**Thumbnail:** [**Click here**]({panel['unlock_embed']['thumbnail']})\n"
		unlockmsg_config += f"**Description:**\n```{panel['unlock_embed']['description']}```\n"
		
		embed.add_field(name="Embed Message for Unlockdown", value=f"{unlockmsg_config}", inline=False)

		
		view = Lockdown_Config_Panel(interaction, data, profile_name)
		confirm_message = await interaction.followup.send(embed=embed, view=view, wait=True, ephemeral=True)
		view.message = confirm_message
		await interaction.delete_original_response()

	@discord.ui.button(label="Delete", style=discord.ButtonStyle.gray, emoji="<:tgk_delete:1113517803203461222>",row=1)
	async def delete_profile(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.lockdown.find(interaction.guild.id)
		options = []
		for profile in data['lockdown_profiles']:
			options.append(discord.SelectOption(
				label=f"{profile.title()}", description=f"Delete {profile.title()}", emoji='<:nat_profile:1073644967492337786>', value=f"{profile}"))
		if len(options) == 0:
			embed = await get_warning_embed(interaction, "This server has no lockdown protocols yet.")
			return await interaction.response.send_message(embed=embed, ephemeral=True)

		view = discord.ui.View()
		view.profile = Dropdown_Default(interaction, options, placeholder="Select a protocol to delete ...")
		view.add_item(view.profile)
		await interaction.response.send_message(view=view, ephemeral=True, delete_after=190)
		await view.wait()

		if not view.value:
			embed = await get_warning_embed("Some error occured!")
			await interaction.followup.send(embed=embed, ephemeral=True)
			return await interaction.delete_original_response()
			
			
		profile_name = view.profile.values[0]
		confirmation_view = Confirm(interaction.user)
		embed = discord.Embed(
			color=3092790,
			description=f"Protocol **`{profile_name.title()}`** will be deleted. Are you sure?"
		)
		confirm_message = await interaction.followup.send(embed=embed, view=confirmation_view, wait=True, ephemeral=True)
		await interaction.delete_original_response()
		await confirmation_view.wait()
		if confirmation_view.value:
			data['lockdown_profiles'].remove(view.profile.values[0])
			await interaction.client.lockdown.upsert(data)
			embed = await get_success_embed(f"Protocol **`{view.profile.values[0].title()}`** has been deleted.")
			await update_lockdown_embed(interaction, data)
			await confirm_message.edit(embed=embed, view=None)
		elif confirmation_view.value == False:
			embed = await get_error_embed("Cancelled protocol deletion.")
			await confirm_message.edit(embed=embed, view=None)

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

async def update_lockdown_embed(interaction: Interaction, data: dict):

	if data['lockdown_profiles'] is None or len(data['lockdown_profiles']) == 0:
		profiles = f"` - ` **Add protocols when?**\n"
	else:
		profiles = ""
		for profile in data['lockdown_profiles']:
			profiles += f"` - ` **{profile.title()}**\n"

	embed = discord.Embed(
		color=3092790,
		title="Configure Server Lockdown"
	)
	embed.add_field(name="Declared protocols are:", value=f"{profiles}", inline=False)
	
	await interaction.message.edit(embed=embed)

class Lockdown_Profile_Add(discord.ui.Modal, title='Add Lockdown Profile'):

	profile_name = discord.ui.TextInput(
		label='What do you think of this new feature?',
		style=discord.TextStyle.short,
		placeholder='Enter lockdown profile name',
		required=True,
		max_length=50,
		min_length=3
	)

	async def on_submit(self, interaction: discord.Interaction):

		name = self.profile_name.value

		data = await interaction.client.lockdown.find(interaction.guild.id)
		if not data:
			data = {"_id": interaction.guild.id, "lockdown_profiles": []}

		length = len(data['lockdown_profiles'])
		if length >= 5 and interaction.user.id not in self.bot.owner_ids:
			embed = await get_warning_embed(f"You can't create more than 5 lockdown protocols.")
			return await interaction.response.send_message(embed=embed, ephemeral=True)
		data['lockdown_profiles'].append(name)
		data[name] = {
			'creator': interaction.user.id, 
			'channel_and_role': {}, 
			'lock_embed':{
				'title':'Server Lockdown <:tgk_lock:1072851190213259375>', 
				'description':f"This channel has been locked.\nRefrain from dm'ing staff, **__you are not muted.__**", 
				'thumbnail':'https://cdn.discordapp.com/emojis/830548561329782815.gif?v=1'
			}, 
			'unlock_embed':{
				'title':'Server Unlock <:tgk_unlock:1072851439161983028>', 
				'description':f"Channel has been unlocked.\nRefrain from asking us why it was previously locked.", 
				'thumbnail':'https://cdn.discordapp.com/emojis/802121702384730112.gif?v=1'
			}
		}
		await interaction.client.lockdown.upsert(data)
		embed = await get_success_embed(f"Successfully created lockdown profile named: **`{name}`**!")
		await update_lockdown_embed(interaction, data)
		await interaction.response.send_message(embed = embed, ephemeral=True)
		

	async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
		await interaction.response.send_message('Oops! Something went wrong.', ephemeral=True)

async def update_embed(interaction: Interaction, data: dict, name:str , failed:bool, message: discord.Message):

	if failed:
		warning = discord.Embed(
				color=0xffd300,
				title=f"<a:nat_warning:1062998119899484190> **|** Updating information failed. Please check the information you provided and try again.")
		return await interaction.followup.send(embed=warning, ephemeral=True)
	panel = data[name]
	embed = discord.Embed(title=f"Lockdown Settings for Profile: {name}", color=discord.Color.blurple())
	
	lockdown_config = ""
	if len(panel['channel_and_role']) > 0:
		for channel_id in panel['channel_and_role']:
			channel = interaction.guild.get_channel(int(channel_id))
			roleIds = [int(role_ids) for role_ids in panel['channel_and_role'][channel_id].split(" ") if role_ids != '']
			roleIds = [discord.utils.get(interaction.guild.roles, id=id) for id in roleIds]
			role = [role for role in roleIds if role != None]
			if channel:
				lockdown_config += f'{channel.mention} **|** {" + ".join([role.mention if role != interaction.guild.default_role else str(role) for role in role])}\n'
	else:
		lockdown_config = "None"

	embed.description = f"**Channel Settings**\n{lockdown_config}\n\n"
	# embed.add_field(name="Channel Settings", value=f"{lockdown_config}", inline=False)

	lockmsg_config = f"**Title:** {panel['lock_embed']['title']}\n"
	lockmsg_config += f"**Thumbnail:** [**Click here**]({panel['lock_embed']['thumbnail']})\n"
	lockmsg_config += f"**Description:**\n```{panel['lock_embed']['description']}```\n"
	
	embed.add_field(name="Embed Message for Lockdown", value=f"{lockmsg_config}", inline=False)

	unlockmsg_config = f"**Title:** {panel['unlock_embed']['title']}\n"
	unlockmsg_config += f"**Thumbnail:** [**Click here**]({panel['unlock_embed']['thumbnail']})\n"
	unlockmsg_config += f"**Description:**\n```{panel['unlock_embed']['description']}```\n"
	
	embed.add_field(name="Embed Message for Unlockdown", value=f"{unlockmsg_config}", inline=False)

	await message.edit(embed=embed)
	# await interaction.followup.send(f"Updated Lockdown Config", ephemeral=True)

class Lockdown_Config_Panel(discord.ui.View):
	def __init__(self, interaction: discord.Interaction, data: dict, name: str ,message: discord.Message=None):
		super().__init__(timeout=180)
		self.interaction = interaction
		self.data = data
		self.message = message
		self.name = name
	
	@discord.ui.button(label="Modify Channels", style=discord.ButtonStyle.gray, emoji="<:tgk_channel:1073908465405268029>", custom_id="LOCKDOWN:ADD:CHANNEL", row = 0)
	async def add_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
		view = Channel_modify_panel(interaction, self.data, self.name, self.message)
		embed = await get_invisible_embed(f'Do you want to lock/unlock channel for @everyone role or for a custom role?')
		await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
		await view.wait()
	
	@discord.ui.button(label="Delete Channel", style=discord.ButtonStyle.gray, emoji="<:tgk_delete:1113517803203461222>", custom_id="LOCKDOWN:DELETE:CHANNEL", row=0)
	async def delete_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
				
		channels = [interaction.guild.get_channel(int(channel_id)) for channel_id in self.data[self.name]['channel_and_role'].keys()]
		options = []

		for channel in channels:
			role = interaction.guild.get_role(int(self.data[self.name]['channel_and_role'][str(channel.id)]))
			if role is not None:
				options.append(discord.SelectOption(label=channel.name, value=str(channel.id), emoji="<:tgk_channel:1073908465405268029>", description=f"{role.name} 🧑 {len(role.members)}"))
		# create ui.Select instance and add it to a new view
		select = Delete_channel(interaction, self.data, self.name, options, self.message)
		view_select = discord.ui.View()
		view_select.add_item(select)

		# edit the message with the new view
		await interaction.response.send_message(content="Select channel to remove.", view=view_select, ephemeral=True)

	@discord.ui.button(label="Lockdown Message", style=discord.ButtonStyle.gray, emoji="<:tgk_message:1113527047373979668>", custom_id="LOCKDOWN:MODIFY:LOCK:MSG", row = 1)
	async def lockdown_msg(self, interaction: discord.Interaction, button: discord.ui.Button):
		modal = Lockdown_Add_Channel(interaction,self.name, self.data, self.message)

		panel = self.data[self.name]
		title = f"{panel['lock_embed']['title']}"
		thumbnail = f"{panel['lock_embed']['thumbnail']}" 
		description = f"{panel['lock_embed']['description']}"

		modal.add_item( 
			discord.ui.TextInput(
				required=True,
				label="lockdown embed title:", 
				style=discord.TextStyle.short, 
				custom_id="LOCKDOWN:MODIFY:EMBED:TITLE",
				default=title, 
				placeholder="Enter title"))

		modal.add_item( 
			discord.ui.TextInput(
				required=True,
				label="lockdown embed thumbnail:", 
				style=discord.TextStyle.short, 
				custom_id="LOCKDOWN:MODIFY:EMBED:THUMBNAIL",
				default=thumbnail, 
				placeholder="Enter thumbnail url"))
			
		modal.add_item( 
			discord.ui.TextInput(
				required=True,
				label="lockdown embed description:", 
				style=discord.TextStyle.long, 
				custom_id="LOCKDOWN:MODIFY:EMBED:DESCRIPTION",
				default=description, 
				placeholder="Enter description"))

		await interaction.response.send_modal(modal)

	@discord.ui.button(label="Unlockdown Message", style=discord.ButtonStyle.gray, emoji="<:tgk_message:1113527047373979668>", custom_id="UNLOCKDOWN:MODIFY:LOCK:MSG", row = 1)
	async def unlockdown_msg(self, interaction: discord.Interaction, button: discord.ui.Button):
		modal = Lockdown_Add_Channel(interaction,self.name, self.data, self.message)

		panel = self.data[self.name]
		title = f"{panel['unlock_embed']['title']}"
		thumbnail = f"{panel['unlock_embed']['thumbnail']}" 
		description = f"{panel['unlock_embed']['description']}"

		modal.add_item( 
			discord.ui.TextInput(
				required=True,
				label="unlockdown embed title:", 
				style=discord.TextStyle.short, 
				custom_id="UNLOCKDOWN:MODIFY:EMBED:TITLE",
				default=title, 
				placeholder="Enter title"))

		modal.add_item( 
			discord.ui.TextInput(
				required=True,
				label="unlockdown embed thumbnail:", 
				style=discord.TextStyle.short, 
				custom_id="UNLOCKDOWN:MODIFY:EMBED:THUMBNAIL",
				default=thumbnail, 
				placeholder="Enter thumbnail url"))
			
		modal.add_item( 
			discord.ui.TextInput(
				required=True,
				label="unlockdown embed description:", 
				style=discord.TextStyle.long, 
				custom_id="UNLOCKDOWN:MODIFY:EMBED:DESCRIPTION",
				default=description, 
				placeholder="Enter description"))

		await interaction.response.send_modal(modal)

	async def interaction_check(self, interaction: Interaction):
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

class Lockdown_Add_Channel(discord.ui.Modal):
	def __init__(self, interaction: Interaction, name: str, data: dict, message: discord.Message):
		super().__init__(timeout=None, title=f"Configuring {name.title()}")
		self.data = data
		self.interaction = interaction
		self.name = name
		self.message = message
	
	async def on_submit(self, interaction: Interaction):
		failed = False
		for child in self.children:
			
			if child.label == "add/edit channel config:":
				channel_id = str(child.value.split(":")[0])
				if len(child.value.split(":")) > 2:
					return
				if len(child.value.split(":")) == 1:
					roles = str(interaction.guild.default_role.id)
				else:
					roles = child.value.split(":")[1]

					if "everyone" in roles:
						roles = str(interaction.guild.default_role.id)
					else:
						roleIds = [int(role_ids) for role_ids in roles.split(" ") if role_ids != '' and role_ids not in ["everyone"]]
						roleIds = [discord.utils.get(interaction.guild.roles, id=id) for id in roleIds]
						roles = [role for role in roleIds if role != None]
						roles = " ".join([str(role.id) for role in roles])

				self.data[self.name]['channel_and_role'][channel_id] = roles
			
			elif child.label == "delete channel from config:":
				if child.value in self.data[self.name]['channel_and_role'].keys():
					del self.data[self.name]['channel_and_role'][child.value]
				else:
					failed = True

			elif child.label == "lockdown embed title:":
				self.data[self.name]['lock_embed']['title'] = child.value
			
			elif child.label == "lockdown embed thumbnail:":
				self.data[self.name]['lock_embed']['thumbnail'] = child.value

			elif child.label == "lockdown embed description:":
				self.data[self.name]['lock_embed']['description'] = child.value

			elif child.label == "unlockdown embed title:":
				self.data[self.name]['unlock_embed']['title'] = child.value
			
			elif child.label == "unlockdown embed thumbnail:":
				self.data[self.name]['unlock_embed']['thumbnail'] = child.value

			elif child.label == "unlockdown embed description:":
				self.data[self.name]['unlock_embed']['description'] = child.value
			
		await interaction.client.lockdown.update(self.data)
		embed = discord.Embed(
					color=0x43b581, 
					description=f'<a:nat_check:1010969401379536958> **|** Successfully updated embed message.'
				)
		await interaction.response.send_message(embed = embed, ephemeral=True)
		await update_embed(interaction, self.data, self.name, failed, self.message)

class Select_channel_roles(discord.ui.View):
	def __init__(self, interaction: discord.Interaction, data: dict, name: str, message: discord.Message):
		super().__init__()
		self.interaction = interaction
		self.data = data
		self.name = name
		self.message = message
		self.selected_channel = None
		self.selected_role = None
	
	@discord.ui.select(cls=ChannelSelect, placeholder="Choose Channel",channel_types=[discord.ChannelType.text], disabled=False)
	async def channel_select(self, interaction: discord.Interaction, select: discord.ui.Select):
				
		self.selected_channel = interaction.guild.get_channel(select.values[0].id)

		if self.selected_role and self.selected_channel is not None:
			self.children[2].disabled = False

		if self.selected_channel == None and self.selected_role == None:
			return await interaction.response.edit_message(
				content=f"**Add/Edit Channel** \n` -> `   Channel `{self.selected_channel}` will be locked for `{self.selected_role}` role.", 
				view=self, allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False)
			)
		elif self.selected_channel != None and self.selected_role == None:
			return await interaction.response.edit_message(
				content=f"**Add/Edit Channel** \n` -> `   Channel {self.selected_channel.mention} will be locked for `{self.selected_role}` role.", 
				view=self, allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False)
			)
		elif self.selected_channel == None and self.selected_role != None:
			return await interaction.response.edit_message(
				content=f"**Add/Edit Channel** \n` -> `   Channel `{self.selected_channel}` will be locked for {self.selected_role.mention} role.", 
				view=self, allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False)
			)
		else:
			return await interaction.response.edit_message(
				content=f"**Add/Edit Channel** \n` -> `   Channel {self.selected_channel.mention} will be locked for {self.selected_role.mention} role.", 
				view=self, allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False)
			)
	
	@discord.ui.select(cls=RoleSelect, placeholder="Lock for which role?", disabled=False)
	async def role_select(self, interaction: discord.Interaction, select: discord.ui.Select):
		
		self.selected_role = interaction.guild.get_role(select.values[0].id)

		if self.selected_role and self.selected_channel is not None:
			self.children[2].disabled = False

		if self.selected_channel == None and self.selected_role == None:
			return await interaction.response.edit_message(
				content=f"**Add/Edit Channel** \n` -> `   Channel `{self.selected_channel}` will be locked for `{self.selected_role}` role.", 
				view=self, allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False)
			)
		elif self.selected_channel != None and self.selected_role == None:
			return await interaction.response.edit_message(
				content=f"**Add/Edit Channel** \n` -> `   Channel {self.selected_channel.mention} will be locked for `{self.selected_role}` role.", 
				view=self, allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False)
			)
		elif self.selected_channel == None and self.selected_role != None:
			return await interaction.response.edit_message(
				content=f"**Add/Edit Channel** \n` -> `   Channel `{self.selected_channel}` will be locked for {self.selected_role.mention} role.", 
				view=self, allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False)
			)
		else:
			return await interaction.response.edit_message(
				content=f"**Add/Edit Channel** \n` -> `   Channel {self.selected_channel.mention} will be locked for {self.selected_role.mention} role.", 
				view=self, allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False)
			)

	@discord.ui.button(label="Submit", style=discord.ButtonStyle.green, disabled=True)
	async def submit(self, interaction: discord.Interaction, button: discord.ui.Button):

		if (len(self.data[self.name]['channel_and_role'].keys())>=25):
			warning = discord.Embed(
				color=0xDA2A2A,
				description=f"<a:nat_cross:1010969491347357717> **|** Can't add more than 25 channels, please consider deleting some!")
			return await interaction.response.edit_message(view=None, content=None, embed=warning)
		
		self.data[self.name]['channel_and_role'][str(self.selected_channel.id)] = str(self.selected_role.id)
		await interaction.client.lockdown.update(self.data)
		await update_embed(self.interaction, self.data, self.name, False, self.message)

		embed = discord.Embed(
					color=0x43b581, 
					description=f'<a:nat_check:1010969401379536958> **|** Channel {self.selected_channel.mention} will be locked/unlocked for role {self.selected_role.mention}.'
				)
		await interaction.response.edit_message(
			content = None, embed = embed, view = None, 
			allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False)
		)
		
		self.selected_role = None
		self.selected_channel = None

class Delete_channel(discord.ui.Select):
	def __init__(self, interaction: discord.Interaction, data: dict, name: str, options, message: discord.Message):
		super().__init__(placeholder="Select", custom_id="LOCKDOWN:DELETE:CHANNEL", options=options)
		self.interaction = interaction
		self.data = data
		self.name = name
		self.message = message

	# This function is called when the user has chosen an option
	async def callback(self, interaction: discord.Interaction):

		failed = False
		if str(self.values[0]) in self.data[self.name]['channel_and_role'].keys():
			del self.data[self.name]['channel_and_role'][str(self.values[0])]
		else:
			failed = True
		await interaction.client.lockdown.update(self.data)
		await update_embed(self.interaction, self.data, self.name, failed, self.message)

		channel = interaction.guild.get_channel(int(self.values[0]))
		embed = discord.Embed(
					color=0x43b581, 
					description=f'<a:nat_check:1010969401379536958> **|** Channel {channel.mention} is successfully removed from **Lockdown Profile** `{self.name}`.'
				)
		await interaction.response.edit_message(
			content = None, embed = embed, view = None, 
			allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False)
		)

class Channel_modify_panel(discord.ui.View):
	def __init__(self, interaction: discord.Interaction, data: dict, name: str, message: discord.Message):
		super().__init__()
		self.interaction = interaction
		self.message = None 
		self.data = data
		self.name = name
		self.message = message
		self.selected_channel = None
		self.selected_role = None
	
	@discord.ui.button(label="Default Role", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>")
	async def default_role(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.lockdown.find(interaction.guild.id)
		view = Dropdown_Channel(interaction)
		await interaction.response.send_message(view=view, ephemeral=True)
		await self.interaction.delete_original_response()
		await view.wait()
		if view.value is None:
			embed = await get_warning_embed(f'Dropdown timed out, please retry.')
			return await interaction.edit_original_response(
				content = None, embed = embed, view = None
			)
		else:
			channel_id = view.value.id			
			if (len(self.data[self.name]['channel_and_role'].keys())>=25):
				warning = discord.Embed(
					color=0xDA2A2A,
					description=f"<a:nat_cross:1010969491347357717> **|** Can't add more than 25 channels, please consider deleting some!")
				return await interaction.edit_original_response(view=None, content=None, embed=warning)
		
			self.data[self.name]['channel_and_role'][str(channel_id)] = str(self.interaction.guild.default_role.id)
			await interaction.client.lockdown.update(self.data)
			await update_embed(self.interaction, self.data, self.name, False, self.message)
			embed = await get_success_embed(f'Channel {view.value.mention} will be locked/unlocked for {interaction.guild.default_role} role.')
			await interaction.edit_original_response(
				content = None, embed = embed, view = None
			)


	@discord.ui.button(label="Custom Role", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>")
	async def custom_role(self, interaction: discord.Interaction, button: discord.ui.Button):
		view = Select_channel_roles(interaction, self.data, self.name, self.message)
		await interaction.response.send_message(content="Please choose from below dropdowns...", view=view, ephemeral=True)
		await self.interaction.delete_original_response()
		await view.wait()

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
