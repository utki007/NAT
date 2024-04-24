import random
import re
import discord
import datetime
import asyncio
import humanfriendly
from pymongo.results import DeleteResult
from discord import app_commands, Interaction
from discord.ext import commands, tasks
import pytz
from utils.db import Document
from typing import List
from ui.settings.payouts import Payout_Buttton, Payout_claim
from utils.views.confirm import Confirm
from utils.transformers import DMCConverter, MultipleMember
from typing import TypedDict
from utils.embeds import get_warning_embed

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
        self.pending_emoji: discord.Emoji = self.bot.get_emoji(998834454292344842)
        self.paid_emoji: discord.Emoji = self.bot.get_emoji(1071752278794575932)

    async def get_config(self, guild_id: int, new=False) -> PayoutConfigCache| PayoutConfig | None:
        if new is True:
            guild_config: PayoutConfig = await self.config.find(guild_id)
            try:
                guild_config['claim_channel'] = await self.bot.fetch_webhook(guild_config['claim_channel']) if guild_config['claim_channel'] is not None else None
                guild_config['claimed_channel'] = await self.bot.fetch_webhook(guild_config['claimed_channel']) if guild_config['claimed_channel'] is not None else None
                self.config_cache[guild_id] = guild_config
                return guild_config
            except:
                return None

        if guild_id in self.config_cache.keys():
            return self.config_cache[guild_id]
        else:
            config = await self.config.find(guild_id)
            if config is None:
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
            except:
                config['claim_channel'] = None
                config['claimed_channel'] = None

            self.config_cache[guild_id] = config            
            config = PayoutConfigCache(**config)
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
            edit_view.add_item(discord.ui.Button(label=f'Payout Denied', style=discord.ButtonStyle.gray, disabled=True, emoji="<a:nat_cross:1010969491347357717>"))

            await config['claimed_channel'].edit_message(claimed_message.id, embed=embed, view=edit_view)
            await self.claimed.delete(payout['_id'])
            return True
        
        except Exception as e:
            return (False, e)


