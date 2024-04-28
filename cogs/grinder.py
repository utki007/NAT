import datetime
import discord
import typing
from discord.ext import commands, tasks
from discord import app_commands, Interaction
from utils.db import Document
from ui.settings.grinder import GrinderConfigPanel
from utils.types import GrinderConfig, GrinderAccount, GrinderProfile
from utils.embeds import get_formated_embed, get_formated_field
from humanfriendly import format_timespan
from utils.views.confirm import Confirm
from utils.dank import get_doantion_from_message, DonationsInfo, calculate_payments

class GrinderDB:
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.mongo['Grinder']
        self.config: Document = Document(self.db, "config", GrinderConfig)
        self.grinders: Document = Document(self.db, "grinders", GrinderAccount)
        self.config_cache = {}

    async def create_config(self, guild: discord.Guild) -> GrinderConfig:
        config: GrinderConfig = {
            "_id": guild.id,
            "payment_channel": None,
            "trail": {
                'duration': None,
                'role': None
            },
            "base_role": None,
            "manager_roles": [],
            "max_profiles": 5,
            "profile": {}
        }
        await self.config.insert(dict(config))
        self.config_cache[guild] = config
        return config
    
    async def get_config(self, guild: discord.Guild) -> GrinderConfig:
        config: GrinderConfig = await self.config.find(guild.id)
        if not config:
            config = await self.create_config(guild)

        self.config_cache[guild.id] = config
        return config
    
    async def update_config(self, guild: discord.Guild, data: GrinderConfig):
        await self.config.update(guild.id, dict(data))
        self.config_cache[guild.id] = data
  
    async def get_payment(self, guild: int, user: int):
        payment = await self.grinders.find({"guild": guild, "user": user})
        return payment

    async def get_config_embed(self, guild: discord.Guild, config: GrinderConfig) -> discord.Embed:
        embed = discord.Embed(color=0x2b2d31, description="")
        arguments = ["Payment Channel", "Manager Roles", "Base Role", "Trail Role", "Trail Duration", "Max Profiles", "Profiles"]
        formated_args = await get_formated_embed(arguments)
        
        embed.description = ""
        embed.description += "<:tgk_cc:1150394902585290854> `Grinder System`"
        embed.description += "\n\n"
        embed.description += f"{await get_formated_field(guild, formated_args['Payment Channel'], 'channel', config['payment_channel'])}\n"
        embed.description += f"{await get_formated_field(guild, formated_args['Manager Roles'], 'role', config['manager_roles'])}\n"
        embed.description += f"{await get_formated_field(guild, formated_args['Base Role'], 'role', config['base_role'])}\n"
        embed.description += f"{await get_formated_field(guild, formated_args['Trail Role'], 'role', config['trail']['role'])}\n"

        if config['trail']['duration'] is not None:
           embed.description += f"{await get_formated_field(guild, formated_args['Trail Duration'], 'time', config['trail']['duration'])}\n"
        else:
           embed.description += f"{await get_formated_field(guild, formated_args['Trail Duration'], 'str', 'None')}\n"

        embed.description += f"{formated_args['Max Profiles']}" + str(config['max_profiles']) + "\n"
        embed.description += f"{formated_args['Profiles']}" + f"{len(config['profile'].keys())}/{config['max_profiles']}\n\n"
        embed.description += "<:tgk_hint:1206282482744561744> Use buttons below to changes the settings"
        return embed

