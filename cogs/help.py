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
        if type(command) == app_commands.commands.Command:
            embed = discord.Embed(title=f"{interaction.client.user.name} help Menu", description="",color=interaction.client.color['default'])
            embed.description += f"```\nSyntax: /{command.name}"
            embed.add_field(name="Description", value=command.description, inline=False)
            useage = ""
            if len(command.parameters) > 0:
                for param in command.parameters:
                    if param.required:
                        embed.description += f" [{param.display_name}]"
                    else:
                        embed.description += f" <{param.display_name}>"
                    use = f"`{param.display_name}"
                    for i in range(25):
                        if len(use) < 20:
                            use += " "
                        else:
                            use += f":` {param.description}\n"
                            break
                    useage += use
            embed.description += "\n```"
            if len(useage) > 0:
                embed.add_field(name="Parameters", value=useage, inline=False)

            await interaction.response.send_message(embed=embed)
        elif type(command) == app_commands.commands.Group:

            embed = discord.Embed(title=f"{interaction.client.user.name} help Menu", description="",color=interaction.client.color['default'])
            embed.add_field(name="Description", value=command.description, inline=False)
            useage = ""
            for subcommand in command.commands:
                use = f"`/{command.name} {subcommand.name}"
                for i in range(20):
                    if len(use) < 20:
                        use += " "
                    else:
                        use += f":` {subcommand.description}\n"
                        break
                useage += use
            if len(useage) > 0:
                embed.add_field(name="Sub-commands", value=useage, inline=False)
            embed.set_footer(text=f"Use below to get more information about a sub-command")
            pages = [embed]
            for sub_command in command.commands:
                if type(sub_command) == app_commands.commands.Command:
                    embed = discord.Embed(title=f"{interaction.client.user.name} help Menu", description="",color=interaction.client.color['default'])
                    embed.description += f"```\nSyntax: /{command.name} {sub_command.name}"
                    embed.add_field(name="Description", value=sub_command.description, inline=False)
                    useage = ""
                    if len(sub_command.parameters) > 0:
                        for param in sub_command.parameters:
                            if param.required:
                                embed.description += f" [{param.display_name}]"
                            else:
                                embed.description += f" <{param.display_name}>"
                            use = f"`{param.display_name}"
                            for i in range(20):
                                if len(use) < 20:
                                    use += " "
                                else:
                                    use += f":` {param.description}\n"
                                    break
                            useage += use
                    embed.description += "\n```"
                    if len(useage) > 0:
                        embed.add_field(name="Parameters", value=useage, inline=False)
                    pages.append(embed)
                elif type(sub_command) == app_commands.commands.Group:
                    embed = discord.Embed(title=f"{interaction.client.user.name} help Menu", description="",color=interaction.client.color['default'])
                    embed.add_field(name="Description", value=sub_command.description, inline=False)
                    useage = ""
                    for subcommand in sub_command.commands:
                        use = f"`/{command.name} {sub_command.name} {subcommand.name}"
                        for i in range(20):
                            if len(use) < 20:
                                use += " "
                            else:
                                use += f":` {subcommand.description}\n"
                                break
                        useage += use
                    if len(useage) > 0:
                        embed.add_field(name="Sub-commands", value=useage, inline=False)
                    embed.set_footer(text=f"Use below to get more information about a sub-command")
                    pages.append(embed)
                    for sub_cmd_groub in sub_command.commands:
                        if type(sub_cmd_groub) == app_commands.commands.Command:
                            embed = discord.Embed(title=f"{interaction.client.user.name} help Menu", description="",color=interaction.client.color['default'])
                            embed.description += f"```\nSyntax: /{command.name} {sub_command.name} {sub_cmd_groub.name}"
                            embed.add_field(name="Description", value=sub_cmd_groub.description, inline=False)
                            useage = ""
                            if len(sub_cmd_groub.parameters) > 0:
                                for param in sub_cmd_groub.parameters:
                                    if param.required:
                                        embed.description += f" [{param.display_name}]"
                                    else:
                                        embed.description += f" <{param.display_name}>"
                                    use = f"`{param.display_name}"
                                    for i in range(25):
                                        if len(use) < 20:
                                            use += " "
                                        else:
                                            use += f":` {param.description}\n"
                                            break
                                    useage += use
                            embed.description += "\n```"
                            if len(useage) > 0:
                                embed.add_field(name="Parameters", value=useage, inline=False)
                            pages.append(embed)

            custom_button = [discord.ui.Button(label="<", style=discord.ButtonStyle.blurple),discord.ui.Button(label="◼", style=discord.ButtonStyle.red),discord.ui.Button(label=">", style=discord.ButtonStyle.blurple)]

            await Paginator(interaction, pages, custom_button).start(embeded=True, quick_navigation=False)

    
async def setup(bot):
    await bot.add_cog(Help(bot))
