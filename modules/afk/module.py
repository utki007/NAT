import discord
from discord.ext import commands
from discord import app_commands, Interaction

from utils.db import Document

import datetime
from typing import TypedDict, List
from traceback import format_exception
from io import BytesIO

from utils.embeds import get_error_embed, get_invisible_embed, get_warning_embed

class PingData(TypedDict):
	id: int
	message: str
	jump_url: str
	pinged_at: datetime.datetime
	channel_id: int
	guild_id: int


class AFKData(TypedDict):
	user_id: int
	guild_id: int
	reason: str
	last_nickname: str
	pings: List
	afk_at: datetime.datetime
	ignored_channels: List[PingData]
	afk: bool
	summary: bool

class AFKConfig(TypedDict):
	_id: int
	enabled: bool
	allowed_roles: List[int]


@app_commands.guild_only()
class AFK(commands.GroupCog, name="afk", description="Away from Keyboard commands"):
	def __init__(self, bot: commands.Bot):
		self.bot = bot
		self.db = self.bot.mongo["AFK"]
		self.config = Document(self.db, "config", AFKConfig)
		self.afk = Document(self.db, "afk", AFKData)
		self.bot.afk_config = self.config
		self.bot.afk_users  = self.afk
		self.afk_cache = {}

	async def interaction_check(self, interaction: Interaction) -> bool:
		if interaction.guild is None: return False
		config = await self.config.find({"_id": interaction.guild.id})
		if not config:
			embed = await get_error_embed("AFK commands are not configured for this server")
			embed.title = "AFK Setup Issue"
			embed.description = "AFK commands are not configured for this server, please ask an admin+ to configure it"
			return await interaction.response.send_message(embed=embed, ephemeral=True)
			
		if config['enabled'] == False: 
			embed = await get_warning_embed("AFK commands are disabled for this server")
			embed.title = "AFK Disabled"
			embed.description = "AFK commands are disabled for this server, please ask an admin+ to enable it"
			await interaction.response.send_message(embed=embed, ephemeral=True)
			return False
		if interaction.user == interaction.guild.owner: return True
		if interaction.user.id in self.bot.owner_ids: return True
		user_roles = [role.id for role in interaction.user.roles]
		if (set(user_roles) & set(config['allowed_roles'])): 
			return True
		else: 
			embed = await get_warning_embed("You don't have permission to use this command")
			await interaction.response.send_message(embed=embed, ephemeral=True)
			return False

	@commands.Cog.listener()
	async def on_ready(self):
		current_afks = await self.afk.find_many_by_custom({"afk": True})
		for afk in current_afks:
			if afk['guild_id'] not in self.afk_cache:
				self.afk_cache[afk['guild_id']] = {}
			self.afk_cache[afk['guild_id']][afk['user_id']] = afk

	@commands.Cog.listener()
	async def on_message(self, message: discord.Message):
		if message.guild is None: return
		if message.author.bot: return
		if message.guild.id not in self.afk_cache.keys(): return
		if message.guild.id in self.afk_cache.keys():
			already_responsed_users = []
			for user in message.mentions:
				if user.id in self.afk_cache[message.guild.id].keys() and user.id != message.author.id and user.id not in already_responsed_users:
					self.bot.dispatch("afk_ping", message, user)
					already_responsed_users.append(user.id)
					continue
				
				if message.reference and isinstance(message.reference.resolved, discord.Message) and message.reference.resolved.author.id == user.id:
					self.bot.dispatch("afk_ping", message, user)
					already_responsed_users.append(user.id)
					continue
			
		if message.author.id in self.afk_cache[message.guild.id].keys():
			self.bot.dispatch("afk_return", message)

	@commands.Cog.listener()
	async def on_afk_ping(self, message: discord.Message, user: discord.User):
		try:user_data = self.afk_cache[message.guild.id][user.id]
		except KeyError: return
		if message.channel.id in user_data['ignored_channels']:
			return
		if user_data['summary']:
			user_data['pings'].append({
				"id": message.author.id,
				"message": message.content,
				"jump_url": message.jump_url,
				"pinged_at": datetime.datetime.now(),
				"channel_id": message.channel.id,
				"guild_id": message.guild.id
			})
		if len(user_data['pings']) > 10:
			while len(user_data['pings']) > 10:
				user_data['pings'].pop(0)
		await self.afk.update(user_data)
		try:
			await message.reply(content=f"`{user_data['last_nickname']}` is AFK {':'+ user_data['reason'] if user_data['reason'] else ''}", delete_after=10, allowed_mentions=discord.AllowedMentions.none(), mention_author=True)
		except discord.HTTPException:
			await message.channel.send(content=f"`{user_data['last_nickname']}` is AFK {':'+ user_data['reason'] if user_data['reason'] else ''}", delete_after=10, allowed_mentions=discord.AllowedMentions.none())
		except: pass

	@commands.Cog.listener()
	async def on_afk_return(self, message: discord.Message):
		try:
			user_data = self.afk_cache[message.guild.id][message.author.id]
			del self.afk_cache[message.guild.id][message.author.id]
		except KeyError: return
		
		guild = message.guild
		if user_data is None: 
			if "[AFK]" in message.author.display_name:
				try: await message.author.edit(nick=message.author.display_name.replace("[AFK]", ""))
				except: pass
			return
		
		if len(user_data['pings']) != 0 and user_data['summary'] != False:
			embeds = []
			for index, msg in enumerate(user_data['pings']):
				user = guild.get_member(msg['id'])
				if not user: user = await self.bot.fetch_user(msg['id'])
				content = msg['message']
				jump_url = msg['jump_url']
				channel = guild.get_channel(msg['channel_id'])
				channel_name = channel.name if channel else "Unknown Channel"
				embed = discord.Embed(color=0x2b2d31)
				embed.set_author(name = f'{user.display_name if user.display_name != None else user.display_name}', icon_url = user.avatar.url if user.avatar else user.default_avatar)
				embed.description = f"<a:tgk_redSparkle:1072168821797965926> [`You were pinged in #{channel_name}.`]({jump_url})\n"
				embed.description += f"<a:tgk_redSparkle:1072168821797965926> **Pinged at:** <t:{int(msg['pinged_at'].timestamp())}> (<t:{int(msg['pinged_at'].timestamp())}:R>) \n"
				embed.description += f"<a:tgk_redSparkle:1072168821797965926> **Message:** {content}"
				embed.set_footer(text = f"Pings you received while you were AFK at {message.guild.name}", icon_url=guild.icon.url if guild.icon else None)
				embeds.append(embed)

			try:
				await message.author.send(embeds=embeds)
			except discord.Forbidden:
				embed = await get_error_embed("Unable to send DMs to you, your DMs are closed")
				await message.reply(embed=embed)

		try:
			user_data['afk'] = False
			user_data['reason'] = None
			user_data['afk_at'] = None
			user_data['last_nickname'] = None
			user_data['pings'] = []			
			await self.afk.update(user_data)
			await message.author.edit(nick=user_data['last_nickname'])
		except: pass
		
		embed = await get_invisible_embed(f"Welcome back! Your AFK status has been removed!")
		# embed.title = "AFK Status Removed"
		embed.description = "Welcome back! Your AFK status has been removed!"
		await message.reply(embed = embed, delete_after=10)

	@app_commands.command(name="set", description="Set your AFK status")
	async def set_afk(self, interaction: Interaction, msg: str = None):
		if msg:
			if len(msg.split(" ")) > 30:
				embed = await get_error_embed("AFK message is too long! (max 30 words)")
				return await interaction.response.send_message(embed=embed, ephemeral=True)
			if len(msg) > 2000:
				embed = await get_error_embed("AFK message is too long! (max 2000 characters)")
				return await interaction.response.send_message(embed=embed, ephemeral=True)
		user_data = await self.afk.find({"user_id": interaction.user.id, "guild_id": interaction.guild.id})
		first_time = False
		if not user_data:
			user_data = {
				"user_id": interaction.user.id,
				"guild_id": interaction.guild.id,
				"reason": msg,
				"last_nickname": interaction.user.nick,
				"pings": [],
				"afk_at": datetime.datetime.utcnow(),
				"ignored_channels": [],
				"afk": False,
				"summary": True
			}
			await self.afk.insert(user_data)
			first_time = True
		
		if user_data['afk']:
			await interaction.response.send_message("You are already AFK!", ephemeral=True)
			return
		user_data['afk'] = True
		user_data['reason'] = msg
		user_data['afk_at'] = datetime.datetime.utcnow()
		user_data['last_nickname'] = interaction.user.nick if interaction.user.nick else interaction.user.display_name

		await self.afk.update(user_data)

		await interaction.response.send_message(f"Set your AFK status to: {msg}", ephemeral=True)
		if interaction.guild.id not in self.afk_cache:
			self.afk_cache[interaction.guild.id] = {}
		self.afk_cache[interaction.guild.id][interaction.user.id] = user_data
		if first_time:
			embed = await get_invisible_embed(f"Get notified when someone pings you while you are AFK, use `/settings` to get a summary of pings")
			embed.title = "DM Notifications"
			embed.description = "Get notified when someone pings you while you are AFK, use </settings:1196688324207853590> to get a summary of last 10 pings"
			try:
				await interaction.user.send(embed=embed)
			except discord.Forbidden:
				await interaction.followup.send(embed=embed, ephemeral=True)

	@app_commands.command(name="unset", description="Unset your AFK status")
	@app_commands.checks.has_permissions(administrator=True)
	@app_commands.describe(user="User to unset AFK status")
	async def unset_afk(self, interaction: Interaction, user: discord.Member):
		user_data = await self.afk.find({"user_id": user.id, "guild_id": interaction.guild.id})
		if not user_data:
			await interaction.response.send_message("User is not AFK!", ephemeral=True)
			return
		
		await self.afk.update({"user_id": user.id, "guild_id": interaction.guild.id}, {"$set": {"afk": False, "reason": None, "afk_at": None, "last_nickname": None, "pings": []}})
		if interaction.guild.id not in self.afk_cache:
			self.afk_cache[interaction.guild.id] = {}
		try:
			del self.afk_cache[interaction.guild.id][user.id]
		except KeyError:
			pass
		
		await interaction.response.send_message(f"Unset {user.mention}'s AFK status", ephemeral=True)
		
	@app_commands.command(name="ignore", description="Ignore a channel")
	@app_commands.describe(channel="Channel to ignore/unignore")
	async def ignore_channel(self, interaction: Interaction, channel: discord.TextChannel):
		user_data = await self.afk.find({"user_id": interaction.user.id, "guild_id": interaction.guild.id})
		first_time = False
		if not user_data:
			user_data = {
				"user_id": interaction.user.id,
				"guild_id": interaction.guild.id,
				"reason": None,
				"last_nickname": interaction.user.nick,
				"pings": [],
				"afk_at": None,
				"ignored_channels": [],
				"afk": False,
				"summary": True
			}
			first_time = True
		
		if channel.id in user_data['ignored_channels']:
			user_data.remove(channel.id)
			await interaction.response.send_message(embed=discord.Embed(description=f"<:tgk_active:1082676793342951475> | Unignored {channel.mention}", color=discord.Color.green()), ephemeral=True)
		else:
			user_data.append(channel.id)
			await interaction.response.send_message(embed=discord.Embed(description=f"<:tgk_active:1082676793342951475> | Ignored {channel.mention}", color=discord.Color.green()), ephemeral=True)
		if first_time:
			embed = await get_invisible_embed(f"Get notified when someone pings you while you are AFK, use `/settings` to get a summary of pings")
			embed.title = "DM Notifications"
			embed.description = "Get notified when someone pings you while you are AFK, use </settings:1196688324207853590> to get a summary of last 10 pings"
			try:
				await interaction.user.send(embed=embed)
			except discord.Forbidden:
				await interaction.followup.send(embed=embed, ephemeral=True)
		if user_data['afk']:
			await interaction.followup.send(content="You are currently AFK, this change will take effect next time you go AFK", ephemeral=True)

	async def cog_app_command_error(self, interaction: discord.Interaction[discord.Client], error: app_commands.AppCommandError) -> None:
		error_traceback = "".join(format_exception(type(error), error, error.__traceback__, 4))
		buffer = BytesIO(error_traceback.encode('utf-8'))
		file = discord.File(buffer, filename=f"Error-{interaction.command.name}.log")
		buffer.close()
		chl = interaction.client.get_channel(1130057933468745849)
		await chl.send(file=file, content="<@488614633670967307>", silent=True)

async def setup(bot):
	await bot.add_cog(AFK(bot))