import time as t
import datetime
import discord
from discord import app_commands
from discord.ext import commands
from utils.convertor import *

class serverUtils(commands.Cog):

	def __init__(self, bot):
		self.bot = bot

	@commands.Cog.listener()
	async def on_ready(self):
		print(f"{self.__class__.__name__} Cog has been loaded\n-----")

	@app_commands.command(name="ping", description="Ping pong! 🏓")
	@app_commands.checks.cooldown(1, 30, key=lambda i: (i.guild_id, i.user.id))
	async def ping(self, interaction:  discord.Interaction):
		await interaction.response.send_message("Pong! 🏓")

		await interaction.edit_original_response(
			content=f"Pong! **`{round(self.bot.latency * 1000)}ms`**",
		)

	@app_commands.command(name="calculate", description="Do math! 🧮")
	@app_commands.checks.cooldown(1, 30, key=lambda i: (i.guild_id, i.user.id))
	async def calculate(self, interaction:  discord.Interaction, query: str):
		await interaction.response.defer()

		start = t.time()
		query = await convert_to_numeral(query)
		output = await calculate(query)
		output = await millify(output)
		end = time.time()

		calc_embed = discord.Embed(
			color=0x9e3bff,
			title=f"**Calculated:** `{round(float(output),2):,}`",
			description=f"**Calculated in:** {round((end - start) * 1000, 3)} ms",
			timestamp=datetime.datetime.utcnow()
		)
		url = f"https://fakeimg.pl/150x40/9e3bff/000000/?retina=1&text={round(float(output),2):,}&font=lobster&font_size=28"
		calc_embed.set_image(url=url)
		calc_embed.set_footer(
			text=f"{interaction.guild.name}",icon_url=interaction.guild.icon_url)
		# calc_embed.set_author(name=f"Solving for {interaction.user.name} ...", icon_url=interaction.user.display_icon)

		await interaction.edit_original_response(
			embed=calc_embed
		)


async def setup(bot):
	await bot.add_cog(serverUtils(bot))