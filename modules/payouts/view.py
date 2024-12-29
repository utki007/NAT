import datetime
import re
import discord
from discord import Interaction, app_commands

import humanfriendly
from utils.convertor import TimeConverter

from utils.embeds import (
    get_error_embed,
    get_invisible_embed,
    get_success_embed,
    get_warning_embed,
)
from utils.views.modal import General_Modal
from utils.views.selects import Role_select
from utils.views.ui import Dropdown_Channel


class ButtonCooldown(app_commands.CommandOnCooldown):
    def __init__(self, retry_after: float):
        self.retry_after = retry_after

    def key(interaction: discord.Interaction):
        return interaction.user


async def update_payouts_embed(interaction: Interaction, data: dict):
    embed = discord.Embed(title="Dank Payout Management", color=3092790)

    if isinstance(data["claim_channel"], discord.Webhook):
        try:
            channel = f"{data['claim_channel'].channel.mention}"
        except Exception:
            channel = "`None`"
    else:
        channel = "`None`"
    embed.add_field(
        name="Claim Channel:",
        value=f"<:nat_reply:1146498277068517386> {channel}",
        inline=True,
    )

    if isinstance(data["claimed_channel"], discord.Webhook):
        try:
            channel = f"{data['claimed_channel'].channel.mention}"
        except Exception:
            channel = "`None`"
    else:
        channel = "`None`"
    embed.add_field(
        name="Queue Channel:",
        value=f"<:nat_reply:1146498277068517386> {channel}",
        inline=True,
    )

    channel = interaction.guild.get_channel(data["payout_channel"])
    if channel is None:
        channel = "`None`"
    else:
        channel = f"{channel.mention}"
    embed.add_field(
        name="Payout Channel:",
        value=f"<:nat_reply:1146498277068517386> {channel}",
        inline=True,
    )

    channel = interaction.guild.get_channel(data["log_channel"])
    if channel is None:
        channel = "`None`"
    else:
        channel = f"{channel.mention}"
    embed.add_field(
        name="Log Payouts:",
        value=f"<:nat_reply:1146498277068517386> {channel}",
        inline=True,
    )
    embed.add_field(
        name="Claim Time:",
        value=f"<:nat_reply:1146498277068517386> **{humanfriendly.format_timespan(data['default_claim_time'])}**",
        inline=True,
    )

    roles = data["manager_roles"]
    roles = [
        interaction.guild.get_role(role)
        for role in roles
        if interaction.guild.get_role(role) is not None
    ]
    roles = [f"1. {role.mention}" for role in roles]
    role = "\n".join(roles)
    if len(roles) == 0:
        role = "`None`"
    embed.add_field(name="Payout Managers (Admin):", value=f">>> {role}", inline=False)

    roles = data["event_manager_roles"]
    roles = [
        interaction.guild.get_role(role)
        for role in roles
        if interaction.guild.get_role(role) is not None
    ]
    roles = [f"1. {role.mention}" for role in roles]
    role = "\n".join(roles)
    if len(roles) == 0:
        role = "`None`"
    embed.add_field(
        name="Staff Roles (Queue Payouts):", value=f">>> {role}", inline=False
    )
    return embed


