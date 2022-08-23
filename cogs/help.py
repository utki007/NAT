import discord
from discord import app_commands, Interaction
from discord.ext import commands
from typing import Union, List

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def command_auto_complete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        commands = await interaction.client.tree.fetch_commands()
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
        print(command)
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
    
async def setup(bot):
    await bot.add_cog(Help(bot))
