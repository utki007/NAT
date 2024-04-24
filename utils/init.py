# Initialize data for mongo db

async def init_dankSecurity(interaction):
    data = {
        "_id": interaction.guild.id,
        "event_manager": None,
        "whitelist": [],
        "quarantine": None,
        "enable_logging": False,
        "logs_channel": None,
        "enabled": False
    }
    await interaction.client.dankSecurity.upsert(data)
    return data
