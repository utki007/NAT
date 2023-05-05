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
		interaction = self.interaction
		self.stop()