import discord
from .db import GuildConfig
from discord.ui import Button, button, View
from discord import interactions
from utils.views.selects import Role_select, Channel_select, Select_General
from utils.views.modal import General_Modal
from utils.transformers import DMCConverter
from utils.embeds import get_formated_embed, get_formated_field


class ConfigEdit(View):
    def __init__(
        self,
        config: GuildConfig,
        member: discord.Member,
        message: discord.Message = None,
    ):
        super().__init__(timeout=60)
        self.config = config
        self.member = member
        self.message = message

    async def interaction_check(self, interaction: interactions.Interaction) -> bool:
        if interaction.user.id == self.member.id:
            return True
        else:
            await interaction.response.send_message(
                "You cannot interact with this message", ephemeral=True
            )
            return False

    async def on_timeout(self):
        for btn in self.children:
            btn.disabled = True
        try:
            await self.message.edit(view=self)
        except discord.NotFound:
            pass

    # async def on_error(
    #     self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item
    # ):
    #     if interaction.response.is_done():
    #         await interaction.followup.send(
    #             f"An error occured: {error}", ephemeral=True
    #         )
    #     else:
    #         await interaction.response.send_message(
    #             f"An error occured: {error}", ephemeral=True
    #         )

    @button(
        label="Manager Roles",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_role:1073908306713780284>",
    )
    async def manager_roles(self, interaction: discord.Interaction, button: Button):
        view = View()
        view.value = None
        view.select = Role_select(
            placeholder="Select role you want to add/remove",
            min_values=1,
            max_values=10,
        )
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)

        await view.wait()

        if view.value is None:
            return

        add_roles = []
        remove_roles = []

        for role in view.select.values:
            if role.id in self.config["manager_roles"]:
                remove_roles.append(role)
                self.config["manager_roles"].remove(role.id)
            else:
                add_roles.append(role)
                self.config["manager_roles"].append(role.id)

        await interaction.client.dono.update_guild_config(
            interaction.guild.id, self.config
        )

        await view.select.interaction.response.send_message(
            f"Added roles: {', '.join([role.mention for role in add_roles])}\nRemoved roles: {', '.join([role.mention for role in remove_roles])}",
            ephemeral=True,
        )

        await self.message.edit(
            embed=await interaction.client.dono.get_config_embed(
                self.config, interaction.guild
            )
        )

    @button(
        label="Log Channel",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_logging:1107652646887759973>",
    )
    async def log_channel(self, interaction: discord.Interaction, button: Button):
        view = View()
        view.value = None
        view.select = Channel_select(
            placeholder="Select channel you want to set as log channel",
            min_values=1,
            max_values=1,
            channel_types=[discord.ChannelType.text],
        )
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()

        if view.value is None:
            return await interaction.delete_original_response()

        if self.config["log_channel"] == view.select.values[0].id:
            self.config["log_channel"] = None
            await interaction.client.dono.update_guild_config(
                interaction.guild.id, self.config
            )
            await view.select.interaction.response.edit_message(
                content="Successfully removed log channel", view=None
            )
        else:
            self.config["log_channel"] = view.select.values[0].id
            await interaction.client.dono.update_guild_config(
                interaction.guild.id, self.config
            )
            await view.select.interaction.response.edit_message(
                content=f"Successfully set {view.select.values[0].mention} as log channel",
                view=None,
                delete_after=3,
            )

        await self.message.edit(
            embed=await interaction.client.dono.get_config_embed(
                self.config, interaction.guild
            )
        )

    @button(
        label="Profiles",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_people_group:1168173646796300420>",
    )
    async def profiles(self, interaction: discord.Interaction, button: Button):
        view = View()
        view.value = None
        options = [
            discord.SelectOption(
                label="Create Profile",
                value="create",
                description="Create a new Donation profile",
                emoji="<:tgk_add:1073902485959352362>",
            ),
            discord.SelectOption(
                label="Delete Profile",
                value="delete",
                description="Delete a Donation profile",
                emoji="<:tgk_delete:1113517803203461222>",
            ),
            discord.SelectOption(
                label="Edit Profile",
                value="edit",
                description="Edit a Donation profile",
                emoji="<:tgk_edit:1073902428224757850>",
            ),
            discord.SelectOption(
                label="List Profiles",
                value="view",
                description="View a Donation profile",
                emoji="<:tgk_description:1215649279360897125>",
            ),
        ]
        view.select = Select_General(
            interaction=interaction, options=options, min_values=1
        )
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()

        if view.value is None:
            return await interaction.delete_original_response()

        match view.select.values[0]:
            case "edit":
                edit_view = View()
                edit_view.value = None
                options = []
                for profile in self.config["profiles"].keys():
                    options.append(discord.SelectOption(label=profile, value=profile))
                edit_view.select = Select_General(
                    interaction=interaction,
                    placeholder="Select profile you want to edit",
                    options=options,
                    min_values=1,
                )
                edit_view.add_item(edit_view.select)

                await view.select.interaction.response.edit_message(view=edit_view)
                await edit_view.wait()

                if edit_view.value is None:
                    return await interaction.delete_original_response()

                profile = self.config["profiles"][edit_view.select.values[0]]
                if profile["name"] == "Dank Donations":
                    profile_edit = DankProfileView(
                        interaction.user,
                        profile=profile["name"],
                        config=self.config,
                        interaction=interaction,
                    )
                    embed = discord.Embed(
                        description="",
                        color=0x2B2D31,
                    )
                    embed.description += "<:tgk_bank:1134892342910914602> ``Dank Donations Profiles``\n\n"
                    embed_args = await get_formated_embed(
                        ["Tracking Channels", "Log Channel", "Events", "Emoji"]
                    )
                    embed.description += f"{await get_formated_field(guild=interaction.guild, name=embed_args['Tracking Channels'], data=profile['tracking_channels'], type='channel')}\n"
                    embed.description += f"{await get_formated_field(guild=interaction.guild, name=embed_args['Log Channel'], data=profile['log_channel'], type='channel')}\n"
                    embed.description += f"{await get_formated_field(guild=interaction.guild, name=embed_args['Events'], data=list(profile['events'].keys()), type='str')}\n"
                    embed.description += f"{await get_formated_field(guild=interaction.guild, name=embed_args['Emoji'], data=profile['emoji'], type='str')}\n"
                    ranks = ""
                    for role_id, rank in profile["ranks"].items():
                        role = interaction.guild.get_role(int(role_id))
                        if not role:
                            continue
                        ranks += f"* {role.mention} - {rank['donations']:,}\n"
                    if ranks == "":
                        ranks = "* None"
                    embed.add_field(name="Ranks", value=ranks)

                    await edit_view.select.interaction.response.edit_message(
                        embed=embed, view=profile_edit
                    )
            case _:
                await edit_view.select.interaction.response.send_message(
                    content="Not Available Yet", ephemeral=True, delete_after=3
                )


