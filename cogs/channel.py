import time as t
from itertools import islice
from typing import List, Union

import discord
from discord import Interaction, app_commands
from discord.ext import commands

from ui.settings.lockdown import *
from utils.checks import App_commands_Checks
from utils.convertor import *
from utils.views.paginator import Paginator


def chunk(it, size):
    it = iter(it)
    return iter(lambda: tuple(islice(it, size)), ())

@app_commands.guild_only()
class channel(commands.GroupCog, name="channel", description="Helps you manage channels #️⃣"):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.__class__.__name__} Cog has been loaded\n-----")
    
    @app_commands.command(name="slowmode", description="Set cooldown for chat ⏰")
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.describe(time="Enter time. Ex: '1h5m4s'")
    async def slowmode(self, interaction: discord.Interaction, time: str="0s"):
        await interaction.response.defer(ephemeral = False)
        
        channel = interaction.channel

        try:
            time = await convert_to_time(time)
            cd = int(await calculate(time))
        except:
            warning = discord.Embed(
                color=0xDA2A2A,
                description=f"<a:nat_cross:1010969491347357717> **|** Incorrect time format, please use `h|m|s`")
            return await interaction.edit_original_response(embed=warning)
    
        desc = f''
        timer = datetime.datetime.strptime(str(datetime.timedelta(seconds=cd)), '%H:%M:%S')
        if timer.hour>0:
            if timer.hour == 1:
                desc = desc + f'{timer.hour} hour '
            else:
                desc = desc + f'{timer.hour} hours '
        if timer.minute>0:
            if timer.minute == 1:
                desc = desc + f'{timer.minute} minute '
            else:
                desc = desc + f'{timer.minute} minutes '
        if timer.second>0:
            if timer.second == 1:
                desc = desc + f'{timer.second} second '
            else:
                    desc = desc + f'{timer.second} seconds '

        if channel.slowmode_delay == cd:
            if cd == 0:
                embed = await get_warning_embed(content = f"Slowmode for {channel.mention} is already removed.")
            else:
                embed = await get_warning_embed(content = f"Slowmode for {channel.mention} is already set to {desc}.")
            return await interaction.edit_original_response(embed=embed)
        
        if cd > 21600:
            warning = discord.Embed(
                color=0xDA2A2A,
                description=f"<a:nat_cross:1010969491347357717> **|** Slowmode interval can't be greater than 6 hours.")
            return await interaction.edit_original_response(embed=warning)
        elif cd == 0:
            await channel.edit(slowmode_delay=cd, reason = f'Slowmode removed by {interaction.user} (ID: {interaction.user.id})')
            embed = await get_success_embed(content = f"Removed slowmode for {channel.mention}.")
            await interaction.edit_original_response(embed=embed)
        else:
            cd = int(cd)
            await channel.edit(slowmode_delay=cd, reason = f'Slowmode has been set to {desc} by {interaction.user} (ID: {interaction.user.id})')
            embed = await get_success_embed(content = f"Slowmode for {channel.mention} has been set to {desc}.")
            await interaction.edit_original_response(embed=embed)

    @app_commands.command(name="lock", description="Lock channel 🙊", extras={'example': '/lock'})
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.describe(role = "Provide role", user = "Input user 👤")
    async def lock(self, interaction:  discord.Interaction, role: discord.Role = None, user: discord.User = None):
        
        if interaction.user.id == 685705841264820247:
            await interaction.response.defer(ephemeral = True)
        else:
            await interaction.response.defer(ephemeral = False)

        unlockFor = ""
        channel = interaction.channel

        if interaction.channel.type == discord.ChannelType.text:
            if role == None:
                if user == None:
                    role = interaction.guild.default_role
                    unlockFor = "role"
                else:
                    unlockFor = "user"
            else:
                unlockFor = "role"

            if unlockFor == "role":
                role_mention = role.mention if role != interaction.guild.default_role else role
                overwrite = channel.overwrites_for(role)
                if overwrite.send_messages == False:
                    embed = await get_warning_embed(content = f"{channel.mention} is already locked for {role_mention}.")
                else:
                    overwrite.send_messages = False
                    await channel.set_permissions(role, overwrite=overwrite, reason = f'Channel lockdown sanctioned by {interaction.user} (ID: {interaction.user.id}) for {role}')
                    embed = await get_success_embed(content = f"Locked {channel.mention} for {role_mention}.")
            elif unlockFor == "user":
                overwrite = channel.overwrites_for(user)
                if overwrite.send_messages == False:
                    embed = await get_warning_embed(content = f"{channel.mention} is already locked for {user.mention}.")
                else:		
                    overwrite.send_messages = False

                    await channel.set_permissions(user, overwrite=overwrite, reason = f'Channel lockdown sanctioned by {interaction.user} (ID: {interaction.user.id}) for {user} ({user.id})')
                    embed = await get_success_embed(content = f"Locked {channel.mention} for {user.mention}.")
            else:
                embed = await get_warning_embed(content = f"Ran into some problem ...")

            await interaction.edit_original_response(embed=embed)
            if interaction.user.id == 685705841264820247:
                await interaction.channel.send(embed=embed)

        else:
            embed = discord.Embed(
                color=0x43b581, description=f'<a:nat_check:1010969401379536958> **|** Locked **{channel.mention}** for {interaction.guild.default_role}')
            if interaction.user.id == 685705841264820247:
                await interaction.channel.send(embed=embed)
            else:
                await interaction.edit_original_response(
                    embed=embed
                )
                if interaction.user.id == 685705841264820247:
                    await interaction.channel.send(embed=embed)
            await channel.edit(archived=True, locked=True)

    @app_commands.command(name="unlock", description="Unlock channel 🗣️", extras={'example': '/unlock'})
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.describe(role = "Provide role", user = "Input user 👤", state = "False for deafult perm, True for override perms")
    async def unlock(self, interaction:  discord.Interaction, state: bool = False, role: discord.Role = None, user: discord.User = None):
        
        if interaction.user.id == 685705841264820247:
            await interaction.response.defer(ephemeral = True)
        else:
            await interaction.response.defer(ephemeral = False)

        unlockFor = ""
        channel = interaction.channel    
        if role == None:
            if user == None:
                role = interaction.guild.default_role
                unlockFor = "role"
            else:
                unlockFor = "user"
        else:
            unlockFor = "role"

        if interaction.channel.type == discord.ChannelType.text:
            if unlockFor == "role":
                overwrite = channel.overwrites_for(role)
                
                msg = ''
                reason = f'Channel lockdown removed by {interaction.user} (ID: {interaction.user.id}) for {role}'

                if state == True:
                    overwrite.send_messages = True
                    reason += ' with state True'
                elif state == False:
                    overwrite.send_messages = None

                
                if role == interaction.guild.default_role :
                    if state:
                        msg = f'Unlocked **{channel.mention}** for {role} with state `True`'
                    else:
                        msg = f'Unlocked **{channel.mention}** for {role}'
                else:
                    if state:
                        msg = f'Unlocked **{channel.mention}** for {role.mention} with state `True`'
                    else:
                        msg = f'Unlocked **{channel.mention}** for {role.mention}'
            
                await channel.set_permissions(role, overwrite=overwrite, reason = reason)

                embed = await get_success_embed(content = msg)

            elif unlockFor == "user":
                overwrite = channel.overwrites_for(user)
                
                msg = ''
                reason = f'Channel lockdown removed by {interaction.user} (ID: {interaction.user.id}) for {user} (ID: {user.id})'
                if state == True:
                    overwrite.send_messages = True
                    reason += ' with state True'
                elif state == False:
                    overwrite.send_messages = None

                
                if state:
                    msg = f'Unlocked **{channel}** for {user.mention} with state `True`'
                else:
                    msg = f'Unlocked **{channel}** for {user.mention}'
            
                await channel.set_permissions(user, overwrite=overwrite, reason=reason)

                embed = await get_success_embed(content = msg)
            else:
                embed = await get_error_embed(content = f"Ran into some problem ...")
            
            await interaction.edit_original_response(embed=embed)
            if interaction.user.id == 685705841264820247:
                await interaction.channel.send(embed=embed)
            
        else:
            warning = await get_warning_embed(content = f"It's already unlocked dum dum")
            await interaction.edit_original_response(embed=warning, ephemeral=True)
            if interaction.user.id == 685705841264820247:
                await interaction.channel.send(embed=warning)

    @app_commands.command(name="viewlock", description="viewloock channel 🙈", extras={'example': '/viewlock'})
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(role = "Provide role")
    async def viewlock(self, interaction:  discord.Interaction, role: discord.Role = None):
        
        channel = interaction.channel
        role = role or interaction.guild.default_role
        role_mention = role.mention if role != interaction.guild.default_role else role

        if interaction.channel.type == discord.ChannelType.text:

            overwrite = channel.overwrites_for(role)
            if overwrite.view_channel == False:
                embed = await get_error_embed(content = f"{role_mention} is already viewlocked")
            else:
                overwrite.view_channel = False

                await channel.set_permissions(role, overwrite=overwrite, reason = f'Channel viewlock sanctioned by {interaction.user} (ID: {interaction.user.id}) for {role}')
                embed = await get_success_embed(content = f"Viewlocked **{channel.mention}** for {role_mention}.")
            
            await interaction.response.send_message(embed=embed, ephemeral=False)

        else:
            warning = await get_error_embed(content = f"It cant be view-locked dum dum")
            return await interaction.response.send_message(embed=warning, ephemeral=True)

    @app_commands.command(name="unviewlock", description="Unviewlock channel 🗣️", extras={'example': '/unviewlock'})
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(role = "Provide role", state = "Input state.")
    async def unviewlock(self, interaction:  discord.Interaction, state: bool = False, role: discord.Role = None):
        
        channel = interaction.channel        
        if role == None:
            role = interaction.guild.default_role

        if interaction.channel.type == discord.ChannelType.text:
            overwrite = channel.overwrites_for(role)
            
            reason = f'Channel viewlock removed by {interaction.user} (ID: {interaction.user.id}) for {role}'
            if state == True:
                overwrite.view_channel = True
                reason += ' with state True'
            elif state == False:
                overwrite.view_channel = None

            msg = ''
            
            if role == interaction.guild.default_role :
                if state:
                    msg = f'Unviewlocked **{channel.mention}** for {role} with state `True`'
                else:
                    msg = f'Unviewlocked **{channel.mention}** for {role}'
            else:
                if state:
                    msg = f'Unviewlocked **{channel.mention}** for {role.mention} with state `True`'
                else:
                    msg = f'Unviewlocked **{channel.mention}** for {role.mention}'
        
            await channel.set_permissions(role, overwrite=overwrite)

            embed = await get_success_embed(content = msg)
            await interaction.response.send_message(embed=embed, ephemeral=False)
        
        else:
            warning = await get_error_embed(content = f"It's already unviewlocked dum dum")
            return await interaction.response.send_message(embed=warning, ephemeral=True)

    @app_commands.command(name="sync", description="sync channel 🔄️", extras={'example': '/sync'})
    @app_commands.checks.has_permissions(administrator=True)
    async def sync(self, interaction:  discord.Interaction):

        if interaction.user.id == 685705841264820247:
            await interaction.response.defer(ephemeral=True)
        else:
            await interaction.response.defer(ephemeral=False)

        
        channel = interaction.channel

        if interaction.channel.type == discord.ChannelType.text:
            
            embed = await get_success_embed(content = f"Synced **{channel.mention}** with channel category.")
            
            await interaction.channel.edit(sync_permissions=True, reason=f"Channel synced by {interaction.user} (ID: {interaction.user.id})")

            await interaction.edit_original_response(embed=embed)
            if interaction.user.id == 685705841264820247:
                await interaction.channel.send(embed=embed)

        else:
            error = await get_error_embed(content = f"It cant be synced dum dum")
            await interaction.edit_original_response(embed=error)
            if interaction.user.id == 685705841264820247:
                await interaction.channel.send(embed=error)

    @app_commands.command(name="dump", description="Dump members in a channel or a role 📜", extras={'example': '/dump'})
    async def dump(self, interaction:  discord.Interaction, channel: discord.TextChannel = None, role: discord.Role = None):
        
        type = None
        footer = None
        if channel != None and role != None:
            members = list(set(channel.members).intersection(set(role.members)))
            color = role.color
            title = f"{len(members)} out of {len(role.members)} targetted members have access to {channel.mention}.\n\n"
            footer = f"Channel ID: {channel.id} | Role ID: {role.id}"
        elif channel != None:
            members = channel.members
            color = discord.Color.default()
            title = f"**{len(members)} members** have access to {channel.mention}.\n\n"
            footer = f"Channel ID: {channel.id}"
        elif role != None:
            members = role.members
            color = role.color
            title = f"**{len(members)} members** have {role.mention} role.\n\n"
            footer = f"Role ID: {role.id}"
        else:
            guild = interaction.guild
            members = guild.members
            color = discord.Color.default()
            title = f"The server **{guild.name}** has a total of **{len(members)} members**.\n\n"
                
        member_list = members

        if len(member_list) == 0:
            error = await get_warning_embed(content = f"No members to dump.")
            return await interaction.response.send_message(embed=error, ephemeral=True)
        
        pages = []
        ping_group = list(chunk(member_list,10))
        member_count = 0
        for members in ping_group:
            desc = ''
            for member in members:
                member_count += 1
                desc += f'` {member_count}. ` {member.mention} (`{member.id}`)\n'
            desc = f"{title}{desc}"
            embed = discord.Embed(description=desc, color=color)
            embed.set_footer(text=footer)
            pages.append(embed)
        
        custom_button = [discord.ui.Button(label="<<", style=discord.ButtonStyle.gray),discord.ui.Button(label="<", style=discord.ButtonStyle.gray),discord.ui.Button(label=">", style=discord.ButtonStyle.gray),discord.ui.Button(label=">>", style=discord.ButtonStyle.gray)]

        await Paginator(interaction, pages, custom_button).start(embeded=True, quick_navigation=False)

    # edit channel name, postion and category
    # @app_commands.command(name="edit", description="Edit channel name, position and category 📝", extras={'example': '/edit'})
    # # @app_commands.checks.has_permissions(administrator=True)
    # @App_commands_Checks.is_owner()
    # @app_commands.describe(channel = 'Enter channel which you wish to edit' ,name = "Enter new name", position = "Enter position", category = "Enter category")
    # @app_commands.checks.cooldown(2, 605, key=lambda i: (i.guild_id))
    # async def edit(self, interaction:  discord.Interaction, channel: discord.TextChannel = None, position: int = None, category: discord.CategoryChannel = None ,  name: str = None,):

    # 	channel = channel or interaction.channel
    # 	name = name or channel.name
    # 	category = category or channel.category

    # 	try:
    # 		if position is None:
    # 			position = category.channels[-1].position + 1
    # 		else:
    # 			position = category.channels[0].position + position
    # 	except:
    # 		position = position or channel.position

    # 	if interaction.channel.type == discord.ChannelType.text:
    # 		embed = await get_invisible_embed(f'- **Channel:** {channel.mention}\n- **Name:** {name}\n- **Position:** {position}\n- **Category:** {category}')
    # 		embed.title = "Edit Channel"
    # 		embed.set_footer(text="Are you sure you want to edit this channel?")
    # 		confirmation_view = Confirm(interaction.user)
    # 		await interaction.response.send_message(embed = embed, view=confirmation_view, ephemeral=False)
    # 		await confirmation_view.wait()
    # 		if confirmation_view.value:
    # 			await channel.edit(name=name, position=position, category=category, reason=f"Channel edited by {interaction.user} (ID: {interaction.user.id})")
    # 			embed = await get_success_embed(content = f"Successfully edited **{channel.mention}**")
    # 			await interaction.edit_original_response(embed=embed, view=None)
    # 		else:
    # 			error = await get_error_embed(content = f"Okay I wont edit {channel.mention}")
    # 			await interaction.edit_original_response(embed=error, view=None)
    # 	else:
    # 		error = await get_error_embed(content = f"It cant be edited dum dum")
    # 		await interaction.response.send_message(embed=error, ephemeral=True)


async def setup(bot):
    await bot.add_cog(channel(bot))