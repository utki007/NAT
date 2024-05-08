import discord
from discord.ext import commands

import os
import asyncio
import datetime
import logging
import logging.handlers
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from utils.db import Document

load_dotenv()

os.remove("discord.log")

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
logging.getLogger('discord.http').setLevel(logging.INFO)

handler = logging.handlers.RotatingFileHandler(
    filename='discord.log',
    encoding='utf-8',
    maxBytes=32 * 1024 * 1024,  # 32 MiB
    backupCount=5,  # Rotate through 5 files
)
dt_fmt = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
handler.setFormatter(formatter)
logger.addHandler(handler)

class Botbase(commands.Bot):
    def __init__(self, application_id, sync: bool = False):
        super().__init__(intents=discord.Intents.all(), command_prefix=".",
                         description="A Bot for server management", case_insensitive=False,
                         owner_ids=[488614633670967307, 301657045248114690],
                         activity=discord.Activity(type=discord.ActivityType.custom, name="Startup"),
                         status=discord.Status.offline, help_command=None, application_id=application_id)
        self.start_time = datetime.datetime.now()
        self.sync = sync
        self.token = os.environ.get("TEST_TOKEN")
        self.secret = os.environ.get("TEST_SECRET")
        self.connection_url = os.environ.get("TEST_MONGO")
        self.connection_url2 = os.environ.get("ACE_DB")
        self.restart = False
        self.mongo = AsyncIOMotorClient(self.connection_url)
        self.db = self.mongo["Database"]
        self.aceDb = AsyncIOMotorClient(self.connection_url2)
        self.db2 = self.aceDb["TGK"]
        self.emoji_server: discord.Guild | None = None
        self.dank_db = self.mongo["Dank_Data"]
        self.dankItems = Document(self.dank_db, "Dank_Items")

    async def setup_hook(self):
        for file in os.listdir("./cogs"):
            if file.endswith(".py") and not file.startswith(("__",)) and file.startswith(("owner", "serverUtils", "mafia")):
                await self.load_extension(f"cogs.{file[:-3]}")

        # for folder in os.listdir("./modules"):
        #     if folder == "Security":                
        #         for file in os.listdir(f"./modules/{folder}"):
        #             if file == "module.py":
        #                 await self.load_extension(f"modules.{folder}.{file[:-3]}")


bot = Botbase(998152864201457754, False)

tree = bot.tree


async def main():
    await bot.start(os.environ.get("TEST_TOKEN"))


@bot.event
async def on_ready():
    print(f"Logged in successfully as {bot.user.name} | {bot.user.id}")
    print(f"loaded cogs: {len(bot.extensions)}")
    #print(f"Cached Emoji Server: {bot.emoji_server.name} | {bot.emoji_server.id}")
    print(f"Bot Views: {len(bot.persistent_views)}")
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="Over Server Security"),
        status=discord.Status.offline)

    await bot.tree.sync()


# @bot.tree.command(
#     name="ping",
#     description="Check bots latency")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await bot.process_commands(message)

async def ping(interaction):
    await interaction.response.send_message("Pong!")
    await interaction.edit_original_response(content=None,
                                             embed=discord.Embed(description=f"Ping {bot.latency * 1000.0:.2f}ms"))


@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.author.id == 461441940496580622:
        return
    await bot.process_commands(message)


asyncio.run(main())
if bot.restart:
    os.system("cls")
    os.system("python dev.py")
