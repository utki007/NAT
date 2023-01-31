import discord

async def get_success_embed(content):
	success_embed = discord.Embed(
		color=0x43b581,
		description=f'<a:nat_check:1010969401379536958> **|** {content}'
	)
	return success_embed

async def get_warning_embed(content):
	warning_embed = discord.Embed(
		color=0xffd300,
		description=f"<a:nat_warning:1062998119899484190> **|** {content}"
	)
	return warning_embed

async def get_error_embed(content):
	error_embed = discord.Embed(
		color=0xDA2A2A,
		description=f"<a:nat_cross:1010969491347357717> **|** {content}"
	)
	return error_embed