import asyncio
import datetime
from tabnanny import check
from typing import Literal
from unicodedata import name
import discord
from discord import app_commands
from discord.ext import commands, tasks
from utils.convertor import *
from utils.paginator import Paginator


class reminder_slash(app_commands.Group):

	def __init__(self, bot):
		super().__init__(name="reminder")
		self.bot = bot

	@app_commands.command(name="create", description="Create a reminder")
	@app_commands.guild_only()
	@app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
	@app_commands.describe(time="Enter time in format: 1h30m2s", about="Enter the message you want to be reminded of")
	async def reminderCreate(self, interaction:  discord.Interaction, about: str, time: str):
		try:
			time = await convert_to_time(time)
			cd = int(await calculate(time))
			end = datetime.datetime.now() + datetime.timedelta(seconds=cd)
		except:
			warning = discord.Embed(
				color=self.bot.color['danger'],
				title=f"<a:nat_warning:1010618708688912466> **|** Incorrect time format, please use `1h30m10s`")
			return await interaction.response.send_message(embed=warning, ephemeral=True)

		if cd < 3:
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
			'time': end,
			'created_at': datetime.datetime.now(),
			'remind_in_seconds': cd,
			'members': [interaction.user.id]
		}
		await interaction.client.doc_remider.upsert(reminder_data)

		await interaction.edit_original_response(
			content=f"Alright **{interaction.user.name}**, I'll remind you about `{about}` in **{await convert_to_human_time(cd)}**. (at <t:{int(datetime.datetime.timestamp(end))}>)"
			f"\nThis reminder's ID is `{reminder_data['_id']}`."
		)
		if cd < 90:
			self.bot.dispatch('reminder_end', reminder_data, True)

	@app_commands.command(name="cancel", description="Cancel a reminder by id")
	@app_commands.guild_only()
	@app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
	@app_commands.describe(reminder_id = "ID of the reminder")
	async def reminderCancel(self, interaction:  discord.Interaction, reminder_id: int):
		await interaction.response.defer(ephemeral=True)
		reminder_data = await interaction.client.doc_remider.find({'_id': reminder_id})
		if reminder_data == None:
			return await interaction.edit_original_response(content="Invalid/Expired reminder!")
		if reminder_data['host_id'] != interaction.user.id:
			if interaction.user.id not in reminder_data['members']:
				return await interaction.edit_original_response(content="You are not subscribed to that reminder!")
			else:
				reminder_data['members'].remove(interaction.user.id)
				if len(reminder_data) > 0:
					await interaction.client.doc_remider.update(reminder_data)
				else:
					await interaction.client.doc_remider.delete(reminder_data)
				return await interaction.edit_original_response(content=f"You have successfully unsubscribed from **Reminder #{reminder_data['_id']}** for `{reminder_data['about']}`!")
		else:
			await interaction.client.doc_remider.delete(reminder_data)
			return await interaction.edit_original_response(content=f"You have successfully deleted **Reminder #{reminder_data['_id']}** for `{reminder_data['about']}`!")

	@app_commands.command(name="clear", description="Clear all reminders")
	@app_commands.guild_only()
	@app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
	async def reminderClear(self, interaction: discord.Interaction, clear_from: Literal['current server', 'all servers']):
		await interaction.response.defer(ephemeral=True)
		if clear_from == 'current server':
			reminders = await interaction.client.doc_remider.get_all({'host_id':interaction.user.id, 'guild_id': interaction.guild.id})
			content = "You have successfully cleared all reminders from **{interaction.guild.name}**!"
		else:
			reminders = await interaction.client.doc_remider.get_all({'host_id':interaction.user.id})
			content = "You have successfully cleared all reminders from all your servers!"
		if reminders == None or reminders == []:
			return await interaction.edit_original_response(content=f"All reminders are already cleared!")
		for reminder in reminders:
			await interaction.client.doc_remider.delete(reminder)
		return await interaction.edit_original_response(content=content)

	@app_commands.command(name="list", description="List of all reminders")
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
			return await interaction.edit_original_response(content=f"You don't have any reminders set.")
		
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
		await Paginator(interaction, pages, custom_button).start(embeded=True, quick_navigation=False) #set quick_navitation to Flase if len(pages) > 24 or you want to remove dromdown
	

class reminder(commands.Cog):

	def __init__(self, bot):
		self.bot = bot
		self.remindertask = self.reminder_loop.start()

	def cog_unload(self) -> None:
		self.remindertask.cancel()

	@commands.Cog.listener()
	async def on_ready(self):
		self.bot.tree.add_command(reminder_slash(self.bot))
		print(f"{self.__class__.__name__} Cog has been loaded\n-----")

	@commands.Cog.listener()
	async def on_reminder_end(self, reminder_data, sleep: bool = None):
		if sleep:
			time_diff = (reminder_data['time'] - datetime.datetime.now()).total_seconds()
			await asyncio.sleep(time_diff)
			reminder_data = await self.bot.doc_remider.find({'_id': reminder_data['_id']})

		channel = self.bot.get_channel(reminder_data['channel_id'])
		if channel == None:
			return await self.bot.doc_remider.delete(reminder_data['_id'])
		try:
			message = await channel.fetch_message(reminder_data['message_id'])
		except discord.NotFound:
			return await self.bot.doc_remider.delete(reminder_data['_id'])

		member_list = [await self.bot.fetch_user(member) for member in reminder_data['members']]
		member_list = [member for member in member_list if member != None]

		content = f'Your reminder ended: **{reminder_data["about"]}**'

		reminder_embed = discord.Embed(
			title=f'Reminder #{reminder_data["_id"]}',
			description=f"You asked to be reminded for `{reminder_data['about']}` [{await convert_to_human_time(reminder_data['remind_in_seconds'])} ago]({message.jump_url}).",
			color=self.bot.color['default']
		)

		for member in member_list:
			try:
				await member.send(content = content, embed = reminder_embed)
				await asyncio.sleep(0.5)
			except:
				await channel.send(content = f"{member.mention}, {content}", embed = reminder_embed)

		await self.bot.doc_remider.delete(reminder_data)

	@tasks.loop(seconds=60)
	async def reminder_loop(self):
		current_reminder = await self.bot.doc_remider.get_all()
		for reminder in current_reminder:
			if reminder['_id'] == "reminder":
				continue
			time_diff = (reminder['time'] - datetime.datetime.now()).total_seconds()
			if time_diff <= 0:
				self.bot.dispatch('reminder_end', reminder, False)
			elif time_diff <= 60:
				self.bot.dispatch('reminder_end', reminder, True)
			else:
				pass

	@reminder_loop.before_loop
	async def before_reminder_loop(self):
		await self.bot.wait_until_ready()


async def setup(bot):
	await bot.add_cog(reminder(bot))
