import asyncio
import time as t
import datetime
import discord
from discord import app_commands, Interaction
from discord.ext import commands
from ui.settings.mafia import Mafia_Panel
from utils.embeds import *
from utils.convertor import *
from utils.checks import App_commands_Checks
from io import BytesIO
from typing import List, Union
from ui.settings import *
from ui.settings.dankPool import *
from utils.functions import *
from utils.views.confirm import Confirm
from utils.views.ui import *
from ui.settings.lockdown import *
from utils.views.paginator import Paginator
from itertools import islice

def chunk(it, size):
	it = iter(it)
	return iter(lambda: tuple(islice(it, size)), ())

class serverUtils(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@commands.hybrid_command(name='ping', description='Check the bot\'s latency! 🏓')
	@commands.cooldown(1, 10, commands.BucketType.user)
	@app_commands.guild_only()
	async def ping(self, ctx):
		msg = await ctx.send("Pong! 🏓")

		await msg.edit(
			content=f"Pong! **`{round(self.bot.latency * 1000)}ms`**"			
		)

	@commands.hybrid_command(name="calculate", description="Do math! 🧮", extras={'example': '/calculate query: 2m+40k'} )
	@app_commands.guild_only()
	@app_commands.checks.cooldown(1, 2, key=lambda i: (i.guild_id, i.user.id))
	@app_commands.describe(query = "5 Mil -> 5e6 or 5m")
	async def calculate(self, ctx, query: str):

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
		calc_embed.set_footer(text=f"{ctx.guild.name} • Calculated in: {round((end - start) * 1000, 2)} ms",icon_url=ctx.guild.icon)
		calc_embed.set_author(name=f"{ctx.author.display_name}'s calculation ...", icon_url=ctx.author.avatar)

		await ctx.send(
			embed=calc_embed
		)

	@app_commands.command(name="serversettings", description="Adjust server-specific settings! ⚙️")
	@app_commands.guild_only()
	@app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
	@App_commands_Checks.is_server_owner()
	async def serversettings(self, interaction:  discord.Interaction):
		embed = discord.Embed(
			color=3092790,
			title="Server Settings",
			description=f"Adjust server-specific settings! ⚙️"
		)
		view = discord.ui.View()
		view.add_item(Serversettings_Dropdown())
		await interaction.response.send_message(embed=embed, view=view)
		
class Serversettings_Dropdown(discord.ui.Select):
	def __init__(self, default = -1):

		options = [
			discord.SelectOption(label='Dank Pool Access', description="Who all can access Server's Donation Pool", emoji='<:tgk_bank:1073920882130558987>'),
			discord.SelectOption(label='Mafia Logs Setup', description='Log entire game', emoji='<:tgk_amongUs:1103542462628253726>'),
			discord.SelectOption(label='Server Lockdown', description='Configure Lockdown Profiles', emoji='<:tgk_lock:1072851190213259375>'),
		]
		if default != -1:
			options[default].default = True
		super().__init__(placeholder='What would you like to configure today?', min_values=1, max_values=1, options=options, row=0)

	async def callback(self, interaction: discord.Interaction):
		
		if self.values[0] == "Dank Pool Access":

			data = await interaction.client.dankSecurity.find(interaction.guild.id)
			if data is None:
				data = { 
					"_id": interaction.guild.id, 
					"event_manager": None, 
					"whitelist": [], 
					"quarantine": None, 
					"enable_logging":False, 
					"logs_channel": None
				}
				await interaction.client.dankSecurity.upsert(data)

			users = f""
			
			if data['whitelist'] is None or len(data['whitelist']) == 0:
				users += f"` - ` **Add users when?**\n"
			else:
				for member_id in data['whitelist']:
					try: 
						member = interaction.guild.get_member(int(member_id))
						users += f"` - ` {member.mention}\n"
					except:
						data['whitelist'].remove(member_id)
						await interaction.client.dankSecurity.upsert(data)
						pass
			event_manager = data['event_manager']
			
			event_manager_error = ''
			if event_manager is None:
				event_manager = f"**`None`**"
			else:
				event_manager = interaction.guild.get_role(int(event_manager))
				if event_manager is not None:
					if event_manager.position > interaction.guild.me.top_role.position:
						event_manager_error = f"> The {event_manager.mention} role is higher than my top role. \n > I cannot remove it from **raiders**."
					event_manager = f"**{event_manager.mention} (`{event_manager.id}`)**"
				else:
					data['event_manager'] = None
					await interaction.client.dankSecurity.upsert(data)
					event_manager = f"**`None`**"

				
			quarantine = data['quarantine']

			if quarantine is None:
				quarantine = f"**`None`**"
			else:
				quarantine = interaction.guild.get_role(int(quarantine))
				if quarantine is not None:
					quarantine = f"**{quarantine.mention} (`{quarantine.id}`)**"
				else:
					data['quarantine'] = None
					await interaction.client.dankSecurity.upsert(data)
					quarantine = f"**`None`**"
			
			if 'log_channel' in data:
				channel = data['logs_channel']
			else:
				channel = None

			if channel is None:
				channel = f"**`None`**"
			else:
				channel = interaction.guild.get_channel(int(channel))
				if channel is not None:
					channel = f"**{channel.mention} (`{channel.name}`)**"
				else:
					data['logs_channel'] = None
					await interaction.client.mafiaConfig.upsert(data)
					channel = f"**`None`**"

			embed = discord.Embed(
				color=3092790,
				title="Dank Pool Access"
			)
			embed.add_field(name="Following users are whitelisted:", value=f"{users}", inline=False)
			embed.add_field(name="Event Manager Role:", value=f"{event_manager}", inline=False)
			embed.add_field(name="Quarantine Role:", value=f"{quarantine}", inline=False)
			embed.add_field(name="Logging Channel:", value=f"{channel}", inline=False)
			if event_manager_error != '':
				embed.add_field(name="<a:nat_warning:1062998119899484190> Warning: <a:nat_warning:1062998119899484190>", value=f"{event_manager_error}", inline=False)

			self.view.stop()
			dank_pool_view =  Dank_Pool_Panel(interaction)

			# Initialize the button
			if data['enable_logging']:
				dank_pool_view.children[0].style = discord.ButtonStyle.green
				dank_pool_view.children[0].label = 'Logs Enabled'
				dank_pool_view.children[0].emoji = "<:tgk_active:1082676793342951475>"
			else:
				dank_pool_view.children[0].style = discord.ButtonStyle.red
				dank_pool_view.children[0].label = 'Logs Disabled'
				dank_pool_view.children[0].emoji = "<:tgk_deactivated:1082676877468119110>"

			dank_pool_view.add_item(Serversettings_Dropdown(0))
			
			await interaction.response.edit_message(embed=embed, view=dank_pool_view)
			dank_pool_view.message = await interaction.original_response()

		elif self.values[0] == "Mafia Logs Setup":

			data = await interaction.client.mafiaConfig.find(interaction.guild.id)
			if data is None:
				data = {"_id": interaction.guild.id, "enable_logging":False, "logs_channel": None, "message_logs": []}
				await interaction.client.mafiaConfig.upsert(data)

			channel = data['logs_channel']

			if channel is None:
				channel = f"**`None`**"
			else:
				channel = interaction.guild.get_channel(int(channel))
				if channel is not None:
					channel = f"**{channel.mention} (`{channel.name}`)**"
				else:
					data['logs_channel'] = None
					await interaction.client.mafiaConfig.upsert(data)
					channel = f"**`None`**"

			embed = discord.Embed(
				color=3092790,
				title="Mafia Logs Setup"
			)
			embed.add_field(name="Logging Channel:", value=f"{channel}", inline=False)

			self.view.stop()
			mafia_view = Mafia_Panel(interaction , data)

			# Initialize the button
			if data['enable_logging']:
				mafia_view.children[0].style = discord.ButtonStyle.green
				mafia_view.children[0].label = 'Logging Enabled'
				mafia_view.children[0].emoji = "<:tgk_active:1082676793342951475>"
			else:
				mafia_view.children[0].style = discord.ButtonStyle.red
				mafia_view.children[0].label = 'Logging Disabled'
				mafia_view.children[0].emoji = "<:tgk_deactivated:1082676877468119110>"

			mafia_view.add_item(Serversettings_Dropdown(1))

			await interaction.response.edit_message(embed=embed, view=mafia_view)
			mafia_view.message = await interaction.original_response()

		
		elif self.values[0] == "Server Lockdown":

			data = await interaction.client.lockdown.find(interaction.guild.id)
			if not data:
				data = {"_id": interaction.guild.id, "lockdown_profiles": []}
				await interaction.client.lockdown.upsert(data)

			if data['lockdown_profiles'] is None or len(data['lockdown_profiles']) == 0:
				profiles = f"` - ` **Add lockdown protocols when?**\n"
			else:
				profiles = ""
				for profile in data['lockdown_profiles']:
					profiles += f"` - ` **{profile.title()}**\n"

			embed = discord.Embed(
				color=3092790,
				title="Configure Server Lockdown"
			)
			embed.add_field(name="Declared protocols are:", value=f"{profiles}", inline=False)
			
			self.view.stop()
			lockdown_profile_view =  Lockdown_Profile_Panel(interaction)			
			lockdown_profile_view.add_item(Serversettings_Dropdown(2))
			await interaction.response.edit_message(embed=embed, view=lockdown_profile_view)
			lockdown_profile_view.message = await interaction.original_response()

			await interaction.message.edit(embed=embed, view=lockdown_profile_view)
			lockdown_profile_view.message = await interaction.original_response()
		else:
			await interaction.response.send_message(f'Invaid Interaction',ephemeral=True)

async def setup(bot):
	await bot.add_cog(serverUtils(bot))
	print(f"loaded serverUtils cog")