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

	@app_commands.command(name="calculate", description="Do math! 🧮", extras={'example': '/calculate query: 2m+40k'})
	@app_commands.checks.cooldown(1, 10, key=lambda i: (i.guild_id, i.user.id))
	@app_commands.describe(query = "5 MIl -> 5e6 or 5m", hidden = "Nobody knows how you calculated so accurately 🥂")
	async def calculate(self, interaction:  discord.Interaction, query: str , hidden: bool = False):
		await interaction.response.defer(ephemeral=hidden)

		start = t.time()
		query = await convert_to_numeral(query)
		output = await calculate(query)
		end = t.time()

		calc_embed = discord.Embed(
			color=0x9e3bff,
			title=f"**Value:** `{output:,}`"
		)
		url = f"https://fakeimg.pl/150x40/9e3bff/000000/?retina=1&text={'%20'.join((await millify(output)).split(' '))}&font=lobster&font_size=28"
		calc_embed.set_image(url=url)
		calc_embed.set_footer(text=f"{interaction.guild.name} • Calculated in: {round((end - start) * 1000, 2)} ms",icon_url=interaction.guild.icon)
		calc_embed.set_author(name=f"{interaction.user.display_name}'s calculation ...", icon_url=interaction.user.avatar)

		await interaction.edit_original_response(
			embed=calc_embed
		)


async def setup(bot):
	await bot.add_cog(serverUtils(bot))