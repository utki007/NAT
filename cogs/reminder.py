import asyncio
import io
import datetime
from itertools import islice
from tabnanny import check

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils.convertor import convert_to_time, calculate
from utils.embeds import get_error_embed, get_invisible_embed, get_success_embed, get_warning_embed


def chunk(it, size):
    it = iter(it)
    return iter(lambda: tuple(islice(it, size)), ())

@app_commands.guild_only()
class Reminder(commands.GroupCog, name="reminder", description="Reminder commands"):
    def __init__(self, bot):
        self.bot = bot
        self.remindertask = self.reminder_loop.start()

    def cog_unload(self) -> None:
        self.remindertask.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.__class__.__name__} Cog has been loaded\n-----")
        
    @commands.Cog.listener()
    async def on_reminder_end(self, reminder_data, reminder_type, sleep:bool=None):
        if sleep:
            time_diff = (reminder_data['drops']['time'] - datetime.datetime.now()).total_seconds()
            await asyncio.sleep(time_diff)
            reminder_data = await self.bot.timer.find({'_id':reminder_data['_id']})

        if reminder_data == None:
            return
        
        user = reminder_data['_id']
        user = await self.bot.fetch_user(int(user))
        if user == None:
            return await self.bot.timer.delete_by_id(reminder_data['_id'])
        
        usersettings = await self.bot.userSettings.find(user.id)
        
        if reminder_type == 'drops':
            if 'cric_drop_events' not in usersettings.keys():
                return await self.bot.cricket.unset(user.id, 'drops')
            elif usersettings['cric_drop_events'] == False:
                return await self.bot.cricket.unset(user.id, 'drops')
            embed = await get_invisible_embed("Drop Reminder")
            embed.title = f"Drop Reminder"
            embed.description = f"You can now drop again!"
            embed.description += f"\n\n-# Run </settings:1196688324207853590> >> User Reminders to manage reminders."
            try:
                embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1260884903139217429.webp?size=128&quality=lossless")
            except:
                pass
            try:
                view = discord.ui.View()
                view.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="Jump to channel", emoji="<:tgk_channel:1073908465405268029>", url=reminder_data['drops']['message']))
            except:
                view = None
                pass
            
            try:
                await user.send(embed=embed, view=view)
                await self.bot.cricket.unset(user.id, 'drops')
            except:
                pass
        
        elif reminder_type == 'daily':
            if 'cric_daily_events' not in usersettings.keys():
                return await self.bot.cricket.unset(user.id, 'daily')
            elif usersettings['cric_daily_events'] == False:
                return await self.bot.cricket.unset(user.id, 'daily')
            embed = await get_invisible_embed("Daily Reminder")
            embed.title = f"Daily Reminder"
            embed.description = f"You can now claim your daily rewards!"
            embed.description += f"\n\n-# Run </settings:1196688324207853590> >> User Reminders to manage reminders."
            try:
                embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1260884903139217429.webp?size=128&quality=lossless")
            except:
                pass
            try:
                view = discord.ui.View()
                view.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="Jump to channel", emoji="<:tgk_channel:1073908465405268029>", url=reminder_data['daily']['message']))
            except:
                view = None
                pass
            try:
                await user.send(embed=embed, view=view)
                await self.bot.cricket.unset(user.id, 'daily')
            except:
                pass

    @tasks.loop(seconds=60)
    async def reminder_loop(self):
        current_reminder = await self.bot.cricket.get_all()
        for timer in current_reminder:
            if 'drops' not in timer.keys():
                continue
            time_diff = (timer['drops']['time'] - datetime.datetime.now()).total_seconds()
            if time_diff <= 0:
                self.bot.dispatch('reminder_end', timer,'drops' , False)
            elif time_diff <= 60:
                self.bot.dispatch('reminder_end', timer,'drops' , True)
            else:
                pass
        for timer in current_reminder:
            if 'daily' not in timer.keys():
                continue
            time_diff = (timer['daily']['time'] - datetime.datetime.now()).total_seconds()
            if time_diff <= 0:
                self.bot.dispatch('reminder_end', timer,'daily' , False)
            elif time_diff <= 60:
                self.bot.dispatch('reminder_end', timer,'daily' , True)
            else:
                pass
    
    # print entire error
    @reminder_loop.error
    async def reminder_loop_error(self, error):
        print(f"Error in reminder loop: {error}")
    
    @reminder_loop.before_loop
    async def before_timer_loop(self):
        await self.bot.wait_until_ready()

    
async def setup(bot):
    await bot.add_cog(Reminder(bot))