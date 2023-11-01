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
class dank(commands.GroupCog, name="adventure", description="Get Fun Adventure Stats 📈"):
	def __init__(self, bot):
		self.bot = bot
					
	async def round_pfp_4_advtop3(self, pfp: discord.User | discord.Member | discord.Guild):
		if isinstance(pfp, discord.Member) or isinstance(pfp, discord.User):
			if pfp.avatar is None:
				pfp = pfp.default_avatar.with_format('png')
			else:
				pfp = pfp.avatar.with_format('png')
		else:
				if pfp.icon is None:
					return None
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

	async def round_pfp(self, user: discord.User | discord.Member, size: tuple):
		if user.avatar is None:
			pfp = user.default_avatar.with_format('png')
		else:
			pfp = user.avatar.with_format('png')
		
		pfp = BytesIO(await pfp.read())
		pfp = Image.open(pfp)
		pfp = pfp.resize(size, Image.Resampling.LANCZOS).convert('RGBA')

		bigzise = (pfp.size[0] * 3, pfp.size[1] * 3)
		mask = Image.new('L', bigzise, 0)
		draw = ImageDraw.Draw(mask)
		draw.ellipse((0, 0) + bigzise, fill=255)
		mask = mask.resize(pfp.size, Image.Resampling.LANCZOS)
		mask = ImageChops.darker(mask, pfp.split()[-1])
		pfp.putalpha(mask)
		
		return pfp

	async def create_adv_top3(self, data: dict, user_position: int, total_users: int):
		image = Image.open('./assets/adv_lb_card.png')
		crown = Image.open('./assets/crown.png')
		draw = ImageDraw.Draw(image)

		draw.text(xy=(160, 480), text=f"Adventure Leaderboard", fill=(0, 0, 1), font=ImageFont.truetype("./assets/fonts/DejaVuSans.ttf", 100), stroke_width=4, spacing=8)
		draw.text(xy=(500, 630), text=f"Rank: #{user_position}/{total_users}", fill=(0, 0, 1), font=ImageFont.truetype("./assets/fonts/DejaVuSans.ttf", 81), stroke_width=2, spacing=8)
		
		# for top 1
		pfp = await self.round_pfp(data[1]['user'], (280, 280))
		image.paste(pfp, (239, 1090), pfp)
		image.paste(crown, (102, 918), crown)
		draw.text(xy=(680, 1137), text=data[1]['name'], fill=(254, 205, 61), font=ImageFont.truetype("./assets/fonts/Symbola.ttf", 100), stroke_width=2, spacing=10)
		draw.text(xy=(680, 1250), text=f"⏣ {await millify(data[1]['amount'])}", fill=(80, 200, 120), font=ImageFont.truetype("./assets/fonts/DejaVuSans.ttf", 100), stroke_width=2, spacing=10)

		# for top 2
		pfp = await self.round_pfp(data[2]['user'], (280, 280))
		image.paste(pfp, (239, 1870), pfp)
		draw.text(xy=(155, 2250), text=data[2]['name'], fill=(254, 205, 61), font=ImageFont.truetype("./assets/fonts/Symbola.ttf", 75), stroke_width=2, spacing=10)
		draw.text(xy=(155, 2350), text=f"⏣ {await millify(data[2]['amount'])}", fill=(80, 200, 120), font=ImageFont.truetype("./assets/fonts/DejaVuSans.ttf", 75), stroke_width=2, spacing=10)

		# for top 3
		pfp = await self.round_pfp(data[3]['user'], (280, 280))
		image.paste(pfp, (966, 1870), pfp)
		draw.text(xy=(885, 2250), text=data[3]['name'], fill=(254, 205, 61), font=ImageFont.truetype("./assets/fonts/Symbola.ttf", 75), stroke_width=2, spacing=10)
		draw.text(xy=(885, 2350), text=f"⏣ {await millify(data[3]['amount'])}", fill=(80, 200, 120), font=ImageFont.truetype("./assets/fonts/DejaVuSans.ttf", 75), stroke_width=2, spacing=10)

		return image
	
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
	
	@app_commands.command(name="stats", description="Get adventure related statistics 📊")
	@app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
	async def adventure_stats(self, interaction:  discord.Interaction, user: discord.Member = None):
		await interaction.response.defer(ephemeral = False)
		today = str(datetime.date.today())
		if user is None:
			user = interaction.user
		guild = interaction.guild
	
		data = await interaction.client.dankAdventureStats.find(user.id)
		if data is None:
			return await interaction.edit_original_response(embed= await get_invisible_embed(f'You have not played any adventure yet!'))
		if today not in data['rewards'].keys():
			return await interaction.edit_original_response(embed= await get_invisible_embed(f'You have not played adventure today!'))
		
		data = data['rewards'][today]		
		grind = 0
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
			grind = total_earn = data["dmc_from_adv"] + df['dummy'].sum()
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
				if 'K' in worth:
					worth = f'  {worth}'

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
		
		if image is None:
			return await interaction.edit_original_response(embed= await get_invisible_embed(f'Make sure to comeback after you have grinded more items!'))

		with BytesIO() as image_binary:
			image.save(image_binary, 'PNG')
			image_binary.seek(0)
			file=discord.File(fp=image_binary, filename=f'item_leaderboard.png')
			await interaction.edit_original_response(content= f'## Adventure Summary\n- **Showing For:** {user.mention} \n- **Total Grind:** ⏣ {grind:,}' ,attachments=[file], allowed_mentions=discord.AllowedMentions.none())
			image_binary.close()

	@app_commands.command(name="leaderboard", description="Get adventure leaderboard 📊")
	@app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
	async def adventure_leaderboard(self, interaction:  discord.Interaction):
		await interaction.response.defer(ephemeral = False)

		today = str(datetime.date.today())
		data = await interaction.client.dankAdventureStats.get_all()
		data = [data for data in data if today in data['rewards'].keys()]

		final_data = []
		item_prices = await interaction.client.dankItems.get_all()
		item_price_dict = {}
		for item in item_prices:
			item_price_dict[item['_id']] = int(item['price'])

		items_not_found = []
		for user_record in data:
			list_of_items = []
			items = user_record['rewards'][today]['items']
			dmc = user_record['rewards'][today]['dmc_from_adv']
			if len(items) == 0:
				continue
			
			for item in items.keys():
				if item not in item_price_dict.keys():
					items_not_found.append(item)
					continue
				else:
					item_price = item_price_dict[item]
				amount = round(items[item] * item_price)
				temp_dict = {"Name": item , "Quantity":str(items[item]),"Amount": amount}
				list_of_items.append(temp_dict)							
			df = pd.DataFrame(list_of_items)
			final_data.append({"user_id": user_record["_id"] , "amount" :  df["Amount"].sum()+dmc})

		if len(items_not_found) > 0:
			items_not_found = list(set(items_not_found))
			items_not_found = f"\n1. ".join([i for i in items_not_found])
			embed = await get_invisible_embed(f'\n1. {items_not_found}')
			embed.title = "Items not found in database"
			channel = await interaction.client.fetch_channel(1168987042697449522)
			await channel.send(embed=embed)
		df = pd.DataFrame(final_data)	
		df['rank'] = df['amount'].rank(method='max',ascending=False)
		top_3 = df.sort_values(by='rank',ascending=True).head(3)
		top_3.reset_index(inplace = True, drop = True)
		top_3.index += 1 


		user_data = df[df['user_id']==interaction.user.id]
		if len(user_data) == 0:
			user_position = '?'
		else:
			user_position = int(user_data['rank'].values[0])

		leaderboard = {1: None, 2: None, 3: None}
		for index in top_3.index:
			user = interaction.guild.get_member(top_3['user_id'][index])
			if user is None:
				user = await interaction.client.fetch_user(top_3['user_id'][index])
			amount = top_3['amount'][index]
			if len(user.display_name) > 12:
				name = user.display_name[:9] + '...'
			else:
				name = user.display_name
			leaderboard[index] = {'user': user, 'name': name, 'amount': amount}


		if None in leaderboard.values():
			return await interaction.followup.send(embed= await get_invisible_embed(f'Not enough players have played adventure today!'))
		
		image = await self.create_adv_top3(data=leaderboard, total_users=len(data), user_position=user_position)

		with BytesIO() as image_binary:
			image.save(image_binary, 'PNG')
			image_binary.seek(0)
			file=discord.File(fp=image_binary, filename=f'adventure_leaderboard.png')
			await interaction.edit_original_response( attachments=[file])
			image_binary.close()

async def setup(bot):
	await bot.add_cog(dank(bot))
	print(f"loaded stats cog")