import asyncio
import datetime
from itertools import islice
import traceback

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils.embeds import get_invisible_embed


def chunk(it, size):
    it = iter(it)
    return iter(lambda: tuple(islice(it, size)), ())

@app_commands.guild_only()
class Reminder(commands.Cog):
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
            try:
                time_diff = (reminder_data['daily']['time'] - datetime.datetime.now()).total_seconds()
            except KeyError:
                return
            await asyncio.sleep(time_diff)

        reminder_data = await self.bot.cricket.find_by_custom({"_id": reminder_data['_id']})
        if reminder_data is None:
            return

        user = reminder_data['user']
        user = self.bot.get_user(user)
        if user is None:
            user = await self.bot.fetch_user(user)

        if isinstance(user, discord.User) or isinstance(user, discord.Member):
            return await self.bot.cricket.delete_by_id(reminder_data['_id'])
        
        usersettings = await self.bot.userSettings.find(user.id)
        if usersettings is None:
            return await self.bot.cricket.delete_by_id(reminder_data['_id'])
        
        if reminder_type == 'cric_drop':
            if 'cric_drop_events' not in usersettings.keys():
                return await self.bot.cricket.delete_by_id(reminder_data['_id'])
            elif not usersettings['cric_drop_events']:
                return await self.bot.cricket.delete_by_id(reminder_data['_id'])
            embed = await get_invisible_embed("Drop Reminder")
            embed.title = "Drop Reminder"
            embed.description = "You can now drop again!"
            embed.description += "\n\n-# Run </settings:1196688324207853590> >> User Reminders to manage reminders."
            try:
                embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1260884903139217429.webp?size=128&quality=lossless")
            except Exception:
                pass
            try:
                view = discord.ui.View()
                view.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="Jump to channel", emoji="<:tgk_channel:1073908465405268029>", url=reminder_data['message']))
            except Exception:
                view = None
                pass
            
            try:
                await user.send(embed=embed, view=view)
                await self.bot.cricket.delete_by_id(reminder_data['_id'])
            except Exception:
                pass
        
        elif reminder_type == 'cric_daily':
            if 'cric_daily' not in usersettings.keys():
                return await self.bot.cricket.delete_by_id(reminder_data['_id'])
            elif not usersettings['cric_daily']:
                return await self.bot.cricket.delete_by_id(reminder_data['_id'])
            embed = await get_invisible_embed("Daily Reminder")
            embed.title = "Daily Reminder"
            embed.description = "You can now claim your daily rewards!"
            embed.description += "\n\n-# Run </settings:1196688324207853590> >> User Reminders to manage reminders."
            try:
                embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1260884903139217429.webp?size=128&quality=lossless")
            except Exception:
                pass
            try:
                view = discord.ui.View()
                view.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="Jump to channel", emoji="<:tgk_channel:1073908465405268029>", url=reminder_data['message']))
            except Exception:
                view = None
                pass
            try:
                await user.send(embed=embed, view=view)
                await self.bot.cricket.delete_by_id(reminder_data['_id'])
            except Exception:
                pass

        elif reminder_type == 'cric_weekly':
            if 'cric_weekly' not in usersettings.keys():
                return await self.bot.cricket.delete_by_id(reminder_data['_id'])
            elif not usersettings['cric_weekly']:
                return await self.bot.cricket.delete_by_id(reminder_data['_id'])
            embed = await get_invisible_embed("Weekly Reminder")
            embed.title = "Weekly Reminder"
            embed.description = "You can now claim your weekly rewards!"
            embed.description += "\n\n-# Run </settings:1196688324207853590> >> User Reminders to manage reminders."
            try:
                embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1260884903139217429.webp?size=128&quality=lossless")
            except Exception:
                pass
            try:
                view = discord.ui.View()
                view.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="Jump to channel", emoji="<:tgk_channel:1073908465405268029>", url=reminder_data['message']))
            except Exception:
                view = None
                pass
            try:
                await user.send(embed=embed, view=view)
                await self.bot.cricket.delete_by_id(reminder_data['_id'])
            except Exception:
                pass

        elif reminder_type == 'cric_monthly':
            if 'cric_monthly' not in usersettings.keys():
                return await self.bot.cricket.delete_by_id(reminder_data['_id'])
            elif not usersettings['cric_monthly']:
                return await self.bot.cricket.delete_by_id(reminder_data['_id'])
            embed = await get_invisible_embed("Monthly Reminder")
            embed.title = "Monthly Reminder"
            embed.description = "You can now claim your monthly rewards!"
            embed.description += "\n\n-# Run </settings:1196688324207853590> >> User Reminders to manage reminders."
            try:
                embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1260884903139217429.webp?size=128&quality=lossless")
            except Exception:
                pass
            try:
                view = discord.ui.View()
                view.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="Jump to channel", emoji="<:tgk_channel:1073908465405268029>", url=reminder_data['message']))
            except Exception:
                view = None
                pass
            try:
                await user.send(embed=embed, view=view)
                await self.bot.cricket.delete_by_id(reminder_data['_id'])
            except Exception:
                pass

        elif reminder_type == 'cric_vote':
            if 'cric_vote' not in usersettings.keys():
                return await self.bot.cricket.delete_by_id(reminder_data['_id'])
            elif not usersettings['cric_vote']:
                return await self.bot.cricket.delete_by_id(reminder_data['_id'])
            embed = await get_invisible_embed("Vote Reminder")
            embed.title = "Vote Reminder"
            embed.description = "Vote now to get **2 cards & 2000** <:cg:1264848906383003699>"
            embed.description += "\n\n-# Run </settings:1196688324207853590> >> User Reminders to manage reminders."
            try:
                embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1260884903139217429.webp?size=128&quality=lossless")
            except Exception:
                pass
            try:
                view = discord.ui.View()
                view.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="Cricket Guru - Vote", emoji="<:vote:1264867718079713291>", url="https://top.gg/bot/814100764787081217/vote"))
            except Exception:
                view = None
                pass
            try:
                await user.send(embed=embed, view=view)
                await self.bot.cricket.delete_by_id(reminder_data['_id'])
            except Exception:
                pass

    @tasks.loop(seconds=60)
    async def reminder_loop(self):
        reminders = await self.bot.cricket.find_many_by_custom({"user":{"$exists":True}})
        for reminder in reminders:
            if reminder['type'] == 'cric_market':
                continue
            time_diff = (reminder['time'] - datetime.datetime.now()).total_seconds()
            if time_diff <= 0:
                self.bot.dispatch('reminder_end', reminder, reminder['type'], False)
            elif time_diff <= 60:
                self.bot.dispatch('reminder_end', reminder, reminder['type'], True)
    
    # print entire error
    @reminder_loop.error
    async def reminder_loop_error(self, error):
        channel = self.bot.get_channel(999555462674522202)
        full_stack_trace = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        await channel.send(f"<@488614633670967307> <@301657045248114690> , Error in reminder: {full_stack_trace}")
        try:
            self.grinder_reminder.restart()
        except Exception:
            error = traceback.format_exc()
            await channel.send(f"<@488614633670967307> <@301657045248114690> , Error in restarting reminder loop: {error}")

    
    @reminder_loop.before_loop
    async def before_timer_loop(self):
        await self.bot.wait_until_ready()

    
async def setup(bot):
    await bot.add_cog(Reminder(bot))