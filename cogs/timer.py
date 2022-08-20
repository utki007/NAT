import asyncio
import datetime
from email import message
from tabnanny import check
import discord
from discord import app_commands
from discord.ext import commands, tasks
from utils.convertor import *

class Button(discord.ui.View):
	def __init__(self,timer_data):
		super().__init__(timeout=None)
		self.message = None #req for disabling buttons after timeout
		self.timer = timer_data
	
	@discord.ui.button(style=discord.ButtonStyle.blurple , emoji="<a:tgk_timer:841624339169935390>",custom_id='timer_button')
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

class timer(commands.Cog):

	def __init__(self, bot):
		self.bot = bot
		self.timertask = self.timer_loop.start()

	def cog_unload(self) -> None:
		self.timertask.cancel()

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
		embed.description = f"**Timer ended!**"

		view = discord.ui.View.from_message(message)
		for children in view.children:
			children.disabled = True
		await message.edit(embed=embed,view=view,delete_after=300)

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

	@app_commands.command(name="timer", description="Set a timer")
	# @app_commands.checks.cooldown(1, 30, key=lambda i: (i.guild_id, i.user.id))
	async def timer(self, interaction:  discord.Interaction, time: str):
		await interaction.response.defer()

		original_time = time
		try:
			time = await convert_to_time(time)
			cd = int(await calculate(time))
			end = datetime.datetime.now() + datetime.timedelta(seconds=cd)
		except:
			warning = discord.Embed(
				color=0xE74C3C,
				description=f"{self.bot.emojis_list['Warrning']} | Error with Heist Timer!!")
			return await interaction.response.send_message(embed=warning, ephemeral=True)

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

		desc = f"<t:{int(datetime.datetime.timestamp(end))}:R>\n"

		e = discord.Embed(
			color= 0x5865F2,
			title=f"{'Timer'}",
			description=f'**{desc}**',
			timestamp=end
		)
		e.set_footer(
				text=f"Ends at")

		view = Button(timer_data)
		timer = await interaction.edit_original_response(embed=e, view=view)
		view.message = timer

		if cd < 90:
			self.bot.dispatch('timer_end', timer_data, True)


async def setup(bot):
	await bot.add_cog(timer(bot))
