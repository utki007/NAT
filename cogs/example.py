import discord
from discord import app_commands
from discord.ext import commands
from utils.embeds import get_invisible_embed
from utils.views.paginator import Paginator
from typing import Union
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageChops

class Button(discord.ui.View):
	def __init__(self):
		super().__init__(timeout=None)
		self.message = None #req for disabling buttons after timeout
	
	@discord.ui.button(label="Click me!",custom_id='button1' , style=discord.ButtonStyle.blurple, emoji="<:StageIconRequests:1005075865564106812>")
	async def click_me(self, interaction: discord.Interaction, button: discord.ui.Button):
		await interaction.response.send_message("You clicked the button!", ephemeral=True)
	
	@discord.ui.button(label="Click 2!" ,custom_id='button2', style=discord.ButtonStyle.blurple, emoji="<:StageIconRequests:1005075865564106812>")
	async def click_2(self, interaction: discord.Interaction, button: discord.ui.Button):
		await interaction.response.send_message("You clicked the button!", ephemeral=True)

	async def interaction_check(self, interaction: discord.Interaction):
		if interaction.user.id != self.interaction.user.id:
			warning = await get_invisible_embed(f"This is not for you")
			return await interaction.response.send_message(embed=warning, ephemeral=True)	
		return True

	async def on_timeout(self):
		for button in self.children:
			button.disabled = True
		
		await self.message.edit(view=self)

class Dropdown(discord.ui.Select):
	def __init__(self):

		# Set the options that will be presented inside the dropdown
		options = [
			discord.SelectOption(label='Red', description='Your favourite colour is red', emoji='🟥'),
			discord.SelectOption(label='Green', description='Your favourite colour is green', emoji='🟩'),
			discord.SelectOption(label='Blue', description='Your favourite colour is blue', emoji='🟦'),
		]

		# The placeholder is what will be shown when no option is chosen
		# The min and max values indicate we can only pick one of the three options
		# The options parameter defines the dropdown options. We defined this above
		super().__init__(placeholder='Choose your favourite colour...', min_values=1, max_values=1, options=options)

	async def callback(self, interaction: discord.Interaction):
		# Use the interaction object to send a response message containing
		# the user's favourite colour or choice. The self object refers to the
		# Select object, and the values attribute gets a list of the user's
		# selected options. We only want the first one.
		await interaction.response.send_message(f'Your favourite colour is {self.values[0]}')


class Feedback(discord.ui.Modal, title='Feedback'):
	# Our modal classes MUST subclass `discord.ui.Modal`,
	# but the title can be whatever you want.

	# This will be a short input, where the user can enter their name
	# It will also have a placeholder, as denoted by the `placeholder` kwarg.
	# By default, it is required and is a short-style input which is exactly
	# what we want.
	name = discord.ui.TextInput(
		label='Name',
		placeholder='Your name here...',
	)

	# This is a longer, paragraph style input, where user can submit feedback
	# Unlike the name, it is not required. If filled out, however, it will
	# only accept a maximum of 300 characters, as denoted by the
	# `max_length=300` kwarg.
	feedback = discord.ui.TextInput(
		label='What do you think of this new feature?',
		style=discord.TextStyle.long,
		placeholder='Type your feedback here...',
		required=False,
		max_length=300,
	)

	async def on_submit(self, interaction: discord.Interaction):
		await interaction.response.send_message(f'Thanks for your feedback, {self.name.value}!', ephemeral=True)
		#we can add embed here if we want to show the feedback in the channel
		

	async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
		await interaction.response.send_message('Oops! Something went wrong.', ephemeral=True)

