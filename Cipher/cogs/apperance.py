import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import io

class AppearanceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    # Define the command group with a different name to avoid the bot_ prefix issue
    manage_group = app_commands.Group(name="bot", description="Bot management commands.")
    
    @manage_group.command(name="nick", description="Changes the bot's nickname in the current server")
    @app_commands.default_permissions(manage_nicknames=True)
    async def change_nickname(self, interaction: discord.Interaction, new_nickname: str = None):
        """
        Change the bot's nickname in the current guild
        Parameters:
            new_nickname (str): The new nickname for the bot
        """
        try:
            # Get the current guild
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message("This command can only be used in a server!", ephemeral=True)
                return

            # Get the bot member object in this guild
            bot_member = guild.get_member(self.bot.user.id)
            
            # Change the bot's nickname in this guild
            await bot_member.edit(nick=new_nickname)
            
            if new_nickname:
                await interaction.response.send_message(f"✅ My nickname has been changed to **{new_nickname}**!")
            else:
                await interaction.response.send_message("✅ My nickname has been reset to default!")
                
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to change my nickname!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

  


async def setup(bot):
    await bot.add_cog(AppearanceCog(bot))
