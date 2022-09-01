import discord
import datetime
from discord import app_commands, Interaction
from discord.ext import commands
from utils.db import Document

class Afk(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.afk = Document(self.bot.db, "afk")
        self.afk_cache = {}
    
    @commands.Cog.listener()
    async def on_ready(self):
        all_afk = await self.bot.afk.get_all()
        for afk in all_afk:
            self.afk_cache[afk['_id']] = afk
        print(f'{self.__class__.__name__} is ready and cached {len(self.afk_cache)} users')

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.guild is None: return
        if message.author.id in self.afk_cache.keys():
            afk = self.afk_cache[message.author.id]
            if str(message.guild.id) in afk['guilds']:
                del afk['guilds'][str(message.guild.id)]
                await self.bot.afk.update(afk)
                await message.reply(f"Welcome back {message.author.mention}! I have removed your afk status")
                if len(afk['guilds']) == 0:
                    del self.afk_cache[message.author.id]
                    await self.bot.afk.delete(afk['_id'])

        if len(message.mentions) > 0: #this will check for reply also
            for user in message.mentions:
                if user.id in self.afk_cache.keys():
                    afk = self.afk_cache[user.id]
                    if str(message.guild.id) in afk['guilds']:
                        await message.reply(f"{user.mention} is afk: {afk['guilds'][str(message.guild.id)]['reason']}", delete_after=10, allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False))
        
    @app_commands.command(name="afk", description="Set your afk status", extras={'example': '/afk I am afk'})
    @app_commands.describe(reason='Reason for being afk')
    @app_commands.checks.cooldown(1, 60, key=lambda i: (i.guild_id, i.user.id))
    async def afk(self, interaction: Interaction, reason:str=None):
        data = await self.bot.afk.find(interaction.user.id)
        if data:
            data['guilds'][str(interaction.guild_id)] = {'reason': reason, 'started':  round(datetime.datetime.now().timestamp())}
            await self.bot.afk.update(interaction.user.id, data)
        else:
            data = {'_id': interaction.user.id, 'guilds': {str(interaction.guild_id): {'reason': reason, 'started':  round(datetime.datetime.now().timestamp())}}}
            await self.bot.afk.insert(data)
        
        await interaction.response.send_message(f"Set your afk status to `{reason}`", ephemeral=True)
        self.afk_cache[interaction.user.id] = data

async def setup(bot):
    await bot.add_cog(Afk(bot))