@app_commands.guild_only()
class Grinders(commands.GroupCog, name="grinders"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.backend = GrinderDB(bot)
        self.bot.grinder = self.backend
        self.payment_reminder.start()
    
    def cog_unload(self):
        self.payment_reminder.stop()
    
    async def GrinderProfileAutoComplete(self, interaction: Interaction, current: str) -> discord.app_commands.Choice[str]:
        guild: discord.Guild = interaction.guild
        config = await self.backend.get_config(guild)
        choices = [
            discord.app_commands.Choice(name=value['name'], value=key)
            for key, value in config['profile'].items() if current.lower() in value['name'].lower()
        ]
        return choices[:24] if len(choices) > 0 else [app_commands.Choice(name="No profile found", value="None")]
    
    @staticmethod
    async def GrinderCheck(interaction: Interaction):

        if interaction.user.guild_permissions.administrator or interaction.user.guild_permissions.manage_guild or interaction.user == interaction.guild.owner:
            return True
        
        if interaction.user.id in interaction.client.owner_ids:
            return True

        guild: discord.Guild = interaction.guild
        user_roles = [role.id for role in interaction.user.roles]
        config = await interaction.client.grinder.get_config(guild)
        if not config:
            await interaction.response.send_message("Grinder system is not setup in this server", ephemeral=True)
            return False
        if (set(config['manager_roles']) & set(user_roles)):
            return True
        await interaction.response.send_message("You don't have permission to use this command", ephemeral=True)
        return False

    async def CalMissedPayment(self, guild: discord.Guild, grinder_account: GrinderAccount, guild_config: GrinderConfig):
        today = datetime.datetime.now()
        if grinder_account['payment']['last_payment'] > grinder_account['payment']['next_payment']:
            due_payment = (grinder_account['payment']['last_payment'] - grinder_account['payment']['next_payment']).days * guild_config['profile'][str(grinder_account['profile_role'])]['payment']
        else:
            due_payment = 0

        return due_payment



    @tasks.loop(seconds=30)
    async def payment_reminder(self):
        guilds_configs = await self.backend.config.find_all()

        for guild_config in guilds_configs:
            guild = self.bot.get_guild(guild_config['_id'])
            if not guild: continue

            grinders = await self.backend.grinders.find_many_by_custom({"guild": guild.id})
            today = datetime.datetime.now()
            for grinder in grinders:
                user = guild.get_member(grinder['user'])
                if not isinstance(user, discord.Member): continue

                if today > grinder['payment']['next_payment']:
                    self.bot.dispatch("grinder_reminder", guild, user, grinder, guild_config)
                    self.bot.dispatch("grinder_kick", guild, user, grinder, guild_config)
    
    @payment_reminder.before_loop
    async def before_payment_reminder(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_grinder_reminder(self, guild: discord.Guild, user: discord.Member, grinder_account: GrinderAccount, guild_config: GrinderConfig):
        due_payment = await self.CalMissedPayment(guild, grinder_account, guild_config)
        grinder_account['payment']['due'] = due_payment
        await self.backend.grinders.update(grinder_account)

        try:await user.send(f"Hey {user.mention}, you have missed your {due_payment} payment. Please pay as soon as possible to avoid any inconvenience")
        except discord.Forbidden: pass

    @commands.Cog.listener()
    async def on_grinder_kick(self, guild: discord.Guild, user: discord.Member, grinder_account: GrinderAccount, guild_config: GrinderConfig):
        today = datetime.datetime.now()
        pending_days = int((today - grinder_account['payment']['next_payment']).days)
        if pending_days > 0:
            if pending_days > guild_config['missed_payment_limit']:
                grinder_account['active'] = False
                try:await user.remove_roles(guild.get_role(grinder_account['profile_role']))
                except discord.Forbidden: pass
                await self.backend.grinders.update(grinder_account)

        

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.id != 270904126974590976: return
        if len(message.embeds) <= 0: return
        if message.guild.id not in [785839283847954433, 999551299286732871]: return
        guild_config = await self.backend.get_config(message.guild)
        if not guild_config['payment_channel']: return

        if message.channel.id != guild_config['payment_channel']: return
        embed = message.embeds[0]

        if embed.description != "Successfully donated!": return
        try: message = await message.channel.fetch_message(message.reference.message_id)
        except discord.NotFound: return        
        donation_info: DonationsInfo = await get_doantion_from_message(message)

        grinder_account = await self.backend.get_payment(message.guild.id, donation_info.donor.id)
        if not grinder_account: return
        profile = guild_config['profile'][str(grinder_account['profile_role'])]
        if grinder_account['active'] == False: grinder_account['active'] = True
        await self.backend.grinders.update(grinder_account)
        self.bot.dispatch("grinder_payment", message.guild, donation_info.donor, donation_info, profile, grinder_account, message, guild_config)

        
    @commands.Cog.listener()
    async def on_grinder_payment(self, guild: discord.Guild, user: discord.Member, donation: DonationsInfo, profile: GrinderProfile, grinder_account: GrinderAccount, message: discord.Message, guild_config: GrinderConfig):                
        if donation.quantity < profile['payment']:
            await message.reply(f"{user.mention}, you have successfully paid {donation.format()} but you are still due for {profile['payment'] - donation.quantity}, if you are paying payment in installments contact the admin when you have paid the full amount so they can update your payment status")
            return
        paid_for = int(donation.quantity/profile['payment'])        
        nextPayment = grinder_account['payment']['next_payment'] + datetime.timedelta(days=paid_for)
        lastPayment = datetime.datetime.now()

        profile_payment = profile['payment']

        total_payment = grinder_account['payment']['total'] + paid_for * profile_payment

        due_payment = await self.CalMissedPayment(guild, grinder_account, guild_config)

        grinder_account['payment']['total'] = total_payment
        grinder_account['payment']['last_payment'] = lastPayment
        grinder_account['payment']['next_payment'] = nextPayment
        grinder_account['payment']['due'] = due_payment

        await self.backend.grinders.update(grinder_account)

        # await message.reply(f"{user.mention}, you have successfully paid {donation.format()} which covered your payment till <t:{round(nextPayment.timestamp())}:R>")
        embed = discord.Embed(color=0x2b2d31, description="")
        embed.description += f"<:tgk_active:1082676793342951475> **Donation Logged**"
        embed.description += f"\n\n"
        embed.description += f"{user.mention}, you have successfully paid {donation.format()} which covered your payment till <t:{round(nextPayment.timestamp())}:R>"
        await message.reply(embed=embed)
        await message.add_reaction("<:tgk_active:1082676793342951475>")
        tgk = self.bot.get_guild(785839283847954433)
        log_channel = tgk.get_channel(1119998681924509747)
        await log_channel.send(f"{user.mention}, you have successfully paid {donation.format()} which covered your payment till <t:{round(nextPayment.timestamp())}:R>")


    @app_commands.command(name="setup", description="Setup the grinder system")
    async def setup(self, interaction: Interaction): 
        config: GrinderConfig = await self.backend.get_config(interaction.guild)
        view = GrinderConfigPanel(config, interaction.user)

        await interaction.response.send_message(embed=await self.backend.get_config_embed(interaction.guild, config), view=view)
        view.message = await interaction.original_response()


    @app_commands.command(name="appoint", description="Add New Grinder")
    @app_commands.autocomplete(profile=GrinderProfileAutoComplete)
    @app_commands.describe(profile="Profile to appoint", user="User to appoint")
    async def appoint(self, interaction: Interaction, profile: str, user: discord.Member):

        if profile == "None":
            await interaction.response.send_message("No profile found", ephemeral=True)
            return
        
        guild_config = await self.backend.get_config(interaction.guild)
        await interaction.response.send_message(embed=discord.Embed(description="Please wait..."))
        try:
            profile: GrinderProfile = guild_config['profile'][profile]
        except KeyError:
                await interaction.edit_original_response(embed=discord.Embed(description="Profile not found! Please choose from the provided list", color=0x2b2d31))
                return
        
        grinder_profile = await self.backend.grinders.find({"guild": interaction.guild.id, "user": user.id})
        
        if not grinder_profile:

            if guild_config['base_role']: 
                role = interaction.guild.get_role(guild_config['base_role'])
                await user.add_roles(role)
            if guild_config['trail']['role']:
                role = interaction.guild.get_role(guild_config['trail']['role'])
                await user.add_roles(role)
            
            await user.add_roles(interaction.guild.get_role(profile['role']))

            
            grinder_profile: GrinderAccount = {
                "guild": interaction.guild.id,
                "user": user.id,
                "profile": profile['name'],
                "profile_role": profile['role'],
                "payment": {
                    "total": 0,
                    "due": 0,
                    "credits": 0,
                    "last_payment": datetime.datetime.now(),
                    "next_payment": datetime.datetime.now(),
                },
                "active": True
            }

            await self.backend.grinders.insert(dict(grinder_profile))
            await interaction.edit_original_response(content=None, embed=discord.Embed(description=f"{user.mention} has been appointed as {profile['name']}"))
            return
        
        if grinder_profile['profile'] == profile['name']:

            await interaction.edit_original_response(content=f"{user.mention} is already appointed as {profile['name']}")
            return
        
        elif grinder_profile['profile'] != profile['name']:

            embed = discord.Embed(color=0x2b2d31, description=f"{user.mention} is already a grinder {grinder_profile['profile']}. Do you want to change it to {profile['name']}?")
            view = Confirm(interaction.user, 30)            
            await interaction.edit_original_response(embed=embed, view=view)
            view.message = await interaction.original_response()

            await view.wait()
            if view.value:

                await view.interaction.response.edit_message(embed=discord.Embed(description="Please wait...", color=0x2b2d31), view=None)
                if guild_config['base_role']: 
                    await user.add_roles(interaction.guild.get_role(guild_config['base_role']))
                if guild_config['trail']['role']:
                    await user.add_roles(interaction.guild.get_role(guild_config['trail']['role']))
                await user.add_roles(interaction.guild.get_role(profile['role']))
                await user.remove_roles(interaction.guild.get_role(grinder_profile['profile_role']))

                grinder_profile['profile'] = profile['name']
                grinder_profile['profile_role'] = int(profile['role'])

                await self.backend.grinders.update(grinder_profile)
                await view.interaction.edit_original_response(embed=discord.Embed(description=f"{user.mention} has successfully changed to {profile['name']}"))

                try:
                    appoint_embed = discord.Embed(color=0x2b2d31, description=f"Congratulations {user.mention}, you have been appointed as {profile['name']} grinder in {interaction.guild.name}")
                    await user.send(embed=appoint_embed)
                except discord.Forbidden:
                    pass
                return
            
            else:
                await interaction.edit_original_response(content="Cancelled")
                return

    @app_commands.command(name="dismiss", description="Dismiss a grinder")
    @app_commands.describe(user="User to dismiss")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.check(GrinderCheck)
    async def dismiss(self, interaction: Interaction, user: discord.Member):
        guild_config = await self.backend.get_config(interaction.guild)
        grinder_profile = await self.backend.grinders.find({"guild": interaction.guild.id, "user": user.id})
        if not grinder_profile:
            await interaction.response.send_message(f"{user.mention} is not a grinder", ephemeral=True)
            return

        embed = discord.Embed(color=0x2b2d31, description=f"Are you sure you want to dismiss {user.mention} from {grinder_profile['profile']}?")
        view = Confirm(interaction.user, 30)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

        await view.wait()
        if view.value:
            await view.interaction.response.edit_message(embed=discord.Embed(description="Please wait...", color=0x2b2d31), view=None)
            if guild_config['base_role']: 
                await user.remove_roles(interaction.guild.get_role(guild_config['base_role']))
            if guild_config['trail']['role']:
                await user.remove_roles(interaction.guild.get_role(guild_config['trail']['role']))
            await user.remove_roles(interaction.guild.get_role(grinder_profile['profile_role']))
            await self.backend.grinders.delete(grinder_profile)
            await view.interaction.edit_original_response(embed=discord.Embed(description=f"{user.mention} has been dismissed from {grinder_profile['profile']}"))
            return
        else:
            await interaction.edit_original_response(content="Cancelled")
            return


    @app_commands.command(name="stats", description="Check payment status")
    @app_commands.describe(user="User to check")
    async def stats(self, interaction: Interaction, user: discord.Member = None):
        user = user if user else interaction.user
        guild_config = await self.backend.get_config(interaction.guild)
        grinder_profile: GrinderAccount = await self.backend.grinders.find({"guild": interaction.guild.id, "user": user.id})
        if not grinder_profile:
            await interaction.response.send_message(f"{user.mention} is not a grinder", ephemeral=True)
            return

        due_payment = await self.CalMissedPayment(interaction.guild, grinder_profile, guild_config)
        grinder_profile['payment']['due'] = due_payment
        await self.backend.grinders.update(grinder_profile)

        embed = discord.Embed(color=0x2b2d31, description=f"<:tgk_money:1199223318662885426> `{user.name}'s Payment Status`\n\n")
        formated_args = await get_formated_embed(["Total Payment", "Missed Payment", "Extra Payment", "Last Payment", "Next Payment"])
        embed.description += f"{await get_formated_field(guild=interaction.guild, name=formated_args['Total Payment'], type='int', data=grinder_profile['payment']['total'])}\n"
        embed.description += f"{await get_formated_field(guild=interaction.guild, name=formated_args['Missed Payment'], type='str', data=grinder_profile['payment']['due'])}\n"
        embed.description += f"{await get_formated_field(guild=interaction.guild, name=formated_args['Extra Payment'], type='int', data=grinder_profile['payment']['credits'])}\n"
        embed.description += f"{await get_formated_field(guild=interaction.guild, name=formated_args['Next Payment'], type='time', data=grinder_profile['payment']['next_payment'])}\n"

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Grinders(bot), 
                      guilds=[discord.Object(999551299286732871), discord.Object(785839283847954433)])


"""
        paid = donation.quantity + grinder_account['payment']['credits']
        if grinder_account['payment']['due'] > 0:
            
            if paid > grinder_account['payment']['due']:
                paid -= grinder_account['payment']['due']
                grinder_account['payment']['due'] = 0
            else:
                grinder_account['payment']['due'] -= paid
                await self.backend.grinders.update(grinder_account)
                await message.reply(f"{user.mention}, you have successfully paid {donation.format()} but you are still due for {grinder_account['payment']['due']}")
                return
            
        if paid < profile_payment:
            grinder_account['payment']['credits'] += paid
            await self.backend.grinders.update(grinder_account)
            await message.reply(f"{user.mention}, you have successfully paid {donation.format()} but you are still due for {profile_payment - paid}")
            return
        
        if paid > profile_payment:
            credits = paid - profile_payment
            grinder_account['payment']['credits'] += credits
            grinder_account['payment']['last_payment'] = datetime.datetime.utcnow()

            #check how many time grinder_account['payment']['credits'] can over the profile_payment and still have some credits left
            if grinder_account['payment']['credits'] > profile_payment:
                future_payments = grinder_account['payment']['credits'] // profile_payment
                extra_credits = grinder_account['payment']['credits'] % profile_payment
                grinder_account['payment']['credits'] = extra_credits

                if future_payments > 1:
                    grinder_account['payment']['next_payment'] = grinder_account['payment']['last_payment'] + datetime.timedelta(seconds=profile['frequency']*future_payments)
                else:
                    grinder_account['payment']['next_payment'] = grinder_account['payment']['last_payment'] + datetime.timedelta(seconds=profile['frequency'])

                await self.backend.grinders.update(grinder_account)
                await message.reply(f"{user.mention}, you have successfully paid {donation.format()} which covered your payment till <t:{round((datetime.datetime.utcnow() + datetime.timedelta(seconds=profile['frequency']*future_payments).timestamp()))}:R>")

            else:
                await self.backend.grinders.update(grinder_account)
                await message.reply(f"{user.mention}, you have successfully paid {donation.format()} which covered your payment till <t:{round((datetime.datetime.utcnow() + datetime.timedelta(seconds=profile['frequency']).timestamp()))}:R>")
            
            return
        
        elif paid == profile_payment:
            grinder_account['payment']['last_payment'] = datetime.datetime.utcnow()
            grinder_account['payment']['next_payment'] = grinder_account['payment']['last_payment'] + datetime.timedelta(seconds=profile['frequency'])
            await self.backend.grinders.update(grinder_account)
            await message.reply(f"{user.mention}, you have successfully paid {donation.format()} which covered your payment till <t:{round((datetime.datetime.utcnow() + datetime.timedelta(seconds=profile['frequency']).timestamp()))}:R>")
            return
"""