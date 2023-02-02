import discord

from utils.embeds import get_warning_embed

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
    try:
        await user.edit(roles=[quarantineRole])
    except:
        embed = await get_warning_embed(f"Unable to quarantine {user.mention} in {user.guild.name}.")
        return False
    data = await bot.quarantinedUsers.find(user.guild.id)
    if not data:
        data = {"_id": user.guild.id, "users": {}}
    data['users'][str(user.id)] = roles
    await bot.quarantinedUsers.upsert(data)
    return True

async def unquarantineUser(bot, user: discord.Member):
    data = await bot.quarantinedUsers.find(user.guild.id)
    if data:
        if str(user.id) in data['users']:
            roles = [user.guild.get_role(role_id) for role_id in data['users'][str(user.id)]]
            await user.edit(roles=roles)
            del data['users'][str(user.id)]
            await bot.quarantinedUsers.upsert(data)
            return True
    return False