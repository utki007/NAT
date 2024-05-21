from itertools import islice
import os
import discord
import datetime

from typing import List, TypedDict, Dict
from amari import AmariClient, User

from utils.db import Document
from utils.embeds import get_formated_embed, get_formated_field

def chunk(it, size):
	it = iter(it)
	return iter(lambda: tuple(islice(it, size)), ())

class Embed(TypedDict):
    title: str
    description: str
    color: int

class Messages(TypedDict):
    host: Embed
    gaw: Embed
    end: Embed
    dm: Embed

class GiveawayConfig(TypedDict):
    _id: int
    enabled: bool
    manager_roles: list[int]
    log_channel: int | None
    multipliers: dict[int, int]
    blacklist: list[int]
    messages: Messages
    global_bypass: list[int]

class GiveawayData(TypedDict):
    _id: int
    channel: int
    guild: int
    winners: int
    prize: str
    item: str
    duration: int
    req_roles: list[int]
    bypass_role: list[int]
    req_level: int
    req_weekly: int
    entries: dict[int, int]
    banned: list[int]
    start_time: datetime.datetime
    end_time: datetime.datetime
    ended: bool
    host: int
    donor: int
    message: str
    channel_messages: dict[int, int]
    dank: bool
    delete_at: datetime.datetime

class Giveaways_Backend:
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.mongo["Giveaways"]
        self.config = Document(self.db, "config")
        self.giveaways = Document(self.db, "giveaways")
        self.config_cache: Dict[int, GiveawayConfig] = {}
        self.amariNat = AmariClient(os.environ.get("AMARI_NAT"))
        self.amariOCTANE = AmariClient(os.environ.get("AMARI_OCTANE"))            
        self.giveaways_cache = {}

    async def get_config(self, guild: discord.Guild | int):
        guild_id = guild.id if isinstance(guild, discord.Guild) else guild
        if guild_id in self.config_cache.keys():
            return self.config_cache[guild_id]
        config = await self.config.find(guild_id)
        if config is None:
            config = await self.create_config(self.bot.get_guild(guild_id))
            self.config_cache[guild_id] = config
        return config
    
    async def create_config(self, guild: discord.Guild | int) -> GiveawayConfig:
        data: GiveawayConfig = {
            "_id":  guild.id if isinstance(guild, discord.Guild) else guild,
            "enabled": True,
            "manager_roles": [],
            "log_channel": None,
            "multipliers": {},
            "blacklist": [],
            "global_bypass": [],
            "messages":{
                "host": {
                    "title": "Your giveaway has ended!",
                    "description": "**Ended At**{timestamp}\nWinners:\n{winners}",
                    "color": 2829617
                },
                "gaw": {
                    "title": "{prize}",
                    "description": "**Ends At:** {timestamp}\n**Donated By:** {donor}\n",
                    "color": 2829617
                },
                "dm": {
                    "title": "You won Giveaway!",
                    "description": "**Congratulations!** You won {prize} in {guild}.",
                    "color": 2829617
                },
                "end": {
                    "title": "Congratulations!",
                    "description": "<a:tgk_blackCrown:1097514279973961770> **Won:** {prize}",
                    "color": 2829617
                }
            
            }
        }
        await self.config.insert(dict(data))
        self.config_cache[guild.id] = data
        return data
    
    async def update_config(self, guild: discord.Guild, data: GiveawayConfig):
        await self.config.update(data)
        self.config_cache[guild.id] = data
    
    async def get_giveaway(self, message: discord.Message) -> GiveawayData | None:
        if message.id in self.giveaways_cache.keys():
            return self.giveaways_cache[message.id]
        giveaway = await self.giveaways.find(message.id)
        if giveaway is None: 
            return None
        return giveaway

    async def update_giveaway(self, message: discord.Message | int, data: dict):
        await self.giveaways.update(data)
        if isinstance(message, discord.Message):
            self.giveaways_cache[message.id] = data
        else:
            self.giveaways_cache[message] = data
    
    async def get_message_giveaways(self, message: discord.Message) -> List[GiveawayData]:
        giveaways = await self.giveaways.find_many_by_custom({'channel_messages.channel': message.channel.id, 'guild': message.guild.id})
        return giveaways
    
    async def get_level(self, user: discord.Member, guild: discord.Guild) -> User | None:
        level:User = await self.amariNat.fetch_user(guild_id=guild.id, user_id=user.id)
        if not isinstance(level, User):
            level:User = await self.amariOCTANE.fetch_user(guild_id=guild.id, user_id=user.id)
        return level if isinstance(level, User) else None
        

    async def get_config_embed(self, config: GiveawayConfig, guild: discord.Guild):
        embed = discord.Embed(color=0x2b2d31, description="")
        embed.title = "Giveaway Settings"
        
        manager_roles = [guild.get_role(role) for role in config['manager_roles'] if guild.get_role(role) is not None]
        if len(manager_roles) == 0:
            embed.add_field(name="Manager Roles", value="` - ` **Add managers when?**", inline=True)
        else:
            embed.add_field(name="Manager Roles", value=f">>> 1. " + f"\n1. ".join([role.mention for role in manager_roles]), inline=True)

        blacklisted_roles = [guild.get_role(role) for role in config['blacklist'] if guild.get_role(role) is not None]
        if len(blacklisted_roles) == 0:
            embed.add_field(name="Blacklisted Roles", value="` - ` **Add blacklisted roles when?**", inline=True)
        else:
            embed.add_field(name="Blacklisted Roles", value=f">>> 1. " + f"\n1. ".join([role.mention for role in blacklisted_roles]), inline=True)

        bypass_roles = [guild.get_role(role) for role in config['global_bypass'] if guild.get_role(role) is not None]
        if len(bypass_roles) == 0:
            embed.add_field(name="Global Bypass", value="` - ` **Add bypass roles when?**", inline=False)
        else:
            embed.add_field(name="Global Bypass", value=f">>> 1. " + f"\n1. ".join([role.mention for role in bypass_roles]), inline=False)

        log_channel = guild.get_channel(config['log_channel'])
        if log_channel is None:
            embed.add_field(name="Log Channel", value="` - ` **Add log channel when?**", inline=False)
        else:
            embed.add_field(name="Log Channel", value=f"<:nat_reply:1146498277068517386> {log_channel.mention}", inline=False)
        
        return embed

        
    
