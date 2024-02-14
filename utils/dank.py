import discord
import re

class DonationsInfo:
    def __init__(self, donor: discord.Member, quantity: int, items: str=None):
        self.donor = donor
        self.quantity = quantity
        self.items = items

    def __str__(self):
        if self.items:
            return f"{self.donor} donated {self.quantity} {self.items}"
        else:
            return f"{self.donor} donated {self.quantity}"

async def get_doantion_from_message(message: discord.Message) -> DonationsInfo:
    if message.author.id != 270904126974590976:
        raise ValueError("Message is not from Dank Memer")
    
    if len(message.embeds) == 0:
        raise ValueError("Message does not contain an embed")

    if not message.interaction:
        raise ValueError("Message doese not contain an interaction object")

    donor: discord.Member = message.interaction.user

    embed: discord.Embed = message.embeds[0]    
    description = embed.description

    items = re.findall(r"\*\*(.*?)\*\*", embed.description)[0]
    if "⏣" in items:
        items = int(items.replace("⏣", "").replace(",", ""))
        return DonationsInfo(donor, items)
    
    else:

        emojis = list(set(re.findall(":\w*:\d*", items)))
        for emoji in emojis :items = items.replace(emoji,"",100); items = items.replace("<>","",100);items = items.replace("<a>","",100);items = items.replace("  "," ",100)
        mathc = re.search(r"(\d+)x (.+)", items)
        if not mathc:
            raise ValueError("Could not parse items from message")

        quantity = int(mathc.group(1))
        items = mathc.group(2)

        return DonationsInfo(donor, quantity, items)