import asyncio
import datetime
from itertools import islice
from tabnanny import check

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils.convertor import convert_to_time, calculate
from utils.embeds import get_error_embed, get_success_embed, get_warning_embed


def chunk(it, size):
	it = iter(it)
	return iter(lambda: tuple(islice(it, size)), ())

class Button(discord.ui.View):
	def __init__(self,timer_data):
		super().__init__(timeout=None)
		self.message = None
		self.timer = timer_data
	
	@discord.ui.button(style=discord.ButtonStyle.gray , emoji="<a:tgk_timer:841624339169935390>",custom_id='timer_button')
	async def click_me(self, interaction: discord.Interaction, button: discord.ui.Button):
		timer_data = await interaction.client.timer.find({'_id':interaction.message.id})
		if timer_data == None:
			return await interaction.response.send_message("Invalid/Expired timer", ephemeral=True)

		if interaction.user.id in timer_data['members']:
			error_embed = await get_error_embed(f"You have already entered the timer!")
			return await interaction.response.send_message(embed = error_embed, ephemeral=True)
		timer_data['members'].append(interaction.user.id)
		await interaction.client.timer.update(timer_data)

		button.label = str(len(timer_data['members'])) 
		await interaction.response.edit_message(view=self)
		# embed = await get_success_embed(f"I will remind you once timer ends!")
		# await asyncio.sleep(1)
		# await interaction.followup.send(embed = embed, ephemeral=True)
		self.timer = timer_data

	async def on_timeout(self):
		for button in self.buttons:
			button.disabled = True
		
		await self.message.edit(view=self)

