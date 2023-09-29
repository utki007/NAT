import discord
import chat_exporter
import datetime
import io
from discord import Interaction, TextStyle, app_commands
from discord.interactions import Interaction
from discord.ui import View, Button, button, TextInput, Item
from discord.ui.item import Item
from utils.views.selects import User_Select, Channel_select
from utils.views.modal import General_Modal
from utils.views.confirm import Confirm
from typing import Any

class ButtonCooldown(app_commands.CommandOnCooldown):
    def __init__(self, retry_after: float):
        self.retry_after = retry_after

    def key(interaction: discord.Interaction):
        return interaction.user

class Voice_config(View):
    def __init__(self, member: discord.Member, data: dict, message: discord.Message=None):
        self.data = data
        self.member = member
        self.message = message
        super().__init__(timeout=None)
        if self.data['enabled'] is True:
            self.children[0].emoji = "<:toggle_on:1123932825956134912>"
            self.children[0].style = discord.ButtonStyle.gray
            self.children[0].label = "Module Enabled"
        else:
            self.children[0].emoji = "<:toggle_off:1123932890993020928>"
            self.children[0].style = discord.ButtonStyle.gray
            self.children[0].label = "Module Disabled"
    
    async def update_embed(self, interaction: discord.Interaction ,data: dict):
        embed = discord.Embed(
            color=3092790,
            title="Private Voice"
        )
        channel = interaction.guild.get_channel(data['join_create'])
        if channel is None:
            channel = f"`None`"
        else:
            channel = f"{channel.mention}"
        embed.add_field(name="Join to create:", value=f"{channel}", inline=False)
        return embed

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.member.id
    
    async def on_error(self, interaction: Interaction, error: Exception, item: Item[Any]):
        if isinstance(error, ButtonCooldown):
            seconds = int(error.retry_after)
            unit = 'second' if seconds == 1 else 'seconds'
            return await interaction.response.send_message(f"You're on cooldown for {seconds} {unit}!", ephemeral=True)
        else:
            raise error
    
    @button(label="Toggle", style=discord.ButtonStyle.gray, custom_id="vc:toggle", row=1)
    async def toggle(self, interaction: discord.Interaction, button: Button):
        if self.data['enabled'] is True:
            self.data['enabled'] = False
            button.emoji = "<:toggle_off:1123932890993020928>"
            button.style = discord.ButtonStyle.gray
        else:
            self.data['enabled'] = True
            self.children[0].emoji = "<:toggle_on:1123932825956134912>"
            self.children[0].style = discord.ButtonStyle.gray
            self.children[0].label = "Module Enabled"
        await interaction.client.vc_config.update(self.data)
        await interaction.response.edit_message(view=self)
        if self.data['enabled'] is True:
            interaction.client.vc_config_cache[self.data['_id']] = self.data
        else:
            del interaction.client.vc_config_cache[self.data['_id']]
    
    @button(label="Channel", style=discord.ButtonStyle.gray, emoji="<:tgk_channel:1073908465405268029>", custom_id="vc:channel", row=1)
    async def channel(self, interaction: discord.Interaction, button: Button):
        view = discord.ui.View()
        view.value = None
        view.select = Channel_select(placeholder="Select new to join to create voice channels", max_values=1, min_values=1, channel_types=[discord.ChannelType.voice])
        view.add_item(view.select)
        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()

        if view.value is None: return await interaction.delete_original_response()

        channel = view.select.values[0]
        if self.data['join_create'] == channel.id:
            self.data['join_create'] = None
            await view.select.interaction.response.edit_message(content=f"Removed the channel", embed=None, view=None)
        else:
            self.data['join_create'] = channel.id
            await view.select.interaction.response.edit_message(content=f"Updated the channel to {channel.mention}", embed=None, view=None)

        await interaction.client.vc_config.update(self.data)
        interaction.client.vc_config_cache[self.data['_id']] = self.data

        embed = await self.update_embed(interaction, self.data)
        
        await self.message.edit(embed=embed)
        

