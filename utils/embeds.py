import discord
from typing import List, Dict, Union, Literal
from humanfriendly import format_timespan
import datetime


async def get_success_embed(content):
    success_embed = discord.Embed(
        color=0x43B581, description=f"<a:nat_check:1010969401379536958> **|** {content}"
    )
    return success_embed


async def get_warning_embed(content):
    warning_embed = discord.Embed(
        color=0xFFD300,
        description=f"<a:nat_warning:1062998119899484190> **|** {content}",
    )
    return warning_embed


async def get_error_embed(content):
    error_embed = discord.Embed(
        color=0xDA2A2A, description=f"<a:nat_cross:1010969491347357717> **|** {content}"
    )
    return error_embed


async def get_invisible_embed(content):
    invis_embed = discord.Embed(color=2829617, description=f"{content}")
    return invis_embed


async def get_formated_embed(
    arguments: List[str], custom_lenth: int = None
) -> Dict[str, str]:
    """
    This fuctions creates a formated embed description fields

    Args:
            arguments (List[str]): The arguments to format the embed.
            custom_lenth (int, optional): Custom length for the embed. Defaults to None.

    Returns:
           Dict[str, str]: The formatted embed as a dictionary where both keys and values are strings.

    """
    output = {}
    longest_arg = max(arguments, key=len)

    if custom_lenth:
        if len(longest_arg) > custom_lenth:
            raise ValueError(
                f"Longest argument {longest_arg}: {len(longest_arg)} is longer than the custom length {custom_lenth}"
            )

    if custom_lenth:
        final_lenth = custom_lenth
    final_lenth = len(longest_arg) + 2

    for arg in arguments:
        output[arg] = f" `{arg}{' '* (final_lenth - len(arg))}` "

    return output


async def get_formated_field(
    guild: discord.Guild,
    name: str,
    type: Literal["role", "channel", "user", "time", "str", "bool", "emoji", "int"],
    data: Union[List[int], None, int],
) -> str:
    """
    This function creates a formated embed field for a role, channel or user.

    Args:
            guild (discord.Guild): The guild where the role, channel or user is located.
            name (str): The name of the role, channel or user.
            type (Literal["role", "channel", "user"]): The type of the field.
            data (Union[List[int], None, int]): The id of the role, channel or user.

    Returns:
            str: The formated embed field.

    Raises:
    ValueError: If the type is invalid.
    """
    match type:
        case "role":
            if isinstance(data, List):
                if len(data) == 0:
                    return f"{name}None"

                roles = []
                [
                    roles.append(role.mention)
                    for role in (guild.get_role(r) for r in data)
                    if role
                ]
                return f"{name}{','.join(roles)}"

            elif isinstance(data, int):
                role = guild.get_role(data)
                return f"{name}{role.mention}" if role else f"{name}None"

            else:
                return f"{name}None"

        case "channel":
            if isinstance(data, List):
                if len(data) == 0:
                    return f"{name}None"

                channels = []
                [
                    channels.append(channel.mention)
                    for channel in (guild.get_channel(c) for c in data)
                    if channel
                ]
                return f"{name}{','.join(channels)}"

            elif isinstance(data, int):
                channel = guild.get_channel(data)
                return f"{name}{channel.mention}" if channel else f"{name}None"

            else:
                return f"{name}None"

        case "user":
            if isinstance(data, int):
                user = guild.get_member(data)
                return f"{name}{user.mention}" if user else f"{name}None"

            elif isinstance(data, List):
                if len(data) == 0:
                    return f"{name}None"

                users = []
                [
                    users.append(user.mention)
                    for user in (guild.get_member(u) for u in data)
                    if user
                ]
                return f"{name}{','.join(users)}"
            else:
                return f"{name}None"

        case "time":
            if isinstance(data, int):
                return f"{name}{format_timespan(data)}"
            elif isinstance(data, datetime.datetime):
                return f"{name}<t:{round(data.timestamp())}:R>(<t:{round(data.timestamp())}:f>)"
            elif isinstance(data, str) and data.lower() == "permanent":
                return f"{name}Permanent"
            else:
                return f"{name}None"
        case "str":
            if isinstance(data, str):
                return f"{name}{data}"
            if isinstance(data, list):
                if len(data) == 0:
                    return f"{name}None"
                return f"{name}".join(data)
            else:
                return f"{name}None"
        case "bool":
            if data is True:
                return f"{name}<:toggle_on:1123932825956134912>"
            elif data is False:
                return f"{name}<:toggle_off:1123932890993020928>"
            elif data is None:
                return f"{name}<:caution:1122473257338151003>"
        case "emoji":
            if isinstance(data, str):
                return f"{name}{data}"
            else:
                return f"{name}None"
        case "int":
            if isinstance(data, int):
                return f"{name}{data:,}"
            elif isinstance(data, List):
                if len(data) == 0:
                    return f"{name}None"
                _str = f"{name}".join([f"{i:,}" for i in data])
                return _str
            else:
                return f"{name}None"

        case _:
            raise ValueError("Invalid type")
