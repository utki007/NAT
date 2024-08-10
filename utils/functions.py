import asyncio
import discord
import re
import datetime

from pytz import timezone
import pytz

from utils.embeds import get_invisible_embed


def clean_code(content):
    if content.startswith("```") and content.endswith("```"):
        return "\n".join(content.split("\n")[1:])[:-3]
    else:
        return content


async def quarantineUser(
    bot, user: discord.Member, quarantineRole: discord.Role = None, reason: str = None
):
    if user.id == user.guild.me.id:
        return
    top_role = user.guild.me.top_role
    top_role_position = top_role.position

    roles = []
    roles = [role for role in user.roles if role != user.guild.default_role]
    roles_to_keep = [
        role for role in roles if role.position >= top_role_position or role.managed
    ]
    roles_to_remove = [
        role for role in roles if role.position < top_role_position and not role.managed
    ]
    roles_to_remove_id = [role.id for role in roles_to_remove if role != quarantineRole]

    if quarantineRole is not None and quarantineRole.position < top_role_position:
        roles_to_keep.append(quarantineRole)
    if sorted(roles_to_keep) == sorted(roles):
        return False
    else:
        await user.edit(roles=roles_to_keep, reason=reason)

    data = await bot.quarantinedUsers.find(user.guild.id)
    if not data:
        data = {"_id": user.guild.id, "users": {}}
        data["users"][str(user.id)] = roles_to_remove_id
    else:
        if str(user.id) in data["users"] and len(roles_to_remove_id) > 0:
            data["users"][str(user.id)].extend(roles_to_remove_id)
        else:
            data["users"][str(user.id)] = roles_to_remove_id
    await bot.quarantinedUsers.upsert(data)
    return True


async def unquarantineUser(
    bot, user: discord.Member, quarantineRole: discord.Role = None, reason: str = None
):
    data = await bot.quarantinedUsers.find(user.guild.id)
    if data and str(user.id) in data["users"].keys():
        guild: discord.Guild = user.guild
        user_data = data["users"][str(user.id)]
        roles: list[discord.Role] = []
        pool_data = await bot.dankSecurity.find(user.guild.id)

        for role in user_data:
            if role == pool_data["event_manager"]:
                continue
            role = guild.get_role(role)
            if isinstance(role, discord.Role):
                roles.append(role)

        roles_to_add: list[discord.Role] = [
            role for role in roles if role.position < user.guild.me.top_role.position
        ]
        user_roles: list[discord.Role] = [
            role
            for role in user.roles
            if role not in [user.guild.default_role, quarantineRole]
        ]
        roles_to_add.extend(user_roles)

        if (
            quarantineRole is not None
            and quarantineRole.position < user.guild.me.top_role.position
        ):
            user_roles = [
                role
                for role in user.roles
                if role not in [user.guild.default_role, quarantineRole]
            ]
        else:
            user_roles = [
                role for role in user.roles if role not in [user.guild.default_role]
            ]

        await user.edit(roles=set(roles_to_add), reason=reason)

        await bot.quarantinedUsers.upsert(data)
        return True


# set emojis based on new_line
async def set_emojis(content):
    content = content.split("\n")
    for line in content:
        index = content.index(line)
        if index + 1 == len(content):
            emoji = "<:nat_reply:1146498277068517386>"
        else:
            emoji = "<:nat_replycont:1146496789361479741>"
        content[index] = f"{emoji} {line}"
    return "\n".join(content)


# create function to remove emojis from string
async def remove_emojis(string):
    emojis = list(set(re.findall(":\w*:\d*", string)))
    if len(emojis) == 0:
        return string
    for emoji in emojis:
        if emoji.replace(":", "", 2).isdigit():
            continue
        string = string.replace(emoji, "")
    string = string.replace("<>", "", 100)
    string = string.replace("<a>", "", 100)
    string = string.replace("  ", " ", 100)
    return string


