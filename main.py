import json
import discord
from discord.ext import commands
import os
import time as t


bot = commands.Bot(
    command_prefix=["nat "],
    case_insensitive=True,
    intents=discord.Intents.all(),
    help_command=None
)

@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")
    await bot.change_presence(activity=discord.Game(name="upgrading ..."))

@bot.command()
async def ping(ctx):
	await ctx.send("pong! {0:.2f}ms".format(bot.latency * 1000))

# loading data from json file
# setting up from tokens.py
if os.path.exists(os.getcwd()+"./properties/tokens.json"):
	with open("./properties/tokens.json") as f:
		configData = json.load(f)
	bot.botToken = configData["token"]
	bot.connection_url = configData["mongo"]
	bot.connection_url2 = configData["mongoBanDB"]
	bot.amari = configData["amari"]
else:
	# for heroku
	bot.botToken = os.environ['BOT_TOKEN']
	bot.connection_url = os.environ['MongoConnectionUrl']
	bot.connection_url2 = os.environ["mongoBanDB"]
	bot.amari = os.environ["amari"]

bot.run(bot.botToken)
