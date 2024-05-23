import discord
import datetime
import asyncio
import io
from discord import Interaction
from discord.ui import ChannelSelect, RoleSelect
from utils.views.confirm import Confirm
from utils.views.selects import Role_select
from utils.views.ui import *
from ui.settings.lockdown import *

async def update_embed(interaction: Interaction, data: dict):
    embed = discord.Embed(
        color=3092790,
        title="Configure AFK"
    )
    roles = data['roles']
    roles = [interaction.guild.get_role(role) for role in roles if interaction.guild.get_role(role) is not None]
    if len([role.id for role in roles]) != len(data['roles']):
        data['roles'] = [role.id for role in roles]
        await interaction.client.afk_config.upsert(data)
    if len(roles) == 0:
        roles = f"` - ` **Add roles when?**\n"
        embed.add_field(name="Roles with AFK access:", value=f"> {roles}", inline=False)
    else:
        roles = [f'1. {role.mention}' for role in roles]
        roles = "\n".join(roles)
        embed.add_field(name="Roles with AFK access:", value=f">>> {roles}", inline=False)
    return embed

class AFKView(discord.ui.View):
    def __init__(self, data: dict, member: discord.Member):
        super().__init__()
        self.member = member
        self.message = None 
        if data['enabled']:
            self.children[0].style = discord.ButtonStyle.green
            self.children[0].label = 'Module Enabled'
            self.children[0].emoji = "<:toggle_on:1123932825956134912>"
        else:
            self.children[0].style = discord.ButtonStyle.red
            self.children[0].label = 'Module Disabled'
            self.children[0].emoji = "<:toggle_off:1123932890993020928>"

    
    @discord.ui.button(label='toggle_button_label' ,row=1)
    async def toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = await interaction.client.afk_config.find(interaction.guild.id)
        if data['enabled']:
            data['enabled'] = False
            await interaction.client.mafiaConfig.upsert(data)
            await update_embed(interaction, data)
            button.style = discord.ButtonStyle.red
            button.label = 'Module Disabled'
            button.emoji = "<:toggle_off:1123932890993020928>"
            await interaction.response.edit_message(view=self)
        else:
            data['enabled'] = True
            await interaction.client.mafiaConfig.upsert(data)
            await update_embed(interaction, data)
            button.style = discord.ButtonStyle.green
            button.label = 'Module Enabled'
            button.emoji = "<:toggle_on:1123932825956134912>"
            await interaction.response.edit_message(view=self)
        
        await interaction.client.afk_config.upsert(data)
    
    @discord.ui.button(label="Allowed Roles", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>",row=1)
    async def manager_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = await interaction.client.afk_config.find(interaction.guild.id)
        view = discord.ui.View()
        view.value = None
        view.role_select = Role_select(placeholder="Which all roles can use afk?", min_values=1, max_values=5)
        view.add_item(view.role_select)
        await interaction.response.send_message(view=view, ephemeral=True)

        await view.wait()

        if view.value is None or view.value is False:
            return await interaction.delete_original_response()
        
        add_roles = ""
        remove_roles = ""

        for role in view.role_select.values:
            if role.id in data["roles"]:
                data["roles"].remove(role.id)
                remove_roles += f"{role.mention} "
            else:
                data["roles"].append(role.id)
                add_roles += f"{role.mention} "

        await interaction.client.afk_config.update(data)
        await view.role_select.interaction.response.edit_message(content=f"Added Roles: {add_roles}\nRemoved Roles: {remove_roles}", view=None)
        await view.role_select.interaction.delete_original_response()

        embed = await update_embed(interaction, data)
        await self.message.edit(embed=embed, view=self)

    
    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.member.id:
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

