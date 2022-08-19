import discord
import json
import os
import time as t
from discord.ext import commands

class MyBot(commands.Bot):
	def __init__(self):
		
		super().__init__(
			command_prefix=["nat "],
			case_insensitive=True,
			owner_ids=[488614633670967307, 301657045248114690],
			intents=discord.Intents.all(),
			application_id=951019275844460565,
		)

	async def setup_hook(self):
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

		await bot.change_presence(status=discord.Status.dnd, activity=discord.Activity(type=discord.ActivityType.watching, name="Upgrading ..."))



bot = MyBot()

@bot.event
async def on_message(message):
	
	# return if message is from bot
	if message.author.bot:
		return

# loading enviroment variables
if os.path.exists(os.getcwd()+"./properties/tokens.json"):
	# loading from tokens.py
	with open("./properties/tokens.json") as f:
		configData = json.load(f)
	bot.botToken = configData["token"]
	bot.connection_url = configData["mongo"]
	bot.amari = configData["amari"]
else:
	# for heroku
	bot.botToken = os.environ['BOT_TOKEN']
	bot.connection_url = os.environ['MongoConnectionUrl']
	bot.connection_url2 = os.environ["mongoBanDB"]
	bot.amari = os.environ["amari"]

bot.run(bot.botToken)
