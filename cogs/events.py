import discord
import datetime
from discord import app_commands
from discord.ext import commands
from utils.checks import Unauthorized


class events(commands.Cog):
	
	def __init__(self, bot):
		self.bot = bot
		self.bot.tree.on_error = self.on_app_command_error
	
	async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
		if isinstance(error, app_commands.CommandOnCooldown):
			m, s = divmod(error.retry_after, 60)
			h, m = divmod(m, 60)
			if int(h) == 0 and int(m) == 0:
				await interaction.response.send_message(f"The command is under a cooldown of **{int(s)} seconds** to prevent abuse!", ephemeral=True)
			elif int(h) == 0 and int(m) != 0:
				await interaction.response.send_message(
					f"The command is under a cooldown of **{int(m)} minutes and {int(s)} seconds** to prevent abuse!", ephemeral=True,
				)
			else:
				await interaction.response.send_message(
					f"The command is under a cooldown of **{int(h)} hours, {int(m)} minutes and {int(s)} seconds** to prevent abuse!", ephemeral=True,
				)
		elif isinstance(error, app_commands.CheckFailure):
			url = "https://cdn.discordapp.com/attachments/999555672733663285/1063392550192431134/access_Denied.png"
			warning = discord.Embed(
				color=0xffd300,
				title=f"Only Server Owners can use this!",
				description=f"Hey! You lack permission to use this command. Imagine trying though <a:nat_roflfr:1063393491549429801>")
			warning.set_thumbnail(url=url)
			await interaction.response.send_message(embed=warning, ephemeral=False)
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
			view.add_item(discord.ui.Button(label=f'Used at', url=f"{message.jump_url}"))
			await log_channel.send(embed=logg, view=view)
			# await interaction.response.send_message(f"You are missing the required permissions to use this command!", ephemeral=True)
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
			view.add_item(discord.ui.Button(label=f'Used at', url=f"{message.jump_url}"))
			await log_channel.send(embed=logg, view=view)
			# await interaction.response.send_message("You are missing the required role to use this command!", ephemeral=True)
		elif isinstance(error, app_commands.MissingAnyRole):
			await interaction.response.send_message("You are missing the required role to use this command!", ephemeral=True)
		else:
			embed = discord.Embed(description="**Error:** {}".format(error), color=discord.Color.red())
			try:
				
				await interaction.response.send_message(embed=embed)
			except:
				await interaction.followup.send(embed=embed, ephemeral=True)

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