import discord
from discord.ext import commands
from discord import app_commands, Interaction
from .db import Backend, GuildConfig, DankProfile, UserDonations
from .view import ConfigEdit
from utils.dank import DonationsInfo, get_donation_from_message


class Donations(commands.GroupCog, name="donations", description="doantions commands"):
    def __init__(self, bot):
        self.bot = bot
        self.backend = Backend(bot)
        self.bot.dono = self.backend

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if after.guild is None:
            return
        if after.author.id != 270904126974590976 or after.interaction is None:
            return
        if after.interaction.name != "serverevents donate":
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
        donations_info: DonationsInfo = get_donation_from_message(after)

        self.bot.dispatch("donation", donations_info, after)

    @commands.Cog.listener()
    async def on_donation(
        self, donations_info: DonationsInfo, message: discord.Message
    ):
        user_donations: UserDonations = await self.backend.get_user_donations(
            donations_info.donor.id, donations_info.donor.guild.id
        )
        if not user_donations:
            return
        user_data: UserDonations = await self.backend.donations.find_by_custom(
            {
                "user_id": donations_info.donor.id,
                "guild_id": donations_info.donor.guild.id,
            }
        )
        if not user_data:
            user_data = {
                "user_id": donations_info.donor.id,
                "guild_id": donations_info.donor.guild.id,
                "events": {},
                "profiles": {},
            }
            await self.backend.donations.insert(user_data)
        if "Dank Donations" not in user_data["profiles"].keys():
            user_data["profiles"]["Dank Donations"] = 0
        if donations_info.items:
            item_data = self.bot.dank_items_cache[donations_info.items]
            user_data["profiles"]["Dank Donations"] += (
                donations_info.quantity * item_data["value"]
            )
        else:
            user_data["profiles"]["Dank Donations"] += donations_info.quantity
        await self.backend.donations.update(user_data)
        config = await self.backend.get_guild_config(donations_info.donor.guild.id)
        if not config:
            return
        if "Dank Donations" not in config["profiles"].keys():
            return
        dank_profile: DankProfile = config["profiles"]["Dank Donations"]
        roles_to_add = []
        next_rank = None
        for rank in dank_profile["ranks"].values():
            if user_data["profiles"]["Dank Donations"] >= rank["required"]:
                role = discord.utils.get(
                    donations_info.donor.guild.roles, id=rank["role"]
                )
                if (
                    role not in donations_info.donor.roles
                    and role < donations_info.donor.guild.me.top_role
                ):
                    roles_to_add.append(role)
            elif (
                user_data["profiles"]["Dank Donations"] < rank["required"]
                and not next_rank
            ):
                next_rank = rank

        if len(roles_to_add) > 0:
            await donations_info.donor.add_roles(*roles_to_add)
            embed = discord.Embed(
                title="Rank Up!",
                description=f"{donations_info.donor.mention} Congratulations! You have ranked up to {roles_to_add[-1].mention}",
                color=discord.Color.green(),
            )
            if next_rank:
                embed.description += f"~# Next Rankup: {next_rank['required'] - user_data['profiles']['Dank Donations']}"
            await message.reply(embed=embed, content=donations_info.donor.mention)

    @app_commands.command(name="setup", description="setup donations")
    async def setup(self, interaction: Interaction):
        config = await self.backend.get_guild_config(interaction.guild_id)
        embed = await self.backend.get_config_embed(config, interaction.guild)

        view = ConfigEdit(config, interaction.user)
        await interaction.response.send_message(embed=embed, ephemeral=False, view=view)

        view.message = await interaction.original_response()


async def setup(bot):
    await bot.add_cog(Donations(bot))
