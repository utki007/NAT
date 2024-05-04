import discord
import datetime
from discord.ext import commands, tasks
from discord import app_commands, Interaction

import random
from typing import List, Dict

from .db import Giveaways_Backend, GiveawayConfig, GiveawayData
from .views import Giveaway 
from utils.transformers import TimeConverter, MutipleRole
from utils.convertor import DMCConverter_Ctx

class Giveaways(commands.GroupCog, name="giveaways"):
    def __init__(self, bot):
        self.backend = Giveaways_Backend(bot)
        self.bot.giveaway = self.backend #type: ignore

    async def item_autocomplete(self, interaction: discord.Interaction, string: str) -> List[app_commands.Choice[str]]:
        choices = []
        for item in self.bot.dank_items_cache.keys():
            if string.lower() in item.lower():
                choices.append(app_commands.Choice(name=item, value=item))
        if len(choices) == 0:
            return [
                app_commands.Choice(name=item, value=item)
                for item in self.bot.dank_items_cache.keys() #type: ignore
            ]
        else:
            return choices[:24]
        
    @tasks.loop(minutes=3)
    async def giveaway_loop(self):
        if self.giveaway_task_progress == True:
            return
        self.giveaway_task_progress = True
        now = datetime.datetime.utcnow()
        giveaways: Dict[int, GiveawayData] = self.backend.giveaways.get_all()
        for giveaway in giveaways.values():
            try:
                if giveaway["end_time"] <= now:
                    if giveaway["_id"] in self.giveaway_in_prosses:
                        continue
                    if giveaway["ended"] == True:
                        if giveaway['delete_at'] and giveaway['delete_at'] <= now:
                            await self.backend.giveaways.delete(giveaway)

                    self.bot.dispatch("giveaway_end", giveaway)
                    self.giveaway_in_prosses.append(giveaway["_id"])
                    del self.backend.giveaways_cache[giveaway["_id"]]
            except:
                pass
            self.giveaway_task_progress = False

    @giveaway_loop.before_loop
    async def before_giveaway_loop(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_giveaway_end(self, giveaway: GiveawayData):
        guild: discord.Guild = self.bot.get_guild(giveaway['guild'])
        channel: discord.TextChannel = guild.get_channel(giveaway['channel'])
        host: discord.Member = guild.get_member(giveaway['host'])
        if giveaway['ended'] == True: return

        try:
            message: discord.Message = await channel.fetch_message(giveaway['_id'])
        except discord.NotFound:
            try:
                await self.backend.giveaways.delete(giveaway['_id'])
                del self.backend.giveaways_cache[giveaway['_id']]
                self.giveaway_in_prosses.remove(giveaway['_id'])
            except:pass

        if len(giveaway['entries'].keys()) == 0 or len(giveaway['entries']) < giveaway['winners']:
            view = Giveaway()
            view.children[0].disabled = True
            await message.edit(view=view, content="**Giveaway Ended**")
            await message.reply(embed=discord.Embed(description="No one entered the giveaway or there were not enough entries to pick a winner", color=self.bot.default_color))
            await self.backend.giveaways.delete(giveaway['_id'])
            try:
                self.giveaway_in_prosses.remove(giveaway['_id'])
            except:
                pass
            try:
                del self.backend.giveaways_cache[giveaway['_id']]
            except:
                pass
            log_data = {
                "guild": guild,
                "channel": channel,
                "message": message,
                "prize": giveaway['prize'],
                "winners": [],
                "winner": [],
                "host": host,
                "item": giveaway['item'] if giveaway['dank'] else None,
                "participants": len(giveaway['entries'].keys()),
            }
            self.bot.dispatch("giveaway_end_log", log_data)
            return
        
        entries: List[int] = []
        for key, value in giveaway['entries'].items():
            if int(key) in entries: continue
            entries.extend([int(key)]*value)


        winners: List[discord.Member] = []
        while len(winners) != giveaway['winners']:
            winner = random.choice(entries)
            member = guild.get_member(winner)
            if member is None: continue
            if member in winners: continue
            winners.append(member)
            if len(winners) == giveaway['winners']: break

        embed: discord.Embed = message.embeds[0]
        if len(embed.fields) != 0:
            fields_name = [field.name for field in embed.fields]
            if "Winners" in fields_name:
                embed.set_field_at(fields_name.index("Winners"), name="Winners", value=",".join([winner.mention for winner in winners]), inline=False)
            else:
                embed.description += f"\n**Total Participants:** {len(giveaway['entries'].keys())}"
                embed.add_field(name="Winners", value=",".join([winner.mention for winner in winners]), inline=False)
        else:
            embed.description += f"\n**Total Participants:** {len(giveaway['entries'].keys())}"
            embed.add_field(name="Winners", value=",".join([winner.mention for winner in winners]), inline=False)

        view = Giveaway()
        view.children[0].disabled = True
        await message.edit(view=view, content="**Giveaway Ended**", embed=embed)

        win_embed = discord.Embed(title="Congratulations", color=self.bot.default_color, description="")
        dm_embed = discord.Embed(title="You won a giveaway!", description=f"**Congratulations!** you won", color=self.bot.default_color)
        host_embed = discord.Embed(title=f"Your Giveaway ", description="", color=self.bot.default_color)

        if giveaway['dank']:
            if giveaway['item']:
                item = await self.bot.dank_items.find(giveaway['item'])
                win_embed.description += f"<a:tgk_blackCrown:1097514279973961770> **Won:** {giveaway['prize']}x {giveaway['item']}\n"
                dm_embed.description += f" {giveaway['prize']}x {giveaway['item']} in {guild.name}"
                host_embed.title += f"{giveaway['prize']}x {giveaway['item']} has ended"
            else:
                item = None
                win_embed.description += f"<a:tgk_blackCrown:1097514279973961770> **Won:** ⏣ {giveaway['prize']:,}\n"
                dm_embed.description += f" ⏣ {giveaway['prize']:,} in {guild.name}"
                host_embed.title += f"⏣ {giveaway['prize']:,} has ended"

        else:
            win_embed.description += f"<a:tgk_blackCrown:1097514279973961770> **Won:** {giveaway['prize']}\n"
            dm_embed.description += f" {giveaway['prize']} in {guild.name}"
            host_embed.title += f"{giveaway['prize']} has ended"


        win_message = await message.reply(embed=win_embed, content=",".join([winner.mention for winner in winners]))
        link_view = discord.ui.View()
        link_view.add_item(discord.ui.Button(label="Jump", url=message.jump_url, style=discord.ButtonStyle.link))
        payout_config = await self.bot.payouts.get_config(guild.id)
        for winner in winners:
            try:
                await winner.send(embed=dm_embed, view=link_view)
            except:
                pass
            if giveaway['dank'] and payout_config is not None:
                try:await self.bot.payouts.create_payout(config=payout_config,
                                                         event="giveaway", winner=winner, host=host, prize=giveaway['prize'], message=message, item=item)
                except:pass


        host_embed.description += f"**Ended at:** <t:{int(datetime.datetime.now().timestamp())}:R>\n"
        host_embed.description += f"**Total Entries:** {len(giveaway['entries'].keys())}\n"
        host_embed.description += f"**Winners:** \n"

        for winner in winners: host_embed.description += f"> {winners.index(winner)+1}. {winner.mention}\n"
        try:
            await host.send(embed=host_embed, view=link_view)
        except:
            pass

        giveaway['ended'] = True
        giveaway['delete_at'] = datetime.datetime.utcnow() + datetime.timedelta(days=7)
        await self.backend.update_giveaway(message, giveaway)
        try:
            self.giveaway_in_prosses.remove(giveaway['_id']); 
        except ValueError:
            pass
        log_data = {
            "guild": guild,
            "channel": channel,
            "message": message,
            "prize": giveaway['prize'],
            "winners": winners,
            "winner": giveaway['winners'],
            "host": host,
            "item": giveaway['item'] if giveaway['dank'] else None,
            "participants": len(giveaway['entries'].keys()),

        }
        self.bot.dispatch("giveaway_end_log", log_data)
        
    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(Giveaway())

    @app_commands.command(name="start", description="Start a giveaway")
    @app_commands.describe(winners="Number of winners", prize="Prize of the giveaway", item="Item to giveaway", duration="Duration of the giveaway",
        req_roles="Roles required to enter the giveaway", bypass_role="Roles that can bypass the giveaway", req_level="Level required to enter the giveaway",
        req_weekly="Weekly XP required to enter the giveaway", donor="Donor of the giveaway", message="Message to accompany the giveaway", dank="Dank Memer Giveaway? (Set it to True for Auto Payout Queue)",
        channel_message="Number of Messages required in specific channel to enter the giveaway")
    async def _start(self, interaction: discord.Interaction, winners: app_commands.Range[int, 1, 20], prize: str,
                     duration: app_commands.Transform[int, TimeConverter],
                     dank: bool=True,
                     item:str=None,
                     req_roles: app_commands.Transform[discord.Role, MutipleRole]=None, 
                     bypass_role: app_commands.Transform[discord.Role, MutipleRole]=None, 
                     req_level: app_commands.Range[int, 1, 100]=None,
                     req_weekly: app_commands.Range[int, 1, 100]=None,
                     channel_message: str=None,
                     donor: discord.Member=None,
                     message: app_commands.Range[str, 1, 250]=None,
    ):
        
        await interaction.response.defer(ephemeral=True)
        config = await self.backend.get_config(interaction.guild)
        if config['enabled'] is False:
            return await interaction.followup.send("Giveaways are disabled in this server!")
        user_role = [role.id for role in interaction.user.roles]
        if not set(user_role) & set(config['manager_roles']): return await interaction.followup.send("You do not have permission to start giveaways!")
        if dank == True:
            prize = await DMCConverter_Ctx().convert(interaction, prize)
            if not isinstance(prize, int):
                return await interaction.followup.send("Prize you entered is not a valid number! If you are not hosting a Dank Memer Giveaway, set dank to False")
        if item is not None:
            if item not in self.bot.dank_items_cache.keys():
                return await interaction.followup.send("Item you entered is not a valid item!")
            
        data: GiveawayData = {
            "channel": interaction.channel.id,
            "guild": interaction.guild.id,
            "winners": winners,
            "prize": prize,
            "item": item,
            "duration": duration,
            "req_roles": req_roles,
            "bypass_role": bypass_role,
            "req_level": req_level,
            "req_weekly": req_weekly,
            "entries": {},
            "start_time": datetime.datetime.utcnow(),
            "end_time": datetime.datetime.utcnow() + datetime.timedelta(seconds=duration),
            "ended": False,
            "host": interaction.user.id,
            "donor": donor.id if donor else None,
            "message": message,
            "channel_messages": {},
            "dank": dank,
            "delete_at": None
        }
        embed = discord.Embed(color=interaction.client.default_color, description="")
        
        if dank:
            if item:
                embed.description += f"## {prize}x {item}\n"
            else:
                try:
                    embed.description += f"## ⏣ {prize:,}\n"
                except:
                    embed.description += f"## ⏣ {prize}\n"
        else:
            embed.description += f"## Prize: {prize}\n"

        embed.description += "‎\n"
        timnestamp = int((datetime.datetime.now() + datetime.timedelta(seconds=duration)).timestamp())
        embed.description += f"**End Time:** <t:{timnestamp}:R> (<t:{timnestamp}:T>)\n"
        embed.description += f"**Winners:** {winners}\n"
        embed.description += f"**Host:** {interaction.user.mention}\n"

        if donor:
            embed.description += f"**Donor:** {donor.mention}"
        if req_roles:
            value = ""
            if len(req_roles) == 2:
                value = f"{req_roles[0].mention} and {req_roles[1].mention}"
            else:
                value = ", ".join([role.mention for role in req_roles])
            embed.add_field(name="Required Roles", value=value, inline=True)
        if bypass_role:
            value = ""
            if len(bypass_role) == 2:
                value = f"{bypass_role[0].mention} and {bypass_role[1].mention}"
            else:
                value = ", ".join([role.mention for role in bypass_role])
            embed.add_field(name="Bypass Roles", value=value, inline=False)
        if req_level:
            embed.add_field(name="Required Level", value=str(req_level), inline=True)
        if req_weekly:
            embed.add_field(name="Required Weekly XP", value=str(req_weekly), inline=False)


        if channel_message:
            channel_message = channel_message.split(" ")
            if len(channel_message) > 2: return await interaction.followup.send(f"Wrong format for channel message!\nFormat: [Channel] [number of messages] {interaction.channel.mention} 10")
            msg_count = int(channel_message[1])
            msg_channel = interaction.guild.get_channel(int(channel_message[0][2:-1]))
            if not msg_channel: return await interaction.followup.send("Provide a valid channel for channel message!")
            embed.add_field(name="Required Messages", value=f"{msg_channel.mention}: {msg_count}", inline=False)
            data["channel_messages"]["channel"] = msg_channel.id
            data["channel_messages"]["count"] = msg_count
            data["channel_messages"]["users"] = {}

        embed.timestamp = datetime.datetime.now() + datetime.timedelta(seconds=duration)
        embed.set_footer(text=f"{winners} winner{'s' if winners > 1 else ''} | Ends at")

        await interaction.followup.send(content="Giveaway Created!")

        gaw_message = await interaction.channel.send(embed=embed, view=Giveaway(), content="<a:tgk_tadaa:806631994770849843> **GIVEAWAY STARTED** <a:tgk_tadaa:806631994770849843>")
        if message:
            host_webhook = None
            for webhook in await interaction.channel.webhooks():
                if webhook.user.id == self.bot.user.id:
                    host_webhook = webhook
                    break

            if not host_webhook:
                pfp = await self.bot.user.avatar.read()
                host_webhook = await interaction.channel.create_webhook(name="Giveaway Host", avatar=pfp)

            author = donor if donor else interaction.user
            await host_webhook.send(content=message, username=author.global_name, avatar_url=author.avatar.url if author.avatar else author.default_avatar, allowed_mentions=discord.AllowedMentions.none())

        data['_id'] = gaw_message.id
        await self.backend.giveaways.insert(data)
        self.backend.giveaways_cache[gaw_message.id] = data
        self.bot.dispatch("giveaway_host", data)


    @app_commands.command(name="reroll", description="Reroll a giveaway Note: Reroll will not Auto Payout Queue Giveaways")
    @app_commands.describe(
        message="Message to accompany the reroll",
        winners="Numbers of winners to reroll"
    )
    @app_commands.rename(message="message_id")
    async def _reroll(self, interaction: discord.Interaction, message: str, winners: app_commands.Range[int, 1, 10]=1):
        config = await self.backend.get_config(interaction.guild)
        if not config:
            return await interaction.followup.send("Giveaways are not enabled in this server!", ephemeral=True)

        user_role = [role.id for role in interaction.user.roles]
        if not set(user_role) & set(config['manager_roles']): return await interaction.response.send_message("You do not have permission to start giveaways!", ephemeral=True)

        try:
            message = await interaction.channel.fetch_message(int(message))
        except:
            return await interaction.response.send_message("Invalid message ID!", ephemeral=True)
        
        giveawa_data = await self.backend.get_giveaway(message)
        if not giveawa_data: return await interaction.response.send_message("This message is not a giveaway!", ephemeral=True)
        if not giveawa_data['ended']: return await interaction.response.send_message("This giveaway has not ended!", ephemeral=True)
        giveawa_data['winners'] = winners
        self.bot.dispatch("giveaway_end", giveawa_data)
        await interaction.response.send_message("Giveaway rerolled successfully! Make sure to cancel the already queued payouts use `/payout search`", ephemeral=True)
        chl = interaction.client.get_channel(1130057933468745849)
        await chl.send(f"Rerolled giveaway by {interaction.user.mention} in {interaction.guild.name} for {winners} winners {message.jump_url}")    


    @app_commands.command(name="end", description="End a giveaway")
    @app_commands.describe(
        message="Message to accompany the end"
    )
    @app_commands.rename(message="message_id")
    async def _end(self, interaction: discord.Interaction, message: str):
        try:
            message = await interaction.channel.fetch_message(int(message))
        except:
            return await interaction.response.send_message("Invalid message ID!", ephemeral=True)
        giveaway_data = await self.backend.get_giveaway(message)
        if not giveaway_data: return await interaction.response.send_message("This message is not a giveaway!", ephemeral=True)
        if giveaway_data['ended']: return await interaction.response.send_message("This giveaway has already ended!", ephemeral=True)
        self.bot.dispatch("giveaway_end", giveaway_data)
        await interaction.response.send_message("Giveaway ended successfully!", ephemeral=True)
        try:
            self.bot.giveaway.giveaways_cache.pop(message.id)
        except Exception as e:
            raise e
        
    @commands.command(name="multiplier", description="Set the giveaway multiplier", aliases=['multi'])
    async def _multiplier(self, ctx, user: discord.Member=None):
        user = user if user else ctx.author
        config = await self.backend.get_config(ctx.guild)
        if not config: return await ctx.send("This server is not set up!")
        if len(config['multipliers'].keys()) == 0: return await ctx.send("This server does not have any multipliers!")
        user_role = [role.id for role in user.roles]
        embed = discord.Embed(color=self.bot.default_color, description=f"@everyone - `1x`\n")
        embed.set_author(name=f"{user}'s Multipliers", icon_url=user.avatar.url if user.avatar else user.default_avatar)
        total = 1
        for role, multi in config['multipliers'].items():
            if int(role) in user_role:
                embed.description += f"<@&{role}> - `{multi}x`\n"
                total += multi
        embed.description += f"**Total Multiplier** - `{total}x`"
        await ctx.reply(embed=embed, allowed_mentions=discord.AllowedMentions.none())


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot: return
        if message.guild is None: return
        user: discord.Member = message.author
        giveaways = await self.backend.get_message_giveaways(message)
        if len(giveaways) == 0: return
        for giveaway in giveaways:
            if user.id in giveaway['entries'].keys(): continue
            if giveaway['ended']: continue
            if giveaway['channel_messages']:
                if message.channel.id != giveaway['channel_messages']['channel']: continue
                if str(user.id) not in giveaway['channel_messages']['users'].keys():
                    giveaway['channel_messages']['users'][str(user.id)] = {
                        "count": 1,
                        "last_message": datetime.datetime.utcnow()
                    }
                    await self.backend.giveaways.update(giveaway)
                    self.backend.giveaways_cache[giveaway['_id']] = giveaway
                else:
                    try:
                        time_diff = (datetime.datetime.utcnow() - giveaway['channel_messages']['users'][str(user.id)]['last_message']).total_seconds()
                    except TypeError:
                        time_diff = 10
                    if time_diff < 8:
                        continue
                    else:
                        if giveaway['channel_messages']['users'][str(user.id)]['count'] >= giveaway['channel_messages']['count']:
                            continue
                        giveaway['channel_messages']['users'][str(user.id)]['count'] += 1
                        giveaway['channel_messages']['users'][str(user.id)]['last_message'] = datetime.datetime.utcnow()
                        await self.backend.giveaways.update(giveaway)
                        self.backend.giveaways_cache[giveaway['_id']] = giveaway


    @commands.Cog.listener()
    async def on_giveaway_end_log(self, giveaway_data: dict):
        config = await self.backend.get_config(giveaway_data['guild'])
        if not config: return
        if not config['log_channel']: return
        chl = self.bot.get_channel(config['log_channel'])
        if not chl: return

        embed = discord.Embed(color=self.bot.default_color,description="", title="Giveaway Ended", timestamp=datetime.datetime.now())
        embed.add_field(name="Host", value=giveaway_data['host'].mention)
        embed.add_field(name="Channel", value=giveaway_data['channel'].mention)
        embed.add_field(name="Number of Winners", value=giveaway_data['winner'])
        embed.add_field(name="Winners", value="\n".join([winner.mention for winner in giveaway_data['winners']] if giveaway_data['winners'] else ["`None`"]))
        if giveaway_data['item']:
            embed.add_field(name="Item", value=giveaway_data['item'])
        if giveaway_data['prize']:
            embed.add_field(name="Prize", value=giveaway_data['prize'])
        embed.add_field(name="Participants", value=giveaway_data['participants'])
        embed.add_field(name="Message", value=f"[Click Here]({giveaway_data['message'].jump_url})")
        embed.add_field(name="Total Participants", value=giveaway_data['participants'])
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Jump", style=discord.ButtonStyle.link, url=giveaway_data['message'].jump_url))
        await chl.send(embed=embed, view=view)
    
    @commands.Cog.listener()
    async def on_giveaway_host(self, data: dict):
        config = await self.backend.get_config(self.bot.get_guild(data['guild']))
        if not config: return
        if not config['log_channel']: return
        chl = self.bot.get_channel(config['log_channel'])
        if not chl: return

        embed = discord.Embed(color=self.bot.default_color,description="", title="Giveaway Hosted", timestamp=datetime.datetime.now())
        embed.add_field(name="Host", value=f"<@{data['host']}>")
        embed.add_field(name="Channel", value=f"<#{data['channel']}>")
        
        embed.add_field(name="Winners", value=data['winners'])
        if data['dank'] == True:
            if data['item']:
                embed.add_field(name="Prize", value=f"{data['prize']}x {data['item']}")
            else:
                embed.add_field(name="Prize", value=f"{data['prize']:,}")
        else:
            embed.add_field(name="Prize", value=f"{data['prize']}")
        embed.add_field(name="Link", value=f"[Click Here](https://discord.com/channels/{data['guild']}/{data['channel']}/{data['_id']})")
        embed.add_field(name="Ends At", value=data['end_time'].strftime("%d/%m/%Y %H:%M:%S"))
        await chl.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Giveaways(bot))




