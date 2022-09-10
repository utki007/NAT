import discord
from discord.ext import commands
from typing import Union
# Define a simple View that gives us a confirmation menu
class Confirm(discord.ui.View):
	def __init__(self, user: Union[discord.Member, discord.User],timeout: int = 30):
		super().__init__(timeout=timeout)
		self.value = None
		self.user = user

	async def on_timeout(self):		
		self.value = None
	
	async def interaction_check(self, interaction: discord.Interaction) -> bool:
		if interaction.user.id == self.user.id:
			return True
		else:
			await interaction.response.send_message("This is not your confirmation menu.", ephemeral=True)
			return False

	@discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
	async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
		self.value = True
		self.stop()

	@discord.ui.button(label='Cancel', style=discord.ButtonStyle.grey)
	async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
		self.value = False
		self.stop()