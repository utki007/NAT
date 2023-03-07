import discord
from utils.embeds import *

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
        