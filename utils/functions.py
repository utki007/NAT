import discord

def clean_code(content):
    if content.startswith("```") and content.endswith("```"):
        return "\n".join(content.split("\n")[1:])[:-3]
    else:
        return content

async def quarantineUser(bot, user: discord.Member, quarantineRole: discord.Role = None):
    roles = []
    for role in user.roles:
        if role == user.guild.default_role:
            continue
        roles.append(role.id)
    roles_to_Remove = [role for role in user.roles if role != user.guild.default_role]
    await user.remove_roles(*roles_to_Remove)
    await user.add_roles(quarantineRole)
    data = await bot.quarantinedUsers.find(user.guild.id)
    if not data:
        data = {"_id": user.guild.id, "users": {}}
    data['users'][str(user.id)] = roles
    await bot.quarantinedUsers.upsert(data)

async def unquarantineUser(bot, user: discord.Member):
    data = await bot.quarantinedUsers.find(user.guild.id)
    roles_to_Remove = [role for role in user.roles if role != user.guild.default_role]
    await user.remove_roles(*roles_to_Remove)
    if data:
        if str(user.id) in data['users']:
            roles = []
            for role in data['users'][str(user.id)]:
                roles.append(user.guild.get_role(role))
            await user.add_roles(*roles)
            del data['users'][str(user.id)]
            await bot.quarantinedUsers.upsert(data)
            return True
    return False