@app_commands.guild_only()
class PayoutV2(commands.GroupCog, name="payout"):
    def __init__(self, bot):
        self.bot = bot
        self.backend = PayoutDB(bot)
        self.bot.payouts = self.backend
        self.bot.dank_items_cache = {}
        self.check_claim.start()
        self.check_claim_task = False
        self.in_expire_task = []

    async def item_autocomplete(self, interaction: discord.Interaction, string: str) -> List[app_commands.Choice[str]]:
        choices = []
        for item in self.bot.dank_items_cache.keys():
            if string.lower() in item.lower():
                choices.append(app_commands.Choice(name=item, value=item))
        if len(choices) == 0:
            return [
                app_commands.Choice(name=item, value=item)
                for item in self.bot.dank_items_cache.keys()
            ]
        else:
            return choices[:24]
    
    async def interaction_check(self, interaction: Interaction):
        if len(interaction.guild.members) < 50:
            await interaction.response.send_message("This command is not available for servers with less than 50 members", ephemeral=True)
            return False
        return True

    @commands.Cog.listener()
    async def on_ready(self):        
        for guild in await self.backend.config.find_many_by_custom({'express': True}):
            if guild['express'] is True:
                guild['express'] = False
                await self.backend.update_config(guild)
        for item in await self.bot.dankItems.get_all(): self.bot.dank_items_cache[item['_id']] = item
        await self.backend.setup()
    
    @tasks.loop(seconds=10)
    async def check_claim(self):
        if self.check_claim_task: return
        self.claim_task = True
        for payout in await self.backend.unclaimed.get_all():
            payout: PayoutQueue = payout
            if datetime.datetime.utcnow() >= payout['queued_at'] + datetime.timedelta(seconds=payout['claim_time']):
                self.bot.dispatch("payout_claim_expired", payout)
                await asyncio.sleep(1.25)
        
        self.check_claim_task = False
    
    @check_claim.before_loop
    async def before_check_claim(self):
        await self.bot.wait_until_ready()
    
    @commands.Cog.listener()
    async def on_payout_claim_expired(self, payout: PayoutQueue):
        if payout['_id'] in self.in_expire_task: return
        self.in_expire_task.append(payout['_id'])
        config: PayoutConfigCache = await self.backend.get_config(payout['guild'])
        
        if config is None: 
            await self.backend.unclaimed.delete(payout['_id'])
            return
        try:
            guild: discord.Guild = self.bot.get_guild(payout['guild'])
            claim_channel: discord.TextChannel = config['claim_channel'].channel
            message: discord.Message = await claim_channel.fetch_message(payout['_id'])
            embed = message.embeds[0]
            embed.title = "Payout Expired"
            embed.color = discord.Color.red()
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Claim time expired", style=discord.ButtonStyle.gray, disabled=True, emoji="<a:nat_cross:1010969491347357717>"))
            view.add_item(discord.ui.Button(label="Event Link", style=discord.ButtonStyle.link, url=f"https://discord.com/channels/{guild.id}/{payout['channel']}/{payout['winner_message_id']}", emoji="<:tgk_link:1105189183523401828>"))
            await config['claim_channel'].edit_message(message.id, embed=embed, view=view, content=None)
            host: discord.Member = guild.get_member(payout['set_by'])
            host_view = discord.ui.View()
            host_view.add_item(discord.ui.Button(label="Payout Link", style=discord.ButtonStyle.link, url=message.jump_url, emoji="<:tgk_link:1105189183523401828>"))
            await host.send(f"Your payout for **{payout['event']}** has expired, please requeue it again.", view=host_view)
        except:
            pass
        await self.backend.unclaimed.delete(payout['_id'])
        self.in_expire_task.remove(payout['_id'])

    @app_commands.command(name="create", description="Create a new payout")
    @app_commands.describe(event="event name", message_id="winner message id", winners="winner of the event", quantity='A constant number like "123" or a shorthand like "5m"', item="what item did they win?")
    @app_commands.autocomplete(item=item_autocomplete)
    @app_commands.rename(winners="winners_list")
    async def payout_create(self, interaction: discord.Interaction, event: str, message_id: str, winners: app_commands.Transform[discord.Member, MultipleMember], quantity: app_commands.Transform[int, DMCConverter], item: str=None):
        guild_config = await self.backend.get_config(interaction.guild_id)
        if guild_config is None:
            return await interaction.response.send_message("Payouts are not enabled on this server", ephemeral=True)
        
        user_roles = [role.id for role in interaction.user.roles]
        if (set(user_roles) & set(guild_config['event_manager_roles'])) or (set(user_roles) & set(guild_config['manager_roles'])):
            pass
        else:
            return await interaction.response.send_message("You are not allowed to use this command!", ephemeral=True)
        
        if guild_config['claim_channel'] is None or guild_config['claimed_channel'] is None:
            embed = await get_warning_embed("Unknown Webhook! Please reconfigure the settings.")
            return await interaction.response.send_message(ephemeral=True, embed=embed)
        
        claim_time_seconds = guild_config['default_claim_time'] if guild_config['default_claim_time'] is not None else 86400

        try:
            event_message = await interaction.channel.fetch_message(message_id)
        except discord.NotFound:
            return await interaction.response.send_message("Oops! Can't find that message!\nDouble-check the message ID and make sure it's in the same channel.", ephemeral=True)

        if guild_config['claim_channel'] is None or guild_config['claimed_channel'] is None:
            embed = await get_warning_embed("Unknown Webhook! Please reconfigure the settings.")
            return await interaction.response.send_message(ephemeral=True, embed=embed)

        if len(winners) == 0:
            return await interaction.response.send_message("Oops! Can't find any winners!\nDouble-check that winners are vaild", ephemeral=True)
        
        confrim_embed = discord.Embed(title="Payout confirmation", description="", color=0x2b2d31)

        confrim_embed.description += f"**Event:** {event}\n"
        confrim_embed.description += f"**Winners:** {', '.join([winner.mention for winner in winners])}\n"

        if item:
            item_data = await interaction.client.dankItems.find(item)
            if not item_data:
                return await interaction.response.send_message("Oops! can't find item with that name", ephemeral=True)
            confrim_embed.description += f"**Prize:** {quantity} x {item}\n"
        else:
            confrim_embed.description += f"**Prize: ⏣ {quantity:,} Each**\n"
            item_data = None
        confrim_embed.description += f"**Message** {event_message.jump_url}\n"
        confrim_embed.description += f"**Claim Time:** {humanfriendly.format_timespan(claim_time_seconds)}\n"

        view = Confirm(interaction.user, 60)
        view.children[0].label = "Confirm"
        view.children[0].style = discord.ButtonStyle.green
        view.children[1].label = "Cancel"
        view.children[1].style = discord.ButtonStyle.red

        await interaction.response.send_message(embed=confrim_embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()
        await view.wait()

        if view.value is None or view.value is False:
            return await interaction.edit_original_response(content="Payout creation has been cancelled.", view=None, embed=None)
        
        loading_embed = discord.Embed(description=f"<a:loading:998834454292344842> | Setting up the payout for total of `{len(winners)}` winners!")
        loading_embed.set_footer(text="This might take a while depending on the number of winners.")
        await view.interaction.response.edit_message(view=None, embed=loading_embed)

        for winner in winners:
            winner: discord.Member
            queue_data = await self.backend.unclaimed.find({'winner_message_id': event_message.id, 'winner': winner.id})
            pending_data = await self.backend.claimed.find({'winner_message_id': event_message.id, 'winner': winner.id})

            if queue_data or pending_data:
                dupe = None
                if queue_data:
                    try:
                        await guild_config['claim_channel'].channel.fetch_message(queue_data['_id'])
                        dupe = True
                    except discord.NotFound:
                        await self.backend.unclaimed.delete(queue_data['_id'])
                        dupe = False
                
                if pending_data:
                    try:
                        await guild_config['claimed_channel'].channel.fetch_message(pending_data['_id'])
                        dupe = True
                    except discord.NotFound:
                        await self.backend.claimed.delete(pending_data['_id'])
                        dupe = False
                
                if dupe:
                    loading_embed.description += f"\n<:dynoError:1000351802702692442> | {winner.mention} `({winner.name})` already has a pending payout. Skipping..."
                    await interaction.edit_original_response(embed=loading_embed)
                    continue

            payout_message = await self.backend.create_payout(config=guild_config, event=event, winner=winner, host=interaction.user, prize=quantity, message=event_message, item=item_data)

            if isinstance(payout_message, discord.Message):
                if winners.index(winner) == 0:
                    link_view = discord.ui.View()
                    link_view.add_item(discord.ui.Button(label="Queued Payouts", url=payout_message.jump_url, style=discord.ButtonStyle.link))
                    await interaction.edit_original_response(view=link_view)
                    await asyncio.sleep(1.5)

                loading_embed.description += f"\n<:octane_yes:1019957051721535618> | {winner.mention} `({winner.name})` has been queued for payout!"                

                await interaction.edit_original_response(embed=loading_embed)
                self.bot.dispatch("payout_queue", interaction.user, event, event_message, payout_message, winner, quantity)

            await asyncio.sleep(2)

        loading_embed.description = f"\n<:octane_yes:1019957051721535618> | Payout has been queued for total of `{len(winners)}` winners!"
        await event_message.add_reaction(self.backend.pending_emoji)
        await interaction.edit_original_response(embed=loading_embed)

    @app_commands.command(name="clear", description="Search for a payout message")
    @app_commands.describe(message_id="The message ID of the event message.")
    async def payout_search(self, interaction: discord.Interaction, message_id: str=None):
        data = await self.backend.get_config(interaction.guild_id)
        if data is None: return await interaction.response.send_message("Payout system is not configured yet!", ephemeral=True)

        user_roles = [role.id for role in interaction.user.roles]
        if (set(user_roles) & set(data['manager_roles'])):
            pass
        else:
            return await interaction.response.send_message("You are not allowed to use this command!", ephemeral=True)
        
        if data['claim_channel'] is None or data['claimed_channel'] is None:
            embed = await get_warning_embed("Unknown Webhook! Please reconfigure the settings.")
            return await interaction.response.send_message(ephemeral=True, embed=embed)

        await self.backend.unclaimed.find_many_by_custom({'_id': int(message_id)})
        await self.backend.claimed.find_many_by_custom({'_id': int(message_id)})
        await interaction.response.send_message("if any payout was attached to this message then it has been deleted.", ephemeral=True)

    @app_commands.command(name="search", description="Search for a payout message")
    @app_commands.describe(message_id="The message ID of the event message.", user="user's payouts you want to search for")
    async def payout_search(self, interaction: discord.Interaction, message_id: str=None, user: discord.Member=None):
        if message_id is None and user is None:
            await interaction.response.send_message("Please provide either message id or user to search for.", ephemeral=True)
            return
        
        config = await self.backend.get_config(interaction.guild_id)
        if config is None: return await interaction.response.send_message("Payout system is not configured yet!", ephemeral=True)

        user_roles = [role.id for role in interaction.user.roles]
        if (set(user_roles) & set(config['event_manager_roles'])) or (set(user_roles) & set(config['manager_roles'])):
            pass
        else:
            return await interaction.response.send_message("You are not allowed to use this command!", ephemeral=True)
        
        if config['claim_channel'] is None or config['claimed_channel'] is None:
            embed = await get_warning_embed("Unknown Webhook! Please reconfigure the settings.")
            return await interaction.response.send_message(ephemeral=True, embed=embed)
        
        unclaim = await self.backend.unclaimed.find_many_by_custom({'winner_message_id': int(message_id)})
        embed = discord.Embed(title="Unclaimed payouts", description="", color=0x2b2d31)
        claim_channel = interaction.guild.get_channel(config['claimed_channel'])
        if len(unclaim) == 0:
            embed.description = "All Payouts are claimed/Expired/Not created yet."
        else:
            i = 1
            for entey in unclaim:
                embed.description += f"\n**{i}.** https://discord.com/channels/{interaction.guild.id}/{claim_channel.id}/{entey['_id']}"
                i += 1

        await self.backend.claimed.find_many_by_custom({'winner_message_id': int(message_id)})
        pending_embed = discord.Embed(title="Pending Payout Search", color=0x2b2d31, description="")
        pendin_channel = interaction.guild.get_channel(config['claim_channel'])

        if len(unclaim) == 0:
            pending_embed.description = "All Payouts are Paid/Rejected/Not created yet."
        else:
            i = 1
            for entey in unclaim:
                pending_embed.description += f"\n**{i}.** https://discord.com/channels/{interaction.guild.id}/{pendin_channel.id}/{entey['_id']}"
                i += 1
        
        await interaction.response.send_message(embeds=[embed, pending_embed], ephemeral=False)

    @app_commands.command(name="express", description="start doing payouts for the oldest payouts with the help of me")
    @app_commands.describe(mode="accessibility mode of the command")
    @app_commands.choices(mode=[
        app_commands.Choice(name="PC/Android", value="pc"),
        app_commands.Choice(name="iOS", value="ios"),
    ]) 
    async def express_payout(self, interaction: discord.Interaction, mode: app_commands.Choice[str]=None):
        if mode is None:
            mode = app_commands.Choice(name="PC/Android", value="pc")
        premium = await self.bot.premium.find(interaction.guild.id)

        guild_config = await self.backend.get_config(interaction.guild_id, new=True)
        if guild_config is None: return
        user_roles = [role.id for role in interaction.user.roles]
        if not (set(user_roles) & set(guild_config['manager_roles'])): 
            await interaction.response.send_message("You don't have permission to use this command", ephemeral=True)
            return
        
        if guild_config['claim_channel'] is None or guild_config['claimed_channel'] is None:
            embed = await get_warning_embed("Unknown Webhook! Please reconfigure the settings.")
            return await interaction.response.send_message(ephemeral=True, embed=embed)
        
        if interaction.channel.id !=  guild_config['payout_channel']:
            await interaction.response.send_message(f"Please use this command in <#{guild_config['payout_channel']}>", ephemeral=True)
            return

        payouts = await self.backend.claimed.find_many_by_custom({'guild': interaction.guild.id})
        if len(payouts) <= 0:
            await interaction.response.send_message("There are no payouts pending", ephemeral=True)
            return
        
        if isinstance(premium, dict):
            if premium['premium'] is True:
                payouts = payouts[:premium['payout_limit']]
        else:
            if len(payouts) > 20:
                payouts = payouts[:20]
                

        if guild_config['express'] is True:
            await interaction.response.send_message("There is already a express payout in progress", ephemeral=True)
            return
        
        await interaction.response.send_message(f"## Starting Payouts for oldest {len(payouts)} payouts in queue", ephemeral=True)
        queue_webhook = guild_config['claimed_channel']   
        claim_channel = queue_webhook.channel

        guild_config['express'] = True
        await self.backend.update_config(guild_config)
        self.backend.config_cache[interaction.guild.id]['express'] = True

        for payout in payouts:
            try:
                winner_message = await claim_channel.fetch_message(payout['_id'])
            except discord.NotFound:
                await self.backend.claimed.delete(payout['_id'])
                continue
            
            def check(m: discord.Message):
                if m.channel.id != interaction.channel.id: 
                    return False
                if m.author.id != 270904126974590976:
                    if m.author.id == interaction.user.id:
                        if m.content.lower() in ["skip", "reject", "exit"]:
                            return True
                    return False

                if len(m.embeds) == 0: 
                    return False
                embed = m.embeds[0]
                if embed.description is None or embed.description == "": return False
                if embed.description.startswith("Successfully paid"):
                    found_winner = interaction.guild.get_member(int(embed.description.split(" ")[2].replace("<", "").replace(">", "").replace("!", "").replace("@", ""))) 
                    if payout['winner'] != found_winner.id: 
                        return False
                    items = re.findall(r"\*\*(.*?)\*\*", embed.description)[0]
                    if "⏣" in items:
                        items = int(items.replace("⏣", "").replace(",", ""))
                        if items == payout['prize']:
                            return True
                        else:
                            return False
                    else:
                        emojis = list(set(re.findall(":\w*:\d*", items)))
                        for emoji in emojis :items = items.replace(emoji,"",100); items = items.replace("<>","",100);items = items.replace("<a>","",100);items = items.replace("  "," ",100)
                        mathc = re.search(r"(\d+)x (.+)", items)
                        item_found = mathc.group(2)
                        quantity_found = int(items.split(" ")[0][:-1].replace(",","",100))
                        if item_found.lower() == payout['item'].lower() and quantity_found == payout['prize']:
                            return True

            embed = discord.Embed(title="Payout Info", description="", color=0x2b2d31)
            embed.description += f"**Winner:** <@{payout['winner']}>\n"

            if payout['item']:
                embed.description += f"**Price:** {payout['prize']}x{payout['item']}\n"
            else:
                embed.description += f"**Price:** ⏣ {payout['prize']:,}\n"

            embed.description += f"**Channel:** <#{payout['channel']}>\n"
            embed.description += f"**Host:** <@{payout['set_by']}>\n"
            embed.description += f"**Quick actions:**\n* skip: skip this payout\n* reject: reject this payout\n* exit: forcefully exit the express payout\n"
            if 'claimed_at' in payout.keys():
                embed.description += f"\n**Payout Claimed At:** <t:{int(payout['claimed_at'].timestamp())}:R>\n"
            embed.description += f"**Timeout in:** <t:{int((datetime.datetime.now() + datetime.timedelta(seconds=60)).timestamp())}:R>\n"
            cmd = ""
            if not payout['item']:
                cmd += f"/serverevents payout user:{payout['winner']} quantity:{payout['prize']}"
            else:
                cmd += f"/serverevents payout user:{payout['winner']} quantity:{payout['prize']} item:{payout['item']}"

            embed.add_field(name="Command", value=cmd, inline=False)
            embed.set_footer(text=f"Queue Number: {payouts.index(payout)+1}/{len(payouts)}")

            await asyncio.sleep(1.25)
            link_view = discord.ui.View()
            link_view.add_item(discord.ui.Button(label=f"Queue Link", style=discord.ButtonStyle.url, url=f"https://discord.com/channels/{interaction.guild.id}/{claim_channel.id}/{payout['_id']}", emoji="<:tgk_link:1105189183523401828>"))
            link_view.add_item(discord.ui.Button(label=f"Event Link", style=discord.ButtonStyle.url, url=f"https://discord.com/channels/{interaction.guild.id}/{payout['channel']}/{payout['winner_message_id']}", emoji="<:tgk_link:1105189183523401828>"))

            keyward = {
                "embed": embed,
                "view": link_view,
                "content": None,
                "ephemeral": True,
            }

            if mode.value == "ios":
                keyward['content'] = cmd
                keyward['embed'].clear_fields()
            await interaction.followup.send(**keyward)

            try:
                payout_message: discord.Message = await self.bot.wait_for('message', check=check, timeout=60)
                if payout_message.author.id == interaction.user.id:
                    match payout_message.content.lower():

                        case "skip":
                            await interaction.followup.send("Skipping this payout", ephemeral=True)
                            await payout_message.delete()
                            await asyncio.sleep(0.5)
                            continue
                            
                        case "reject":
                            await interaction.followup.send("Rejecting this payout", ephemeral=True)
                            reject = await self.backend.reject_payout(interaction.user, payout)
                            if reject is True:
                                await payout_message.delete()
                                await asyncio.sleep(0.5)
                                continue
                            elif isinstance(reject, tuple):
                                await interaction.followup.send(f"Failed to reject this payout due to {reject[1]}" , ephemeral=True)
                                await asyncio.sleep(0.5)
                                break
                            elif reject is False:
                                await interaction.followup.send("Failed to reject this payout due to unknown error" , ephemeral=True)
                                await asyncio.sleep(0.5)
                                break
                        case "exit":
                            await interaction.followup.send("Exiting the express payout", ephemeral=True)
                            await payout_message.delete()
                            await asyncio.sleep(0.5)
                            break                            

                view = discord.ui.View()
                view.add_item(discord.ui.Button(label=f"Paid at", style=discord.ButtonStyle.url, url=payout_message.jump_url, emoji="<:tgk_link:1105189183523401828>"))
                embed = winner_message.embeds[0]
                embed.title = "Payout Paid"
                
                await payout_message.add_reaction("<:tgk_active:1082676793342951475>")
                try:
                    await queue_webhook.edit_message(winner_message.id, embed=embed, view=view)
                except Exception as e:
                    await interaction.followup.send(f"Failed to edit the message due webhooks are changed, there no need to worry about this as payout has been registered as paid", ephemeral=True)
                    await winner_message.add_reaction(self.backend.paid_emoji)


                self.bot.dispatch("more_pending", payout)

                if not payout['item']:
                    interaction.client.dispatch("payout_paid", payout_message, interaction.user, interaction.guild.get_member(payout['winner']), payout['prize'])
                else:
                    interaction.client.dispatch("payout_paid", payout_message, interaction.user, interaction.guild.get_member(payout['winner']), f"{payout['prize']}x{payout['item']}")

                await self.backend.claimed.delete(payout['_id'])

                continue

            except asyncio.TimeoutError:
                guild_config['express'] = False
                await self.backend.update_config(guild_config)
                self.backend.config_cache[interaction.guild.id]['express'] = False
                await interaction.followup.send("Timed out you can try command again", ephemeral=True)

                return
            
        guild_config['express'] = False
        await self.backend.update_config(guild_config)
        self.backend.config_cache[interaction.guild.id]['express'] = False
        await interaction.followup.send("All payouts have been paid", ephemeral=True)
    
    @express_payout.error
    async def express_payout_error(self, interaction: discord.Interaction, error):
        config = await self.backend.get_config(interaction.guild_id)
        if config is None: return
        config['express'] = False
        await self.backend.update_config(config)

            
    @commands.Cog.listener()
    async def on_payout_queue(self, host: discord.Member,event: str, win_message: discord.Message, queue_message: discord.Message, winner: discord.Member, prize: str, item: str = None):
        embed = discord.Embed(title="Payout | Queued", color=discord.Color.green(), timestamp=datetime.datetime.now(), description="")
        embed.description += f"**Host:** {host.mention}\n"
        embed.description += f"**Event:** {event}\n"
        embed.description += f"**Winner:** {winner.mention} ({winner.name})\n"
        embed.description += f"**Prize:** {prize:,}\n"
        embed.description += f"**Event Message:** [Jump to Message]({win_message.jump_url})\n"
        embed.description += f"**Queue Message:** [Jump to Message]({queue_message.jump_url})\n"
        embed.set_footer(text=f"Queue Message ID: {queue_message.id}")

        config = await self.backend.get_config(queue_message.guild.id)
        if config is None: return
        log_channel = queue_message.guild.get_channel(config['log_channel'])
        if log_channel is None: return
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_payout_claim(self, message: discord.Message, user: discord.Member):
        embed = discord.Embed(title="Payout | Claimed", color=discord.Color.green(), timestamp=datetime.datetime.now(), description="")
        embed.description += f"**User:** {user.mention}\n"
        embed.description += f"**Queue Message:** [Jump to Message]({message.jump_url})\n"
        embed.set_footer(text=f"Queue Message ID: {message.id}")

        config = await self.backend.get_config(message.guild.id)
        if config is None: return
        log_channel = message.guild.get_channel(config['log_channel'])
        if log_channel is None: return
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_payout_pending(self, message: discord.Message):
        embed = discord.Embed(title="Payout | Pending", color=discord.Color.yellow(), timestamp=datetime.datetime.now(), description="")
        embed.description += f"**Queue Message:** [Jump to Message]({message.jump_url})\n"
        embed.set_footer(text=f"Queue Message ID: {message.id}")

        config = await self.backend.get_config(message.guild.id)
        if config is None: return
        log_channel = message.guild.get_channel(config['log_channel'])
        if log_channel is None: return
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_payout_paid(self, message: discord.Message, user: discord.Member, winner: discord.Member, prize: str):
        embed = discord.Embed(title="Payout | Paid", color=discord.Color.dark_green(), timestamp=datetime.datetime.now(), description="")
        embed.description += f"**User:** {user.mention}\n"
        embed.description += f"**Winner:** {winner.mention} ({winner.name})\n"
        embed.description += f"**Prize:** {prize}\n"
        embed.description += f"**Queue Message:** [Jump to Message]({message.jump_url})\n"
        embed.set_footer(text=f"Queue Message ID: {message.id}")

        config = await self.backend.get_config(message.guild.id)
        if config is None: return
        log_channel = message.guild.get_channel(config['log_channel'])
        if log_channel is None: return
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_payout_expired(self, message: discord.Message, user: discord.Member):
        embed = discord.Embed(title="Payout | Expired", color=discord.Color.red(), timestamp=datetime.datetime.now(), description="")
        embed.description += f"**User:** {user.mention}\n"
        embed.description += f"**Queue Message:** [Jump to Message]({message.jump_url})\n"
        embed.set_footer(text=f"Queue Message ID: {message.id}")

        config = await self.backend.get_config(message.guild.id)
        if config is None: return
        log_channel = message.guild.get_channel(config['log_channel'])
        if log_channel is None: return
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_more_pending(self, info: dict):
        data = await self.backend.unclaimed.find_many_by_custom({'winner_message_id': info['winner_message_id']})
        if len(data) <= 0:
            winner_channel = self.bot.get_channel(info['channel'])
            try:
                winner_message = await winner_channel.fetch_message(info['winner_message_id'])
                await winner_message.remove_reaction(self.backend.pending_emoji, self.bot.user)
                await winner_message.add_reaction(self.backend.paid_emoji)
            except Exception as e:
                pass
        else:
            return

async def setup(bot):
    await bot.add_cog(PayoutV2(bot))

async def teardown(bot):
    for guild in await bot.payouts.config.find_many_by_custom({'express': True}):
        if guild['express'] is True:
            guild['express'] = False
            await bot.payouts.update_config(guild)
    await bot.remove_cog(PayoutV2(bot))


