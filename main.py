import json
import logging
import logging.handlers
import os
from ast import literal_eval

import discord
import motor.motor_asyncio
from discord.ext import commands

from utils.db import Document
from utils.embeds import *
from utils.functions import *

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

intents = discord.Intents.all()
intents.presences = False
class MyBot(commands.Bot):
	def __init__(self):
		
		super().__init__(
			command_prefix=["nat "],
			case_insensitive=True,
			owner_ids=[488614633670967307, 301657045248114690],
			intents=intents,
			application_id=951019275844460565, # for nat
			# application_id=1010883367119638658 # for natasha
		)

	async def setup_hook(self):

		bot.mongo = motor.motor_asyncio.AsyncIOMotorClient(str(bot.connection_url))
		bot.db = bot.mongo["NAT"]
		bot.timer = Document(bot.db, "timer")
		bot.lockdown = Document(bot.db, "lockdown")
		bot.dankSecurity = Document(bot.db, "dankSecurity")
		bot.quarantinedUsers = Document(bot.db, "quarantinedUsers")

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
		await bot.tree.sync()
		for guild in bot.guilds:
			await bot.tree.sync(guild=guild)

		members_list = [len(guild.members) for guild in  bot.guilds]
		total_members = sum(members_list)

		await bot.change_presence(status=discord.Status.dnd, activity=discord.Activity(type=discord.ActivityType.watching, name=f"Beta Version 2.0.2!"))

bot = MyBot()

@bot.event
async def on_message(message):
	
	# return if message is from bot
	if message.author.bot:
		return
	await bot.process_commands(message)

@bot.event
async def on_message_edit(before, after):
	message = after

	if message.author.id == 270904126974590976 and len(message.embeds)>0:
		
		# for serversettings in dank
		if message.interaction is not None and message.interaction.name == 'serversettings':
			if message.embeds[0].to_dict()['title'] == 'Events Manager':
				managerRole = int(message.embeds[0].to_dict()['description'].split(" ")[-1])
				data = await bot.dankSecurity.find(message.guild.id)
				if not data:
					data = {"_id": message.guild.id, "event_manager": None, "whitelist": [], "quarantine": None}
				if data['event_manager'] != managerRole:
					data['event_manager'] = managerRole
					await bot.dankSecurity.upsert(data)

	# return if message is from bot
	if message.author.bot:
		return

@bot.event
async def on_member_update(before, after):
	member = after

	after_roles = set([role.id for role in after.roles])
	before_roles = set([role.id for role in before.roles])
	roles = list(after_roles - before_roles)

	if len(roles) > 0:
		data = await bot.dankSecurity.find(member.guild.id)
		if data:
			if data['event_manager'] in roles and member.id not in data['whitelist']:
				securityLog = bot.get_channel(1089973828215644241)
				await securityLog.send(f"{member.mention} has made an unauthorized attempt to get **Dank Manager role** in {member.guild.name}.")
				try:
					await member.remove_roles(member.guild.get_role(data['event_manager']), reason="Member is not a authorized Dank Manager.")
				except:
					pass
				role = None
				if data['quarantine'] is not None:					
					role = member.guild.get_role(data['quarantine'])
				await quarantineUser(bot, member, role)					
				try:
					embed = await get_warning_embed(f"{member.mention} has made an unsucessful attempt to get Dank Manager role in {member.guild.name}")
					await member.guild.owner.send(embed = embed)
				except:
					pass

# @bot.event
# async def on_guild_join(guild):
# 	embed = await get_invisible_embed(f'Unable to stay in **{guild.name}**.\n > Dm utki007#0690 to whitelist your server.')
# 	whitelistedServer = [815849745327194153, 947525009247707157, 999551299286732871, 1069994776977494146, 991711295139233834, 785839283847954433]
# 	if guild.id not in whitelistedServer:
# 		try:
# 			await guild.owner.send(embed=embed)
# 		except:
# 			pass
# 		await guild.leave()

# loading enviroment variables
if os.path.exists(os.getcwd()+"./properties/tokens.json"):
	# loading from tokens.py
	with open("./properties/tokens.json") as file_data:
		configData = json.load(file_data)
	bot.botToken = configData["BOT_TOKEN"]
	bot.connection_url = configData["MongoConnectionUrl"]
	bot.amari = configData["amari"]
else:
	# for heroku
	bot.botToken = os.environ['BOT_TOKEN']
	bot.connection_url = os.environ['MongoConnectionUrl']
	bot.amari = os.environ["amari"]

# fetching assets
if os.path.exists("./utils/assets/colors.json"):
	with open("./utils/assets/colors.json") as file_data:
		bot.color = json.load(file_data)
		for color in bot.color:
			bot.color[color] = discord.Color(literal_eval(bot.color[color]))

bot.run(bot.botToken)