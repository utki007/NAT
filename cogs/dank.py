import datetime
import enum
import time as t
from typing import List, Union

import discord
import pandas as pd
from discord import Interaction, app_commands
from discord.ext import commands
from tabulate import tabulate

import time as t

from utils.embeds import get_invisible_embed


class Historical_Data(enum.Enum):
	Today = 1
	Yesterday = 2
	Day_Before_Yesterday = 3

@app_commands.guild_only()
class stats(commands.GroupCog, name="stats", description="Run server based commands"):
	def __init__(self, bot):
		self.bot = bot
		
	stats_group = app_commands.Group(name="stats", description="Get Fun Dank Memer Stats 📈")
	
	

	@app_commands.command(name="adventure", description="Get adventure related statistics 📊")
	# @app_commands.describe(historical_data = "Which Day's Data to See?")
	@app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
	# async def lockdown_start(self, interaction:  discord.Interaction, historical_data: Historical_Data):
	async def lockdown_start(self, interaction:  discord.Interaction):
		# await interaction.response.defer(ephemeral = False)
		today = str(datetime.date.today())
		user = interaction.user
		guild = interaction.guild

		stats_embed = discord.Embed(
			color=2829617,
			description=f"<a:nat_timer:1010824320672604260> **|** Fetching your stats...",
		)
		stats_embed.set_author(name=f"{user.display_name}'s Adventure Stats", icon_url=user.avatar.url)
		stats_embed.set_footer(text = f'{guild.name}', icon_url=guild.icon.url)
		stats_embed.set_image(url='https://cdn.discordapp.com/attachments/999555672733663285/1144576365430059048/calculation-math.gif')

		await interaction.response.send_message(embed = stats_embed, ephemeral=False)
	
		start = t.time()
		data = await interaction.client.dankAdventureStats.find(user.id)
		if data is None:
			return await interaction.edit_original_response(embed= await get_invisible_embed(f'You have not played any adventure yet!'))
		if today not in data['rewards'].keys():
			return await interaction.edit_original_response(embed= await get_invisible_embed(f'You have not played adventure today!'))
		
		data = data['rewards'][today]		

		bullet = '<:ace_replycont:1082575852061073508>'
		last_bullet = '<:ace_reply:1082575762856620093>'

		list_of_items = []
		dict = data['items']

		for key in dict.keys():
			item_price = int((await interaction.client.dankItems.find(key))['price'])
			amount = round(dict[key] * item_price)
			temp_dict = {"Name": key , "Quantity":str(dict[key]),"Amount": f'{amount:,}', "dummy":amount}
			list_of_items.append(temp_dict)
		
		df = pd.DataFrame(list_of_items)
		df = df.sort_values(by=['dummy'],ascending=False)
		df.reset_index(inplace = True, drop = True)
		total_earn = df['dummy'].sum()
		df.drop(['dummy'], axis=1,inplace=True)
		df["Item"] = df[['Quantity', 'Name']].agg('x '.join, axis=1)
		# df["Net Amount"] = f'[0;37m' + df["Amount"] + f'[0;0m'
		# df["Item"] = f'[1;36m' + df["Item"] + f'[0;0m'
		df["Net Amount"] =  df["Amount"] 
		df["Item"] =  df["Item"] 
		df.drop(['Name'], axis=1,inplace=True)
		df.drop(['Quantity'], axis=1,inplace=True)
		df.drop(['Amount'], axis=1,inplace=True)
		df.index += 1 
		# item_str = f'```fix\n{tabulate(df.head(),["[4;34mItems[0;0m","[4;34mAmount[0;0m"], showindex=False, tablefmt="rounded_outline")}\n```'
		item_str = f'```fix\n{tabulate(df.head(),["Items","Amount"], showindex=False, tablefmt="rounded_outline")}\n```'
		# Overall Statistics
		ostats = f'{bullet} **Grinded:** ⏣ {data["dmc_from_adv"]+total_earn:,}\n'
		if data['frags'] > 0:
			ostats += f'{bullet} **Skin Fragments:**  __{data["frags"]}__\n'
		ostats += f'{bullet} **Played:** __{data["total_adv"]}__ adventures\n'
		ostats += f'{last_bullet} **Won:** __{data["reward_adv"]}__ adventures\n'
		stats_embed.add_field(name='Overall Statistics', value=ostats, inline=False)

		# Luck Multipliers
		luck_dict = data['luck']
		if len(luck_dict) > 0:

			if len(luck_dict) == 1:
				stats_embed.add_field(name='Luck Multipliers', value=f'{last_bullet} {list(luck_dict.values())[0]}x +{list(luck_dict.keys())[0]}%', inline=True)

			elif len(luck_dict) > 1:
				luck_str = ''
				for key, value in luck_dict.items():
					if key == list(luck_dict.keys())[-1]:
						luck_str += f'{last_bullet} {value}x +{key}%'
					else:
						luck_str += f'{bullet} {value}x +{key}%\n'
				stats_embed.add_field(name='Luck Multipliers', value=luck_str, inline=True)
		
		# XP Multipliers
		xp_dict = data['xp']
		if len(xp_dict) > 0:

			if len(xp_dict) == 1:
				stats_embed.add_field(name='XP Multipliers', value=f'{last_bullet} {list(xp_dict.values())[0]}x {list(xp_dict.keys())[0]} XP', inline=True)

			elif len(xp_dict) > 1:
				xp_str = ''
				for key, value in xp_dict.items():
					if key == list(xp_dict.keys())[-1]:
						xp_str += f'{last_bullet} {value}x {key} XP'
					else:
						xp_str += f'{bullet} {value}x {key} XP\n'
				stats_embed.add_field(name='XP Multipliers', value=xp_str, inline=True)

		# Coins Multipliers
		coins_dict = data['coins']
		if len(coins_dict) > 0:

			if len(coins_dict) == 1:
				stats_embed.add_field(name='Coins Multipliers', value=f'{last_bullet} {list(coins_dict.values())[0]}x +{list(coins_dict.keys())[0]}%', inline=True)
			
			elif len(coins_dict) > 1:
				coins_str = ''
				for key, value in coins_dict.items():
					if key == list(coins_dict.keys())[-1]:
						coins_str += f'{last_bullet} {value}x +{key}%'
					else:
						coins_str += f'{bullet} {value}x +{key}%\n'
				stats_embed.add_field(name='Coins Multipliers', value=coins_str, inline=True)

		stats_embed.add_field(name="Top 5 Items Grinded:", value=f"{item_str}", inline=False)
		# stats_embed.set_thumbnail(url='https://cdn.discordapp.com/emojis/1114280462131666967.webp?size=56&quality=lossless')

		stats_embed.set_image(url=None)
		stats_embed.description = None
		stats_embed.set_footer(text=f"{guild.name} • Time Taken: {round(t.time()-start,2)}s", icon_url=guild.icon.url)
		return await interaction.edit_original_response(embed=stats_embed)

async def setup(bot):
	await bot.add_cog(
		stats(bot),
		guilds = [
			discord.Object(785839283847954433), 
			discord.Object(999551299286732871),
			discord.Object(1072079211419938856),
			discord.Object(833719462016057364)
		]
	)
	print(f"loaded stats cog")