import discord

from utils.embeds import get_warning_embed

def clean_code(content):
    if content.startswith("```") and content.endswith("```"):
        return "\n".join(content.split("\n")[1:])[:-3]
    else:
        return content

async def quarantineUser(bot, user: discord.Member, quarantineRole: discord.Role = None):
    
    top_role = user.guild.me.top_role
    top_role_position = top_role.position
    
    roles = []
    roles = [role for role in user.roles if role != user.guild.default_role]
    roles_to_remove = [role for role in roles if role.position < top_role_position]
    roles_to_remove.reverse()
    roles_to_remove_id = [role.id for role in roles_to_remove if role != quarantineRole]

    if roles_to_remove is not None or len(roles_to_remove) > 0:
        await user.remove_roles(*roles_to_remove)
    if quarantineRole is not None and quarantineRole not in user.roles and quarantineRole.position < top_role_position:
        await user.add_roles(quarantineRole)

    data = await bot.quarantinedUsers.find(user.guild.id)
    if not data:
        data = {"_id": user.guild.id, "users": {}}
    data['users'][str(user.id)] = roles_to_remove_id
    await bot.quarantinedUsers.upsert(data)

async def unquarantineUser(bot, user: discord.Member, quarantineRole: discord.Role = None):
    data = await bot.quarantinedUsers.find(user.guild.id)
    if quarantineRole is not None and quarantineRole in user.roles:
        await user.remove_roles(quarantineRole)
    if data:
        if str(user.id) in data['users']:
            roles = [user.guild.get_role(role_id) for role_id in data['users'][str(user.id)]]
            roles_to_add = [role for role in roles if role.position < user.guild.me.top_role.position]
            await user.add_roles(*roles_to_add)
            del data['users'][str(user.id)]
            await bot.quarantinedUsers.upsert(data)