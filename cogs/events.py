import datetime
import traceback
from io import BytesIO

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from utils.convertor import dict_to_tree


class events(commands.Cog):
	
	def __init__(self, bot):
		self.bot = bot
		self.bot.tree.on_error = self.on_app_command_error
	
	async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
		if isinstance(error, app_commands.CommandOnCooldown):
			m, s = divmod(error.retry_after, 60)
			h, m = divmod(m, 60)
			if int(h) == 0 and int(m) == 0:
				return await interaction.response.send_message(f"The command is under a cooldown of **{int(s)} seconds** to prevent abuse!", ephemeral=True)
			elif int(h) == 0 and int(m) != 0:
				return await interaction.response.send_message(
					f"The command is under a cooldown of **{int(m)} minutes and {int(s)} seconds** to prevent abuse!", ephemeral=True,
				)
			else:
				return await interaction.response.send_message(
					f"The command is under a cooldown of **{int(h)} hours, {int(m)} minutes and {int(s)} seconds** to prevent abuse!", ephemeral=True,
				)
		elif isinstance(error, app_commands.MissingPermissions):
			url = "https://cdn.discordapp.com/attachments/999555672733663285/1063392550192431134/access_Denied.png"
			warning = discord.Embed(
				color=0xffd300,
				title=f"This incident has been reported!",
				description=f"{error} Imagine trying though <a:nat_roflfr:1063393491549429801>")
			warning.set_thumbnail(url=url)

			perm = str(error).replace("You are missing ","",1)
			perm = perm.replace("to run this command.","",1)
			# for logging
			logg = discord.Embed(
				title="__Missing Perms!__",
				description=
				f"` - `   **Command:** `/{interaction.command.qualified_name}`\n"
				f"` - `   **Used at:** <t:{int(datetime.datetime.timestamp(interaction.created_at))}>\n"
				f'` - `   **User:** {interaction.user.mention}(`{interaction.user.id}`)\n'
				f'` - `   **Missing:** {perm}\n',
				colour=discord.Color.random(),
				timestamp=datetime.datetime.utcnow()
			)

			logg.set_footer(
				text=f"Sanctioned by: {interaction.user.name}", icon_url=interaction.user.avatar.url)

			log_channel = self.bot.get_channel(1063395262757875822)

			await interaction.response.send_message(embed=warning, ephemeral=False)
			message = await interaction.original_response()

			view = discord.ui.View()
			view.add_item(discord.ui.Button(emoji="<:tgk_link:1105189183523401828>",label=f'Used at', url=f"{message.jump_url}"))
			return await log_channel.send(embed=logg, view=view)
			# await interaction.response.send_message(f"You are missing the required permissions to use this command!", ephemeral=True)
		elif isinstance(error, app_commands.CheckFailure):
			if int(interaction.data['id']) == 1150390920433381406:
				return
			url = "https://cdn.discordapp.com/attachments/999555672733663285/1063392550192431134/access_Denied.png"
			warning = discord.Embed(
				color=0xffd300,
				title=f"Unauthorized!",
				description=f"Hey! You lack permission to use this command. Imagine trying though <a:nat_roflfr:1063393491549429801>")
			warning.set_thumbnail(url=url)
			if "check functions for command 'serversettings'" in str(error):
				warning.title = "Only Server Owners can use this!"
			# else:
			# 	embed.description = f"{error} Imagine trying though <a:nat_roflfr:1063393491549429801>"
			return await interaction.response.send_message(embed=warning, ephemeral=False)
		elif isinstance(error, app_commands.MissingRole):
			url = "https://cdn.discordapp.com/attachments/999555672733663285/1063392550192431134/access_Denied.png"
			warning = discord.Embed(
				color=0xffd300,
				title=f"This incident has been reported!",
				description=f"{error} Imagine trying though <a:nat_roflfr:1063393491549429801>")
			warning.set_thumbnail(url=url)

			perm = str(error).replace("You are missing ","",1)
			perm = perm.replace("to run this command.","",1)
			# for logging
			logg = discord.Embed(
				title="__Missing Perms!__",
				description=
				f"` - `   **Command:** `/{interaction.command.qualified_name}`\n"
				f"` - `   **Used at:** <t:{int(datetime.datetime.timestamp(interaction.created_at))}>\n"
				f'` - `   **User:** {interaction.user.mention}(`{interaction.user.id}`)\n'
				f'` - `   **Missing:** {perm}\n',
				colour=discord.Color.random(),
				timestamp=datetime.datetime.utcnow()
			)

			logg.set_footer(
				text=f"Sanctioned by: {interaction.user.name}", icon_url=interaction.user.avatar.url)

			log_channel = self.bot.get_channel(1063395262757875822)

			await interaction.response.send_message(embed=warning, ephemeral=False)
			message = await interaction.original_response()

			view = discord.ui.View()
			view.add_item(discord.ui.Button(emoji="<:tgk_link:1105189183523401828>",label=f'Used at', url=f"{message.jump_url}"))
			return await log_channel.send(embed=logg, view=view)
			# await interaction.response.send_message("You are missing the required role to use this command!", ephemeral=True)
		elif isinstance(error, app_commands.MissingAnyRole):
			return await interaction.response.send_message("You are missing the required role to use this command!", ephemeral=True)
		else:
			embed = discord.Embed(description="**Error:** {}".format(error), color=discord.Color.red())
			try:
				await interaction.response.send_message(embed=embed)
			except:
				await interaction.followup.send(embed=embed, ephemeral=True)

		tree_format = interaction.data.copy()
		tree_format = dict_to_tree(tree_format)
		message = await interaction.original_response()

		embed = discord.Embed(title="Error", color=0x2f3136, description="")
		embed.description += f"**Interaction Data Tree**\n```yaml\n{tree_format}\n```"
		embed.add_field(name="Channel", value=f"{interaction.channel.mention} | {interaction.channel.id}", inline=False)
		embed.add_field(name="Guild", value=f"{interaction.guild.name} | {interaction.guild.id}", inline=False)
		embed.add_field(name="Author", value=f"{interaction.user.mention} | {interaction.user.id}", inline=False)
		embed.add_field(name="Command", value=f"{interaction.command.name if interaction.command else 'None'}",
						inline=False)
		embed.add_field(name="Message", value=f"[Jump]({message.jump_url})", inline=False)

		error_traceback = "".join(traceback.format_exception(type(error), error, error.__traceback__, 4))
		buffer = BytesIO(error_traceback.encode('utf-8'))
		file = discord.File(buffer, filename=f"Error-{interaction.command.name}.log")
		buffer.close()

		url = "https://canary.discord.com/api/webhooks/1145313909109174292/cFcaeWMF6inKN_DRZVZx0c1WExDUq0VvNtUiYd_GiBLzemMUyuGyq0P7eHWRpMExBjLY"

		async with aiohttp.ClientSession() as session:
			webhook = discord.Webhook.from_url(url, session=session)
			await webhook.send(embed=embed,
								avatar_url=interaction.client.user.avatar.url if interaction.client.user.avatar else interaction.client.user.default_avatar,
								username=f"{interaction.client.user.name}'s Error Logger", file=file)

	@commands.Cog.listener()
	async def on_ready(self):
		print(f"{self.__class__.__name__} Cog has been loaded\n-----")
	
	@commands.Cog.listener()
	async def on_command_error(self, ctx, error):

		if isinstance(error, commands.CommandOnCooldown):
			# If the command is currently on cooldown trip this
			m, s = divmod(error.retry_after, 60)
			h, m = divmod(m, 60)
			if int(h) == 0 and int(m) == 0:
				await ctx.send(f"The command is under a cooldown of **{int(s)} seconds** to prevent abuse!")
			elif int(h) == 0 and int(m) != 0:
				await ctx.send(
					f"The command is under a cooldown of **{int(m)} minutes and {int(s)} seconds** to prevent abuse!"
				)
			else:
				await ctx.send(
					f"The command is under a cooldown of **{int(h)} hours, {int(m)} minutes and {int(s)} seconds** to prevent abuse!"
				)
		elif isinstance(error, commands.CheckFailure):
			# If the command has failed a check, trip this
			await ctx.send("Hey! You lack permission to use this command.")

		elif isinstance(error, commands.CommandInvokeError):
			return
			
		elif isinstance(error, commands.CommandNotFound):
			return
		else:
			#raise error
			embed = discord.Embed(color=0xE74C3C, 
				description=f"<:tgk_warning:840638147838738432> **|** Error: `{error}`")
			await ctx.send(embed=embed)

async def setup(bot):
	await bot.add_cog(events(bot))