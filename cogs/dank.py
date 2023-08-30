from collections import Counter
import datetime
import enum
from io import BytesIO
import time as t
from typing import List, Union

import discord
import pandas as pd
from discord import Interaction, app_commands
from discord.ext import commands
from tabulate import tabulate

import time as t

from utils.embeds import get_invisible_embed
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageChops

class Historical_Data(enum.Enum):
	Today = 1
	Yesterday = 2
	Day_Before_Yesterday = 3

@app_commands.guild_only()
class dank(commands.GroupCog, name="dank", description="Run dank based commands"):
	def __init__(self, bot):
		self.bot = bot
		
	adventure_group = app_commands.Group(name="adventure", description="Get Fun Adventure Stats 📈")
	
				
	async def round_pfp(self, pfp: discord.User | discord.Member | discord.Guild):
		if isinstance(pfp, discord.Member) or isinstance(pfp, discord.User):
			if pfp.avatar is None:
				pfp = pfp.default_avatar.with_format('png')
			else:
				pfp = pfp.avatar.with_format('png')
		else:
				pfp = pfp.icon.with_format('png')

		pfp = BytesIO(await pfp.read())
		pfp = Image.open(pfp)
		pfp = pfp.resize((80, 80), Image.Resampling.LANCZOS).convert('RGBA')

		bigzise = (pfp.size[0] * 3, pfp.size[1] * 3)
		mask = Image.new('L', bigzise, 0)
		draw = ImageDraw.Draw(mask)
		draw.ellipse((0, 0) + bigzise, fill=255)
		mask = mask.resize(pfp.size, Image.Resampling.LANCZOS)
		mask = ImageChops.darker(mask, pfp.split()[-1])
		pfp.putalpha(mask)

		return pfp

	async def create_winner_card(self, guild: discord.Guild, event_name:str, data: list):
		template = Image.open('./assets/leaderboard_template.png')
		guild_icon = await self.round_pfp(guild)
		template.paste(guild_icon, (15, 16), guild_icon)

		draw = ImageDraw.Draw(template)
		font = ImageFont.truetype('./assets/fonts/Symbola.ttf', 24)
		winner_name_font = ImageFont.truetype('./assets/fonts/Symbola.ttf', 28)
		winner_exp_font = ImageFont.truetype('./assets/fonts/DejaVuSans.ttf', 20)

		winne_postions = {
			#postions of the winners, pfp and name and donation
			0: {'icon': (58, 150), 'name': (160, 165), 'donated': (160, 202)},
			1: {'icon': (58, 270), 'name': (160, 285), 'donated': (160, 322)},
			2: {'icon': (58, 390), 'name': (160, 405), 'donated': (160, 442)}}

		draw.text((125, 28), f"{event_name}", font=winner_name_font, fill="#9A9BD5") #guild name 
		draw.text((118, 61), f"📈 Adventure Top 3 📈", font=font, fill="#9A9BD5") #event name

		for i in data[:3]:
			user = i['user']
			index = data.index(i)
			user_icon = await self.round_pfp(user)
			template.paste(user_icon, winne_postions[index]['icon'], user_icon)
			draw.text(winne_postions[index]['name'], f"{i['name']}", font=winner_name_font, fill="#9A9BD5")
			draw.text(winne_postions[index]['donated'], f"⏣ {i['donated']:,}", font=winner_exp_font, fill="#A8A8C8")

		return template
	
	async def create_item_lb(self, guild: discord.Guild, data: list):
		template = Image.open('./assets/item_lb_1.png')

		draw = ImageDraw.Draw(template)
		winner_name_font = ImageFont.truetype('./assets/fonts/Lobster.ttf', 14)
		winner_exp_font = ImageFont.truetype('./assets/fonts/Lobster.ttf', 11)

		item_lb_positions = {
			# postions of the winners, pfp and name and donation
			0: {'item': (50, 40), 'amount': (207, 45)},
			1: {'item': (50, 72), 'amount': (207, 78)},
			2: {'item': (50, 105), 'amount': (207, 111)},
			3: {'item': (50, 137), 'amount': (207, 145)}, 
			4: {'item': (50, 170), 'amount': (207, 180)}
		}

		for i in data:
			index = data.index(i)
			draw.text(item_lb_positions[index]['item'], f"{i['item']}", font=winner_name_font, fill="#ffffff")
			draw.text(item_lb_positions[index]['amount'], f"⏣ {i['amount']:,}", font=winner_exp_font, fill="#ffffff")

		return template
	
	@adventure_group.command(name="stats", description="Get adventure related statistics 📊")
	# @app_commands.describe(historical_data = "Which Day's Data to See?")
	@app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
	async def adventure_stats(self, interaction:  discord.Interaction, user: discord.Member = None):
		await interaction.response.defer(ephemeral = False)
		today = str(datetime.date.today())
		if user is None:
			user = interaction.user
		guild = interaction.guild

		start = t.time()
		stats_embed = discord.Embed(
			color=2829617,
			# description=f"<a:nat_timer:1010824320672604260> **|** Fetching your stats...",
		)
		stats_embed.set_author(name=f"{user.display_name}'s Adventure Stats", icon_url=user.avatar.url)
		stats_embed.set_footer(text = f'{guild.name}', icon_url=guild.icon.url)
		# stats_embed.set_image(url='https://cdn.discordapp.com/attachments/999555672733663285/1144576365430059048/calculation-math.gif')

		# await interaction.response.send_message(embed = stats_embed, ephemeral=False)
	
		data = await interaction.client.dankAdventureStats.find(user.id)
		if data is None:
			return await interaction.edit_original_response(embed= await get_invisible_embed(f'You have not played any adventure yet!'))
		if today not in data['rewards'].keys():
			return await interaction.edit_original_response(embed= await get_invisible_embed(f'You have not played adventure today!'))
		
		data = data['rewards'][today]		

		bullet = '<:ace_replycont:1082575852061073508>'
		last_bullet = '<:ace_reply:1082575762856620093>'

		if len(data['items']) > 0:
			
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
		
		else:
			total_earn = 0
			item_str = '```fix\nNo Items Grinded Yet!\n```'

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

		# stats_embed.set_image(url=None)
		# stats_embed.description = None
		stats_embed.set_footer(text=f"{guild.name} • Time Taken: {round(t.time()-start,2)}s", icon_url=guild.icon.url)
		return await interaction.edit_original_response(embed=stats_embed)

	@adventure_group.command(name="leaderboard", description="Get adventure leaderboard 📊")
	@app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
	async def adventure_leaderboard(self, interaction:  discord.Interaction):
		await interaction.response.defer(ephemeral = False)
		stats_embed = discord.Embed(
			color=2829617,
			# description=f"<a:nat_timer:1010824320672604260> **|** Fetching adventure leaderboard...",
		)
		# await interaction.response.send_message(embed = stats_embed, ephemeral=False)

		today = str(datetime.date.today())
		data = await interaction.client.dankAdventureStats.get_all()
		data = [data for data in data if today in data['rewards'].keys()]

		final_data = {}
		item_prices = await interaction.client.dankItems.get_all()
		item_price_dict = {}
		for item in item_prices:
			item_price_dict[item['_id']] = int(item['price'])

		for user_record in data:
			list_of_items = []
			items = user_record['rewards'][today]['items']
			if len(items) == 0:
				continue
			
			for item in items.keys():
				item_price = item_price_dict[item]
				amount = round(items[item] * item_price)
				temp_dict = {"Name": item , "Quantity":str(items[item]),"Amount": amount}
				list_of_items.append(temp_dict)				
			df = pd.DataFrame(list_of_items)
			df = df.sort_values(by=['Amount'],ascending=False)
			final_data[user_record['_id']] = df['Amount'].sum()

		k = Counter(final_data)
		top_3 = k.most_common(3)

		leaderboard = []
		for user_record in top_3:
			user = await interaction.client.fetch_user(user_record[0])
			amount = user_record[1]
			if len(user.display_name) > 18:
				name = user.display_name[:15] + '...'
			else:
				name = user.display_name
			leaderboard.append({'user': user,'name': name,'donated': amount}) 

		
		image = await self.create_winner_card(interaction.guild, "🐸 Dank Memer 🐸", leaderboard)

		with BytesIO() as image_binary:
			image.save(image_binary, 'PNG')
			image_binary.seek(0)
			file=discord.File(fp=image_binary, filename=f'adventure_leaderboard.png')
			stats_embed.description = None
			stats_embed.set_image(url=f'attachment://adventure_leaderboard.png')
			await interaction.edit_original_response(embed=stats_embed, attachments=[file])
			image_binary.close()


@app_commands.guild_only()
class stats(commands.GroupCog, name="stats", description="Run server based commands"):
	def __init__(self, bot):
		self.bot = bot	

	@app_commands.command(name="adventure", description="Get adventure related statistics 📊")
	@app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
	async def adventure_Stats(self, interaction:  discord.Interaction):
		embed = await get_invisible_embed(f'You have not played any adventure yet!')
		embed.description = f'## Adventure Stats has been moved!!\n- </dank adventure stats:1146314513688309790>\n- </dank adventure leaderboard:1146314513688309790>'
		return await interaction.response.send_message(embed = embed, ephemeral=False)


async def setup(bot):
	await bot.add_cog(dank(bot))
	await bot.add_cog(stats(bot))
	print(f"loaded stats cog")