async def check_gboost(bot, message):
    data = await bot.dank.find("gboost")
    if data is None:
        data = {"_id": "gboost", "active": False, "timestamp": 0}
        await bot.dank.upsert(data)
    boostMsgs = [
        line
        for line in message.embeds[0].to_dict()["description"].split("\n")
        if "Global Boost" in line
    ]
    if len(boostMsgs) < 2:
        if len(boostMsgs) == 0:
            if data["active"] is True:
                current_timestamp = int(
                    datetime.datetime.now(timezone("Asia/Kolkata")).timestamp()
                )
                if current_timestamp > int(data["timestamp"]):
                    data["active"] = False
                    await bot.dank.upsert(data)
        return

    timestamp = re.findall("\<t:\w*:R\>\d*", boostMsgs[1])
    if len(timestamp) < 1:
        return
    timestamp = int(timestamp[0].replace("<t:", "", 1).replace(":R>", "", 1))

    if data["active"] is False:
        # return if end time > current time
        current_timestamp = int(datetime.datetime.now(pytz.utc).timestamp())
        if data["timestamp"] > current_timestamp:
            data["active"] = True
            await bot.dank.upsert(data)
            return

        data["active"] = True
        data["timestamp"] = timestamp
        await bot.dank.upsert(data)

        records = await bot.userSettings.get_all({"gboost": True})
        user_ids = [record["_id"] for record in records]

        gboostmsg = [
            line for line in message.embeds[0].to_dict()["description"].split("\n")
        ]
        gboostmsg = [line[2:] for line in gboostmsg if line.startswith(">")]
        gboostmsg[1] = gboostmsg[1].replace("(", "(<").replace(")", ">)")
        gboostmsg = [list.strip() for list in gboostmsg]
        content = ""
        try:
            extraGboost = re.findall("\((.*?)\)", boostMsgs[1])
            if len(extraGboost) == 2:
                boost_count = int(extraGboost[0].split(" ")[0][1:])
                content = f"## Global Boost (+{boost_count} pending)\n<:nat_replycont:1146496789361479741> "
        except Exception:
            pass
        if content == "":
            content = "## Global Boost\n<:nat_replycont:1146496789361479741> "
        content += f"{gboostmsg[1]}\n<:nat_replycont:1146496789361479741> **Message:** {gboostmsg[2]}"
        content += f"\n<:nat_reply:1146498277068517386> **Ends at:** <t:{timestamp}:R>"

        for user_id in user_ids:
            user = await bot.fetch_user(user_id)
            try:
                if user_id in bot.owner_ids:
                    view = discord.ui.View()
                    view.add_item(
                        discord.ui.Button(
                            label="Jump to message",
                            style=discord.ButtonStyle.url,
                            url=message.jump_url,
                            emoji="<:tgk_link:1105189183523401828>",
                        )
                    )
                    view.add_item(
                        discord.ui.Button(
                            label=f"{message.guild.name}",
                            style=discord.ButtonStyle.url,
                            url=str((await message.guild.invites())[0]),
                            emoji="<:tgk_link:1105189183523401828>",
                        )
                    )
                    await user.send(
                        f"{content}\n> {message._interaction.user.mention}(`{message._interaction.user.id}`) used in [` {message.guild.name} `]({(await message.guild.invites())[0]})",
                        view=view,
                    )
                else:
                    try:
                        await user.send(content)
                        await asyncio.sleep(0.2)
                    except Exception:
                        data = await bot.userSettings.find(user.id)
                        data["gboost"] = False
                        await bot.userSettings.upsert(data)
                        pass
            except Exception:
                pass

    elif data["active"] is True:
        current_timestamp = int(datetime.datetime.now(pytz.utc).timestamp())
        if current_timestamp > data["timestamp"]:
            data["active"] = False
            await bot.dank.upsert(data)


async def set_cric_reminder(
    bot,
    message,
    remind_at: datetime.datetime,
    user: discord.Member,
    type,
    send_message: bool = True,
):
    data = await bot.cricket.find_by_custom({"user": user.id, "type": type})
    if data is None:
        data = {
            "user": user.id,
            "type": type,
            "time": remind_at,
            "message": f"https://discord.com/channels/{message.guild.id}/{message.channel.id}",
        }
        await bot.cricket.insert(data)
    elif data["time"] != remind_at:
        data["time"] = remind_at
        data["message"] = (
            f"https://discord.com/channels/{message.guild.id}/{message.channel.id}"
        )
        await bot.cricket.upsert(data)
    else:
        return False
    # await bot.cricket.upsert(data)
    if send_message:
        embed = await get_invisible_embed("hi")
        embed.description = None
        embed.title = "Drop Reminder"
        embed.description = f"Will remind for drop in <t:{int(remind_at.timestamp())}:R>(<t:{int(remind_at.timestamp())}:t>)."
        embed.description += "\n\n-# Run </settings:1196688324207853590> >> User Reminders to manage reminders."
        await message.reply(embed=embed)
    return True


async def bar(value: int):
    max_value = 100
    bar_length = 8
    bar_start = {'fill': '<:bar_start_fill:1149296377222930463>', 'empty': '<:bar_start_empty:1149296377222930463>'}
    bar_end = {'fill': '<:bar_end_fill:1149297916037582858>', 'empty': '<:bar_end_empty:1149297776535027733>'}
    bar_middle = {'fill': '<:bar_mid_fill:1149298022287679538>', 'empty': '<:bar_mid_empty:1149298212021211136>'}
    if value < 10:
        return f"{bar_start['empty']}{bar_middle['empty']*bar_length}{bar_end['empty']} {value}%"
    elif value >= 100:
        return f"{bar_start['fill']}{bar_middle['fill']*bar_length}{bar_end['fill']} {value}%"
    else:
        fill_length = int(value / max_value * bar_length)
        empty_length = bar_length - fill_length
        return f"{bar_start['fill']}{bar_middle['fill']*fill_length}{bar_middle['empty']*empty_length}{bar_end['empty']} {value}%"
