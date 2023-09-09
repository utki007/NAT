import discord
from discord import Interaction, TextStyle
from discord.ui import View, Modal


class General_Modal(Modal):
    def __init__(self, title: str, interaction: Interaction=None, **kwargs):
        super().__init__(timeout=120, title=title, **kwargs)
        self.interaction = interaction
        self.value = None

    async def on_submit(self, interaction: Interaction):
        self.value = True
        self.interaction = interaction
        self.stop()