import asyncio
import datetime
from itertools import islice
import discord
from humanfriendly import format_timespan

from utils.convertor import DMCConverter, TimeConverter
from utils.embeds import get_error_embed, get_formated_embed, get_invisible_embed, get_success_embed, get_warning_embed
from utils.types import GrinderProfile
from utils.views.confirm import Confirm
from utils.views.modal import General_Modal
from utils.views.paginator import Paginator
from utils.views.selects import Role_select, Select_General
from utils.views.ui import Dropdown_Channel


async def update_grinder_settings_embed(interaction: discord.Interaction, data: dict):

	embed = discord.Embed(
		color=3092790,
		title="Configure Dank's Grinder Manager"
	)

	channel = interaction.guild.get_channel(data['payment_channel'])
	if channel is None:
		channel = f"`None`"
	else:
		channel = f"{channel.mention}"
	embed.add_field(name="Payment Channel:", value=f"<:nat_reply:1146498277068517386> {channel}", inline=True)

	channel = interaction.guild.get_channel(data['grinder_logs'])
	if channel is None:
		channel = f"`None`"
	else:
		channel = f"{channel.mention}"
	embed.add_field(name="Logs Channel:", value=f"<:nat_reply:1146498277068517386> {channel}", inline=True)
	embed.add_field(name="\u200b", value='\u200b', inline=True)

	grinder_duration = data['grinder']['demotion_in']
	role = interaction.guild.get_role(data['grinder']['role'])
	if grinder_duration == 0:
		grinder_duration = f"**Demote in:** `None`"
	else:
		grinder_duration = f"**Demote in:** {format_timespan(grinder_duration)}"
	if role is None:
		role = f"**Role:** `None`"
	else:
		role = f"**Role:** {role.mention}"
	embed.add_field(name="Grinder Config:", value=f"<:nat_replycont:1146496789361479741> {role} \n <:nat_reply:1146498277068517386> {grinder_duration}", inline=True)
				
	
	trial_duration = data['trial']['duration']
	trial_role = interaction.guild.get_role(data['trial']['role'])
	if trial_duration == 0:
		trial_duration = f"**Promote in:** `None`"
	else:
		trial_duration = f"**Promote in:** {format_timespan(trial_duration)}"
	if trial_role is None:
		trial_role = f"**Role:** `None`"
	else:
		trial_role = f"**Role:** {trial_role.mention}"
	embed.add_field(name="Trial Config:", value=f"<:nat_replycont:1146496789361479741> {trial_role} \n <:nat_reply:1146498277068517386> {trial_duration}", inline=True)
	embed.add_field(name="\u200b", value='\u200b', inline=True)

	roles = data['manager_roles']
	roles = [interaction.guild.get_role(role) for role in roles if interaction.guild.get_role(role) is not None]
	roles = [f'1. {role.mention}' for role in roles]
	role = "\n".join(roles)
	if len(roles) == 0 :
		role = f"` - ` Add grinder mangers when?"
	embed.add_field(name="Manager Roles:", value=f">>> {role}", inline=False)

	if len(data['grinder_profiles']) == 0:
		profiles = f"` - ` **Add profiles when?**\n"
	else:
		profiles = ""
		for key in data['grinder_profiles'].keys():
			profiles += f"1. **{data['grinder_profiles'][key]['name'].title()}** : <@&{key}>\n"
	embed.add_field(name='Grinder Profiles:', value=f">>> {profiles}", inline=False)

	await interaction.message.edit(embed=embed)

def chunk(it, size):
	it = iter(it)
	return iter(lambda: tuple(islice(it, size)), ())

