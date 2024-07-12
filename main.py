import asyncio
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

from dotenv import load_dotenv
from utils.db import Document
from utils.embeds import *
from utils.functions import *
from dotenv import load_dotenv
from utils.init import init_dankSecurity

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
        self.maintenance = False
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
        bot.dank = Document(bot.db, "dank")
        bot.cricket = Document(bot.db, "cricket")

        # Grinders DB
        bot.grinder_db = bot.mongo["Grinders_V2"]
        bot.grinderSettings = Document(bot.grinder_db, "settings")
        bot.grinderUsers = Document(bot.grinder_db, "users")    

        # Octane DB
        bot.octane = motor.motor_asyncio.AsyncIOMotorClient(str(bot.dankHelper))
        bot.db2 = bot.octane["Dank_Data"]
        bot.dankItems = Document(bot.db2, "Item prices")

        config = await bot.config.find(bot.user.id)
        if config is None: pass
        if bot.user.id != 1010883367119638658:
            self.maintenance = config['maintenance']
    
        
        for file in os.listdir('./cogs'):
            if file.endswith('.py') and not file.startswith(("_", "donations")):
                await bot.load_extension(f'cogs.{file[:-3]}')

        for folder in os.listdir("./modules"):
            if folder in ["giveaways","afk", "payouts"]:               
                for file in os.listdir(f"./modules/{folder}"):
                    if file == "module.py":
                        await bot.load_extension(f"modules.{folder}.{file[:-3]}")
    
    async def interaction_check(self, interaction: discord.Interaction):
        if self.maintenance and interaction.user.id not in self.owner_ids:
            await interaction.response.send_message("Bot is under maintenance. Please try again later.", ephemeral=True)
            return False

    async def on_ready(self):		
        print(f"{bot.user} has connected to Discord!")
        await bot.change_presence(status=discord.Status.dnd, activity=discord.Activity(type=discord.ActivityType.watching, name=f"Over Server Pools!"))
        if self.maintenance:
            await bot.change_presence(status=discord.Status.dnd, activity=discord.Activity(type=discord.ActivityType.watching, name="Under Maintenance!"))

        if os.environ.get('ENV') == 'PROD':
            with open("bot.log", "r+") as file:
                content = file.read()
                file = io.BytesIO(content.encode('utf-8'))
                chl = bot.get_channel(1246042670418362378)
                await chl.send(file=discord.File(fp=file, filename=f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.log"), 
                            content=f"<t:{int(datetime.datetime.now().timestamp())}:R>")
                with open("bot.log", "w") as edit_file:
                    pass

if os.path.exists(os.getcwd()+"./properties/tokens.json"):
    application_id = 1010883367119638658
else:
    application_id = 951019275844460565

bot = MyBot(application_id)

@bot.event
async def on_message(message):

    # transcript for mafia bot
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
                    link_msg  = await log_channel.send(content = f"**Mafia Logs:** <t:{int(datetime.datetime.now(pytz.utc).timestamp())}>", file=transcript_file, allowed_mentions=discord.AllowedMentions.none())
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
                        owner = message.guild.owner
                        owner_list = [owner.id]
                        if 'psuedo_owner' in data.keys():
                            owner_list.append(data['psuedo_owner'])
                            owner = message.guild.get_member(data['psuedo_owner'])
                        if owner is None:
                            owner = message.guild.owner
                        if member.id not in data['whitelist'] and member.id not in owner_list: 
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
                            if 'logs_channel' in data.keys():
                                loggingChannel = bot.get_channel(data['logs_channel'])
                            else:
                                loggingChannel = None
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
                                if owner.id != message.guild.owner.id:
                                    await owner.send(embed = embed, view=view)
                                if loggingChannel is not None:
                                    embed = discord.Embed(
                                        title = f"Security Breach!",
                                        description=
                                        f"` - `   **Command:** `/{message.interaction.name}`\n"
                                        f"` - `   **Used by:** {member.mention}\n",
                                        color=discord.Color.random()
                                    )
                                    try:
                                        desc = message.embeds[0].description
                                        if 'Are you sure you want' in desc:
                                            user_id = int(re.findall(r'\<\@\d+\>', desc)[0].replace('<@','',1).replace('>','',1))
                                            item = re.findall(r'\*\*(.*?)\*\*', desc)[0]
                                            item = await remove_emojis(item)
                                            embed.description += f"` - `   Tried to give **{item}** to <@{user_id}>\n"
                                    except:
                                        pass
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
                data = await bot.dank.find('dankFish')
                if data is None:
                    data = {"_id":"dankFish","dankFish":{}}
                    await bot.dank.upsert(data)
                if fish_event is None:
                    if data['dankFish'] != {}:
                        current_timestamp = int(datetime.datetime.now(pytz.utc).timestamp())
                        copy_data = data['dankFish'].copy()
                        for key in copy_data:
                            if copy_data[key] < current_timestamp:
                                del data['dankFish'][key]							
                    return await bot.dank.upsert(data)
                fish_event = fish_event['value']
                event_names = re.findall(r'\[(.*?)\]',fish_event)
                timestamp = re.findall("\<t:\w*:\d*", fish_event)# [0].replace("<t:","",1).replace(":","",1))
                timestamp = [int(t.replace("<t:","",1).replace(":","",1)) for t in timestamp]
                dict = {event_names[i]:timestamp[i] for i in range(len(event_names))}

                fish_event = await remove_emojis(fish_event)
                fish_event = fish_event.split("\n")
                for line in fish_event:
                    index = fish_event.index(line)
                    if 'https:' in fish_event[index]:
                        fish_event[index] = f"## " + fish_event[index].split(']')[0] + "](<https://dankmemer.lol/tutorial/random-timed-fishing-events>)"
                    elif index == len(fish_event)-1:
                        fish_event[index] = "<:nat_reply:1146498277068517386>" + fish_event[index]
                    else:
                        fish_event[index] = "<:nat_replycont:1146496789361479741>" + fish_event[index]
                fish_event = "\n".join(fish_event)

                if data['dankFish'] == {} or data['dankFish'] != dict:
                    data['dankFish'] = dict
                    await bot.dank.upsert(data)

                    records = await bot.userSettings.get_all({'fish_events':True})
                    user_ids = [record["_id"] for record in records]

                    for user_id in user_ids:
                        user = await bot.fetch_user(user_id)
                        try:
                            await user.send(fish_event)
                            await asyncio.sleep(0.2)	
                        except:
                            pass
                elif data['dankFish'] == dict:
                    change_in_event = False
                    current_timestamp = int(datetime.datetime.now(pytz.utc).timestamp())
                    for key in data['dankFish']:
                        if data['dankFish'][key] < current_timestamp:
                            change_in_event = True
                            del data['dankFish'][key]
                    if change_in_event:
                        await bot.dank.upsert(data)
                        records = await bot.userSettings.get_all({'fish_events':True})
                        user_ids = [record["_id"] for record in records]

                        for user_id in user_ids:
                            user = await bot.fetch_user(user_id)
                            try:
                                await user.send(fish_event)
                                await asyncio.sleep(0.2)	
                            except:
                                pass
                else:
                    return

            if 'multipliers xp' in message.interaction.name:
                await check_gboost(bot, message)

    # reminder processing for cricket bot
    if message.author.id == 814100764787081217 and len(message.embeds)>0:

        embed_dict = message.embeds[0].to_dict()
        if 'title' in embed_dict.keys():

            if embed_dict['title'] == '⏳ COOLDOWNS':

                try:
                    user = message.embeds[0].to_dict()['footer']['text']
                    user = message.guild.get_member_named(user)
                    if user is None:
                        return
                except:
                    return
                
                content = message.embeds[0].to_dict()['description']
                try:
                    drop_line = [line for line in content.split("\n") if 'Drop' in line][0]
                except:
                    return
                drop = {}
                try:
                    timestamp = int(re.findall(":\w*:", drop_line)[0].replace(":","",2))
                    remind_at = datetime.datetime.fromtimestamp(timestamp)
                    drop = {
                        "time": remind_at,
                        "message": f'https://discord.com/channels/{message.guild.id}/{message.channel.id}'
                    }
                except:
                    if 'Ready' in drop_line:
                        pass
                    else:
                        return
                
                

                try:
                    daily_line = [line for line in content.split("\n") if 'Daily' in line][0]
                except:
                    return
                daily = {}
                try:
                    timestamp = int(re.findall(":\w*:", daily_line)[0].replace(":","",2))
                    remind_at = datetime.datetime.fromtimestamp(timestamp)
                    daily = {
                        "time": remind_at,
                        "message": f'https://discord.com/channels/{message.guild.id}/{message.channel.id}'
                    }
                except:
                    if 'Ready' in drop_line:
                        pass
                    else:
                        return
                
                

                req = await check_cric_drop_and_daily(bot, message, drop, daily, user)
                if req:
                    try:
                        await message.add_reaction('<:tgk_active:1082676793342951475>')
                    except:
                        pass

    # return if message is from bot
    if message.author.bot:
        return
    await bot.process_commands(message)

@bot.event
async def on_message_edit(before, after):

    message = after

    if message.author.id == 270904126974590976 and len(message.embeds)>0:
        
        if message.interaction is not None:
            
            # for serversettings in dank
            if message.interaction.name == 'serversettings':
                if message.embeds[0].to_dict()['title'] == 'Events Manager':
                    managerRole = None
                    description = message.embeds[0].to_dict()['fields'][0]['value']
                    idList = re.findall("(\d{18,19})", description)
                    if len(idList) > 0:
                        managerRole = int(idList[0])
                        data = await bot.dankSecurity.find(message.guild.id)
                        if not data:
                            data = await init_dankSecurity(message)
                        if data['event_manager'] != managerRole:
                            data['event_manager'] = managerRole
                            await bot.dankSecurity.upsert(data)
        
            # For adventure stats
            if message.interaction.name == 'adventure':
                            
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
                                data['rewards'][today]['frags'] += int(item_list[0])
                            else:
                                quantity = int(item_list[0])
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

    if message.author.id == 814100764787081217 and len(message.embeds)>0:

        # check for drops
        if message.content != '':
            matches = ['released', 'retained']
            if any(x in message.content for x in matches):
                remind_at = datetime.datetime.now() + datetime.timedelta(hours=1)
                user = message.guild.get_member(int(re.findall("\<\@(.*?)\>", message.content)[0]))
                if user is None:
                    return
                await check_cric_drop(bot, message, remind_at, user , True)

    # return if message is from bot
    if message.author.bot:
        return

@bot.event
async def on_audit_log_entry_create(entry: discord.AuditLogEntry):
    match entry.action:
        case discord.AuditLogAction.member_role_update:
            if entry.changes.after.roles:
                added_by = entry.user
                roles = entry.changes.after.roles
                member = entry.target

                if member is None: return

                # check if dank manager role is added
                try:
                    data = await bot.dankSecurity.find(entry.target.guild.id)
                except:
                    data = None

                if data:
                    if data['enabled'] is False: return
                    event_manager = member.guild.get_role(data['event_manager'])
                    owner = member.guild.owner
                    if owner is None:
                        return
                    owner_list = [owner.id]
                    if 'psuedo_owner' in data.keys():
                        owner = member.guild.get_member(data['psuedo_owner'])
                        owner_list.append(owner.id)
                    if owner is None:
                        owner = member.guild.owner
                    if event_manager is not None and event_manager in roles and member.id not in data['whitelist'] and added_by.id not in owner_list: 
                        try:
                            await member.remove_roles(member.guild.get_role(data['event_manager']), reason="Member is not a authorized Dank Manager.")
                        except:
                            pass
                        role = None
                        if data['quarantine'] is not None:					
                            role = member.guild.get_role(data['quarantine'])
                        try:
                            await quarantineUser(bot, member, role, f"{member.name}(ID: {member.id}) has made an unauthorized attempt to get Dank Manager role.")	
                            if added_by.id not in owner_list:								
                                await quarantineUser(bot, added_by, role, f"{added_by.name}(ID: {added_by.id}) has made an unauthorized attempt to give Dank Manager role to {member.name} (ID: {member.id}).")					
                        except:
                            pass
                        
                        securityLog = bot.get_channel(1089973828215644241)
                        if 'logs_channel' in data.keys():
                            loggingChannel = bot.get_channel(data['logs_channel'])
                        else:
                            loggingChannel = None
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
                            if owner.id != member.guild.owner.id:
                                await owner.send(embed = embed)
                        except:
                            pass
                        if loggingChannel is not None:
                            embed = discord.Embed(
                                title = f"Security Breach!",
                                description=
                                f"` - `   **Added to:** {member.mention}\n"
                                f"` - `   **Added by:** {added_by.mention}\n"
                                f"` - `   {added_by.mention} tried to add {role.mention} to {member.mention}\n",
                                color=discord.Color.random()
                            )
                            await loggingChannel.send(embed=embed)

@bot.event
async def on_guild_join(guild: discord.Guild):
    channel = bot.get_channel(1145314908599222342)
    await channel.send(
        f"## ★｡ﾟ☆ﾟ Joined {guild.name.title()}☆ﾟ｡★\n"
        f'- **ID:** {guild.id}\n'
        f'- **Owner:** {guild.owner.mention} (ID: `{guild.owner.id}`)\n'
        f'- **Members:** {guild.member_count}\n'
        f'- **Created At:** <t:{int(guild.created_at.timestamp())}>\n'
        f'- **Joined At:** <t:{int(datetime.datetime.now(pytz.utc).timestamp())}>\n'
          f'- **Bot is in:** {len(bot.guilds)} guilds.\n'
        f'## ☆ﾟ｡★｡ﾟ☆ﾟ｡★｡ﾟ☆ﾟ｡★｡ﾟ☆ﾟ｡ﾟ☆ﾟ｡★｡ﾟ☆ﾟ\n**\n**',
        allowed_mentions=discord.AllowedMentions.none()
    )

@bot.event
async def on_guild_remove(guild: discord.Guild):
    channel = bot.get_channel(1145314908599222342)
    await channel.send(
        f"## ★｡ﾟ☆ﾟ Left {guild.name.title()}☆ﾟ｡★\n"
        f'- **ID:** {guild.id}\n'
        f'- **Owner:** {guild.owner.mention} (ID: `{guild.owner.id}`)\n'
        f'- **Members:** {guild.member_count}\n'
        f'- **Created At:** <t:{int(guild.created_at.timestamp())}>\n'
        f'- **Left At:** <t:{int(datetime.datetime.now(pytz.utc).timestamp())}>\n'
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
    load_dotenv()
    bot.botToken = os.environ.get("BOT_TOKEN")
    bot.connection_url = os.environ.get("MongoConnectionUrl")
    bot.amari = os.environ.get("amari")
    bot.dankHelper = os.environ.get("dankHelper")

# fetching assets
if os.path.exists("./utils/assets/colors.json"):
    with open("./utils/assets/colors.json") as file_data:
        bot.color = json.load(file_data)
        for color in bot.color:
            bot.color[color] = discord.Color(literal_eval(bot.color[color]))

bot.run(bot.botToken)