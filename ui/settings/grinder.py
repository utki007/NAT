import asyncio
import discord
from discord import Interaction, ui
from utils.views.selects import Channel_select, Role_select, Select_General
from utils.views.confirm import Confirm
from utils.views.modal import General_Modal
from utils.types import GrinderConfig, GrinderProfile
from utils.convertor import TimeConverter, DMCConverter
from utils.views.paginator import Paginator
from humanfriendly import format_timespan
from utils.embeds import get_formated_embed

class GrinderConfigPanel(ui.View):
    def __init__(self, config: GrinderConfig, user: discord.Member, message: discord.Message):
        super().__init__(timeout=120)
        self.config = config
        self.user = user
        self.message = message
    
    async def on_timeout(self):
        for chl in self.children: chl.disabled = True
        try:
            await self.message.edit(view=self)
        except discord.HTTPException:
            pass
    
    async def interaction_check(self, interaction: Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("You are not allowed to interact with this view", ephemeral=True)
            return False
        return True
    
    # async def on_error(self, interaction: Interaction, error: Exception, item: any):
    #     try:
    #         await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)
    #     except:
    #         await interaction.followup.send(f"An error occurred: {error}", ephemeral=True)
        
    @ui.button(label="Payment Channel", style=discord.ButtonStyle.gray, emoji="<:tgk_channel:1073908465405268029>")
    async def payout_channel(self, interaction: Interaction, button: ui.Button):
        view = discord.ui.View()
        view.channel_select = Channel_select(placeholder="Select your payment channel", min_values=1, max_values=1, channel_types=[discord.ChannelType.text])
        view.add_item(view.channel_select)
        await interaction.response.send_message(view=view, ephemeral=True)

        await view.wait()
        if view.channel_select.value is None or view.channel_select.value is False:
            return await interaction.delete_original_response()
        
        new_channel = view.channel_select.values[0]
        if new_channel.id == self.config["payment_channel"]: self.config["payment_channel"] = None
        else: self.config["payment_channel"] = new_channel.id
        await interaction.client.grinder.update_config(interaction.guild, self.config)        
        await view.channel_select.interaction.response.edit_message(content="Payment Channel updated", view=None)
        await view.channel_select.interaction.delete_original_response()
        await self.message.edit(embed=await interaction.client.grinder.get_config_embed(interaction.guild, self.config), view=self)        

    @ui.button(label="Manager Roles", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>")
    async def manager_roles(self, interaction: Interaction, button: ui.Button):
        view = discord.ui.View()
        view.value = None
        view.role_select = Role_select(placeholder="Select your manager roles", min_values=1, max_values=5)
        view.add_item(view.role_select)
        await interaction.response.send_message(view=view, ephemeral=True)

        await view.wait()

        if view.value is None or view.value is False:
            return await interaction.delete_original_response()
        
        add_roles = ""
        remove_roles = ""

        for role in view.role_select.values:
            if role not in self.config["manager_roles"]:
                self.config["manager_roles"].append(role.id)
                add_roles += f"{role.mention} "
            else:
                self.config["manager_roles"].remove(role.id)
                remove_roles += f"{role.mention} "
        await interaction.client.grinder.update_config(interaction.guild, self.config)
        await view.role_select.interaction.response.edit_message(content=f"Added Roles: {add_roles}\nRemoved Roles: {remove_roles}", view=None)
        await view.role_select.interaction.delete_original_response()

        await self.message.edit(embed=await interaction.client.grinder.get_config_embed(interaction.guild, self.config), view=self)
    
    @ui.button(label="Trail", style=discord.ButtonStyle.gray, emoji="<:tgk_partner:1072850156355072033>", row=1)
    async def trail(self, interaction: Interaction, button: ui.Button):
        modal = General_Modal(title="Trail Configuration", interaction=interaction)
        modal.duration = ui.TextInput(custom_id="duration", label="Duration",placeholder="Enter the duration of the trail", max_length=50, style=discord.TextStyle.short)

        modal.add_item(modal.duration)
        await interaction.response.send_modal(modal)
        await modal.wait()

        if modal.value is None or modal.value is False:
            return await interaction.delete_original_response()
        
        duration = await TimeConverter().convert(modal.interaction, modal.duration.value)

        role_view = discord.ui.View()
        role_view.value = None
        role_view.select = Role_select(placeholder="Select role for the trail", min_values=1, max_values=1)
        role_view.add_item(role_view.select)

        await modal.interaction.response.send_message(view=role_view, ephemeral=True)
        await role_view.wait()

        if role_view.value is None or role_view.value is False:
            return await interaction.delete_original_response()
        
        role = role_view.select.values[0]

        args = await get_formated_embed(["Role", "Duration"])
        embed = discord.Embed(color=0x2b2d31, description="")
        embed.description += f"### <:tgk_message_reload:1073908878774906940> `Review Trail`"
        embed.description += "\n<:tgk_blank:1072224743266193459>\n"
        embed.description += f"{args['Role']}{role.mention}\n"
        embed.description += f"{args['Duration']}{format_timespan(duration)}\n\n"

        confirm_view = Confirm(user=interaction.user, timeout=30)
        await role_view.select.interaction.response.edit_message(embed=embed, view=confirm_view)
        await confirm_view.wait()

        if confirm_view.value is None or confirm_view.value is False:
            return await interaction.delete_original_response()
        
        self.config["trail"] = {
            "role": role.id,
            "duration": duration
        }
        await interaction.client.grinder.update_config(interaction.guild, self.config)
        embed.color = discord.Color.green()
        confirm_view.children[0].style = discord.ButtonStyle.green
        confirm_view.children[0].disabled = True
        confirm_view.children[1].disabled = True

        await confirm_view.interaction.response.edit_message(embed=embed, view=confirm_view)
        await asyncio.sleep(1.5)
        await confirm_view.interaction.delete_original_response()
    
    @ui.button(label="Base Role", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>", row=1)
    async def base_role(self, interaction: Interaction, button: ui.Button):
        view = discord.ui.View()
        view.value = None
        view.role_select = Role_select(placeholder="Select your base role", min_values=1, max_values=1)
        view.add_item(view.role_select)
        await interaction.response.send_message(view=view, ephemeral=True)

        await view.wait()

        if view.value is None or view.value is False:
            return await interaction.delete_original_response()
        
        role = view.role_select.values[0]
        self.config["base_role"] = role.id
        await interaction.client.grinder.update_config(interaction.guild, self.config)
        await view.role_select.interaction.response.edit_message(content=f"Base Role updated to {role.mention}", view=None)
        await view.role_select.interaction.delete_original_response()
        await self.message.edit(embed=await interaction.client.grinder.get_config_embed(interaction.guild, self.config), view=self)


    @ui.button(label="Profiles", style=discord.ButtonStyle.gray, emoji="<:tgk_entries:1124995375548338176>", row=1)
    async def profiles(self, interaction: Interaction, button: ui.Button):
        op_view = discord.ui.View()
        op_view.value = None
        op_view.select = Select_General(interaction=interaction, placeholder="Select a operation", 
                        options=[
                            discord.SelectOption(label="Add Profile", value="add", emoji="<:tgk_add:1073902485959352362>", description="Add a new profile"),
                            discord.SelectOption(label="Remove Profile", value="remove", emoji="<:tgk_delete:1113517803203461222>", description="Remove a profile"),
                            discord.SelectOption(label="List Profiles", value="list", emoji="<:tgk_logging:1107652646887759973>", description="List all profiles")                            
                        ])
        op_view.add_item(op_view.select)
        await interaction.response.send_message(view=op_view, ephemeral=True)
        await op_view.wait()

        if op_view.value is None or op_view.value is False:
            return await interaction.delete_original_response()
        

        match op_view.select.values[0].lower():

            case "add":
                if len(self.config['profile']) >= self.config['max_profiles']:
                    return await op_view.select.interaction.response.send_message("You have reached the maximum number of profiles", ephemeral=True)
                
                profile_modal = General_Modal(title="Profile Creation", interaction=interaction)
                profile_modal.profile_name = ui.TextInput(custom_id="profile_name", label="Profile Name",placeholder="Enter the Profile Name Ex: Legendary Grinder (daily 3M", max_length=50, style=discord.TextStyle.short)
                profile_modal.profile_amount = ui.TextInput(custom_id="profile_amount", label="Grind Amount",placeholder="Enter the Grind Amount Ex: 3M", max_length=10, style=discord.TextStyle.short)
                profile_modal.profile_time = ui.TextInput(custom_id="profile_time", label="Frquency",placeholder="Enter the Frequency of the grind Ex: 1d/1w", max_length=50, style=discord.TextStyle.short)

                profile_modal.add_item(profile_modal.profile_name)
                profile_modal.add_item(profile_modal.profile_amount)
                profile_modal.add_item(profile_modal.profile_time)

                await op_view.select.interaction.response.send_modal(profile_modal)

                await profile_modal.wait()
                if profile_modal.value is None or profile_modal.value is False:
                    return await interaction.delete_original_response()
                
                profile_name = profile_modal.profile_name.value
                profile_amount = int(await DMCConverter().convert(profile_modal.interaction, profile_modal.profile_amount.value))
                profile_time = int(await TimeConverter().convert(profile_modal.interaction, profile_modal.profile_time.value))

                embed = discord.Embed(color=0x2b2d31, description="")
                formated_args = await get_formated_embed(["Profile Name", "Payment", "Frquency", "Role"])

                role_view = discord.ui.View()
                role_view.value = None
                role_view.select = Role_select(placeholder="Select role for the profile", min_values=1, max_values=1)
                role_view.add_item(role_view.select)

                await profile_modal.interaction.response.edit_message(view=role_view)

                await role_view.wait()
                if role_view.value is None or role_view.value is False:
                    return await interaction.delete_original_response()
                
                profile_role = role_view.select.values[0]
                
                if str(profile_role.id) in self.config['profile'].keys():
                    await role_view.select.interaction.response.edit_message(f"This role already has a profile {self.config['profile'][str(profile_role.id)]['name']}", ephemeral=True)
                    return

                embed.description += "### <:tgk_message_reload:1073908878774906940> `Review Profile`"
                embed.description += "\n<:tgk_blank:1072224743266193459>\n"
                embed.description += f"{formated_args['Profile Name']}{profile_name}\n" 
                embed.description += f"{formated_args['Payment']}⏣ {profile_amount}\n"
                embed.description += f"{formated_args['Frquency']}{format_timespan(profile_time)}\n"
                embed.description += f"{formated_args['Role']}{profile_role.mention}\n\n"
                embed.description += "<:tgk_hint:1206282482744561744> Use buttons below to confirm or cancel the operation"

                confirm_view = Confirm(user=interaction.user, timeout=30)
                await role_view.select.interaction.response.edit_message(embed=embed, view=confirm_view)

                await confirm_view.wait()
                if confirm_view.value is None or confirm_view.value is False:
                    return await interaction.delete_original_response()
                
                self.config['profile'][str(profile_role.id)] = GrinderProfile(
                    name=profile_name,
                    role=profile_role.id,
                    payment=profile_amount,
                    frequency=profile_time
                )

                await interaction.client.grinder.update_config(interaction.guild, self.config)
                embed.color = discord.Color.green()
                confirm_view.children[0].style = discord.ButtonStyle.green
                confirm_view.children[0].disabled = True
                confirm_view.children[1].disabled = True

                await confirm_view.interaction.response.edit_message(embed=embed, view=confirm_view)
                await asyncio.sleep(1.5)
                await interaction.delete_original_response()

                await self.message.edit(embed=await interaction.client.grinder.get_config_embed(interaction.guild, self.config), view=self)

            case "remove":
                if len(self.config['profile']) == 0:
                    return await op_view.select.interaction.response.send_message("You don't have any profiles to remove", ephemeral=True)

                profile_select = discord.ui.View()
                profile_select.value = None
                profile_select.select = Select_General(interaction=interaction, placeholder="Select a profile to remove", max_values=len(self.config["profile"].keys()), min_values=1,options=[
                    discord.SelectOption(label=self.config['profile'][role_id]["name"], value=role_id)
                    for role_id in self.config['profile']
                ])
                profile_select.add_item(profile_select.select)

                await op_view.select.interaction.response.edit_message(view=profile_select)

                await profile_select.wait()
                if profile_select.value is None or profile_select.value is False:
                    return await interaction.delete_original_response()
                
                embed = discord.Embed(color=0x2b2d31, description="")
                embed.description += f"Are you sure you want to remove the following {','.join([self.config['profile'][role_id]['name'] for role_id in profile_select.select.values])} profiles?"
                confirm_view = Confirm(user=interaction.user, timeout=30)
                await profile_select.select.interaction.response.edit_message(embed=embed, view=confirm_view)

                await confirm_view.wait()
                if confirm_view.value is None or confirm_view.value is False:
                    return await interaction.delete_original_response()
                
                for role_id in profile_select.select.values:
                    del self.config['profile'][role_id]

                await interaction.client.grinder.update_config(interaction.guild, self.config)
                embed.color = discord.Color.green()
                confirm_view.children[0].style = discord.ButtonStyle.green
                confirm_view.children[0].disabled = True
                confirm_view.children[1].disabled = True

                await confirm_view.interaction.response.edit_message(embed=embed, view=confirm_view)
                await asyncio.sleep(1.5)
                await interaction.delete_original_response()

                await self.message.edit(embed=await interaction.client.grinder.get_config_embed(interaction.guild, self.config), view=self)

            case "list":
                if len(self.config['profile']) == 0:
                    return await op_view.select.interaction.response.send_message("You don't have any profiles", ephemeral=True)
                
                pages = []
                for key, item in self.config['profile'].items():
                    embed = discord.Embed(color=0x2b2d31, description="")
                    formated_args = await get_formated_embed(["Profile Name", "Payment", "Frquency", "Role"])
                    embed.description += f"### <:tgk_entries:1124995375548338176> `Profile` {item['name']}\n"
                    embed.description += f"{formated_args['Payment']}{item['payment']}\n"
                    embed.description += f"{formated_args['Frquency']}{item['frequency']}\n"
                    embed.description += f"{formated_args['Role']}{interaction.guild.get_role(item['role']).mention}\n\n"
                    
                    pages.append(embed)
                
                await Paginator(interaction=op_view.select.interaction, pages=pages, ephemeral=True).start(embeded=True, quick_navigation=False)


