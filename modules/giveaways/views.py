import discord
from discord.ext import commands
from discord import Interaction, SelectOption
from discord.interactions import Interaction
from discord.ui import View, Button, Select
from discord.ui.item import Item

from typing import Any, List, Union
from amari import User

from utils.views.selects import Role_select, Channel_select, Select_General
from utils.views.modal import General_Modal
from utils.views.paginator import Paginator
from .db import GiveawayConfig as GConfig
from .db import Giveaways_Backend, GiveawayData

class Giveaway(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    async def on_error(self, interaction: Interaction, error: Exception, item: Item):
        return await interaction.followup.send(content=f"An error occured: {error}", ephemeral=True)
    
    @discord.ui.button(emoji="<a:tgk_tadaa:806631994770849843>", style=discord.ButtonStyle.gray, custom_id="giveaway:Join")
    async def _join(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True, ephemeral=True)
        data: GiveawayData = await interaction.client.giveaway.get_giveaway(interaction.message)
        if data is None: await interaction.followup.send("This giveaway is not available anymore.", ephemeral=True)
        config = await interaction.client.giveaway.get_config(interaction.guild)

        if interaction.user.id in data['banned']:
            await interaction.followup.send("You have been manually blacklisted from joining this giveaway. Reach out to the server staff for more information.", ephemeral=True)
            return
        
        user_roles = [role.id for role in interaction.user.roles]
        if (set(user_roles) & set(config["blacklist"])): 
            embed = discord.Embed(description="Unable to join the giveawy due to blacklisted role.", color=discord.Color.red())
            return await interaction.followup.send(embed=embed, ephemeral=True)

        if str(interaction.user.id) in data['entries'].keys():
            view = GiveawayLeave(data, interaction.user, interaction)
            embed = discord.Embed(description="You already joined this giveaway.",color=0x2b2d31)
            await interaction.followup.send(embed=embed, view=view)
            await view.wait()
            if view.value is True:
                self.children[1].label = f"{len(data['entries'].keys())}"
                if len(data['entries'].keys()) == 0:
                    self.children[1].label = None
                    self.children[1].disabled = True
                await interaction.followup.edit_message(message_id=interaction.message.id, view=self)
                return
        
        result = {}
        backend: Giveaways_Backend = interaction.client.giveaway
        if data['ended']: return await interaction.followup.send("This giveaway has ended.", ephemeral=True)

        if data['req_level'] or data['req_weekly']:
            amari = interaction.guild.get_member(339254240012664832)
            if amari is None:
                return await interaction.followup.send("Amari is not in this server. Please contact the server owner to add Amari to the server.", ephemeral=True)
            user_level: User = await backend.get_level(interaction.user, interaction.guild)

            if not isinstance(user_level, User):
                return await interaction.followup.send("Unable to fetch your level data. Please contact the Bot owner.", ephemeral=True)

            if data['req_level']:
                if user_level.level >= data['req_level']:
                    pass
                else:
                    result['level'] = f"You don't have the required level to join this giveaway.\n> `Required levels: {data['req_level']}`"

            if data['req_weekly']:
                if user_level.weeklyexp >= data['req_weekly']:
                    pass
                else:
                    result['weekly'] = "You don't have the required weekly XP to join this giveaway.\n> `Required weekly XP: {}`".format(data['req_weekly'])
        
        if data['req_roles']:
            if set(data['req_roles']) <= set(user_roles):
                pass
            else:
                missing_roles = set(data['req_roles']) - set(user_roles)
                missing_roles = [f"<@&{role}>" for role in missing_roles]
                result['roles'] = f"You don't have the required role(s) to join this giveaway.\n> Missing roles: {', '.join(missing_roles)}"

        if data['channel_messages'] != {}:
            channel = str(data['channel_messages']['channel'])
            user_data = data['channel_messages']['users'][str(interaction.user.id)] if str(interaction.user.id) in data['channel_messages']['users'].keys() else None
            try:
                if user_data is None:
                    result['channel'] = f"You have not completed the channel message requirement.\n> Required messages: {data['channel_messages']['count']} in <#{channel}>\n > You have sent: 0"
                elif user_data['count'] >= data['channel_messages']['count']:
                    pass
                else:
                    result['channel'] = f"You have not completed the channel message requirement.\n> Required messages: {data['channel_messages']['count']} in <#{channel}>\n > You have sent: {user_data['count']}"
            except Exception as e:
                print(e)
                pass

        bypassed = False    
        if len(result.keys()) > 0:
            if data['bypass_role'] and (set(user_roles) & set(data['bypass_role'])):
                bypassed = True
                pass
            elif set(user_roles) & set(config['global_bypass']):
                bypassed = True
                pass
            else:
                embed = discord.Embed(description="", title="You Failed to meet the following requriements")
                i = 1
                for key, value in result.items():
                    embed.description += f"{i}. {value}\n"
                    i += 1
                embed.color = discord.Color.red()
                return await interaction.followup.send(embed=embed, ephemeral=True)
        
        entries = 1
        for key, value in config['multipliers'].items():
            if int(key) in user_roles:
                entries += value
        
        data['entries'][str(interaction.user.id)] = entries
        await interaction.client.giveaway.update_giveaway(interaction.message, data)
        embed = discord.Embed(description="You have successfully joined the giveaway.", color=discord.Color.green())
        if bypassed:
            embed.description += "\nYou have bypassed the requirements due to your bypass role."       
        await interaction.followup.send(embed=embed, ephemeral=True)

        self.children[1].label = f"{len(data['entries'].keys())}"
        if self.children[1].disabled:
            self.children[1].disabled = False
        await interaction.followup.edit_message(message_id=interaction.message.id, view=self)

    @discord.ui.button(label=None, style=discord.ButtonStyle.gray, emoji="<:tgk_people_group:1168173646796300420>", custom_id="giveaway:Entries", disabled=True)
    async def _entries(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = await interaction.client.giveaway.get_giveaway(interaction.message)
        if data is None: return await interaction.followup.send("This giveaway is not available anymore/invalid.", ephemeral=True)
        if len(data['entries'].keys()) == 0: return await interaction.response.send_message("No one has joined this giveaway yet.", ephemeral=True)
        entries = data['entries']
        entries = sorted(entries.items(), key=lambda x: x[1], reverse=True)
        entries = [entries[i:i + 10] for i in range(0, len(entries), 10)]
        pages = []
        i = 1
        for page in entries:
            embed = discord.Embed(title="Giveaway Participants", description="", color=0x2b2d31)
            for user in page:
                embed.description += f"{i}. <@{user[0]}>\n"                
                i += 1
            try:
                embed.set_footer(text=f"Your Entries: {data['entries'][str(interaction.user.id)]}")
            except:
                pass
            pages.append(embed)
        
        await Paginator(interaction=interaction, pages=pages, ephemeral=True).start(embeded=True, quick_navigation=False)

class GiveawayLeave(View):
    def __init__(self, data: dict, user: discord.Member, interaction: discord.Interaction):
        self.data = data
        self.user = user
        self.interaction = interaction
        self.value = None
        super().__init__(timeout=30)
    
    async def on_timeout(self):
        await self.interaction.delete_original_response()
    
    @discord.ui.button(label="View your chances", style=discord.ButtonStyle.gray, emoji="<:tgk_entries:1124995375548338176>", custom_id="giveaway:Chances")
    async def _chances(self, interaction: discord.Interaction, button: discord.ui.Button):
        entries: List[int] = []
        for key, value in self.data['entries'].items():
            if int(key) in entries: continue
            entries.extend([int(key)] * value)
        percentage = round(entries.count(self.user.id) / len(entries) * 100, 2)
        embed = discord.Embed(description=f"You have a *{percentage}%* chance of winning this giveaway.", color=0x2b2d31)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Leave", style=discord.ButtonStyle.gray, emoji="<:tgk_pepeexit:790189030569934849>", custom_id="giveaway:Leave")
    async def _leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            del self.data['entries'][str(self.user.id)]
            await interaction.client.giveaway.update_giveaway(interaction.message, self.data)
        except:
            pass
        await interaction.response.edit_message(content="You have successfully left the giveaway.", view=None, delete_after=10, embed=None)
        self.value = True
        self.stop()

class GiveawayConfigView(View):
    def __init__(self, data: dict, user: discord.Member, message: discord.Message=None, dropdown: Item=None):
        self.data = data
        self.user = user
        self.message = message
        super().__init__(timeout=120)
        if dropdown is not None:
            dropdown.row = 0
            self.add_item(dropdown)     

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id == self.user.id:
            return True
        else:
            return False
    
    async def update_embed(self, interaction: discord.Interaction, giveaway_data: GConfig) -> discord.Embed:
        embed = await interaction.client.giveaway.get_config_embed(giveaway_data, interaction.guild)
        return embed
        
    
    @discord.ui.button(label="Manager Roles", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>", custom_id="giveaway:ManagerRoles", row=1)
    async def _manager_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = View()
        view.value = None
        view.select = Role_select(placeholder="Please select the roles you want to add/remove.", min_values=1, max_values=10)
        view.add_item(view.select)
        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()

        if view.value is None:
            return await interaction.delete_original_response()
        added = ""
        removed = ""
        for role in view.select.values:
            if role.id not in self.data['manager_roles']:
                self.data['manager_roles'].append(role.id)
                added += f"<@&{role.id}> "
            else:
                self.data['manager_roles'].remove(role.id)
                removed += f"<@&{role.id}> "
        await view.select.interaction.response.edit_message(content=f"Added: {added}\nRemoved: {removed}", view=None)
        await interaction.delete_original_response()
        await interaction.message.edit(embed=await self.update_embed(interaction, self.data))
        await interaction.client.giveaway.update_config(interaction.guild, self.data)
    
    @discord.ui.button(label="Blacklist", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>", custom_id="giveaway:Blacklist", row=1)
    async def _blacklist(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = View()
        view.value = None
        view.select = Role_select(placeholder="Please select the roles you want to add/remove.", min_values=1, max_values=10)
        view.add_item(view.select)
        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()

        if view.value is None:
            return await interaction.delete_original_response()
        added = ""
        removed = ""
        for role in view.select.values:
            if role.id not in self.data['blacklist']:
                self.data['blacklist'].append(role.id)
                added += f"<@&{role.id}> "
            else:
                self.data['blacklist'].remove(role.id)
                removed += f"<@&{role.id}> "
        await view.select.interaction.response.edit_message(content=f"Added: {added}\nRemoved: {removed}", view=None)
        await interaction.delete_original_response()
        await interaction.message.edit(embed=await self.update_embed(interaction, self.data))
        await interaction.client.giveaway.update_config(interaction.guild, self.data)
    
    @discord.ui.button(label="Global Bypass", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>", custom_id="giveaway:GlobalBypass", row=1)
    async def _global_bypass(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = View()
        view.value = None
        view.select = Role_select(placeholder="Please select the roles you want to add/remove.", min_values=1, max_values=10)
        view.add_item(view.select)
        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()

        if view.value is None:
            return await interaction.delete_original_response()
        added = ""
        removed = ""

        for role in view.select.values:
            if role.id not in self.data['global_bypass']:
                self.data['global_bypass'].append(role.id)
                added += f"<@&{role.id}> "
            else:
                self.data['global_bypass'].remove(role.id)
                removed += f"<@&{role.id}> "
        await view.select.interaction.response.edit_message(content=f"Added: {added}\nRemoved: {removed}", view=None)
        await interaction.delete_original_response()
        await interaction.message.edit(embed=await self.update_embed(interaction, self.data))
        await interaction.client.giveaway.update_config(interaction.guild, self.data)

    @discord.ui.button(label="Logging Channel", style=discord.ButtonStyle.gray, emoji="<:tgk_channel:1073908465405268029>", custom_id="giveaway:LoggingChannel", row=2)
    async def _logging_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = View()
        view.value = None
        view.select = Channel_select(placeholder="Please select the channel you want to set as logging channel.", min_values=1, max_values=1, channel_types=[discord.ChannelType.text])
        view.add_item(view.select)
        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()

        if view.value is None:
            return await interaction.delete_original_response()
        self.data['log_channel'] = view.select.values[0].id
        await view.select.interaction.response.edit_message(content=f"Set logging channel to {view.select.values[0].mention}", view=None)
        await interaction.delete_original_response()
        await interaction.message.edit(embed=await self.update_embed(interaction, self.data))
        await interaction.client.giveaway.update_config(interaction.guild, self.data)
    
    @discord.ui.button(label="Multipliers", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>", custom_id="giveaway:Multipliers", row=2)
    async def _multipliers(self, interaction: discord.Interaction, button: discord.ui.Button):
        multi_view = View()
        multi_view.value = None
        multi_view.select = Select_General(interaction, options=[SelectOption(label="Remove", value="0"),SelectOption(label="List", value="list"),SelectOption(label="1x", value="1"), SelectOption(label="2x", value="2"), SelectOption(label="3x", value="3"), SelectOption(label="4x", value="4"), SelectOption(label="5x", value="5"), SelectOption(label="6x", value="6"), SelectOption(label="7x", value="7"), SelectOption(label="8x", value="8"), SelectOption(label="9x", value="9"), SelectOption(label="10x", value="10")], placeholder="Select the multiplier you want to set",min_values=1, max_values=1)
        multi_view.add_item(multi_view.select)
        await interaction.response.send_message(view=multi_view, ephemeral=True)
        await multi_view.wait()
        if not multi_view.value: return await interaction.delete_original_message()
        
        if multi_view.select.values[0] == "list":
            embed = discord.Embed(title="Multipliers", description="", color=0x2b2d31)
            for key, value in self.data['multipliers'].items():
                embed.description += f"<@&{key}> - {value}x\n"
            return await multi_view.select.interaction.response.edit_message(embed=embed, view=None)
        
        multiplier = int(multi_view.select.values[0])

        roles_view = View()
        roles_view.value = None
        roles_view.select = Role_select(placeholder="Select the role you want to set multiplier for", min_values=1, max_values=15)
        roles_view.add_item(roles_view.select)
        await multi_view.select.interaction.response.edit_message(view=roles_view)
        await roles_view.wait()
        if not roles_view.value: return await interaction.delete_original_message()
        roles = roles_view.select.values
        if multiplier == 0:
            for role in roles:
                    try:
                        del self.data['multipliers'][str(role.id)]
                    except KeyError:
                        pass
            await roles_view.select.interaction.response.edit_message(content=f"Removed multiplier for {', '.join([f'<@&{role.id}>' for role in roles])}", view=None)
        else:
            for role in roles:
                self.data['multipliers'][str(role.id)] = multiplier
            await roles_view.select.interaction.response.edit_message(content=f"Set multiplier for {', '.join([f'<@&{role.id}>' for role in roles])} to {multiplier}x", view=None, delete_after=5)
            await interaction.message.edit(embed=await self.update_embed(interaction, self.data))
        await interaction.client.giveaway.update_config(interaction.guild, self.data)

    @discord.ui.button(label="Embeds", style=discord.ButtonStyle.gray, emoji="<:tgk_edit:1073902428224757850>", custom_id="giveaway:DmMessage", row=2)
    async def _dm_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(description="## Supported variables List\n", color=0x2b2d31)
        embed.description += "- {prize} - The prize of the giveaway\n"
        embed.description += "- {guild} - Name of the guild\n"
        embed.description += "- {timestamp} - The timestamp of the giveaway\n"
        embed.description += "- {winner} - The winners of the giveaway\n"
        embed.description += "- {link} - The link to the giveaway message\n"        
        view = Messages(self.data, interaction.user, interaction.message)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)
class Messages(View):
    def __init__(self, data: GConfig, user: discord.Member, message: discord.Message=None):
        self.config: GConfig = data
        self.user = user
        self.message = message
        self.current_message = None
        super().__init__(timeout=120)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id == self.user.id:
            return True
        else:
            await interaction.response.send_message("You are not allowed to interact with this view.", ephemeral=True)
            return False
    
    async def on_error(self, interaction: Interaction, error: Exception, item: Item):
        raise error

    async def refreshEmbed(self, interaction: discord.Interaction, giveaway_data: GConfig) -> discord.Embed:
        embed = discord.Embed(title=self.config["messages"][self.current_message]['title'], description=self.config["messages"][self.current_message]['description'], color=self.config["messages"][self.current_message]['color'])        
        value = ""
        value += "- {prize} - The prize of the giveaway\n"
        value += "- {guild} - Name of the guild\n"
        value += "- {timestamp} - The timestamp of the giveaway\n"
        value += "- {winner} - The winners of the giveaway\n"
        value += "- {link} - The link to the giveaway message\n"
        embed.add_field(name="Supported variables List", value=value)
        return embed

    @discord.ui.select(placeholder="Select the message you want to edit", 
        options=[SelectOption(label="Giveaway Embed", value="gaw"), 
                 SelectOption(label="Dm Message", value="dm"), 
                 SelectOption(label="Host Dm Message", value="host"), 
                 SelectOption(label="End Message", value="end")
                 ],
        max_values=1, min_values=1, row=0)
    async def select(self, interaction: discord.Interaction, select: discord.ui.Select, ):
        self.current_message = select.values[0]
        child = self.children[0]
        for option in child.options:
            if option.value == self.current_message: 
                option.default=True
            else:
                option.default=False

        await interaction.response.edit_message(embed=await self.refreshEmbed(interaction=interaction, giveaway_data=self.config), view=self)

    @discord.ui.button(label="Title", style=discord.ButtonStyle.gray, emoji="<:tgk_edit:1073902428224757850>", custom_id="giveaway:Title", row=1)
    async def _setTitleModal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_message is None: return await interaction.response.send_message("Please select a message first.", ephemeral=True)
        view = General_Modal(title="Title", interaction=interaction)
        view.value = None
        view.input = discord.ui.TextInput(label="Title",placeholder="Enter the embed title", min_length=1, max_length=250, style=discord.TextStyle.short)
        if self.config['messages'][self.current_message]['title']:
            view.input.default = str(self.config['messages'][self.current_message]['title'])
        view.add_item(view.input)
        await interaction.response.send_modal(view)
        await view.wait()

        if view.value is None: return
        self.config["messages"][self.current_message]['title'] = view.input.value
        await view.interaction.response.edit_message(embed=await self.refreshEmbed(interaction, self.config), view=self)
        await interaction.client.giveaway.update_config(interaction.guild, self.config)


    @discord.ui.button(label="Description", style=discord.ButtonStyle.gray, emoji="<:tgk_edit:1073902428224757850>", custom_id="giveaway:Description", row=1)
    async def _updateDescription(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_message is None: return await interaction.response.send_message("Please select a message first.", ephemeral=True)
        view = General_Modal(title="Description", interaction=interaction)
        view.value = None
        view.input = discord.ui.TextInput(label="Description",placeholder="Enter the embed description", min_length=1, max_length=2000, style=discord.TextStyle.paragraph)
        if self.config['messages'][self.current_message]['description']:
            view.input.default = str(self.config['messages'][self.current_message]['description'])
        view.add_item(view.input)
        await interaction.response.send_modal(view)
        await view.wait()

        if view.value is None: return
        self.config["messages"][self.current_message]['description'] = view.input.value
        await view.interaction.response.edit_message(embed=await self.refreshEmbed(interaction, self.config), view=self)
        await interaction.client.giveaway.update_config(interaction.guild, self.config)

    @discord.ui.button(label="Color", style=discord.ButtonStyle.gray, emoji="<:tgk_edit:1073902428224757850>", custom_id="giveaway:Color", row=1)
    async def _updateColor(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_message is None: return await interaction.response.send_message("Please select a message first.", ephemeral=True)
        view = General_Modal(title="Color", interaction=interaction)
        view.value = None
        view.input = discord.ui.TextInput(label="Color",placeholder="Enter the embed color", min_length=1, max_length=2000, style=discord.TextStyle.short)
        if self.config['messages'][self.current_message]['color']:
            view.input.default = str(hex(self.config['messages'][self.current_message]['color'])).replace("0x", "#")
        view.add_item(view.input)
        await interaction.response.send_modal(view)
        await view.wait()

        if view.value is None: return
        try:color = discord.Color.from_str(view.input.value)
        except ValueError: return await view.interaction.response.send_message(content="Invalid color value.", view=None)

        self.config["messages"][self.current_message]['color'] = color.value
        await view.interaction.response.edit_message(embed=await self.refreshEmbed(interaction, self.config), view=self)
        await interaction.client.giveaway.update_config(interaction.guild, self.config)