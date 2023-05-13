import datetime
import io
import json
import logging
import logging.handlers
import os
import re
from ast import literal_eval

import chat_exporter
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
			# application_id=951019275844460565, # for nat
			application_id=1010883367119638658 # for natasha
		)

	async def setup_hook(self):

		# Nat DB
		bot.mongo = motor.motor_asyncio.AsyncIOMotorClient(str(bot.connection_url))
		bot.db = bot.mongo["NAT"]
		bot.timer = Document(bot.db, "timer")
		bot.lockdown = Document(bot.db, "lockdown")
		bot.dankSecurity = Document(bot.db, "dankSecurity")
		bot.quarantinedUsers = Document(bot.db, "quarantinedUsers")
		bot.mafiaConfig = Document(bot.db, "mafiaConfig")
		
		# Octane DB
		bot.octane = motor.motor_asyncio.AsyncIOMotorClient(str(bot.dankHelper))
		bot.db2 = bot.octane["Dank_Data"]
		bot.dankItems = Document(bot.db2, "Item prices")

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
	
	# setup mafia transcript
	if message.author.id == 511786918783090688 and len(message.embeds)>0:
		embed = message.embeds[0]
		if embed.description is not None and "Thank you all for playing! Deleting this channel in 10 seconds" in embed.description:
			
			channel = message.channel
			guild = channel.guild
			client = guild.me
			messages = [message async for message in channel.history(limit=None)]

			data = await bot.mafiaConfig.find(guild.id)
			if data is None:
				return
			
			if data['enable_logging'] is True and data['logs_channel'] is not None:
				log_channel = guild.get_channel(int(data['logs_channel']))
				if log_channel is None:
					return
				
				# print transcript file
				transcript_file = await chat_exporter.raw_export(
					channel, messages=messages, tz_info="Asia/Kolkata", 
					guild=guild, bot=client, fancy_times=True, support_dev=False)
				transcript_file = discord.File(io.BytesIO(transcript_file.encode()), filename=f"Mafia Logs.html")
				link_msg  = await log_channel.send(content = f"**Mafia Logs:** <t:{int(datetime.datetime.utcnow().timestamp())}>", file=transcript_file, allowed_mentions=discord.AllowedMentions.none())
				link_view = discord.ui.View()
				link_view.add_item(discord.ui.Button(emoji="<:nat_mafia:1102305100527042622>",label="Mafia Evidence", style=discord.ButtonStyle.link, url=f"https://mahto.id/chat-exporter?url={link_msg.attachments[0].url}"))
				await link_msg.edit(view=link_view)

	# pool logging for dank memer
	if message.author.id == 270904126974590976 and len(message.embeds)>0:
		if message.interaction is not None:
			if 'serverevents' in message.interaction.name:
				bl_list = ['serverevents payout', 'serverevents run serverbankrob', 'serverevents run raffle', 'serverevents run splitorsteal']
				if message.interaction.name in bl_list:
					data = await bot.dankSecurity.find(message.guild.id)
					member = message.interaction.user
					if data:
						if member.id not in data['whitelist'] and member.id != member.guild.owner.id: 
							await message.delete()
							try:
								await member.remove_roles(message.guild.get_role(data['event_manager']), reason="Member is not a authorized Dank Manager.")
							except:
								pass
							role = None
							if data['quarantine'] is not None:					
								role = message.guild.get_role(data['quarantine'])
							try:
								await quarantineUser(bot, member, role, f"{member.name} (ID: {member.id}) {member.mention} has made an unsucessful attempt to run `/{message.interaction.name}`!")					
							except:
								pass
							
							securityLog = bot.get_channel(1089973828215644241)
							loggingChannel = bot.get_channel(data['logs_channel'])
							isLogEnabled = data['enable_logging']
							if securityLog is not None:
								webhooks = await securityLog.webhooks()
								webhook = discord.utils.get(webhooks, name=bot.user.name)
								if webhook is None:
									webhook = await securityLog.create_webhook(name=bot.user.name, reason="Dank Pool Logs", avatar=await bot.user.avatar.read())
								embed = await get_warning_embed(f"{member.mention} has made an unsucessful attempt to run `/{message.interaction.name}`!")	
								view = discord.ui.View()
								view.add_item(discord.ui.Button(emoji = '<:tgk_link:1105189183523401828>',label=f'Used at', url=f"{message.jump_url}"))
								await webhook.send(
									embed=embed,
									username=message.guild.name,
									avatar_url=message.guild.icon.url,
									view=view
								)
								if loggingChannel is not None and isLogEnabled is True:
									webhooks = await loggingChannel.webhooks()
									webhook = discord.utils.get(webhooks, name=bot.user.name)
									if webhook is None:
										webhook = await loggingChannel.create_webhook(name=bot.user.name, reason="Dank Pool Logs", avatar=await bot.user.avatar.read())

									embed = discord.Embed(
										title = f"Security Breach!",
										description=
										f"` - `   **Command:** `/{message.interaction.name}`\n"
										f"` - `   **Used by:** {member.mention}\n",
										color=discord.Color.random()
									)

									await webhook.send(
										embed=embed,
										username=member.name,
										avatar_url=str(member.avatar.url),
										view=view
									)
							embed = await get_warning_embed(f"{member.mention} has made an unsucessful attempt to run `/{message.interaction.name}`!")
							try:
								view = discord.ui.View()
								view.add_item(discord.ui.Button(label=f'Used at', url=f"{message.jump_url}"))
								await message.guild.owner.send(embed = embed, view=view)
							except:
								pass
				

	# payout logging
	# if message.author.id == 270904126974590976 and len(message.embeds)>0:
	# 	embed = message.embeds[0]
	# 	if embed.description is not None and embed.description.startswith('Successfully paid') and embed.description.endswith("from the server's pool!"):
	# 		try:
	# 			command_message = await message.channel.fetch_message(message.reference.message_id)
	# 		except:
	# 			command_message = None
			
	# 		if command_message is not None and command_message.interaction.name == "serverevents payout":
	# 			payoutEmbed = command_message.embeds[0].to_dict()
	# 			winner = re.findall(r"<@!?\d+>", payoutEmbed['description'])

	# 			# get prize
	# 			prize = re.findall(r"\*\*(.*?)\*\*", payoutEmbed['description'])[0]
	# 			emojis = list(set(re.findall(":\w*:\d*", prize)))
	# 			for emoji in emojis:
	# 				prize = prize.replace(emoji,"",100)
	# 				prize = prize.replace("<>","",100)
	# 				prize = prize.replace("<a>","",100)
	# 				prize = prize.replace("  "," ",100)
	# 			prize = prize.strip()
	# 			if "⏣" not in prize:
	# 				number_of_item = prize.split(" ")[0][:-1]
	# 				item = " ".join(prize.split(" ")[1:])
	# 				item_prize = int((await bot.dankItems.find(item))['price'])
	# 				prize = int(number_of_item)*item_prize
	# 			else:
	# 				prize = int(prize.split(" ")[1])

	# 			user = command_message.interaction.user.id
	# 			guild = message.guild.id
	# 			time = datetime.datetime.utcnow()
					


	# 		payoutLog = bot.get_channel(1089973828215644241)
	# 		if payoutLog is not None:
	# 			await payoutLog.send(embed=embed)

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
				managerRole = None
				description = message.embeds[0].to_dict()['description']
				idList = re.findall("(\d{18,19})", description)
				if len(idList) > 0:
					managerRole = int(idList[0])
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
async def on_audit_log_entry_create(entry):
	match entry.action:
		case discord.AuditLogAction.member_role_update:
			if entry.changes.after.roles:
				added_to = entry.target
				added_by = entry.user
				roles = entry.changes.after.roles
				member = entry.target

				# check if dank manager role is added
				data = await bot.dankSecurity.find(entry.target.guild.id)

				if data:
					event_manager = member.guild.get_role(data['event_manager'])
					if event_manager is not None and event_manager in roles and member.id not in data['whitelist'] and member.id != member.guild.owner.id: 
						try:
							await member.remove_roles(member.guild.get_role(data['event_manager']), reason="Member is not a authorized Dank Manager.")
						except:
							pass
						role = None
						if data['quarantine'] is not None:					
							role = member.guild.get_role(data['quarantine'])
						try:
							await quarantineUser(bot, member, role, f"{member.name}(ID: {member.id}) has made an unauthorized attempt to get Dank Manager role.")	
							await quarantineUser(bot, added_by, role, f"{added_by.name}(ID: {added_by.id}) has made an unauthorized attempt to give Dank Manager role to {member.name} (ID: {member.id}).")					
						except:
							pass
						
						securityLog = bot.get_channel(1089973828215644241)
						loggingChannel = bot.get_channel(data['logs_channel'])
						isLogEnabled = data['enable_logging']
						if securityLog is not None:
							webhooks = await securityLog.webhooks()
							webhook = discord.utils.get(webhooks, name=bot.user.name)
							if webhook is None:
								webhook = await securityLog.create_webhook(name=bot.user.name, reason="Dank Pool Logs", avatar=await bot.user.avatar.read())
							embed = await get_warning_embed(f"{member.mention} has made an unsucessful attempt to get **Dank Manager role**!")	
							await webhook.send(
								embed=embed,
								username=member.guild.name,
								avatar_url=member.guild.icon.url
							)
							if loggingChannel is not None and isLogEnabled:
								webhooks = await loggingChannel.webhooks()
								webhook = discord.utils.get(webhooks, name=bot.user.name)
								if webhook is None:
									webhook = await loggingChannel.create_webhook(name=bot.user.name, reason="Dank Pool Logs", avatar=await bot.user.avatar.read())
								embed = discord.Embed(
									title=f'Unauthorized attempt to get Dank Manager role!',
									description=
									f"` - `   **Added to:** {added_to.mention}\n"
									f"` - `   **Added by:** {added_by.mention}\n"
									f"` - `   **Added at:** <t:{int(datetime.datetime.timestamp(datetime.datetime.now()))}>\n",
									color=2829617
								)
								await webhook.send(
									embed=embed,
									username=member.name,
									avatar_url=str(member.avatar.url)
								)
						embed = await get_warning_embed(f"{member.mention} has made an unsucessful attempt to get Dank Manager role in {member.guild.name}")
						try:
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
	bot.dankHelper = configData["dankHelper"]
else:
	# for heroku
	bot.botToken = os.environ['BOT_TOKEN']
	bot.connection_url = os.environ['MongoConnectionUrl']
	bot.amari = os.environ["amari"]
	bot.dankHelper = os.environ["dankHelper"]

# fetching assets
if os.path.exists("./utils/assets/colors.json"):
	with open("./utils/assets/colors.json") as file_data:
		bot.color = json.load(file_data)
		for color in bot.color:
			bot.color[color] = discord.Color(literal_eval(bot.color[color]))

bot.run(bot.botToken)