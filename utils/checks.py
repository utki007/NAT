import discord
from discord import app_commands
from discord import Interaction

class App_commands_Checks():

    def is_owner():
        async def predicate(Interaction: Interaction) -> bool:
            if Interaction.user.id in Interaction.client.owner_ids:
                return True
            else:
                raise Unauthorized(Interaction)
        return app_commands.check(predicate)

    def is_bot_mod():
        async def predicate(Interaction: Interaction) -> bool:
            if Interaction.user.id in Interaction.client.bot_mod_ids:
                return True
            else:
                raise Unauthorized(Interaction)
        return app_commands.check(predicate)


#custom Errors for custom checks
            
class Unauthorized(app_commands.AppCommandError):
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        
