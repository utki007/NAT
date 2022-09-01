import discord
import datetime
from discord.ext import commands
from discord import app_commands, Interaction
from utils.db import Document

class AutoReact(commands.GroupCog, name='autoreact', description='Auto react to messages with emoji'):
    def __init__(self, bot):
        self.bot = bot
        self.bot.autoreact = Document(self.bot.db, "autoreact")
        self.autoreact_cache = {}
    
    @commands.Cog.listener()
    async def on_ready(self):
        all_autoreact = await self.bot.autoreact.get_all()
        for autoreact in all_autoreact:
            autoreact['last_reacted'] = None
            self.autoreact_cache[autoreact['_id']] = autoreact
        print(f'{self.__class__.__name__} is ready and cached {len(self.autoreact_cache)} users')
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.guild is None: return
        if not len(message.mentions) > 0: return
        for user in message.mentions:
            if user.id in self.autoreact_cache.keys():
                autoreact = self.autoreact_cache[user.id]
                if str(message.guild.id) in autoreact['guilds']:
                    if autoreact['last_reacted'] is None:
                        autoreact['last_reacted'] = datetime.datetime.now()
                        await message.add_reaction(autoreact['guilds'][str(message.guild.id)]['emoji'])
                    else:
                        #check if last reacted was 30s ago
                        if (datetime.datetime.now() - autoreact['last_reacted']).total_seconds() > 30:
                            autoreact['last_reacted'] = datetime.datetime.now()
                            await message.add_reaction(autoreact['guilds'][str(message.guild.id)]['emoji'])
                        else:
                            pass
    
    @app_commands.command(name="set", description="Set an autoreact for a user", extras={'example': '/autoreact set @user :emoji:'})
    @app_commands.describe(user='User to set autoreact for', emoji='Emoji to react with')
    @app_commands.default_permissions(manage_guild=True)
    async def set_autoreact(self, interaction: Interaction, user: discord.User, emoji: str):
        data = await self.bot.autoreact.find(user.id)
        if data:
            data['guilds'][str(interaction.guild.id)] = {'emoji': emoji}
            await self.bot.autoreact.update(data)
        else:
            data = {'_id': user.id, 'guilds': {str(interaction.guild.id): {'emoji': emoji}}}
            await self.bot.autoreact.insert(data)
        self.autoreact_cache[user.id] = data
        self.autoreact_cache[user.id]['last_reacted'] = None
        embed = discord.Embed(description=f"<:dynosuccess:1000349098240647188> | Successfully set {emoji} as autoreact for {user.mention}", color=self.bot.color['default'])
        embed.set_footer(text="if emoji is not showing, either it is invalid or bot does not have access to it")
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="remove", description="Remove an autoreact for a user", extras={'example': '/autoreact remove @user'})
    @app_commands.describe(user='User to remove autoreact for')
    @app_commands.default_permissions(manage_guild=True)
    async def remove_autoreact(self, interaction: Interaction, user: discord.User):
        data = await self.bot.autoreact.find(interaction.user.id)
        if data:
            if str(interaction.guild.id) in data['guilds']:
                del data['guilds'][str(interaction.guild.id)]
                await self.bot.autoreact.update(data)
                self.autoreact_cache[interaction.user.id] = data
                embed = discord.Embed(description=f"<:dynosuccess:1000349098240647188> | Successfully removed autoreact for {user.mention}", color=self.bot.color['default'])
                return await interaction.response.send_message(embed=embed)

        embed = discord.Embed(description=f"<:dynoerror:1000349098240647188> | {user.mention} does not have autoreact set", color=self.bot.color['default'])
        await interaction.response.send_message(embed=embed)
        if len(data['guilds']) == 0:
            await self.bot.autoreact.delete(user.id)
            del self.autoreact_cache[user.id]

async def setup(bot):
    await bot.add_cog(AutoReact(bot))