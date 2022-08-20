import asyncio
import datetime
from email import message
from tabnanny import check
import discord
from discord import app_commands
from discord.ext import commands, tasks
from utils.convertor import *
from itertools import islice

def chunk(it, size):
	it = iter(it)
	return iter(lambda: tuple(islice(it, size)), ())

class Button(discord.ui.View):
	def __init__(self,timer_data):
		super().__init__(timeout=None)
		self.message = None #req for disabling buttons after timeout
		self.timer = timer_data
	
	@discord.ui.button(style=discord.ButtonStyle.gray , emoji="<a:tgk_timer:841624339169935390>",custom_id='timer_button')
	async def click_me(self, interaction: discord.Interaction, button: discord.ui.Button):
		# await interaction.response.defer()
		timer_data = await interaction.client.timer.find({'_id':interaction.message.id})
		if timer_data == None:
			return await interaction.response.send_message("Invalid/Expired timer", ephemeral=True)

		if interaction.user.id in timer_data['members']:
			return await interaction.response.send_message("You have already entered the timer!", ephemeral=True)
		timer_data['members'].append(interaction.user.id)

		button.label = len(timer_data['members'])
		await interaction.message.edit(view=self)
		await interaction.response.send_message("You will be reminded once timer ends!", ephemeral=True)
		await interaction.client.timer.update(timer_data)
		self.timer = timer_data
	
	async def on_timeout(self):
		for button in self.buttons:
			button.disable = True
		
		await self.message.edit(view=self)

class timer_slash(app_commands.Group):
	
	def __init__(self, bot):
		super().__init__(name="timer")
		self.bot = bot

	@app_commands.command(name="start", description="Create a timer")
	@app_commands.guild_only()
	# @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
	async def timerStart(self, interaction:  discord.Interaction, time: str):
		try:
			time = await convert_to_time(time)
			cd = int(await calculate(time))
			end = datetime.datetime.now() + datetime.timedelta(seconds=cd)
		except:
			warning = discord.Embed(
				color=0xFF0000,
				title=f"<a:nat_warning:1010618708688912466> **|** Incorrect time format, please use `1h30m10s`")
			return await interaction.response.send_message(embed=warning, ephemeral=True)

		if cd < 30:
			warning = discord.Embed(
				color=0xFF0000,
				title=f"<a:nat_warning:1010618708688912466> **|** Time should be more than 30s")
			return await interaction.response.send_message(embed=warning, ephemeral=True)
		await interaction.response.defer()
		timer_left = datetime.datetime.strptime(str(datetime.timedelta(seconds=cd)), '%H:%M:%S')
		message = await interaction.original_response()
		timer_data = {
			"_id": message.id,
			'user_id': interaction.user.id,
			'guild_id': interaction.guild.id,
			'channel_id': interaction.channel.id,
			'host_id': interaction.user.id,
			'time': end,
			'members': []
		}
		await interaction.client.timer.upsert(timer_data)

		desc = f"\n"

		e = discord.Embed(
			# color= 0x5865F2,
			color=0xE74C3C,
			title=f"{'Timer'}",
			description = f"> **Ends:** **<t:{int(datetime.datetime.timestamp(end))}:R>**\n> **Launched by:** <@{timer_data['user_id']}>\n",
			timestamp=end
		)
		e.set_footer(
				text=f"Ends at")

		view = Button(timer_data)
		timer = await interaction.edit_original_response(embed=e, view=view)
		view.message = timer

		if cd < 90:
			self.bot.dispatch('timer_end', timer_data, True)

	@app_commands.command(name="end", description="End a timer")
	@app_commands.guild_only()
	# @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
	async def timerEnd(self, interaction:  discord.Interaction, message_id: str):
		await interaction.response.defer(ephemeral=True)
		try:
			timer_data = await interaction.client.timer.find({'_id': int(message_id)})
			if timer_data == None:
				return await interaction.edit_original_response(content="Invalid/Expired timer")
			if timer_data['user_id'] != interaction.user.id:
				return await interaction.edit_original_response(content="You are not the host of the timer!")
			interaction.client.dispatch('timer_end', timer_data, False)
			await interaction.edit_original_response(content="Timer ended successfully!")
		except:
			warning = discord.Embed(
				color=0xFF0000,
				title=f"<a:nat_warning:1010618708688912466> **|** Invalid message id")
			return await interaction.edit_original_response(embed=warning)

	@app_commands.command(name="delete", description="Delete a timer")
	@app_commands.guild_only()
	# @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
	async def timerDelete(self, interaction:  discord.Interaction, message_id: str):
		await interaction.response.defer(ephemeral=True)
		try:
			timer_data = await interaction.client.timer.find({'_id': int(message_id)})
			if timer_data == None:
				return await interaction.edit_original_response(content="Invalid/Expired timer")
			if timer_data['user_id'] != interaction.user.id:
				return await interaction.edit_original_response(content="You are not the host of the timer!")
			
			channel = self.bot.get_channel(timer_data['channel_id'])
			if channel == None:
				self.bot.remove_view(Button(timer_data))
				return await self.bot.timer.delete(timer_data['_id'])
			try:
				message = await channel.fetch_message(timer_data['_id'])
			except discord.NotFound:
				self.bot.remove_view(Button(timer_data))
				return await self.bot.timer.delete(timer_data['_id'])
			await message.delete()
			await interaction.client.timer.delete(timer_data)
			await interaction.edit_original_response(content="Timer deleted successfully!")
		except:
			warning = discord.Embed(
				color=0xFF0000,
				title=f"<a:nat_warning:1010618708688912466> **|** Invalid message id")
			return await interaction.edit_original_response(embed=warning)

