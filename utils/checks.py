import discord
from discord import app_commands
from discord import Interaction

class App_commands_Checks():

    def is_owner():
        async def predicate(Interaction: Interaction) -> bool:
            if Interaction.user.id in Interaction.client.owner_ids:
                return True
            else:
                return False
        return app_commands.check(predicate)
    
    def is_server_owner():
        async def predicate(Interaction: Interaction) -> bool:
            if Interaction.user.id == Interaction.guild.owner.id or Interaction.user.id in Interaction.client.owner_ids:
                return True
            else:
                return False
        return app_commands.check(predicate)
        
