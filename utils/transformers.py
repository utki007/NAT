import discord
from discord import app_commands, Interaction
from discord.ext import commands
import re

time_regex = re.compile("(?:(\d{1,5})(h|s|m|d))+?")
time_dict = {"h": 3600, "s": 1, "m": 60, "d": 86400}


class BadArgument(app_commands.AppCommandError):
    def _call__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

class TimeConverter(app_commands.Transformer, commands.Converter):

    @classmethod
    def __do_convert(cls, argument: str ) -> int:
        args = argument.lower()
        matches = re.findall(time_regex, args)
        time = 0
        for key, value in matches:
            try:
                time += time_dict[value] * float(key)
            except KeyError:
              raise BadArgument(f"{args} is not a valid time key! Use h, m, s, d")  
            except ValueError:
                raise BadArgument(f"{args} is not a number!")
        
        return int(time)

    async def transform(self, interaction: discord.Interaction, argument: str) -> int:
        try:
            return self.__do_convert(argument)
        except BadArgument as e:
            raise BadArgument(f"{argument} is not a valid time key! Use h, m, s, d") from None
        
    async def convert(self, ctx: commands.Context, argument: str) -> int:
        try:
            return self.__do_convert(argument)
        except BadArgument as e:
            raise BadArgument(f"{argument} is not a valid time key! Use h, m, s, d") from None
    
class MutipleRole(app_commands.Transformer):
    async def transform(self, interaction: Interaction, value: str,):
        try:
            og_arg = value
            value = value.split(" ")
            roles = [await commands.RoleConverter().convert(interaction, role) for role in value]
            return roles
        except Exception as e:
            raise BadArgument(f"Failed to tranform {og_arg} to a list of roles make sure to add a space between each role")

class MultipleMember(app_commands.Transformer):
    async def transform(self, interaction: Interaction, value: str,):
        try:
            og_arg = value
            value = value.split(" ")
            value = [value.replace("<", "").replace(">", "").replace("@", "").replace("!", "") for value in value]
            members = []
            for i in value:
                if i not in ["", " ", None, "None"]:
                    member = interaction.guild.get_member(int(i))
                    if not isinstance(member, discord.Member):
                        member = await interaction.guild.fetch_member(int(i))
                    if isinstance(member, discord.Member):
                        members.append(member)
            return members
        except Exception as e:
            raise BadArgument(f"Failed to tranform {og_arg} to a list of members make sure to add a space between each member")

class MutipleChannel(app_commands.Transformer):
    async def transform(self, interaction: Interaction, value: str,):
        try:
            og_arg = value
            value = value.split(" ")
            value = [value.replace("<", "").replace(">", "").replace("#", "") for value in value]
            channels = []
            for i in value:
                if i not in ["", " ", None, "None"]:
                    channel = interaction.guild.get_channel(int(i))
                    if channel is not None:
                        channels.append(channel)
        
            return channels
        except Exception as e:
            raise BadArgument(f"Failed to tranform {og_arg} to a list of channels make sure to add a space between each channel")


class DMCConverter(app_commands.Transformer):
    async def transform(self, interaction: Interaction, value: str):
        try:
            og_arg = value
            value = value.lower()
            value = value.replace("⏣", "").replace(",", "").replace("k", "e3").replace("m", "e6").replace(" mil", "e6").replace("mil", "e6").replace("b", "e9")
            if 'e' not in value:
                return int(value)
            value = value.split("e")

            if len(value) > 2: 
                raise BadArgument(f"Failed to convert {og_arg} to a valid number use k, m, b, e3, e6, e9")

            price = value[0]
            multi = int(value[1])
            price = float(price) * (10 ** multi)
            return int(price)
        except Exception as e:
            raise BadArgument(f"Failed to convert {og_arg} to a valid number use k, m, b, e3, e6, e9")