import discord
from discord import app_commands, Interaction
from discord.ext import commands
from datetime import datetime
from typing import List

class Donation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def donation_auto_complete(self, interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
        data = await self.bot.donation_config.find(interaction.guild.id)
        if data is None or len(data['donations'].keys()) == 0:
            return [app_commands.Choice(name="No donation system found", value="no system found")]
        choices = [ 
            app_commands.Choice(name=donation, value=donation)
            for donation in data['donations'].keys() if current.lower() in donation.lower()
        ]
        return choices[:24]
    
    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.__class__.__name__} Cog has been loaded")
    
    @app_commands.command(name="donate", description="Make a donation request to the server")
    @app_commands.describe(amount="The amount you want to donate", message="The message you want to send with donation", event="The event you want to donate for")
    @app_commands.autocomplete(event=donation_auto_complete)
    async def donate(self, interaction: Interaction, event: str, amount: str, message: str):
        if event == "no system found":
            return await interaction.response.send_message("No donation system found", ephemeral=True)
        data = await self.bot.donation_config.find(interaction.guild.id)
        if data is None:
            return await interaction.response.send_message("No donation system found", ephemeral=True)
        if event not in data['donations'].keys():
            return await interaction.response.send_message("No donation system found", ephemeral=True)
        if data['donations'][event]['embed'] == {}:
            embed = discord.Embed(title=f"Donation for {event}", description="", color=self.bot.color['default'])
            embed.description += f"Donor: {interaction.user.mention}\n"
            embed.description += f"Amount: {amount}\n"
            embed.description += f"Message: {message}\n"
            embed.set_footer(text=f"Event: {event}")
            embed.timestamp = datetime.utcnow()
            channel = self.bot.get_channel(data['donations'][event]['loggin_channel'])
            if channel is None:
                return await interaction.response.send_message("No logging channel found", ephemeral=True)
            role = interaction.guild.get_role(data['donations'][event]['manager_role'])
            await channel.send(role.mention,embed=embed)
            await interaction.response.send_message("Donation request sent successfully", ephemeral=True)
        else:
            donor = interaction.user
            embed = discord.Embed.from_dict(data['donations'][event]['embed'])
            embed.title = embed.title.format(donor=donor, amount=amount, message=message, event=event)
            embed.description = embed.description.format(donor=donor, amount=amount, message=message, event=event)
            embed.set_footer(text=embed.footer.text.format(donor=donor, amount=amount, message=message, event=event))
            embed.timestamp = datetime.utcnow()
            channel = self.bot.get_channel(data['donations'][event]['loggin_channel'])
            if channel is None:
                return await interaction.response.send_message("No logging channel found", ephemeral=True)
            role = interaction.guild.get_role(data['donations'][event]['manager_role'])
            await channel.send(role.mention,embed=embed)
            await interaction.response.send_message("Donation request sent successfully", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Donation(bot))