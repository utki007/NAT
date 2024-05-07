import asyncio
import datetime
import discord
from discord import Interaction, app_commands
from discord.ext import commands, tasks
from humanfriendly import format_timespan

from utils.dank import get_donation_from_message
from utils.embeds import get_error_embed, get_invisible_embed, get_warning_embed

utc = datetime.timezone.utc
midnight = datetime.time(tzinfo=utc)
times = [
    datetime.time(tzinfo=utc),
    datetime.time(hour=1, tzinfo=utc),
    datetime.time(hour=2, tzinfo=utc),
    datetime.time(hour=3, tzinfo=utc),
    datetime.time(hour=4, tzinfo=utc),
    datetime.time(hour=5, tzinfo=utc),
    datetime.time(hour=6, tzinfo=utc),
    datetime.time(hour=7, tzinfo=utc),
    datetime.time(hour=8, tzinfo=utc),
    datetime.time(hour=9, tzinfo=utc),
    datetime.time(hour=10, tzinfo=utc),
    datetime.time(hour=11, tzinfo=utc),
    datetime.time(hour=12, tzinfo=utc),
    datetime.time(hour=13, tzinfo=utc),
    datetime.time(hour=14, tzinfo=utc),
    datetime.time(hour=15, tzinfo=utc),
    datetime.time(hour=16, tzinfo=utc),
    datetime.time(hour=17, tzinfo=utc),
    datetime.time(hour=18, tzinfo=utc),
    datetime.time(hour=19, tzinfo=utc),
    datetime.time(hour=20, tzinfo=utc),
    datetime.time(hour=21, tzinfo=utc),
    datetime.time(hour=22, tzinfo=utc),
    datetime.time(hour=23, tzinfo=utc)
]

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
        
        days_paid = int(amount / grinder_profile['payment']['amount_per_grind'])
        amount_paid = days_paid * grinder_profile['payment']['amount_per_grind']
        extra_amount = amount - amount_paid

        grinder_profile['payment']['total'] += amount_paid
        grinder_profile['payment']['next_payment'] = grinder_profile['payment']['next_payment'] + datetime.timedelta(days=days_paid)
        await self.bot.grinderUsers.upsert(grinder_profile)

        role_changed = False
        trial_role = message.guild.get_role(guild_config['trial']['role'])
        if trial_role is not None and trial_role in donor.roles:
            date = datetime.date.today()
            today = datetime.datetime(date.year, date.month, date.day)
            if grinder_profile['payment']['next_payment'] > today and (today - grinder_profile['payment']['first_payment']).days >= guild_config['trial']['duration']:
                if trial_role in donor.roles:
                    try:
                        await donor.remove_roles(trial_role)
                    except:
                        pass
                    grinder_role = message.guild.get_role(guild_config['grinder_role'])
                    if grinder_role is not None and grinder_role not in donor.roles:
                        try:
                            await donor.add_roles(grinder_role)
                            role_changed = True
                        except:
                            pass

        embed = await get_invisible_embed(f"⏣ {amount_paid:,} has been added to {donor.mention}")
        embed.title = f"{donor.display_name}'s Grinder Payment"
        embed.description = None
        embed.add_field(name="Profile:", value=f"{grinder_profile['profile']}", inline=True)
        embed.add_field(name="Paid for:", value=f"{days_paid} {'day' if days_paid==1 else 'days'}", inline=True)
        embed.add_field(name="Sanctioned By:", value=f"Automatic Detection", inline=True)
        embed.add_field(name="Amount Credited:", value=f"⏣ {amount_paid:,}", inline=True)
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
        embeds = []
        if days_paid > 0:
            embeds.append(embed)
        if extra_amount > 0:
            embeds.append(await get_invisible_embed(f"**Extra amount:** ⏣ {extra_amount:,} hasn't been added to {donor.mention}."))
        msg = None
        try:
            await donor.send(embeds=embeds)
        except:
            pass

        if msg is None:
            return
        log_channel = message.guild.get_channel(guild_config['grinder_logs'])
        if log_channel:
            log_embed = await get_invisible_embed(f"⏣ {amount_paid:,} has been added to {donor.mention}")
            log_embed.title = f"Amount Added"
            log_embed.description = None
            log_embed.add_field(name="Paid for:", value=f"{days_paid} {'day' if days_paid==1 else 'days'}", inline=True)
            log_embed.add_field(name="Amount Credited:", value=f"⏣ {amount_paid:,}", inline=True)
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
            discord.app_commands.Choice(name=value['name'], value=key)
            for key, value in config['grinder_profiles'].items() if current.lower() in value['name'].lower()
        ]
        return choices[:24] if len(choices) > 0 else [app_commands.Choice(name="No profile found", value="None")]

    @tasks.loop(time=times)
    async def grinder_reminder(self):
        
        guild_configs = await self.bot.grinderSettings.get_all()

        date = datetime.date.today()
        today = datetime.datetime(date.year, date.month, date.day)
        time = datetime.datetime.now()
        time = datetime.time(hour=time.hour, tzinfo=utc)

        for guild_config in guild_configs:
            guild = self.bot.get_guild(guild_config['_id'])
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
                    pending_days = (today - grinder_user['payment']['next_payment']).days
                    amount = grinder_user['payment']['amount_per_grind'] * pending_days
                    embed = await get_invisible_embed(f"Hey {user.mention}, you have pending payment of ⏣ {amount:,} for {pending_days} days. Please grind soon.")
                    
                    embed.title = f"{guild.name}'s Grinder Reminder"
                    embed.description = None
                    embed.add_field(name="Pending From:", value = f"{pending_days} {'day' if pending_days==1 else 'days'}", inline=True)
                    embed.add_field(name="Amount:", value = f"⏣ {amount:,}", inline=True)
                    embed.add_field(name="Donation Channel:", value = f"{grinder_channel.mention}", inline=True)
                    embed.timestamp = datetime.datetime.now()
                    embed.set_footer(text=f"Inform manager if you have any trouble with donations.")
                    try:
                        embed.set_thumbnail(url=guild.icon.url)
                    except:
                        pass
                    try:
                        await user.send(embed=embed)
                        await asyncio.sleep(1)
                    except:
                        pass

    @grinder_reminder.before_loop
    async def before_grinder_reminder(self):
        await self.bot.wait_until_ready()

    @grinder_reminder.error
    async def grinder_reminder_error(self, error):
        chal = self.bot.get_channel(999555462674522202)
        await chal.send(f"<@488614633670967307> <@301657045248114690> ,Error in grinder reminder: {error}")

    @tasks.loop(time=midnight)
    async def grinder_demotions(self):
        
        guild_configs = await self.bot.grinderSettings.get_all()
        date = datetime.date.today()
        today = datetime.datetime(date.year, date.month, date.day)
        for guild_config in guild_configs:
            
            guild = self.bot.get_guild(guild_config['_id'])
            log_channel = guild.get_channel(guild_config['grinder_logs'])
            demote_days = int(guild_config['trial']['duration']/(3600*24))
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
                    if days > demote_days*2:
                        grinder_user['active'] = False
                        await self.bot.grinderUsers.upsert(grinder_user)
                        roles_to_remove = [role.id for role in user.roles if role.id in [guild_config['grinder_role'], guild_config['trial']['role'], grinder_user['profile_role']]]
                        roles_to_remove = [guild.get_role(role) for role in roles_to_remove]
                        try:
                            await user.remove_roles(*roles_to_remove)
                        except:
                            pass
                        embed.title = f"Kicked from {grinder_user['profile'].title()}"
                    elif days > demote_days:
                        roles_to_remove = [role.id for role in user.roles if role.id in [guild_config['grinder_role'], grinder_user['profile_role']]]
                        roles_to_remove = [guild.get_role(role) for role in roles_to_remove]
                        try:
                            await user.remove_roles(*roles_to_remove)
                        except:
                            pass
                        embed.title = f"Demoted to Trial Grinder"

                    
                    embed.description = guild_config['dismiss_embed']['description']
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
        chal = self.bot.get_channel(999555462674522202)
        await chal.send(f"<@488614633670967307> <@301657045248114690> ,Error in grinder demotions: {error}")

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
        await interaction.response.defer(ephemeral=False)

        try:
            profile = guild_config['grinder_profiles'][profile]
        except KeyError:
            embed = await get_error_embed("Profile not found! Please choose from the provided list")
            return await interaction.edit_original_response(embed=embed)
        
        grinder_profile = await interaction.client.grinderUsers.find({"guild": interaction.guild.id, "user": user.id})

        date = datetime.date.today()
        if not grinder_profile:

            grinder_profile = {
                "guild": interaction.guild.id,
                "user": user.id,
                "profile": profile['name'],
                "profile_role": profile['role'],
                "payment": {
                    "total": 0,
                    "amount_per_grind": profile['payment'],
                    "grinder_since": datetime.datetime(date.year, date.month, date.day),
                    "first_payment": datetime.datetime(date.year, date.month, date.day),
                    "next_payment": datetime.datetime(date.year, date.month, date.day),
                },
                "reminder_time": str(datetime.time(hour=12, tzinfo=utc)),
                "active": True
            }
            await interaction.client.grinderUsers.insert(grinder_profile)

        elif grinder_profile['profile'] == profile['name'] and grinder_profile['profile_role'] == profile['role'] and grinder_profile['payment']['amount_per_grind'] == profile['payment']:
            if grinder_profile['active']:
                return await interaction.edit_original_response(embed= await get_error_embed(f"{user.mention} is already appointed as {profile['name'].title()}"))
            else:
                grinder_profile['active'] = True
                grinder_profile['payment']['first_payment'] = datetime.datetime(date.year, date.month, date.day)
                grinder_profile['payment']['next_payment'] = datetime.datetime(date.year, date.month, date.day)
                grinder_profile['payment']['amount_per_grind'] = profile['payment']
                await interaction.client.grinderUsers.upsert(grinder_profile)
                # user roles in id 
                removable_roles = list(guild_config['grinder_profiles'].keys())
                removable_roles.append(guild_config['grinder_role'])
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
                    view.add_item(discord.ui.Button(label="#Grinder-donation channel", style=discord.ButtonStyle.primary, url=f"{grind_channel.jump_url}"))
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
        
        grinder_profile['profile'] = profile['name']
        grinder_profile['profile_role'] = profile['role']
        grinder_profile['active'] = True
        grinder_profile['payment']['first_payment'] = datetime.datetime(date.year, date.month, date.day)
        grinder_profile['payment']['next_payment'] = datetime.datetime(date.year, date.month, date.day)
        await interaction.client.grinderUsers.upsert(grinder_profile)

        embed = await get_invisible_embed(f"{user.mention} has been appointed as {profile['name'].title()}")

        removable_roles = list(guild_config['grinder_profiles'].keys())
        removable_roles.append(guild_config['grinder_role'])
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
            view.add_item(discord.ui.Button(label="#Grinder-donation channel", style=discord.ButtonStyle.primary, url=f"{grind_channel.jump_url}"))
        try:
            if view:
                await user.send(embed=appoint_dm, view=view)
            else:
                await user.send(embed=appoint_dm)
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
    async def dismiss(self, interaction: Interaction, user: discord.Member):

        guild_config = await interaction.client.grinderSettings.find(interaction.guild.id)
        await interaction.response.send_message(embed=await get_invisible_embed("<a:nat_timer:1010824320672604260> **|** Please wait..."))

        grinder_profile = await interaction.client.grinderUsers.find({"guild": interaction.guild.id, "user": user.id})
        if not grinder_profile:
            return await interaction.edit_original_response(embed= await get_error_embed(f"{user.mention} is not appointed as grinder"))
        if not grinder_profile['active']:
            return await interaction.edit_original_response(embed= await get_error_embed(f"{user.mention} is either demoted or on a break. Contact support to join grinders again!"))
        grinder_profile['active'] = False
        await interaction.client.grinderUsers.upsert(grinder_profile)

        roles_to_remove = [role.id for role in user.roles if role.id in [guild_config['grinder_role'], guild_config['trial']['role'], grinder_profile['profile_role']]]
        roles_to_remove = [interaction.guild.get_role(role) for role in roles_to_remove]
        try:
            await user.remove_roles(*roles_to_remove)
        except:
            embed = await get_error_embed(f"Unable to remove roles from {user.mention}.")
            return await interaction.edit_original_response(embed=embed)
        
        dismiss_embed = await get_invisible_embed(f"{user.mention} has been dismissed from grinders. Thanks for your support!")
        dismiss_embed.title = f"Dismissed from Grinders"
        dismiss_embed.description = guild_config['dismiss_embed']['description']
        dismiss_embed.timestamp = datetime.datetime.now()
        try:
            dismiss_embed.set_footer(text = interaction.guild.name, icon_url = interaction.guild.icon.url)
        except:
            dismiss_embed.set_footer(text = interaction.guild.name)
        try:
            dismiss_embed.set_thumbnail(url = guild_config['dismiss_embed']['thumbnail'])
        except:
            pass
        try:
            await user.send(embed=dismiss_embed)
        except:
            pass
        
        msg = await interaction.edit_original_response(embed= await get_invisible_embed(f"{user.mention} has been dismissed from grinders. Thanks for your support!"))
        
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
    async def log(self, interaction: Interaction, user: discord.Member, amount: int):
        guild_config = await interaction.client.grinderSettings.find(interaction.guild.id)
        grinder_profile = await interaction.client.grinderUsers.find({"guild": interaction.guild.id, "user": user.id})
        if not grinder_profile:
            return await interaction.response.send_message(embed= await get_error_embed(f"{user.mention} is not appointed as grinder"), ephemeral=True)
        if not grinder_profile['active']:
            return await interaction.response.send_message(embed= await get_error_embed(f"{user.mention} is either demoted or on a break. Contact support to join grinders again!"), ephemeral=True)
        
        
        days_paid = int(amount / grinder_profile['payment']['amount_per_grind'])
        if days_paid == 0:
            return await interaction.response.send_message(embed= await get_error_embed(f"Amount should be in multiples of ⏣ {grinder_profile['payment']['amount_per_grind']:,}"))
        amount_paid = days_paid * grinder_profile['payment']['amount_per_grind']
        extra_amount = amount - amount_paid

        await interaction.response.defer(ephemeral=False)
        if amount < 0:
            extra_amount = amount + amount_paid
            if amount_paid + grinder_profile['payment']['total'] < 0:
                return await interaction.edit_original_response(embed= await get_error_embed(f"Can't deduct more than ⏣ {grinder_profile['payment']['total']}"), ephemeral=True)
            else:
                grinder_profile['payment']['total'] += amount_paid
                grinder_profile['payment']['next_payment'] = grinder_profile['payment']['next_payment'] - datetime.timedelta(days=days_paid)
                await interaction.client.grinderUsers.upsert(grinder_profile)

                embed = await get_invisible_embed(f"⏣ {amount:,} has been deducted from {user.mention}")
                embed.title = f"{user.display_name}'s Grinder Payment"
                embed.description = None
                embed.add_field(name="Profile:", value=f"{grinder_profile['profile']}", inline=True)
                embed.add_field(name="Paid for:", value=f"{days_paid} {'day' if days_paid==1 else 'days'}", inline=True)
                embed.add_field(name="Sanctioned By:", value=f"{interaction.user.mention}", inline=True)
                embed.add_field(name="Amount Debited:", value=f"⏣ {-amount:,}", inline=True)
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
                        log_embed.set_footer(text=f"Deducted by {interaction.user.name} | ID: {interaction.user.id}", icon_url=interaction.guild.icon.url)
                    except:
                        log_embed.set_footer(text=f"Deducted by {interaction.user.name} | ID: {interaction.user.id}")
                    view = discord.ui.View()
                    view.add_item(discord.ui.Button(label="Jump to message", style=discord.ButtonStyle.link, url=msg.jump_url))
                    try:
                        await log_channel.send(embed=log_embed,view=view)
                    except:
                        pass
                
        else:
            grinder_profile['payment']['total'] += amount_paid
            grinder_profile['payment']['next_payment'] = grinder_profile['payment']['next_payment'] + datetime.timedelta(days=days_paid)
            await interaction.client.grinderUsers.upsert(grinder_profile)

            embed = await get_invisible_embed(f"⏣ {amount_paid:,} has been added to {user.mention}")
            embed.title = f"{user.display_name}'s Grinder Payment"
            embed.description = None
            embed.add_field(name="Profile:", value=f"{grinder_profile['profile']}", inline=True)
            embed.add_field(name="Paid for:", value=f"{days_paid} {'day' if days_paid==1 else 'days'}", inline=True)
            embed.add_field(name="Sanctioned By:", value=f"{interaction.user.mention}", inline=True)
            embed.add_field(name="Amount Credited:", value=f"⏣ {amount_paid:,}", inline=True)
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
            if extra_amount > 0: 
                await interaction.followup.send(embed= await get_invisible_embed(f"**Extra amount:** ⏣ {extra_amount:,} hasn't been added to {user.mention}."), ephemeral=False, allowed_mentions=discord.AllowedMentions.none())
            
            log_channel = interaction.guild.get_channel(guild_config['grinder_logs'])
            if log_channel:
                log_embed = await get_invisible_embed(f"⏣ {amount_paid:,} has been added to {user.mention}")
                log_embed.title = f"Amount Added"
                log_embed.description = None
                log_embed.add_field(name="Paid for:", value=f"{days_paid} {'day' if days_paid==1 else 'days'}", inline=True)
                log_embed.add_field(name="Amount Credited:", value=f"⏣ {amount_paid:,}", inline=True)
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
                if grinder_profile['payment']['next_payment'] > today and (today - grinder_profile['payment']['first_payment']).days >= guild_config['trial']['duration']:
                    if trial_role in user.roles:
                        try:
                            await user.remove_roles(trial_role)
                        except:
                            pass
                        grinder_role = interaction.guild.get_role(guild_config['grinder_role'])
                        if grinder_role is not None and grinder_role not in user.roles:
                            try:
                                await user.add_roles(grinder_role)
                                role_changed = True
                            except:
                                pass
            if role_changed:
                await interaction.followup.send(embed= await get_invisible_embed(f"{user.mention} has been promoted to {grinder_role.name}"), ephemeral=False, allowed_mentions=discord.AllowedMentions.none())

    @app_commands.command(name="bank", description="Check your grinder details")
    @app_commands.describe(user="User to check grinder details")
    async def bank(self, interaction: Interaction, user: discord.Member = None):
        guild_config = await interaction.client.grinderSettings.find(interaction.guild.id)
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
        embed.add_field(name="Grinder Since:", value=f'{format_timespan(today - grinder_profile["payment"]["grinder_since"])}', inline=True)
        embed.add_field(name="Amount per grind", value=f"⏣ {grinder_profile['payment']['amount_per_grind']:,}", inline=True)
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
        upto_Date_grinders = [grinder for grinder in grinder_profiles if grinder['payment']['next_payment'] > today]
        overdue_grinders = [grinder for grinder in grinder_profiles if grinder['payment']['next_payment'] <= today]
        total_grinders = len(grinder_profiles)

        # dono by active grinders
        expected_amount = sum([grinder['payment']['amount_per_grind'] for grinder in grinder_profiles])
        total_amount = sum([grinder['payment']['amount_per_grind'] for grinder in upto_Date_grinders])

        embed = await get_invisible_embed(f"Fetching {interaction.guild.name}'s Grinder Stats ...")
        embed.description = None
        embed.title = f"{interaction.guild.name}'s Grinder Summary"
        embed.add_field(name="Total:", value=f"{total_grinders} grinders", inline=True)
        embed.add_field(name="Active:", value=f"{len(upto_Date_grinders)} grinders", inline=True)
        embed.add_field(name="Overdue:", value=f"{len(overdue_grinders)} grinders", inline=True)
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
        return await interaction.edit_original_response(embed=embed)

async def setup(bot):
    await bot.add_cog(
        grinder(bot),
        guilds=[discord.Object(999551299286732871), discord.Object(785839283847954433)]
    )
    print(f"loaded grinder cog")