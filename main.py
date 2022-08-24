import discord
import json
import os
from discord.ext import commands
import logging
import logging.handlers
import motor.motor_asyncio
from utils.db import Document
from ast import literal_eval

logger = logging.getLogger('discord')
handler = logging.handlers.RotatingFileHandler(
    filename='bot.log',
    encoding='utf-8',
    maxBytes=32 * 1024 * 1024,  # 32 MiB
    backupCount=5,  # Rotate through 5 files
)
dt_fmt = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
handler.setFormatter(formatter)
logger.addHandler(handler)
class MyBot(commands.Bot):
	def __init__(self):
		
		super().__init__(
			command_prefix=["nat "],
			case_insensitive=True,
			owner_ids=[488614633670967307, 301657045248114690],
			intents=discord.Intents.all(),
			# application_id=951019275844460565, # for nat
			application_id=1010883367119638658 # for natasha
		)

	async def setup_hook(self):

		bot.mongo = motor.motor_asyncio.AsyncIOMotorClient(str(bot.connection_url))
		bot.db = bot.mongo["NAT"]
		bot.timer = Document(bot.db, "timer")
		bot.oath = Document(bot.db, "oath")
		bot.doc_remider = Document(bot.db, "reminders")

		for file in os.listdir('./cogs'):
			if file.endswith('.py') and not file.startswith("_"):
				await bot.load_extension(f'cogs.{file[:-3]}')
	
	async def on_ready(self):		
		print(f"{bot.user} has connected to Discord!")
		await bot.change_presence(
			status=discord.Status.idle, 
			activity=discord.Activity(
				type=discord.ActivityType.playing, 
				name="Starting up ..."
			)
		)
		 
		for guild in list(bot.guilds):
			await bot.tree.sync(guild=discord.Object(guild.id))
		await bot.tree.sync()

		await bot.change_presence(status=discord.Status.dnd, activity=discord.Activity(type=discord.ActivityType.listening, name="tgk devs"))

bot = MyBot()

@bot.event
async def on_message(message):
	
	# return if message is from bot
	if message.author.bot:
		return
	await bot.process_commands(message)

# loading enviroment variables
if os.path.exists(os.getcwd()+"./properties/tokens.json"):
	# loading from tokens.py
	with open("./properties/tokens.json") as file_data:
		configData = json.load(file_data)
	bot.botToken = configData["token"]
	bot.connection_url = configData["mongo"]
	bot.amari = configData["amari"]
else:
	# for heroku
	bot.botToken = os.environ['BOT_TOKEN']
	bot.connection_url = os.environ['MongoConnectionUrl']
	bot.connection_url2 = os.environ["mongoBanDB"]
	bot.amari = os.environ["amari"]

# fetching assets
if os.path.exists(os.getcwd()+"./utils/assets/colors.json"):
	with open("./utils/assets/colors.json") as file_data:
		bot.color = json.load(file_data)
		for color in bot.color:
			bot.color[color] = discord.Color(literal_eval(bot.color[color]))

bot.run(bot.botToken)