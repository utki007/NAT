import discord
import datetime
from discord.ext import commands, tasks
from utils.db import Document
from ui.settings.voiceView import Voice_UI

class Voice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.mongo["Voice"]
        self.config = Document(self.db, "config")
        self.channels = Document(self.db, "channels")
        self.bot.vc_config = self.config
        self.bot.vc_channel = self.channels
        self.bot.vc_config_cache = {}
        self.voice_expire.start()        
    
    def cog_unload(self):
        self.voice_expire.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        for config in await self.config.get_all():
            if config['enabled'] is False: continue
            self.bot.vc_config_cache[config['_id']] = config
        self.bot.add_view(Voice_UI())


    @tasks.loop(minutes=5)
    async def voice_expire(self):
        now = datetime.datetime.utcnow()
        for data in await self.channels.get_all():
            if data['last_activity'] is None: continue
            if now > data['last_activity'] + datetime.timedelta(minutes=5):
                channel = self.bot.get_channel(data['_id'])
                if channel is None: 
                    await self.channels.delete(data['_id'])
                    continue
                if len(channel.members) != 0: 
                    data['last_activity'] = None
                    await self.channels.update(data)
                    continue
                await channel.delete(reason="Voice channel expired")
                await self.channels.delete(data['_id'])
    
    @voice_expire.before_loop
    async def before_voice_expire(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if before.channel is not None and after.channel is None:
            data = await self.channels.find({"_id": before.channel.id})
            if not data: return
            if len(before.channel.members) == 0:
                data['last_activity'] = datetime.datetime.utcnow()
                await self.channels.update(data)

        if before.channel is None and after.channel is not None:
            channel: discord.VoiceChannel = after.channel
            
            dup = await self.channels.find({"owner": member.id})
            if dup: 
                channel = self.bot.get_channel(dup['_id'])
                if channel is None: 
                    await self.channels.delete(dup['_id'])
                    return                
                if len(channel.members) > 0:
                    dup['last_activity'] = None
                    await self.channels.update(dup)
                    await member.move_to(channel)
                if isinstance(channel, discord.VoiceChannel):
                    await member.move_to(channel)
                return
            try:
                if channel.id != self.bot.vc_config_cache[member.guild.id]['join_create']: return
            except KeyError: return
            if self.bot.vc_config_cache[member.guild.id]['enabled'] is False: return
            overrite = {
                member: discord.PermissionOverwrite(view_channel=True,connect=True, speak=True, stream=True, use_voice_activation=True, priority_speaker=True),
                member.guild.default_role: discord.PermissionOverwrite(connect=False, speak=False, stream=False, use_voice_activation=False, priority_speaker=False, use_application_commands=True),
                member.guild.me: discord.PermissionOverwrite(view_channel=True)
            }
            try:
                private_channel = await member.guild.create_voice_channel(name=f"{member.display_name}'s Voice", category=channel.category, overwrites=overrite, reason="Private Voice Channel")
            except discord.Forbidden:
                try:
                    return await member.send("I don't have permission to create a voice channel")
                except discord.Forbidden:
                    pass
            await member.move_to(private_channel)
            data = {
                "_id": private_channel.id,
                "owner": member.id,
                "guild_id": member.guild.id,
                "friends": [],
                "last_activity": None,
            }
            await private_channel.send(f"Welcome to your private voice channel {member.mention}", view=Voice_UI())
            await self.channels.insert(data)

async def setup(bot):
    await bot.add_cog(Voice(bot))