@app_commands.guild_only()
class Timer(commands.GroupCog, name="timer", description="Timer commands"):
	def __init__(self, bot):
		self.bot = bot
		self.timertask = self.timer_loop.start()

	def cog_unload(self) -> None:
		self.timertask.cancel()

	@app_commands.command(name="start", description="Create a timer", extras={'example': '/timer start [time]'})
	@app_commands.checks.cooldown(1, 3, key=lambda i: (i.guild_id, i.user.id))
	@app_commands.describe(time = "Enter time in format: 1h30m2s", title = "Enter title of the timer")
	async def timerStart(self, interaction:  discord.Interaction, time: str, title: str = 'Timer'):
		try:
			time = await convert_to_time(time)
			cd = int(await calculate(time))
			end = datetime.datetime.now() + datetime.timedelta(seconds=cd)
		except:
			warning = await get_warning_embed("Incorrect time format, please use `1h30m10s`")
			return await interaction.response.send_message(embed=warning, ephemeral=True)

		if cd < 30:
			warning = await get_warning_embed("Time should be more than 30s")
			return await interaction.response.send_message(embed=warning, ephemeral=True)
		await interaction.response.defer()
		message = await interaction.original_response()
		timer_data = {
			"_id": message.id,
			'user_id': interaction.user.id,
			'guild_id': interaction.guild.id,
			'channel_id': interaction.channel.id,
			'time': end,
			'title': title,
			'members': []
		}
		await interaction.client.timer.upsert(timer_data)

		desc = f"\n"

		e = discord.Embed(
			color=self.bot.color['default'],
			title=f"{title}",
			description = f"> **Ends:** **<t:{int(datetime.datetime.timestamp(end))}:R>**\n> **Launched by:** {interaction.user.mention}\n",
			timestamp=end
		)
		e.set_footer(
				text=f"Ends at")

		view = Button(timer_data)
		timer = await interaction.edit_original_response(embed=e, view=view)
		view.message = timer

	@app_commands.command(name="end", description="End a timer", extras={'example': '/timer end [timer_id]'})
	@app_commands.checks.cooldown(1, 3, key=lambda i: (i.guild_id, i.user.id))
	@app_commands.describe(message_id = "Enter Message ID of an active timer")
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
			warning = await get_warning_embed("Invalid timer ID")
			return await interaction.edit_original_response(embed=warning)

	@app_commands.command(name="delete", description="Delete a timer", extras={'example': '/timer delete [timer_id]'})
	@app_commands.checks.cooldown(1, 3, key=lambda i: (i.guild_id, i.user.id))
	@app_commands.describe(message_id = "Enter Message ID of an active timer")
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
				# self.bot.remove_view(Button(timer_data))
				return await self.bot.timer.delete(timer_data['_id'])
			try:
				message = await channel.fetch_message(timer_data['_id'])
			except discord.NotFound:
				# self.bot.remove_view(Button(timer_data))
				return await self.bot.timer.delete(timer_data['_id'])
			await message.delete()
			await interaction.client.timer.delete(timer_data['_id'])
			await interaction.edit_original_response(content="Timer deleted successfully!")
		except:
			warning = await get_warning_embed("Invalid timer ID")
			return await interaction.edit_original_response(embed=warning)

	@app_commands.command(name="re-ping", description="Ping from an expired timer!" , extras={'example': '/timer re-ping [timer_id]'})
	@app_commands.checks.cooldown(1, 3, key=lambda i: (i.guild_id, i.user.id))
	@app_commands.describe(message_id = "Inactive timer message id < 1h")
	async def timerPing(self, interaction:  discord.Interaction, message_id: str):
		await interaction.response.defer(ephemeral=True)
		try:
			timer_data = await interaction.client.timer.find({'_id': int(message_id)})
			if timer_data == None:
				return await interaction.edit_original_response(content="Cannot ping from a timer that has ended more than an hour ago!")
			if timer_data['user_id'] != interaction.user.id:
				return await interaction.edit_original_response(content="You are not the host of the timer!")
			if timer_data['time'] > datetime.datetime.now():
				return await interaction.edit_original_response(content="Timer has not ended yet!")
			if len(timer_data['members']) == 0:
				return await interaction.edit_original_response(content="No one has entered the timer!")
			
			channel = self.bot.get_channel(timer_data['channel_id'])
			if channel == None:
				# self.bot.remove_view(Button(timer_data))
				return await self.bot.timer.delete(timer_data['_id'])
			try:
				message = await channel.fetch_message(timer_data['_id'])
			except discord.NotFound:
				# self.bot.remove_view(Button(timer_data))
				return await self.bot.timer.delete(timer_data['_id'])
			
			member_list = [await self.bot.fetch_user(member) for member in timer_data['members']]
			member_list = [member for member in member_list if member != None]

			try:
				ping_group = list(chunk(member_list,30))
				for members in ping_group:
					await channel.send(f"{', '.join(user.mention for user in members)}",delete_after=1)
			except:
				pass

			try:
				view = discord.ui.View()
				view.add_item(discord.ui.Button(label=f'Timer link', url=message.jump_url))
				end_message = await message.reply(f"<@{timer_data['user_id']}> your timer has been repinged!", view=view)
				await end_message.add_reaction("<a:gk_waiting:945772518776664104>")
				await self.bot.timer.delete(timer_data['_id'])
			except:
				pass
			await interaction.edit_original_response(content="Ping sent successfully!")
		except:
			warning = await get_warning_embed("Invalid timer ID")
			return await interaction.edit_original_response(embed=warning)

	@commands.Cog.listener()
	async def on_ready(self):
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

		if timer_data == None:
			return

		channel = self.bot.get_channel(timer_data['channel_id'])
		if channel == None:
			# self.bot.remove_view(Button(timer_data))
			return await self.bot.timer.delete(timer_data['_id'])
		try:
			message = await channel.fetch_message(timer_data['_id'])
		except:
			return await self.bot.timer.delete(timer_data['_id'])
		# except discord.HTTPException:
		# 	return await self.bot.timer.delete(timer_data['_id'])

		embed = message.embeds[0]
		if "Timer ended!" in embed.description:
			time_diff_to_delete = int((datetime.datetime.now() - timer_data['time']).total_seconds())
			if time_diff_to_delete > 60*60:
				return await self.bot.timer.delete(timer_data['_id'])
			return
		embed.description = f"> **Entrants:** **{len(timer_data['members'])}**\n> **Timer ended!**\n> **Launched by:** <@{timer_data['user_id']}>"
		embed.timestamp = datetime.datetime.now()
		timer_data['time'] = datetime.datetime.now()

		view = discord.ui.View.from_message(message)
		for children in view.children:
			children.disabled = True
			children.label = None
		if message.author.id == self.bot.user.id:
			await message.edit(embed=embed,view=view)
		else:
			return await self.bot.timer.delete(timer_data['_id'])

		member_list = timer_data['members']
		title = timer_data['title']

		try:
			ping_group = list(chunk(member_list,50))
			for members in ping_group:
				await channel.send(f"{', '.join(f'<@{id}>' for id in members)}",delete_after=1)
		except:
			pass

		try:
			view = discord.ui.View()
			view.add_item(discord.ui.Button(label=f'Timer link', url=message.jump_url))
			if title == 'Timer':
				end_message = await channel.send(f"<@{timer_data['user_id']}> your timer has ended!", view=view)
			else:
				end_message = await channel.send(f"<@{timer_data['user_id']}> your timer for **{timer_data['title'].title()}** has ended!", view=view)
			await end_message.add_reaction("<a:gk_waiting:945772518776664104>")
		except:
			pass
		
		await self.bot.timer.update(timer_data)

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

	
async def setup(bot):
	await bot.add_cog(Timer(bot))