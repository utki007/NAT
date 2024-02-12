import discord
from typing import List, Dict, Union, TypedDict

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

async def get_invisible_embed(content):
	invis_embed = discord.Embed(
		color=2829617,
		description=f"{content}"
	)
	return invis_embed

async def get_formated_embed(arguments: List[str], custom_lenth: int = None) -> Dict[str, str]:
	"""
	This fuctions creates a formated embed description fields

	Args:
		arguments (List[str]): The arguments to format the embed.
		custom_lenth (int, optional): Custom length for the embed. Defaults to None.

	Returns:
        Dict[str, str]: The formatted embed as a dictionary where both keys and values are strings.

	"""
	output =  {}
	longest_arg = max(arguments, key=len)

	if custom_lenth:
		if len(longest_arg) > custom_lenth:
			raise ValueError(f"Longest argument {longest_arg}: {len(longest_arg)} is longer than the custom length {custom_lenth}")
	
	if custom_lenth:
		final_lenth = custom_lenth
	final_lenth = len(longest_arg) + 2

	for arg in arguments:
		output[arg] = f" `{arg}{' '* (final_lenth - len(arg))}` "
		
	return output