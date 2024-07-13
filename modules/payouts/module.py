from discord import app_commands
from discord.ext import commands, tasks
from utils.transformers import DMCConverter, MultipleMember, MessageConverter
from utils.embeds import get_warning_embed
from typing import List
from utils.views.confirm import Confirm

from .db import PayoutDB, PayoutConfigCache, PayoutQueue

import re
import humanfriendly
import asyncio
import discord
import datetime


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

    def cog_unload(self):
        self.check_claim.cancel()

    async def item_autocomplete(
        self, interaction: discord.Interaction, string: str
    ) -> List[app_commands.Choice[str]]:
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

    @tasks.loop(seconds=10)
    async def check_claim(self):
        if self.check_claim_task:
            return
        self.claim_task = True
        for payout in await self.backend.unclaimed.get_all():
            payout: PayoutQueue = payout
            if datetime.datetime.utcnow() >= payout["queued_at"] + datetime.timedelta(
                seconds=payout["claim_time"]
            ):
                self.bot.dispatch("payout_claim_expired", payout)
                await asyncio.sleep(1.25)

        self.check_claim_task = False

    @check_claim.before_loop
    async def before_check_claim(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_payout_claim_expired(self, payout: PayoutQueue):
        if payout["_id"] in self.in_expire_task:
            return
        self.in_expire_task.append(payout["_id"])
        config: PayoutConfigCache = await self.backend.get_config(payout["guild"])

        if config is None:
            await self.backend.unclaimed.delete(payout["_id"])
            return
        try:
            guild: discord.Guild = self.bot.get_guild(payout["guild"])
            claim_channel: discord.TextChannel = config["claim_channel"].channel
            message: discord.Message = await claim_channel.fetch_message(payout["_id"])
            embed = message.embeds[0]
            embed.title = "Payout Expired"
            embed.color = discord.Color.red()
            view = discord.ui.View()
            view.add_item(
                discord.ui.Button(
                    label="Claim time expired",
                    style=discord.ButtonStyle.gray,
                    disabled=True,
                    emoji="<a:nat_cross:1010969491347357717>",
                )
            )
            view.add_item(
                discord.ui.Button(
                    label="Event Link",
                    style=discord.ButtonStyle.link,
                    url=f"https://discord.com/channels/{guild.id}/{payout['channel']}/{payout['winner_message_id']}",
                    emoji="<:tgk_link:1105189183523401828>",
                )
            )
            await config["claim_channel"].edit_message(
                message.id,
                embed=embed,
                view=view,
                content=f"<@{payout['winner']}>, your payout has expired!",
            )
            host: discord.Member = guild.get_member(payout["set_by"])
            host_view = discord.ui.View()
            host_view.add_item(
                discord.ui.Button(
                    label="Payout Link",
                    style=discord.ButtonStyle.link,
                    url=message.jump_url,
                    emoji="<:tgk_link:1105189183523401828>",
                )
            )
            await host.send(
                f"Your payout for **{payout['event']}** has expired, please requeue it again.",
                view=host_view,
            )
        except Exception:
            pass
        await self.backend.unclaimed.delete(payout["_id"])
        self.in_expire_task.remove(payout["_id"])

    @app_commands.command(name="create", description="Create a new payout")
    @app_commands.describe(
        event="event name",
        message_id="winner message id",
        winners="winner of the event",
        quantity='A constant number like "123" or a shorthand like "5m"',
        item="what item did they win?",
    )
    @app_commands.autocomplete(item=item_autocomplete)
    @app_commands.rename(winners="winners_list")
    async def payout_create(
        self,
        interaction: discord.Interaction,
        event: str,
        message_id: app_commands.Transform[discord.Message, MessageConverter],
        winners: app_commands.Transform[discord.Member, MultipleMember],
        quantity: app_commands.Transform[int, DMCConverter],
        item: str = None,
    ):
        guild_config = await self.backend.get_config(interaction.guild_id)
        if guild_config is None:
            return await interaction.response.send_message(
                "Payouts are not enabled on this server", ephemeral=True
            )

        user_roles = [role.id for role in interaction.user.roles]
        if (set(user_roles) & set(guild_config["event_manager_roles"])) or (
            set(user_roles) & set(guild_config["manager_roles"])
        ):
            pass
        else:
            return await interaction.response.send_message(
                "You are not allowed to use this command!", ephemeral=True
            )

        if (
            guild_config["claim_channel"] is None
            or guild_config["claimed_channel"] is None
        ):
            embed = await get_warning_embed(
                "Unknown Webhook! Please reconfigure the settings."
            )
            return await interaction.response.send_message(ephemeral=True, embed=embed)

        claim_time_seconds = (
            guild_config["default_claim_time"]
            if guild_config["default_claim_time"] is not None
            else 86400
        )

        if not isinstance(message_id, discord.Message):
            await interaction.response.send_message(
                "Please provide a valid message id", ephemeral=True
            )
            return
        event_message = message_id

        if (
            guild_config["claim_channel"] is None
            or guild_config["claimed_channel"] is None
        ):
            embed = await get_warning_embed(
                "Unknown Webhook! Please reconfigure the settings."
            )
            return await interaction.response.send_message(ephemeral=True, embed=embed)

        if len(winners) == 0:
            return await interaction.response.send_message(
                "Oops! Can't find any winners!\nDouble-check that winners are vaild",
                ephemeral=True,
            )

        confrim_embed = discord.Embed(
            title="Payout confirmation", description="", color=0x2B2D31
        )

        confrim_embed.description += f"**Event:** {event}\n"
        confrim_embed.description += (
            f"**Winners:** {', '.join([winner.mention for winner in winners])}\n"
        )

        if item:
            item_data = await interaction.client.dankItems.find(item)
            if not item_data:
                return await interaction.response.send_message(
                    "Oops! can't find item with that name", ephemeral=True
                )
            confrim_embed.description += f"**Prize:** {quantity} x {item}\n"
        else:
            confrim_embed.description += f"**Prize: ⏣ {quantity:,} Each**\n"
            item_data = None
        confrim_embed.description += f"**Message** {event_message.jump_url}\n"
        confrim_embed.description += (
            f"**Claim Time:** {humanfriendly.format_timespan(claim_time_seconds)}\n"
        )

        view = Confirm(interaction.user, 60)
        view.children[0].label = "Confirm"
        view.children[0].style = discord.ButtonStyle.green
        view.children[1].label = "Cancel"
        view.children[1].style = discord.ButtonStyle.red

        await interaction.response.send_message(
            embed=confrim_embed, view=view, ephemeral=True
        )
        view.message = await interaction.original_response()
        await view.wait()

        if view.value is None or view.value is False:
            return await interaction.edit_original_response(
                content="Payout creation has been cancelled.", view=None, embed=None
            )

        loading_embed = discord.Embed(
            description=f"<a:loading:998834454292344842> | Setting up the payout for total of `{len(winners)}` winners!"
        )
        loading_embed.set_footer(
            text="This might take a while depending on the number of winners."
        )
        await view.interaction.response.edit_message(view=None, embed=loading_embed)

        for winner in winners:
            winner: discord.Member
            queue_data = await self.backend.unclaimed.find(
                {"winner_message_id": event_message.id, "winner": winner.id}
            )
            pending_data = await self.backend.claimed.find(
                {"winner_message_id": event_message.id, "winner": winner.id}
            )

            if queue_data or pending_data:
                dupe = None
                if queue_data:
                    try:
                        await guild_config["claim_channel"].channel.fetch_message(
                            queue_data["_id"]
                        )
                        dupe = True
                    except discord.NotFound:
                        await self.backend.unclaimed.delete(queue_data["_id"])
                        dupe = False

                if pending_data:
                    try:
                        await guild_config["claimed_channel"].channel.fetch_message(
                            pending_data["_id"]
                        )
                        dupe = True
                    except discord.NotFound:
                        await self.backend.claimed.delete(pending_data["_id"])
                        dupe = False

                if dupe:
                    loading_embed.description += f"\n<:dynoError:1000351802702692442> | {winner.mention} `({winner.name})` already has a pending payout. Skipping..."
                    await interaction.edit_original_response(embed=loading_embed)
                    continue

            payout_message = await self.backend.create_payout(
                config=guild_config,
                event=event,
                winner=winner,
                host=interaction.user,
                prize=quantity,
                message=event_message,
                item=item_data,
            )

            if isinstance(payout_message, discord.Message):
                if winners.index(winner) == 0:
                    link_view = discord.ui.View()
                    link_view.add_item(
                        discord.ui.Button(
                            label="Queued Payouts",
                            url=payout_message.jump_url,
                            style=discord.ButtonStyle.link,
                        )
                    )
                    await interaction.edit_original_response(view=link_view)
                    await asyncio.sleep(1.5)

                loading_embed.description += f"\n<:octane_yes:1019957051721535618> | {winner.mention} `({winner.name})` has been queued for payout!"

                await interaction.edit_original_response(embed=loading_embed)
                self.bot.dispatch(
                    "payout_queue",
                    interaction.user,
                    event,
                    event_message,
                    payout_message,
                    winner,
                    quantity,
                )

            await asyncio.sleep(2)

        loading_embed.description = f"\n<:octane_yes:1019957051721535618> | Payout has been queued for total of `{len(winners)}` winners!"
        await interaction.edit_original_response(embed=loading_embed)

    @app_commands.command(name="clear", description="Search for a payout message")
    @app_commands.describe(message_id="The message ID of the event message.")
    async def payout_search_(
        self, interaction: discord.Interaction, message_id: str = None
    ):
        data = await self.backend.get_config(interaction.guild_id)
        if data is None:
            return await interaction.response.send_message(
                "Payout system is not configured yet!", ephemeral=True
            )

        user_roles = [role.id for role in interaction.user.roles]
        if set(user_roles) & set(data["manager_roles"]):
            pass
        else:
            return await interaction.response.send_message(
                "You are not allowed to use this command!", ephemeral=True
            )

        if data["claim_channel"] is None or data["claimed_channel"] is None:
            embed = await get_warning_embed(
                "Unknown Webhook! Please reconfigure the settings."
            )
            return await interaction.response.send_message(ephemeral=True, embed=embed)

        await self.backend.unclaimed.find_many_by_custom(
            {"winner_message_id": int(message_id)}
        )
        await self.backend.claimed.find_many_by_custom(
            {"winner_message_id": int(message_id)}
        )
        await interaction.response.send_message(
            "if any payout was attached to this message then it has been deleted.",
            ephemeral=True,
        )

    @app_commands.command(name="search", description="Search for a payout message")
    @app_commands.describe(
        message_id="The message ID of the event message.",
        user="user's payouts you want to search for",
    )
    async def payout_search(
        self,
        interaction: discord.Interaction,
        message_id: str = None,
        user: discord.Member = None,
    ):
        if not message_id and not user:
            return await interaction.response.send_message(
                "Please provide a message id", ephemeral=True
            )
        


        config = await self.backend.get_config(interaction.guild_id)
        if config is None:
            return await interaction.response.send_message(
                "Payout system is not configured yet!", ephemeral=True
            )

        user_roles = [role.id for role in interaction.user.roles]
        if (set(user_roles) & set(config["event_manager_roles"])) or (
            set(user_roles) & set(config["manager_roles"])
        ):
            pass
        else:
            return await interaction.response.send_message(
                "You are not allowed to use this command!", ephemeral=True
            )

        if config["claim_channel"] is None or config["claimed_channel"] is None:
            embed = await get_warning_embed(
                "Unknown Webhook! Please reconfigure the settings."
            )
            return await interaction.response.send_message(ephemeral=True, embed=embed)

        if message_id:
            unclaim = await self.backend.unclaimed.find_many_by_custom(
                {"winner_message_id": int(message_id)}
            )
        elif user:
            unclaim = await self.backend.unclaimed.find_many_by_custom(
                {"winner": user.id}
            )

        embed = discord.Embed(title="Unclaimed payouts", description="", color=0x2B2D31)
        claim_channel = interaction.guild.get_channel(config["claimed_channel"])
        if len(unclaim) == 0:
            embed.description = "All Payouts are claimed/Expired/Not created yet."
        else:
            i = 1
            for entey in unclaim:
                embed.description += f"\n**{i}.** https://discord.com/channels/{interaction.guild.id}/{claim_channel.id}/{entey['_id']}"
                i += 1

        if message_id:
            claimed = await self.backend.claimed.find_many_by_custom(
                {"winner_message_id": int(message_id)}
            )
        elif user:
            claimed = await self.backend.claimed.find_many_by_custom(
                {"winner": user.id}
            )
        pending_embed = discord.Embed(
            title="Pending Payout Search", color=0x2B2D31, description=""
        )
        pendin_channel = interaction.guild.get_channel(config["claim_channel"])

        if len(claimed) == 0:
            pending_embed.description = "All Payouts are Paid/Rejected/Not created yet."
        else:
            i = 1
            for entey in claimed:
                pending_embed.description += f"\n**{i}.** https://discord.com/channels/{interaction.guild.id}/{pendin_channel.id}/{entey['_id']}"
                i += 1

        await interaction.response.send_message(
            embeds=[embed, pending_embed], ephemeral=False
        )

    @app_commands.command(
        name="express",
        description="start doing payouts for the oldest payouts with the help of me",
    )
    @app_commands.describe(mode="accessibility mode of the command")
    @app_commands.choices(
        mode=[
            app_commands.Choice(name="PC", value="pc"),
            app_commands.Choice(name="Android/iOS", value="ios"),
        ]
    )
    async def express_payout(
        self, interaction: discord.Interaction, mode: app_commands.Choice[str] = None
    ):
        if mode is None:
            mode = app_commands.Choice(name="PC/Android", value="pc")

        guild_config = await self.backend.get_config(interaction.guild_id)
        if guild_config is None:
            return
        user_roles = [role.id for role in interaction.user.roles]
        if not (set(user_roles) & set(guild_config["manager_roles"])):
            await interaction.response.send_message(
                "You don't have permission to use this command", ephemeral=True
            )
            return

        if (
            guild_config["claim_channel"] is None
            or guild_config["claimed_channel"] is None
        ):
            embed = await get_warning_embed(
                "Unknown Webhook! Please reconfigure the settings."
            )
            return await interaction.response.send_message(ephemeral=True, embed=embed)

        if interaction.channel.id != guild_config["payout_channel"]:
            await interaction.response.send_message(
                f"Please use this command in <#{guild_config['payout_channel']}>",
                ephemeral=True,
            )
            return

        payouts = await self.backend.claimed.find_many_by_custom(
            {"guild": interaction.guild.id}
        )
        if len(payouts) <= 0:
            await interaction.response.send_message(
                "There are no payouts pending", ephemeral=True
            )
            return

        elif len(payouts) > 50:
            payouts = payouts[:50]

        # if isinstance(premium, dict):
        #     if premium["premium"] is True:
        #         payouts = payouts[: premium["payout_limit"]]
        # else:
        #     if len(payouts) > 20:
        #         payouts = payouts[:20]

        if guild_config["express"] is True:
            await interaction.response.send_message(
                "There is already a express payout in progress", ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"## Starting Payouts for oldest {len(payouts)} payouts in queue",
            ephemeral=True,
        )
        queue_webhook = guild_config["claimed_channel"]
        claim_channel = queue_webhook.channel

        guild_config["express"] = True
        await self.backend.update_config(guild_config)
        self.backend.config_cache[interaction.guild.id]["express"] = True

        for payout in payouts:
            try:
                winner_message = await claim_channel.fetch_message(payout["_id"])
            except discord.NotFound:
                await self.backend.claimed.delete(payout["_id"])
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
                if embed.description is None or embed.description == "":
                    return False
                if embed.description.startswith("Successfully paid"):
                    found_winner = interaction.guild.get_member(
                        int(
                            embed.description.split(" ")[2]
                            .replace("<", "")
                            .replace(">", "")
                            .replace("!", "")
                            .replace("@", "")
                        )
                    )
                    if payout["winner"] != found_winner.id:
                        return False
                    items = re.findall(r"\*\*(.*?)\*\*", embed.description)[0]
                    if "⏣" in items:
                        items = int(items.replace("⏣", "").replace(",", "", 100))
                        if items == payout["prize"]:
                            return True
                        else:
                            return False
                    else:
                        emojis = list(set(re.findall(":\w*:\d*", items)))
                        for emoji in emojis:
                            items = items.replace(emoji, "", 100)
                            items = items.replace("<>", "", 100)
                            items = items.replace("<a>", "", 100)
                            items = items.replace("  ", " ", 100)
                        mathc = re.search(r"^([\d,]+) (.+)$", items)
                        item_found = mathc.group(2)
                        quantity_found = int(mathc.group(1).replace(",", "", 100))
                        if (
                            item_found.lower() == payout["item"].lower()
                            and quantity_found == payout["prize"]
                        ):
                            return True

            embed = discord.Embed(title="Payout Info", description="", color=0x2B2D31)
            embed.description += f"**Winner:** <@{payout['winner']}>\n"

            if payout["item"]:
                embed.description += f"**Price:** {payout['prize']}x {payout['item']}\n"
            else:
                embed.description += f"**Price:** ⏣ {payout['prize']:,}\n"

            embed.description += f"**Channel:** <#{payout['channel']}>\n"
            embed.description += f"**Host:** <@{payout['set_by']}>\n"
            embed.description += "\n**Type the below commands to execute:**\n* skip: skip this payout\n* reject: reject this payout\n* exit: exit the entire payout queue\n"
            if "claimed_at" in payout.keys():
                embed.description += f"\n**Payout Claimed At:** <t:{int(payout['claimed_at'].timestamp())}:R>\n"
            embed.description += f"**Timeout:** <t:{int((datetime.datetime.now() + datetime.timedelta(seconds=60)).timestamp())}:R>\n"
            cmd = ""
            if not payout["item"]:
                cmd += f"/serverevents payout user:{payout['winner']} quantity:{payout['prize']}"
            else:
                cmd += f"/serverevents payout user:{payout['winner']} quantity:{payout['prize']} item:{payout['item']}"

            embed.add_field(name="Command", value=cmd, inline=False)
            embed.set_footer(
                text=f"Queue Number: {payouts.index(payout)+1}/{len(payouts)}"
            )

            await asyncio.sleep(1.25)
            link_view = discord.ui.View()
            link_view.add_item(
                discord.ui.Button(
                    label="Queue Link",
                    style=discord.ButtonStyle.url,
                    url=f"https://discord.com/channels/{interaction.guild.id}/{claim_channel.id}/{payout['_id']}",
                    emoji="<:tgk_link:1105189183523401828>",
                )
            )
            link_view.add_item(
                discord.ui.Button(
                    label="Event Link",
                    style=discord.ButtonStyle.url,
                    url=f"https://discord.com/channels/{interaction.guild.id}/{payout['channel']}/{payout['winner_message_id']}",
                    emoji="<:tgk_link:1105189183523401828>",
                )
            )

            keyward = {
                "embed": embed,
                "view": link_view,
                "content": None,
                "ephemeral": True,
            }

            if mode.value == "ios":
                keyward["content"] = cmd
                keyward["embed"].clear_fields()
            await interaction.followup.send(**keyward)

            try:
                payout_message: discord.Message = await self.bot.wait_for(
                    "message", check=check, timeout=60
                )
                if payout_message.author.id == interaction.user.id:
                    match payout_message.content.lower():
                        case "skip":
                            await interaction.followup.send(
                                "Skipping this payout", ephemeral=True
                            )
                            await payout_message.delete()
                            await asyncio.sleep(0.5)
                            continue

                        case "reject":
                            await interaction.followup.send(
                                "Rejecting this payout", ephemeral=True
                            )
                            reject = await self.backend.reject_payout(
                                interaction.user, payout
                            )
                            if reject is True:
                                await payout_message.delete()
                                await asyncio.sleep(0.5)
                                continue
                            elif isinstance(reject, tuple):
                                await interaction.followup.send(
                                    f"Failed to reject this payout due to {reject[1]}",
                                    ephemeral=True,
                                )
                                await asyncio.sleep(0.5)
                                break
                            elif reject is False:
                                await interaction.followup.send(
                                    "Failed to reject this payout due to unknown error",
                                    ephemeral=True,
                                )
                                await asyncio.sleep(0.5)
                                break
                        case "exit":
                            await interaction.followup.send(
                                "Stopped the payout queue", ephemeral=True
                            )
                            guild_config["express"] = False
                            await self.backend.update_config(guild_config)
                            await payout_message.delete()
                            await asyncio.sleep(0.5)
                            return

                view = discord.ui.View()
                view.add_item(
                    discord.ui.Button(
                        label="Paid at",
                        style=discord.ButtonStyle.url,
                        url=payout_message.jump_url,
                        emoji="<:tgk_link:1105189183523401828>",
                    )
                )
                embed = winner_message.embeds[0]
                embed.title = "Payout Paid"

                await payout_message.add_reaction("<:tgk_active:1082676793342951475>")
                try:
                    await queue_webhook.edit_message(
                        winner_message.id, embed=embed, view=view
                    )
                except Exception:
                    await interaction.followup.send(
                        "Failed to edit the message due webhooks are changed, there no need to worry about this as payout has been registered as paid",
                        ephemeral=True,
                    )
                    await winner_message.add_reaction(self.backend.paid_emoji)

                self.bot.dispatch("more_pending", payout)

                if not payout["item"]:
                    interaction.client.dispatch(
                        "payout_paid",
                        payout_message,
                        interaction.user,
                        interaction.guild.get_member(payout["winner"]),
                        payout["prize"],
                    )
                else:
                    interaction.client.dispatch(
                        "payout_paid",
                        payout_message,
                        interaction.user,
                        interaction.guild.get_member(payout["winner"]),
                        f"{payout['prize']}x{payout['item']}",
                    )

                await self.backend.claimed.delete(payout["_id"])

                continue

            except asyncio.TimeoutError:
                guild_config["express"] = False
                await self.backend.update_config(guild_config)
                self.backend.config_cache[interaction.guild.id]["express"] = False
                await interaction.followup.send(
                    "Timed out you can try command again", ephemeral=True
                )

                return

        guild_config["express"] = False
        await self.backend.update_config(guild_config)
        self.backend.config_cache[interaction.guild.id]["express"] = False
        await interaction.followup.send("All payouts have been paid", ephemeral=True)

    @express_payout.error
    async def express_payout_error(self, interaction: discord.Interaction, error):
        config = await self.backend.get_config(interaction.guild_id)
        if config is None:
            return
        config["express"] = False
        await self.backend.update_config(config)

    @commands.Cog.listener()
    async def on_payout_queue(
        self,
        host: discord.Member,
        event: str,
        win_message: discord.Message,
        queue_message: discord.Message,
        winner: discord.Member,
        prize: str,
        item: str = None,
    ):
        embed = discord.Embed(
            title="Payout | Queued",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(),
            description="",
        )
        embed.description += f"**Host:** {host.mention}\n"
        embed.description += f"**Event:** {event}\n"
        embed.description += f"**Winner:** {winner.mention} ({winner.name})\n"
        if not item:
            embed.description += f"**Prize:** {prize:,}\n"
        else:
            embed.description += f"**Prize:** {prize}x {item}\n"
        embed.description += (
            f"**Event Message:** [Jump to Message]({win_message.jump_url})\n"
        )
        embed.description += (
            f"**Queue Message:** [Jump to Message]({queue_message.jump_url})\n"
        )
        embed.set_footer(text=f"Queue Message ID: {queue_message.id}")

        config = await self.backend.get_config(queue_message.guild.id)
        if config is None:
            return
        log_channel = queue_message.guild.get_channel(config["log_channel"])
        if log_channel is None:
            return
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_payout_claim(self, message: discord.Message, user: discord.Member):
        embed = discord.Embed(
            title="Payout | Claimed",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(),
            description="",
        )
        embed.description += f"**User:** {user.mention}\n"
        embed.description += (
            f"**Queue Message:** [Jump to Message]({message.jump_url})\n"
        )
        embed.set_footer(text=f"Queue Message ID: {message.id}")

        config = await self.backend.get_config(message.guild.id)
        if config is None:
            return
        log_channel = message.guild.get_channel(config["log_channel"])
        if log_channel is None:
            return
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_payout_pending(self, message: discord.Message):
        embed = discord.Embed(
            title="Payout | Pending",
            color=discord.Color.yellow(),
            timestamp=datetime.datetime.now(),
            description="",
        )
        embed.description += (
            f"**Queue Message:** [Jump to Message]({message.jump_url})\n"
        )
        embed.set_footer(text=f"Queue Message ID: {message.id}")

        config = await self.backend.get_config(message.guild.id)
        if config is None:
            return
        log_channel = message.guild.get_channel(config["log_channel"])
        if log_channel is None:
            return
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_payout_paid(
        self,
        message: discord.Message,
        user: discord.Member,
        winner: discord.Member,
        prize: str,
    ):
        embed = discord.Embed(
            title="Payout | Paid",
            color=discord.Color.dark_green(),
            timestamp=datetime.datetime.now(),
            description="",
        )
        embed.description += f"**User:** {user.mention}\n"
        embed.description += f"**Winner:** {winner.mention} ({winner.name})\n"
        embed.description += f"**Prize:** {prize}\n"
        embed.description += (
            f"**Queue Message:** [Jump to Message]({message.jump_url})\n"
        )
        embed.set_footer(text=f"Queue Message ID: {message.id}")

        config = await self.backend.get_config(message.guild.id)
        if config is None:
            return
        log_channel = message.guild.get_channel(config["log_channel"])
        if log_channel is None:
            return
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_payout_expired(self, message: discord.Message, user: discord.Member):
        embed = discord.Embed(
            title="Payout | Expired",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now(),
            description="",
        )
        embed.description += f"**User:** {user.mention}\n"
        embed.description += (
            f"**Queue Message:** [Jump to Message]({message.jump_url})\n"
        )
        embed.set_footer(text=f"Queue Message ID: {message.id}")

        config = await self.backend.get_config(message.guild.id)
        if config is None:
            return
        log_channel = message.guild.get_channel(config["log_channel"])
        if log_channel is None:
            return
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_more_pending(self, info: dict):
        data = await self.backend.unclaimed.find_many_by_custom(
            {"winner_message_id": info["winner_message_id"]}
        )
        if len(data) <= 0:
            winner_channel = self.bot.get_channel(info["channel"])
            try:
                winner_message = await winner_channel.fetch_message(
                    info["winner_message_id"]
                )
                await winner_message.remove_reaction(
                    self.backend.pending_emoji, self.bot.user
                )
                await winner_message.add_reaction(self.backend.paid_emoji)
            except Exception:
                pass
        else:
            return


async def setup(bot):
    await bot.add_cog(PayoutV2(bot))
    for guild in await bot.payouts.config.find_many_by_custom({"express": True}):
        if guild["express"] is True:
            guild["express"] = False
            await bot.payouts.config.update_config(guild)
    for item in await bot.dankItems.get_all():
        bot.dank_items_cache[item["_id"]] = item
    await bot.payouts.setup()


async def teardown(bot):
    for guild in await bot.payouts.config.find_many_by_custom({"express": True}):
        if guild["express"] is True:
            guild["express"] = False
            await bot.payouts.update_config(guild)
    await bot.remove_cog(PayoutV2(bot))
