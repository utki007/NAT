import asyncio
import datetime
import io
import json
import logging
import logging.handlers
import os
import re
import traceback
import aiohttp
from ast import literal_eval

import chat_exporter
import discord
import motor.motor_asyncio
from discord.ext import commands
from discord import app_commands

from dotenv import load_dotenv
from utils.db import Document
from utils.embeds import *
from utils.functions import *
from utils.convertor import dict_to_tree
from io import BytesIO

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

load_dotenv()
intents = discord.Intents.all()
intents.presences = False
class MyBot(commands.Bot):
	def __init__(self, application_id):
		super().__init__(
			command_prefix=["nat ", "Nat ", "nAt", "naT ", "NAt ", "NaT ", "nAT ", "NAT "],
			case_insensitive=True,
			owner_ids=[488614633670967307, 301657045248114690],
			intents=intents,
			help_command=None,
			application_id=application_id,
			activity=discord.Activity(
				type=discord.ActivityType.playing, 
				name="Starting up ..."
			),
			status=discord.Status.idle
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
		bot.dankAdventureStats = Document(bot.db, "dankAdventureStats")
		bot.premium = Document(bot.db, "premium")
		bot.userSettings = Document(bot.db, "userSettings")
		bot.config = Document(bot.db, "config")
		bot.dankFish = {
			"timestamp" : 1705583700,
			"active" : True
 		}
		bot.gboost = {
			"timestamp" : 1705583700,
			"active" : True
		}

		# Octane DB
		bot.octane = motor.motor_asyncio.AsyncIOMotorClient(str(bot.dankHelper))
		bot.db2 = bot.octane["Dank_Data"]
		bot.dankItems = Document(bot.db2, "Item prices")

		for file in os.listdir('./cogs'):
			if file.endswith('.py') and not file.startswith(("_", "donations")):
				await bot.load_extension(f'cogs.{file[:-3]}')
	
	async def on_ready(self):		
		print(f"{bot.user} has connected to Discord!")
		await bot.change_presence(status=discord.Status.dnd, activity=discord.Activity(type=discord.ActivityType.watching, name=f"Beta Version 2.1.0!"))

if os.path.exists(os.getcwd()+"./properties/tokens.json"):
	application_id = 1010883367119638658
else:
	application_id = 951019275844460565

bot = MyBot(application_id)

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
						if data['enabled'] is False: return
						if member.id not in data['whitelist'] and member.id != member.guild.owner.id: 
							try:
								await message.delete()
							except:
								pass
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
							if 'logs_channel' in data.keys() and 'enable_logging' in data.keys():
								loggingChannel = bot.get_channel(data['logs_channel'])
								isLogEnabled = data['enable_logging']
							else:
								loggingChannel = None
								isLogEnabled = False
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
								# if loggingChannel is not None and isLogEnabled is True:
								# 	webhooks = await loggingChannel.webhooks()
								# 	webhook = discord.utils.get(webhooks, name=bot.user.name)
								# 	if webhook is None:
								# 		webhook = await loggingChannel.create_webhook(name=bot.user.name, reason="Dank Pool Logs", avatar=await bot.user.avatar.read())

								# 	embed = discord.Embed(
								# 		title = f"Security Breach!",
								# 		description=
								# 		f"` - `   **Command:** `/{message.interaction.name}`\n"
								# 		f"` - `   **Used by:** {member.mention}\n",
								# 		color=discord.Color.random()
								# 	)

								# 	await webhook.send(
								# 		embed=embed,
								# 		username=member.name,
								# 		avatar_url=str(member.avatar.url),
								# 		view=view
								# 	)
							embed = await get_warning_embed(f"{member.mention} has made an unsucessful attempt to run `/{message.interaction.name}`!")
							try:
								view = discord.ui.View()
								view.add_item(discord.ui.Button(label=f'Used at', url=f"{message.jump_url}"))
								await message.guild.owner.send(embed = embed, view=view)
								if loggingChannel is not None and isLogEnabled is True:
									embed = discord.Embed(
										title = f"Security Breach!",
										description=
										f"` - `   **Command:** `/{message.interaction.name}`\n"
										f"` - `   **Used by:** {member.mention}\n",
										color=discord.Color.random()
									)
									await loggingChannel.send(embed=embed, view=view)
							except:
								pass
			
			if 'fish catch' in message.interaction.name:
				if 'fields' not in message.embeds[0].to_dict().keys():
					return
				if len(message.embeds[0].to_dict()['fields']) < 1:
					return
				fields_dict = message.embeds[0].to_dict()['fields']
				try:
					fish_event = next((item for item in fields_dict if item["name"] in ["Active Event", "Active Events"]), None)
				except:
					return
				if fish_event is None:
					if bot.dankFish['active'] is True:
						current_timestamp = int(datetime.datetime.utcnow().timestamp())
						if current_timestamp > int(bot.dankFish['timestamp']) + 600:
							bot.dankFish['active'] = False
					return
				fish_event = fish_event['value']
				fish_event = await remove_emojis(fish_event)
				fish_event = fish_event.split("\n")
				for line in fish_event:
					index = fish_event.index(line)
					if 'https:' in fish_event[index]:
						fish_event[index] = f"## " + fish_event[index].split(']')[0] + "](<https://dankmemer.lol/tutorial/random-timed-fishing-events>)"
					elif '<t:' in fish_event[index]:
						fish_event[index] = "<:nat_reply:1146498277068517386>" + fish_event[index]
					else:
						fish_event[index] = "<:nat_replycont:1146496789361479741>" + fish_event[index]
				fish_event = "\n".join(fish_event)

				if bot.dankFish['active'] is False:
					
					# return if end time > current time
					current_timestamp = int(datetime.datetime.utcnow().timestamp())
					if bot.dankFish['timestamp'] > current_timestamp:
						bot.dankFish['active'] = True
						return 
					
					bot.dankFish['active'] = True
					timestamp = list(set(re.findall("\<t:\w*:R\>\d*", fish_event)))
					bot.dankFish['timestamp'] = int(timestamp[0].replace("<t:","",1).replace(":R>","",1))
					
					records = await bot.userSettings.get_all({'fish_events':True})
					user_ids = [record["_id"] for record in records]

					for user_id in user_ids:
						user = await bot.fetch_user(user_id)
						try:
							await user.send(fish_event)
							await asyncio.sleep(0.2)	
						except:
							pass
				
				elif bot.dankFish['active'] is True:
					current_timestamp = int(datetime.datetime.utcnow().timestamp())
					if current_timestamp > bot.dankFish['timestamp']:
						bot.dankFish['active'] = False

			if 'multipliers xp' in message.interaction.name:
				
				boostMsgs = [line for line in message.embeds[0].to_dict()['description'].split("\n") if "Global Boost" in line]
				if len(boostMsgs) < 2: 
					if len(boostMsgs) == 0:
						if bot.gboost['active'] is True:
							current_timestamp = int(datetime.datetime.utcnow().timestamp())
							if current_timestamp > int(bot.gboost['timestamp']) + 600:
								bot.gboost['active'] = False
								bot.gboost['timestamp'] = 1705583700
					return
				timestamp = re.findall("\<t:\w*:R\>\d*", boostMsgs[1])
				if len(timestamp) < 1: return
				timestamp = int(timestamp[0].replace("<t:","",1).replace(":R>","",1))


				if bot.gboost['active'] is False:
					
					# return if end time > current time
					current_timestamp = int(datetime.datetime.utcnow().timestamp())
					if bot.gboost['timestamp'] > current_timestamp:
						bot.gboost['active'] = True
						return 
					
					bot.gboost['active'] = True
					bot.gboost['timestamp'] = timestamp
					
					records = await bot.userSettings.get_all({'gboost':True})
					user_ids = [record["_id"] for record in records]

					gboostMsg = [line for line in message.embeds[0].to_dict()['description'].split(">")]
					gboostMsg[3] = gboostMsg[3].split('\n')[0]
					gboostMsg[2] = gboostMsg[2].split(']')[0] + "](<https://dankmemer.lol/store>)"
					gboostMsg = [list.strip() for list in gboostMsg[2:4]]
					content = "## Global Boost\n<:nat_replycont:1146496789361479741> "
					content += f"\n<:nat_replycont:1146496789361479741> **Message:** ".join(gboostMsg)
					content += f"\n<:nat_reply:1146498277068517386> **Ends at:** <t:{timestamp}:R>"

					for user_id in user_ids:
						user = await bot.fetch_user(user_id)
						try:
							await user.send(content)
							await asyncio.sleep(0.2)	
						except:
							pass
				
				elif bot.gboost['active'] is True:
					current_timestamp = int(datetime.datetime.utcnow().timestamp())
					if current_timestamp > bot.gboost['timestamp']:
						if current_timestamp > bot.gboost['timestamp'] + 18000:
							bot.gboost['active'] = False
						else:
							bot.gboost['timestamp'] = timestamp
				
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
				description = message.embeds[0].to_dict()['fields'][0]['value']
				idList = re.findall("(\d{18,19})", description)
				if len(idList) > 0:
					managerRole = int(idList[0])
					data = await bot.dankSecurity.find(message.guild.id)
					if not data:
						data = {"_id": message.guild.id, "event_manager": None, "whitelist": [], "quarantine": None, "enabled": False}
					if data['event_manager'] != managerRole:
						data['event_manager'] = managerRole
						await bot.dankSecurity.upsert(data)
		
		# For adventure stats
		if message.interaction is not None and message.interaction.name == 'adventure':
						
			if 'author' not in message.embeds[0].to_dict().keys():
				return
			
			if 'name' not in message.embeds[0].to_dict()['author'].keys():
				return

			if message.embeds[0].to_dict()['author']['name'] != 'Adventure Summary':
				return
					
			user = message.interaction.user
			today = str(datetime.date.today())
			data = await bot.dankAdventureStats.find(user.id)
			if data is None:
				data = {
					"_id": user.id,
					"rewards": {
						today : {
							"total_adv": 0,
							"reward_adv": 0,
							"dmc_from_adv": 0,
							"frags": 0,
							"dmc": {},
							"items": {},
							"luck": {},
							"xp": {},
							"coins":	{}
						}
					}
				}
			else:
				if today not in data['rewards'].keys():
					while len(data['rewards']) >= 3:
						del data['rewards'][list(data['rewards'].keys())[0]]
					data['rewards'][today] = {
						"total_adv": 0,
						"reward_adv": 0,
						"dmc_from_adv": 0,
						"frags": 0,
						"dmc": {},
						"items": {},
						"luck": {},
						"xp": {},
						"coins":	{}
					}

			if 'total_adv' not in data['rewards'][today].keys():
				data['rewards'][today]['total_adv'] = 0
			rewards = next((item for item in message.embeds[0].to_dict()['fields'] if item["name"] == "Rewards"), None)
			if rewards is None:
				data['rewards'][today]['total_adv'] += 1
				return await bot.dankAdventureStats.upsert(data)
			else:
				data['rewards'][today]['total_adv'] += 1
				data['rewards'][today]['reward_adv'] += 1
				rewards = rewards['value'].replace('-','',100).split('\n')
				rewards = [rewards.strip() for rewards in rewards]
				
				# parse rewards
				for items in rewards:
					item_list = items.split(" ")

					# for dmc
					if item_list[0] == '⏣':
						data['rewards'][today]['dmc_from_adv'] += int(item_list[1].replace(',','',100))

						key = item_list[1].replace(',','',100)
						if key in data['rewards'][today]['dmc']:
							data['rewards'][today]['dmc'][key] += 1
						else:
							data['rewards'][today]['dmc'][key] = 1

					# for items
					elif items[0].isdigit():

						# remove emojis from item name
						emojis = list(set(re.findall(":\w*:\d*", items)))
						for emoji in emojis:
							items = items.replace(emoji,"",100)
						items = items.replace("<>","",100)
						items = items.replace("<a>","",100)
						items = items.replace("  "," ",100)

						if '.' in items:
							key = " ".join(item_list[0:1])
							if key in data['rewards'][today]['xp'] :
								data['rewards'][today]['xp'][key] += 1
							else:
								data['rewards'][today]['xp'][key] = 1
						elif 'Skin Fragments' in items:
							data['rewards'][today]['frags'] += int(item_list[0][:-1])
						else:
							quantity = int(item_list[0][:-1])
							key = (" ".join(items.split(" ")[1:])).strip()
							if key in data['rewards'][today]['items']:
								data['rewards'][today]['items'][key] += quantity
							else:
								data['rewards'][today]['items'][key] = quantity
								
					else:
						if 'Luck Multiplier' in items:
							key = item_list[0][1:-1]
							if key in data['rewards'][today]['luck']:
								data['rewards'][today]['luck'][key] += 1
							else:
								data['rewards'][today]['luck'][key] = 1
						elif ' Coin Multiplier' in items:
							key = item_list[0][1:-1]
							if key in data['rewards'][today]['coins']:
								data['rewards'][today]['coins'][key] += 1
							else:
								data['rewards'][today]['coins'][key] = 1
				
			return await bot.dankAdventureStats.upsert(data)

		# for fish catch
		if message.interaction is not None and message.interaction.name == 'fish catch':
			if 'title' not in message.embeds[0].to_dict().keys():
				return
			if message.embeds[0].to_dict()['title'] != 'Fishing':
				return
			if 'fields' not in message.embeds[0].to_dict().keys():
				return
			if len(message.embeds[0].to_dict()['fields']) < 1:
				return
			fields_dict = message.embeds[0].to_dict()['fields']
			try:
				fish_event = next((item for item in fields_dict if item["name"] in ["Active Event", "Active Events"]), None)
			except:
				return
			if fish_event is None:
				if bot.dankFish['active'] is True:
					current_timestamp = int(datetime.datetime.utcnow().timestamp())
					if current_timestamp > int(bot.dankFish['timestamp']) + 600:
						bot.dankFish['active'] = False
				return
			fish_event = fish_event['value']
			fish_event = await remove_emojis(fish_event)
			fish_event = fish_event.split("\n")
			# fish_event[0] = f"## " + fish_event[0].split(']')[0] + "](<https://dankmemer.lol/tutorial/random-timed-fishing-events>)"
			# fish_event[-1] = "<:nat_reply:1146498277068517386>" + fish_event[-1]
			for line in fish_event:
				index = fish_event.index(line)
				if 'https:' in fish_event[index]:
					fish_event[index] = f"## " + fish_event[index].split(']')[0] + "](<https://dankmemer.lol/tutorial/random-timed-fishing-events>)"
				elif '<t:' in fish_event[index]:
					fish_event[index] = "<:nat_reply:1146498277068517386>" + fish_event[index]
				else:
					fish_event[index] = "<:nat_replycont:1146496789361479741>" + fish_event[index]
			fish_event = "\n".join(fish_event)

			if bot.dankFish['active'] is False:
				
				# return if end time > current time
				current_timestamp = int(datetime.datetime.utcnow().timestamp())
				if bot.dankFish['timestamp'] > current_timestamp:
					bot.dankFish['active'] = True
					return 
				
				bot.dankFish['active'] = True
				timestamp = list(set(re.findall("\<t:\w*:R\>\d*", fish_event)))
				bot.dankFish['timestamp'] = int(timestamp[0].replace("<t:","",1).replace(":R>","",1))
				
				records = await bot.userSettings.get_all({'fish_events':True})
				user_ids = [record["_id"] for record in records]

				for user_id in user_ids:
					user = await bot.fetch_user(user_id)
					try:
						await user.send(fish_event)
						await asyncio.sleep(0.2)			
					except:
						pass
			
			elif bot.dankFish['active'] is True:
				current_timestamp = int(datetime.datetime.utcnow().timestamp())
				if current_timestamp > bot.dankFish['timestamp']:
					bot.dankFish['active'] = False
	# return if message is from bot
	if message.author.bot:
		return

@bot.event
async def on_audit_log_entry_create(entry: discord.AuditLogEntry):
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
					if data['enabled'] is False: return
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
							if added_by.id != member.guild.owner.id:								
								await quarantineUser(bot, added_by, role, f"{added_by.name}(ID: {added_by.id}) has made an unauthorized attempt to give Dank Manager role to {member.name} (ID: {member.id}).")					
						except:
							pass
						
						securityLog = bot.get_channel(1089973828215644241)
						if 'logs_channel' in data.keys() and 'enable_logging' in data.keys():
							loggingChannel = bot.get_channel(data['logs_channel'])
							isLogEnabled = data['enable_logging']
						else:
							loggingChannel = None
							isLogEnabled = False
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
							# if loggingChannel is not None and isLogEnabled:
							# 	webhooks = await loggingChannel.webhooks()
							# 	webhook = discord.utils.get(webhooks, name=bot.user.name)
							# 	if webhook is None:
							# 		webhook = await loggingChannel.create_webhook(name=bot.user.name, reason="Dank Pool Logs", avatar=await bot.user.avatar.read())
							# 	embed = discord.Embed(
							# 		title=f'Unauthorized attempt to get Dank Manager role!',
							# 		description=
							# 		f"` - `   **Added to:** {added_to.mention}\n"
							# 		f"` - `   **Added by:** {added_by.mention}\n"
							# 		f"` - `   **Added at:** <t:{int(datetime.datetime.timestamp(datetime.datetime.now()))}>\n",
							# 		color=2829617
							# 	)
							# 	await webhook.send(
							# 		embed=embed,
							# 		username=member.name,
							# 		avatar_url=str(member.avatar.url)
							# 	)
						embed = await get_warning_embed(f"{member.mention} has made an unsucessful attempt to get Dank Manager role in {member.guild.name}")
						try:
							await member.guild.owner.send(embed = embed)
						except:
							pass

@bot.event
async def on_guild_join(guild: discord.Guild):
	if guild.member_count < 50:
		config = await bot.config.find(bot.user.id)
		if config is None:pass
		if guild.id in config['member_lock_bypass']:
			pass
		else:
			try:
				await guild.owner.send(f"Hey, {guild.owner.name}!\nThanks for adding me to your server {guild.name}!\n\nBut sad to say your server dose not meet the minimum member requirement of 50 members.\n\nPlease add me back when you have 50 members in your server, if you want to whitelist your server please contact us in our support [server](https://discord.gg/4BpUghwr9w).\n\nThanks for understanding!")
			except:
				for channel in guild.channels:
					try:
						await channel.send(f"Hey, {guild.owner.name}!\nThanks for adding me to your server {guild.name}!\n\nBut sad to say your server dose not meet the minimum member requirement of 50 members.\n\nPlease add me back when you have 50 members in your server, if you want to whitelist your server please contact us in our support [server](https://discord.gg/4BpUghwr9w).\n\nThanks for understanding!")
						break
					except:
						pass
			await guild.leave()

	channel = bot.get_channel(1145314908599222342)
	await channel.send(
		f"## ★｡ﾟ☆ﾟ{guild.name.title()}☆ﾟ｡★\n"
		f'- **ID:** {guild.id}\n'
		f'- **Owner:** {guild.owner.mention} (ID: `{guild.owner.id}`)\n'
		f'- **Members:** {guild.member_count}\n'
		f'- **Created At:** <t:{int(guild.created_at.timestamp())}>\n'
		f'- **Joined At:** <t:{int(datetime.datetime.utcnow().timestamp())}>\n'
  		f'- **Bot is in:** {len(bot.guilds)} guilds.\n'
		f'## ☆ﾟ｡★｡ﾟ☆ﾟ｡★｡ﾟ☆ﾟ｡★｡ﾟ☆ﾟ｡ﾟ☆ﾟ｡★｡ﾟ☆ﾟ\n**\n**',
		allowed_mentions=discord.AllowedMentions.none()
	)

@bot.event
async def on_guild_remove(guild: discord.Guild):
	channel = bot.get_channel(1145314908599222342)
	await channel.send(
		f"## ★｡ﾟ☆ﾟ{guild.name.title()}☆ﾟ｡★\n"
		f'- **ID:** {guild.id}\n'
		f'- **Owner:** {guild.owner.mention} (ID: `{guild.owner.id}`)\n'
		f'- **Members:** {guild.member_count}\n'
		f'- **Created At:** <t:{int(guild.created_at.timestamp())}>\n'
		f'- **Left At:** <t:{int(datetime.datetime.utcnow().timestamp())}>\n'
  		f'- **Bot is in:** {len(bot.guilds)} guilds.\n'
		f'## ☆ﾟ｡★｡ﾟ☆ﾟ｡★｡ﾟ☆ﾟ｡★｡ﾟ☆ﾟ｡ﾟ☆ﾟ｡★｡ﾟ☆ﾟ\n**\n**',
		allowed_mentions=discord.AllowedMentions.none()
	)

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
	# for sparked
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