import discord
import datetime
import pytz
from discord.ext import commands
from utils.db import Document
from typing import List, TypedDict
from .view import Payout_Buttton, Payout_claim

class PayoutConfig(TypedDict):
    _id: int
    claim_channel: int
    claimed_channel: int
    default_claim_time: int
    express: bool
    manager_roles: List[int]
    event_manager_roles: List[int]
    log_channel: int
    enable_payouts: bool
    payout_channel: int

class PayoutConfigCache(TypedDict):
    _id: int
    claim_channel: discord.Webhook
    claimed_channel: discord.Webhook
    default_claim_time: int
    express: bool
    manager_roles: List[int]
    event_manager_roles: List[int]
    log_channel: int
    enable_payouts: bool
    payout_channel: int


class PayoutQueue(TypedDict):
    _id: int
    channel: int
    guild: int
    winner: int
    prize: int
    item: str | None
    event: str
    claimed: bool
    set_by: int
    winner_message_id: int
    queued_at: datetime.datetime
    claim_time: int

class PayoutDB:
    def __init__(self, bot: commands.Bot):
        self.db = bot.mongo['Payout_System']
        self.config = Document(self.db, "payout_config")
        self.unclaimed = Document(self.db, "payout_queue")
        self.claimed = Document(self.db, "payout_pending")
        self.pending_emoji = None
        self.paid_emoji = None
        self.bot: commands.Bot = bot
        self.bot.add_view(Payout_Buttton())
        self.bot.add_view(Payout_claim())
        self.config_cache = {}
    
    async def setup(self):
        self.pending_emoji: discord.Emoji = "<a:loading:998834454292344842>"
        self.paid_emoji: discord.Emoji = "<:paid:1071752278794575932>"

    async def get_config(self, guild_id: int) -> PayoutConfigCache| PayoutConfig | None:
        if guild_id in self.config_cache.keys():
            return self.config_cache[guild_id]
        else:
            config = await self.config.find(guild_id)
            if not config:
                config: PayoutConfig = {
                        '_id': guild_id,
                        'claim_channel': None,
                        'claimed_channel': None,
                        'payout_channel': None,
                        'manager_roles': [],
                        'event_manager_roles': [],
                        'log_channel': None,
                        'default_claim_time': 3600,
                        'express': False,
                        'enable_payouts': False,
						}
                await self.config.insert(config)
                return config
            
            try:
                config['claim_channel'] = await self.bot.fetch_webhook(config['claim_channel']) if config['claim_channel'] is not None else None
                config['claimed_channel'] = await self.bot.fetch_webhook(config['claimed_channel']) if config['claimed_channel'] is not None else None
            except discord.HTTPException:
                config['claim_channel'] = None
                config['claimed_channel'] = None
                await self.config.update(config)

            self.config_cache[guild_id] = config
            return config
        
    async def update_config(self, data: PayoutConfigCache):
        config = data.copy()
        if isinstance(data['claim_channel'], discord.Webhook):
            config['claim_channel'] = data['claim_channel'].id
        if isinstance(data['claimed_channel'], discord.Webhook):
            config['claimed_channel'] = data['claimed_channel'].id
        await self.config.update(config)
        self.config_cache[data['_id']]['claim_channel'] = data['claim_channel']
        self.config_cache[data['_id']]['claimed_channel'] = data['claimed_channel']
    
    async def create_pending_embed(self, event: str, winner: discord.Member, prize: int, host: discord.Member, item_data: dict=None) -> discord.Embed:
        embed = discord.Embed(title="Payout Queue", timestamp=datetime.datetime.now(), description="", color=0x2b2d31)
        embed.add_field(name="Event Info", value=f"<:nat_replycont:1146496789361479741> **Name:** {event}\n<:nat_reply:1146498277068517386> **Winner:** {winner.mention} ", inline=True)
        value = ""
        if isinstance(item_data, dict):
           value += f"<:nat_replycont:1146496789361479741> **Won:**  `{prize}x` {item_data['_id']}\n"
           value += f"<:nat_reply:1146498277068517386> **Net Worth:** `⏣ {(prize * item_data['price']):,}`\n"
        else:
            value += f"<:nat_reply:1146498277068517386> **Won:**  `⏣ {prize:,}`\n"
        embed.add_field(name="Prize Info", value=value, inline=True)
        embed.set_footer(text="Queued by: {}".format(host.name))
        return embed

    async def create_payout(self, config: PayoutConfigCache, event: str, winner: discord.Member, host: discord.Member, prize: int, message: discord.Message, item: dict=None):
    
        if config is None:
            return None
        queue_data: PayoutQueue = {
            'channel': message.channel.id,
            'guild': message.guild.id,
            'winner': winner.id,
            'prize': prize,
            'item': item['_id'] if item else None,
            'event': event,
            'claimed': False,
            'set_by': host.id,
            'winner_message_id': message.id,
            'queued_at': datetime.datetime.now(pytz.utc),
            'claim_time': config['default_claim_time']
        }

        claim_time_timestamp = int((datetime.datetime.now() + datetime.timedelta(seconds=int(config['default_claim_time']))).timestamp())

        embed = await self.create_pending_embed(event=event, winner=winner, prize=prize, host=host,item_data=item)
        view = Payout_claim()
        view.add_item(discord.ui.Button(label="Event Message",style=discord.ButtonStyle.link,url=message.jump_url ,emoji="<:tgk_link:1105189183523401828>"))

        unclaim_webhook = config['claim_channel']
        if unclaim_webhook is None:
            return None
        
        claim_message = await unclaim_webhook.send(username="👑 | N.A.T Payouts",embed=embed, view=view, wait=True, content=f"{winner.mention} Your prize has been queued for payout\n> Please claim it within <t:{claim_time_timestamp}:R> or it will rerolled.")
        await message.add_reaction(self.pending_emoji)
        queue_data['_id'] = claim_message.id
        await self.unclaimed.insert(queue_data)
        return claim_message

    async def reject_payout(self, host: discord.Member, payout: PayoutQueue) -> bool | tuple:
        config = await self.get_config(payout['guild'])

        if isinstance(config['claimed_channel'], discord.Webhook):
            claimed_channel = config['claimed_channel'].channel
        elif isinstance(config['claimed_channel'], int):
            claimed_webhook = await self.bot.fetch_webhook(config['claimed_channel'])
            claimed_channel = claimed_webhook.channel
        else:
            return (False, "Unknown Webhook! Please reconfigure the settings.")
        
        try:
            claimed_message = await claimed_channel.fetch_message(payout['_id'])
            embed = claimed_message.embeds[0]
            embed.title = "Payout Rejected"

            edit_view = discord.ui.View()
            edit_view.add_item(discord.ui.Button(label='Payout Denied', style=discord.ButtonStyle.gray, disabled=True, emoji="<a:nat_cross:1010969491347357717>"))

            await config['claimed_channel'].edit_message(claimed_message.id, embed=embed, view=edit_view)
            await self.claimed.delete(payout['_id'])
            return True
        
        except Exception as e:
            return (False, e)