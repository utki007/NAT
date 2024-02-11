import discord
from discord import Interaction, ui
from utils.views.selects import Channel_select, Role_select

class GrinderConfigPanel(ui.View):
    def __init__(self, config: dict, user: discord.Member, message: discord.Message):
        super().__init__(timeout=120)
        self.config = config
        self.user = user
        self.message = message
    
    async def on_timeout(self):
        for chl in self.children: chl.disabled = True
        try:
            await self.message.edit(view=self)
        except discord.HTTPException:
            pass
    
    async def interaction_check(self, interaction: Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("You are not allowed to interact with this view", ephemeral=True)
            return False
        return True
    
    async def on_error(self, interaction: Interaction, error: Exception):
        try:
            await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)
        except discord.HTTPException:
            await interaction.followup.send(f"An error occurred: {error}", ephemeral=True)
        
    @ui.button(label="Payment Channel", style=discord.ButtonStyle.gray, emoji="<:tgk_channel:1073908465405268029>")
    async def payout_channel(self, interaction: Interaction, button: ui.Button):
        view = discord.ui.View()
        view.channel_select = Channel_select(placeholder="Select your payment channel", min_values=1, max_values=1, channel_types=[discord.ChannelType.text])
        view.add_item(view.channel_select)
        await interaction.response.send_message(view=view, ephemeral=True)

        await view.wait()
        if view.value is None or view.value is False:
            return await interaction.delete_original_response()
        
        new_channel = view.channel_select.values[0]
        self.config["payment_channel"] = new_channel.id
        await interaction.client.grinder.update_config(interaction.guild.id, self.config)        
        await view.channel_select.interaction.response.edit_message(content="Payment Channel updated", view=None)
        await view.channel_select.interaction.delete_original_response()
        await self.message.edit(embed=await interaction.client.grinder.get_config_embed(interaction.guild, self.config), view=self)        

    @ui.button(label="Manager Roles", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908465405268029>")
    async def manager_roles(self, interaction: Interaction, button: ui.Button):
        view = discord.ui.View()
        view.role_select = Role_select(placeholder="Select your manager roles", min_values=1, max_values=5)
        view.add_item(view.role_select)
        await interaction.response.send_message(view=view, ephemeral=True)

        await view.wait()

        if view.value is None or view.value is False:
            return await interaction.delete_original_response()
        
        add_roles = ""
        remove_roles = ""

        for role in view.role_select.values:
            if role not in self.config["manager_roles"]:
                self.config["manager_roles"].append(role.id)
                add_roles += f"{role.mention} "
            else:
                self.config["manager_roles"].remove(role.id)
                remove_roles += f"{role.mention} "
        await interaction.client.grinder.update_config(interaction.guild.id, self.config)
        await view.role_select.interaction.response.edit_message(content=f"Added Roles: {add_roles}\nRemoved Roles: {remove_roles}", view=None)
        await view.role_select.interaction.delete_original_response()

        await self.message.edit(embed=await interaction.client.grinder.get_config_embed(interaction.guild, self.config), view=self)

            
