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
            "WELCOME_CHANNEL_ID": None,
            "LEAVES_CHANNEL_ID": None,
            "ANNOUNCEMENT_CHANNEL_ID": None,
            "REQUEST_CHANNEL_ID": None,
            "INFRACTIONS_CHANNEL_ID": None,
            "PROMOTIONS_CHANNEL_ID": None,
            "SUGGEST_CHANNEL_ID": None,
            "RETIREMENTS_CHANNEL_ID": None,
            "TRAINING_CHANNEL_ID": None,
            "INTERNAL_AFFAIRS_ID": None,
            "LOA_CHANNEL_ID": None,
            "OT_ID": None,
            "STAFF_TEAM_ID": None,
            "AWAITING_TRAINING_ID": None,
            "LOA_ID": None,
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
            # Show configuration selection menu
            await interaction.response.send_message(
                "📝 Select which setting you'd like to configure:",
                view=ConfigSettingSelector(self, guild_id),
                ephemeral=True
            )
        elif action == "reset":
            await self._handle_reset_config(interaction, guild_id)

    async def _handle_view_config(self, interaction: discord.Interaction, guild_id):
        """Display current configuration for a guild"""
        config = self.get_guild_config(guild_id)
        
        embed = discord.Embed(
            title="📊 Current Bot Configuration",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )

        # Channels section
        channels_value = (
            f"Welcome: {self._format_channel(config.get('WELCOME_CHANNEL_ID'))}\n"
            f"Leaves: {self._format_channel(config.get('LEAVES_CHANNEL_ID'))}\n"
            f"Announcements: {self._format_channel(config.get('ANNOUNCEMENT_CHANNEL_ID'))}\n"
            f"Requests: {self._format_channel(config.get('REQUEST_CHANNEL_ID'))}\n"
            f"Infractions: {self._format_channel(config.get('INFRACTIONS_CHANNEL_ID'))}\n"
            f"Promotions: {self._format_channel(config.get('PROMOTIONS_CHANNEL_ID'))}\n"
            f"Suggestions: {self._format_channel(config.get('SUGGEST_CHANNEL_ID'))}\n"
            f"Retirements: {self._format_channel(config.get('RETIREMENTS_CHANNEL_ID'))}\n"
            f"Training: {self._format_channel(config.get('TRAINING_CHANNEL_ID'))}\n"
            f"LOA: {self._format_channel(config.get('LOA_CHANNEL_ID'))}"
        )
        embed.add_field(name="📋 Channels", value=channels_value, inline=False)

        # Roles section
        roles_value = (
            f"Staff Team: {self._format_role(config.get('STAFF_TEAM_ID'))}\n"
            f"Awaiting Training: {self._format_role(config.get('AWAITING_TRAINING_ID'))}\n"
            f"LOA: {self._format_role(config.get('LOA_ID'))}\n"
            f"Ownership Team: {self._format_role(config.get('OT_ID'))}\n"
            f"Internal Affairs: {self._format_role(config.get('INTERNAL_AFFAIRS_ID'))}"
        )
        embed.add_field(name="👥 Roles", value=roles_value, inline=False)
        
        embed.set_footer(text=f"Server ID: {guild_id}")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    def _format_channel(self, channel_id):
        """Format channel for display in config view"""
        return f"<#{channel_id}>" if channel_id else "Not set"
    
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


# Main configuration selection menu
class ConfigSettingSelector(discord.ui.View):
    def __init__(self, config_cog, guild_id):
        super().__init__(timeout=120)
        self.config_cog = config_cog
        self.guild_id = guild_id
        
        # Add the category select
        self.add_item(ConfigCategorySelect())


class ConfigCategorySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Channel Settings",
                description="Configure channel IDs",
                emoji="📝",
                value="channels"
            ),
            discord.SelectOption(
                label="Role Settings",
                description="Configure role IDs",
                emoji="👥",
                value="roles"
            )
        ]
        super().__init__(placeholder="Select a category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        config_cog = self.view.config_cog
        guild_id = self.view.guild_id
        
        if self.values[0] == "channels":
            # Show channel selection view
            await interaction.response.edit_message(
                content="🔧 Select which channel to configure:", 
                view=ChannelConfigView(config_cog, guild_id, interaction.guild)
            )
        elif self.values[0] == "roles":
            # Show role selection view
            await interaction.response.edit_message(
                content="🔧 Select which role to configure:", 
                view=RoleConfigView(config_cog, guild_id, interaction.guild)
            )


# Channel configuration view
class ChannelConfigView(discord.ui.View):
    def __init__(self, config_cog, guild_id, guild):
        super().__init__(timeout=180)
        self.config_cog = config_cog
        self.guild_id = guild_id
        self.guild = guild
        
        # Add the channel select dropdown
        self.add_item(ChannelConfigSelect())
        
        # Add back button
        self.add_item(BackButton())


class ChannelConfigSelect(discord.ui.Select):
    def __init__(self):
        # Create options for each configurable channel
        options = [
            discord.SelectOption(
                label="Welcome Channel",
                description="Channel for welcome messages",
                value="WELCOME_CHANNEL_ID"
            ),
            discord.SelectOption(
                label="Leaves Channel",
                description="Channel for leave messages",
                value="LEAVES_CHANNEL_ID"
            ),
            discord.SelectOption(
                label="Announcement Channel",
                description="Channel for announcements",
                value="ANNOUNCEMENT_CHANNEL_ID"
            ),
            discord.SelectOption(
                label="Request Channel",
                description="Channel for requests",
                value="REQUEST_CHANNEL_ID"
            ),
            discord.SelectOption(
                label="Infractions Channel",
                description="Channel for infractions",
                value="INFRACTIONS_CHANNEL_ID"
            ),
            discord.SelectOption(
                label="Promotions Channel",
                description="Channel for promotions",
                value="PROMOTIONS_CHANNEL_ID"
            ),
            discord.SelectOption(
                label="Suggestions Channel",
                description="Channel for suggestions",
                value="SUGGEST_CHANNEL_ID"
            ),
            discord.SelectOption(
                label="Retirements Channel",
                description="Channel for retirements",
                value="RETIREMENTS_CHANNEL_ID"
            ),
            discord.SelectOption(
                label="Training Channel",
                description="Channel for training",
                value="TRAINING_CHANNEL_ID"
            ),
            discord.SelectOption(
                label="LOA Channel",
                description="Channel for leave of absence",
                value="LOA_CHANNEL_ID"
            )
        ]
        super().__init__(placeholder="Select a channel to configure...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        config_cog = self.view.config_cog
        guild_id = self.view.guild_id
        
        # Show channel selection UI
        await interaction.response.edit_message(
            content=f"Select a channel to set as the **{self.values[0].replace('_ID', '').replace('_', ' ').title()}**:",
            view=ChannelSelectionView(config_cog, guild_id, self.values[0])
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
        
        # Add back button
        self.add_item(BackButton())


class ChannelSelector(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(placeholder="Select a channel...", channel_types=[discord.ChannelType.text])
    
    async def callback(self, interaction: discord.Interaction):
        channel = self.values[0]
        config_key = self.view.config_key
        config_cog = self.view.config_cog
        guild_id = self.view.guild_id
        
        # Get the parent view's config_key to know which setting to update
        try:
            # Update the guild config
            guild_config = config_cog.get_guild_config(guild_id)
            guild_config[config_key] = channel.id
            
            # Save the configuration
            config_cog._save_guild_config(guild_id)
            
            await interaction.response.edit_message(
                content=f"✅ Successfully set {config_key.replace('_ID', '').replace('_', ' ').title()} to {channel.mention}",
                view=None
            )
        except Exception as e:
            await interaction.response.edit_message(
                content=f"❌ Error setting channel: {e}",
                view=None
            )


# Role configuration view
class RoleConfigView(discord.ui.View):
    def __init__(self, config_cog, guild_id, guild):
        super().__init__(timeout=180)
        self.config_cog = config_cog
        self.guild_id = guild_id
        self.guild = guild
        
        # Add the role select dropdown
        self.add_item(RoleConfigSelect())
        
        # Add back button
        self.add_item(BackButton())


class RoleConfigSelect(discord.ui.Select):
    def __init__(self):
        # Create options for each configurable role
        options = [
            discord.SelectOption(
                label="Staff Team Role",
                description="Role for staff team members",
                value="STAFF_TEAM_ID"
            ),
            discord.SelectOption(
                label="Awaiting Training Role",
                description="Role for members awaiting training",
                value="AWAITING_TRAINING_ID"
            ),
            discord.SelectOption(
                label="LOA Role",
                description="Role for members on leave of absence",
                value="LOA_ID"
            ),
            discord.SelectOption(
                label="Ownership Team Role",
                description="Role for ownership team",
                value="OT_ID"
            ),
            discord.SelectOption(
                label="Internal Affairs Role",
                description="Role for internal affairs team",
                value="INTERNAL_AFFAIRS_ID"
            )
        ]
        super().__init__(placeholder="Select a role to configure...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        config_cog = self.view.config_cog
        guild_id = self.view.guild_id
        
        # Show role selection UI
        await interaction.response.edit_message(
            content=f"Select a role to set as the **{self.values[0].replace('_ID', '').replace('_', ' ').title()}**:",
            view=RoleSelectionView(config_cog, guild_id, self.values[0])
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
        
        # Add back button
        self.add_item(BackButton())


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
                view=None
            )
        except Exception as e:
            await interaction.response.edit_message(
                content=f"❌ Error setting role: {e}",
                view=None
            )


# Back button for navigation
class BackButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.secondary, label="Back", row=4)
    
    async def callback(self, interaction: discord.Interaction):
        config_cog = self.view.config_cog
        guild_id = self.view.guild_id
        
        # Go back to main category selector
        await interaction.response.edit_message(
            content="📝 Select which setting you'd like to configure:",
            view=ConfigSettingSelector(config_cog, guild_id)
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
            "WELCOME_CHANNEL_ID": None,
            "LEAVES_CHANNEL_ID": None,
            "ANNOUNCEMENT_CHANNEL_ID": None,
            "REQUEST_CHANNEL_ID": None,
            "INFRACTIONS_CHANNEL_ID": None,
            "PROMOTIONS_CHANNEL_ID": None,
            "SUGGEST_CHANNEL_ID": None,
            "RETIREMENTS_CHANNEL_ID": None,
            "TRAINING_CHANNEL_ID": None,
            "INTERNAL_AFFAIRS_ID": None,
            "LOA_CHANNEL_ID": None,
            "OT_ID": None,
            "STAFF_TEAM_ID": None,
            "AWAITING_TRAINING_ID": None,
            "LOA_ID": None,
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


# Function to add this cog to the bot
async def setup(bot):
    await bot.add_cog(ConfigCog(bot))


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
            
            


async def setup(bot):
    await bot.add_cog(ConfigCog(bot))