class Voice_UI(View):
    def __init__(self):
        self.cd = app_commands.Cooldown(2, 10)
        super().__init__(timeout=None)

    async def on_error(self, interaction: Interaction, error: Exception, item: Item[Any]):
        if isinstance(error, ButtonCooldown):
            seconds = int(error.retry_after)
            unit = 'second' if seconds == 1 else 'seconds'
            return await interaction.response.send_message(f"You're on cooldown for {seconds} {unit}!", ephemeral=True)
        else:
            raise error
    
    @button(label="Lock", style=discord.ButtonStyle.gray, emoji="<:tgk_lock:1072851190213259375>", row=0, custom_id="vc:lock")
    async def lock(self, interaction: discord.Interaction, button: Button):
        data = await interaction.client.vc_channel.find(interaction.channel.id)
        if not data:
            return await interaction.response.send_message("This voice channel is not registered", ephemeral=True, delete_after=5)
        if interaction.user.id != data['owner']:
            return await interaction.response.send_message("You are not the owner of this voice channel", ephemeral=True, delete_after=5)
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.update(connect=False)
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.response.send_message("Locked the voice channel", ephemeral=True, delete_after=5)
    
    @button(label="Unlock", style=discord.ButtonStyle.gray, emoji="<:tgk_unlock:1072851439161983028>", row=0, custom_id="vc:unlock")
    async def unlock(self, interaction: discord.Interaction, button: Button):
        data = await interaction.client.vc_channel.find(interaction.channel.id)
        if not data:
            return await interaction.response.send_message("This voice channel is not registered", ephemeral=True, delete_after=5)
        if interaction.user.id != data['owner']:
            return await interaction.response.send_message("You are not the owner of this voice channel", ephemeral=True, delete_after=5)
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.update(connect=True)
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.response.send_message("Unlocked the voice channel", ephemeral=True, delete_after=5)
    
    @button(label="Hide", style=discord.ButtonStyle.gray, emoji="<:Hide:1132021554188931102>", row=0, custom_id="vc:hide")
    async def hide(self, interaction: discord.Interaction, button: Button):
        data = await interaction.client.vc_channel.find(interaction.channel.id)
        if not data:
            return await interaction.response.send_message("This voice channel is not registered", ephemeral=True, delete_after=5)
        if interaction.user.id != data['owner']:
            return await interaction.response.send_message("You are not the owner of this voice channel", ephemeral=True, delete_after=5)
        
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.update(view_channel=False)
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.response.send_message("Hided the voice channel", ephemeral=True, delete_after=5)
    
    @button(label="Unhide", style=discord.ButtonStyle.gray, emoji="<:Unhide:1132021407543459941>", row=0, custom_id="vc:unhide")
    async def unhide(self, interaction: discord.Interaction, button: Button):
        data = await interaction.client.vc_channel.find(interaction.channel.id)
        if not data:
            return await interaction.response.send_message("This voice channel is not registered", ephemeral=True, delete_after=5)
        if interaction.user.id != data['owner']:
            return await interaction.response.send_message("You are not the owner of this voice channel", ephemeral=True, delete_after=5)
        
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.update(view_channel=True)
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.response.send_message("Unhided the voice channel", ephemeral=True, delete_after=5)
    
    @button(label="Add/Remove Friend", style=discord.ButtonStyle.gray, emoji="<:tgk_person_add:1132022878288744598>", row=1, custom_id="vc:add_friend")
    async def add_friend(self, interaction: discord.Interaction, button: Button):
        data = await interaction.client.vc_channel.find(interaction.channel.id)
        if not data:
            return await interaction.response.send_message("This voice channel is not registered", ephemeral=True, delete_after=5)
        if interaction.user.id != data['owner']:
            return await interaction.response.send_message("You are not the owner of this voice channel", ephemeral=True, delete_after=5)
        
        view = discord.ui.View()
        view.value = None
        view.select: discord.ui.UserSelect = User_Select(placeholder="Select friends you want to add/remove", max_values=10, min_values=1)
        view.add_item(view.select)
        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()
        if view.value is None: return await interaction.delete_original_response()
    
        added = ""
        removed = ""
        for user in view.select.values:
            if user.id in data['friends']:
                data['friends'].remove(user.id)
                removed += f"{user.mention} "
                await interaction.channel.set_permissions(user, overwrite=None)
                if user in interaction.channel.members:
                    await user.move_to(None)
            else:
                data['friends'].append(user.id)
                added += f"{user.mention} "
                overwrites = discord.PermissionOverwrite(connect=True, view_channel=True, speak=True, stream=True, use_voice_activation=True)
                await interaction.channel.set_permissions(user, overwrite=overwrites)
        await interaction.client.vc_channel.update(data)

        await view.select.interaction.response.edit_message(content=f"Added: {added}\nRemoved: {removed}", view=None)

    @button(label="Set Limit", style=discord.ButtonStyle.gray, emoji="<:tgk_limit:1132030665672626359>", row=1, custom_id="vc:set_limit")
    async def set_limit(self, interaction: discord.Interaction, button: Button):
        data = await interaction.client.vc_channel.find(interaction.channel.id)
        if not data:
            return await interaction.response.send_message("This voice channel is not registered", ephemeral=True, delete_after=5)
        if interaction.user.id != data['owner']:
            return await interaction.response.send_message("You are not the owner of this voice channel", ephemeral=True, delete_after=5)
        
        modal = General_Modal(title="Editing Limit", interaction=interaction)
        modal.value = None
        modal.limit = TextInput(label="New Limit",placeholder="Enter the limit of the voice channel", default=interaction.channel.user_limit)
        modal.add_item(modal.limit)
        await interaction.response.send_modal(modal)
        await modal.wait()

        if modal.value is None: return
        try:
            limit = int(modal.limit.value)
        except ValueError:
            return await modal.interaction.response.send_message("Please enter a valid number", ephemeral=True, delete_after=5)
        if limit >= 100:
            await interaction.channel.edit(user_limit=None)
            await modal.interaction.response.send_message("Removed the limit of the voice channel", ephemeral=True, delete_after=5)
        else:
            await interaction.channel.edit(user_limit=limit)
            await modal.interaction.response.send_message(f"Set the limit of the voice channel to {limit}", ephemeral=True, delete_after=5)
    
    @button(label="Set Bitrate", style=discord.ButtonStyle.gray, emoji="<:tgk_bitrate:1132034718603431976> ", row=1, custom_id="vc:set_bitrate")
    async def set_bitrate(self, interaction: discord.Interaction, button: Button):
        data = await interaction.client.vc_channel.find(interaction.channel.id)
        if not data:
            return await interaction.response.send_message("This voice channel is not registered", ephemeral=True, delete_after=5)
        if interaction.user.id != data['owner']:
            return await interaction.response.send_message("You are not the owner of this voice channel", ephemeral=True, delete_after=5)
        
        modal = General_Modal(title="Editing Bitrate", interaction=interaction)
        modal.value = None
        modal.bitrate = TextInput(label="New Bitrate",placeholder="Enter the bitrate of the voice channel", default=f"{int(round(interaction.channel.bitrate)/1000)}")
        modal.add_item(modal.bitrate)
        await interaction.response.send_modal(modal)
        await modal.wait()

        if modal.value is None: return
        try:
            bitrate = int(modal.bitrate.value)
        except ValueError:
            return await modal.interaction.response.send_message("Please enter a valid number", ephemeral=True, delete_after=5)
        bitrate *= 1000
        if bitrate < 8000 or bitrate > 96000:
            return await modal.interaction.response.send_message("Please enter a valid from 8 to 96", ephemeral=True, delete_after=5)
        await interaction.channel.edit(bitrate=bitrate)
        await modal.interaction.response.send_message(f"Set the bitrate of the voice channel to {int(bitrate/1000)} Kbps", ephemeral=True, delete_after=5)

    @button(label="Set Name", style=discord.ButtonStyle.gray, emoji="<:tgk_edit:1132037251757510666>", row=2, custom_id="vc:set_name")
    async def set_name(self, interaction: discord.Interaction, button: Button):
        data = await interaction.client.vc_channel.find(interaction.channel.id)
        if not data:
            return await interaction.response.send_message("This voice channel is not registered", ephemeral=True, delete_after=5)
        if interaction.user.id != data['owner']:
            return await interaction.response.send_message("You are not the owner of this voice channel", ephemeral=True, delete_after=5)
        
        modal = General_Modal(title="Editing Name", interaction=interaction)
        modal.value = None
        modal.name = TextInput(label="New Name",placeholder="Enter the name of the voice channel", default=interaction.channel.name)
        modal.add_item(modal.name)
        await interaction.response.send_modal(modal)

        await modal.wait()
        if modal.value is None: return
        await interaction.channel.edit(name=modal.name.value)
        await modal.interaction.response.send_message(f"Set the name of the voice channel to {modal.name.value}", ephemeral=True, delete_after=5)
    
    @button(label="Delete", style=discord.ButtonStyle.red, emoji="<:tgk_delete:1132040126478950400>", row=2, custom_id="vc:delete")
    async def delete(self, interaction: discord.Interaction, button: Button):
        data = await interaction.client.vc_channel.find(interaction.channel.id)
        if not data:
            return await interaction.response.send_message("This voice channel is not registered", ephemeral=True, delete_after=5)
        if interaction.user.id != data['owner']:
            return await interaction.response.send_message("You are not the owner of this voice channel", ephemeral=True, delete_after=5)
        
        view = Confirm(user=interaction.user,timeout=30)
        await interaction.response.send_message("Are you sure you want to delete this voice channel?", view=view)
        view.message = await interaction.original_response()
        await view.wait()
        if view.value is None: return await interaction.delete_original_response()
        await view.interaction.response.edit_message(content="Deleting the voice channel...", view=None)
        await interaction.client.vc_channel.delete(interaction.channel.id)
        await interaction.channel.delete()