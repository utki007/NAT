import asyncio
from io import BytesIO
import re
import traceback
import discord
import datetime
from discord import app_commands
from discord.ext import commands, tasks

import random
from typing import List, Dict
import discord.http

from .db import Giveaways_Backend, GiveawayConfig, GiveawayData, chunk
from .views import Giveaway, GiveawayConfigView
from utils.transformers import TimeConverter, MutipleRole
from utils.convertor import DMCConverter
from utils.embeds import get_formated_embed, get_formated_field, get_error_embed
from utils.views.paginator import Paginator

@app_commands.guild_only()
class Giveaways(commands.GroupCog, name="g", description="Create Custom Giveaways"):
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
		now = datetime.datetime.utcnow()
		giveaways: Dict[int, GiveawayData] = {giveaway['_id']: giveaway for giveaway in await self.backend.giveaways.find_many_by_custom({"ended": False})}
		for key, value in giveaways.items():
			timediff = int((value['end_time'] - now).total_seconds())
			if timediff <= 0:
				if key not in self.giveaway_in_prosses:
					self.giveaway_in_prosses.append(key)
					self.bot.dispatch("giveaway_end", value, await self.backend.get_config(self.bot.get_guild(value['guild'])))
			elif timediff <= 60:
				if key not in self.giveaway_in_prosses:
					self.giveaway_in_prosses.append(key)
					self.bot.dispatch("giveaway_end", giveaway=value, config=await self.backend.get_config(self.bot.get_guild(value['guild'])), sleep_time=timediff)
		
		ended_gaw: Dict[int, GiveawayData] = {giveaway['_id']: giveaway for giveaway in await self.backend.giveaways.find_many_by_custom({"ended": True})}
		for key, value in ended_gaw.items():
			if value['delete_at'] is not None and value['delete_at'] <= now:
				await self.backend.giveaways.delete(value)
				if key in self.giveaway_in_prosses:
					self.giveaway_in_prosses.remove(key)

	@giveaway_loop.before_loop
	async def before_giveaway_loop(self):
		await self.bot.wait_until_ready()

	@commands.Cog.listener()
	async def on_giveaway_end(self, giveaway: GiveawayData, config: GiveawayConfig, sleep_time: int=None, reroll=False):
		if sleep_time != None:
			await asyncio.sleep(sleep_time)
			giveaway = await self.backend.giveaways.find(giveaway['_id'])
		
		if not giveaway: return
	
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
		if not channel:
			await self.backend.giveaways.delete(giveaway)
			if giveaway['_id'] in self.giveaway_in_prosses: self.giveaway_in_prosses.remove(giveaway['_id'])
			return
		
		host: discord.Member = guild.get_member(giveaway['host'])
		view = Giveaway()
		for child in view.children:
			child.disabled = True
			if child.custom_id == "giveaway:Entries":
				child.label = len(giveaway['entries'].keys()) if len(giveaway['entries'].keys()) > 0 else None

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
		
		if "Giveaway Ended" in gaw_message.content:			
			giveaway['ended'] = True
			await self.backend.update_giveaway(gaw_message, giveaway)
			return
		
		giveaway['ended'] = True
		giveaway['delete_at'] = datetime.datetime.utcnow() + datetime.timedelta(days=7)		
		await self.backend.update_giveaway(gaw_message, giveaway)

		if not len(giveaway['entries'].keys()) >= giveaway['winners']:

			embed = gaw_message.embeds[0]
			embed.description  = "Could not determine a winner!" + "\n" + embed.description
			content = "Giveaway Ended"
			if reroll == True:
				content = "Giveaway Rerolled!"
			await gaw_message.edit(embed=embed, view=view, content=content)
			end_emd = discord.Embed(title="Giveaway Ended", description="Could not determine a winner!", color=discord.Color.red())
			await gaw_message.reply(embed=end_emd, view=None)

			await self.backend.giveaways.delete(giveaway)
			if giveaway['_id'] in self.giveaway_in_prosses:
				self.giveaway_in_prosses.remove(giveaway['_id'])
				
			host = guild.get_member(giveaway['host'])
			view = discord.ui.View()
			view.add_item(discord.ui.Button(label="Jump", style=discord.ButtonStyle.link, url=gaw_message.jump_url, emoji="<:tgk_link:1105189183523401828>"))
			if host:
				embed = discord.Embed(title="Giveaway Ended", description="Could not determine a winner!", color=discord.Color.red())
				await host.send(embed=embed, view=view)
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
				if giveaway['item']:
					prize = f"{giveaway['prize']} {giveaway['item']}"
				else:
					prize = giveaway['prize']

			guild_name = guild.name
			if giveaway['donor']:
				donor = guild.get_member(giveaway['donor'])
				if donor:
					donor_name = donor.mention
			else:
				donor_name = host.mention
			winners_mention = ""

			for winner in winners:
				winners_mention += f"{winners.index(winner)+1}. {winner.mention}\n"
			
			values = {'guild': guild_name, 'prize': prize, 'donor': donor_name, 'timestamp': f"<t:{int(giveaway['end_time'].timestamp())}:R> (<t:{int(giveaway['end_time'].timestamp())}:t>)", "winners": winners_mention}
			end_emd_title = {};end_emd_description = {};host_dm_title = {};host_dm_description = {};dm_emd_title = {};dm_emd_description = {}
			for key, value in values.items():
				if key in end_emd.title:
					end_emd_title[key] = value
				if key in end_emd.description:
					end_emd_description[key] = value
				if key in host_dm.title:
					host_dm_title[key] = value
				if key in host_dm.description:
					host_dm_description[key] = value
				if key in dm_emd.title:
					dm_emd_title[key] = value
				if key in dm_emd.description:
					dm_emd_description[key] = value




			end_emd.title = end_emd.title.format(**end_emd_title)
			end_emd.description = end_emd.description.format(**end_emd_description)

			host_dm.title = host_dm.title.format(**host_dm_title)
			host_dm.description = host_dm.description.format(**host_dm_description)

			dm_emd.title = dm_emd.title.format(**dm_emd_title)
			dm_emd.description = dm_emd.description.format(**dm_emd_description)

			payoyt_mesg = await gaw_message.reply(embed=end_emd, view=None, content=",".join([winner.mention for winner in winners]))
			
			host = guild.get_member(giveaway['host'])
			link_view = discord.ui.View()
			link_view.add_item(discord.ui.Button(label="Jump", style=discord.ButtonStyle.link, url=payoyt_mesg.jump_url, emoji="<:tgk_link:1105189183523401828>"))
			if host:
				try:
					await host.send(embed=host_dm, view=link_view)
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
						await self.bot.payouts.create_payout(config=payout_config, event="Giveaway", winner=winner, host=host, prize=giveaway['prize'], message=payoyt_mesg, item=item)
					try:
						await winner.send(embed=dm_emd, view=link_view)
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
	@app_commands.describe(winners="Number of winners", prize="Prize/Quantity of the giveaway", time="Duration of the giveaway", item="Item to giveaway",
		req_roles="Roles required to enter the giveaway", bypass_role="Roles that can bypass the giveaway", blacklist_role="Roles that are blacklisted from this giveaway", req_level="Level required to enter the giveaway",
		req_weekly="Weekly XP required to enter the giveaway", donor="Donor of the giveaway", message="Message to accompany the giveaway", dank="Dank Memer Giveaway? (Set it to True for Auto Payout Queue)",
		channel_message="Number of Messages required in specific channel (Format: [Channel] [number of messages])")
	@app_commands.autocomplete(item=item_autocomplete)
	@app_commands.rename(channel_message="message_requirement", prize="quantity", req_roles="role_requirement",req_level="level_requirement", req_weekly="weekly_xp_requirement", message = "donor_message")
	async def _start(self, interaction: discord.Interaction, 
					 winners: app_commands.Range[int, 1, 20],
					 time: app_commands.Transform[int, TimeConverter],
					 prize: str,
					 item:str=None,
					 dank: bool=True,
					 donor: discord.Member=None,
					 req_roles: app_commands.Transform[discord.Role, MutipleRole]=None, 
					 bypass_role: app_commands.Transform[discord.Role, MutipleRole]=None,
					 blacklist_role: app_commands.Transform[discord.Role, MutipleRole]=None,
					 req_level: app_commands.Range[int, 1, 100]=None,
					 req_weekly: app_commands.Range[int, 1, 100]=None,
					 channel_message: str=None,
					 message: app_commands.Range[str, 1, 250]=None,
	):
		if time < 60:
			return await interaction.response.send_message("Duration of the giveaway should be atleast 60 seconds!", ephemeral=True)

		await interaction.response.defer(thinking=True)
		config = await self.backend.get_config(interaction.guild)
		if config['enabled'] is False:
			return await interaction.followup.send("Giveaways are disabled in this server!")
		user_role = [role.id for role in interaction.user.roles]
		if not set(user_role) & set(config['manager_roles']): return await interaction.followup.send("You do not have permission to start giveaways!")
		if dank == True:
			prize = await DMCConverter().convert(interaction, prize)
			if not isinstance(prize, int):
				embed = await get_error_embed("Failed to convert prize try again using the correct format\nDank Giveaway Format:\n* (without item) quantity: 1e3\n* (with item) item: select_from_autocomplete quantity: 1")
				return await interaction.followup.send(embed=embed)
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
			"bl_roles": [role.id for role in blacklist_role] if blacklist_role else [],
			"req_level": req_level,
			"req_weekly": req_weekly,
			"entries": {},
			"banned": [],
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
		timestamp = f"<t:{raw_timestap}:R> (<t:{raw_timestap}:t>)"
		values = {'guild': guild_name, 'prize': prize, 'donor': donor_name, 'timestamp': timestamp}
		title_kewrd = {}
		description_kewrd = {}

		for key, value in values.items():
			if key in embed.title:
				title_kewrd[key] = value
			if key in embed.description:
				description_kewrd[key] = value
				
		embed.title = embed.title.format(**title_kewrd)
		embed.description = embed.description.format(**description_kewrd)

		if any([req_roles, bypass_role, blacklist_role, req_level, req_weekly, channel_message]):
			value = ""
			req_role = f"Required: {', '.join([role.mention for role in req_roles])}\n" if req_roles else None
			bypass_roles = f"Bypass: {', '.join([role.mention for role in bypass_role])}\n" if bypass_role else None
			blacklist_roles = f"Blacklist: {', '.join([role.mention for role in blacklist_role])}\n" if blacklist_role else None
			roles = [req_role, bypass_roles, blacklist_roles]
			roles = [role for role in roles if role]
			if len(roles) == 1:
				value += f"**<a:tgk_blut_arrow:1236738254024474776> Roles:**\n<:nat_reply_cont:1011501118163013634> {roles[0]}"
			elif len(roles) == 2:
				value += f"**<a:tgk_blut_arrow:1236738254024474776> Roles:**\n<:nat_reply:1011501024625827911> {roles[0]}<:nat_reply_cont:1011501118163013634> {roles[1]}"
			elif len(roles) == 3:
				value += f"**<a:tgk_blut_arrow:1236738254024474776> Roles:**\n<:nat_reply:1011501024625827911> {roles[0]}<:nat_reply:1011501024625827911> {roles[1]}<:nat_reply_cont:1011501118163013634> {roles[2]}"

			if req_level and req_weekly:
				value += f"**<a:tgk_blut_arrow:1236738254024474776> Amari Required:**\n<:nat_reply:1011501024625827911>  Level: {req_level}\n<:nat_reply_cont:1011501118163013634> Weekly XP: {req_weekly}\n"
			elif req_level and not req_weekly:
				value += f"**<a:tgk_blut_arrow:1236738254024474776> Amari Required:**\n<:nat_reply_cont:1011501118163013634> Level: {req_level}\n"
			elif req_weekly and not req_level:
				value += f"**<a:tgk_blut_arrow:1236738254024474776> Amari Required:**\n<:nat_reply_cont:1011501118163013634> Weekly XP: {req_weekly}\n"

			if channel_message:
				value += f"<a:tgk_blut_arrow:1236738254024474776> **Required Message Count:** {data['channel_messages']['count']}\n<:nat_reply:1011501024625827911>  Channel: <#{data['channel_messages']['channel']}>\n<:nat_reply_cont:1011501118163013634> Cooldown: 8 seconds\n"                
			embed.add_field(name="Requirements", value=value, inline=False)
		embed.timestamp = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(seconds=time)
		embed.set_footer(text=f"{winners}w | Ends at")

		await interaction.followup.send(embed=embed, view=Giveaway(), content="<a:tgk_tadaa:806631994770849843> **GIVEAWAY STARTED** <a:tgk_tadaa:806631994770849843>")
		gaw_message = await interaction.original_response()
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
		
		if message.author.id != self.bot.user.id or "giveaway" not in message.content.lower():
			return await interaction.response.send_message("This message is not a giveaway!", ephemeral=True)
		
		giveawa_data = await self.backend.get_giveaway(message)

		if not giveawa_data: 
			return await interaction.response.send_message("This giveaway is expired and can't be rerolled!", ephemeral=True)

		if not giveawa_data: return await interaction.response.send_message("This message is not a giveaway!", ephemeral=True)
		if not giveawa_data['ended']: return await interaction.response.send_message("This giveaway has not ended!", ephemeral=True)
		giveawa_data['winners'] = winners
		giveawa_data['ended'] = False		
		self.bot.dispatch("giveaway_end", giveaway=giveawa_data, config=config, reroll=True)
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
		
		if message.author.id != self.bot.user.id or "giveaway" not in message.content.lower():
			return await interaction.response.send_message("This message is not a giveaway!", ephemeral=True)

		giveaway_data = await self.backend.get_giveaway(message)
		if not giveaway_data: 
			return await interaction.response.send_message("This giveaway Not Found!", ephemeral=True)
		if giveaway_data['ended']: return await interaction.response.send_message("This giveaway has already ended!", ephemeral=True)
		giveaway_data['end_time'] = datetime.datetime.utcnow()
		await self.backend.update_giveaway(message=message, data=giveaway_data)
		self.bot.dispatch("giveaway_end", giveaway_data, config)
		await interaction.response.send_message("Giveaway ended successfully!", ephemeral=True)
		try:
			self.bot.giveaway.giveaways_cache.pop(message.id)
		except Exception as e:
			raise e
		
	@app_commands.command(name="cancel", description="Cancel a giveaway")
	@app_commands.describe(
		message="Message to accompany the cancel"
	)
	@app_commands.rename(message="message_id")
	async def _cancel(self, interaction: discord.Interaction, message: str):
		config = await self.backend.get_config(interaction.guild)
		user_role = [role.id for role in interaction.user.roles]

		if not (set(user_role) & set(config['manager_roles'])): return await interaction.response.send_message("You do not have permission to cancel giveaways!", ephemeral=True)

		try:
			message = await interaction.channel.fetch_message(int(message))
		except:
			return await interaction.response.send_message("Invalid message ID!", ephemeral=True)
		
		if message.author.id != self.bot.user.id or "giveaway" not in message.content.lower():
			return await interaction.response.send_message("This message is not a giveaway!", ephemeral=True)
		
		embed = message.embeds[0]
		embed.description = f"This giveaway has been cancelled by {interaction.user.mention}!"
		embed.title = None
		embed.set_footer(text="Cancelled")
		view = Giveaway()
		view.children[0].disabled = True
		view.children[1].disabled = True
		await message.edit(embed=embed, view=view, content="Giveaway Cancelled")

		await self.backend.giveaways.delete(message.id)
		if message.id in self.backend.giveaways_cache.keys():
			self.backend.giveaways_cache.pop(message.id)
		await interaction.response.send_message("Giveaway cancelled successfully!", ephemeral=True)

	@app_commands.command(name="remove-entry", description="Remove an entry from a giveaway")
	@app_commands.describe(
		message="Message to accompany the removal",
		user="User to remove"
	)
	@app_commands.rename(message="message_id")
	async def _remove_entry(self, interaction: discord.Interaction, message: str, user: discord.Member):
		config = await self.backend.get_config(interaction.guild)
		user_role = [role.id for role in interaction.user.roles]
		if not (set(user_role) & set(config['manager_roles'])): return await interaction.response.send_message("You do not have permission to remove entries!", ephemeral=True)

		try:
			message = await interaction.channel.fetch_message(int(message))
		except:
			return await interaction.response.send_message("Invalid message ID!", ephemeral=True)
		
		if message.author.id != self.bot.user.id or "giveaway" not in message.content.lower():
			return await interaction.response.send_message("This message is not a giveaway!", ephemeral=True)
		
		giveaway_data = await self.backend.get_giveaway(message)
		if not giveaway_data: 
			return await interaction.response.send_message("This giveaway Not Found!", ephemeral=True)
		if giveaway_data['ended']: return await interaction.response.send_message("This giveaway has already ended!", ephemeral=True)
		if str(user.id) not in giveaway_data['entries'].keys():
			return await interaction.response.send_message("This user is not in the giveaway!", ephemeral=True)
		
		if str(user.id) in giveaway_data['entries'].keys():
			del giveaway_data['entries'][str(user.id)]
		if giveaway_data['channel_messages'] != {} and str(user.id) in giveaway_data['channel_messages']['users'].keys():
			del giveaway_data['channel_messages']['users'][str(user.id)]
		giveaway_data['banned'].append(user.id)
		await self.backend.update_giveaway(message=message, data=giveaway_data)
		await interaction.response.send_message("Entry removed successfully!", ephemeral=True)
		view = Giveaway()
		if len(giveaway_data['entries'].keys()) == 0:
			view.children[1].disabled = True
			view.children[1].label = None
		else:
			view.children[1].label = len(giveaway_data['entries'].keys())
			view.children[1].disabled = False
		await message.edit(view=view)

	@app_commands.command(name="list", description="List all the giveaways")
	async def _list(self, interaction: discord.Interaction):
		giveaways: List[GiveawayData] = await self.backend.giveaways.find_many_by_custom({"guild": interaction.guild.id, "ended": False})
		if len(giveaways) == 0:
			return await interaction.response.send_message("No giveaways found in this server!", ephemeral=True)
		await interaction.response.defer(ephemeral=False)
		giveaways_group = list(chunk(giveaways, 5))
		pages = []
		gaw_count = 1
		for giveaways in giveaways_group:
			desc = ''
			for giveaway in giveaways:
				desc += f"**` {gaw_count}. ` {giveaway['prize']}**\n"
				desc += f"<:nat_replycont:1146496789361479741>**Ends at:** <t:{int(giveaway['end_time'].timestamp())}:R>\n"
				desc += f"<:nat_reply:1146498277068517386>**Link:** [Click Here](https://discord.com/channels/{giveaway['guild']}/{giveaway['channel']}/{giveaway['_id']})\n\n"
				gaw_count += 1
			embed = discord.Embed(title="Giveaways", description=desc, color=0x2b2d31)
			pages.append(embed)
		
		await Paginator(interaction=interaction, pages=pages, ephemeral=False).start(embeded=True, deffer=True, quick_navigation=False)

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


	async def cog_app_command_error(self, interaction: discord.Interaction[discord.Client], error: app_commands.AppCommandError) -> None:
		error_traceback = "".join(traceback.format_exception(type(error), error, error.__traceback__, 4))
		buffer = BytesIO(error_traceback.encode('utf-8'))
		file = discord.File(buffer, filename=f"Error-{interaction.command.name}.log")
		buffer.close()
		chl = interaction.client.get_channel(1130057933468745849)
		await chl.send(file=file, content="<@488614633670967307>", silent=True)

async def setup(bot):
	await bot.add_cog(Giveaways(bot))
