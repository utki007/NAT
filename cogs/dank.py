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
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps
from tabulate import tabulate
from utils.convertor import millify

from utils.embeds import get_invisible_embed


class Historical_Data(enum.Enum):
	Today = 1
	Yesterday = 2
	Day_Before_Yesterday = 3

@app_commands.guild_only()
class dank(commands.GroupCog, name="dank", description="Run dank based commands"):
	def __init__(self, bot):
		self.bot = bot
		
	adventure_group = app_commands.Group(name="adventure", description="Get Fun Adventure Stats 📈")
	
				
	async def round_pfp_4_advtop3(self, pfp: discord.User | discord.Member | discord.Guild):
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

	async def round_pfp_4_itemlb(self, pfp: discord.User | discord.Member | discord.Guild):
		if pfp.avatar is None:
			pfp = pfp.default_avatar.with_format('png')
		else:
			pfp = pfp.avatar.with_format('png')

		pfp = BytesIO(await pfp.read())
		pfp = Image.open(pfp)
		pfp = pfp.resize((100, 100), Image.Resampling.LANCZOS).convert('RGBA')

		bigzise = (pfp.size[0] * 3, pfp.size[1] * 3)
		mask = Image.new('L', bigzise, 0)
		draw = ImageDraw.Draw(mask)
		draw.ellipse((0, 0) + bigzise, fill=255)
		mask = mask.resize(pfp.size, Image.Resampling.LANCZOS)
		mask = ImageChops.darker(mask, pfp.split()[-1])
		pfp.putalpha(mask)

		return pfp

	async def create_adv_top3(self, guild: discord.Guild, event_name:str, data: list):
		template = Image.open('./assets/leaderboard_template.png')
		guild_icon = await self.round_pfp_4_advtop3(guild)
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
			user_icon = await self.round_pfp_4_advtop3(user)
			template.paste(user_icon, winne_postions[index]['icon'], user_icon)
			draw.text(winne_postions[index]['name'], f"{i['name']}", font=winner_name_font, fill="#9A9BD5")
			draw.text(winne_postions[index]['donated'], f"⏣ {i['donated']:,}", font=winner_exp_font, fill="#A8A8C8")

		return template
	
	async def create_item_lb(self, guild: discord.Guild, data: list):
		image = Image.open('./assets/item_leaderboard.png')

		draw = ImageDraw.Draw(image)
		footer_font = ImageFont.truetype('./assets/fonts/Symbola.ttf', 52)
		top_line = ImageFont.truetype("./assets/fonts/DejaVuSans.ttf", 66)
		multi_white = ImageFont.truetype("./assets/fonts/DejaVuSans.ttf", 52)
		item_font = ImageFont.truetype("./assets/fonts/DejaVuSans.ttf", 52)

		guild_icon = await self.round_pfp_4_itemlb(self.bot.user)
		image.paste(guild_icon, (100, 2025), guild_icon)
		
		# Grinded, Played, Won
		draw.text(xy=(130, 400), text=f'{data["grinded"]}', fill=(255, 211, 63), font=top_line, align="right", stroke_width=2)
		draw.text(xy=(730, 400), text=f'{data["played"]}', fill=(255, 211, 63), font=top_line, align="right", stroke_width=2)
		draw.text(xy=(1205, 400), text=str(data["won"]), fill=(255, 211, 63), font=top_line, align="right", stroke_width=2)

		# Luck, XP
		draw.text(xy=(410, 850), text=f'Luck', fill=(80, 200, 120), font=item_font, align="right", stroke_width=2)
		draw.text(xy=(360, 960), text=f'{data["luck"]["qty"]}', fill=(255, 211, 63), font=multi_white, align="right", stroke_width=2)
		draw.text(xy=(460, 960), text=f' {data["luck"]["rate"]}', fill=(255, 255, 255), font=multi_white, align="right", stroke_width=1)
		
		draw.text(xy=(960, 850), text=f'XP', fill=(80, 200, 120), font=item_font, align="right", stroke_width=2)
		draw.text(xy=(910, 960), text=f'{data["xp"]["qty"]}', fill=(255, 211, 63), font=multi_white, align="right", stroke_width=2)
		draw.text(xy=(1010, 960), text=f'{data["xp"]["rate"]}', fill=(255, 255, 255), font=multi_white, align="right", stroke_width=1)
		
		# Items
		for item in data["items"].keys():
			draw.text(xy=(142, 1329+(int(item)*100)), text=f"{data['items'][item]['qty']}x ", fill=(255, 211, 63), font=item_font, align="right", stroke_width=2)
			draw.text(xy=(458, 1329+(int(item)*100)), text=f"{data['items'][item]['name']} ", fill=(255, 255, 255), font=item_font, align="right", stroke_width=1)
			draw.text(xy=(1017, 1329+(int(item)*100)), text=f"⏣ {data['items'][item]['worth']}", fill=(255, 255, 255), font=item_font, align="left", stroke_width=1)

		# for footer
		draw.text(xy=(245, 2048), text=f'Dank Adventure stats by: {self.bot.user}', fill=(80, 200, 120), font=footer_font, align="right", stroke_width=1)
		
		return image
	
	@adventure_group.command(name="stats", description="Get adventure related statistics 📊")
	@app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
	async def adventure_stats(self, interaction:  discord.Interaction, user: discord.Member = None):
		await interaction.response.defer(ephemeral = False)
		today = str(datetime.date.today())
		if user is None:
			user = interaction.user
		guild = interaction.guild

		start = t.time()
		stats_embed = discord.Embed(
			color=2829617
		)
		if user.avatar is None:
			icon_url = user.default_avatar.url
		else:
			icon_url = user.avatar.url
		stats_embed.set_author(name=f"Adventure Stats", icon_url=icon_url)
	
		data = await interaction.client.dankAdventureStats.find(user.id)
		if data is None:
			return await interaction.edit_original_response(embed= await get_invisible_embed(f'You have not played any adventure yet!'))
		if today not in data['rewards'].keys():
			return await interaction.edit_original_response(embed= await get_invisible_embed(f'You have not played adventure today!'))
		
		data = data['rewards'][today]		

		if len(data['items']) > 0:
			
			item_str = f''
			list_of_items = []
			dict = data['items']

			for item_name in dict.keys():
				item_price = int((await interaction.client.dankItems.find(item_name))['price'])
				amount = round(dict[item_name] * item_price)
				temp_dict = {"Name": item_name , "Quantity":str(dict[item_name]),"Amount": await millify(amount), "dummy":amount}
				list_of_items.append(temp_dict)
			
			df = pd.DataFrame(list_of_items)
			df = df.sort_values(by=['dummy'],ascending=False)
			df.reset_index(inplace = True, drop = True)
			total_earn = data["dmc_from_adv"] + df['dummy'].sum()
			df.drop(['dummy'], axis=1,inplace=True)
			df.index += 1 
			df = df.head(5)

			leaderboard = {
				"grinded": await millify(total_earn),
				"played": data["total_adv"],
				"won": data["reward_adv"],
				"luck": data["luck"],
				"xp": data["xp"],
				"items": {}
			}

			# get higest luck from leaderboard['luck']
			luck_dict = leaderboard['luck']
			if len(luck_dict) > 0:
				luck_keys = list(luck_dict.keys())
				luck_keys.sort(reverse=True)
				leaderboard['luck'] = {'qty': f"{luck_dict[luck_keys[0]]}x" , 'rate': f'+{luck_keys[0]}%'}
			else:
				leaderboard['luck'] = {'qty': '0x' , 'rate': '+0%'}
			
			# get higest xp from leaderboard['xp']
			xp_dict = leaderboard['xp']
			if len(xp_dict) > 0:
				xp_keys = list(xp_dict.keys())
				xp_keys.sort(reverse=True)
				leaderboard['xp'] = {'qty': f"{xp_dict[xp_keys[0]]}x" , 'rate': f'{xp_keys[0]}'}
			else:
				leaderboard['xp'] = {'qty': '0x' , 'rate': '0'}

			for index in df.index:
				#  for quantity
				quantity = f'{df["Quantity"][index]}' if int(df["Quantity"][index]) >= 10 else f'  {df["Quantity"][index]}'
				
				# for worth
				amt = df["Amount"][index].split(" ")[0]
				if float(amt) >= 100.0:
					worth = f'{df["Amount"][index]}'
				elif float(amt) >= 10.0:
					worth = f'  {df["Amount"][index]}'
				else:
					worth = f'    {df["Amount"][index]}'

				# for item name
				item_name = df['Name'][index] 
				if len(item_name) > 15:
					item_name = item_name[:12] + '...'

				leaderboard['items'][str(index)]  = {'name': item_name,'qty': quantity,'worth': worth}
			
			image = await self.create_item_lb(interaction.guild, leaderboard)

		else:
			total_earn = 0
			image = None
			item_str = '```fix\nNo Items Grinded Yet!\n```'

		if item_str != '':
			stats_embed.add_field(name="Top 5 Items Grinded:", value=f"{item_str}", inline=False)
		
		if guild.icon is None:
			icon_url = guild.default_avatar.url
		else:
			icon_url = guild.icon.url
		
		if image is None:
			stats_embed.set_footer(text=f"{guild.name} • Time Taken: {round(t.time()-start,2)}s", icon_url=icon_url)
			return await interaction.edit_original_response(embed=stats_embed)

		with BytesIO() as image_binary:
			image.save(image_binary, 'PNG')
			image_binary.seek(0)
			file=discord.File(fp=image_binary, filename=f'item_leaderboard.png')
			stats_embed.description = None
			stats_embed.set_image(url=f'attachment://item_leaderboard.png')
			stats_embed.remove_footer()
			await interaction.edit_original_response(embed=stats_embed, attachments=[file])
			image_binary.close()

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
			dmc = user_record['rewards'][today]['dmc_from_adv']
			if len(items) == 0:
				continue
			
			for item in items.keys():
				item_price = item_price_dict[item]
				amount = round(items[item] * item_price)
				temp_dict = {"Name": item , "Quantity":str(items[item]),"Amount": amount}
				list_of_items.append(temp_dict)				
			df = pd.DataFrame(list_of_items)
			df = df.sort_values(by=['Amount'],ascending=False)
			final_data[user_record['_id']] = df['Amount'].sum() + dmc

		k = Counter(final_data)
		top_3 = k.most_common(3)

		leaderboard = []
		for user_record in top_3:
			user = interaction.guild.get_member(user_record[0])
			if user is None:
				user = await interaction.client.fetch_user(user_record[0])
			amount = user_record[1]
			if len(user.display_name) > 18:
				name = user.display_name[:15] + '...'
			else:
				name = user.display_name
			leaderboard.append({'user': user,'name': name,'donated': amount}) 

		
		image = await self.create_adv_top3(interaction.guild, "🐸 Dank Memer 🐸", leaderboard)

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
		embed.description = f'## Adventure Stats has been moved!!\n- </dank adventure stats:1146318807984513096>\n- </dank adventure leaderboard:1146318807984513096>'
		return await interaction.response.send_message(embed = embed, ephemeral=False)


async def setup(bot):
	await bot.add_cog(dank(bot))
	await bot.add_cog(stats(bot))
	print(f"loaded stats cog")