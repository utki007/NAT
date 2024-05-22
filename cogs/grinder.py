import asyncio
import datetime
import traceback
from typing import Literal
import discord
from discord import Interaction, app_commands
from discord.ext import commands, tasks
from humanfriendly import format_timespan

from utils.dank import get_donation_from_message
from utils.embeds import get_error_embed, get_invisible_embed, get_warning_embed
from utils.transformers import DMCConverter
from ui.settings.grinder import GrinderSummeris

utc = datetime.timezone.utc
midnight = datetime.time(tzinfo=utc)
times = [datetime.time(hour = hour,tzinfo=utc) for hour in range(24)]

@app_commands.guild_only()
class grinder(commands.GroupCog, name="grinder", description="Manage server grinders"):

    def __init__(self, bot):
        self.bot = bot
        self.grinder_reminder.start()
        self.grinder_demotions.start()
    
    def cog_unload(self):
        self.grinder_reminder.cancel()
        self.grinder_demotions.cancel()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        
        if not message.guild or message.author.id != 270904126974590976:
            return
        if len(message.embeds) <= 0: 
            return
        
        guild_config = await self.bot.grinderSettings.find(message.guild.id)
        if guild_config is None:
            return
        if not guild_config['payment_channel']: 
            return
        if message.channel.id != guild_config['payment_channel']:
            return
        embed = message.embeds[0]

        if embed.description != "Successfully donated!": 
            return

        try: 
            message = await message.channel.fetch_message(message.reference.message_id)
        except discord.NotFound: 
            return
        
        
        donation_info = await get_donation_from_message(message)

        if donation_info.items is not None:
            return await message.channel.send(embed = await get_error_embed(f"Donating items is not allowed in this channel. Please reach out to the manager for further assistance."))
        
        amount = donation_info.quantity
        donor = donation_info.donor
        donor = message.guild.get_member(int(donor.id))

        grinder_profile = await self.bot.grinderUsers.find({"guild": message.guild.id, "user": donor.id})
        if not grinder_profile:
            return await message.channel.send(embed = await get_error_embed(f"{donor.mention} is not appointed as grinder"))
        if not grinder_profile['active']:
            return await message.channel.send(embed = await get_error_embed(f"{donor.mention} is either demoted or on a break. Contact support to join grinders again!"))
        
        days_paid = int((amount+grinder_profile['payment']['extra']) / grinder_profile['payment']['amount_per_grind'])
        amount_paid = days_paid * grinder_profile['payment']['amount_per_grind']
        extra_amount = int((amount+grinder_profile['payment']['extra']) - amount_paid)

        grinder_profile['payment']['total'] += amount_paid
        if extra_amount>=0:
            grinder_profile['payment']['extra'] = extra_amount
        grinder_profile['payment']['next_payment'] = grinder_profile['payment']['next_payment'] + datetime.timedelta(days=days_paid)
        await self.bot.grinderUsers.upsert(grinder_profile)

        role_changed = False
        user = message.guild.get_member(grinder_profile['user'])
        trial_role = message.guild.get_role(guild_config['trial']['role'])
        if trial_role is not None and trial_role in user.roles:
            date = datetime.date.today()
            today = datetime.datetime(date.year, date.month, date.day)
            if grinder_profile['payment']['next_payment'] > today and (grinder_profile['payment']['next_payment'] - grinder_profile['payment']['first_payment']).days >= int(guild_config['trial']['duration'])/(3600*24):
                if trial_role in user.roles:
                    try:
                        await user.remove_roles(trial_role)
                    except:
                        pass
                    grinder_role = message.guild.get_role(guild_config['grinder']['role'])
                    if grinder_role is not None and grinder_role not in user.roles:
                        try:
                            await user.add_roles(grinder_role)
                            role_changed = True
                        except:
                            pass
                    profile_role = message.guild.get_role(grinder_profile['profile_role'])
                    if profile_role is not None and profile_role not in user.roles:
                        try:
                            await user.add_roles(profile_role)
                        except:
                            pass

        embed = await get_invisible_embed(f"⏣ {amount:,} has been added to {donor.mention}")
        embed.title = f"{donor.display_name}'s Grinder Payment"
        embed.description = None
        embed.add_field(name="Profile:", value=f"{grinder_profile['profile']}", inline=True)
        embed.add_field(name="Paid for:", value=f"{days_paid} {'day' if days_paid==1 else 'days'}", inline=True)
        embed.add_field(name="Sanctioned By:", value=f"Automatic Detection", inline=True)
        embed.add_field(name="Amount Credited:", value=f"⏣ {amount:,}", inline=True)
        if extra_amount > 0:
            embed.add_field(name="Grinder Wallet:", value=f"⏣ {extra_amount:,}", inline=True)
        embed.add_field(name="Grinder Bank:", value=f"⏣ {grinder_profile['payment']['total']:,}", inline=True)
        embed.timestamp = datetime.datetime.now()
        try:
            embed.set_footer(text=f"{message.guild.name}", icon_url=message.guild.icon.url)
        except:
            embed.set_footer(text=f"{message.guild.name}")
        try:
            embed.set_thumbnail(url=donor.avatar.url)
        except:
            embed.set_thumbnail(url=donor.default_avatar.url)
        embeds = [embed]
        if role_changed:
            embeds.append(await get_invisible_embed(f"{donor.mention} has been promoted to {grinder_role.mention}"))
        msg = None
        try:
            msg = await message.channel.send(embeds=embeds)
            await donor.send(embed=embed)
        except:
            pass

        if msg is None:
            return
        log_channel = message.guild.get_channel(guild_config['grinder_logs'])
        if log_channel:
            log_embed = await get_invisible_embed(f"⏣ {amount:,} has been added to {donor.mention}")
            log_embed.title = f"Amount Added"
            log_embed.description = None
            log_embed.add_field(name="Paid for:", value=f"{days_paid} {'day' if days_paid==1 else 'days'}", inline=True)
            log_embed.add_field(name="Amount Credited:", value=f"⏣ {amount:,}", inline=True)
            log_embed.add_field(name="Credited To:", value=f"{donor.mention}", inline=True)
            log_embed.timestamp = datetime.datetime.now()
            try:
                log_embed.set_thumbnail(url=donor.avatar.url)
            except:
                log_embed.set_thumbnail(url=donor.default_avatar.url)
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Jump to message", style=discord.ButtonStyle.link, url=msg.jump_url))
            try:
                await log_channel.send(embed=log_embed, view=view)
            except:
                pass

    @staticmethod
    async def GrinderCheck(interaction: Interaction):
        
        if interaction.user.id in interaction.client.owner_ids:
            return True

        guild: discord.Guild = interaction.guild
        user_roles = [role.id for role in interaction.user.roles]
        config = await interaction.client.grinderSettings.find(guild.id)
        if not config:
            await interaction.response.send_message("Grinder system is not setup in this server", ephemeral=True)
            return False
        if (set(config['manager_roles']) & set(user_roles)):
            return True
        await interaction.response.send_message("You don't have permission to use this command", ephemeral=True)
        return False
    
    async def GrinderProfileAutoComplete(self, interaction: Interaction, current: str) -> discord.app_commands.Choice[str]:
        guild: discord.Guild = interaction.guild
        config = await interaction.client.grinderSettings.find(guild.id)
        choices = [
            discord.app_commands.Choice(name=f"{value['name']} - ⏣ {value['payment']:,}", value=key)
            for key, value in config['grinder_profiles'].items() if current.lower() in value['name'].lower()
        ]
        return choices[:24] if len(choices) > 0 else [app_commands.Choice(name="No profile found", value="None")]

    @tasks.loop(time=times)
    async def grinder_reminder(self):
        
        guild_configs = await self.bot.grinderSettings.get_all()

        date = datetime.date.today()
        today = datetime.datetime(date.year, date.month, date.day)
        time = datetime.datetime.now(utc)
        time = datetime.time(hour=time.hour, tzinfo=utc)

        for guild_config in guild_configs:
            guild = self.bot.get_guild(guild_config['_id'])
            if guild is None:
                continue
            grinder_channel = guild.get_channel(guild_config['payment_channel'])
            if grinder_channel is None:
                continue
            if not guild:
                continue
            grinder_users = await self.bot.grinderUsers.get_all({"guild": guild.id, "reminder_time": str(time) })
            for grinder_user in grinder_users:
                if not grinder_user['active']:
                    continue
                if today > grinder_user['payment']['next_payment']:
                    user = guild.get_member(grinder_user['user'])
                    if not user:
                        continue
                    pending_days = (today - grinder_user['payment']['next_payment']).days
                    amount = grinder_user['payment']['amount_per_grind'] * pending_days
                    embed = await get_invisible_embed(f"Hey {user.mention}, you have pending payment of ⏣ {amount:,} for {pending_days} days. Please grind soon.")
                    
                    embed.title = f"Grinder Reminder"
                    embed.description = None
                    embed.add_field(name="Pending For:", value = f"{pending_days} {'day' if pending_days==1 else 'days'}", inline=True)
                    embed.add_field(name="Amount:", value = f"⏣ {amount:,}", inline=True)
                    embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/951400609322512435.webp?size=128&quality=lossless")
                    embed.timestamp = datetime.datetime.now()
                    try:
                        embed.set_footer(text=f"{guild.name}", icon_url=guild.icon.url)
                    except:
                        embed.set_footer(text=f"{guild.name}")
                    try:
                        view = discord.ui.View()
                        view.add_item(discord.ui.Button(label="Grinder's Donation Channel", emoji="<:tgk_channel:1073908465405268029>" , style=discord.ButtonStyle.primary, url=f"{grinder_channel.jump_url}"))
                        await user.send(embed=embed, view=view)
                        await asyncio.sleep(0.1)
                    except:
                        pass

    @grinder_reminder.before_loop
    async def before_grinder_reminder(self):
        await self.bot.wait_until_ready()

    @grinder_reminder.error
    async def grinder_reminder_error(self, error):
        channel = self.bot.get_channel(999555462674522202)
        await channel.send(f"<@488614633670967307> <@301657045248114690> , Error in grinder reminders: {error}")
        full_stack_trace = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        await channel.send(f"<@488614633670967307> <@301657045248114690> , Error in grinder reminder: {full_stack_trace}")

    @tasks.loop(time=midnight)
    async def grinder_demotions(self):
        
        guild_configs = await self.bot.grinderSettings.get_all()
        date = datetime.date.today()
        today = datetime.datetime(date.year, date.month, date.day)
        for guild_config in guild_configs:
            
            guild = self.bot.get_guild(guild_config['_id'])
            if guild is None:
                continue
            log_channel = guild.get_channel(guild_config['grinder_logs'])
            demote_days = int(guild_config['grinder']['demotion_in']/(3600*24))
            grinder_users = await self.bot.grinderUsers.get_all({"guild": guild.id})
            for grinder_user in grinder_users:
                if not grinder_user['active']:
                    continue
                if today > grinder_user['payment']['next_payment']:
                    user = guild.get_member(grinder_user['user'])
                    if not user:
                        continue
                    days = (today - grinder_user['payment']['next_payment']).days
                    if days <= demote_days:
                        continue
                    embed = await get_invisible_embed(f"You have been dismissed from grinders. Thanks for your support!")
                    view = None
                    trial_role = guild.get_role(guild_config['trial']['role'])
                    grinder_role = guild.get_role(guild_config['grinder']['role'])
                    profile_role = guild.get_role(grinder_user['profile_role'])
                    if days > demote_days*2:
                        grinder_user['active'] = False
                        await self.bot.grinderUsers.upsert(grinder_user)
                        roles_to_remove = [trial_role, profile_role, grinder_role]
                        try:
                            await user.remove_roles(*roles_to_remove)
                        except:
                            pass
                        embed.title = f"Kicked from Grinders Team!"
                        embed.description = guild_config['dismiss_embed']['description']
                    elif days > demote_days:
                        roles_to_remove = [grinder_role]
                        try:
                            await user.remove_roles(*roles_to_remove)
                        except:
                            pass
                        roles_to_add = [trial_role]
                        try:
                            await user.add_roles(*roles_to_add)
                        except:
                            pass
                        embed.title = f"Demoted to Trial Grinder"
                        embed.description = f'You have been demoted to trial grinder. You have {format_timespan((demote_days*2 - days)*86400)} to grind else you will be dismissed from grinders. Thanks for your support!'
                        grind_channel = guild.get_channel(guild_config['payment_channel'])
                        if grind_channel:
                            view = discord.ui.View()
                            view.add_item(discord.ui.Button(label="Grinder's Donation Channel", emoji="<:tgk_channel:1073908465405268029>" , style=discord.ButtonStyle.primary, url=f"{grind_channel.jump_url}"))
                    
                    embed.timestamp = datetime.datetime.now()
                    try:
                        embed.set_footer(text = guild.name, icon_url = guild.icon.url)
                    except:
                        embed.set_footer(text = guild.name)
                    try:
                        embed.set_thumbnail(url = guild_config['dismiss_embed']['thumbnail'])
                    except:
                        pass
                    try:
                        if view != None:
                            await user.send(embed=embed, view=view)
                        else:
                            await user.send(embed=embed)
                    except:
                        pass
                    
                    if log_channel:
                        log_embed = await get_invisible_embed(f"{user.mention} has been dismissed from grinders. Thanks for your support!")
                        log_embed.title = embed.title
                        log_embed.description = None
                        log_embed.add_field(name="User:", value=f"{user.mention}", inline=True)
                        log_embed.add_field(name="Dismissed At:", value=f"<t:{int(embed.timestamp.timestamp())}>", inline=True)
                        log_embed.set_footer(text=f"Automatic Removal")
                        try:
                            await log_channel.send(embed=log_embed)
                        except:
                            pass
                    await asyncio.sleep(1)

    @grinder_demotions.before_loop
    async def before_grinder_demotions(self):
        await self.bot.wait_until_ready()

    @grinder_demotions.error
    async def grinder_demotions_error(self, error):
        channel = self.bot.get_channel(999555462674522202)
        await channel.send(f"<@488614633670967307> <@301657045248114690> , Error in grinder demotions: {error}")
        full_Stack_trace = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        await channel.send(f"<@488614633670967307> <@301657045248114690> , Error in grinder demotions: {full_Stack_trace}")

    @app_commands.command(name="appoint", description="Add New Grinder")
    @app_commands.autocomplete(profile=GrinderProfileAutoComplete)
    @app_commands.describe(profile="Add grinder to which tier?", user="User to appoint")
    @app_commands.check(GrinderCheck)
    async def appoint(self, interaction: Interaction, profile: str, user: discord.Member):
        
        if user.bot:
            return await interaction.response.send_message(embed= await get_error_embed("Bots can't be appointed as grinder"), ephemeral=True)

        if profile == "None":
            return await interaction.response.send_message(embed= await get_error_embed("No profile found"), ephemeral=True)
        
        guild_config = await interaction.client.grinderSettings.find(interaction.guild.id)
        if not guild_config:
            return await interaction.response.send_message(embed= await get_error_embed("Grinder system is not setup in this server"), ephemeral=True)
        await interaction.response.defer(ephemeral=False)

        try:
            profile = guild_config['grinder_profiles'][profile]
        except KeyError:
            embed = await get_error_embed("Profile not found! Please choose from the provided list")
            return await interaction.edit_original_response(embed=embed)
        
        grinder_profile = await interaction.client.grinderUsers.find({"guild": interaction.guild.id, "user": user.id})

        date = datetime.date.today()
        today = datetime.datetime(date.year, date.month, date.day)
        reminder_dm = False
        active_grinder = False
        if not grinder_profile:

            record = await interaction.client.grinderUsers.find({"reminder_time": {"$exists":"true"}, "user": interaction.user.id})
            if record:
                reminder_time = datetime.time.fromisoformat(record['reminder_time'])
            else:
                reminder_time = datetime.time(hour=12, tzinfo=utc)

            grinder_profile = {
                "guild": interaction.guild.id,
                "user": user.id,
                "profile": profile['name'],
                "profile_role": profile['role'],
                "payment": {
                    "total": 0,
                    "extra": 0,
                    "amount_per_grind": profile['payment'],
                    "grinder_since": today,
                    "first_payment": today,
                    "next_payment": today,
                },
                "reminder_time": str(reminder_time),
                "active": True
            }
            reminder_dm = True
            reminder_embed = await get_invisible_embed(
                f">>> You will be reminded to donate everyday at <t:{int(datetime.datetime.combine(today, reminder_time).timestamp())}:t>. Use </settings:1196688324207853590> to change the reminder time."
            )
            reminder_embed.title = "Custom Grinder Reminder"
            reminder_embed.set_thumbnail(url='https://cdn.discordapp.com/emojis/841624339169935390.gif?size=128&quality=lossless')
            await interaction.client.grinderUsers.insert(grinder_profile)

        
        elif grinder_profile['profile'] == profile['name'] and grinder_profile['profile_role'] == profile['role'] and grinder_profile['payment']['amount_per_grind'] == profile['payment']:
            if grinder_profile['active']:
                active_grinder = True
                await interaction.edit_original_response(embed= await get_error_embed(f"{user.mention} is already appointed as {profile['name'].title()}"))
            else:
                grinder_profile['active'] = True
                grinder_profile['payment']['first_payment'] = datetime.datetime(date.year, date.month, date.day)
                grinder_profile['payment']['next_payment'] = datetime.datetime(date.year, date.month, date.day)
                grinder_profile['payment']['amount_per_grind'] = profile['payment']
                await interaction.client.grinderUsers.upsert(grinder_profile)
                # user roles in id 
                removable_roles = list(guild_config['grinder_profiles'].keys())
                removable_roles.append(guild_config['grinder']['role'])
                if profile['role'] in removable_roles:
                    removable_roles.remove(profile['role'])
                roles_to_remove = [role.id for role in user.roles if role.id in removable_roles]
                roles_to_remove = [interaction.guild.get_role(role) for role in roles_to_remove]
                try:
                    await user.remove_roles(*roles_to_remove)
                except:
                    embed = await get_error_embed(f"Unable to remove roles from {user.mention}.")
                    return await interaction.edit_original_response(embed=embed)

                roles_to_add = [profile['role'] , guild_config['trial']['role']]
                roles_to_add = [role for role in roles_to_add if role not in [role.id for role in user.roles]]
                roles_to_add = [interaction.guild.get_role(role) for role in roles_to_add]
                try:
                    await user.add_roles(*roles_to_add)
                except:
                    embed = await get_error_embed(f"Unable to assign roles to {user.mention}.")
                    return await interaction.edit_original_response(embed=embed)
                
                appoint_dm = await get_invisible_embed(f"You have been reappointed as {profile['name'].title()}")
                appoint_dm.title = f"Grinder Reappointment as {profile['name'].title()}"
                appoint_dm.description = guild_config['appoint_embed']['description']
                appoint_dm.timestamp = datetime.datetime.now()
                try:
                    appoint_dm.set_footer(text = interaction.guild.name, icon_url = interaction.guild.icon.url)
                except:
                    appoint_dm.set_footer(text = interaction.guild.name)
                try:
                    appoint_dm.set_thumbnail(url = guild_config['appoint_embed']['thumbnail'])
                except:
                    pass
                grind_channel = interaction.guild.get_channel(guild_config['payment_channel'])
                if grind_channel:
                    view = discord.ui.View()
                    view.add_item(discord.ui.Button(label="Grinder's Donation Channel", emoji="<:tgk_channel:1073908465405268029>" , style=discord.ButtonStyle.primary, url=f"{grind_channel.jump_url}"))
                try:
                    if view:
                        await user.send(embed=appoint_dm, view=view)
                    else:
                        await user.send(embed=appoint_dm)
                except:
                    pass

                msg = await interaction.edit_original_response(embed= await get_invisible_embed(f"{user.mention} has been reappointed as {profile['name'].title()}"))
                log_channel = interaction.guild.get_channel(guild_config['grinder_logs'])
                if log_channel:
                    log_embed = await get_invisible_embed(f"{user.mention} has been reappointed as {profile['name'].title()}")
                    log_embed.title = f"Reappointed as {profile['name'].title()}"
                    log_embed.description = None
                    log_embed.add_field(name="User:", value=f"<:nat_reply:1146498277068517386> {user.mention}", inline=True)
                    log_embed.add_field(name="Appointed At:", value=f"<:nat_reply:1146498277068517386> {msg.jump_url}", inline=True)
                    try:
                        log_embed.set_footer(text=f"Reappointed by {interaction.user.name} | ID: {interaction.user.id}", icon_url=interaction.user.avatar.url)
                    except:
                        log_embed.set_footer(text=f"Reappointed by {interaction.user.name} | ID: {interaction.user.id}", icon_url=interaction.user.default_avatar.url)
                    try:
                        await log_channel.send(embed=log_embed)
                    except:
                        pass
                return
        
        if active_grinder == False:
            grinder_profile['profile'] = profile['name']
            grinder_profile['profile_role'] = profile['role']
            grinder_profile['active'] = True
            grinder_profile['payment']['amount_per_grind'] = profile['payment']
            grinder_profile['payment']['first_payment'] = datetime.datetime(date.year, date.month, date.day)
            grinder_profile['payment']['next_payment'] = datetime.datetime(date.year, date.month, date.day)
            await interaction.client.grinderUsers.upsert(grinder_profile)

        embed = await get_invisible_embed(f"{user.mention} has been appointed as {profile['name'].title()}")

        removable_roles = list(guild_config['grinder_profiles'].keys())
        removable_roles.append(guild_config['grinder']['role'])
        if profile['role'] in removable_roles:
            removable_roles.remove(profile['role'])
        roles_to_remove = [role.id for role in user.roles if role.id in removable_roles]
        roles_to_remove = [interaction.guild.get_role(role) for role in roles_to_remove]
        try:
            await user.remove_roles(*roles_to_remove)
        except:
            embed = await get_error_embed(f"Unable to remove roles from {user.mention}.")
            return await interaction.edit_original_response(embed=embed)
        roles_to_add = [profile['role'] , guild_config['trial']['role']]
        roles_to_add = [role for role in roles_to_add if role not in [role.id for role in user.roles]]
        roles_to_add = [interaction.guild.get_role(role) for role in roles_to_add]
        try:
            await user.add_roles(*roles_to_add)
        except:
            embed = await get_error_embed(f"Unable to assign roles to {user.mention}.")
            return await interaction.edit_original_response(embed=embed)
        
        appoint_dm = await get_invisible_embed(f"You have been reappointed as {profile['name'].title()}")
        appoint_dm.title = f"Grinder Appointment as {profile['name'].title()}"
        appoint_dm.description = guild_config['appoint_embed']['description']
        appoint_dm.timestamp = datetime.datetime.now()
        try:
            appoint_dm.set_footer(text = interaction.guild.name, icon_url = interaction.guild.icon.url)
        except:
            appoint_dm.set_footer(text = interaction.guild.name)
        try:
            appoint_dm.set_thumbnail(url = guild_config['appoint_embed']['thumbnail'])
        except:
            pass
        grind_channel = interaction.guild.get_channel(guild_config['payment_channel'])
        if grind_channel:
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Grinder's Donation Channel", emoji="<:tgk_channel:1073908465405268029>" , style=discord.ButtonStyle.primary, url=f"{grind_channel.jump_url}"))
        try:
            if reminder_dm:
                embeds = [appoint_dm, reminder_embed]
            else:
                embeds = [appoint_dm]
            if view:
                await user.send(embeds=embeds, view=view)
            else:
                await user.send(embeds=embeds)
        except:
            pass

        msg = await interaction.edit_original_response(embed= await get_invisible_embed(f"{user.mention} has been appointed as {profile['name'].title()}"))
        log_channel = interaction.guild.get_channel(guild_config['grinder_logs'])
        if log_channel:
            log_embed = await get_invisible_embed(f"{user.mention} has been reappointed as {profile['name'].title()}")
            log_embed.title = f"Appointed as {profile['name'].title()}"
            log_embed.description = None
            log_embed.add_field(name="User:", value=f"<:nat_reply:1146498277068517386> {user.mention}", inline=True)
            log_embed.add_field(name="Appointed At:", value=f"<:nat_reply:1146498277068517386> {msg.jump_url}", inline=True)
            try:
                log_embed.set_footer(text=f"Appointed by {interaction.user.name} | ID: {interaction.user.id}", icon_url=interaction.user.avatar.url)
            except:
                log_embed.set_footer(text=f"Appointed by {interaction.user.name} | ID: {interaction.user.id}", icon_url=interaction.user.default_avatar.url)
            try:
                await log_channel.send(embed=log_embed)
            except:
                pass
        
    @app_commands.command(name="dismiss", description="Remove Grinder")
    @app_commands.describe(user="User to dismiss")
    @app_commands.check(GrinderCheck)
    async def dismiss(self, interaction: Interaction, user: discord.Member, reason: Literal['Inactivity', 'Vacation', 'Others']):

        guild_config = await interaction.client.grinderSettings.find(interaction.guild.id)
        await interaction.response.defer(ephemeral=False)

        grinder_profile = await interaction.client.grinderUsers.find({"guild": interaction.guild.id, "user": user.id})
        if not grinder_profile:
            return await interaction.edit_original_response(embed= await get_error_embed(f"{user.mention} is not appointed as grinder"))
        if not grinder_profile['active']:
            return await interaction.edit_original_response(embed= await get_error_embed(f"{user.mention} is either demoted or on a break. Contact support to join grinders again!"))
        grinder_profile['active'] = False
        await interaction.client.grinderUsers.upsert(grinder_profile)

        roles_to_remove = [role.id for role in user.roles if role.id in [guild_config['grinder']['role'], guild_config['trial']['role'], grinder_profile['profile_role']]]
        roles_to_remove = [interaction.guild.get_role(role) for role in roles_to_remove]
        try:
            await user.remove_roles(*roles_to_remove)
        except:
            embed = await get_error_embed(f"Unable to remove roles from {user.mention}.")
            return await interaction.edit_original_response(embed=embed)
        
        embed = await get_invisible_embed(f"thanks for support")
        if reason == 'Vacation':
            embed.title = f"We'll miss you!"
            embed.description = guild_config['vacation_embed']['description']
            embed.timestamp = datetime.datetime.now()
            try:
                embed.set_thumbnail(url = guild_config['vacation_embed']['thumbnail'])
            except:
                pass
        else:
            embed.title = f"Dismissed from Grinders!"
            embed.description = guild_config['dismiss_embed']['description']
            embed.timestamp = datetime.datetime.now()
            try:
                embed.set_thumbnail(url = guild_config['dismiss_embed']['thumbnail'])
            except:
                pass
        try:
            embed.set_footer(text = interaction.guild.name, icon_url = interaction.guild.icon.url)
        except:
            embed.set_footer(text = interaction.guild.name)
        try:
            await user.send(embed=embed)
        except:
            pass
        
        msg = await interaction.edit_original_response(embed= await get_invisible_embed(f"{user.mention} has been dismissed from grinders."))
        
        log_channel = interaction.guild.get_channel(guild_config['grinder_logs'])
        if log_channel:
            log_embed = await get_invisible_embed(f"{user.mention} has been dismissed from grinders. Thanks for your support!")
            log_embed.title = f"Dismissed from Grinders"
            log_embed.description = None
            log_embed.add_field(name="User:", value=f"<:nat_reply:1146498277068517386> {user.mention}", inline=True)
            log_embed.add_field(name="Dismissed At:", value=f"<:nat_reply:1146498277068517386> {msg.jump_url}", inline=True)
            try:
                log_embed.set_footer(text=f"Dismissed by {interaction.user.name} | ID: {interaction.user.id}", icon_url=interaction.user.avatar.url)
            except:
                log_embed.set_footer(text=f"Dismissed by {interaction.user.name} | ID: {interaction.user.id}", icon_url=interaction.user.default_avatar.url)
            try:
                await log_channel.send(embed=log_embed)
            except:
                pass

    @app_commands.command(name="log-donation", description="Log Grinder Payment")
    @app_commands.describe(user="Whose donation to log?", amount="Amount to log, negative for deduction")
    @app_commands.check(GrinderCheck)
    async def log(self, interaction: Interaction, user: discord.Member, amount: app_commands.Transform[int, DMCConverter]):
        guild_config = await interaction.client.grinderSettings.find(interaction.guild.id)
        grinder_profile = await interaction.client.grinderUsers.find({"guild": interaction.guild.id, "user": user.id})
        if not grinder_profile:
            return await interaction.response.send_message(embed= await get_error_embed(f"{user.mention} is not appointed as grinder"), ephemeral=True)
        if not grinder_profile['active']:
            return await interaction.response.send_message(embed= await get_error_embed(f"{user.mention} is either demoted or on a break. Contact support to join grinders again!"), ephemeral=True)
        
        
        days_paid = int((amount+grinder_profile['payment']['extra'])/ grinder_profile['payment']['amount_per_grind'])
        amount_paid = days_paid * grinder_profile['payment']['amount_per_grind']
        extra_amount = int((amount+grinder_profile['payment']['extra'])-amount_paid)

        await interaction.response.defer(ephemeral=False)
        if amount < 0:
            if amount_paid + grinder_profile['payment']['total'] < 0:
                return await interaction.edit_original_response(embed= await get_error_embed(f"Can't deduct more than ⏣ {grinder_profile['payment']['total']}"))
            else:
                if extra_amount < 0:
                    grinder_profile['payment']['total'] += amount_paid - grinder_profile['payment']['amount_per_grind']
                    grinder_profile['payment']['extra'] = grinder_profile['payment']['amount_per_grind'] + extra_amount
                else:
                    grinder_profile['payment']['total'] += amount_paid
                    grinder_profile['payment']['extra'] = extra_amount
                grinder_profile['payment']['next_payment'] = grinder_profile['payment']['next_payment'] + datetime.timedelta(days=days_paid)
                await interaction.client.grinderUsers.upsert(grinder_profile)

                embed = await get_invisible_embed(f"⏣ {amount:,} has been deducted from {user.mention}")
                embed.title = f"{user.display_name}'s Grinder Payment"
                embed.description = None
                embed.add_field(name="Profile:", value=f"{grinder_profile['profile']}", inline=True)
                embed.add_field(name="Paid for:", value=f"{days_paid} {'day' if days_paid==1 else 'days'}", inline=True)
                embed.add_field(name="Sanctioned By:", value=f"{interaction.user.mention}", inline=True)
                embed.add_field(name="Amount Debited:", value=f"⏣ {-amount:,}", inline=True)
                if grinder_profile['payment']['extra'] > 0:
                    embed.add_field(name="Grinder Wallet:", value=f"⏣ {grinder_profile['payment']['extra']:,}", inline=True)
                embed.add_field(name="Grinder Bank:", value=f"⏣ {grinder_profile['payment']['total']:,}", inline=True)
                
                embed.timestamp = datetime.datetime.now()
                try:
                    embed.set_footer(text=f"{interaction.guild.name}", icon_url=interaction.guild.icon.url)
                except:
                    embed.set_footer(text=f"{interaction.guild.name}")
                try:
                    embed.set_thumbnail(url=user.avatar.url)
                except:
                    embed.set_thumbnail(url=user.default_avatar.url)
                msg = await interaction.edit_original_response(embed=embed)
                view = discord.ui.View()
                view.add_item(discord.ui.Button(label="Jump to message", style=discord.ButtonStyle.link, url=msg.jump_url))
                try:
                    embed.title = f"Manually Deducted by {interaction.user.name}"
                    await user.send(embed=embed, view=view)
                except:
                    pass

                log_channel = interaction.guild.get_channel(guild_config['grinder_logs'])
                if log_channel:
                    log_embed = await get_invisible_embed(f"⏣ {amount:,} has been deducted from {user.mention}")
                    log_embed.title = f"Amount Deducted"
                    log_embed.description = None
                    log_embed.add_field(name="Paid for:", value=f"{days_paid} {'day' if days_paid==1 else 'days'}", inline=True)
                    log_embed.add_field(name="Amount Debited:", value=f"⏣ {-amount:,}", inline=True)
                    log_embed.add_field(name="Deducted From:", value=f"{user.mention}", inline=True)
                    log_embed.timestamp = datetime.datetime.now()
                    try:
                        log_embed.set_thumbnail(url=user.avatar.url)
                    except:
                        log_embed.set_thumbnail(url=user.default_avatar.url)
                    try:
                        log_embed.set_footer(text=f"Deducted by {interaction.user.name} | ID: {interaction.user.id}", icon_url=interaction.user.avatar.url)
                    except:
                        log_embed.set_footer(text=f"Deducted by {interaction.user.name} | ID: {interaction.user.id}", icon_url=interaction.user.default_avatar.url)
                    view = discord.ui.View()
                    view.add_item(discord.ui.Button(label="Jump to message", style=discord.ButtonStyle.link, url=msg.jump_url))
                    try:
                        await log_channel.send(embed=log_embed,view=view)
                    except:
                        pass
                
        else:
            grinder_profile['payment']['total'] += amount_paid
            if extra_amount >= 0:
                grinder_profile['payment']['extra'] = extra_amount
            grinder_profile['payment']['next_payment'] = grinder_profile['payment']['next_payment'] + datetime.timedelta(days=days_paid)
            await interaction.client.grinderUsers.upsert(grinder_profile)

            embed = await get_invisible_embed(f"⏣ {amount:,} has been added to {user.mention}")
            embed.title = f"{user.display_name}'s Grinder Payment"
            embed.description = None
            embed.add_field(name="Profile:", value=f"{grinder_profile['profile']}", inline=True)
            embed.add_field(name="Paid for:", value=f"{days_paid} {'day' if days_paid==1 else 'days'}", inline=True)
            embed.add_field(name="Sanctioned By:", value=f"{interaction.user.mention}", inline=True)
            embed.add_field(name="Amount Credited:", value=f"⏣ {amount:,}", inline=True)
            if extra_amount > 0:
                embed.add_field(name="Grinder Wallet:", value=f"⏣ {extra_amount:,}", inline=True)
            embed.add_field(name="Grinder Bank:", value=f"⏣ {grinder_profile['payment']['total']:,}", inline=True)
            embed.timestamp = datetime.datetime.now()
            try:
                embed.set_footer(text=f"{interaction.guild.name}", icon_url=interaction.guild.icon.url)
            except:
                embed.set_footer(text=f"{interaction.guild.name}")
            try:
                embed.set_thumbnail(url=user.avatar.url)
            except:
                embed.set_thumbnail(url=user.default_avatar.url)
            msg = await interaction.edit_original_response(embed=embed)
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Jump to message", style=discord.ButtonStyle.link, url=msg.jump_url))
            try:
                embed.title = f"Manually Credited by {interaction.user.name}"
                await user.send(embed=embed, view=view)
            except:
                pass
            
            log_channel = interaction.guild.get_channel(guild_config['grinder_logs'])
            if log_channel:
                log_embed = await get_invisible_embed(f"⏣ {amount:,} has been added to {user.mention}")
                log_embed.title = f"Amount Added"
                log_embed.description = None
                log_embed.add_field(name="Paid for:", value=f"{days_paid} {'day' if days_paid==1 else 'days'}", inline=True)
                log_embed.add_field(name="Amount Credited:", value=f"⏣ {amount:,}", inline=True)
                log_embed.add_field(name="Credited To:", value=f"{user.mention}", inline=True)
                log_embed.timestamp = datetime.datetime.now()
                try:
                    log_embed.set_thumbnail(url=user.avatar.url)
                except:
                    log_embed.set_thumbnail(url=user.default_avatar.url)
                try:
                    log_embed.set_footer(text=f"Credited by {interaction.user.name} | ID: {interaction.user.id}", icon_url=interaction.user.avatar.url)
                except:
                    log_embed.set_footer(text=f"Credited by {interaction.user.name} | ID: {interaction.user.id}")
                view = discord.ui.View()
                view.add_item(discord.ui.Button(label="Jump to message", style=discord.ButtonStyle.link, url=msg.jump_url))
                try:
                    await log_channel.send(embed=log_embed, view=view)
                except:
                    pass
            
        role_changed = False
        user = interaction.guild.get_member(grinder_profile['user'])
        trial_role = interaction.guild.get_role(guild_config['trial']['role'])
        if trial_role is not None and trial_role in user.roles:
            date = datetime.date.today()
            today = datetime.datetime(date.year, date.month, date.day)
            if grinder_profile['payment']['next_payment'] > today and (grinder_profile['payment']['next_payment'] - grinder_profile['payment']['first_payment']).days >= int(guild_config['trial']['duration'])/(3600*24):
                if trial_role in user.roles:
                    try:
                        await user.remove_roles(trial_role)
                    except:
                        pass
                    grinder_role = interaction.guild.get_role(guild_config['grinder']['role'])
                    if grinder_role is not None and grinder_role not in user.roles:
                        try:
                            await user.add_roles(grinder_role)
                            role_changed = True
                        except:
                            pass
        if role_changed:
            await interaction.followup.send(embed= await get_invisible_embed(f"{user.mention} has been promoted to {grinder_role.mention}"), ephemeral=False, allowed_mentions=discord.AllowedMentions.none())

    @app_commands.command(name="bank", description="Check your grinder details")
    @app_commands.describe(user="User to check grinder details")
    async def bank(self, interaction: Interaction, user: discord.Member = None):
        await interaction.response.defer(ephemeral=False)

        if not user:
            user = interaction.user

        date = datetime.date.today()
        today = datetime.datetime(date.year, date.month, date.day)

        grinder_profile = await interaction.client.grinderUsers.find({"guild": interaction.guild.id, "user": user.id})
        if not grinder_profile:
            return await interaction.edit_original_response(embed= await get_error_embed(f"{user.mention} is not appointed as grinder"))
        if not grinder_profile['active']:
            return await interaction.edit_original_response(embed= await get_error_embed(f"{user.mention} is either demoted or on a break."))
        embed = await get_invisible_embed(f"Fetching {user.display_name}'s Grinder Stats ...")
        embed.description = None
        embed.title = f"{user.display_name}'s Grinder Stats"
        embed.add_field(name="Profile:", value=f"{grinder_profile['profile']}", inline=True)
        embed.add_field(name="Next Payment:", value=f'<t:{int(grinder_profile["payment"]["next_payment"].timestamp())}:D>', inline=True)
        embed.add_field(name="Grinder Since:", value=f'<t:{int(grinder_profile["payment"]["grinder_since"].timestamp())}:R>', inline=True)
        
        if grinder_profile['payment']['extra'] > 0:
            embed.add_field(name="Grinder Wallet:", value=f"⏣ {grinder_profile['payment']['extra']:,}", inline=True)
        else:
            embed.add_field(name="Amount per grind", value=f"⏣ {grinder_profile['payment']['amount_per_grind']:,}", inline=True)
        # amount to clear dues
        if grinder_profile['payment']['next_payment'] < today:
            pending_days = (today - grinder_profile['payment']['next_payment']).days
            amount = grinder_profile['payment']['amount_per_grind'] * pending_days - grinder_profile['payment']['extra']
            embed.add_field(name="Pending Amount:", value=f"⏣ {amount:,}", inline=True)
        embed.add_field(name="Grinder Bank:", value=f"⏣ {grinder_profile['payment']['total']:,}", inline=True)

        try:
            embed.set_thumbnail(url=user.avatar.url)
        except:
            embed.set_thumbnail(url=user.default_avatar.url)
        
        try:
            embed.set_footer(text=f"{interaction.guild.name}", icon_url=interaction.guild.icon.url)
        except:
            embed.set_footer(text=f"{interaction.guild.name}")
        embed.timestamp = datetime.datetime.now()

        return await interaction.edit_original_response(embed=embed)

    # summary for grinders
    @app_commands.command(name="summary", description="Check server based summary")
    @app_commands.check(GrinderCheck)
    async def summary(self, interaction: Interaction):
        guild_config = await interaction.client.grinderSettings.find(interaction.guild.id)
        await interaction.response.defer(ephemeral=False)

        date = datetime.date.today()
        today = datetime.datetime(date.year, date.month, date.day)

        grinder_profiles = await interaction.client.grinderUsers.get_all({"guild": interaction.guild.id, "active": True})
        upto_Date_grinders = [grinder for grinder in grinder_profiles if grinder['payment']['next_payment'] > today] # active grinders
        overdue_grinders = [grinder for grinder in grinder_profiles if grinder['payment']['next_payment'] <= today] # unpaid grinders
        total_grinders = len(grinder_profiles)

        # dono by active grinders
        expected_amount = sum([grinder['payment']['amount_per_grind'] for grinder in grinder_profiles])
        total_amount = sum([grinder['payment']['amount_per_grind'] for grinder in upto_Date_grinders])

        embed = await get_invisible_embed(f"Fetching {interaction.guild.name}'s Grinder Stats ...")
        embed.description = None
        embed.title = f"{interaction.guild.name}'s Grinder Summary"
        embed.add_field(name="Total:", value=f"{total_grinders} grinders", inline=True)
        embed.add_field(name="Active:", value=f"{len(upto_Date_grinders)} grinders", inline=True)
        embed.add_field(name="Inactive:", value=f"{len(overdue_grinders)} grinders", inline=True)
        embed.add_field(
            name = 'Weekly Stats:',
            value = f">>> **Expected Amount:** ⏣ {7*expected_amount:,}\n**Actual Amount:** ⏣ {7*total_amount:,}",
            inline = False
        )

        embed.timestamp = datetime.datetime.now()
        try:
            embed.set_footer(text=f"{interaction.guild.name}", icon_url=interaction.guild.icon.url)
        except:
            embed.set_footer(text=f"{interaction.guild.name}")
        view = GrinderSummeris(interaction=interaction, active_grinder=upto_Date_grinders, inactive_grinder=overdue_grinders)
        await interaction.edit_original_response(embed=embed, view=view)
        view.message = await interaction.original_response()

async def setup(bot):
    await bot.add_cog(
        grinder(bot)
    )
    print(f"loaded grinder cog")