class DankProfileView(View):
    def __init__(
        self,
        member: discord.Member,
        profile: str,
        config: GuildConfig,
        interaction: discord.Interaction = None,
    ):
        super().__init__(timeout=60)
        self.member = member
        self.profile = profile
        self.message = interaction
        self.config = config

    async def interaction_check(self, interaction: interactions.Interaction) -> bool:
        if interaction.user.id == self.member.id:
            return True
        else:
            await interaction.response.send_message(
                "You cannot interact with this message", ephemeral=True
            )
            return False

    async def on_timeout(self):
        for btn in self.children:
            btn.disabled = True
        try:
            await self.message.edit_original_response(view=self)
        except discord.NotFound:
            pass

    # async def on_error(
    #     self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item
    # ) -> None:
    #     if interaction.response.is_done():
    #         await interaction.followup.send(
    #             f"An error occured: {error}", ephemeral=True
    #         )
    #     else:
    #         await interaction.response.send_message(
    #             f"An error occured: {error}", ephemeral=True
    #         )

    async def update_embed(self, interaction: discord.Interaction):
        embed = discord.Embed(
            description="",
            color=0x2B2D31,
        )
        embed.description += (
            "<:tgk_bank:1134892342910914602> ``Dank Donations Profiles``\n\n"
        )
        embed_args = await get_formated_embed(
            ["Tracking Channels", "Log Channel", "Events", "Emoji"]
        )
        embed.description += f"{await get_formated_field(guild=interaction.guild, name=embed_args['Tracking Channels'], data=self.config['profiles'][self.profile]['tracking_channels'], type='channel')}\n"
        embed.description += f"{await get_formated_field(guild=interaction.guild, name=embed_args['Log Channel'], data=self.config['profiles'][self.profile]['log_channel'], type='channel')}\n"
        embed.description += f"{await get_formated_field(guild=interaction.guild, name=embed_args['Events'], data=list(self.config['profiles'][self.profile]['events'].keys()), type='str')}\n"
        embed.description += f"{await get_formated_field(guild=interaction.guild, name=embed_args['Emoji'], data=self.config['profiles'][self.profile]['emoji'], type='str')}\n"
        ranks = ""
        for role_id, rank in self.config["profiles"][self.profile]["ranks"].items():
            role = interaction.guild.get_role(int(role_id))
            if not role:
                continue
            ranks += f"* {role.mention} - {rank['donations']:,}\n"
        if ranks == "":
            ranks = "* None"
        embed.add_field(name="Ranks", value=ranks)
        return embed

    @button(
        label="Auto Tracking",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_bank:1134892342910914602>",
    )
    async def auto_tracking(self, interaction: discord.Interaction, button: Button):
        view = View()
        view.select = Channel_select(
            placeholder="Select channel you want to add/remove",
            min_values=1,
            max_values=10,
            channel_types=[discord.ChannelType.text],
        )
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()

        if view.value is None:
            return await interaction.delete_original_response()

        add_channels = []
        remove_channels = []

        for channel in view.select.values:
            if channel.id in self.config["profiles"][self.profile]["tracking_channels"]:
                remove_channels.append(channel.mention)
                self.config["profiles"][self.profile]["tracking_channels"].remove(
                    channel.id
                )
            else:
                add_channels.append(channel.mention)
                self.config["profiles"][self.profile]["tracking_channels"].append(
                    channel.id
                )

        await interaction.client.dono.update_guild_config(
            interaction.guild.id, self.config
        )

        await view.select.interaction.response.edit_message(
            embed=discord.Embed(
                description=f"Added channels: {', '.join(add_channels) if len(add_channels) >= 1 else 'None'}\nRemoved channels: {', '.join(remove_channels) if len(remove_channels) >= 1 else 'None'}",
                color=0x2B2D31,
            ),
            delete_after=3,
        )

        await self.message.edit_original_response(
            embed=await self.update_embed(interaction)
        )

    @button(
        label="Log Channel",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_logging:1107652646887759973>",
    )
    async def log_channel(self, interaction: discord.Interaction, button: Button):
        view = View()
        view.select = Channel_select(
            placeholder="Select channel you want to set as log channel",
            min_values=1,
            max_values=1,
            channel_types=[discord.ChannelType.text],
        )
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()

        if view.value is None:
            return await interaction.delete_original_response()

        if (
            self.config["profiles"][self.profile]["log_channel"]
            == view.select.values[0].id
        ):
            self.config["profiles"][self.profile]["log_channel"] = None
            await interaction.client.dono.update_guild_config(
                interaction.guild.id, self.config
            )
            await view.select.interaction.response.edit_message(
                content="Successfully removed log channel", view=None
            )
        else:
            self.config["profiles"][self.profile]["log_channel"] = view.select.values[
                0
            ].id
            await interaction.client.dono.update_guild_config(
                interaction.guild.id, self.config
            )
            await view.select.interaction.response.edit_message(
                content=f"Successfully set {view.select.values[0].mention} as log channel",
                view=None,
                delete_after=3,
            )

        await self.message.edit_original_response(
            embed=await self.update_embed(interaction)
        )

    @button(
        label="Ranks",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_people_group:1168173646796300420>",
    )
    async def ranks(self, interaction: discord.Interaction, button: Button):
        view = View()
        options = [
            discord.SelectOption(
                label="Add Rank",
                value="add",
                description="Add a new rank to the profile",
                emoji="<:tgk_addPerson:1132590758831079454>",
            ),
            discord.SelectOption(
                label="Remove Rank",
                value="remove",
                description="Remove a rank from the profile",
                emoji="<:tgk_removePerson:1132593125588733983>",
            ),
        ]
        view.select = Select_General(
            interaction=interaction,
            options=options,
            placeholder="Select the action you want to perform",
        )
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()

        if view.value is None:
            return await interaction.delete_original_response()

        match view.select.values[0]:
            case "remove":
                options = []
                for role_id, rank in self.config["profiles"][self.profile][
                    "ranks"
                ].items():
                    role = interaction.guild.get_role(int(role_id))
                    if not role:
                        continue
                    options.append(
                        discord.SelectOption(
                            label=role.name,
                            value=str(role.id),
                            description=f"Rank: {rank['donations']:,}",
                        )
                    )
                if len(options) == 0:
                    return await view.select.interaction.response.edit_message(
                        content="There are no ranks to remove",
                        view=None,
                        delete_after=3,
                    )
                elif len(options) >= 25:
                    options = options[:24]
                rank_remove_view = View()
                rank_remove_view.select = Select_General(
                    interaction=interaction,
                    options=options,
                    placeholder="Select the rank you want to remove",
                    min_values=1,
                    max_values=len(options),
                )
                rank_remove_view.add_item(rank_remove_view.select)
                await view.select.interaction.response.edit_message(
                    view=rank_remove_view
                )
                await rank_remove_view.wait()
                if rank_remove_view.value is None:
                    return await interaction.delete_original_response()
                removed_ranks = []
                for role in rank_remove_view.select.values:
                    del self.config["profiles"][self.profile]["ranks"][str(role)]
                    removed_ranks.append(f"<@&{role}>")

                await interaction.client.dono.update_guild_config(
                    interaction.guild.id, self.config
                )
                await rank_remove_view.select.interaction.response.edit_message(
                    embed=discord.Embed(
                        description=f"Removed ranks: {', '.join(removed_ranks)}",
                        color=0x2B2D31,
                    ),
                    delete_after=3,
                    view=None,
                )

                await self.message.edit_original_response(
                    embed=await self.update_embed(interaction)
                )

            case "add":
                rankAddView = View()
                rankAddView.value = None
                rankAddView.select = Role_select(
                    placeholder="Select role you want to add",
                    min_values=1,
                    max_values=1,
                )
                rankAddView.add_item(rankAddView.select)

                await view.select.interaction.response.edit_message(view=rankAddView)
                await rankAddView.wait()

                if rankAddView.value is None:
                    return await interaction.delete_original_response()

                role = rankAddView.select.values[0]
                if (
                    str(role.id)
                    in self.config["profiles"][self.profile]["ranks"].keys()
                ):
                    return await rankAddView.select.interaction.response.edit_message(
                        content="This role is already a rank", view=None, delete_after=3
                    )
                if role >= interaction.guild.me.top_role:
                    return await rankAddView.select.interaction.response.edit_message(
                        content="I cannot assign roles higher than my own",
                        view=None,
                        delete_after=3,
                    )
                if role.managed or role.is_bot_managed():
                    return await rankAddView.select.interaction.response.edit_message(
                        content="I cannot assign bot/managed roles",
                        view=None,
                        delete_after=3,
                    )

                rank_data = {"role_id": role.id, "donations": None}
                modalView = General_Modal(
                    title="Donations form",
                    interaction=rankAddView.select.interaction,
                )
                modalView.donations = discord.ui.TextInput(
                    label="Amount of Donations",
                    placeholder="Enter the amount of donations required for this rank",
                    min_length=1,
                    max_length=10,
                )
                modalView.add_item(modalView.donations)

                await rankAddView.select.interaction.response.send_modal(modalView)
                await modalView.wait()

                if modalView.value is None:
                    return await interaction.delete_original_response()

                donations = await DMCConverter().transform(
                    interaction=modalView.interaction, value=modalView.donations.value
                )

                if not isinstance(donations, int):
                    return await modalView.interaction.response.send_message(
                        content="Invalid number", ephemeral=True
                    )

                rank_data["donations"] = donations

                self.config["profiles"][self.profile]["ranks"][str(role.id)] = rank_data
                await interaction.client.dono.update_guild_config(
                    interaction.guild.id, self.config
                )

                await modalView.interaction.response.edit_message(
                    content=f"Successfully added {role.mention} as a rank",
                    view=None,
                    delete_after=3,
                )
                await self.message.edit_original_response(
                    embed=await self.update_embed(interaction)
                )

    @button(
        label="Emoji",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_color:1107261678204244038>",
    )
    async def emoji(self, interaction: discord.Interaction, button: Button):
        modalView = General_Modal(title="Emoji form", interaction=interaction)
        modalView.value = None
        modalView.emoji = discord.ui.TextInput(
            label="Emoji",
            placeholder="Enter the emoji you want to set",
            max_length=100,
        )
        modalView.add_item(modalView.emoji)

        await interaction.response.send_modal(modalView)
        await modalView.wait()

        if modalView.value is None:
            return await interaction.delete_original_response()

        emoji = modalView.emoji.value

        self.config["profiles"][self.profile]["emoji"] = emoji

        await interaction.client.dono.update_guild_config(
            interaction.guild.id, self.config
        )

        await modalView.interaction.response.send_message(
            content=f"Successfully set {emoji} as the emoji",
            view=None,
            delete_after=3,
            ephemeral=True,
        )

        await interaction.client.dono.update_guild_config(
            interaction.guild.id, self.config
        )

        await self.message.edit_original_response(
            embed=await self.update_embed(interaction)
        )
