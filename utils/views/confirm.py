import discord
from discord.ext import commands

# Define a simple View that gives us a confirmation menu
class Confirm(discord.ui.View):
	def __init__(self):
		super().__init__(timeout=10)
		self.value = None

	async def on_timeout(self):		
		self.value = None

	@discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
	async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
		self.value = True
		self.stop()

	@discord.ui.button(label='Cancel', style=discord.ButtonStyle.grey)
	async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
		self.value = False
		self.stop()
