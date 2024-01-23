import asyncio
import discord
import re
import datetime

from utils.embeds import get_warning_embed

def clean_code(content):
    if content.startswith("```") and content.endswith("```"):
        return "\n".join(content.split("\n")[1:])[:-3]
    else:
        return content

async def quarantineUser(bot, user: discord.Member, quarantineRole: discord.Role = None, reason: str = None):
    
    if user.id == user.guild.me.id:
        return 
    top_role = user.guild.me.top_role
    top_role_position = top_role.position
    
    roles = []
    roles = [role for role in user.roles if role != user.guild.default_role]
    roles_to_keep = [role for role in roles if role.position >= top_role_position or role.managed]
    roles_to_remove = [role for role in roles if role.position < top_role_position and not role.managed]
    roles_to_remove_id = [role.id for role in roles_to_remove if role != quarantineRole]

    if quarantineRole is not None and quarantineRole.position < top_role_position:
        roles_to_keep.append(quarantineRole)
    if sorted(roles_to_keep) == sorted(roles):
        return False
    else:
        await user.edit(roles = roles_to_keep, reason=reason)

    data = await bot.quarantinedUsers.find(user.guild.id)
    if not data:
        data = {"_id": user.guild.id, "users": {}}
        data['users'][str(user.id)] = roles_to_remove_id
    else:
        if str(user.id) in data['users'] and len(roles_to_remove_id) > 0:
            data['users'][str(user.id)].extend(roles_to_remove_id)
        else:
            data['users'][str(user.id)] = roles_to_remove_id
    await bot.quarantinedUsers.upsert(data)
    return True

async def unquarantineUser(bot, user: discord.Member, quarantineRole: discord.Role = None, reason: str = None):
    data = await bot.quarantinedUsers.find(user.guild.id)
    if data and str(user.id) in data['users'].keys():
        guild: discord.Guild = user.guild
        user_data = data['users'][str(user.id)]
        roles: list[discord.Role] = []
        pool_data = await bot.dankSecurity.find(user.guild.id)

        for role in user_data:
            if role == pool_data['event_manager']: continue
            role = guild.get_role(role)
            if isinstance(role, discord.Role): roles.append(role)
        
        roles_to_add: list[discord.Role] = [role for role in roles if role.position < user.guild.me.top_role.position]
        user_roles: list[discord.Role] = [role for role in user.roles if role not in [user.guild.default_role, quarantineRole]]
        roles_to_add.extend(user_roles)

        if quarantineRole is not None and quarantineRole.position < user.guild.me.top_role.position:
            user_roles = [role for role in user.roles if role not in [user.guild.default_role, quarantineRole]]
        else:
            user_roles = [role for role in user.roles if role not in [user.guild.default_role]]
                
        await user.edit(roles=set(roles_to_add), reason=reason)

        await bot.quarantinedUsers.upsert(data)
        return True

# create function to remove emojis from string
async def remove_emojis(string):
    emojis = list(set(re.findall(":\w*:\d*", string)))
    for emoji in emojis:
        if emoji.replace(":", "", 2).isdigit():
            continue
        string = string.replace(emoji, "")
    string = string.replace("<>", "", 100)
    string = string.replace("<a>", "", 100)
    string = string.replace("  "," ",100)
    return string

async def check_gboost(bot, message):
    boostMsgs = [line for line in message.embeds[0].to_dict()['description'].split("\n") if "Global Boost" in line]
    if len(boostMsgs) < 2: 
        if len(boostMsgs) == 0:
            if bot.gboost['active'] is True:
                current_timestamp = int(datetime.datetime.utcnow().timestamp())
                if current_timestamp > int(bot.gboost['timestamp']):
                    bot.gboost['active'] = False
                    bot.gboost['timestamp'] = 0
        return
    
    extraGboost = re.findall("\((.*?)\)", boostMsgs[1])
    if len(extraGboost) == 2:
        gboost = (int(extraGboost[0].split(" ")[0][1:]))
    elif len(extraGboost) == 0:
        gboost = 0
    timestamp = re.findall("\<t:\w*:R\>\d*", boostMsgs[1])
    if len(timestamp) < 1: return
    timestamp = int(timestamp[0].replace("<t:","",1).replace(":R>","",1))

    if bot.gboost['active'] is False:
        
        # return if end time > current time
        current_timestamp = int(datetime.datetime.utcnow().timestamp())
        if bot.gboost['timestamp'] > current_timestamp:
            bot.gboost['active'] = True
            return

        bot.gboost['active'] = True
        bot.gboost['timestamp'] = timestamp
        
        records = await bot.userSettings.get_all({'gboost':True})
        user_ids = [record["_id"] for record in records]
        user_ids = [301657045248114690]

        gboostmsg = [line for line in message.embeds[0].to_dict()['description'].split(">")]
        gboostmsg[3] = gboostmsg[3].split('\n')[0]
        gboostmsg[2] = (gboostmsg[2].split(']')[0] + "](<https://dankmemer.lol/store>)" + "]".join(gboostmsg[2].split(']')[1:])).replace("(https://dankmemer.lol/store)","",1)
        gboostmsg = [list.strip() for list in gboostmsg[2:4]]
        content = "## Global Boost\n<:nat_replycont:1146496789361479741> "
        content += f"\n<:nat_replycont:1146496789361479741> **Message:** ".join(gboostmsg)
        content += f"\n<:nat_reply:1146498277068517386> **Ends at:** <t:{timestamp}:R>"

        for user_id in user_ids:
            user = await bot.fetch_user(user_id)
            try:
                await user.send(content)
                await asyncio.sleep(0.2)	
            except:
                pass
    
    elif bot.gboost['active'] is True:
        current_timestamp = int(datetime.datetime.utcnow().timestamp())
        if current_timestamp > bot.gboost['timestamp']:
            bot.gboost['active'] = False
            bot.gboost['timestamp'] = 0
        else:
            bot.gboost['timestamp'] = timestamp