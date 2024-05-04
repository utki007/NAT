import datetime
import io
import chat_exporter
import discord 
import re
from discord.ext import commands
import pytz
from utils.db import Document
import io
from typing import TypedDict, List, Dict

night_pattern = re.compile(r"Night ([1-9]|1[0-5])")


class NightData(TypedDict):
    NightNumber: int
    Players: Dict[discord.Member, int]

class PlayerData(TypedDict):
    user: discord.Member
    alive: bool
    death_night: int

class MafiaData(TypedDict):
    current_night: int
    players: Dict[int, PlayerData]
    MininumMessages: int
    Nights: Dict[int, NightData]

class GuildConfig(TypedDict):
    _id: int
    game_count: int
    logs_channel: int
    minimum_messages: int
    enable_logging: bool


class Mafia(commands.GroupCog):
    def __init__(self, bot):
        self.bot = bot
        self.mafia_channels: Dict[int, MafiaData] = {}
        self.mafia_inprosses: List[int] = []
        self.db = Document(self.bot.db, "mafiaConfig")
        self.disabled_guilds = []
    
    async def get_dead_plater(self, str):
        pattern = r"<@!?(\d+)>"
        matches = re.findall(pattern, str)
        return [int(match) for match in matches]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        if self.bot.user.id == 1010883367119638658:
            return
        
        if message.channel.id in self.mafia_inprosses:
            return
        if not message.guild: return
        if message.guild.id in self.disabled_guilds: return

        if message.channel.name == "mafia" and message.channel.id not in self.mafia_channels.keys():
            guildData: GuildConfig = await self.db.find(message.guild.id)
            if not guildData:
                guildData: GuildConfig = {
                    "_id": message.guild.id,
                    "game_count": 0,
                    "logs_channel": None,
                    "enable_logging": False,
                    "minimum_messages": 3
                }
                await self.db.insert(guildData)
                self.disabled_guilds.append(message.guild.id)
                return

            new_game_data: MafiaData = {
                "current_night": 1,
                "players": {},
                "MininumMessages": guildData['minimum_messages'] if guildData else 3,
                "Nights": {1: {
                    "NightNumber": 1,
                    "Players": {}
                }}
            }
            for member in message.channel.overwrites:
                if isinstance(member, discord.Member):
                    if not member.bot:
                        new_game_data['players'][member.id] = {
                            "user": member,
                            "alive": True,
                            "death_night": 0
                        }
                        new_game_data['Nights'][1]['Players'][member.id] = 0
            self.mafia_channels[message.channel.id] = new_game_data
        
        if message.channel.id in self.mafia_channels.keys():
            if message.author.id == 511786918783090688 and message.embeds != [] and isinstance(message.embeds[0].title, str):
                new_night = night_pattern.findall(message.embeds[0].title)
                if new_night != []: 
                    self.mafia_channels[message.channel.id]['current_night'] = int(new_night[0])
                    self.mafia_channels[message.channel.id]['Nights'][int(new_night[0])] = {
                        "NightNumber": int(new_night[0]),
                        "Players": {}
                    }

            if message.author.id == 511786918783090688 and message.embeds != [] and isinstance(message.embeds[0].description, str):
                if message.embeds[0].description == "Thank you all for playing! Deleting this channel in 10 seconds":
                    self.bot.dispatch("mafia_transcript", message.channel, message)
                    self.bot.dispatch("mafia_ends", self.mafia_channels[message.channel.id], message.channel)                    
                    return
            
                if message.embeds[0].title == "Currently ded:":
                    dead_players = await self.get_dead_plater(message.embeds[0].description)
                    for player in dead_players:
                        if self.mafia_channels[message.channel.id]['players'][player]['alive']:
                            self.mafia_channels[message.channel.id]['players'][player]['alive'] = False
                            self.mafia_channels[message.channel.id]['players'][player]['death_night'] = self.mafia_channels[message.channel.id]['current_night']

            if message.author.bot: return
            
            if message.author.id not in self.mafia_channels[message.channel.id]['players'].keys():
                pass
            if message.author.id not in self.mafia_channels[message.channel.id]['Nights'][self.mafia_channels[message.channel.id]['current_night']]['Players'].keys():
                self.mafia_channels[message.channel.id]['Nights'][self.mafia_channels[message.channel.id]['current_night']]['Players'][message.author.id] = 1
            else:
                self.mafia_channels[message.channel.id]['Nights'][self.mafia_channels[message.channel.id]['current_night']]['Players'][message.author.id] += 1


    @commands.Cog.listener()
    async def on_mafia_ends(self, data: MafiaData, channel: discord.TextChannel):
        self.mafia_inprosses.append(channel.id)
        
        guildData: GuildConfig = await self.db.find(channel.guild.id)
        if not guildData:
            guildData: GuildConfig = {
                "_id": channel.guild.id,
                "game_count": 0,
                "logs_channel": None,
                "enable_logging": False,
                "minimum_messages": 3                
            }
            await self.db.insert(guildData)
            return 

        if guildData['enable_logging'] == False: return

        log_channel = channel.guild.get_channel(guildData['logs_channel'])
        if not log_channel:
            return
        
        game_num = guildData['game_count'] + 1
        guildData['game_count'] = game_num
        await self.db.update(guildData)

        embed = discord.Embed(description="", color=0x2b2d31)
        for night in data['Nights'].keys():
            if len(data['Nights'][night]['Players'].keys()) == 0:
                continue
            _str = f"## Night {night} #{game_num}\n"
            for index, player in enumerate(data['Nights'][night]['Players'].keys()):
                user = channel.guild.get_member(int(player))
                if index+1 == len(data['Nights'][night]['Players'].keys()):
                    emoji = "<:nat_reply:1146498277068517386>" 
                else:
                    emoji = "<:nat_replycont:1146496789361479741>"

                _str += f"{emoji} {user.mention}: Sent {data['Nights'][night]['Players'][player]}/{data['MininumMessages']}"
                if data['Nights'][night]['Players'][player] >= data['MininumMessages']:
                    _str += " <:tgk_active:1082676793342951475>\n"
                else:
                    _str += " <:tgk_deactivated:1082676877468119110>\n"
            
            if len(embed.description) + len(_str) > 4096:
                await log_channel.send(embed=embed)
                embed = discord.Embed(description=_str, color=0x2b2d31)
            else:
                embed.description += _str

        await log_channel.send(embed=embed)

        embed = discord.Embed(title="Dead Info", description="", color=0x2b2d31)
        dead_players = {}
        for i in data['players'].keys():
            if not data['players'][i]['alive']:
                if data['players'][i]['death_night'] in dead_players.keys():
                    dead_players[data['players'][i]['death_night']].append(data['players'][i]['user'].id)
                else:
                    dead_players[data['players'][i]['death_night']] = [data['players'][i]['user'].id]
        
        keys = list(dead_players.keys())
        keys.sort()
        dead_players = {i:dead_players[i] for i in keys}

        for night in dead_players.keys():
            title = f'Night {night}\n'
            _str = ''
            for player in dead_players[night]:
                index = dead_players[night].index(player)
                if index+1 == len(dead_players[night]):
                    emoji = "<:nat_reply:1146498277068517386>"
                else:
                    emoji = "<:nat_replycont:1146496789361479741>"
                _str += f"{emoji} {channel.guild.get_member(player).mention}\n"
            embed.add_field(name=title, value=_str, inline=True)
            if night % 2 == 0:
                embed.add_field(name = '\u200b', value= '\u200b', inline= True)
        await log_channel.send(embed=embed)
        self.mafia_inprosses.remove(channel.id)
        del self.mafia_channels[channel.id]


    @commands.command()
    async def mafia_transcript(self, channel: discord.TextChannel, message: discord.Message):
        if message.author.id != 511786918783090688 and len(message.embeds)<0: return
        
        embed = message.embeds[0]
        if embed.description is None and "Thank you all for playing! Deleting this channel in 10 seconds" not in embed.description: return
            
        channel = message.channel
        guild = channel.guild
        client = guild.me
        messages = [message async for message in channel.history(limit=None)]

        data = await self.db.find(guild.id)
        if data is None:
            return
        
        if data['enable_logging'] is True and data['logs_channel'] is not None:
            log_channel = guild.get_channel(int(data['logs_channel']))
            if log_channel is None:
                return
            
            transcript_file = await chat_exporter.raw_export(
                channel, messages=messages, tz_info="Asia/Kolkata", 
                guild=guild, bot=client, fancy_times=True, support_dev=False)
            transcript_file = discord.File(io.BytesIO(transcript_file.encode()), filename=f"Mafia Logs.html")
            link_msg  = await log_channel.send(content = f"**Mafia Logs:** <t:{int(datetime.datetime.now(pytz.utc).timestamp())}>", file=transcript_file, allowed_mentions=discord.AllowedMentions.none())
            link_view = discord.ui.View()
            link_view.add_item(discord.ui.Button(emoji="<:nat_mafia:1102305100527042622>",label="Mafia Evidence", style=discord.ButtonStyle.link, url=f"https://mahto.id/chat-exporter?url={link_msg.attachments[0].url}"))
            await link_msg.edit(view=link_view)


async def setup(bot):
    await bot.add_cog(Mafia(bot), guilds=[discord.Object(785839283847954433)])
