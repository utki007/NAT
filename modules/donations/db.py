from typing import TypedDict
from utils.db import Document
from discord.ext import commands
from discord import Embed, Guild
from utils.embeds import get_formated_embed, get_formated_field


class Events(TypedDict):
    event_name: str
    donations: int


class UserDonations(TypedDict):
    user_id: int
    donations: int
    events: dict[str, Events]


class Ranks(TypedDict):
    role_id: int
    donations: int


class EventConfig(TypedDict):
    event_name: str
    ranks: dict[str, Ranks]
    auto_log_channels: list[int]
    log_channel: int


class DankProfile(TypedDict):
    name: str
    events: dict[str, EventConfig]
    ranks: dict[str, Ranks]
    tracking_channels: list[int]
    log_channel: int
    emoji: str


class GuildConfig(TypedDict):
    _id: int
    manager_roles: list[int]
    profiles: dict[int, UserDonations]
    log_channel: int

class UserDonations(TypedDict):
    user_id: int
    guild_id: int
    events: dict[str, Events]
    profiles: dict[str, int]

class Backend:
    def __init__(self, bot: commands.Bot):
        self.db = bot.mongo["Donations"]
        self.config = Document(self.db, "config", GuildConfig)
        self.donations = Document(self.db, "users", UserDonations)

    async def get_guild_config(self, guild_id: int) -> GuildConfig:
        guild_config = await self.config.find({"_id": guild_id})
        if not guild_config:
            guild_config = {
                "_id": guild_id,
                "manager_roles": [],
                "profiles": {
                    "Dank Donations": {
                        "name": "Dank Donations",
                        "events": {},
                        "ranks": {},
                        "tracking_channels": [],
                        "log_channel": None,
                        "emoji": "⏣",
                    }
                },
                "log_channel": None,
            }
            await self.config.insert(guild_config)

        return guild_config

    async def update_guild_config(self, guild_id: int, data: dict):
        await self.config.update({"_id": guild_id}, data)

    async def get_user_donations(self, guild_id: int, user_id: int) -> UserDonations:
        user_info = await self.donations.find(
            {"user_id": user_id, "guild_id": guild_id}
        )
        return user_info

    async def get_config_embed(self, guild_config: GuildConfig, guild: Guild):
        embed = Embed(
            description="",
            color=0x2B2D31,
        )
        embed_args = await get_formated_embed(
            ["Manager Roles", "Log Channel", "Profiles"]
        )

        embed.description = (
            "<:tgk_money:1199223318662885426> `Server Donations Settings`\n\n"
        )

        embed.description += f"{await get_formated_field(guild=guild, name=embed_args['Manager Roles'], data=guild_config['manager_roles'], type='role')}\n"
        embed.description += f"{await get_formated_field(guild=guild, name=embed_args['Log Channel'], data=guild_config['log_channel'], type='channel')}\n"

        profiles = "".join([key for key in guild_config["profiles"].keys()])
        if len(profiles) == 0:
            profiles = None
        embed.description += f"{await get_formated_field(guild=guild, name=embed_args['Profiles'], data=profiles, type='str')}\n"

        return embed