class Payouts_Panel(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, data: dict):
        super().__init__(timeout=180)
        self.interaction = interaction
        self.message = None  # req for disabling buttons after timeout
        self.data = data

    @discord.ui.button(label="toggle_button_label", row=1)
    async def toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = await interaction.client.payouts.get_config(interaction.guild.id)
        if data["enable_payouts"]:
            data["enable_payouts"] = False
            await interaction.client.payouts.update_config(data)
            button.style = discord.ButtonStyle.gray
            button.label = "Module Disabled"
            button.emoji = "<:toggle_off:1123932890993020928>"
            await interaction.response.edit_message(view=self)
        else:
            data["enable_payouts"] = True
            await interaction.client.payouts.update_config(data)
            button.style = discord.ButtonStyle.gray
            button.label = "Module Enabled"
            button.emoji = "<:toggle_on:1123932825956134912>"
            await interaction.response.edit_message(view=self)

    @discord.ui.button(
        label="Claim Channel",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_channel:1073908465405268029>",
        row=1,
    )
    async def modify_claim_channel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.guild.me.guild_permissions.manage_webhooks is False:
            embed = await get_warning_embed(
                "I do not have the `Manage Webhooks` permission, please give me the permission and try again."
            )
            return await interaction.response.send_message(embed=embed)
        data = await interaction.client.payouts.get_config(interaction.guild.id)
        view = Dropdown_Channel(interaction)
        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()
        if view.value is None:
            embed = await get_warning_embed("Dropdown timed out, please retry.")
            return await interaction.edit_original_response(
                content=None, embed=embed, view=None
            )
        else:
            await view.interaction.response.edit_message(
                content="Setting up webhook...", view=None
            )
            channel = interaction.guild.get_channel(view.value.id)
            New_webhook = None
            for webhook in await channel.webhooks():
                webhook: discord.Webhook = webhook
                if webhook.user.id == interaction.client.user.id:
                    New_webhook = webhook
                    break
            if New_webhook is None:
                New_webhook = await channel.create_webhook(
                    name="Payout Webhook",
                    avatar=await interaction.client.user.avatar.read(),
                )
            data["claim_channel"] = New_webhook

            await interaction.client.payouts.update_config(data)
            interaction.client.payouts.config_cache[interaction.guild.id][
                "claim_channel"
            ] = New_webhook

            embed = await get_success_embed(
                f"Payouts Claim Channel changed from {channel} to {view.value.mention}"
            )
            await view.interaction.edit_original_response(
                content=None, embed=embed, view=None
            )
            embed = await update_payouts_embed(self.interaction, data)
            try:
                await interaction.message.edit(embed=embed)
            except Exception:
                pass

    @discord.ui.button(
        label="Queue Channel",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_channel:1073908465405268029>",
        row=2,
    )
    async def modify_queue_channel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.guild.me.guild_permissions.manage_webhooks is False:
            embed = await get_warning_embed(
                "I do not have the `Manage Webhooks` permission, please give me the permission and try again."
            )
            return await interaction.response.send_message(embed=embed)
        data = await interaction.client.payouts.get_config(interaction.guild.id)
        view = Dropdown_Channel(interaction)
        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()
        if view.value is None:
            embed = await get_warning_embed("Dropdown timed out, please retry.")
            return await interaction.edit_original_response(
                content=None, embed=embed, view=None
            )
        else:
            channel = interaction.guild.get_channel(view.value.id)
            New_webhook = None

            for webhook in await channel.webhooks():
                webhook: discord.Webhook = webhook
                if webhook.user.id == interaction.client.user.id:
                    New_webhook = webhook
                    break
            if New_webhook is None:
                New_webhook = await channel.create_webhook(
                    name="Payout Webhook",
                    avatar=await interaction.client.user.avatar.read(),
                )

            data["claimed_channel"] = New_webhook
            await interaction.client.payouts.update_config(data)
            interaction.client.payouts.config_cache[interaction.guild.id][
                "claimed_channel"
            ] = New_webhook.id

            embed = await get_success_embed(
                f"Payouts Queue Channel changed from {channel} to {view.value.mention}"
            )
            await interaction.edit_original_response(
                content=None, embed=embed, view=None
            )
            embed = await update_payouts_embed(self.interaction, data)
            try:
                await interaction.message.edit(embed=embed)
            except Exception:
                pass

    @discord.ui.button(
        label="Payouts Channel",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_channel:1073908465405268029>",
        row=2,
    )
    async def payouts_channel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        data = await interaction.client.payouts.get_config(interaction.guild.id)
        view = Dropdown_Channel(interaction)
        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()
        if view.value is None:
            embed = await get_warning_embed("Dropdown timed out, please retry.")
            return await interaction.edit_original_response(
                content=None, embed=embed, view=None
            )
        else:
            channel = data["payout_channel"]
            if channel is None:
                channel = "`None`"
            else:
                channel = f"<#{channel}>"
            if (
                data["payout_channel"] is None
                or data["payout_channel"] != view.value.id
            ):
                data["payout_channel"] = view.value.id

                await interaction.client.payouts.update_config(data)
                interaction.client.payouts.config_cache[interaction.guild.id][
                    "payout_channel"
                ] = view.value.id

                embed = await get_success_embed(
                    f"Payouts Channel changed from {channel} to {view.value.mention}"
                )
                await interaction.edit_original_response(
                    content=None, embed=embed, view=None
                )
                embed = await update_payouts_embed(self.interaction, data)
                try:
                    await interaction.message.edit(embed=embed)
                except Exception:
                    pass
            else:
                embed = await get_error_embed(
                    f"Payouts Channel was already set to {channel}"
                )
                return await interaction.edit_original_response(
                    content=None, embed=embed, view=None
                )

    @discord.ui.button(
        label="Logs Channel",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_channel:1073908465405268029>",
        row=3,
    )
    async def logs_channel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        data = await interaction.client.payouts.get_config(interaction.guild.id)
        view = Dropdown_Channel(interaction)
        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()
        if view.value is None:
            embed = await get_warning_embed("Dropdown timed out, please retry.")
            return await interaction.edit_original_response(
                content=None, embed=embed, view=None
            )
        else:
            channel = data["log_channel"]
            if channel is None:
                channel = "`None`"
            else:
                channel = f"<#{channel}>"
            if data["log_channel"] is None or data["log_channel"] != view.value.id:
                data["log_channel"] = view.value.id

                await interaction.client.payouts.update_config(data)
                interaction.client.payouts.config_cache[interaction.guild.id][
                    "log_channel"
                ] = view.value.id

                embed = await get_success_embed(
                    f"Logs Channel changed from {channel} to {view.value.mention}"
                )
                await interaction.edit_original_response(
                    content=None, embed=embed, view=None
                )
                embed = await update_payouts_embed(self.interaction, data)
                try:
                    await interaction.message.edit(embed=embed)
                except Exception:
                    pass
            else:
                embed = await get_error_embed(
                    f"Logs Channel was already set to {channel}"
                )
                return await interaction.edit_original_response(
                    content=None, embed=embed, view=None
                )

    @discord.ui.button(
        label="Claim Time",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_clock:1150836621890031697>",
        row=3,
    )
    async def claim_time(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        data = await interaction.client.payouts.get_config(interaction.guild.id)
        modal = General_Modal("Claim Time Modal", interaction=interaction)
        modal.question = discord.ui.TextInput(
            label="Enter New Claim Time",
            placeholder="Enter New Claim Time like 1h45m",
            min_length=1,
            max_length=10,
        )
        modal.value = None
        modal.add_item(modal.question)
        await interaction.response.send_modal(modal)

        await modal.wait()
        if modal.value:
            time = await TimeConverter().convert(
                modal.interaction, modal.question.value
            )
            if time < 3600:
                return await modal.interaction.response.send_message(
                    embed=await get_error_embed(
                        "Claim time must be greater than 1 hour"
                    ),
                    ephemeral=True,
                )
            data["default_claim_time"] = time

            await interaction.client.payouts.update_config(data)
            interaction.client.payouts.config_cache[interaction.guild.id][
                "default_claim_time"
            ] = time

            embed = await get_success_embed(
                f"Successfully updated claim time to : **`{humanfriendly.format_timespan(data['default_claim_time'])}`**!"
            )
            embed = await update_payouts_embed(self.interaction, data)
            await modal.interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="Payout Manager",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_role:1073908306713780284>",
        row=4,
    )
    async def manager_role(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        data = await interaction.client.payouts.get_config(interaction.guild.id)
        view = discord.ui.View()
        view.value = False
        view.select = Role_select(
            "select new manager role", max_values=10, min_values=1, disabled=False
        )
        view.add_item(view.select)

        await interaction.response.send_message(
            content="Select a new role from the dropdown menu below",
            view=view,
            ephemeral=True,
        )
        await view.wait()

        if view.value:
            added = []
            removed = []
            for ids in view.select.values:
                if ids.id not in data["manager_roles"]:
                    data["manager_roles"].append(ids.id)
                    added.append(ids.mention)
                else:
                    data["manager_roles"].remove(ids.id)
                    removed.append(ids.mention)
            await view.select.interaction.response.edit_message(
                content=f"Suscessfully updated manager roles\nAdded: {', '.join(added)}\nRemoved: {', '.join(removed)}",
                view=None,
            )

            await interaction.client.payouts.update_config(data)
            interaction.client.payouts.config_cache[interaction.guild.id][
                "manager_roles"
            ] = data["manager_roles"]

            embed = await update_payouts_embed(self.interaction, data)
            try:
                await interaction.message.edit(embed=embed)
            except Exception:
                pass
        else:
            await interaction.edit_original_response(
                content="No role selected", view=None
            )

    @discord.ui.button(
        label="Staff Roles",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_role:1073908306713780284>",
        row=4,
    )
    async def event_managers(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        data = await interaction.client.payouts.get_config(interaction.guild.id)
        view = discord.ui.View()
        view.value = False
        view.select = Role_select(
            "select new event manager role", max_values=10, min_values=1, disabled=False
        )
        view.add_item(view.select)

        await interaction.response.send_message(
            content="Select a new role from the dropdown menu below",
            view=view,
            ephemeral=True,
        )
        await view.wait()

        if view.value:
            added = []
            removed = []
            for ids in view.select.values:
                if ids.id not in data["event_manager_roles"]:
                    data["event_manager_roles"].append(ids.id)
                    added.append(ids.mention)
                else:
                    data["event_manager_roles"].remove(ids.id)
                    removed.append(ids.mention)
            await view.select.interaction.response.edit_message(
                content=f"Suscessfully updated event manager roles\nAdded: {', '.join(added)}\nRemoved: {', '.join(removed)}",
                view=None,
            )

            await interaction.client.payouts.update_config(data)
            interaction.client.payouts.config_cache[interaction.guild.id][
                "event_manager_roles"
            ] = data["event_manager_roles"]
            embed = await update_payouts_embed(self.interaction, data)
            try:
                await interaction.message.edit(embed=embed)
            except Exception:
                pass
        else:
            await interaction.edit_original_response(
                content="No role selected", view=None
            )

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.interaction.user.id:
            warning = await get_invisible_embed("This is not for you")
            return await interaction.response.send_message(
                embed=warning, ephemeral=True
            )
        return True

    async def on_timeout(self):
        for button in self.children:
            button.disabled = True

        await self.message.edit(view=self)


class Payout_claim(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.cd = app_commands.Cooldown(1, 15)

    async def interaction_check(self, interaction: discord.Interaction):
        retry_after = self.cd.update_rate_limit()
        if retry_after:
            raise ButtonCooldown(retry_after)
        return True

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item
    ):
        if isinstance(error, ButtonCooldown):
            seconds = int(error.retry_after)
            unit = "second" if seconds == 1 else "seconds"
            await interaction.response.send_message(
                f"You're on cooldown for {seconds} {unit}!", ephemeral=True
            )
        else:
            await super().on_error(interaction, error, item)

    @discord.ui.button(
        label="Claim", style=discord.ButtonStyle.green, custom_id="payout:claim"
    )
    async def payout_claim(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        loading_embed = discord.Embed(
            description="<a:loading:998834454292344842> | Processing claim...",
            color=discord.Color.yellow(),
        )
        await interaction.response.send_message(embed=loading_embed, ephemeral=True)

        data = await interaction.client.payouts.unclaimed.find(interaction.message.id)
        if not data:
            return await interaction.edit_original_response(
                embed=discord.Embed(
                    description="<:octane_no:1019957208466862120> | This payout has already been claimed or invalid",
                    color=discord.Color.red(),
                )
            )

        if data["claimed"] is True:
            return await interaction.edit_original_response(
                embed=discord.Embed(
                    description="<:octane_no:1019957208466862120> | This payout has already been claimed or invalid",
                    color=discord.Color.red(),
                )
            )

        if interaction.user.id != data["winner"]:
            await interaction.edit_original_response(
                embed=discord.Embed(
                    description="<:octane_no:1019957208466862120> | You are not the winner of this payout",
                    color=discord.Color.red(),
                )
            )
            return

        data["claimed"] = True
        await interaction.client.payouts.unclaimed.update(data)

        payout_config = await interaction.client.payouts.get_config(
            interaction.guild.id
        )

        if not isinstance(
            payout_config["claimed_channel"], discord.Webhook
        ) or not isinstance(payout_config["claim_channel"], discord.Webhook):
            try:
                payout_config[
                    "claimed_channel"
                ] = await interaction.client.fetch_webhook(
                    payout_config["claimed_channel"]
                )
                payout_config["claim_channel"] = await interaction.client.fetch_webhook(
                    payout_config["claim_channel"]
                )
            except Exception as e:
                print(e)
                return await interaction.edit_original_response(
                    embed=discord.Embed(
                        description="<:octane_no:1019957208466862120> | Invalid webhook",
                        color=discord.Color.red(),
                    )
                )

        queue_webhook = payout_config["claimed_channel"]
        claim_webhook = payout_config["claim_channel"]

        queue_embed = interaction.message.embeds[0]
        current_embed = interaction.message.embeds[0]
        current_embed.title = "Payout Claimed"
        queue_embed.title = "Payout Queued"

        await interaction.edit_original_response(
            content=None,
            embed=discord.Embed(
                description="<:octane_yes:1019957051721535618> | Sucessfully claimed payout",
                color=0x2B2D31,
            ),
        )

        view = Payout_Buttton()
        view.add_item(
            discord.ui.Button(
                label="Event Message",
                style=discord.ButtonStyle.url,
                disabled=False,
                url=f"https://discord.com/channels/{interaction.guild.id}/{data['channel']}/{data['winner_message_id']}",
                emoji="<:tgk_link:1105189183523401828>",
            )
        )
        queue_message: discord.Message = await queue_webhook.send(
            embed=queue_embed, view=view, wait=True
        )
        pending_data = data
        pending_data["_id"] = queue_message.id
        pending_data["claimed_at"] = datetime.datetime.now()
        await interaction.client.payouts.claimed.insert(pending_data)
        await interaction.client.payouts.unclaimed.delete(interaction.message.id)

        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="Event Message",
                style=discord.ButtonStyle.url,
                disabled=False,
                url=f"https://discord.com/channels/{interaction.guild.id}/{data['channel']}/{data['winner_message_id']}",
                emoji="<:tgk_link:1105189183523401828>",
            )
        )
        view.add_item(
            discord.ui.Button(
                label="Queue Message",
                style=discord.ButtonStyle.url,
                disabled=False,
                url=queue_message.jump_url,
                emoji="<:tgk_link:1105189183523401828>",
            )
        )

        await claim_webhook.edit_message(
            interaction.message.id, embed=current_embed, view=view
        )
        interaction.client.dispatch(
            "payout_claim", interaction.message, interaction.user
        )
        interaction.client.dispatch("payout_pending", queue_message)

    @discord.ui.button(
        label="Cancel", style=discord.ButtonStyle.red, custom_id="payout:cancel"
    )
    async def payout_cancel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        payout_data = await interaction.client.payouts.unclaimed.find(
            interaction.message.id
        )
        if not payout_data:
            return await interaction.edit_original_response(
                embed=discord.Embed(
                    description="<:octane_no:1019957208466862120> | This payout has already been claimed or invalid",
                    color=discord.Color.red(),
                )
            )

        config = await interaction.client.payouts.get_config(interaction.guild.id)
        if payout_data["set_by"] != interaction.user.id:
            config = await interaction.client.payouts.get_config(interaction.guild.id)
            user_roles = [role.id for role in interaction.user.roles]
            authorized_roles = set(config["event_manager_roles"]) | set(
                config["manager_roles"]
            )

            if not set(user_roles) & authorized_roles:
                return

        modal = General_Modal("Reason for cancelling payout?", interaction)
        modal.reason = discord.ui.TextInput(
            label="Reason",
            placeholder="Reason for cancelling payout",
            min_length=3,
            max_length=100,
            required=True,
        )
        modal.add_item(modal.reason)

        await interaction.response.send_modal(modal)

        await modal.wait()
        if modal.value:
            loading_embed = discord.Embed(
                description="<a:loading:998834454292344842> | Processing claim...",
                color=discord.Color.yellow(),
            )
            await modal.interaction.response.send_message(
                embed=loading_embed, ephemeral=True
            )

            embed = interaction.message.embeds[0]
            embed.title = "Payout Cancelled"
            embed.add_field(
                name="Rejected",
                value=f"<:nat_replycont:1146496789361479741> **Reason:** {modal.reason.value}\n<:nat_reply:1146498277068517386>  **Rejected By**: {interaction.user.mention}",
                inline=True,
            )

            temp_view = discord.ui.View()
            temp_view.add_item(
                discord.ui.Button(
                    label="Payout Cancelled",
                    style=discord.ButtonStyle.gray,
                    emoji="<a:nat_cross:1010969491347357717>",
                    disabled=True,
                )
            )

            unclaim_webhook = config["claim_channel"]
            await unclaim_webhook.edit_message(
                interaction.message.id, embed=embed, view=temp_view
            )

            await interaction.client.payouts.unclaimed.delete(interaction.message.id)
            await modal.interaction.edit_original_response(
                embed=discord.Embed(
                    description="Sucessfully cancelled payout",
                    color=discord.Color.green(),
                )
            )


class Payout_Buttton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.cd = app_commands.Cooldown(5, 10)

    @discord.ui.button(
        label="Reject",
        style=discord.ButtonStyle.gray,
        emoji="<a:nat_cross:1010969491347357717>",
        custom_id="reject",
    )
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = General_Modal("Reason for cancelling payout?", interaction)
        modal.reason = discord.ui.TextInput(
            label="Reason",
            placeholder="Reason for cancelling payout",
            min_length=3,
            max_length=100,
            required=True,
        )
        modal.add_item(modal.reason)

        await interaction.response.send_modal(modal)
        await modal.wait()
        if modal.value is None or modal.value is False:
            return

        data = await interaction.client.payouts.claimed.find(interaction.message.id)
        embed = interaction.message.embeds[0]
        embed.title = "Payout Rejected"
        embed.add_field(
            name="Rejected",
            value=f"<:nat_replycont:1146496789361479741> **Reason:** {modal.reason.value}\n<:nat_reply:1146498277068517386>  **Rejected By**: {interaction.user.mention}",
            inline=True,
        )

        edit_view = discord.ui.View()
        edit_view.add_item(
            discord.ui.Button(
                label="Payout Denied",
                style=discord.ButtonStyle.gray,
                disabled=True,
                emoji="<a:nat_cross:1010969491347357717>",
            )
        )

        config = await interaction.client.payouts.get_config(interaction.guild.id)
        claimed_webhook: discord.Webhook = config["claimed_channel"]

        await modal.interaction.response.edit_message(embed=embed, view=edit_view)
        await claimed_webhook.edit_message(
            interaction.message.id, embed=embed, view=edit_view
        )
        await interaction.client.payouts.claimed.delete(data["_id"])

    @discord.ui.button(
        label="Manual Verification",
        style=discord.ButtonStyle.gray,
        emoji="<:caution:1122473257338151003>",
        custom_id="manual_verification",
        disabled=False,
    )
    async def manual_verification(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        view: General_Modal = General_Modal(
            title="Manual Verification", interaction=interaction
        )
        view.msg = discord.ui.TextInput(
            label="Message Link",
            placeholder="Enter the message link of te confirmation message",
            max_length=100,
            required=True,
            style=discord.TextStyle.long,
        )
        view.add_item(view.msg)

        await interaction.response.send_modal(view)
        await view.wait()
        if not view.value:
            return
        msg_link = view.msg.value
        await view.interaction.response.send_message("Verifying...", ephemeral=True)
        data = await interaction.client.payouts.claimed.find(interaction.message.id)
        config = await interaction.client.payouts.get_config(interaction.guild.id)

        claimed_webhook: discord.Webhook = config["claimed_channel"]
        if isinstance(claimed_webhook, int):
            claimed_webhook = await interaction.client.fetch_webhook(claimed_webhook)

        try:
            msg_id = int(msg_link.split("/")[-1])
            msg_channel = int(msg_link.split("/")[-2])
            channel = interaction.guild.get_channel(msg_channel)
            message = await channel.fetch_message(msg_id)

            if message.author.id != 270904126974590976:
                raise Exception("Invalid Message Link")
            if len(message.embeds) <= 0:
                raise Exception("Invalid Message Link")

            embed = message.embeds[0]
            if not embed.description.startswith("Successfully paid"):
                raise Exception("Invalid Message Link")

            winner = message.guild.get_member(
                int(
                    embed.description.split(" ")[2]
                    .replace("<", "")
                    .replace(">", "")
                    .replace("!", "")
                    .replace("@", "")
                )
            )
            if not winner:
                raise Exception("Invalid Message Link")
            if winner.id != data["winner"]:
                return await view.interaction.edit_original_response(
                    content="The winner of the provided message is not the winner of this payout"
                )

            items = re.findall(r"\*\*(.*?)\*\*", embed.description)[0]
            if "⏣" in items:
                items = int(items.replace("⏣", "").replace(",", "", 100))
                if items == data["prize"]:
                    await view.interaction.edit_original_response(
                        content="Verified Successfully"
                    )
                else:
                    embed = discord.Embed(
                        description="The prize of the provided message is not the prize of this payout",
                        color=discord.Color.red(),
                    )
                    embed.description += f"\n\n**Prize Found:** {items}\n**Payout Prize:** {data['prize']}"
                    return await view.interaction.edit_original_response(
                        content=None, embed=embed
                    )
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
                    item_found.lower() == data["item"].lower()
                    and quantity_found == data["prize"]
                ):
                    await view.interaction.edit_original_response(
                        content="Verified Successfully"
                    )
                else:
                    embed = discord.Embed(
                        description="The prize of the provided message is not the prize of this payout",
                        color=discord.Color.red(),
                    )
                    embed.description += f"\n\n**Prize Found:** `{quantity_found}x` {item_found}\n**Payout Prize:** `{data['prize']}x` {data['item']}"
                    return await view.interaction.edit_original_response(
                        content=None, embed=embed
                    )

            Payout_embed = interaction.message.embeds[0]
            Payout_embed.title = "Successfully Paid"
            Payout_embed.add_field(
                name="Payout Location",
                value=f"<:nat_reply:1146498277068517386> [Click Here]({message.jump_url})",
                inline=True,
            )

            view = discord.ui.View()
            view.add_item(
                discord.ui.Button(
                    label="Paid at",
                    style=discord.ButtonStyle.url,
                    url=message.jump_url,
                    emoji="<:tgk_link:1105189183523401828>",
                )
            )
            await claimed_webhook.edit_message(
                interaction.message.id, embed=Payout_embed, view=view
            )

            config = await interaction.client.payouts.get_config(interaction.guild.id)
            claimed_webhook: discord.Webhook = config["claimed_channel"]
            await claimed_webhook.edit_message(
                interaction.message.id, embed=Payout_embed, view=view
            )
            interaction.client.dispatch(
                "payout_paid",
                message,
                interaction.user,
                interaction.guild.get_member(data["winner"]),
                f"{data['prize']}x{data['item']}",
            )
            await interaction.client.payouts.claimed.delete(data["_id"])

        except Exception as e:
            print(e)
            return await view.interaction.followup.send(content=e)

    async def on_error(
        self, interaction: Interaction, error: Exception, item: discord.ui.Item
    ):
        if isinstance(error, ButtonCooldown):
            seconds = int(error.retry_after)
            unit = "second" if seconds == 1 else "seconds"
            return await interaction.response.send_message(
                f"You're on cooldown for {seconds} {unit}!", ephemeral=True
            )
        try:
            await interaction.response.send_message(f"Error: {error}", ephemeral=True)
        except Exception:
            if interaction.response.is_done():
                await interaction.followup.send(f"Error: {error}", ephemeral=True)
            else:
                await interaction.response.send_message(
                    f"Error: {error}", ephemeral=True
                )

    async def interaction_check(self, interaction: Interaction):
        config = await interaction.client.payouts.get_config(interaction.guild.id)
        roles = [role.id for role in interaction.user.roles]
        if set(roles) & set(config["manager_roles"]):
            retry_after = self.cd.update_rate_limit()
            if retry_after:
                raise ButtonCooldown(retry_after)
            return True
        else:
            embed = discord.Embed(
                title="Error",
                description="You don't have permission to use this button",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
