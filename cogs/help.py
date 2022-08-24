import discord
from discord import app_commands, Interaction
from discord.ext import commands
from typing import Union, List
from utils.views.paginator import Paginator

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def command_auto_complete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        commands = interaction.client.tree.get_commands()
        return [
            app_commands.Choice(name=str(commnad.name), value=str(commnad.name))
            for commnad in commands if current.lower() in commnad.name.lower()
        ]
    
    @app_commands.command(name="help", description="Show an short help message about a command", extras={'example': '/help command: ping'})
    @app_commands.describe(command="command to show help message")
    @app_commands.autocomplete(command=command_auto_complete)
    async def _help(self, interaction: discord.Interaction, command: str):
        command = interaction.client.tree.get_command(command)
        embed = discord.Embed(title=f"Info of {command.name}", description=f"{command.description}", color=interaction.client.color['default'])
        useage = ""
        query = ""
        useage += f"/{command.name}"
        if type(command) == app_commands.commands.Command:
            if len(command.parameters) > 0:
                extra_flags = False
                for argument in command.parameters:
                    if argument.required:
                        useage += f" [{argument.display_name}]"
                        
                    else:
                        extra_flags = True

                    query += f"**{argument.display_name}:** `{argument.description}`\n<:nat_newline:1011695174281351179> Autocomplete? `{argument.autocomplete}`\n"
                if extra_flags == True:
                    useage += f" <Extra Flags>"
                embed.add_field(name="Usage:", value=f"`{useage}`")
                embed.add_field(name="Options:", value=f"{query}", inline=False)
                embed.set_footer(text=f"Note: arguments in [] are required, arguments in <> are optional")
            
            if command.extras != None:
                try:
                    embed.add_field(name="Example", value=f"`{command.extras['example']}`", inline=False)
                except KeyError:
                    pass
            await interaction.response.send_message(embed=embed)
        elif type(command) == app_commands.commands.Group:
            embed = discord.Embed(title=f"Info of {command.name}", description=f"{command.description}", color=interaction.client.color['default'])
            embed.description += f"\n\n**Available Commands:**\n"
            for subcommand in command.commands:
                embed.description += f"`/{command.name} {subcommand.name}`\n"
            embed.set_footer(text=f"Use buttons to know more about each command")
            pages = [embed]
            for sub_command in command.commands:
                sub_cmd_embed = discord.Embed(title=f"Info of {sub_command.name}", description=f"{sub_command.description}", color=interaction.client.color['default'])
                useage = ""
                query = ""
                useage += f"/{command.name} {sub_command.name}"
                if len(sub_command.parameters) > 0:
                    extra_flags = False
                    for argument in sub_command.parameters:
                        if argument.required:
                            useage += f" [{argument.display_name}]"
                            
                        else:
                            extra_flags = True

                        query += f"**{argument.display_name}:** `{argument.description}`\n<:nat_newline:1011695174281351179> Autocomplete? `{argument.autocomplete}`\n"
                    if extra_flags == True:
                        useage += f" <Extra Flags>"
                    sub_cmd_embed.add_field(name="Usage:", value=f"`{useage}`")
                    sub_cmd_embed.add_field(name="Options:", value=f"{query}", inline=False)
                    sub_cmd_embed.set_footer(text=f"Note: arguments in [] are required, arguments in <> are optional")
                pages.append(sub_cmd_embed)
            custom_button = [discord.ui.Button(label="Previous", style=discord.ButtonStyle.blurple),discord.ui.Button(label="Stop", style=discord.ButtonStyle.red),discord.ui.Button(label="Next", style=discord.ButtonStyle.blurple)]

            await Paginator(interaction, pages, custom_button).start(embeded=True, quick_navigation=False)

    
async def setup(bot):
    await bot.add_cog(Help(bot))
