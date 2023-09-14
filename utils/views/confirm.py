import discord
from discord.ext import commands
from typing import Union
# Define a simple View that gives us a confirmation menu
class Confirm(discord.ui.View):
	def __init__(self, user: Union[discord.Member, discord.User],timeout: int = 30, message:discord.Message = None):
		super().__init__(timeout=timeout)
		self.value = None
		self.user = user
		self.message = message
		self.interaction: discord.Interaction = None

	async def on_timeout(self):		
		for button in self.children:
			button.disabled = True
		try:
			await self.message.edit(view=self)
		except:
			pass
		self.stop()
	
	async def interaction_check(self, interaction: discord.Interaction) -> bool:
		if interaction.user.id == self.user.id:
			return True
		else:
			await interaction.response.send_message("This is not your confirmation menu.", ephemeral=True)
			return False

	@discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
	async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
		self.interaction = interaction
		self.value = True
		self.stop()

	@discord.ui.button(label='Cancel', style=discord.ButtonStyle.grey)
	async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
		self.interaction = interaction
		self.value = False
		self.stop()

class Toggle(discord.ui.View):
	def __init__(self, user: discord.Member, value: bool,message: discord.Message = None,timeout: int = 30):
		super().__init__()
		self.value = None
		self.message = None
		if self.value is True:
			self.children[0].disabled = True
		elif self.value is False:
			self.children[1].disabled = False
	
	async def on_timeout(self):
		try:
			for button in self.children:
				button.disabled = True
			await self.message.edit(view=self)
		except:
			pass

	async def interaction_check(self, interaction: discord.Interaction) -> bool:
		if interaction.user.id == self.user.id:
			return True
		else:
			await interaction.response.send_message("This is not your confirmation menu.", ephemeral=True)
			return False
	
	async def update_embed(self):
		embed = discord.Embed(
				color=3092790,
				title="Nat Changelogs",
				description=f"Your current settings are: Dm Notifications: **{self.value}**"
			)
		return embed

	@discord.ui.button(label='Enable', style=discord.ButtonStyle.green)
	async def enable(self, button: discord.ui.Button, interaction: discord.Interaction):
		self.value = True
		await interaction.response.edit_message(view=self, embed=await self.update_embed())
	
	@discord.ui.button(label='Disable', style=discord.ButtonStyle.grey)
	async def disable(self, button: discord.ui.Button, interaction: discord.Interaction):
		self.value = False
		await interaction.response.edit_message(view=self, embed=await self.update_embed())