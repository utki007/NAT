import random
import re
import discord
import datetime
import asyncio
import humanfriendly
from discord import app_commands, Interaction
from discord.ext import commands, tasks
from utils.db import Document
from typing import List
from ui.settings.payouts import Payout_Buttton, Payout_claim
from utils.views.confirm import Confirm
from utils.transformers import DMCConverter, MultipleMember


class Payout(commands.GroupCog, name="payout", description="Payout commands"):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.mongo['Payout_System']
        self.bot.payout_config = Document(self.db, "payout_config")
        self.bot.payout_queue = Document(self.db, "payout_queue")
        self.bot.payout_pending = Document(self.db, "payout_pending")
        self.claim_task = self.check_unclaim.start()
        self.bot.create_payout = self.create_payout
        self.claim_task_progress = False
        self.bot.dank_items_cache = {}
        self.paid_emoji = None
        self.pending_emoji = None
    
    def cog_unload(self):
        self.claim_task.cancel()
    
    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.guild.member_count < 10:
            await interaction.response.send_message("This command is only available for servers with more than 50 members.", ephemeral=True)
            return False
        else:
            data = await interaction.client.payout_config.find(interaction.guild.id)
            if data is None or data is False:
                await interaction.response.send_message("Payout system is not configured yet!", ephemeral=True)
                return False
            else:
                if 'enable_payouts' not in data.keys():
                    data['enable_payouts'] = False
                    await interaction.client.payout_config.update(data)

                if data['enable_payouts'] is False or data['enable_payouts'] is None:
                    await interaction.response.send_message("Payout system is disabled!", ephemeral=True)
                    return False                
        return True

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
    
    async def create_pending_embed(self, event: str, winner: discord.Member, prize: str, channel: discord.TextChannel, message: discord.Message, claim_time: int, host: discord.Member, item_data: dict) -> discord.Embed:
        embed = discord.Embed(title="Payout Queue", timestamp=datetime.datetime.now(), description="", color=self.bot.default_color)
        embed.description += f"**Event:** {event}\n"
        embed.description += f"**Winner:** {winner.mention}\n"
        if item_data != None:
            embed.description += f"**Prize:** `{prize}x {item_data['_id']}`\n"
        else:
            embed.description += f"**Prize:** `⏣ {prize:,}`\n"
        embed.description += f"**Channel:** {channel.mention}\n"
        embed.description += f"**Message:** [Click Here]({message.jump_url})\n"
        embed.description += f"**Claim Time:** <t:{int(claim_time)}:R>\n"
        embed.description += f"**Set By:** {host.mention}\n"
        embed.description += f"**Status:** `Pending`"
        embed.set_footer(text=f"ID: {message.id}")
        if item_data != None:
            value = f"**Name**: {item_data['_id']}\n"
            value += f"**Price**: ⏣ {item_data['price']:,}\n"
            value += f"Total Value of this payout with {prize}x {item_data['_id']} is ⏣ {prize * item_data['price']:,}"
            embed.add_field(name="Item Info", value=value)
        return embed
    
    async def create_payout(self, event: str, winner: discord.Member, host: discord.Member, prize: int, message: discord.Message, item: dict=None):
        config = await self.bot.payout_config.find(message.guild.id)
        queue_data = {
            '_id': None,
            'channel': message.channel.id,
            'guild': message.guild.id,
            'winner': winner.id,
            'prize': prize,
            'item': item['_id'] if item else None,
            'event': event,
            'claimed': False,
            'set_by': host.id,
            'winner_message_id': message.id,
            'queued_at': datetime.datetime.utcnow(),
            'claim_time': config['default_claim_time']
            }
        claim_time_timestamp = int((datetime.datetime.now() + datetime.timedelta(seconds=int(config['default_claim_time']))).timestamp())
        embed = await self.create_pending_embed(event, winner, prize, message.channel, message, claim_time_timestamp, host, item)
        claim_channel = message.guild.get_channel(config['pending_channel'])
        if not claim_channel: return		
        claim_message = await claim_channel.send(embed=embed, view=Payout_claim(), content=f"{winner.mention} Your prize has been queued for payout. Please claim it within <t:{claim_time_timestamp}:R> or it will rerolled.")
        queue_data['_id'] = claim_message.id
        await self.bot.payout_queue.insert(queue_data)
        await message.add_reaction(self.pending_emoji)
        return claim_message
    
    async def expire_payout(self, data: dict):
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Claim period expired!", style=discord.ButtonStyle.gray, disabled=True, emoji="<a:nat_cross:1010969491347357717>"))
        payout_config = await self.bot.payout_config.find(data['guild'])
        guild = self.bot.get_guild(data['guild'])
        channel = guild.get_channel(payout_config['pending_channel'])
        if not channel:
            await self.bot.payout_queue.delete(data['_id'])
            return
        try:
            message = await channel.fetch_message(data['_id'])
        except discord.NotFound:
            await self.bot.payout_queue.delete(data['_id'])
            return
        
        embed = message.embeds[0]
        embed = message.embeds[0]
        embed.title = "Payout Expired"
        embed.description = embed.description.replace("`Pending`", "`Expired`")
        await message.edit(embed=embed,view=view, content=f"<@{data['winner']}> your prize has expired. host has been notified.")
        host = guild.get_member(data['set_by'])

        dm_view = discord.ui.View()
        dm_view.add_item(discord.ui.Button(label="Payout Message Link", style=discord.ButtonStyle.url, url=message.jump_url))
        user = guild.get_member(data['winner'])

        event_channel = guild.get_channel(data['channel'])
        if not event_channel:
            await self.bot.payout_queue.delete(data['_id'])
            return
        
        try:
            event_message = await event_channel.fetch_message(data['winner_message_id'])
            for reactions in event_message.reactions:
                if reactions.emoji == self.pending_emoji:
                    async for user in reactions.users():
                        if user.id == self.bot.user.id:
                            await event_message.remove_reaction(self.pending_emoji, user)
                            break							
                    break
        except discord.NotFound:
            pass

        self.bot.dispatch("payout_expired", message, user)

        if host:
            if host.id != self.bot.user.id:
                try:
                    await host.send(f"<@{data['winner']}> has failed to claim within the deadline. Please reroll/rehost the event/giveaway.", view=dm_view)
                except discord.HTTPException:
                    pass
        await self.bot.payout_queue.delete(data['_id'])

    
    @commands.Cog.listener()
    async def on_ready(self):
        self.pending_emoji = self.bot.get_emoji(998834454292344842)
        self.paid_emoji = self.bot.get_emoji(998834454292344842)
        self.bot.add_view(Payout_Buttton())
        self.bot.add_view(Payout_claim())
        for item in await self.bot.dankItems.get_all(): self.bot.dank_items_cache[item['_id']] = item

    
    @tasks.loop(seconds=10)
    async def check_unclaim(self):
        if self.claim_task_progress: return
        self.claim_task_progress = True
        data = await self.bot.payout_queue.get_all()
        now = datetime.datetime.utcnow()
        for queue in data:
            if now > queue['queued_at'] + datetime.timedelta(seconds=queue['claim_time']):
                await self.expire_payout(queue)

            
        self.claim_task_progress = False
    
    @check_unclaim.before_loop
    async def before_check_unclaim(self):
        await self.bot.wait_until_ready()

    
    @app_commands.command(name="create", description="Create a new payout")
    @app_commands.describe(event="event name", message_id="winner message id", winners="winner of the event", quantity='A constant number like "123" or a shorthand like "5m"', item="what item did they win?")
    @app_commands.autocomplete(item=item_autocomplete)
    async def payout_create(self, interaction: discord.Interaction, event: str, message_id: str, winners: app_commands.Transform[discord.Member, MultipleMember], quantity: app_commands.Transform[int, DMCConverter], item: str=None):
        data = await self.bot.payout_config.find(interaction.guild.id)
        if data is None: return await interaction.response.send_message("Payout system is not configured yet!", ephemeral=True)

        user_roles = [role.id for role in interaction.user.roles]
        if (set(user_roles) & set(data['event_manager_roles'])):
            pass
        else:
            return await interaction.response.send_message("You are not allowed to use this command!", ephemeral=True)
        
        claim_time_seconds = data['default_claim_time'] if data['default_claim_time'] is not None else 86400

        try:
            event_message = await interaction.channel.fetch_message(message_id)
        except discord.NotFound:
            return await interaction.response.send_message("Error: Message not found! Please make sure you have the correct message id and in same channel as the message.", ephemeral=True)

        claim_channel = interaction.guild.get_channel(data['pending_channel'])
        if claim_channel is None:
            return await interaction.response.send_message("Error: Claim channel not found! Please make sure your configured claim channel is still valid.", ephemeral=True)

        queue_channel = interaction.guild.get_channel(data['queue_channel'])
        if queue_channel is None:
            return await interaction.response.send_message("Error: Queue channel not found! Please make sure your configured queue channel is still valid.", ephemeral=True)


        confrim_embed = discord.Embed(title="Payout confirmation", description="", color=0x2b2d31)
        
        confrim_embed.description += f"**Event:** {event}\n"
        confrim_embed.description += f"**Winners:** {', '.join([winner.mention for winner in winners])}\n"
        if item:
            item_data = await interaction.client.dank_items.find(item)
            if not item_data:
                return await interaction.response.send_message("Error: Item not found! Please make sure you have the correct item name.", ephemeral=True)
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
            return await interaction.edit_original_message(content="Payout cancelled!")
        
        loading_embed = discord.Embed(description=f"<a:loading:998834454292344842> | Setting up the payout for total of `{len(winners)}` winners!")
        loading_embed.set_footer(text="This might take a while depending on the number of winners.")
        await view.interaction.response.edit_message(view=None, embed=loading_embed)

        for winner in winners:
            queue_data = await self.bot.payout_queue.find({'winner_message_id': event_message.id, 'winner': winner.id})
            pending_data = await self.bot.payout_pending.find({'winner_message_id': event_message.id, 'winner': winner.id})

            if queue_data or pending_data:
                dupe = None
                if queue_data:
                    try:
                        await claim_channel.fetch_message(queue_data['_id'])
                        dupe = True
                    except discord.NotFound:
                        await self.bot.payout_queue.delete(queue_data['_id'])
                        dupe = False
                
                if pending_data:
                    try:
                        await claim_channel.fetch_message(pending_data['_id'])
                        dupe = True
                    except discord.NotFound:
                        await self.bot.payout_pending.delete(pending_data['_id'])
                        dupe = False
                
                if dupe:
                    loading_embed.description += f"\n<:dynoError:1000351802702692442> | {winner.mention} `({winner.name})` already has a pending payout. Skipping..."
                    await interaction.edit_original_response(embed=loading_embed)
                    continue
            
            payout_message = await self.create_payout(event=event, winner=winner, host=interaction.user, prize=quantity, message=event_message, item=item_data)


            if isinstance(payout_message, discord.Message):
                if winners.index(winner) == 0:
                    link_view = discord.ui.View()
                    link_view.add_item(discord.ui.Button(label="Queued Payouts", url=payout_message.jump_url, style=discord.ButtonStyle.link))
                    await interaction.edit_original_response(view=link_view)

                loading_embed.description += f"\n<:octane_yes:1019957051721535618> | {winner.mention} `({winner.name})` has been queued for payout!"
            else:
                loading_embed.description += f"\n<:dynoError:1000351802702692442> | {winner.mention} `({winner.name})` has failed to queue for payout!"
            await interaction.edit_original_response(embed=loading_embed)
            self.bot.dispatch("payout_queue", interaction.user, event, event_message, payout_message, winner, quantity)
            await asyncio.sleep(0.75)

        await asyncio.sleep(2)

        loading_embed.description += f"\n<:octane_yes:1019957051721535618> | Payout has been queued for total of `{len(winners)}` winners!"
        await event_message.add_reaction(self.pending_emoji)
        await interaction.edit_original_response(embed=loading_embed)

    @app_commands.command(name="delete", description="Only use this command if the payout message is deleted by accident.")
    @app_commands.describe(message_id="message id of the payout")
    async def payout_delete(self, interaction: discord.Interaction, message_id: str):
        data = await self.bot.payout_config.find(interaction.guild.id)
        if data is None: return await interaction.response.send_message("Payout system is not configured yet!", ephemeral=True)

        user_roles = [role.id for role in interaction.user.roles]
        if (set(user_roles) & set(data['event_manager_roles'])):
            pass
        else:
            return await interaction.response.send_message("You are not allowed to use this command!", ephemeral=True)

        await self.bot.payout_queue.delete(message_id)
        await self.bot.payout_queue.delete(message_id)
        await interaction.response.send_message("if any payout was attached to this message then it has been deleted.", ephemeral=True)
    
    @app_commands.command(name="search", description="Search for a payout message")
    @app_commands.describe(message_id="The message ID of the event message.", user="user's payouts you want to search for")
    async def payout_search(self, interaction: discord.Interaction, message_id: str=None, user: discord.Member=None):
        if message_id is None and user is None:
            await interaction.response.send_message("Please provide either message id or user to search for.", ephemeral=True)
            return
        
        config = await self.bot.payout_config.find(interaction.guild.id)
        if config is None: return await interaction.response.send_message("Payout system is not configured yet!", ephemeral=True)

        user_roles = [role.id for role in interaction.user.roles]
        if (set(user_roles) & set(config['event_manager_roles'])):
            pass
        else:
            return await interaction.response.send_message("You are not allowed to use this command!", ephemeral=True)
        
        unclaim = await interaction.client.payout_queue.find_many_by_custom({'winner_message_id': int(message_id)})
        embed = discord.Embed(title="Unclaimed payouts", description="", color=0x2b2d31)
        queue_channel = interaction.guild.get_channel(config['pending_channel'])
        if len(unclaim) == 0:
            embed.description = "All Payouts are claimed/Expired/Not created yet."
        else:
            i = 1
            for entey in unclaim:
                embed.description += f"\n**{i}.** https://discord.com/channels/{interaction.guild.id}/{queue_channel.id}/{entey['_id']}"
                i += 1

        await interaction.client.payout_pending.find_many_by_custom({'winner_message_id': int(message_id)})
        pending_embed = discord.Embed(title="Pending Payout Search", color=0x2b2d31, description="")
        pendin_channel = interaction.guild.get_channel(config['queue_channel'])

        if len(unclaim) == 0:
            pending_embed.description = "All Payouts are Paid/Rejected/Not created yet."
        else:
            i = 1
            for entey in unclaim:
                pending_embed.description += f"\n**{i}.** https://discord.com/channels/{interaction.guild.id}/{pendin_channel.id}/{entey['_id']}"
                i += 1
        
        await interaction.response.send_message(embeds=[embed, pending_embed], ephemeral=False)
    
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

        config = await self.bot.payout_config.find(queue_message.guild.id)
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

        config = await self.bot.payout_config.find(message.guild.id)
        if config is None: return
        log_channel = message.guild.get_channel(config['log_channel'])
        if log_channel is None: return
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_payout_pending(self, message: discord.Message):
        embed = discord.Embed(title="Payout | Pending", color=discord.Color.yellow(), timestamp=datetime.datetime.now(), description="")
        embed.description += f"**Queue Message:** [Jump to Message]({message.jump_url})\n"
        embed.set_footer(text=f"Queue Message ID: {message.id}")

        config = await self.bot.payout_config.find(message.guild.id)
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

        config = await self.bot.payout_config.find(message.guild.id)
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

        config = await self.bot.payout_config.find(message.guild.id)
        if config is None: return
        log_channel = message.guild.get_channel(config['log_channel'])
        if log_channel is None: return
        await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_payout_payment(self, message: discord.Message, user: discord.Member, winner: discord.Member, payout_channel: discord.TextChannel,data: dict, interaction: discord.Interaction):
        def check(m: discord.Message):
            if m.channel.id != payout_channel.id: 
                return False
            if m.author.id != 270904126974590976:
                return False
            
            if len(m.embeds) == 0: 
                return False
            embed = m.embeds[0]
            if embed.description.startswith("Successfully paid"):

                found_winner = message.guild.get_member(int(embed.description.split(" ")[2].replace("<", "").replace(">", "").replace("!", "").replace("@", ""))) 
                if winner.id != found_winner.id: 
                    return False
                
                items = re.findall(r"\*\*(.*?)\*\*", embed.description)[0]
                if "⏣" in items:
                    items = int(items.replace("⏣", "").replace(",", ""))
                    if items == data['prize']:
                        return True
                    else:
                        return False
                else:
                    emojis = list(set(re.findall(":\w*:\d*", items)))
                    for emoji in emojis :items = items.replace(emoji,"",100); items = items.replace("<>","",100);items = items.replace("<a>","",100);items = items.replace("  "," ",100)
                    mathc = re.search(r"(\d+)x (.+)", items)
                    item_found = mathc.group(2)
                    quantity_found = int(mathc.group(1))
                    if item_found == data['item'] and quantity_found == data['prize']:
                        return True			

        try:
            msg: discord.Message = await self.bot.wait_for('message', check=check, timeout=60)
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label=f"Paid at", style=discord.ButtonStyle.url, url=msg.jump_url, emoji="<:tgk_link:1105189183523401828>"))
            embed = message.embeds[0]
            embed.description += f"\n**Payout Location:** {msg.jump_url}"
            embed.description = embed.description.replace("`Initiated`", "`Successfuly Paid`")
            embed.description += f"\n**Santioned By:** {user.mention}"
            embed.title = "Successfully Paid"
            await self.bot.payout_pending.delete(data['_id'])
            await msg.add_reaction("<:tgk_active:1082676793342951475>")
            await asyncio.sleep(random.randint(1, 5))
            await interaction.message.edit(embeds=[embed], view=view)
            is_more_payout_pending = await interaction.client.payout_pending.find_many_by_custom({'winner_message_id': data['winner_message_id']})
            if len(is_more_payout_pending) <= 0:
                winner_channel = interaction.client.get_channel(data['channel'])
                try:
                    winner_message = await winner_channel.fetch_message(data['winner_message_id'])
                    await winner_message.remove_reaction(self.pending_emoji, interaction.client.user)
                    await winner_message.add_reaction(self.paid_emoji)
                except Exception as e:
                    pass

        except asyncio.TimeoutError:
            embed = message.embeds[0]
            embed.title = "Payout Queue"
            embed.description = embed.description.replace("`Initiated`", "`Awaiting Payment`")
            view = Payout_Buttton()
            view.children[2].disabled = False
            await interaction.message.edit(embeds=[embed], view=view)
            await message.reply(f"{user.mention} This payout could not be confirmed in time. Please try again, if you think it's a mistake, please contact a `developers`", delete_after=10)
        

    @commands.Cog.listener()
    async def on_more_pending(self, info: dict):
        data = await self.bot.payout_pending.find_many_by_custom({'winner_message_id': info['_id']})
        if len(data) <= 0:
            winner_channel = self.bot.get_channel(info['channel'])
            try:
                winner_message = await winner_channel.fetch_message(info['winner_message_id'])
                await winner_message.remove_reaction(self.pending_emoji, self.bot.user)
                await winner_message.add_reaction(self.paid_emoji)
            except Exception as e:
                pass
        else:
            return
        
    @app_commands.command(name="express", description="start doing payouts for the oldest payouts with the help of me")
    async def express_payout(self, interaction: discord.Interaction):
        # premium = await self.bot.premium.find(interaction.guild.id)
        # if premium is None: 
        #     await interaction.response.send_message("This command is only available for premium servers.", ephemeral=True)
        #     return
        
        config = await self.bot.payout_config.find(interaction.guild.id)
        if config is None: return
        user_roles = [role.id for role in interaction.user.roles]
        if not (set(user_roles) & set(config['manager_roles'])): 
            await interaction.response.send_message("You don't have permission to use this command", ephemeral=True)
            return
        payouts = await self.bot.payout_pending.find_many_by_custom({'guild': interaction.guild.id})
        if len(payouts) <= 0:
            await interaction.response.send_message("There are no payouts pending", ephemeral=True)
            return
        payouts = payouts[:25]
        if config['express'] is True:
            await interaction.response.send_message("There is already a express payout in progress", ephemeral=True)
            return

        await interaction.response.send_message("## Starting Payouts for oldest 25 payouts in queue", ephemeral=True)
        queue_channel = interaction.guild.get_channel(config['queue_channel'])
        config['express'] = True
        await interaction.client.payout_config.update(config)
        for data in payouts:
            def check(m: discord.Message):
                if m.channel.id != interaction.channel.id: 
                    return False
                if m.author.id != 270904126974590976:
                    if m.author.id == interaction.user.id:
                        if m.content.lower() in ["skip", "next", "pass"]:
                            return True
                    return False

                if len(m.embeds) == 0: 
                    return False
                embed = m.embeds[0]
                if embed.description is None or embed.description == "": return False
                if embed.description.startswith("Successfully paid"):

                    found_winner = interaction.guild.get_member(int(embed.description.split(" ")[2].replace("<", "").replace(">", "").replace("!", "").replace("@", ""))) 
                    if data['winner'] != found_winner.id: 
                        return False
                    items = re.findall(r"\*\*(.*?)\*\*", embed.description)[0]
                    if "⏣" in items:
                        items = int(items.replace("⏣", "").replace(",", ""))
                        if items == data['prize']:
                            return True
                        else:
                            return False
                    else:
                        emojis = list(set(re.findall(":\w*:\d*", items)))
                        for emoji in emojis :items = items.replace(emoji,"",100); items = items.replace("<>","",100);items = items.replace("<a>","",100);items = items.replace("  "," ",100)
                        mathc = re.search(r"(\d+)x (.+)", items)
                        item_found = mathc.group(2)
                        quantity_found = int(mathc.group(1))
                        if item_found == data['item'] and quantity_found == data['prize']:
                            return True

            embed = discord.Embed(title="Payout Info", description="")
            embed.description += f"**Winner:** <@{data['winner']}>\n"
            if data['item']:
                embed.description += f"**Price:** {data['prize']}x{data['item']}\n"
            else:
                embed.description += f"**Price:** ⏣ {data['prize']:,}\n"
            embed.description += f"**Channel:** <#{data['channel']}>\n"
            embed.description += f"**Host:** <@{data['set_by']}>\n"
            embed.description += f"* Note: To skip this payout, type `skip`, `next` or `pass`"
            cmd = ""
            if not data['item']:
                cmd += f"/serverevents payout user:{data['winner']} quantity:{data['prize']}"
            else:
                cmd += f"/serverevents payout user:{data['winner']} quantity:{data['prize']} item:{data['item']}"
            embed.add_field(name="Command", value=f"{cmd}")
            embed.set_footer(text=f"Queue Number: {payouts.index(data)+1}/{len(payouts)}")
            await asyncio.sleep(1.25)
            link_view = discord.ui.View()
            link_view.add_item(discord.ui.Button(label=f"Queue Link", style=discord.ButtonStyle.url, url=f"https://discord.com/channels/{interaction.guild.id}/{queue_channel.id}/{data['_id']}", emoji="<:tgk_link:1105189183523401828>"))
            await interaction.followup.send(embed=embed, ephemeral=True, view=link_view)
            try:
                msg: discord.Message = await self.bot.wait_for('message', check=check, timeout=60)
                if msg.author.id == interaction.user.id:
                    if msg.content.lower() in ["skip", "next", "pass"]:
                        await interaction.followup.send("Skipping...", ephemeral=True)
                        await msg.delete()
                        continue

                view = discord.ui.View()
                view.add_item(discord.ui.Button(label=f"Paid at", style=discord.ButtonStyle.url, url=msg.jump_url, emoji="<:tgk_link:1105189183523401828>"))
                try:
                    winner_message = await queue_channel.fetch_message(data['_id'])
                except discord.NotFound:
                    continue
                embed = winner_message.embeds[0]
                embed.description += f"\n**Payout Location:** {msg.jump_url}"
                embed.description = embed.description.replace("`Awaiting Payment`", "`Successfuly Paid`")
                embed.description = embed.description.replace("`Initiated`", "`Successfuly Paid`")
                embed.title = "Successfully Paid"
                await self.bot.payout_pending.delete(data['_id'])
                await msg.add_reaction("<:tgk_active:1082676793342951475>")
                await winner_message.edit(embed=embed, view=view, content=None)
                self.bot.dispatch("more_pending", data)
                if not data['item']:
                    interaction.client.dispatch("payout_paid", msg, interaction.user, interaction.guild.get_member(data['winner']), data['prize'])
                else:
                    interaction.client.dispatch("payout_paid", msg, interaction.user, interaction.guild.get_member(data['winner']), f"{data['prize']}x{data['item']}")
                continue

            except asyncio.TimeoutError:
                config['express'] = False
                await interaction.client.payout_config.update(config)
                await interaction.followup.send("Timed out you can try command again", ephemeral=True)
                return

        config['express'] = False
        await interaction.client.payout_config.update(config)
        await interaction.followup.send("Finished Express Payout", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Payout(bot), guilds=[discord.Object(999551299286732871), discord.Object(1072079211419938856), discord.Object(785839283847954433)])