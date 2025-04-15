import discord
from discord.ext import commands
from discord import app_commands
import json
import os

CONFIG_DIR = 'configs'
os.makedirs(CONFIG_DIR, exist_ok=True)

class ConfigCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_dir = 'configs'
        # Ensure config directory exists
        os.makedirs(self.config_dir, exist_ok=True)
        # Dictionary to store configs for different guilds
        self.guild_configs = {}
        
    def _get_config_path(self, guild_id):
        """Get the path to the config file for a specific guild"""
        return os.path.join(self.config_dir, f'{guild_id}.json')
        
    def _load_guild_config(self, guild_id):
        """Load the configuration for a specific guild"""
        config_path = self._get_config_path(guild_id)
        
        # Initialize with default values
        default_config = {
            # Staff Management
            "LOA_CHANNEL_ID": None,
            "INFRACTIONS_CHANNEL_ID": None,
            "PROMOTIONS_CHANNEL_ID": None,
            "RETIREMENTS_CHANNEL_ID": None,
            "TRAINING_CHANNEL_ID": None,
            "STAFF_TEAM_ID": None,
            "AWAITING_TRAINING_ID": None,
            "LOA_ID": None,
            
            # Moderation
            "WELCOME_CHANNEL_ID": None,
            "LEAVES_CHANNEL_ID": None,
            "ANNOUNCEMENT_CHANNEL_ID": None,
            "SUGGEST_CHANNEL_ID": None,
            "INTERNAL_AFFAIRS_ID": None,
            "OT_ID": None,
            "MOD_LOGS_CHANNEL_ID": None,
            "MOD_ROLE_ID": None,
            "ADMIN_ROLE_ID": None,
            
            # Tickets
            "TICKET_LOGS_CHANNEL_ID": None,
            "TICKET_CATEGORY_ID": None,
            "TICKET_ADMIN_ROLE_ID": None,
            "TICKET_SUPPORT_ROLE_ID": None,
            "REQUEST_CHANNEL_ID": None,
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                    # Update default config with loaded values
                    default_config.update(loaded_config)
        except Exception as e:
            print(f"Error loading config for guild {guild_id}: {e}")
            
        return default_config
    
    def get_guild_config(self, guild_id):
        """Get configuration for a specific guild, loading it if necessary"""
        guild_id_str = str(guild_id)
        if guild_id_str not in self.guild_configs:
            self.guild_configs[guild_id_str] = self._load_guild_config(guild_id_str)
        return self.guild_configs[guild_id_str]
            
    def _save_guild_config(self, guild_id):
        """Save the configuration for a specific guild"""
        guild_id_str = str(guild_id)
        config_path = self._get_config_path(guild_id_str)
        
        try:
            if guild_id_str in self.guild_configs:
                with open(config_path, 'w') as f:
                    json.dump(self.guild_configs[guild_id_str], f, indent=4)
                return True
        except Exception as e:
            print(f"Error saving config for guild {guild_id}: {e}")
        return False

    @app_commands.command(name="config", description="Configure the bot settings")
    @app_commands.describe(
        action="The action to perform (view, set, reset)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="view", value="view"),
        app_commands.Choice(name="set", value="set"),
        app_commands.Choice(name="reset", value="reset")
    ])
    async def config(self, interaction: discord.Interaction, action: str):
        # Check admin permissions
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
        
        guild_id = interaction.guild_id

        if action == "view":
            await self._handle_view_config(interaction, guild_id)
        elif action == "set":
            # Show configuration overview embed with buttons
            await self._show_config_overview(interaction, guild_id)
        elif action == "reset":
            await self._handle_reset_config(interaction, guild_id)

    async def _show_config_overview(self, interaction: discord.Interaction, guild_id):
        """Show the configuration overview embed with category buttons"""
        embed = discord.Embed(
            title="⚙️ Bot Configuration",
            description="Select a category below to configure settings for your server.",
            color=discord.Color.blue()
        )
        
        # Add fields for each category
        embed.add_field(
            name="👥 Staff Management",
            value="Configure settings related to LOA, infractions, promotions, staff roles and channels.",
            inline=False
        )
        
        embed.add_field(
            name="🛡️ Moderation",
            value="Configure moderation commands, logs, roles and channels.",
            inline=False
        )
        
        embed.add_field(
            name="🎫 Tickets",
            value="Configure ticket system, logs, categories and admin roles.",
            inline=False
        )
        
        embed.set_footer(text=f"Server ID: {guild_id}")
        
        # Create a view with category buttons
        view = ConfigCategoryView(self, guild_id)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def _handle_view_config(self, interaction: discord.Interaction, guild_id):
        """Display current configuration for a guild"""
        config = self.get_guild_config(guild_id)
        
        embed = discord.Embed(
            title="📊 Current Bot Configuration",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )

        # Staff Management section
        staff_value = (
            f"LOA Channel: {self._format_channel(config.get('LOA_CHANNEL_ID'))}\n"
            f"Infractions Channel: {self._format_channel(config.get('INFRACTIONS_CHANNEL_ID'))}\n"
            f"Promotions Channel: {self._format_channel(config.get('PROMOTIONS_CHANNEL_ID'))}\n"
            f"Retirements Channel: {self._format_channel(config.get('RETIREMENTS_CHANNEL_ID'))}\n"
            f"Training Channel: {self._format_channel(config.get('TRAINING_CHANNEL_ID'))}\n"
            f"Staff Team Role: {self._format_role(config.get('STAFF_TEAM_ID'))}\n"
            f"Awaiting Training Role: {self._format_role(config.get('AWAITING_TRAINING_ID'))}\n"
            f"LOA Role: {self._format_role(config.get('LOA_ID'))}"
        )
        embed.add_field(name="👥 Staff Management", value=staff_value, inline=False)

        # Moderation section
        mod_value = (
            f"Welcome Channel: {self._format_channel(config.get('WELCOME_CHANNEL_ID'))}\n"
            f"Leaves Channel: {self._format_channel(config.get('LEAVES_CHANNEL_ID'))}\n"
            f"Announcements Channel: {self._format_channel(config.get('ANNOUNCEMENT_CHANNEL_ID'))}\n"
            f"Suggestions Channel: {self._format_channel(config.get('SUGGEST_CHANNEL_ID'))}\n"
            f"Mod Logs Channel: {self._format_channel(config.get('MOD_LOGS_CHANNEL_ID'))}\n"
            f"Ownership Team Role: {self._format_role(config.get('OT_ID'))}\n"
            f"Internal Affairs Role: {self._format_role(config.get('INTERNAL_AFFAIRS_ID'))}\n"
            f"Moderator Role: {self._format_role(config.get('MOD_ROLE_ID'))}\n"
            f"Admin Role: {self._format_role(config.get('ADMIN_ROLE_ID'))}"
        )
        embed.add_field(name="🛡️ Moderation", value=mod_value, inline=False)

        # Tickets section
        tickets_value = (
            f"Ticket Logs Channel: {self._format_channel(config.get('TICKET_LOGS_CHANNEL_ID'))}\n"
            f"Ticket Category: {self._format_channel(config.get('TICKET_CATEGORY_ID'), True)}\n"
            f"Request Channel: {self._format_channel(config.get('REQUEST_CHANNEL_ID'))}\n"
            f"Ticket Admin Role: {self._format_role(config.get('TICKET_ADMIN_ROLE_ID'))}\n"
            f"Ticket Support Role: {self._format_role(config.get('TICKET_SUPPORT_ROLE_ID'))}"
        )
        embed.add_field(name="🎫 Tickets", value=tickets_value, inline=False)
        
        embed.set_footer(text=f"Server ID: {guild_id}")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    def _format_channel(self, channel_id, is_category=False):
        """Format channel for display in config view"""
        if not channel_id:
            return "Not set"
        
        if is_category:
            return f"<#{channel_id}> (Category)"
        return f"<#{channel_id}>"
    
    def _format_role(self, role_id):
        """Format role for display in config view"""
        return f"<@&{role_id}>" if role_id else "Not set"

    async def _handle_reset_config(self, interaction: discord.Interaction, guild_id):
        """Reset configuration to default values for a guild"""
        # Create a confirmation view with buttons
        view = ConfigResetConfirmation(self, guild_id)
        await interaction.response.send_message(
            "⚠️ This will reset all configuration values to default for this server. Are you sure?",
            view=view,
            ephemeral=True
        )


