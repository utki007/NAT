import discord
from utils.embeds import *
from discord.ui import ChannelSelect, UserSelect

class Dropdown_Default(discord.ui.Select):
	def __init__(self, interaction: discord.Interaction=None, options: list=None, **kwargs):
		self.interaction = interaction
		self.value = None
		super().__init__(options=options, **kwargs)
	
	async def callback(self, interaction: discord.Interaction):
		# use view.values[0] to access dropdown value
		self.interaction = interaction
		self.view.value = True
		self.view.stop()

class Dropdown_Channel(discord.ui.View):
	def __init__(self, interaction: discord.Interaction):
		super().__init__(timeout=30)
		self.interaction = interaction
		self.value = None

	@discord.ui.select(cls=ChannelSelect, channel_types=[discord.ChannelType.text], placeholder='Select channel...', min_values=1, max_values=1)
	async def select_channels(self, interaction: discord.Interaction, select: ChannelSelect):
		self.value = select.values[0]
		self.interaction = interaction
		self.stop()

class Reload(discord.ui.View):
	def __init__(self, cog: str,message: discord.Message=None):
		self.message = message
		self.cog = cog
		super().__init__(timeout=540)

	async def interaction_check(self, interaction: discord.Interaction) -> bool:
		if interaction.user.id in [488614633670967307, 301657045248114690]:
			return True
		else:
			await interaction.response.send_message("Imagin use this button when you can't even reload me.", ephemeral=True)
			return False
	
	async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
		await interaction.edit_original_response(content=f"An error occured: {error}")
		return

	async def on_timeout(self):
		for button in self.children:
			button.disabled = True
		await self.message.edit(view=self)
		self.stop()

	@discord.ui.button(emoji="<:reload:1127218199969144893>", style=discord.ButtonStyle.gray, custom_id="DEV:RELOAD")
	async def reload(self, interaction: discord.Interaction, button: discord.ui.Button):
		await interaction.response.send_message("Reloading...", ephemeral=True)
		try:
			await interaction.client.reload_extension(self.cog)
		except Exception as e:
			await interaction.edit_original_response(content=f"An error occured: {e}")
			return
		await interaction.edit_original_response(content="Reloaded!", view=None)