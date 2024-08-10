import discord
from discord.ext import commands
from discord import app_commands, Interaction
from .db import Backend, GuildConfig, DankProfile, UserDonations
from .view import ConfigEdit
from utils.dank import DonationsInfo, get_donation_from_message
from utils.functions import bar


class Donations(commands.GroupCog, name="donations", description="doantions commands"):
    def __init__(self, bot):
        self.bot = bot
        self.backend = Backend(bot)
        self.bot.dono = self.backend

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
            # take the ratio of the current donations to the next rank
            ratio = (
                user_donations["profiles"]["Dank Donations"] - ranks[-2]["donations"]
            ) / (next_rank["donations"] - ranks[-2]["donations"])
            # get the percentage of the ratio
            percentage = int(ratio * 100)

        embed = discord.Embed(description="", color=message.guild.me.color)
        embed.set_author(
            name=f"{donations_info.donor.display_name}'s Donations",
            icon_url=donations_info.donor.avatar.url
            if donations_info.donor.avatar
            else donations_info.donor.default_avatar,
        )
        embed.description = ""
        embed.description += f"* Total Donations `-` ⏣ {user_donations['profiles']['Dank Donations']:,}\n"
        if percentage == 100:
            embed.description += "-# Next Rank\n`-` MAX\n"
        else:
            embed.description += ("-# Next Rank • ") + (f"{await bar(percentage)}\n")

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


async def setup(bot):
    await bot.add_cog(Donations(bot))