class GrinderConfigPanel(discord.ui.View):

	def __init__(self, interaction: discord.Interaction):
		super().__init__()
		self.interaction = interaction
		self.message = None
	
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

	@discord.ui.button(label="Payment Channel", style=discord.ButtonStyle.gray, emoji="<:tgk_channel:1073908465405268029>", row=1)
	async def payout_channel(self, interaction: discord.Interaction , button: discord.ui.Button):
		data = await interaction.client.grinderSettings.find(interaction.guild.id)
		view = Dropdown_Channel(interaction)
		await interaction.response.send_message(view=view, ephemeral=True)
		await view.wait()
		if view.value is None:
			embed = await get_warning_embed(f'Dropdown timed out, please retry.')
			return await interaction.edit_original_response(
				content = None, embed = embed, view = None
			)
		else:
			channel = data['payment_channel']
			if channel is None:
				channel = f"**`None`**"
			else:
				channel = interaction.guild.get_channel(channel)
				if channel is None:
					data['payment_channel'] = None
					await interaction.client.grinderSettings.upsert(data)
					channel = f"**`None`**"
				else:
					channel = channel.mention

			if data['payment_channel'] is None or data['payment_channel'] != view.value.id:
				data['payment_channel'] = view.value.id
				await interaction.client.grinderSettings.upsert(data)
				embed = await get_success_embed(f'Payment Channel changed from {channel} to {view.value.mention}')
				await interaction.edit_original_response(
					content = None, embed = embed, view = None
				)
				await update_grinder_settings_embed(self.interaction, data)
			else:
				embed = await get_error_embed(f"Payment Channel was already set to {channel}")
				return await interaction.edit_original_response(
					content = None, embed = embed, view = None
				)


	@discord.ui.button(label="Logs Channel", style=discord.ButtonStyle.gray, emoji="<:tgk_channel:1073908465405268029>", row=1)
	async def logs_channel(self, interaction: discord.Interaction , button: discord.ui.Button):
		data = await interaction.client.grinderSettings.find(interaction.guild.id)
		view = Dropdown_Channel(interaction)
		await interaction.response.send_message(view=view, ephemeral=True)
		await view.wait()
		if view.value is None:
			embed = await get_warning_embed(f'Dropdown timed out, please retry.')
			return await interaction.edit_original_response(
				content = None, embed = embed, view = None
			)
		else:
			channel = data['grinder_logs']
			if channel is None:
				channel = f"**`None`**"
			else:
				channel = interaction.guild.get_channel(channel)
				if channel is None:
					data['grinder_logs'] = None
					await interaction.client.grinderSettings.upsert(data)
					channel = f"**`None`**"
				else:
					channel = channel.mention

			if data['grinder_logs'] is None or data['grinder_logs'] != view.value.id:
				data['grinder_logs'] = view.value.id
				await interaction.client.grinderSettings.upsert(data)
				embed = await get_success_embed(f'Logging Channel changed from {channel} to {view.value.mention}')
				await interaction.edit_original_response(
					content = None, embed = embed, view = None
				)
				await update_grinder_settings_embed(self.interaction, data)
			else:
				embed = await get_error_embed(f"Logging Channel was already set to {channel}")
				return await interaction.edit_original_response(
					content = None, embed = embed, view = None
				)

	@discord.ui.button(label="Grinder Role", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>", row=2)
	async def base_role(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.grinderSettings.find(interaction.guild.id)
		modal = General_Modal(title="Grinder Configuration", interaction=interaction)
		modal.duration = discord.ui.TextInput(custom_id="duration", label="Number of missed days to get trial role",placeholder="Enter a value between 1 to 24", max_length=2, style=discord.TextStyle.short)

		modal.add_item(modal.duration)
		await interaction.response.send_modal(modal)
		await modal.wait()

		if modal.value is None or modal.value is False:
			return await interaction.delete_original_response()
		
		try:
			if int(modal.duration.value) < 1 or int(modal.duration.value) > 24:
				raise ValueError
			duration = int(modal.duration.value)*3600*24
		except:
			embed = await get_error_embed(f"Invalid duration provided")
			return await interaction.edit_original_response(embed=embed, view=None)

		role_view = discord.ui.View()
		role_view.value = None
		role_view.select = Role_select(placeholder="Grinder role is:", min_values=1, max_values=1)
		role_view.add_item(role_view.select)

		await modal.interaction.response.send_message(view=role_view, ephemeral=True)
		await role_view.wait()

		if role_view.value is None or role_view.value is False:
			return await interaction.delete_original_response()
		
		role = role_view.select.values[0]
		
		if duration is None:
			duration = 0
		
		data["grinder"] = {
			"role": role.id,
			"demotion_in": duration
		}
		await interaction.client.grinderSettings.upsert(data)
		embed = await get_success_embed(f"Grinder role is updated to {role.mention}")
		await role_view.select.interaction.response.edit_message(embed=embed, view=None)
		await update_grinder_settings_embed(self.interaction, data)

	@discord.ui.button(label="Trial Config", style=discord.ButtonStyle.gray, emoji="<:tgk_money:1199223318662885426>", row=2)
	async def trail(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.grinderSettings.find(interaction.guild.id)
		modal = General_Modal(title="Trial Configuration", interaction=interaction)
		modal.duration = discord.ui.TextInput(custom_id="duration", label="Number of days paid to get grinder role?",placeholder="Enter a value between 1 to 24", max_length=2, style=discord.TextStyle.short)

		modal.add_item(modal.duration)
		await interaction.response.send_modal(modal)
		await modal.wait()

		if modal.value is None or modal.value is False:
			return await interaction.delete_original_response()
		
		try:
			if int(modal.duration.value) < 1 or int(modal.duration.value) > 24:
				raise ValueError
			duration = int(modal.duration.value)*3600*24
		except:
			embed = await get_error_embed(f"Invalid duration provided")
			return await interaction.edit_original_response(embed=embed, view=None)

		role_view = discord.ui.View()
		role_view.value = None
		role_view.select = Role_select(placeholder="Trial grinder role is:", min_values=1, max_values=1)
		role_view.add_item(role_view.select)

		await modal.interaction.response.send_message(view=role_view, ephemeral=True)
		await role_view.wait()

		if role_view.value is None or role_view.value is False:
			return await interaction.delete_original_response()
		
		role = role_view.select.values[0]
		
		if duration is None:
			duration = 0
		
		data["trial"] = {
			"role": role.id,
			"duration": duration
		}
		await interaction.client.grinderSettings.upsert(data)
		embed = await get_success_embed(f"Trial grinder role is updated to {role.mention}")
		await role_view.select.interaction.response.edit_message(embed=embed, view=None)
		await update_grinder_settings_embed(self.interaction, data)

	@discord.ui.button(label="Manager Roles", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>",row=3)
	async def manager_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.grinderSettings.find(interaction.guild.id)
		view = discord.ui.View()
		view.value = None
		view.role_select = Role_select(placeholder="Which all roles can manage grinders?", min_values=1, max_values=5)
		view.add_item(view.role_select)
		await interaction.response.send_message(view=view, ephemeral=True)

		await view.wait()

		if view.value is None or view.value is False:
			return await interaction.delete_original_response()
		
		add_roles = ""
		remove_roles = ""

		for role in view.role_select.values:
			if role not in data["manager_roles"]:
				data["manager_roles"].append(role.id)
				add_roles += f"{role.mention} "
			else:
				data["manager_roles"].remove(role.id)
				remove_roles += f"{role.mention} "
		await interaction.client.grinderSettings.upsert(data)
		await view.role_select.interaction.response.edit_message(content=f"Added Roles: {add_roles}\nRemoved Roles: {remove_roles}", view=None)
		await view.role_select.interaction.delete_original_response()

		await update_grinder_settings_embed(self.interaction, data)

	@discord.ui.button(label="Grinder Profiles", style=discord.ButtonStyle.gray, emoji="<:tgk_entries:1124995375548338176>", row=3)
	async def profiles(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.grinderSettings.find(interaction.guild.id)
		embed = discord.Embed(
			color=3092790,
			title="Manage Grinder Profiles"
		)
		if len(data['grinder_profiles']) == 0:
			embed.description = "No profiles found. Add some profiles to manage grinders."
		else:
			profiles = ""
			for key in data['grinder_profiles'].keys():
				profiles += f"\n` - ` **{data['grinder_profiles'][key]['name'].title()}** \n<:nat_replycont:1146496789361479741>**Role:** <@&{key}>\n<:nat_replycont:1146496789361479741>**Payment:** ⏣ {data['grinder_profiles'][key]['payment']:,}\n<:nat_reply:1146498277068517386>**Frequency:** {format_timespan(data['grinder_profiles'][key]['frequency'])}\n"
			embed.description = profiles
		view = GrinderProfilePanel(interaction, data)
		await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
		view.message = await interaction.original_response()

	@discord.ui.button(label="Edit DM Embeds", style=discord.ButtonStyle.gray, emoji="<:tgk_edit:1073902428224757850>", row=4)
	async def embeds(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = await interaction.client.grinderSettings.find(interaction.guild.id)
		embed = discord.Embed(
			color=3092790,
			title="Manage DM Embeds"
		)
		embed.add_field(
			name = "Appoint Embed",
			value = f"**Thumbnail:** [Link]({data['appoint_embed']['thumbnail']})\n**Description:** ```{data['appoint_embed']['description']}```\n",
			inline = False
		)
		embed.add_field(
			name = "Dismiss Embed",
			value = f"**Thumbnail:** [Link]({data['dismiss_embed']['thumbnail']})\n**Description:** ```{data['dismiss_embed']['description']}```\n",
			inline = False
		)
		embed.add_field(
			name = "Vacation Embed",
			value = f"**Thumbnail:** [Link]({data['vacation_embed']['thumbnail']})\n**Description:** ```{data['vacation_embed']['description']}```\n",
			inline = False
		)
		view = GrinderEmbedPanel(interaction, data)
		await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
		view.message = await interaction.original_response()

class GrinderProfilePanel(discord.ui.View):
	def __init__(self, interaction: discord.Interaction, data):
		super().__init__()
		self.interaction = interaction
		self.message = None
		self.data = data
	
	@discord.ui.button(label="Create", style=discord.ButtonStyle.gray, emoji="<:tgk_add:1073902485959352362>",row=1)
	async def create_profile(self, interaction: discord.Interaction, button: discord.ui.Button):
		if len(self.data['grinder_profiles']) >= self.data['max_profiles']:
			embed = await get_warning_embed(f"You have reached the maximum number of profiles")
			return await self.message.edit(embed=embed, ephemeral=True)

		profile_modal = General_Modal(title="Create Grinder Profile", interaction=interaction)
		profile_modal.profile_name = discord.ui.TextInput(custom_id="profile_name", label="Profile Name",placeholder="Enter the Profile Name,Ex:Legendary Grinder (3M)", max_length=50, style=discord.TextStyle.short)
		profile_modal.profile_amount = discord.ui.TextInput(custom_id="profile_amount", label="Grind Amount",placeholder="Enter the Grind Amount Ex: 3M", max_length=10, style=discord.TextStyle.short)
		profile_modal.profile_time = discord.ui.TextInput(custom_id="profile_time", label="Frquency",placeholder="Enter the Frequency of the grind Ex: 1d/1w", max_length=50, style=discord.TextStyle.short)

		profile_modal.add_item(profile_modal.profile_name)
		profile_modal.add_item(profile_modal.profile_amount)
		# profile_modal.add_item(profile_modal.profile_time)

		await interaction.response.send_modal(profile_modal)

		await profile_modal.wait()
		if profile_modal.value is None or profile_modal.value is False:
			return await interaction.delete_original_response()
		
		profile_name = profile_modal.profile_name.value
		profile_amount = int(await DMCConverter().convert(profile_modal.interaction, profile_modal.profile_amount.value))
		profile_time = int(await TimeConverter().convert(profile_modal.interaction, '1d'))

		role_view = discord.ui.View()
		role_view.value = None
		role_view.select = Role_select(placeholder="Select role for the profile", min_values=1, max_values=1)
		role_view.add_item(role_view.select)

		await profile_modal.interaction.response.edit_message(embed=None, view=role_view)

		await role_view.wait()
		if role_view.value is None or role_view.value is False:
			return await interaction.delete_original_response()
		
		profile_role = role_view.select.values[0]
		
		if str(profile_role.id) in self.data['grinder_profiles'].keys():
			await role_view.select.interaction.response.edit_message(f"This role already has a profile {self.data['grinder_profiles'][str(profile_role.id)]['name']}", ephemeral=True)
			return
		
		self.data['grinder_profiles'][str(profile_role.id)] = GrinderProfile(
			name=profile_name,
			role=profile_role.id,
			payment=profile_amount,
			frequency=profile_time
		)
		await interaction.client.grinderSettings.upsert(self.data)
		await update_grinder_settings_embed(self.interaction, self.data)
		await interaction.delete_original_response()

	@discord.ui.button(label="Delete", style=discord.ButtonStyle.gray, emoji="<:tgk_delete:1113517803203461222>",row=1)
	async def delete_profile(self, interaction: discord.Interaction, button: discord.ui.Button):
		if len(self.data['grinder_profiles']) == 0:
			embed = await get_error_embed(f"Create profiles before attempting to delete them!")
			return await self.message.edit(embed = embed, ephemeral=True)
		
		profile_select = discord.ui.View()
		profile_select.value = None
		profile_select.select = Select_General(interaction=interaction, placeholder="Select a profile to remove", max_values=1, min_values=1,options=[
			discord.SelectOption(label=self.data['grinder_profiles'][role_id]["name"].title(), value=role_id)
			for role_id in self.data['grinder_profiles']
		])
		profile_select.add_item(profile_select.select)

		await interaction.response.edit_message(view=profile_select, embed=None)

		await profile_select.wait()
		if profile_select.value is None or profile_select.value is False:
			return await interaction.delete_original_response()

		profile_name = ''
		role_id = self.data['grinder_profiles'][profile_select.select.values[0]]
		for role_id in profile_select.select.values:
			profile_name = self.data['grinder_profiles'][role_id]['name'].title()
			del self.data['grinder_profiles'][role_id]
		
		log_channel = interaction.guild.get_channel(self.data['grinder_logs'])
		if log_channel:
			try:
				await log_channel.send(embed = await get_warning_embed(f"Profile `{profile_name}` was deleted by {interaction.user.mention}"), allowed_mentions= discord.AllowedMentions.none())
			except:
				pass

		await interaction.client.grinderSettings.upsert(self.data)
		await update_grinder_settings_embed(self.interaction, self.data)
		await interaction.delete_original_response()

		grinder_profiles  = await interaction.client.grinderUsers.get_all({"guild": interaction.guild.id, "active": True})
		for profile in grinder_profiles:
			if profile['profile_role'] == int(role_id):
				profile['active'] = False
				await interaction.client.grinderUsers.upsert(profile)
				user = interaction.guild.get_member(profile['user'])
				if user:
					try:
						roles_to_remove = [profile['profile_role'],self.data['grinder']['role'],self.data['trial']['role']]
						roles_to_remove = [role for role in user.roles if role.id in roles_to_remove]
						await user.remove_roles(*roles_to_remove)
					except:
						pass
				
					embed = discord.Embed(
						color=discord.Color.red(),
						title="Grinder Profile Deleted"
					)
					embed.add_field(name=f"Profile Name:", value=f"{profile_name}", inline=True)
					role = interaction.guild.get_role(int(role_id))
					if role is not None:
						embed.add_field(name=f"Profile Role:", value=f"{role.name}", inline=True)
					else:
						embed.add_field(name=f"Profile Role:", value=f"Role was deleted", inline=True)
					embed.add_field(name=f"Reason:", value=f"Profile was deleted by {interaction.user.mention}", inline=False)
					try:
						embed.set_footer(text=f"{interaction.guild.name} | {interaction.guild.id}", icon_url=interaction.guild.icon.url)
					except: 
						embed.set_footer(text=f"{interaction.guild.name} | {interaction.guild.id}")
					try:
						await user.send(embed=embed)
						await asyncio.sleep(0.1)
					except:
						pass


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

class GrinderEmbedPanel(discord.ui.View):
	def __init__(self, interaction: discord.Interaction, data):
		super().__init__()
		self.interaction = interaction
		self.message = None
		self.data = data
	
	@discord.ui.button(label="Appoint Embed", style=discord.ButtonStyle.gray, emoji="<:tgk_message:1113527047373979668>",row=1)
	async def appoint_embed(self, interaction: discord.Interaction, button: discord.ui.Button):

		profile_modal = General_Modal(title="Modify Appoint Embed", interaction=interaction)
		profile_modal.profile_tb = discord.ui.TextInput(custom_id="profile_tb", label="Thumbnail:",placeholder="Enter thumbnail url", max_length=1000, style=discord.TextStyle.long, default=self.data['appoint_embed']['thumbnail'])
		profile_modal.profile_desc = discord.ui.TextInput(custom_id="profile_desc", label="Description:",placeholder="Enter content you wish to dm grinders", max_length=3000, style=discord.TextStyle.paragraph, default=self.data['appoint_embed']['description'])

		profile_modal.add_item(profile_modal.profile_tb)
		profile_modal.add_item(profile_modal.profile_desc)

		await interaction.response.send_modal(profile_modal)

		await profile_modal.wait()
		if profile_modal.value is None or profile_modal.value is False:
			return await interaction.delete_original_response()

		tb = profile_modal.profile_tb.value
		desc = profile_modal.profile_desc.value

		data = self.data
		data['appoint_embed'] = {
			"thumbnail": tb,
			"description": desc,
		}
		await interaction.client.grinderSettings.upsert(data)

		embed = discord.Embed(
			color=3092790,
			title="Manage DM Embeds"
		)
		embed.add_field(
			name = "Appoint Embed",
			value = f"**Thumbnail:** [Link]({data['appoint_embed']['thumbnail']})\n**Description:** ```{data['appoint_embed']['description']}```\n",
			inline = False
		)
		embed.add_field(
			name = "Dismiss Embed",
			value = f"**Thumbnail:** [Link]({data['dismiss_embed']['thumbnail']})\n**Description:** ```{data['dismiss_embed']['description']}```\n",
			inline = False
		)
		embed.add_field(
			name = "Vacation Embed",
			value = f"**Thumbnail:** [Link]({data['vacation_embed']['thumbnail']})\n**Description:** ```{data['vacation_embed']['description']}```\n",
			inline = False
		)
		await profile_modal.interaction.response.edit_message(embed=embed)

	@discord.ui.button(label="Dismiss Embed", style=discord.ButtonStyle.gray, emoji="<:tgk_message:1113527047373979668>",row=1)
	async def dismiss_embed(self, interaction: discord.Interaction, button: discord.ui.Button):

		profile_modal = General_Modal(title="Modify Dismiss Embed", interaction=interaction)
		profile_modal.profile_tb = discord.ui.TextInput(custom_id="profile_tb", label="Thumbnail:",placeholder="Enter thumbnail url", max_length=1000, style=discord.TextStyle.long, default=self.data['dismiss_embed']['thumbnail'])
		profile_modal.profile_desc = discord.ui.TextInput(custom_id="profile_desc", label="Description:",placeholder="Enter content you wish to dm grinders", max_length=3000, style=discord.TextStyle.paragraph, default=self.data['dismiss_embed']['description'])

		profile_modal.add_item(profile_modal.profile_tb)
		profile_modal.add_item(profile_modal.profile_desc)

		await interaction.response.send_modal(profile_modal)

		await profile_modal.wait()
		if profile_modal.value is None or profile_modal.value is False:
			return await interaction.delete_original_response()

		tb = profile_modal.profile_tb.value
		desc = profile_modal.profile_desc.value

		data = self.data
		data['dismiss_embed'] = {
			"thumbnail": tb,
			"description": desc,
		}
		await interaction.client.grinderSettings.upsert(data)

		embed = discord.Embed(
			color=3092790,
			title="Manage DM Embeds"
		)
		embed.add_field(
			name = "Appoint Embed",
			value = f"**Thumbnail:** [Link]({data['appoint_embed']['thumbnail']})\n**Description:** ```{data['appoint_embed']['description']}```\n",
			inline = False
		)
		embed.add_field(
			name = "Dismiss Embed",
			value = f"**Thumbnail:** [Link]({data['dismiss_embed']['thumbnail']})\n**Description:** ```{data['dismiss_embed']['description']}```\n",
			inline = False
		)
		embed.add_field(
			name = "Vacation Embed",
			value = f"**Thumbnail:** [Link]({data['vacation_embed']['thumbnail']})\n**Description:** ```{data['vacation_embed']['description']}```\n",
			inline = False
		)
		await profile_modal.interaction.response.edit_message(embed=embed)
	
	@discord.ui.button(label="Vacation Embed", style=discord.ButtonStyle.gray, emoji="<:tgk_message:1113527047373979668>",row=1)
	async def vacation_embed(self, interaction: discord.Interaction, button: discord.ui.Button):

		profile_modal = General_Modal(title="Modify Vacation Embed", interaction=interaction)
		profile_modal.profile_tb = discord.ui.TextInput(custom_id="profile_tb", label="Thumbnail:",placeholder="Enter thumbnail url", max_length=1000, style=discord.TextStyle.long, default=self.data['vacation_embed']['thumbnail'])
		profile_modal.profile_desc = discord.ui.TextInput(custom_id="profile_desc", label="Description:",placeholder="Enter content you wish to dm grinders", max_length=3000, style=discord.TextStyle.paragraph, default=self.data['vacation_embed']['description'])

		profile_modal.add_item(profile_modal.profile_tb)
		profile_modal.add_item(profile_modal.profile_desc)

		await interaction.response.send_modal(profile_modal)

		await profile_modal.wait()
		if profile_modal.value is None or profile_modal.value is False:
			return await interaction.delete_original_response()

		tb = profile_modal.profile_tb.value
		desc = profile_modal.profile_desc.value

		data = self.data
		data['vacation_embed'] = {
			"thumbnail": tb,
			"description": desc,
		}
		await interaction.client.grinderSettings.upsert(data)

		embed = discord.Embed(
			color=3092790,
			title="Manage DM Embeds"
		)
		embed.add_field(
			name = "Appoint Embed",
			value = f"**Thumbnail:** [Link]({data['appoint_embed']['thumbnail']})\n**Description:** ```{data['appoint_embed']['description']}```\n",
			inline = False
		)
		embed.add_field(
			name = "Dismiss Embed",
			value = f"**Thumbnail:** [Link]({data['dismiss_embed']['thumbnail']})\n**Description:** ```{data['dismiss_embed']['description']}```\n",
			inline = False
		)
		embed.add_field(
			name = "Vacation Embed",
			value = f"**Thumbnail:** [Link]({data['vacation_embed']['thumbnail']})\n**Description:** ```{data['vacation_embed']['description']}```\n",
			inline = False
		)
		await profile_modal.interaction.response.edit_message(embed=embed)

	@discord.ui.button(label="Reset Embeds", style=discord.ButtonStyle.red, emoji="<:tgk_delete:1113517803203461222>",row=1)
	async def reset_embeds(self, interaction: discord.Interaction, button: discord.ui.Button):
		data = self.data
		data["appoint_embed"] = {
			'description' : f"We're excited to inform you that you've been appointed as one of our newest trial grinders! If you have any questions or need further information, feel free to reach out to us anytime. Let's make this journey memorable and enjoyable together! ",
			'thumbnail' : 'https://cdn.discordapp.com/emojis/814161045966553138.webp?size=128&quality=lossless',
		}
		data["dismiss_embed"] = {
			'description' : "We understand that this may come as a disappointment, and we want to express our gratitude for your contributions during your time with us. Feel free to apply later if you're still interested.",
			'thumbnail' : 'https://cdn.discordapp.com/emojis/830548561329782815.gif?v=1',
		}
		data["vacation_embed"] = {
			'description' : f"We understand that you're taking a well-deserved break, and we wanted to acknowledge and support your decision. While you're away, your role as a Dank Memer grinder will be put on hold. We'll look forward to having you back on the team soon! In case of any queries, please feel free to reach out to us anytime.",
			'thumbnail' : 'https://cdn.discordapp.com/emojis/1109396272382759043.webp?size=128&quality=lossless',
		}
		await interaction.client.grinderSettings.upsert(data)

		embed = discord.Embed(
			color=3092790,
			title="Manage DM Embeds"
		)
		embed.add_field(
			name = "Appoint Embed",
			value = f"**Thumbnail:** [Link]({data['appoint_embed']['thumbnail']})\n**Description:** ```{data['appoint_embed']['description']}```\n",
			inline = False
		)
		embed.add_field(
			name = "Dismiss Embed",
			value = f"**Thumbnail:** [Link]({data['dismiss_embed']['thumbnail']})\n**Description:** ```{data['dismiss_embed']['description']}```\n",
			inline = False
		)
		embed.add_field(
			name = "Vacation Embed",
			value = f"**Thumbnail:** [Link]({data['vacation_embed']['thumbnail']})\n**Description:** ```{data['vacation_embed']['description']}```\n",
			inline = False
		)
		await interaction.response.edit_message(embed=embed)

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

class GrinderSummeris(discord.ui.View):
	def __init__(self, interaction: discord.Interaction, active_grinder: list, inactive_grinder: list):
		super().__init__(timeout=120)
		self.interaction = interaction
		self.active_grinder = active_grinder
		self.inactive_grinder = inactive_grinder
		self.message = None
	
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

	@discord.ui.button(label="Active Grinders", style=discord.ButtonStyle.gray, emoji="<:toggle_on:1123932825956134912>",row=1)
	async def active_grinder(self, interaction: discord.Interaction, button: discord.ui.Button):
		member_list = [
			interaction.guild.get_member(int(member['user'])) for member in self.active_grinder
		]

		if len(member_list) == 0:
			error = await get_warning_embed(content = f"No active grinders found!")
			return await interaction.response.send_message(embed=error, ephemeral=True)
		
		pages = []
		ping_group = list(chunk(member_list,10))
		member_count = 0
		for members in ping_group:
			desc = ''
			for member in members:
				if not isinstance(member, discord.Member): continue
				member_count += 1
				desc += f'` {member_count}. ` {member.mention} (`{member.id}`)\n'
			embed = discord.Embed(description=desc, color=0x2b2d31)
			embed.set_footer(text=f"{len(pages)+1}/{len(ping_group)}")
			pages.append(embed)
		
		custom_button = [discord.ui.Button(label="<<", style=discord.ButtonStyle.gray),discord.ui.Button(label="<", style=discord.ButtonStyle.gray),discord.ui.Button(label=">", style=discord.ButtonStyle.gray),discord.ui.Button(label=">>", style=discord.ButtonStyle.gray)]

		await Paginator(interaction, pages, custom_button).start(embeded=True, quick_navigation=False)

	@discord.ui.button(label="Inactive Grinders", style=discord.ButtonStyle.gray, emoji="<:toggle_off:1123932890993020928>",row=1)
	async def inactive_grinder(self, interaction: discord.Interaction, button: discord.ui.Button):
		member_list = [
			interaction.guild.get_member(int(member['user'])) for member in self.inactive_grinder
		]

		if len(member_list) == 0:
			error = await get_warning_embed(content = f"No inactive grinders found!")
			return await interaction.response.send_message(embed=error, ephemeral=True)
		
		pages = []
		ping_group = list(chunk(member_list,10))
		member_count = 0
		for members in ping_group:
			desc = ''
			for member in members:
				member_count += 1
				desc += f'` {member_count}. ` {member.mention} (`{member.id}`)\n'
			embed = discord.Embed(description=desc, color=0x2b2d31)
			embed.set_footer(text=f"{len(pages)+1}/{len(ping_group)}")
			pages.append(embed)

		custom_button = [discord.ui.Button(label="<<", style=discord.ButtonStyle.gray),discord.ui.Button(label="<", style=discord.ButtonStyle.gray),discord.ui.Button(label=">", style=discord.ButtonStyle.gray),discord.ui.Button(label=">>", style=discord.ButtonStyle.gray)]
		await Paginator(interaction, pages, custom_button).start(embeded=True, quick_navigation=False)

