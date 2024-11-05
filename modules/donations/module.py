from typing import Literal, List
import discord
from discord.ext import commands
from discord import app_commands, Interaction
from .db import Backend, GuildConfig, DankProfile, UserDonations
from .view import ConfigEdit
from utils.dank import DonationsInfo, get_donation_from_message
from utils.functions import bar
from utils.transformers import DMCConverter


class Donations(commands.GroupCog, name="donations", description="doantions commands"):
    def __init__(self, bot):
        self.bot = bot
        self.backend = Backend(bot)
        self.bot.dono = self.backend

    modify = app_commands.Group(name="modify", description="modify donations")
    donations = app_commands.Group(name="donations", description="donations commands")

    async def on_error(self, event, *args, **kwargs):
        raise Exception(f"Error in {event} event", args, kwargs)

    async def profile_auto_complete(
        self, interaction: Interaction, profile: str
    ) -> List[app_commands.Choice[str]]:
        config = await self.backend.get_guild_config(interaction.guild_id)
        if not config:
            return
        profiles = list(config["profiles"].keys())
        options = []
        for profile in profiles:
            if profile.lower().startswith(profile.lower()):
                options.append(app_commands.Choice(name=profile, value=profile))
        return options

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if after.guild is None:
            return
        if after.author.id != 270904126974590976 or after._interaction is None:
            return
        if after._interaction.name != "serverevents donate":
            return
        if len(after.embeds) == 0:
            return

        embed: discord.Embed = after.embeds[0]
        if not embed.description.startswith("Successfully donated "):
            return
        config: GuildConfig = await self.backend.get_guild_config(after.guild.id)
        if not config:
            return
        if "Dank Donations" not in config["profiles"].keys():
            return
        dank_profile: DankProfile = config["profiles"]["Dank Donations"]
        if after.channel.id not in dank_profile["tracking_channels"]:
            return
        donations_info: DonationsInfo = await get_donation_from_message(after)

        self.bot.dispatch("donation", donations_info, after)

    @commands.Cog.listener()
    async def on_donation(
        self, donations_info: DonationsInfo, message: discord.Message
    ):
        user_donations: UserDonations = await self.backend.get_user_donations(
            donations_info.donor.id, donations_info.donor.guild.id
        )

        if "Dank Donations" not in user_donations["profiles"].keys():
            user_donations["profiles"]["Dank Donations"] = 0

        TotalDonatedAmount = 0
        if donations_info.items:
            try:
                item_data = self.bot.dank_items_cache[donations_info.items]
                TotalDonatedAmount = item_data["price"] * donations_info.quantity
            except KeyError:
                await message.reply("Please inform developers about this error")
                return
        else:
            TotalDonatedAmount = donations_info.quantity

        user_donations["profiles"]["Dank Donations"] += TotalDonatedAmount
        await self.backend.update_user_donations(
            donations_info.donor.id, donations_info.donor.guild.id, user_donations
        )
        guild_config: GuildConfig = await self.backend.get_guild_config(
            donations_info.donor.guild.id
        )
        if not guild_config:
            return
        if "Dank Donations" not in guild_config["profiles"].keys():
            return

        dank_profile: DankProfile = guild_config["profiles"]["Dank Donations"]
        roles_to_add = []
        next_rank = None
        ranks = sorted(dank_profile["ranks"].values(), key=lambda x: x["donations"])
        for rank in ranks:
            if user_donations["profiles"]["Dank Donations"] >= rank["donations"]:
                role = message.guild.get_role(int(rank["role_id"]))
                if (
                    role not in donations_info.donor.roles
                    and role < donations_info.donor.guild.me.top_role
                ):
                    roles_to_add.append(role)
            elif (
                user_donations["profiles"]["Dank Donations"] < rank["donations"]
                and not next_rank
            ):
                next_rank = rank
                break

        if not next_rank:
            percentage = 100
        else:
            # take the ratio of the current donations to the next rank make it so last rank is 0% and next rank is 100% add egde cases for division by 0

            percentage = (
                user_donations["profiles"]["Dank Donations"] / next_rank["donations"]
            ) * 100

            if next_rank == ranks[0]:
                percentage = (
                    user_donations["profiles"]["Dank Donations"]
                    / next_rank["donations"]
                ) * 100
            else:
                diffrence = (
                    next_rank["donations"]
                    - ranks[ranks.index(next_rank) - 1]["donations"]
                )
                user_progress = (
                    user_donations["profiles"]["Dank Donations"]
                    - ranks[ranks.index(next_rank) - 1]["donations"]
                )
                percentage = (user_progress / diffrence) * 100

        embed = discord.Embed(description="", color=message.guild.me.color)
        embed.set_author(
            name=f"{donations_info.donor.display_name}'s Donations",
            icon_url=donations_info.donor.avatar.url
            if donations_info.donor.avatar
            else donations_info.donor.default_avatar,
        )
        embed.description = ""
        embed.description += f"* Total Donations `-` ⏣ {user_donations['profiles']['Dank Donations']:,}\n"
        if next_rank:
            embed.description += f"* Next Rank `-` ⏣ {next_rank['donations']:,}\n"
        if percentage == 100:
            embed.description += "-# Next Rank\n`-` MAX\n"
        else:
            progress_bar = await bar(percentage)
            embed.description += ("-# Next Rank • ") + (
                f"{progress_bar} • {percentage} %\n"
            )

        await message.reply(
            embed=embed,
            content=f"{donations_info.donor.mention} Thank you for your generous donation!",
        )

        if roles_to_add:
            await donations_info.donor.add_roles(*roles_to_add)

    @app_commands.command(name="setup", description="setup donations")
    async def setup(self, interaction: Interaction):
        config = await self.backend.get_guild_config(interaction.guild_id)
        embed = await self.backend.get_config_embed(config, interaction.guild)

        view = ConfigEdit(config, interaction.user)
        await interaction.response.send_message(embed=embed, ephemeral=False, view=view)

        view.message = await interaction.original_response()

    @modify.command(name="user", description="modify user donations")
    @app_commands.describe(
        user="The user to modify",
        profile="The profile to modify",
        operation="The operation to perform",
        amount="The amount to modify",
    )
    @app_commands.autocomplete(profile=profile_auto_complete)
    async def user(
        self,
        interaction: Interaction,
        user: discord.Member,
        profile: str,
        operation: Literal["Add", "Remove", "Set"],
        amount: app_commands.Transform[int, DMCConverter],
    ):
        config = await self.backend.get_guild_config(interaction.guild_id)
        if not config:
            return
        interaction_user_roles = [role.id for role in interaction.user.roles]
        if (set(config["admin_roles"]) & set(interaction_user_roles)) == set():
            return await interaction.response.send_message(
                "You don't have permission to use this command", ephemeral=True
            )

        if profile not in config["profiles"].keys():
            return await interaction.response.send_message(
                "Invalid profile", ephemeral=True
            )

        user_donations = await self.backend.get_user_donations(
            user.id, interaction.guild_id
        )
        if operation == "Add":
            user_donations["profiles"][profile] += amount
        elif operation == "Remove":
            user_donations["profiles"][profile] -= amount
        elif operation == "Set":
            user_donations["profiles"][profile] = amount

        await self.backend.update_user_donations(
            user.id, interaction.guild_id, user_donations
        )

        await interaction.response.send_message(
            f"Successfully {operation.lower()} {amount:,} to {profile} for {user.display_name}, new balance: {user_donations['profiles'][profile]:,}",
        )

        ranks = sorted(
            config["profiles"][profile]["ranks"].values(), key=lambda x: x["donations"]
        )
        roles_to_add = []
        next_rank = None

        for rank in ranks:
            role = interaction.guild.get_role(int(rank["role_id"]))
            if user_donations["profiles"][profile] >= rank["donations"]:
                if role not in user.roles and role < interaction.guild.me.top_role:
                    roles_to_add.append(role)
            elif (
                user_donations["profiles"][profile] < rank["donations"]
                and not next_rank
            ):
                next_rank = rank
                break

        if roles_to_add:
            await user.add_roles(*roles_to_add)
            await interaction.followup.send(
                content=f"Successfully added {','.join([role.mention for role in roles_to_add])} to {user.display_name}",
                allowed_mentions=discord.AllowedMentions.none(),
            )

    @app_commands.command(name="balance", description="check your donations balance")
    async def balance(self, interaction: Interaction):
        user_donations = await self.backend.get_user_donations(
            interaction.user.id, interaction.guild_id
        )
        config = await self.backend.get_guild_config(interaction.guild_id)
        if not config:
            return
        embed = discord.Embed(
            title=f"{interaction.user.display_name}'s Donations",
            color=interaction.guild.me.color,
        )

        for profile in config["profiles"].keys():
            if profile in user_donations["profiles"].keys():
                emoji = config["profiles"][profile]["emoji"]
                embed.add_field(
                    name=f"{profile}",
                    value=f"{emoji} {user_donations['profiles'][profile]:,}",
                    inline=False,
                )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Donations(bot))
