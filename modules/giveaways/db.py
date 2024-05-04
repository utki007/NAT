import discord
import datetime
from utils.db import Document
from typing import List, TypedDict, Dict

class GiveawayConfig(TypedDict):
    _id: int
    enabled: bool
    manager_roles: list[int]
    log_channel: int | None
    multipliers: dict[int, int]
    blacklist: list[int]
    dm_message: str
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
        self.db = bot.mongo["Giveaways"]
        self.config = Document(self.db, "config")
        self.giveaways = Document(self.db, "giveaways")
        self.config_cache: Dict[int, GiveawayConfig] = {}
        self.giveaways_cache = {}

    async def get_config(self, guild: discord.Guild):
        if guild.id in self.config_cache.keys():
            return self.config_cache[guild.id]
        config = await self.config.find(guild.id)
        if config is None:
            config = await self.create_config(guild)
            self.config_cache[guild.id] = config
        return config
    
    async def create_config(self, guild: discord.Guild) -> GiveawayConfig:
        data: GiveawayConfig = {
            "_id": guild.id,
            "enabled": True,
            "manager_roles": [],
            "log_channel": None,
            "multipliers": {},
            "blacklist": [],
            "dm_message": "Please dm Host to claim your prize!",
            "global_bypass": []
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