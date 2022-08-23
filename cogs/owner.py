import discord
import contextlib
import io
from traceback import format_exception
import textwrap
from utils.paginator import Contex_Paginator
from discord import app_commands
from discord.ext import commands
from utils.functions import clean_code

class owner(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.__class__.__name__} Cog has been loaded\n-----")
    
    @app_commands.command(name="get-logs", description="Get the logs of bot")
    @app_commands.checks.has_permissions(administrator=True)
    async def get_logs(self, interaction: discord.Interaction):
        if interaction.user.id not in self.bot.owner_ids:
            await interaction.response.send_message("You do not have permission to use this command.")
            return
        await interaction.response.send_message(file=discord.File("./bot.log", filename="discord.log"))
    
    @commands.command(name="eval", description="Evaluate code")
    async def _eval(self, ctx, *,code):
        if ctx.author.id not in self.bot.owner_ids:
            raise commands.CheckFailure(ctx.message)

        code = clean_code(code)
        local_variables = {
            "discord": discord,
            "commands": commands,
            "bot": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message
        }

        stdout = io.StringIO()

        try:
            with contextlib.redirect_stdout(stdout):

                exec(
                    f"async def func():\n{textwrap.indent(code, '    ')}", local_variables,
                )
                obj = await local_variables["func"]()

                result = f"{stdout.getvalue()}\n-- {obj}\n"
                
        except Exception as e:
            result = "".join(format_exception(e,e,e.__traceback__))
        page = []
        for i in range(0, len(result), 2000):
            page.append(discord.Embed(description=f'```py\n{result[i:i + 2000]}\n```', color=self.bot.color['default']))

        await Contex_Paginator(ctx, page).start(embeded=True, quick_navigation=False)



        
async def setup(bot):
    await bot.add_cog(
        owner(bot),
        guilds = [discord.Object(999551299286732871)]
    )