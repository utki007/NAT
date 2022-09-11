import discord
from discord import ui, Interaction

class DonationEmbed(ui.Modal, title="Donation Embed"):
    def __init__(self, interaction: Interaction, data: dict, name:str):
        super().__init__(timeout=None, title=f"Donation Embed {name}")
        self.interaction = interaction
        self.data = data
        self.name = name
        self.add_item(ui.TextInput(label="Title", placeholder="Title of the donation embed", default=self.data['donations'][self.name]['embed'] if self.data['donations'][self.name]['embed'] else None, required=False))
        self.add_item(ui.TextInput(label="Description", placeholder="Description of the donation embed", default=self.data['donations'][self.name]['embed'] if self.data['donations'][self.name]['embed'] else None, required=False))
        self.add_item(ui.TextInput(label="Footer", placeholder="Footer of the donation embed", default=self.data['donations'][self.name]['embed'] if self.data['donations'][self.name]['embed'] else None), required=False)
        self.add_item(ui.TextInput(label="Color", placeholder="Color of the donation embed", default=self.data['donations'][self.name]['embed'] if self.data['donations'][self.name]['embed'] else None), required=False)
    
    async def interaction_check(self, interaction: Interaction):
        if interaction.user.id == self.interaction.user.id:
            return True
        else:
            await interaction.response.send_message("You are not the user who started this interaction", ephemeral=True)
            return False
    
    async def on_timeout(self):
        self.stop()
    
    async def on_submit(self, interaction: Interaction):
        for child in self.children:
            if child.label == "Title":
                self.data['donations'][self.name]['embed']['title'] = child.value
            elif child.label == "Description":
                self.data['donations'][self.name]['embed']['description'] = child.value
            elif child.label == "Footer":
                self.data['donations'][self.name]['embed']['footer'] = child.value
            elif child.label == "Color":
                self.data['donations'][self.name]['embed']['color'] = child.value
        await interaction.client.donation_config.update(self.data)
        embed = discord.Embed.from_dict(self.data['donation_embed'])        
        await interaction.response.send_message(embed=embed, ephemeral=True, content=f"This is how the embed will look like you can edit it by using the command again")