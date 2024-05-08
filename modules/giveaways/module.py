import asyncio
import re
import discord
import datetime
from discord.ext import commands, tasks
from discord import app_commands, Interaction

import random
from typing import List, Dict
from amari import AmariClient
import discord.http

from .db import Giveaways_Backend, GiveawayConfig, GiveawayData
from .views import Giveaway, GiveawayConfigView
from utils.transformers import TimeConverter, MutipleRole
from utils.convertor import DMCConverter
from utils.embeds import get_formated_embed, get_formated_field

class Giveaways(commands.GroupCog, name="g"):
	def __init__(self, bot):
		self.bot = bot
		self.backend = Giveaways_Backend(bot)
		self.bot.giveaway = self.backend #type: ignore
		self.giveaway_loop.start()
		self.giveaway_in_prosses = []
		self.giveaway_task_progress = False

	async def item_autocomplete(self, interaction: discord.Interaction, string: str) -> List[app_commands.Choice[str]]:
		choices = []
		for item in self.bot.dank_items_cache.keys():
			if string.lower() in item.lower():
				choices.append(app_commands.Choice(name=item, value=item))
		if len(choices) == 0:
			return [
				app_commands.Choice(name=item, value=item)
				for item in self.bot.dank_items_cache.keys() #type: ignore
			]
		else:
			return choices[:24]
		
	@tasks.loop(seconds=60)
	async def giveaway_loop(self):
		if self.giveaway_task_progress == True:
			return
		self.giveaway_task_progress = True
		now = datetime.datetime.utcnow()
		giveaways: Dict[int, GiveawayData] = {giveaway['_id']: giveaway for giveaway in await self.backend.giveaways.get_all()}
		for giveaway in giveaways.values():
			try:
				if giveaway["end_time"] <= now:
					if giveaway["_id"] in self.giveaway_in_prosses:
						continue
					if giveaway["ended"] == True:
						if giveaway['delete_at'] and giveaway['delete_at'] <= now:
							await self.backend.giveaways.delete(giveaway)

					self.bot.dispatch("giveaway_end", giveaway, await self.backend.get_config(giveaway['guild']))
					self.giveaway_in_prosses.append(giveaway["_id"])
					if giveaway['_id'] in self.backend.giveaways_cache.keys():
						del self.backend.giveaways_cache[giveaway["_id"]]
				else:
					# get how many seconds are left for the giveaway to end
					seconds_left = (giveaway["end_time"] - now).total_seconds()
					if seconds_left < 100:
						self.bot.dispatch("giveaway_end", giveaway, await self.backend.get_config(giveaway['guild']), seconds_left)
						self.giveaway_in_prosses.append(giveaway["_id"])

			except:
				pass
			self.giveaway_task_progress = False

		self.giveaway_task_progress = False

	@giveaway_loop.before_loop
	async def before_giveaway_loop(self):
		await self.bot.wait_until_ready()

	@commands.Cog.listener()
	async def on_giveaway_end(self, giveaway: GiveawayData, config: GiveawayConfig, sleep_time: int=None):
		if sleep_time != None:
			await asyncio.sleep(sleep_time)
			giveaway = await self.backend.giveaways.find(giveaway['_id'])
	
		guild: discord.Guild = self.bot.get_guild(giveaway['guild'])
		if not guild:
			try:
				guild = await self.bot.fetch_guild(giveaway['guild'])
			except discord.HTTPException:
				await self.backend.giveaways.delete(giveaway)
				if giveaway['_id'] in self.giveaway_in_prosses:
					self.giveaway_in_prosses.remove(giveaway['_id'])
				return
		channel: discord.TextChannel = guild.get_channel(giveaway['channel'])
		host: discord.Member = guild.get_member(giveaway['host'])

		view = Giveaway()
		for child in view.children:
			child.disabled = True
			if child.custom_id == "giveaway:Entries":
				child.label = len(giveaway['entries'].keys())

		try:
			gaw_message = await channel.fetch_message(giveaway['_id'])
		except discord.HTTPException:
			await self.backend.giveaways.delete(giveaway)
			if giveaway['_id'] in self.giveaway_in_prosses:
				self.giveaway_in_prosses.remove(giveaway['_id'])
			return
		
		if giveaway['ended'] == True:
			if giveaway['delete_at'] is not None and giveaway['delete_at'] <= datetime.datetime.utcnow():
				await self.backend.giveaways.delete(giveaway)
			return

		if not len(giveaway['entries'].keys()) >= giveaway['winners']:

			embed = gaw_message.embeds[0]
			embed.description  = "Could not determine a winner!" + "\n" + embed.description

			await gaw_message.edit(embed=embed, view=view, content="Giveaway Ended")
			end_emd = discord.Embed(title="Giveaway Ended", description="Could not determine a winner!", color=discord.Color.red())
			await gaw_message.reply(embed=end_emd, view=None)

			await self.backend.giveaways.delete(giveaway)
			if giveaway['_id'] in self.giveaway_in_prosses:
				self.giveaway_in_prosses.remove(giveaway['_id'])
			return
		else:
			entries: List[int] = []
			for key, value in giveaway['entries'].items():
				if int(key) in entries: continue
				entries.extend([int(key)] * value)
			
			winners = []
			while len(winners) != giveaway['winners']:
				winner = random.choice(entries)
				winner = guild.get_member(winner)
				if winner is None: continue
				if winner not in winners:
					winners.append(winner)

			embed = gaw_message.embeds[0]
			for field in embed.fields:
				if field.name == "Winners":
					embed.remove_field(embed.fields.index(field))
			embed.insert_field_at(0, name="Winners", value="\n".join([winner.mention for winner in winners]))
			await gaw_message.edit(embed=embed, view=view, content="Giveaway Ended")

			end_emd = discord.Embed(title=config['messages']['end']['title'], description=config['messages']['end']['description'], color=config['messages']['end']['color'])
			host_dm = discord.Embed(title=config['messages']['host']['title'], description=config['messages']['host']['description'], color=config['messages']['host']['color'])
			dm_emd = discord.Embed(title=config['messages']['dm']['title'], description=config['messages']['dm']['description'], color=config['messages']['dm']['color'])

			if giveaway['dank']:
				if giveaway['item']:
					prize = f"{giveaway['prize']}x {giveaway['item']}"
				else:
					prize = f"⏣ {giveaway['prize']:,}"
			else:
				prize = giveaway['prize']

			guild_name = guild.name
			if giveaway['donor']:
				donor = guild.get_member(giveaway['donor'])
				if donor:
					donor_name = donor.mention
			else:
				donor_name = host.mention
			winners_mention = ",".join([winner.mention for winner in winners])

			end_emd.title = end_emd.title.format(prize=prize, winner=winners_mention, guild=guild_name, donor=donor_name)
			end_emd.description = end_emd.description.format(prize=prize, winner=winners_mention, guild=guild_name, donor=donor_name)

			host_dm.title = host_dm.title.format(prize=prize)
			host_dm.description = host_dm.description.format(prize=prize, winner=winners_mention, guild=guild_name, donor=donor_name)

			dm_emd.title = dm_emd.title.format(prize=prize)
			dm_emd.description = dm_emd.description.format(prize=prize, winner=winners_mention, guild=guild_name, donor=donor_name)

			await gaw_message.reply(embed=end_emd, view=None)
			
			host = guild.get_member(giveaway['host'])
			if host:
				try:
					await host.send(embed=host_dm)
				except discord.Forbidden:
					pass
			payout_config = await self.bot.payouts.get_config(guild_id=guild.id, new=True)
			if giveaway['item']:
				item = await self.bot.dankItems.find(giveaway['item'])
			else:
				item = None
			for winner in winners:
				if isinstance(winner, discord.Member):
					if giveaway['dank'] is True:
						await self.bot.payouts.create_payout(config=payout_config, event="Giveaway", winner=winner, host=host, prize=giveaway['prize'], message=gaw_message, item=item)
					try:
						await winner.send(embed=dm_emd)
					except discord.Forbidden:
						pass
			
			giveaway['ended'] = True
			giveaway['delete_at'] = datetime.datetime.utcnow() + datetime.timedelta(days=7)
			await self.backend.giveaways.update(giveaway)
			if giveaway['_id'] in self.giveaway_in_prosses:
				self.giveaway_in_prosses.remove(giveaway['_id'])

	@commands.Cog.listener()
	async def on_ready(self):
		self.bot.add_view(Giveaway())

	@app_commands.command(name="start", description="Start a giveaway")
	@app_commands.describe(winners="Number of winners", prize="Prize of the giveaway", item="Item to giveaway", time="Duration of the giveaway",
		req_roles="Roles required to enter the giveaway", bypass_role="Roles that can bypass the giveaway", req_level="Level required to enter the giveaway",
		req_weekly="Weekly XP required to enter the giveaway", donor="Donor of the giveaway", message="Message to accompany the giveaway", dank="Dank Memer Giveaway? (Set it to True for Auto Payout Queue)",
		channel_message="Number of Messages required in specific channel to enter the giveaway")
	async def _start(self, interaction: discord.Interaction, prize: str,
					 time: app_commands.Transform[int, TimeConverter],
					 winners: app_commands.Range[int, 1, 20] = 1,
					 dank: bool=True,
					 item:str=None,
					 req_roles: app_commands.Transform[discord.Role, MutipleRole]=None, 
					 bypass_role: app_commands.Transform[discord.Role, MutipleRole]=None, 
					 req_level: app_commands.Range[int, 1, 100]=None,
					 req_weekly: app_commands.Range[int, 1, 100]=None,
					 channel_message: str=None,
					 donor: discord.Member=None,
					 message: app_commands.Range[str, 1, 250]=None,
	):
		
		await interaction.response.defer(ephemeral=True)
		config = await self.backend.get_config(interaction.guild)
		if config['enabled'] is False:
			return await interaction.followup.send("Giveaways are disabled in this server!")
		user_role = [role.id for role in interaction.user.roles]
		if not set(user_role) & set(config['manager_roles']): return await interaction.followup.send("You do not have permission to start giveaways!")
		if dank == True:
			prize = await DMCConverter().convert(interaction, prize)
			if not isinstance(prize, int):
				return await interaction.followup.send("Invalid Prize!")
		if item is not None:
			if item not in self.bot.dank_items_cache.keys():
				return await interaction.followup.send("Item you entered is not a valid item!")
			
		data: GiveawayData = {
			"channel": interaction.channel.id,
			"guild": interaction.guild.id,
			"winners": winners,
			"prize": prize,
			"item": item,
			"duration": time,
			"req_roles": [role.id for role in req_roles] if req_roles else [],
			"bypass_role": [role.id for role in bypass_role] if bypass_role else [],
			"req_level": req_level,
			"req_weekly": req_weekly,
			"entries": {},
			"start_time": datetime.datetime.utcnow(),
			"end_time": datetime.datetime.utcnow() + datetime.timedelta(seconds=time),
			"ended": False,
			"host": interaction.user.id,
			"donor": donor.id if donor else None,
			"message": message,
			"channel_messages": {},
			"dank": dank,
			"delete_at": None
		}
		if channel_message:
			channel_message = channel_message.split(" ")
			if len(channel_message) > 2: return await interaction.followup.send("Wrong format for channel message!\nFormat: [Channel] [number of messages]")
			msg_count = int(channel_message[1])
			msg_channel = interaction.guild.get_channel(int(channel_message[0][2:-1]))
			if not msg_channel: return await interaction.followup.send("Provide a valid channel for channel message!")
			data["channel_messages"]["channel"] = msg_channel.id
			data["channel_messages"]["count"] = msg_count
			data["channel_messages"]["users"] = {}
		
		embed = discord.Embed(title=f"{config['messages']['gaw']['title']}", description=f"{config['messages']['gaw']['description']}", color=config['messages']['gaw']['color'])

		if dank:
			if item:
				prize = f"{prize}x {item}"
			else:
				prize = f"⏣ {prize:,}"

		
		guild_name = interaction.guild.name
		donor_name = donor.mention if donor else interaction.user.mention
		raw_timestap = int((datetime.datetime.now() + datetime.timedelta(seconds=time)).timestamp())
		timestamp = f"<t:{raw_timestap}:R> <t:{raw_timestap}:t>"
		winners_num = winners
		embed.title = embed.title.format(prize=prize, guild=guild_name, donor=donor_name, timestamp=timestamp)
		embed.description = embed.description.format(prize=prize, guild=guild_name, donor=donor_name, timestamp=timestamp)

		if any([req_roles, bypass_role, req_level, req_weekly, channel_message]):
			value = ""
			if req_roles and bypass_role:
				value += f"**<a:tgk_blut_arrow:1236738254024474776> Roles:**\n<:nat_reply:1011501024625827911>  Required: {', '.join([role.mention for role in req_roles])}\n<:nat_reply_cont:1011501118163013634> Bypass: {', '.join([role.mention for role in bypass_role])}\n"
			elif req_roles and not bypass_role:
				value += f"**<a:tgk_blut_arrow:1236738254024474776> Roles:**\n<:nat_reply_cont:1011501118163013634> Required: {', '.join([role.mention for role in req_roles])}\n"
			elif bypass_role and not req_roles:
				value += f"**<a:tgk_blut_arrow:1236738254024474776> Roles:**\n<:nat_reply_cont:1011501118163013634> Bypass: {', '.join([role.mention for role in bypass_role])}\n"

			if req_level and req_weekly:
				value += f"**<a:tgk_blut_arrow:1236738254024474776> Amari Required:**\n<:nat_reply:1011501024625827911>  Level: {req_level}\n<:nat_reply_cont:1011501118163013634> Weekly XP: {req_weekly}\n"
			elif req_level and not req_weekly:
				value += f"**<a:tgk_blut_arrow:1236738254024474776> Amari Required:**\n<:nat_reply_cont:1011501118163013634> Level: {req_level}\n"
			elif req_weekly and not req_level:
				value += f"**<a:tgk_blut_arrow:1236738254024474776> Amari Required:**\n<:nat_reply_cont:1011501118163013634> Weekly XP: {req_weekly}\n"

			if channel_message:
				value += f"<a:tgk_blut_arrow:1236738254024474776> Required Message Count: {data['channel_messages']['count']}\n<:nat_reply:1011501024625827911>  Channel: <#{data['channel_messages']['channel']}>\n<:nat_reply_cont:1011501118163013634> Cooldown: 8 seconds\n"                
			embed.add_field(name="Requirements", value=value, inline=False)
		
		embed.set_footer(text=f"Hosted by {interaction.user.display_name} | Winners: {winners}")

		await interaction.followup.send(content="Giveaway started!")
		gaw_message = await interaction.channel.send(embed=embed, view=Giveaway(), content="<a:tgk_tadaa:806631994770849843> **GIVEAWAY STARTED** <a:tgk_tadaa:806631994770849843>")
		if message and interaction.guild.me.guild_permissions.manage_webhooks:
			host_webhook = None
			for webhook in await interaction.channel.webhooks():
				if webhook.user.id == self.bot.user.id:
					host_webhook = webhook
					break
			if not host_webhook:
				pfp = await self.bot.user.avatar.read()
				host_webhook = await interaction.channel.create_webhook(name="Giveaway Host", avatar=pfp)
			
			author = donor if donor else interaction.user
			await host_webhook.send(content=message, username=author.display_name, avatar_url=author.avatar.url if author.avatar else author.default_avatar, allowed_mentions=discord.AllowedMentions.none())

		data['_id'] = gaw_message.id
		await self.backend.giveaways.insert(data)
		self.backend.giveaways_cache[gaw_message.id] = data
		self.bot.dispatch("giveaway_host", data)

	@app_commands.command(name="reroll", description="Reroll a giveaway Note: Reroll will not Auto Payout Queue Giveaways")
	@app_commands.describe(
		message="Message to accompany the reroll",
		winners="Numbers of winners to reroll"
	)
	@app_commands.rename(message="message_id")
	async def _reroll(self, interaction: discord.Interaction, message: str, winners: app_commands.Range[int, 1, 10]=1):
		config = await self.backend.get_config(interaction.guild)
		if not config:
			return await interaction.followup.send("Giveaways are not enabled in this server!", ephemeral=True)

		user_role = [role.id for role in interaction.user.roles]
		if not set(user_role) & set(config['manager_roles']): return await interaction.response.send_message("You do not have permission to start giveaways!", ephemeral=True)

		try:
			message = await interaction.channel.fetch_message(int(message))
		except:
			return await interaction.response.send_message("Invalid message ID!", ephemeral=True)
		
		if message.author.id != self.bot.user.id or "Giveaway" not in message.content:
			return await interaction.response.send_message("This message is not a giveaway!", ephemeral=True)
		
		giveawa_data = await self.backend.get_giveaway(message)

		if not giveawa_data: 
			return await interaction.response.send_message("This giveaway is expired and can't be rerolled!", ephemeral=True)

		if not giveawa_data: return await interaction.response.send_message("This message is not a giveaway!", ephemeral=True)
		if not giveawa_data['ended']: return await interaction.response.send_message("This giveaway has not ended!", ephemeral=True)
		giveawa_data['winners'] = winners
		giveawa_data['ended'] = False		
		self.bot.dispatch("giveaway_end", giveawa_data, config)
		await interaction.response.send_message("Giveaway rerolled successfully! Make sure to cancel the already queued payouts use `/payout search`", ephemeral=True)

	@app_commands.command(name="end", description="End a giveaway")
	@app_commands.describe(
		message="Message to accompany the end"
	)
	@app_commands.rename(message="message_id")
	async def _end(self, interaction: discord.Interaction, message: str):
		config = await self.backend.get_config(interaction.guild)
		user_role = [role.id for role in interaction.user.roles]
		if not (set(user_role) & set(config['manager_roles'])): return await interaction.response.send_message("You do not have permission to end giveaways!", ephemeral=True)
		
		try:
			message = await interaction.channel.fetch_message(int(message))
		except:
			return await interaction.response.send_message("Invalid message ID!", ephemeral=True)
		
		if message.author.id != self.bot.user.id or "Giveaway" not in message.content:
			return await interaction.response.send_message("This message is not a giveaway!", ephemeral=True)

		giveaway_data = await self.backend.get_giveaway(message)
		if not giveaway_data: 
			return await interaction.response.send_message("This giveaway Not Found!", ephemeral=True)
		if giveaway_data['ended']: return await interaction.response.send_message("This giveaway has already ended!", ephemeral=True)
		giveaway_data['end_time'] = datetime.datetime.utcnow()
		await self.backend.update_giveaway(giveaway_data)
		self.bot.dispatch("giveaway_end", giveaway_data, config)
		await interaction.response.send_message("Giveaway ended successfully!", ephemeral=True)
		try:
			self.bot.giveaway.giveaways_cache.pop(message.id)
		except Exception as e:
			raise e
		
	@commands.command(name="multiplier", description="Set the giveaway multiplier", aliases=['multi'])
	async def _multiplier(self, ctx, user: discord.Member=None):
		user = user if user else ctx.author
		config = await self.backend.get_config(ctx.guild)
		if not config: return await ctx.send("This server is not set up!")
		if len(config['multipliers'].keys()) == 0: return await ctx.send("This server does not have any multipliers!")
		user_role = [role.id for role in user.roles]
		embed = discord.Embed(color=0x2b2d31, description=f"@everyone - `1x`\n")
		embed.set_author(name=f"{user}'s Multipliers", icon_url=user.avatar.url if user.avatar else user.default_avatar)
		total = 1
		for role, multi in config['multipliers'].items():
			if int(role) in user_role:
				embed.description += f"<@&{role}> - `{multi}x`\n"
				total += multi
		embed.description += f"**Total Multiplier** - `{total}x`"
		await ctx.reply(embed=embed, allowed_mentions=discord.AllowedMentions.none())


	@commands.Cog.listener()
	async def on_message(self, message: discord.Message):
		if message.author.bot: return
		if message.guild is None: return
		user: discord.Member = message.author
		giveaways = await self.backend.get_message_giveaways(message)
		if len(giveaways) == 0: return
		for giveaway in giveaways:
			if user.id in giveaway['entries'].keys(): continue
			if giveaway['ended']: continue
			if giveaway['channel_messages']:
				if message.channel.id != giveaway['channel_messages']['channel']: continue
				if str(user.id) not in giveaway['channel_messages']['users'].keys():
					giveaway['channel_messages']['users'][str(user.id)] = {
						"count": 1,
						"last_message": datetime.datetime.utcnow()
					}
					await self.backend.giveaways.update(giveaway)
					self.backend.giveaways_cache[giveaway['_id']] = giveaway
				else:
					try:
						time_diff = (datetime.datetime.utcnow() - giveaway['channel_messages']['users'][str(user.id)]['last_message']).total_seconds()
					except TypeError:
						time_diff = 10
					if time_diff < 8:
						continue
					else:
						if giveaway['channel_messages']['users'][str(user.id)]['count'] >= giveaway['channel_messages']['count']:
							continue
						giveaway['channel_messages']['users'][str(user.id)]['count'] += 1
						giveaway['channel_messages']['users'][str(user.id)]['last_message'] = datetime.datetime.utcnow()
						await self.backend.giveaways.update(giveaway)
						self.backend.giveaways_cache[giveaway['_id']] = giveaway


	@commands.Cog.listener()
	async def on_giveaway_end_log(self, giveaway_data: dict):
		config = await self.backend.get_config(giveaway_data['guild'])
		if not config: return
		if not config['log_channel']: return
		chl = self.bot.get_channel(config['log_channel'])
		if not chl: return

		embed = discord.Embed(color=0x2b2d31,description="", title="Giveaway Ended", timestamp=datetime.datetime.now())
		embed.add_field(name="Host", value=giveaway_data['host'].mention)
		embed.add_field(name="Channel", value=giveaway_data['channel'].mention)
		embed.add_field(name="Number of Winners", value=giveaway_data['winner'])
		embed.add_field(name="Winners", value="\n".join([winner.mention for winner in giveaway_data['winners']] if giveaway_data['winners'] else ["`None`"]))
		if giveaway_data['item']:
			embed.add_field(name="Item", value=giveaway_data['item'])
		if giveaway_data['prize']:
			embed.add_field(name="Prize", value=giveaway_data['prize'])
		embed.add_field(name="Participants", value=giveaway_data['participants'])
		embed.add_field(name="Message", value=f"[Click Here]({giveaway_data['message'].jump_url})")
		embed.add_field(name="Total Participants", value=giveaway_data['participants'])
		view = discord.ui.View()
		view.add_item(discord.ui.Button(label="Jump", style=discord.ButtonStyle.link, url=giveaway_data['message'].jump_url))
		await chl.send(embed=embed, view=view)
	
	@commands.Cog.listener()
	async def on_giveaway_host(self, data: dict):
		config = await self.backend.get_config(self.bot.get_guild(data['guild']))
		if not config: return
		if not config['log_channel']: return
		chl = self.bot.get_channel(config['log_channel'])
		if not chl: return

		embed = discord.Embed(color=0x2b2d31,description="", title="Giveaway Hosted", timestamp=datetime.datetime.now())
		embed.add_field(name="Host", value=f"<@{data['host']}>")
		embed.add_field(name="Channel", value=f"<#{data['channel']}>")
		
		embed.add_field(name="Winners", value=data['winners'])
		if data['dank'] == True:
			if data['item']:
				embed.add_field(name="Prize", value=f"{data['prize']}x {data['item']}")
			else:
				embed.add_field(name="Prize", value=f"{data['prize']:,}")
		else:
			embed.add_field(name="Prize", value=f"{data['prize']}")
		embed.add_field(name="Link", value=f"[Click Here](https://discord.com/channels/{data['guild']}/{data['channel']}/{data['_id']})")
		embed.add_field(name="Ends At", value=data['end_time'].strftime("%d/%m/%Y %H:%M:%S"))
		await chl.send(embed=embed)


async def setup(bot):
	await bot.add_cog(Giveaways(bot))
