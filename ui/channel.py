import discord
import datetime
import asyncio
import io
from discord import Interaction
from discord.ui import ChannelSelect, RoleSelect

async def update_embed(interaction: Interaction, data: dict, name:str , failed:bool):

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
			roleIds = [int(role_ids) for role_ids in panel['channel_and_role'][channel_id].split(" ") if role_ids != '' and role_ids not in ["everyone"]]
			roleIds = [discord.utils.get(interaction.guild.roles, id=id) for id in roleIds]
			role = [role for role in roleIds if role != None]
			if channel:
				lockdown_config += f'{channel.mention} | {" + ".join([role.mention for role in role])}\n'
	else:
		lockdown_config = "None"

	embed.add_field(name="Channel Settings", value=f"{lockdown_config}", inline=False)

	lockmsg_config = f"**Title:** {panel['lock_embed']['title']}\n"
	lockmsg_config += f"**Thumbnail:** [**Click here**]({panel['lock_embed']['thumbnail']})\n"
	lockmsg_config += f"**Description:**\n```{panel['lock_embed']['description']}```\n"
	
	embed.add_field(name="Embed Message for Lockdown", value=f"{lockmsg_config}", inline=False)

	unlockmsg_config = f"**Title:** {panel['unlock_embed']['title']}\n"
	unlockmsg_config += f"**Thumbnail:** [**Click here**]({panel['unlock_embed']['thumbnail']})\n"
	unlockmsg_config += f"**Description:**\n```{panel['unlock_embed']['description']}```\n"
	
	embed.add_field(name="Embed Message for Unlockdown", value=f"{unlockmsg_config}", inline=False)

	await interaction.message.edit(embed=embed)
	# await interaction.followup.send(f"Updated Lockdown Config", ephemeral=True)

class Lockdown_Config_Panel(discord.ui.View):
	def __init__(self, interaction: discord.Interaction, data: dict, name: str ,message: discord.Message=None):
		super().__init__(timeout=180)
		self.interaction = interaction
		self.data = data
		self.message = message
		self.name = name
	
	@discord.ui.button(label="Add/Edit Channel", style=discord.ButtonStyle.gray, emoji="<:channel:1017378607863181322>", custom_id="LOCKDOWN:ADD:CHANNEL", row = 0)
	async def add_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
		view = Select_channel_roles(interaction, self.data, self.name)
		await interaction.response.send_message(content="Please choose from below dropdowns...", view=view, ephemeral=True)
		await view.wait()
	
	@discord.ui.button(label="Delete Channel", style=discord.ButtonStyle.gray, emoji="<:nat_delete:1063067661602402314>", custom_id="LOCKDOWN:DELETE:CHANNEL", row=0)
	async def delete_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
				
		channels = [interaction.guild.get_channel(int(channel_id)) for channel_id in self.data[self.name]['channel_and_role'].keys()]
		options = []

		for channel in channels:
			role = interaction.guild.get_role(int(self.data[self.name]['channel_and_role'][str(channel.id)]))
			options.append(discord.SelectOption(label=channel.name, value=str(channel.id), emoji="<:channel:1017378607863181322>", description=f"{role.name} 🧑 {len(role.members)}"))
		# create ui.Select instance and add it to a new view
		select = Delete_channel(interaction, self.data, self.name, options)
		view_select = discord.ui.View()
		view_select.add_item(select)

		# edit the message with the new view
		await interaction.response.send_message(content="Select channel to remove.", view=view_select, ephemeral=True)

	@discord.ui.button(label="Lockdown Message", style=discord.ButtonStyle.gray, emoji="<a:nat_message:1063077628036272158>", custom_id="LOCKDOWN:MODIFY:LOCK:MSG", row = 1)
	async def lockdown_msg(self, interaction: discord.Interaction, button: discord.ui.Button):
		modal = Lockdown_Add_Channel(interaction,self.name, self.data)

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

	@discord.ui.button(label="Unlockdown Message", style=discord.ButtonStyle.gray, emoji="<a:nat_message:1063077628036272158>", custom_id="UNLOCKDOWN:MODIFY:LOCK:MSG", row = 1)
	async def unlockdown_msg(self, interaction: discord.Interaction, button: discord.ui.Button):
		modal = Lockdown_Add_Channel(interaction,self.name, self.data)

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
			warning = discord.Embed(
				color=0xffd300,
				title=f"<a:nat_warning:1062998119899484190> **|** This is not your menu.")
			return await interaction.response.send_message(embed=warning, ephemeral=True)	
		return True

	async def on_timeout(self):
		for button in self.children:
			button.disabled = True
			await self.message.edit(view=self)

class Lockdown_Add_Channel(discord.ui.Modal):
	def __init__(self, interaction: Interaction, name: str, data: dict):
		super().__init__(timeout=None, title=f"Configuring {name.title()}")
		self.data = data
		self.interaction = interaction
		self.name = name
	
	async def on_submit(self, interaction: Interaction):
		await interaction.response.defer(thinking=True, ephemeral=True)
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
		await update_embed(interaction, self.data, self.name, failed)

class Select_channel_roles(discord.ui.View):
	def __init__(self, interaction: discord.Interaction, data: dict, name: str):
		super().__init__()
		self.interaction = interaction
		self.data = data
		self.name = name
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
		await update_embed(self.interaction, self.data, self.name, False)

		# await interaction.response.edit_message(view=None ,content=f"\n` -> `   {self.selected_channel.mention}\n` -> `   {self.selected_role.mention}")
		await interaction.response.edit_message(view=None ,content=f"Successfully Updated Channel Settings!")
		
		await interaction.delete_original_response()
		self.selected_role = None
		self.selected_channel = None

class Delete_channel(discord.ui.Select):
	def __init__(self, interaction: discord.Interaction, data: dict, name: str, options):
		super().__init__(placeholder="Select", custom_id="LOCKDOWN:DELETE:CHANNEL", options=options)
		self.interaction = interaction
		self.data = data
		self.name = name

	# This function is called when the user has chosen an option
	async def callback(self, interaction: discord.Interaction):

		failed = False
		if str(self.values[0]) in self.data[self.name]['channel_and_role'].keys():
			del self.data[self.name]['channel_and_role'][str(self.values[0])]
		else:
			failed = True
		await interaction.client.lockdown.update(self.data)
		await update_embed(self.interaction, self.data, self.name, failed)

		await interaction.response.edit_message(view=None ,content=f"Successfully Deleted Channel!")
		await interaction.delete_original_response()