class timer(commands.Cog):

	def __init__(self, bot):
		self.bot = bot
		self.timertask = self.timer_loop.start()

	def cog_unload(self) -> None:
		self.timertask.cancel()

	@commands.Cog.listener()
	async def on_ready(self):
		self.bot.tree.add_command(timer_slash(self.bot))
		print(f"{self.__class__.__name__} Cog has been loaded\n-----")
		current_timer = await self.bot.timer.get_all()
		for timer in current_timer:
			self.bot.add_view(Button(timer))
	
	@commands.Cog.listener()
	async def on_timer_end(self, timer_data, sleep:bool=None):
		if sleep:
			time_diff = (timer_data['time'] - datetime.datetime.now()).total_seconds()
			await asyncio.sleep(time_diff)
			timer_data = await self.bot.timer.find({'_id':timer_data['_id']})

		channel = self.bot.get_channel(timer_data['channel_id'])
		if channel == None:
			self.bot.remove_view(Button(timer_data))
			return await self.bot.timer.delete(timer_data['_id'])
		try:
			message = await channel.fetch_message(timer_data['_id'])
		except discord.NotFound:
			self.bot.remove_view(Button(timer_data))
			return await self.bot.timer.delete(timer_data['_id'])

		embed = message.embeds[0]
		embed.description = f"> **Entrants:** {len(timer_data['members'])}\n> **Timer ended!**\n> **Launched by:** <@{timer_data['user_id']}>"
		embed.timestamp = datetime.datetime.now()

		view = discord.ui.View.from_message(message)
		for children in view.children:
			children.disabled = True
			children.label = None
		await message.edit(embed=embed,view=view)

		member_list = [await self.bot.fetch_user(member) for member in timer_data['members']]

		try:
			ping_group = list(chunk(member_list,30))
			for memmbers in ping_group:
				await channel.send(f"{', '.join(user.mention for user in memmbers)}",delete_after=1)
		except:
			pass

		try:
			view = discord.ui.View()
			view.add_item(discord.ui.Button(label=f'Timer link', url=message.jump_url))
			end_message = await channel.send(f"<@{timer_data['user_id']}> your timer has ended!", view=view)
			await end_message.add_reaction("<a:gk_waiting:945772518776664104>")
		except:
			pass

		await self.bot.timer.delete(timer_data['_id'])

	@tasks.loop(seconds=60)
	async def timer_loop(self):
		current_timer = await self.bot.timer.get_all()
		for timer in current_timer:
			time_diff = (timer['time'] - datetime.datetime.now()).total_seconds()
			if time_diff <= 0:
				self.bot.dispatch('timer_end', timer, False)
			elif time_diff <= 60:
				self.bot.dispatch('timer_end', timer, True)
			else:
				pass
	
	@timer_loop.before_loop
	async def before_timer_loop(self):
		await self.bot.wait_until_ready()

	# @app_commands.command(name="timer", description="Set a timer")
	# @app_commands.guild_only()
	# # @app_commands.checks.cooldown(1, 30, key=lambda i: (i.guild_id, i.user.id))
	# async def timer(self, interaction:  discord.Interaction, time: str):
	# 	try:
	# 		time = await convert_to_time(time)
	# 		cd = int(await calculate(time))
	# 		end = datetime.datetime.now() + datetime.timedelta(seconds=cd)
	# 	except:
	# 		warning = discord.Embed(
	# 			color=0xFF0000,
	# 			title=f"<a:nat_warning:1010618708688912466> **|** Incorrect time format, please use `1h30m10s`")
	# 		return await interaction.response.send_message(embed=warning, ephemeral=True)

	# 	if cd < 10:
	# 		warning = discord.Embed(
	# 			color=0xFF0000,
	# 			title=f"<a:nat_warning:1010618708688912466> **|** Time should be more than 10s")
	# 		return await interaction.response.send_message(embed=warning, ephemeral=True)
	# 	await interaction.response.defer()
	# 	timer_left = datetime.datetime.strptime(str(datetime.timedelta(seconds=cd)), '%H:%M:%S')
	# 	message = await interaction.original_response()
	# 	timer_data = {
	# 		"_id": message.id,
	# 		'user_id': interaction.user.id,
	# 		'guild_id': interaction.guild.id,
	# 		'channel_id': interaction.channel.id,
	# 		'host_id': interaction.user.id,
	# 		'time': end,
	# 		'members': []
	# 	}
	# 	await interaction.client.timer.upsert(timer_data)

	# 	desc = f"\n"

	# 	e = discord.Embed(
	# 		# color= 0x5865F2,
	# 		color=0xE74C3C,
	# 		title=f"{'Timer'}",
	# 		description = f"> **Ends:** **<t:{int(datetime.datetime.timestamp(end))}:R>**\n> **Launched by:** <@{timer_data['user_id']}>\n",
	# 		timestamp=end
	# 	)
	# 	e.set_footer(
	# 			text=f"Ends at")

	# 	view = Button(timer_data)
	# 	timer = await interaction.edit_original_response(embed=e, view=view)
	# 	view.message = timer

	# 	if cd < 90:
	# 		self.bot.dispatch('timer_end', timer_data, True)


async def setup(bot):
	await bot.add_cog(timer(bot))
