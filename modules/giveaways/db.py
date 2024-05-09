import os
import discord
import datetime

from typing import List, TypedDict, Dict
from amari import AmariClient, User

from utils.db import Document
from utils.embeds import get_formated_embed, get_formated_field


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
        embed_args = await get_formated_embed(["Manager Roles", "Log Channel", "Blacklisted Roles", "Global Bypass", "Multipliers"])
        embed.description += f"<a:tgk_firstprize:1215646428085620756> `{guild.name} Giveaway Settings`\n\n"
        embed.description += f"{await get_formated_field(guild, name=embed_args['Manager Roles'], type='role', data=config['manager_roles'])}\n"
        embed.description += f"{await get_formated_field(guild, name=embed_args['Blacklisted Roles'], type='role', data=config['blacklist'])}\n"
        embed.description += f"{await get_formated_field(guild, name=embed_args['Global Bypass'], type='role', data=config['global_bypass'])}\n"
        embed.description += f"{await get_formated_field(guild, name=embed_args['Log Channel'], type='channel', data=config['log_channel'])}\n"
        embed.description += "\n\n `Multipliers`\n"
        if config['multipliers'] == {}:
            embed.description += "* No Multipliers Set"
            return embed

        for key, multi in config['multipliers'].items():
            role = guild.get_role(int(key))
            if not isinstance(role, discord.Role):
                del config['multipliers'][key]
                await self.update_config(guild, config)
                continue
            embed.description += f"* `{multi}`x {role.mention}\n"
        return embed

        
    
