import datetime
import discord
from discord.ext import commands, tasks
from discord import app_commands, Interaction
from utils.db import Document
from utils.views.confirm import Confirm
from humanfriendly import format_timespan

class Vote(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.votes = Document(bot.db, 'Votes')
        self.check_preimum.start()
    
    def cog_unload(self):
        self.check_preimum.cancel()

    @tasks.loop(minutes=30)
    async def check_preimum(self):
        guild_data: dict = await self.bot.premium.get_all()
        now = datetime.datetime.now(pytz.utc)
        for data in guild_data:
            if data['duration'] == 'permeant':
                continue
            if now > data['duration']:
                await self.bot.premium.delete(data['_id'])

    @check_preimum.before_loop
    async def before_check_preimum(self):
        await self.bot.wait_until_ready()
    
    
        

    Votes = app_commands.Group(name="votes", description="Vote management commands")
    premium = app_commands.Group(name="premium", description="Premium management commands")

    @Votes.command(name="show", description="Show the current vote")
    async def show(self, interaction: Interaction):
        user_data: dict = await self.votes.find({'discordId': str(interaction.user.id)})
        if not user_data:
            await interaction.response.send_message("You have not voted yet!", ephemeral=True)
            return
        embed = discord.Embed(title="Vote", description=f"Your Total credits are: {user_data['votes']}")
        embed.set_footer(text="You can use credits to buy temporary premium for your server!")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @Votes.command(name="use", description="Use your vote credits")
    async def use(self, interaction: Interaction):
        user_data: dict = await self.votes.find({'discordId': str(interaction.user.id)})
        if not user_data:
            await interaction.response.send_message("You have not voted yet!", ephemeral=True)
            return
        
        if user_data['votes'] < 5:
            await interaction.response.send_message("You don't have enough credits!", ephemeral=True)
            return
        
        embed = discord.Embed(description=f"Do you want to use 5 credits to get 1 day of premium {interaction.guild.name}?", color=0x2b2d31)
        view = Confirm(interaction.user, timeout=30)

        await interaction.response.send_message(embed=embed, ephemeral=False, view=view)

        view.message = await interaction.original_response()

        await view.wait()

        if view.value is None or view.value == False:
            await interaction.edit_original_response(content="You have cancelled the process!", view=None)
        
        if view.value == True:
            for item in view.children:item.disabled = True
            await view.interaction.response.send_message("Applying premium...", ephemeral=True)
            guild_data = await self.bot.premium.find({'_id': interaction.guild.id})
            if not guild_data:
                guild_data = {
                    '_id': interaction.guild.id,
                    'premium': True,
                    'duration': datetime.datetime.now(pytz.utc) + datetime.timedelta(seconds=86400),
                    'premium_by': interaction.user.id,
                    'payout_limit': 40
                }
                await self.bot.premium.insert(guild_data)
            else:
                
                if guild_data['duration'] == 'permeant':
                    await view.interaction.edit_original_response(content="This guild is permanently premium!", view=None)
                    await interaction.edit_original_response(view=view)
                    return

                guild_data['premium'] = True
                guild_data['duration'] += datetime.timedelta(seconds=86400)
                guild_data['premium_by'] = interaction.user.id
                guild_data['payout_limit'] = 40
                await self.bot.premium.update(guild_data)
            
            user_data['votes'] -= 5
            await self.votes.update(user_data)
            preimin_duration = (guild_data['duration'] - datetime.datetime.now(pytz.utc)).total_seconds()
            await view.interaction.edit_original_response(content=f"{interaction.guild.name} is now premium for duration of {format_timespan(preimin_duration)}", view=None)

    @app_commands.command(name="vote", description="Vote for the bot")
    async def vote(self, interaction: Interaction):
        embed = discord.Embed(title="Vote", description="You can vote for the bot on the following sites:\n[discordbotlist](https://discordbotlist.com/bots/nat/upvote)")
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="discordbotlist", url="https://discordbotlist.com/bots/nat/upvote", style=discord.ButtonStyle.url))
        await interaction.response.send_message(embed=embed, ephemeral=False, view=view)

    @premium.command(name="show", description="Show the current premium status of the server")
    async def _premium_show(self, interaction: Interaction):
        guild_data = await self.bot.premium.find({'_id': interaction.guild.id})
        if not guild_data:
            await interaction.response.send_message("This guild is not premium! try using `/votes use` to get premium!", ephemeral=True)
            return
        embed = discord.Embed(title=f"Premium status of {interaction.guild.name}", description="", color=0x2b2d31)
        embed.description += f"Premium: {guild_data['premium']}\n"
        embed.description += f"Premium by: <@{guild_data['premium_by']}>\n"
        
        if guild_data['duration'] == 'permeant':
            embed.description += f"Duration: Permeant\n"
        else:
            embed.description += f"Duration: <t:{int(guild_data['duration'].timestamp())}:R>\n"
            
        await interaction.response.send_message(embed=embed, ephemeral=False)

async def setup(bot):
    await bot.add_cog(Vote(bot))