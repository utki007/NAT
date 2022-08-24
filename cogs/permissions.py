import discord
import aiohttp
from discord import app_commands
from discord.ext import commands
from typing import List, Union
from utils.db import Document
import motor.motor_asyncio

class Permissions(commands.GroupCog, name="permissions", description="Manage permissions for the bot commands"):
    def __init__(self, bot):
        self.bot = bot
        self.auth_db = Document(bot.db, "OAuth2")
        self.session = aiohttp.ClientSession()
    
    async def command_auto_complete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        commands = await interaction.client.tree.fetch_commands()
        return [
            app_commands.Choice(name=str(commnad.name), value=str(commnad.id))
            for commnad in commands if current.lower() in commnad.name.lower()
        ]
    
    async def get_command_permission(self, interaction: discord.Interaction, command_id:int):
        url = f"https://discord.com/api/v10/applications/{interaction.client.id}/guilds/{interaction.guild.id}/commands/{command_id}/permissions"
        headers = {"Authorization": f"Bot {interaction.client.botToken}", "Content-Type": "application/json"}
        async with self.session.get(url) as resp:
            resp = await resp.json()
            if resp["code"] == 10066:
                return "Invalid command id"
            else:
                return resp
    
    async def set_command_permission(self, interaction: discord.Interaction, command_id: int, permission: list, bearer: str):
        url = f"https://discord.com/api/v10/applications/{interaction.client.user.id}/guilds/{interaction.guild.id}/commands/{command_id}/permissions"
        headers = {"Authorization": f"Bearer {bearer}", "Content-Type": "application/json"}
        print(permission)
        data = {"permissions": permission}
        async with self.session.put(url, headers=headers, json=data) as resp:
            resp = await resp.json()
            return resp

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.__class__.__name__} Cog has been loaded\n-----")

    @app_commands.command(name="view", description="Edit permissions of a command")
    @app_commands.describe(command="command to edit permissions")
    @app_commands.autocomplete(command=command_auto_complete)
    async def _view(self, interaction: discord.Interaction, command: str):
        command = await interaction.client.tree.fetch_command(int(command))
        try:
            permission = await command.fetch_permissions(interaction.guild)
        except discord.NotFound:
            permission = "Permission are set to default"
        embed = discord.Embed(title=f"Edit permissions of {command.name}", description="")
        embed.description += f"Name: {command.name}\n"
        embed.description += f"Description: {command.description}\n"
        if type(permission) == str:
            embed.description += f"Permissions: {permission}\n"
        else:
            overwrite_user = ""
            overwrite_role = ""
            overwrite_channel = ""
            for perm in permission.permissions:
                if isinstance(perm.target, discord.Member):
                    overwrite_user += f"{perm.target.name}: {perm.permission}\n"
                elif isinstance(perm.target, discord.Role):
                    overwrite_role += f"{perm.target.name}: {perm.permission}\n"
                elif isinstance(perm.target, discord.TextChannel):
                    overwrite_channel += f"{perm.target.name}: {perm.permission}\n"
                elif isinstance(perm.target, discord.app_commands.models.AllChannels):
                    overwrite_channel = f"All channels: {perm.permission}\n"
                
            embed.add_field(name="Overwrite user", value=overwrite_user if overwrite_user else "None", inline=False)
            embed.add_field(name="Overwrite role", value=overwrite_role if overwrite_role else "None", inline=False)
            embed.add_field(name="Overwrite channel", value=overwrite_channel if overwrite_channel else "None", inline=False)

        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="set", description="Set permissions of a command")
    @app_commands.describe(command="command to set permissions", channel="select channel to set permission", role="select role to set permission", member="select user to set permission", _type="type of permission to set")
    @app_commands.autocomplete(command=command_auto_complete)
    async def _set(self, interaction: discord.Interaction, command: str, channel: discord.TextChannel=None, role: discord.Role=None, member:discord.Member=None, _type: bool=False):
        ouath_data = await self.auth_db.find(interaction.user.id)
        await interaction.response.defer(thinking=True)
        if not ouath_data:
            view = discord.View()
            view.add_item(discord.ui.Button(label=f'Authorize me', url="https://discord.com/api/oauth2/authorize?client_id=951019275844460565&permissions=0&redirect_uri=http%3A%2F%2Flocalhost%3A5000%2Fcallback&response_type=code&scope=guilds%20identify%20applications.commands.permissions.update"))
            await interaction.followup.send("your have not authorized bot's 0auth token", ephemeral=True, view=view)
            return
        command = await interaction.client.tree.fetch_command(int(command))
        try:
            command_permmission = await command.fetch_permissions(interaction.guild)
            command_permmission_dict = []
            for perm in command_permmission.permissions:
                data = {"id": str(perm.id)}
                if isinstance(perm.target, discord.Member):
                    data["type"] = 2
                if isinstance(perm.target, discord.Role):
                    data["type"] = 1
                if isinstance(perm.target, discord.TextChannel):
                    data["type"] = 3
                if isinstance(perm.target, discord.app_commands.models.AllChannels):
                    data['type'] = 3
                data['permission'] = perm.permission
                command_permmission_dict.append(data)
        except discord.NotFound:
            command_permmission_dict = []
        
        if channel:
            channel_inlist = False
            for perm in command_permmission_dict:
                if perm['id'] == str(channel.id):
                    perm['permission'] = _type
                    channel_inlist = True
                    break
            if channel_inlist == False:
                command_permmission_dict.append({"id": str(channel.id), "type": 3, "permission": _type})
        
        if role:
            role_inlist = False
            for perm in command_permmission_dict:
                if perm['id'] == str(role.id):
                    perm['permission'] = _type
                    role_inlist = True
                    break
            if role_inlist == False:
                command_permmission_dict.append({"id": str(role.id), "type": 1, "permission": _type})
        
        if member:
            member_inlist = False
            for perm in command_permmission_dict:
                if perm['id'] == str(member.id):
                    perm['permission'] = _type
                    member_inlist = True
                    break
            if member_inlist == False:
                command_permmission_dict.append({"id": str(member.id), "type": 2, "permission": _type})
        
        res = await self.set_command_permission(interaction, command.id, command_permmission_dict, ouath_data["access_token"])
        await interaction.followup.send(content=f"{res}")

async def setup(bot):
    await bot.add_cog(Permissions(bot))