class Example(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
	
	@commands.Cog.listener()
	async def on_ready(self):
		self.bot.add_view(Button())
		print(f"{self.__class__.__name__} Cog has been loaded\n-----")
	
	@app_commands.command(name="button", description="Send a buttonn with message")
	async def button(self, interaction: discord.Interaction):
		view = Button()
		await interaction.response.send_message("Wow this is a button", view=view)
		view.message = await interaction.original_response()
	
	@app_commands.command(name="dropdown", description="Send a dropdown with message")
	async def dropdown(self, interaction: discord.Interaction):
		view = discord.ui.View()
		view.add_item(Dropdown())
		await interaction.response.send_message("Wow this is a dropdown", view=view)
	
	@app_commands.command(name="modal", description="Send a modal")
	async def modal(self, interaction: discord.Interaction):
		await interaction.response.send_modal(Feedback())

	
	@app_commands.command(name="thread2", description="create thread with message")
	@app_commands.describe(message_id="Message id to create thread with")
	@app_commands.rename(message_id="message")
	async def thread2(self, interaction: discord.Interaction, message_id: str):
		message = await interaction.channel.fetch_message(str(message_id))
		thread = await message.create_thread(name="Thread")
		await thread.send("Hello World")
		await interaction.response.send_message(f"Thread created {thread.mention}")
	
	@app_commands.command(name="page", description="Send a page with message")
	async def page(self, interaction: discord.Interaction):
		emed = discord.Embed(title="Page", description="This is a page", color=discord.Color.blue())
		embed2 = discord.Embed(title="Page2", description="This is a page", color=discord.Color.blue())
		embed3 = discord.Embed(title="Page3", description="This is a page", color=discord.Color.blue())
		embed4 = discord.Embed(title="Page4", description="This is a page", color=discord.Color.blue())
		pages = [emed, embed2, embed3, embed4]
		await Paginator(interaction, pages).start(embeded=True, quick_navigation=True) #set quick_navitation to Flase if len(pages) > 24 or you want to remove dromdown


class donation(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
	
	async def round_pfp(self, pfp: Union[discord.Member, discord.Guild]):
		if isinstance(pfp, discord.Member):
			if pfp.avatar is None:
				pfp = pfp.default_avatar.with_format("png")
			else:
				pfp = pfp.avatar.with_format("png")
		else:
			pfp = pfp.icon.with_format("png")

		pfp = BytesIO(await pfp.read())
		pfp = Image.open(pfp)
		pfp = pfp.resize((95, 95), Image.Resampling.LANCZOS).convert('RGBA')

		bigzise = (pfp.size[0] * 3, pfp.size[1] * 3)
		mask = Image.new('L', bigzise, 0)
		draw = ImageDraw.Draw(mask)
		draw.ellipse((0, 0) + bigzise, fill=255)
		mask = mask.resize(pfp.size, Image.Resampling.LANCZOS)
		mask = ImageChops.darker(mask, pfp.split()[-1])
		pfp.putalpha(mask)

		return pfp

	async def create_winner_card(self, guild: discord.Guild, event_name:str, data: list):
		template = Image.open('./utils/assets/leaderboard_template.png')
		guild_icon = await self.round_pfp(guild)
		template.paste(guild_icon, (15, 8), guild_icon)

		draw = ImageDraw.Draw(template)
		font = ImageFont.load_default('Arial.ttf', 25)
		winner_name_font = ImageFont.truetype('Arial.ttf', 28)
		winner_exp_font = ImageFont.truetype('Arial.ttf', 20)

		winne_postions = {
			#postions of the winners, pfp and name and donation
			0: {'icon': (58, 150), 'name': (176, 165), 'donated': (176, 202)},
			1: {'icon': (58, 265), 'name': (176, 273), 'donated': (176, 309)},
			2: {'icon': (58, 380), 'name': (176, 392), 'donated': (176, 428)}}

		draw.text((116, 28), f"{guild.name}", font=font, fill="#DADBE3") #guild name 
		draw.text((116, 61), f"{event_name}", font=font, fill="#DADBE3") #event name

		for i in data[:3]:
			user = i['user']
			index = data.index(i)
			user_icon = await self.round_pfp(user)
			template.paste(user_icon, winne_postions[index]['icon'], user_icon)
			draw.text(winne_postions[index]['name'], f"{user.name}#{user.discriminator}", font=winner_name_font, fill="#9A9BD5")
			draw.text(winne_postions[index]['donated'], f"⏣ {i['donated']} Dmc", font=winner_exp_font, fill="#A8A8C8")

		return template
	
	@app_commands.command(name="leaderboard", description="Donate to the bot")
	async def leaderborad(self, interaction: discord.Interaction, event_name: str):
		await interaction.response.defer(thinking=True, ephemeral=False)

		mok_data = [301657045248114690, 488614633670967307, self.bot.user.id]
		leader_borad = []
		for i in mok_data:
			user = interaction.guild.get_member(i)
			#do your logic here to change donation to k,m,billion etc
			#also append member as 1st, 2nd, 3rd
			#as they will be displayed in same order as they are appended
			leader_borad.append({'user': user, 'donated': 1000000}) 
		
		image = await self.create_winner_card(interaction.guild, event_name, leader_borad)

		with BytesIO() as image_binary:
			image.save(image_binary, 'PNG')
			image_binary.seek(0)
			await interaction.followup.send(file=discord.File(fp=image_binary, filename=f'{interaction.guild.id}_weekly_winner_card.png'))
			image_binary.close()

async def setup(bot):
	await bot.add_cog(
		Example(bot),
		guilds = [discord.Object(999551299286732871)]
	)
	await bot.add_cog(
		donation(bot),
		guilds = [discord.Object(999551299286732871)]
	)