# Main configuration category view
class ConfigCategoryView(discord.ui.View):
    def __init__(self, config_cog, guild_id):
        super().__init__(timeout=180)
        self.config_cog = config_cog
        self.guild_id = guild_id
    
    @discord.ui.button(label="Staff Management", emoji="👥", style=discord.ButtonStyle.primary, row=0)
    async def staff_management_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="Select a section to configure in Staff Management:",
            embed=None,
            view=StaffManagementView(self.config_cog, self.guild_id)
        )
    
    @discord.ui.button(label="Moderation", emoji="🛡️", style=discord.ButtonStyle.primary, row=0)
    async def moderation_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="Select a section to configure in Moderation:",
            embed=None,
            view=ModerationView(self.config_cog, self.guild_id)
        )
    
    @discord.ui.button(label="Tickets", emoji="🎫", style=discord.ButtonStyle.primary, row=0)
    async def tickets_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="Select a section to configure in Tickets:",
            embed=None,
            view=TicketsView(self.config_cog, self.guild_id)
        )


# Staff Management View
class StaffManagementView(discord.ui.View):
    def __init__(self, config_cog, guild_id):
        super().__init__(timeout=180)
        self.config_cog = config_cog
        self.guild_id = guild_id
        
        # Add the staff management options
        self.add_item(StaffManagementSelect())
        
        # Add back button
        self.add_item(BackButton())


class StaffManagementSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="LOA Channel",
                description="Channel for leave of absence announcements",
                value="LOA_CHANNEL_ID",
                emoji="🚗"
            ),
            discord.SelectOption(
                label="Infractions Channel",
                description="Channel for staff infractions",
                value="INFRACTIONS_CHANNEL_ID",
                emoji="💢"
            ),
            discord.SelectOption(
                label="Promotions Channel",
                description="Channel for staff promotions",
                value="PROMOTIONS_CHANNEL_ID",
                emoji="⭐"
            ),
            discord.SelectOption(
                label="Retirements Channel",
                description="Channel for staff retirements",
                value="RETIREMENTS_CHANNEL_ID",
                emoji="🎓"
            ),
            discord.SelectOption(
                label="Training Channel",
                description="Channel for staff training",
                value="TRAINING_CHANNEL_ID",
                emoji="🙏"
            ),
            discord.SelectOption(
                label="Staff Team Role",
                description="Role for staff team members",
                value="STAFF_TEAM_ID",
                emoji="👥"
            ),
            discord.SelectOption(
                label="Awaiting Training Role",
                description="Role for members awaiting training",
                value="AWAITING_TRAINING_ID",
                emoji="👥"
            ),
            discord.SelectOption(
                label="LOA Role",
                description="Role for members on leave of absence",
                value="LOA_ID",
                emoji="👥"
            )
        ]
        super().__init__(placeholder="Select an option to configure...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        config_cog = self.view.config_cog
        guild_id = self.view.guild_id
        selected_value = self.values[0]
        
        # Determine if this is a channel or role configuration
        if selected_value.endswith("_CHANNEL_ID"):
            await interaction.response.edit_message(
                content=f"Select a channel to set as the **{selected_value.replace('_ID', '').replace('_', ' ').title()}**:",
                view=ChannelSelectionView(config_cog, guild_id, selected_value)
            )
        else:  # Role configuration
            await interaction.response.edit_message(
                content=f"Select a role to set as the **{selected_value.replace('_ID', '').replace('_', ' ').title()}**:",
                view=RoleSelectionView(config_cog, guild_id, selected_value)
            )


# Moderation View
class ModerationView(discord.ui.View):
    def __init__(self, config_cog, guild_id):
        super().__init__(timeout=180)
        self.config_cog = config_cog
        self.guild_id = guild_id
        
        # Add the moderation options
        self.add_item(ModerationSelect())
        
        # Add back button
        self.add_item(BackButton())


class ModerationSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Welcome Channel",
                description="Channel for welcome messages",
                value="WELCOME_CHANNEL_ID",
                emoji="👋"
            ),
            discord.SelectOption(
                label="Leaves Channel",
                description="Channel for leave messages",
                value="LEAVES_CHANNEL_ID",
                emoji="😢"
            ),
            discord.SelectOption(
                label="Announcement Channel",
                description="Channel for announcements",
                value="ANNOUNCEMENT_CHANNEL_ID",
                emoji="📢"
            ),
            discord.SelectOption(
                label="Suggestions Channel",
                description="Channel for suggestions",
                value="SUGGEST_CHANNEL_ID",
                emoji="💡"
            ),
            discord.SelectOption(
                label="Mod Logs Channel",
                description="Channel for moderation logs",
                value="MOD_LOGS_CHANNEL_ID",
               	emoji="🤖"
            ),
            discord.SelectOption(
                label="Ownership Team Role",
                description="Can use all commands and configure the bot.",
                value="OT_ID",
                emoji="👥"
            ),
            discord.SelectOption(
                label="Internal Affairs Role",
                description="Can use most commands.",
                value="INTERNAL_AFFAIRS_ID",
                emoji="👥"
            ),
            discord.SelectOption(
                label="Admin Role",
                description="Can use some commands.",
                value="ADMIN_ROLE_ID",
                emoji="👥"
            ),
            discord.SelectOption(
                label="Moderator Role",
                description="Can use some basic commands.",
                value="MOD_ROLE_ID",
                emoji="👥"
            )       
        ]
        super().__init__(placeholder="Select an option to configure...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        config_cog = self.view.config_cog
        guild_id = self.view.guild_id
        selected_value = self.values[0]
        
        # Determine if this is a channel or role configuration
        if selected_value.endswith("_CHANNEL_ID"):
            await interaction.response.edit_message(
                content=f"Select a channel to set as the **{selected_value.replace('_ID', '').replace('_', ' ').title()}**:",
                view=ChannelSelectionView(config_cog, guild_id, selected_value)
            )
        else:  # Role configuration
            await interaction.response.edit_message(
                content=f"Select a role to set as the **{selected_value.replace('_ID', '').replace('_', ' ').title()}**:",
                view=RoleSelectionView(config_cog, guild_id, selected_value)
            )


# Tickets View
class TicketsView(discord.ui.View):
    def __init__(self, config_cog, guild_id):
        super().__init__(timeout=180)
        self.config_cog = config_cog
        self.guild_id = guild_id
        
        # Add the tickets options
        self.add_item(TicketsSelect())
        
        # Add back button
        self.add_item(BackButton())


class TicketsSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Ticket Logs Channel",
                description="Channel for ticket logs",
                value="TICKET_LOGS_CHANNEL_ID",
                emoji="🎫"
            ),
            discord.SelectOption(
                label="Ticket Category",
                description="Category for tickets",
                value="TICKET_CATEGORY_ID",
                emoji="🔧"
            ),
            discord.SelectOption(
                label="Ticket Admin Role",
                description="Role for ticket administrators",
                value="TICKET_ADMIN_ROLE_ID",
                emoji="👥"
            ),
            discord.SelectOption(
                label="Ticket Support Role",
                description="Role for ticket support staff",
                value="TICKET_SUPPORT_ROLE_ID",
                emoji="👥"
            )
        ]
        super().__init__(placeholder="Select an option to configure...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        config_cog = self.view.config_cog
        guild_id = self.view.guild_id
        selected_value = self.values[0]
        
        # Determine if this is a channel/category or role configuration
        if selected_value.endswith("_CHANNEL_ID"):
            await interaction.response.edit_message(
                content=f"Select a channel to set as the **{selected_value.replace('_ID', '').replace('_', ' ').title()}**:",
                view=ChannelSelectionView(config_cog, guild_id, selected_value)
            )
        elif selected_value == "TICKET_CATEGORY_ID":
            await interaction.response.edit_message(
                content=f"Select a category to set as the **Ticket Category**:",
                view=CategorySelectionView(config_cog, guild_id, selected_value)
            )
        else:  # Role configuration
            await interaction.response.edit_message(
                content=f"Select a role to set as the **{selected_value.replace('_ID', '').replace('_', ' ').title()}**:",
                view=RoleSelectionView(config_cog, guild_id, selected_value)
            )


# Channel selection view
class ChannelSelectionView(discord.ui.View):
    def __init__(self, config_cog, guild_id, config_key):
        super().__init__(timeout=180)
        self.config_cog = config_cog
        self.guild_id = guild_id
        self.config_key = config_key
        
        # Add channel selector
        self.add_item(ChannelSelector())
        
        # Add back button based on category
        if config_key in ["LOA_CHANNEL_ID", "INFRACTIONS_CHANNEL_ID", "PROMOTIONS_CHANNEL_ID", 
                          "RETIREMENTS_CHANNEL_ID", "TRAINING_CHANNEL_ID"]:
            self.add_item(CategoryBackButton("staff"))
        elif config_key in ["WELCOME_CHANNEL_ID", "LEAVES_CHANNEL_ID", "ANNOUNCEMENT_CHANNEL_ID", 
                            "SUGGEST_CHANNEL_ID", "MOD_LOGS_CHANNEL_ID"]:
            self.add_item(CategoryBackButton("moderation"))
        else:
            self.add_item(CategoryBackButton("tickets"))


class ChannelSelector(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(placeholder="Select a channel...", channel_types=[discord.ChannelType.text])
    
    async def callback(self, interaction: discord.Interaction):
        channel = self.values[0]
        config_key = self.view.config_key
        config_cog = self.view.config_cog
        guild_id = self.view.guild_id
        
        try:
            # Update the guild config
            guild_config = config_cog.get_guild_config(guild_id)
            guild_config[config_key] = channel.id
            
            # Save the configuration
            config_cog._save_guild_config(guild_id)
            
            await interaction.response.edit_message(
                content=f"✅ Successfully set {config_key.replace('_ID', '').replace('_', ' ').title()} to {channel.mention}",
                view=SuccessView(config_cog, guild_id, get_category_from_key(config_key))
            )
        except Exception as e:
            await interaction.response.edit_message(
                content=f"❌ Error setting channel: {e}",
                view=None
            )


# Category selection view
class CategorySelectionView(discord.ui.View):
    def __init__(self, config_cog, guild_id, config_key):
        super().__init__(timeout=180)
        self.config_cog = config_cog
        self.guild_id = guild_id
        self.config_key = config_key
        
        # Add category selector
        self.add_item(CategorySelector())
        
        # Add back button
        self.add_item(CategoryBackButton("tickets"))


class CategorySelector(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(placeholder="Select a category...", channel_types=[discord.ChannelType.category])
    
    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        config_key = self.view.config_key
        config_cog = self.view.config_cog
        guild_id = self.view.guild_id
        
        try:
            # Update the guild config
            guild_config = config_cog.get_guild_config(guild_id)
            guild_config[config_key] = category.id
            
            # Save the configuration
            config_cog._save_guild_config(guild_id)
            
            await interaction.response.edit_message(
                content=f"✅ Successfully set Ticket Category to {category.name}",
                view=SuccessView(config_cog, guild_id, "tickets")
            )
        except Exception as e:
            await interaction.response.edit_message(
                content=f"❌ Error setting category: {e}",
                view=None
            )


# Role selection view
class RoleSelectionView(discord.ui.View):
    def __init__(self, config_cog, guild_id, config_key):
        super().__init__(timeout=180)
        self.config_cog = config_cog
        self.guild_id = guild_id
        self.config_key = config_key
        
        # Add role selector
        self.add_item(RoleSelector())
        
        # Add back button based on category
        if config_key in ["STAFF_TEAM_ID", "AWAITING_TRAINING_ID", "LOA_ID"]:
            self.add_item(CategoryBackButton("staff"))
        elif config_key in ["OT_ID", "INTERNAL_AFFAIRS_ID", "MOD_ROLE_ID", "ADMIN_ROLE_ID"]:
            self.add_item(CategoryBackButton("moderation"))
        else:
            self.add_item(CategoryBackButton("tickets"))


class RoleSelector(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(placeholder="Select a role...")
    
    async def callback(self, interaction: discord.Interaction):
        role = self.values[0]
        config_key = self.view.config_key
        config_cog = self.view.config_cog
        guild_id = self.view.guild_id
        
        try:
            # Update the guild config
            guild_config = config_cog.get_guild_config(guild_id)
            guild_config[config_key] = role.id
            
            # Save the configuration
            config_cog._save_guild_config(guild_id)
            
            await interaction.response.edit_message(
                content=f"✅ Successfully set {config_key.replace('_ID', '').replace('_', ' ').title()} to {role.mention}",
                view=SuccessView(config_cog, guild_id, get_category_from_key(config_key))
            )
        except Exception as e:
            await interaction.response.edit_message(
                content=f"❌ Error setting role: {e}",
                view=None
            )


# Success view with "Configure More" button
class SuccessView(discord.ui.View):
    def __init__(self, config_cog, guild_id, category):
        super().__init__(timeout=180)
        self.config_cog = config_cog
        self.guild_id = guild_id
        self.category = category
    
    @discord.ui.button(label="Configure More", style=discord.ButtonStyle.primary)
    async def configure_more_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.category == "staff":
            await interaction.response.edit_message(
                content="Select a section to configure in Staff Management:",
                view=StaffManagementView(self.config_cog, self.guild_id)
            )
        elif self.category == "moderation":
            await interaction.response.edit_message(
                content="Select a section to configure in Moderation:",
                view=ModerationView(self.config_cog, self.guild_id)
            )
        elif self.category == "tickets":
            await interaction.response.edit_message(
                content="Select a section to configure in Tickets:",
                view=TicketsView(self.config_cog, self.guild_id)
            )
        else:
            # Show main category view as fallback
            await interaction.response.edit_message(
                content="Select a category to configure:",
                view=ConfigCategoryView(self.config_cog, self.guild_id)
            )
    
    @discord.ui.button(label="Done", style=discord.ButtonStyle.secondary)
    async def done_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="✅ Configuration saved successfully!",
            view=None
        )


# Helper function to determine category from config key
def get_category_from_key(config_key):
    if config_key in ["LOA_CHANNEL_ID", "INFRACTIONS_CHANNEL_ID", "PROMOTIONS_CHANNEL_ID", 
                       "RETIREMENTS_CHANNEL_ID", "TRAINING_CHANNEL_ID", "STAFF_TEAM_ID", 
                       "AWAITING_TRAINING_ID", "LOA_ID"]:
        return "staff"
    elif config_key in ["WELCOME_CHANNEL_ID", "LEAVES_CHANNEL_ID", "ANNOUNCEMENT_CHANNEL_ID", 
                         "SUGGEST_CHANNEL_ID", "MOD_LOGS_CHANNEL_ID", "OT_ID", 
                         "INTERNAL_AFFAIRS_ID", "MOD_ROLE_ID", "ADMIN_ROLE_ID"]:
        return "moderation"
    else:
        return "tickets"


# Back button for navigation
class BackButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.secondary, label="Back to Main Menu", row=4)
    
    async def callback(self, interaction: discord.Interaction):
        config_cog = self.view.config_cog
        guild_id = self.view.guild_id
        
        # Go back to main category selector
        await config_cog._show_config_overview(interaction, guild_id)


# Category-specific back button
class CategoryBackButton(discord.ui.Button):
    def __init__(self, category):
        super().__init__(style=discord.ButtonStyle.secondary, label="Back", row=4)
        self.category = category
    
    async def callback(self, interaction: discord.Interaction):
        config_cog = self.view.config_cog
        guild_id = self.view.guild_id
        
        if self.category == "staff":
            await interaction.response.edit_message(
                content="Select a section to configure in Staff Management:",
                view=StaffManagementView(config_cog, guild_id)
            )
        elif self.category == "moderation":
            await interaction.response.edit_message(
                content="Select a section to configure in Moderation:",
                view=ModerationView(config_cog, guild_id)
            )
        elif self.category == "tickets":
            await interaction.response.edit_message(
                content="Select a section to configure in Tickets:",
                view=TicketsView(config_cog, guild_id)
            )


# Confirmation view for reset
class ConfigResetConfirmation(discord.ui.View):
    def __init__(self, config_cog, guild_id):
        super().__init__(timeout=60)
        self.config_cog = config_cog
        self.guild_id = guild_id

    @discord.ui.button(label="Yes, Reset", style=discord.ButtonStyle.danger)
    async def confirm_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Reset guild configuration to default values
        default_config = {
            # Staff Management
            "LOA_CHANNEL_ID": None,
            "INFRACTIONS_CHANNEL_ID": None,
            "PROMOTIONS_CHANNEL_ID": None,
            "RETIREMENTS_CHANNEL_ID": None,
            "TRAINING_CHANNEL_ID": None,
            "STAFF_TEAM_ID": None,
            "AWAITING_TRAINING_ID": None,
            "LOA_ID": None,
            
            # Moderation
            "WELCOME_CHANNEL_ID": None,
            "LEAVES_CHANNEL_ID": None,
            "ANNOUNCEMENT_CHANNEL_ID": None,
            "SUGGEST_CHANNEL_ID": None,
            "INTERNAL_AFFAIRS_ID": None,
            "OT_ID": None,
            "MOD_LOGS_CHANNEL_ID": None,
            "MOD_ROLE_ID": None,
            "ADMIN_ROLE_ID": None,
            
            # Tickets
            "TICKET_LOGS_CHANNEL_ID": None,
            "TICKET_CATEGORY_ID": None,
            "TICKET_ADMIN_ROLE_ID": None,
            "TICKET_SUPPORT_ROLE_ID": None,
            "REQUEST_CHANNEL_ID": None,
        }
        
        # Update the guild config
        self.config_cog.guild_configs[str(self.guild_id)] = default_config
        
        # Save the reset configuration
        self.config_cog._save_guild_config(self.guild_id)
        
        await interaction.response.edit_message(
            content="✅ Configuration has been reset to default values for this server.",
            view=None
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Reset cancelled.", view=None)


# Example usage in a bot command
@app_commands.command(name="config", description="Configure the bot settings")
@app_commands.describe(
    action="The action to perform (view, set, reset)"
)
@app_commands.choices(action=[
    app_commands.Choice(name="view", value="view"),
    app_commands.Choice(name="set", value="set"),
    app_commands.Choice(name="reset", value="reset")
])
async def config(interaction: discord.Interaction, action: str):
    # This command is handled by the ConfigCog, this is just an interface
    config_cog = interaction.client.get_cog("ConfigCog")
    if config_cog:
        await config_cog.config(interaction, action)
    else:
        await interaction.response.send_message("❌ Configuration system is not available.", ephemeral=True)
            
@app_commands.command(name="dashboard", description="Get the link to this server's dashboard")
async def dashboard(interaction: discord.Interaction):
    await interaction.response.send_message(f"The link to this server's dashboard is https://PLACEHOLDER/{interaction.guild.id}/", ephemeral=True)


async def setup(bot):
    await bot.add_cog(ConfigCog(bot))
