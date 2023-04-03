import discord

from utils.embeds import get_warning_embed

def clean_code(content):
    if content.startswith("```") and content.endswith("```"):
        return "\n".join(content.split("\n")[1:])[:-3]
    else:
        return content

async def quarantineUser(bot, user: discord.Member, quarantineRole: discord.Role = None, reason: str = None):
    
    top_role = user.guild.me.top_role
    top_role_position = top_role.position
    
    roles = []
    roles = [role for role in user.roles if role != user.guild.default_role]
    roles_to_keep = [role for role in roles if role.position >= top_role_position or role.managed]
    roles_to_remove = [role for role in roles if role.position < top_role_position and not role.managed]
    roles_to_remove_id = [role.id for role in roles_to_remove if role != quarantineRole]

    if quarantineRole is not None and quarantineRole.position < top_role_position:
        roles_to_keep.append(quarantineRole)
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

async def unquarantineUser(bot, user: discord.Member, quarantineRole: discord.Role = None, reason: str = None):
    data = await bot.quarantinedUsers.find(user.guild.id)
    if data:
        if str(user.id) in data['users']:
            roles = [user.guild.get_role(role_id) for role_id in data['users'][str(user.id)]]
            roles_to_add = [role for role in roles if role.position < user.guild.me.top_role.position]
            user_roles = [role for role in user.roles if role not in [user.guild.default_role, quarantineRole]]
            roles_to_add.extend(user_roles)
            if quarantineRole is not None and quarantineRole.position < user.guild.me.top_role.position:
                user_roles = [role for role in user.roles if role not in [user.guild.default_role, quarantineRole]]
            else:
                user_roles = [role for role in user.roles if role not in [user.guild.default_role]]
            await user.edit(roles=set(roles_to_add), reason=reason)
            del data['users'][str(user.id)]
            await bot.quarantinedUsers.upsert(data)
            return True