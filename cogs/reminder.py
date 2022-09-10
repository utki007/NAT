import asyncio
import datetime
from tabnanny import check
from typing import Literal, List
from unicodedata import name
import discord
from discord import app_commands
from discord.ext import commands, tasks
from utils.convertor import *
from utils.views.paginator import Paginator
from utils.views.confirm import Confirm
from copy import deepcopy
import enum
class RemiderType(enum.Enum):
	WORK = "work"
	NORMAL = "normal"

class Reminder(commands.GroupCog, name="reminder", description="Reminder commands"):
	def __init__(self, bot):
		self.bot = bot
		self.remindertask = self.reminder_loop.start()

	def cog_unload(self) -> None:
		self.remindertask.cancel()

	async def remider_auto_complete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
		current_remider = await self.bot.doc_remider.find_many_by_custom({'host_id': interaction.user.id, 'guild_id': interaction.guild.id})
		if len(current) == 0:
			choices = [
				app_commands.Choice(name=f"#{remider['_id']} - " + remider['about'] if len(remider) < 50 else f"{remider['about'][:50]}...", value=remider['_id'])
				for remider in current_remider
			]
		else:
			choices = [
				app_commands.Choice(name=f"#{remider['_id']} - " + remider['about'] if len(remider) < 50 else f"{remider['about'][:50]}...", value=remider['_id'])
				for remider in current_remider if current.lower() in remider['about'].lower()
			]
		return choices[:24]

	@app_commands.command(name="create", description="Create a reminder", extras={'example': '/reminder create <about> <time>'})
	@app_commands.guild_only()
	@app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
	@app_commands.describe(time="Enter time in format: 1h30m2s", about="Enter the message you want to be reminded of", recurring="How many times your reminder should repeat")
	async def reminderCreate(self, interaction:  discord.Interaction, about: str, time: str, recurring: app_commands.Range[int,2, 1000]= 1):
		try:
			time = await convert_to_time(time)
			cd = int(await calculate(time))
			end = datetime.datetime.now() + datetime.timedelta(seconds=cd)
		except:
			warning = discord.Embed(
				color=self.bot.color['danger'],
				title=f"<a:nat_warning:1010618708688912466> **|** Incorrect time format, please use `1h30m10s`")
			return await interaction.response.send_message(embed=warning, ephemeral=True)

		if cd < 30:
			warning = discord.Embed(
				color=self.bot.color['danger'],
				title=f"<a:nat_warning:1010618708688912466> **|** Time should be more than 30s")
			return await interaction.response.send_message(embed=warning, ephemeral=True)
		await interaction.response.defer()

		message = await interaction.original_response()

		counter = await self.bot.doc_remider.find("reminder")
		if counter == None:
			id = 1997
			await self.bot.doc_remider.insert({"_id": "reminder", "counter": id})
		else:
			counter["counter"] += 1
			id = counter["counter"]
			await self.bot.doc_remider.update(counter)

		reminder_data = {
			'_id': id,
			'host_id': interaction.user.id,
			'guild_id': interaction.guild.id,
			'channel_id': interaction.channel.id,
			'message_id': message.id,
			'message_link': message.jump_url,
			'about': about,
			'time': datetime.datetime.now() + datetime.timedelta(seconds=cd),
			'created_at': datetime.datetime.now(),
			'remind_in_seconds': cd,
			'type': RemiderType.NORMAL.value,
			'recurring': recurring,
			'reminded': None,
		}
		await interaction.client.doc_remider.upsert(reminder_data)

		await interaction.edit_original_response(
			content=f"Alright **{interaction.user.name}**, I'll remind you about `{about}` in **{await convert_to_human_time(cd)}**. (at <t:{int(datetime.datetime.timestamp(datetime.datetime.now() + datetime.timedelta(seconds=cd)))}>)"
			f"\nThis reminder's ID is `{reminder_data['_id']}`."
		)
		if cd < 90:
			self.bot.dispatch('reminder_end', reminder_data, True)

	@app_commands.command(name="cancel", description="Cancel a reminder by id", extras={'example': '/reminder cancel <id>'})
	@app_commands.guild_only()
	@app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
	@app_commands.describe(reminder_id = "ID of the reminder")
	@app_commands.autocomplete(reminder_id=remider_auto_complete)
	async def reminderCancel(self, interaction:  discord.Interaction, reminder_id: int):
		await interaction.response.defer(ephemeral=True)
		reminder_data = await interaction.client.doc_remider.find({'_id': reminder_id})
		if reminder_data == None:
			return await interaction.edit_original_response(content="Invalid/Expired reminder!")
		if reminder_data['host_id'] != interaction.user.id:
			return await interaction.edit_original_response(content="You are not subscribed to that reminder!")
		else:
			await interaction.client.doc_remider.delete(reminder_data)
			return await interaction.edit_original_response(content=f"You have successfully deleted **Reminder #{reminder_data['_id']}** for `{reminder_data['about']}`!")

	@app_commands.command(name="clear", description="Clears all reminders", extras={'example': '/reminder clear'})
	@app_commands.guild_only()
	@app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
	async def reminderClear(self, interaction: discord.Interaction, clear_from: Literal['current server', 'all servers']):
		await interaction.response.defer(ephemeral=False)
		if clear_from == 'current server':
			reminders = await interaction.client.doc_remider.get_all({'host_id':interaction.user.id, 'guild_id': interaction.guild.id})
			content = f"You have successfully cleared all reminders from **{interaction.guild.name}**."
			question = f"Do you wish to clear {len(reminders)} active reminders from **{interaction.guild.name}**?"
		else:
			reminders = await interaction.client.doc_remider.get_all({'host_id':interaction.user.id})
			content = "You have successfully cleared all reminders from all your servers."
			question = f"Do you wish to clear {len(reminders)} active reminders from all your servers?"
		
		if reminders == None or reminders == []:
			warning = discord.Embed(
				color=self.bot.color['danger'],
				title=f"<a:nat_cross:1010969491347357717> **|** Nothing to clear",
				description=f"You don't have any reminders to clear.")
			return await interaction.edit_original_response(embed=warning, content=None, view=None)

		# sending a confirmation dialog box
		view = Confirm(timeout=60)
		await interaction.followup.send(content=question, view=view)
		await view.wait()

		if view.value is None:
			warning = discord.Embed(
				color=self.bot.color['danger'],
				title=f"<a:nat_warning:1010618708688912466> **|** Timed out",
				description=f"I couldn't clear your reminders because you were timed out.")
			return await interaction.edit_original_response(embed=warning, content=None, view=None)
		elif view.value:
			for reminder in reminders:
				await interaction.client.doc_remider.delete(reminder)
			success_embed = discord.Embed(
					color=self.bot.color['default'],
					title=f"<a:nat_check:1010969401379536958> **|** Cleared up",
					description=content)
			return await interaction.edit_original_response(embed=success_embed, content=None, view=None)
		else:
			warning = discord.Embed(
				color=self.bot.color['danger'],
				title=f"<a:nat_cross:1010969491347357717> **|** Cancelled",
				description=f'Come back once you are sure about what you are doing.')
			return await interaction.edit_original_response(embed=warning, content=None, view=None)

	@app_commands.command(name="list", description="List of all reminders", extras={'example': '/reminder list [current server|all servers]'})
	@app_commands.guild_only()
	@app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
	async def reminderList(self, interaction: discord.Interaction, list_from: Literal['current server', 'all servers']):
		# await interaction.response.defer()
		if list_from == 'current server':
			reminders = await interaction.client.doc_remider.get_all({'host_id':interaction.user.id, 'guild_id': interaction.guild.id})
			title = "Your reminders!"
			desc = []
			for index, reminder in enumerate(reminders):
				content = f"` {index+1} ` **Reminder #{reminder['_id']}**"
				content += f'\n<:nat_reply:1011501024625827911> **Server:** {interaction.guild.name.title()}'
				content += f'\n<:nat_reply:1011501024625827911> **On:** <t:{int(datetime.datetime.timestamp(reminder["time"]))}:d> <t:{int(datetime.datetime.timestamp(reminder["time"]))}:t>'
				content += f'\n<:nat_reply_cont:1011501118163013634> **About:** {reminder["about"]}\n\n'
				desc.append(content)
		else:
			reminders = await interaction.client.doc_remider.get_all({'host_id':interaction.user.id})
			title = "You reminders across discord!"
			desc = []
			for index, reminder in enumerate(reminders):
				content = f"` {index+1} ` **Reminder #{reminder['_id']}**"
				content += f'\n<:nat_reply:1011501024625827911> **Server:** {interaction.guild.name.title()}'
				content += f'\n<:nat_reply:1011501024625827911> **On:** <t:{int(datetime.datetime.timestamp(reminder["time"]))}:d> <t:{int(datetime.datetime.timestamp(reminder["time"]))}:t>'
				content += f'\n<:nat_reply_cont:1011501118163013634> **About:** {reminder["about"]}\n\n'
				desc.append(content)
		if reminders == None or reminders == [] or len(desc) < 1:
			return await interaction.response.send_message(content=f"You don't have any reminders set.")
		
		pages = []
		for i in range(0,len(desc),3): 
			embed = discord.Embed(
				color=self.bot.color['default'],
				title=title,
				description=" ".join([desc for desc in desc[i:i + 3]])
			)
			embed.set_footer(text=f'You have {len(reminders)} active reminders!')
			pages.append(embed)
		custom_button = [
			# discord.ui.Button(label="<<", style=discord.ButtonStyle.gray),
			discord.ui.Button(label="Previous", style=discord.ButtonStyle.gray),
			discord.ui.Button(label="Stop", style=discord.ButtonStyle.gray),
			discord.ui.Button(label="Next", style=discord.ButtonStyle.gray),
			# discord.ui.Button(label=">>", style=discord.ButtonStyle.gray)
		]
		await Paginator(interaction, pages, custom_button).start(embeded=True, quick_navigation=False)
	
	@app_commands.command(name="subscibe", description="Creates a copy of a reminder", extras={'example': '/reminder subscibe <reminder id>'})
	@app_commands.guild_only()
	@app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
	async def reminderSubscibe(self, interaction: discord.Interaction, reminder_id: int):
		await interaction.response.defer()
		reminder_data = await interaction.client.doc_remider.find({'_id': reminder_id})
		if reminder_data == None:
			return await interaction.edit_original_response(content="Invalid/Expired reminder!")
		if reminder_data['host_id'] != interaction.user.id:
			counter = await self.bot.doc_remider.find("reminder")
			if counter == None:
				id = 1997
				await self.bot.doc_remider.insert({"_id": "reminder", "counter": id})
			else:
				counter["counter"] += 1
				id = counter["counter"]
				await self.bot.doc_remider.update(counter)

			message = await interaction.original_response()
			cd = int((reminder_data['time'] - datetime.datetime.now()).total_seconds())
			about = reminder_data['about']
			reminder_data = {
				'_id': id,
				'host_id': interaction.user.id,
				'guild_id': interaction.guild.id,
				'channel_id': interaction.channel.id,
				'message_id': message.id,
				'message_link': message.jump_url,
				'about': reminder_data['about'],
				'time': reminder_data['time'],
				'created_at': datetime.datetime.now(),
				'remind_in_seconds': cd,
				'recurring': 1,
				'reminded': None,
				'type': RemiderType.NORMAL.value
			}
			await interaction.client.doc_remider.upsert(reminder_data)

			await interaction.edit_original_response(
				content=f"Alright **{interaction.user.name}**, I'll remind you about `{about}` in **{await convert_to_human_time(cd)}**. (at <t:{int(datetime.datetime.timestamp(datetime.datetime.now() + datetime.timedelta(seconds=cd)))}>)"
				f"\nThis reminder's ID is `{reminder_data['_id']}`."
			)
			if cd < 90:
				self.bot.dispatch('reminder_end', reminder_data, True)
		else:
			return await interaction.edit_original_response(content="You are already subscribed to that reminder!")

	@commands.Cog.listener()
	async def on_ready(self):
		print(f"{self.__class__.__name__} Cog has been loaded\n-----")

	@commands.Cog.listener()
	async def on_message(self, message):
		if not message.author.bot and not message.author.id ==270904126974590976: return
		if message.interaction == None: return
		if message.interaction.name == "work shift":
			try:
				edited = await self.bot.wait_for('message_edit', check=lambda m: m.id == message.id and m.channel.id == message.channel.id, timeout=60)
				self.bot.dispatch('work_shift', edited)
			except:
				pass
				
	@commands.Cog.listener()
	async def on_work_shift(self, message):
		user: discord.User = message.interaction.user
		data = await self.bot.doc_remider.find_by_custom({'host_id': user.id, 'type': RemiderType.value})
		if not data:

			view = Confirm(user, 60)
			msg = await message.channel.send(f"{user.mention} Do want to be reminded about your future work shifts?", view=view)
			await view.wait()

			if view.value == True:
				counter = await self.bot.doc_remider.find("reminder")
				reminder_data = {
					'_id': counter['counter'],
					'host_id': user.id,
					'guild_id': message.guild.id,
					'channel_id': message.channel.id,
					'message_id': msg.id,
					'message_link': msg.jump_url,
					'about': "Work Shift",
					'time': datetime.datetime.now() + datetime.timedelta(hours=1),
					'created_at': datetime.datetime.now(),
					'remind_in_seconds': 3600,
					'type': RemiderType.WORK.value,
					'reminded': False,
					'recurring': 1,
					'enabled': True
				}
				await self.bot.doc_remider.increment("reminder", 1, "counter")
				await self.bot.doc_remider.insert(reminder_data)

			elif view.value == False:

				await msg.edit(content=f"{user.mention} Alright, I won't remind you about your future work shifts.", view=None)
				reminder_data = {
					'_id': counter['counter'],
					'host_id': user.id,
					'guild_id': message.guild.id,
					'channel_id': message.channel.id,
					'message_id': msg.id,
					'message_link': msg.jump_url,
					'about': "Work Shift",
					'time': datetime.datetime.now() + datetime.timedelta(hours=1),
					'created_at': datetime.datetime.now(),
					'remind_in_seconds': 3600,
					'type': RemiderType.WORK.value,
					'reminded': False,
					'recurring': 1,
					'enabled': False
				}
				await self.bot.doc_remider.upsert(reminder_data)
				await message.add_reaction("<:nat_cross:1010965036237324430>")
		else:
			if data['enabled'] == False:
				return

			data['reminded'] = False
			data['time'] = datetime.datetime.now() + datetime.timedelta(hours=1)
			data['remind_in_seconds'] = 3600
			data['recurring'] = 1
			await self.bot.doc_remider.upsert(data)
			await message.add_reaction("<:nat_tick:1010964967970848778>")

	@commands.Cog.listener()
	async def on_reminder_end(self, reminder_data, sleep: bool = None):
		remider_type = reminder_data['type']
		if sleep:
			time_diff = (reminder_data['time'] - datetime.datetime.now()).total_seconds()
			await asyncio.sleep(time_diff)
			
		match remider_type:

			case 'work':
				if reminder_data['reminded'] == True or reminder_data['enabled'] == False: return
				user = self.bot.get_user(reminder_data['host_id'])
				embed = discord.Embed(description=f"Hey you can work again! {user.mention}", color=discord.Color.green())
				embed.set_footer(text="To stop getting reminded about work shifts, use /reminder dank type:work set:False", icon_url=self.bot.user.avatar.url)
				try:
					await user.send(embed=embed)
				except discord.HTTPException:
					channel = self.bot.get_channel(reminder_data['channel_id'])
					await channel.send(f"{user.mention}",embed=embed)
					reminder_data['reminded'] = True
					await self.bot.doc_remider.update(reminder_data)
				return

			case 'normal':
				if reminder_data['recurring'] == 0: return await self.bot.doc_remider.delete(reminder_data['_id'])
				guild = self.bot.get_guild(reminder_data['guild_id'])
				if guild == None: return await self.bot.doc_remider.delete(reminder_data)

				channel = self.bot.get_channel(reminder_data['channel_id'])
				if channel == None: return await self.bot.doc_remider.delete(reminder_data)
				try:
					message = await channel.fetch_message(reminder_data['message_id'])
				except discord.NotFound:
					return await self.bot.doc_remider.delete(reminder_data)
				
				content = f"Hey, you asked me to remind you about `{reminder_data['about']}`. (at <t:{round(reminder_data['created_at'].timestamp())}:R>)\nHere's the link to the message: {reminder_data['message_link']}"

				remider_embed = discord.Embed(title=f"Reminder #{reminder_data['_id']}",description=content,color=self.bot.color['default'])

				mmeber  = guild.get_member(reminder_data['host_id'])
				if mmeber == None: return await self.bot.doc_remider.delete(reminder_data)
				try:
					await mmeber.send(embed=remider_embed)
					await asyncio.sleep(0.5)
					print("faild to send dm")
				except discord.HTTPException:
					print("Sent to channel")
					await channel.send(f"{mmeber.mention}", embed=remider_embed)
					await asyncio.sleep(0.5)
				reminder_data['recurring'] -= 1
				if reminder_data['recurring'] == 0:
					await self.bot.doc_remider.delete(reminder_data['_id'])
				else:

					reminder_data['time'] = reminder_data['time'] + datetime.timedelta(seconds=reminder_data['remind_in_seconds'])
					await self.bot.doc_remider.update(reminder_data)

	# @commands.Cog.listener()
	# async def on_reminder_end(self, reminder_data, sleep: bool = None):
	# 	if sleep:
	# 		time_diff = (reminder_data['time'] - datetime.datetime.now()).total_seconds()
	# 		await asyncio.sleep(time_diff)
	# 		reminder_data = await self.bot.doc_remider.find({'_id': reminder_data['_id']})

	# 	channel = self.bot.get_channel(reminder_data['channel_id'])
	# 	if channel == None:
	# 		return await self.bot.doc_remider.delete(reminder_data['_id'])
	# 	try:
	# 		message = await channel.fetch_message(reminder_data['message_id'])
	# 	except discord.NotFound:
	# 		return await self.bot.doc_remider.delete(reminder_data['_id'])

	# 	content = f'Your reminder ended: **{reminder_data["about"]}**'
	# 	time_passed = await convert_to_human_time((datetime.datetime.now() - reminder_data['created_at']).total_seconds())

	# 	reminder_embed = discord.Embed(
	# 		title=f'Reminder #{reminder_data["_id"]}',
	# 		description=f"You asked to be reminded for **{reminder_data['about']}** [{time_passed} ago]({message.jump_url}).",
	# 		color=self.bot.color['default']
	# 	)
	# 	member = await self.bot.fetch_user(reminder_data['host_id'])
	# 	if member != None:
	# 		try:
	# 			await member.send(content = content, embed = reminder_embed)
	# 			await asyncio.sleep(0.5)
	# 		except:
	# 			await channel.send(content = f"{member.mention}, Your reminder ended!", embed = reminder_embed, allowed_mentions=discord.AllowedMentions(everyone = False, users = True, roles = False, replied_user = True))

	# 	await self.bot.doc_remider.delete(reminder_data)

	@tasks.loop(seconds=60)
	async def reminder_loop(self):
		current_reminder = await self.bot.doc_remider.get_all()
		for reminder in current_reminder:
			if reminder['_id'] == "reminder":
				continue
			time_diff = (reminder['time'] - datetime.datetime.now()).total_seconds()
			if time_diff <= 0:
				self.bot.dispatch('reminder_end', reminder, False)
				return
			elif time_diff <= 60:
				self.bot.dispatch('reminder_end', reminder, True)
				return
			else:
				pass

	@reminder_loop.before_loop
	async def before_reminder_loop(self):
		await self.bot.wait_until_ready()


async def setup(bot):
	await bot.add_cog(Reminder(bot))