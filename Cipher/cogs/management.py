import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime

class StaffManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Config cog will be accessed when needed instead of at initialization
        self.config_cog = None
        self.guild_config = None
        
        self.INTERNAL_AFFAIRS_ID = None
        self.OT_ID = None
        self.STAFF_TEAM_ID = None
        self.INFRACTIONS_CHANNEL_ID = None
        self.PROMOTIONS_CHANNEL_ID = None
        self.RETIREMENTS_CHANNEL_ID = None

    async def load_config(self, guild_id):
        """Load configuration for the specified guild"""
        self.config_cog = self.bot.get_cog("ConfigCog")
        if not self.config_cog:
            return False
        
        self.guild_config = self.config_cog.get_guild_config(guild_id)
        if self.guild_config:
            self.INTERNAL_AFFAIRS_ID = self.guild_config.get("INTERNAL_AFFAIRS_ID")
            self.OT_ID = self.guild_config.get("OT_ID")
            self.STAFF_TEAM_ID = self.guild_config.get("STAFF_TEAM")  # Note: Inconsistent naming
            self.INFRACTIONS_CHANNEL_ID = self.guild_config.get("INFRACTIONS_CHANNEL_ID")
            self.PROMOTIONS_CHANNEL_ID = self.guild_config.get("PROMOTIONS_CHANNEL_ID")
            self.RETIREMENTS_CHANNEL_ID = self.guild_config.get("RETIREMENTS_CHANNEL_ID")
            return True
        return False

    async def get_channel_by_id(self, guild, channel_id):
        """Helper method to get a channel by ID"""
        return guild.get_channel(channel_id)
    
    # Define infraction group
    infraction = app_commands.Group(name="infraction", description="Infraction related commands.")
    
    @infraction.command(name="issue", description="Infract a user.")
    async def infract(self, interaction: discord.Interaction, user: discord.Member, punishment: str, reason: str, notes: str):
        """Issue an infraction to a staff member"""
        # Load config for the current guild
        if not await self.load_config(interaction.guild.id):
            await interaction.response.send_message("Failed to load configuration. Please contact an administrator.", ephemeral=True)
            return
            
        role = discord.utils.get(interaction.guild.roles, id=self.INTERNAL_AFFAIRS_ID)
        if role not in interaction.user.roles:
            role = discord.utils.get(interaction.guild.roles, id=self.OT_ID)
            if role not in interaction.user.roles:
                await interaction.response.send_message(f'Sorry {interaction.user.mention}, you do not have the required role to run this command.', ephemeral=True)
                return

        channel = await self.get_channel_by_id(interaction.guild, self.INFRACTIONS_CHANNEL_ID)
        if channel:
            await channel.send(f"{user.mention}")
            embed = discord.Embed(
                title="Staff Infraction",
                description=f'The Internal Affairs team has decided to infract you. Please do not create any drama by this infraction. Please open a appeal ticket if you have any problems. \n\n**User getting infracted**:\n {user.mention} \n\n **Punishment**:\n {punishment} \n\n **Reason**:\n {reason} \n\n **Notes**: {notes} ',
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text=f"Issued by {interaction.user.name}")
            await channel.send(embed=embed)
            await interaction.response.send_message("Infraction logged!", ephemeral=True)
        else:
            await interaction.response.send_message("Internal error: channel not found!", ephemeral=True)

    @app_commands.command(name="promote", description="Promote a user.")
    async def promote(self, interaction: discord.Interaction, user: discord.Member, new_rank: discord.Role, reason: str):
        """Promote a staff member to a new rank"""
        # Load config for the current guild
        if not await self.load_config(interaction.guild.id):
            await interaction.response.send_message("Failed to load configuration. Please contact an administrator.", ephemeral=True)
            return
            
        role = discord.utils.get(interaction.guild.roles, id=self.INTERNAL_AFFAIRS_ID)
        if role not in interaction.user.roles:
            role = discord.utils.get(interaction.guild.roles, id=self.OT_ID)
            if role not in interaction.user.roles:
                await interaction.response.send_message(f'Sorry {interaction.user.mention}, you do not have the required role to run this command.', ephemeral=True)
                return

        channel = await self.get_channel_by_id(interaction.guild, self.PROMOTIONS_CHANNEL_ID)
        if channel:
            await channel.send(f"{user.mention}")
            embed = discord.Embed(
                title="Staff Promotion!",
                description=f'The High ranking team has decided to grant you a promotion! \n\n **User getting promoted**:\n {user.mention} \n\n **New Rank**:\n {new_rank.mention} \n\n **Reason**:\n {reason}',
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text=f"Promoted by {interaction.user.name}")
            await channel.send(embed=embed)

            try:
                await user.add_roles(new_rank)
            except discord.Forbidden:
                await interaction.response.send_message("I don't have permission to add roles to this user!", ephemeral=True)
                return
            except discord.HTTPException:
                await interaction.response.send_message("Failed to add the role. Please try again.", ephemeral=True)
                return

            await interaction.response.send_message("Promotion logged!", ephemeral=True)
        else:
            await interaction.response.send_message("Internal error: channel not found!", ephemeral=True)

    @app_commands.command(name="retire", description="Retire yourself, THIS IS A ONE WAY ACTION, THERE IS NO GOING BACK.")
    async def retire(self, interaction: discord.Interaction, last_words: str):
        """Retire from the staff team"""
        # Load config for the current guild
        if not await self.load_config(interaction.guild.id):
            await interaction.response.send_message("Failed to load configuration. Please contact an administrator.", ephemeral=True)
            return
            
        role = discord.utils.get(interaction.guild.roles, id=self.STAFF_TEAM_ID)
        if role not in interaction.user.roles:
            await interaction.response.send_message(f'Sorry {interaction.user.mention}, you do not have the required role to run this command.', ephemeral=True)
            return

        channel = await self.get_channel_by_id(interaction.guild, self.RETIREMENTS_CHANNEL_ID)
        if channel:
            await channel.send(f"{interaction.user.mention}")
            embed = discord.Embed(
                title="Retirement :(",
                description=f'{interaction.user.mention} has decided to **retire!** \n  The Los Angoles **staff team** wishes you best of luck! \n\n  **Last words:** \n {last_words} \n \n  Goodbye!',
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text=f"Best of wishes from the ownership and development team!")
            sent_message = await channel.send(embed=embed)
            await sent_message.add_reaction('❤️')
            await sent_message.add_reaction('🫡')
            await sent_message.add_reaction('😭')
            
            await interaction.response.send_message("Retirement sent, your roles will be removed in the near future.", ephemeral=True)
        else:
            await interaction.response.send_message("Internal error: channel not found!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(StaffManagement(bot))
