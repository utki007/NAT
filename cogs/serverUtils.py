import time as t
import datetime
import discord
from discord import app_commands, Interaction
from discord.ext import commands
from utils.convertor import *
from io import BytesIO

class Dump(commands.GroupCog, name="dump"):
	def __init__(self, bot):
		self.bot = bot
	
	@app_commands.command(name="role", description="Dump a role")
	@app_commands.describe(role='Role to dump')
	async def dump_role(self, interaction: Interaction, role:discord.Role):
		msg = f"{role.name} has {len(role.members)} members"
		
		if len(role.members) > 20:
			await interaction.response.send_message("Role has more than 20 members, sending as file", ephemeral=False)
			members = [f"{member.name}#{member.discriminator} | {member.id}" for member in role.members]

			buffer = BytesIO("\n".join(members).encode('utf-8'))
			file = discord.File(buffer, filename=f"{role.name}.txt")
			buffer.close()
			await interaction.edit_original_response(content=msg, attachments=[file])
		else:
			embed = discord.Embed(title=f"{role.name} dump", description="\n".join([f"{member.name}#{member.discriminator} | {member.id}" for member in role.members]), color=role.color)
			await interaction.response.send_message(content=msg, embeds=[embed])
	
	@app_commands.command(name="channel", description="Dump a channel")
	@app_commands.describe(channel='Channel to dump')
	async def dump_channel(self, interaction: Interaction, channel:discord.TextChannel):
		msg = f"{channel.name} has {len(channel.members)} members"

		if len(channel.members) > 20:
			await interaction.response.send_message("Channel has more than 20 members, sending as file", ephemeral=False)
			members = [f"{member.name}#{member.discriminator} | {member.id}" for member in channel.members]

			buffer = BytesIO("\n".join(members).encode('utf-8'))
			file = discord.File(buffer, filename=f"{channel.name}.txt")
			buffer.close()
			await interaction.edit_original_response(content=msg, attachments=[file])
		
		else:
			embed = discord.Embed(title=f"{channel.name} dump", description="\n".join([f"{member.name}#{member.discriminator} | {member.id}" for member in channel.members]), color=self.bot.color['default'])
			await interaction.response.send_message(content=msg, embeds=[embed])


class serverUtils(commands.Cog):
	def __init__(self, bot):
		self.bot = bot


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
	await bot.add_cog(Dump(bot))
	print(f"loaded serverUtils cog")