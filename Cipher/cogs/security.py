import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from discord import app_commands
import json
import os
import io

SECURITY_CONFIG_FILE = 'storage/security_config.json'

DEFAULT_SECURITY_CONFIG = {
    'log_channel_id': None,
    'staff_roles': [],
    'ignored_users': [],
    'alert_mode': 'log'  # Options: 'log', 'dm_owner'
}

SUSPICIOUS_ACTIONS = {
    'mass_ban': {'count': 5, 'window': 60},
    'mass_kick': {'count': 5, 'window': 60},
    'channel_delete': {'count': 3, 'window': 60},
    'role_delete': {'count': 3, 'window': 60}
}


class SecurityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = DEFAULT_SECURITY_CONFIG.copy()
        self.action_log = {}  # {guild_id: {user_id: {action: [timestamps]}}}
        self.load_config()
        self.cleanup_actions.start()

    def load_config(self):
        # Ensure directory exists
        os.makedirs(os.path.dirname(SECURITY_CONFIG_FILE), exist_ok=True)
        if os.path.exists(SECURITY_CONFIG_FILE):
            try:
                with open(SECURITY_CONFIG_FILE, 'r') as f:
                    self.config.update(json.load(f))
            except json.JSONDecodeError:
                print("Error loading security config, using default")

    def save_config(self):
        os.makedirs(os.path.dirname(SECURITY_CONFIG_FILE), exist_ok=True)
        with open(SECURITY_CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=4)

    def record_action(self, guild_id, user_id, action):
        now = datetime.utcnow().timestamp()
        self.action_log.setdefault(guild_id, {}).setdefault(user_id, {}).setdefault(action, []).append(now)

    def is_suspicious(self, guild_id, user_id, action):
        now = datetime.utcnow().timestamp()
        if guild_id not in self.action_log or user_id not in self.action_log[guild_id] or action not in self.action_log[guild_id][user_id]:
            return False
        timestamps = self.action_log[guild_id][user_id][action]
        window = SUSPICIOUS_ACTIONS[action]['window']
        count = SUSPICIOUS_ACTIONS[action]['count']
        recent = [t for t in timestamps if now - t <= window]
        return len(recent) >= count

    async def alert(self, guild: discord.Guild, message: str):
        if self.config['log_channel_id']:
            channel = self.bot.get_channel(self.config['log_channel_id'])
            if channel:
                await channel.send(embed=discord.Embed(title="⚠️ Security Alert", description=message, color=discord.Color.red()))
        if self.config['alert_mode'] == 'dm_owner':
            try:
                await guild.owner.send(f"[Security Alert] {message}")
            except:
                pass

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        try:
            entries = await guild.audit_logs(limit=1, action=discord.AuditLogAction.ban).flatten()
            if not entries:
                return
            entry = entries[0]
            if entry.user.id in self.config['ignored_users']: 
                return
            self.record_action(guild.id, entry.user.id, 'mass_ban')
            if self.is_suspicious(guild.id, entry.user.id, 'mass_ban'):
                await self.alert(guild, f"{entry.user} is mass banning members!")
        except Exception as e:
            print(f"Error in on_member_ban: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        try:
            guild = member.guild
            # Check if it was a kick
            entries = await guild.audit_logs(limit=1, action=discord.AuditLogAction.kick).flatten()
            if not entries:
                return
            entry = entries[0]
            # Check if this audit log entry is recent (within last 2 seconds)
            if (datetime.utcnow() - entry.created_at).total_seconds() > 2:
                return  # Not a recent action
            if entry.user.id in self.config['ignored_users']: 
                return
            self.record_action(guild.id, entry.user.id, 'mass_kick')
            if self.is_suspicious(guild.id, entry.user.id, 'mass_kick'):
                await self.alert(guild, f"{entry.user} is mass kicking members!")
        except Exception as e:
            print(f"Error in on_member_remove: {e}")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        try:
            guild = channel.guild
            entries = await guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete).flatten()
            if not entries:
                return
            entry = entries[0]
            if entry.user.id in self.config['ignored_users']: 
                return
            self.record_action(guild.id, entry.user.id, 'channel_delete')
            if self.is_suspicious(guild.id, entry.user.id, 'channel_delete'):
                await self.alert(guild, f"{entry.user} is deleting multiple channels!")
        except Exception as e:
            print(f"Error in on_guild_channel_delete: {e}")

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        try:
            guild = role.guild
            entries = await guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete).flatten()
            if not entries:
                return
            entry = entries[0]
            if entry.user.id in self.config['ignored_users']: 
                return
            self.record_action(guild.id, entry.user.id, 'role_delete')
            if self.is_suspicious(guild.id, entry.user.id, 'role_delete'):
                await self.alert(guild, f"{entry.user} is deleting multiple roles!")
        except Exception as e:
            print(f"Error in on_guild_role_delete: {e}")

    @tasks.loop(minutes=1)
    async def cleanup_actions(self):
        now = datetime.utcnow().timestamp()
        for guild_id in list(self.action_log):
            for user_id in list(self.action_log[guild_id]):
                for action in list(self.action_log[guild_id][user_id]):
                    self.action_log[guild_id][user_id][action] = [
                        t for t in self.action_log[guild_id][user_id][action] if now - t <= 120
                    ]
                    # Clean up empty lists
                    if not self.action_log[guild_id][user_id][action]:
                        del self.action_log[guild_id][user_id][action]
                # Clean up empty user entries
                if not self.action_log[guild_id][user_id]:
                    del self.action_log[guild_id][user_id]
            # Clean up empty guild entries
            if not self.action_log[guild_id]:
                del self.action_log[guild_id]

    @cleanup_actions.before_loop
    async def before_cleanup(self):
        await self.bot.wait_until_ready()

    # Regular command group
    @commands.group(name="quarantine", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def quarantine_cmd(self, ctx):
        """Security monitoring configuration commands"""
        await ctx.send("Security monitoring commands. Use `quarantine set` to configure settings.")

    @quarantine_cmd.command(name="set")
    @commands.has_permissions(administrator=True)
    async def set_config_cmd(self, ctx, setting, *, value=None):
        """Configure security monitoring settings"""
        if setting == "log_channel":
            # Convert mention to ID if needed
            if value.startswith("<#") and value.endswith(">"):
                value = value[2:-1]
            
            try:
                channel_id = int(value)
                channel = ctx.guild.get_channel(channel_id)
                if not channel:
                    return await ctx.send("Invalid channel.")
                
                self.config['log_channel_id'] = channel_id
                self.save_config()
                await ctx.send(f"Security logs will be sent to {channel.mention}")
            except ValueError:
                await ctx.send("Please provide a valid channel ID or mention.")
                
        elif setting == "monitor_role":
            if value.startswith("<@&") and value.endswith(">"):
                value = value[3:-1]
                
            try:
                role_id = int(value)
                role = ctx.guild.get_role(role_id)
                if not role:
                    return await ctx.send("Invalid role.")
                
                if role_id not in self.config['staff_roles']:
                    self.config['staff_roles'].append(role_id)
                    self.save_config()
                    await ctx.send(f"Added {role.name} to monitored staff roles.")
                else:
                    await ctx.send(f"{role.name} is already being monitored.")
            except ValueError:
                await ctx.send("Please provide a valid role ID or mention.")
                
        elif setting == "ignore_user":
            if value.startswith("<@") and value.endswith(">"):
                value = value[2:-1]
                if value.startswith("!"):
                    value = value[1:]
                    
            try:
                user_id = int(value)
                user = ctx.guild.get_member(user_id)
                if not user:
                    return await ctx.send("Invalid user.")
                
                if user_id not in self.config['ignored_users']:
                    self.config['ignored_users'].append(user_id)
                    self.save_config()
                    await ctx.send(f"Added {user.name} to ignored users (their actions won't trigger alerts).")
                else:
                    await ctx.send(f"{user.name} is already being ignored.")
            except ValueError:
                await ctx.send("Please provide a valid user ID or mention.")
                
        elif setting == "alert_mode":
            valid_modes = ['log', 'dm_owner', 'auto_revert']
            if value not in valid_modes:
                return await ctx.send(f"Invalid mode. Choose from: {', '.join(valid_modes)}")
                
            self.config['alert_mode'] = value
            self.save_config()
            
            mode_descriptions = {
                'log': "Log events only",
                'dm_owner': "Log events and DM server owner on critical alerts",
                'auto_revert': "Log events, DM owner, and attempt to auto-revert dangerous changes"
            }
            
            await ctx.send(f"Alert mode set to: {value} - {mode_descriptions[value]}")
            
        else:
            await ctx.send("Unknown setting. Available settings: log_channel, monitor_role, ignore_user, alert_mode")

    @quarantine_cmd.command(name="status")
    @commands.has_permissions(administrator=True)
    async def show_status_cmd(self, ctx):
        """Show current security monitoring configuration"""
        embed = discord.Embed(
            title="Security Monitoring Status",
            color=discord.Color.blue(),
            description="Current configuration for staff activity monitoring"
        )
        
        # Log channel info
        if self.config.get('log_channel_id'):
            channel = ctx.guild.get_channel(int(self.config['log_channel_id']))
            channel_value = f"{channel.mention}" if channel else "Invalid channel"
        else:
            channel_value = "Not set"
        embed.add_field(name="Log Channel", value=channel_value, inline=False)
        
        # Staff roles being monitored
        staff_roles = []
        for role_id in self.config.get('staff_roles', []):
            role = ctx.guild.get_role(int(role_id))
            if role:
                staff_roles.append(f"{role.name}")
        
        embed.add_field(
            name="Monitored Staff Roles", 
            value=", ".join(staff_roles) if staff_roles else "None set",
            inline=False
        )
        
        # Ignored users
        ignored_users = []
        for user_id in self.config.get('ignored_users', []):
            user = ctx.guild.get_member(int(user_id))
            if user:
                ignored_users.append(f"{user.name}")
        
        embed.add_field(
            name="Ignored Users", 
            value=", ".join(ignored_users) if ignored_users else "None set",
            inline=False
        )
        
        # Alert mode
        mode_descriptions = {
            'log': "Log events only",
            'dm_owner': "Log events and DM server owner on critical alerts",
            'auto_revert': "Log events, DM owner, and attempt to auto-revert dangerous changes"
        }
        
        embed.add_field(
            name="Alert Mode", 
            value=f"{self.config.get('alert_mode', 'log')} - {mode_descriptions.get(self.config.get('alert_mode', 'log'), 'Unknown')}",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    # Command group
    quarantine = app_commands.Group(name="quarantine", description="Security monitoring configuration commands")

    @quarantine.command(name="set", description="Configure security monitoring settings")
    @app_commands.describe(setting="Setting to change", value="New value for the setting")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_config_slash(self, interaction: discord.Interaction, setting: str, value: str = None):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild

        if setting == "log_channel":
            if value.startswith("<#") and value.endswith(">"):
                value = value[2:-1]

            try:
                channel_id = int(value)
                channel = guild.get_channel(channel_id)
                if not channel:
                    return await interaction.followup.send("❌ Invalid channel.")

                self.config['log_channel_id'] = channel_id
                self.save_config()
                await interaction.followup.send(f"✅ Security logs will be sent to {channel.mention}")
            except ValueError:
                await interaction.followup.send("⚠️ Please provide a valid channel ID or mention.")

        elif setting == "monitor_role":
            if value.startswith("<@&") and value.endswith(">"):
                value = value[3:-1]

            try:
                role_id = int(value)
                role = guild.get_role(role_id)
                if not role:
                    return await interaction.followup.send("❌ Invalid role.")

                if role_id not in self.config['staff_roles']:
                    self.config['staff_roles'].append(role_id)
                    self.save_config()
                    await interaction.followup.send(f"✅ Added {role.name} to monitored staff roles.")
                else:
                    await interaction.followup.send(f"⚠️ {role.name} is already being monitored.")
            except ValueError:
                await interaction.followup.send("⚠️ Please provide a valid role ID or mention.")

        elif setting == "ignore_user":
            if value.startswith("<@") and value.endswith(">"):
                value = value[2:-1]
                if value.startswith("!"):
                    value = value[1:]

            try:
                user_id = int(value)
                user = guild.get_member(user_id)
                if not user:
                    return await interaction.followup.send("❌ Invalid user.")

                if user_id not in self.config['ignored_users']:
                    self.config['ignored_users'].append(user_id)
                    self.save_config()
                    await interaction.followup.send(f"✅ Added {user.name} to ignored users.")
                else:
                    await interaction.followup.send(f"⚠️ {user.name} is already being ignored.")
            except ValueError:
                await interaction.followup.send("⚠️ Please provide a valid user ID or mention.")

        elif setting == "alert_mode":
            valid_modes = ['log', 'dm_owner', 'auto_revert']
            if value not in valid_modes:
                return await interaction.followup.send(f"❌ Invalid mode. Choose from: {', '.join(valid_modes)}")

            self.config['alert_mode'] = value
            self.save_config()

            mode_descriptions = {
                'log': "Log events only",
                'dm_owner': "Log events and DM server owner on critical alerts",
                'auto_revert': "Log events, DM owner, and attempt to auto-revert dangerous changes"
            }

            await interaction.followup.send(f"✅ Alert mode set to: `{value}` - {mode_descriptions[value]}")
        else:
            await interaction.followup.send("❌ Unknown setting. Available settings: `log_channel`, `monitor_role`, `ignore_user`, `alert_mode`")

    @quarantine.command(name="status", description="Show current security monitoring configuration")
    @app_commands.checks.has_permissions(administrator=True)
    async def status_slash(self, interaction: discord.Interaction):
        guild = interaction.guild

        embed = discord.Embed(
            title="🔐 Security Monitoring Status",
            color=discord.Color.blue(),
            description="Current configuration for staff activity monitoring"
        )

        # Log channel
        channel_value = "Not set"
        if self.config.get('log_channel_id'):
            channel = guild.get_channel(self.config['log_channel_id'])
            channel_value = channel.mention if channel else "Invalid channel"
        embed.add_field(name="Log Channel", value=channel_value, inline=False)

        # Staff roles
        staff_roles = []
        for role_id in self.config.get('staff_roles', []):
            role = guild.get_role(role_id)
            if role:
                staff_roles.append(role.name)
        embed.add_field(
            name="Monitored Staff Roles",
            value=", ".join(staff_roles) if staff_roles else "None set",
            inline=False
        )

        # Ignored users
        ignored_users = []
        for user_id in self.config.get('ignored_users', []):
            user = guild.get_member(user_id)
            if user:
                ignored_users.append(user.name)
        embed.add_field(
            name="Ignored Users",
            value=", ".join(ignored_users) if ignored_users else "None set",
            inline=False
        )

        # Alert mode
        mode = self.config.get('alert_mode', 'log')
        mode_descriptions = {
            'log': "Log events only",
            'dm_owner': "Log events and DM server owner on critical alerts",
            'auto_revert': "Log events, DM owner, and attempt to auto-revert dangerous changes"
        }
        embed.add_field(
            name="Alert Mode",
            value=f"{mode} - {mode_descriptions.get(mode, 'Unknown')}",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    @app_commands.command(name="backup", description="Back up all roles and channels")
    @app_commands.checks.has_permissions(administrator=True)
    async def backup(self, interaction: discord.Interaction):
        guild = interaction.guild

        backup_data = {
            "roles": [],
            "channels": []
        }

        # Roles (excluding @everyone)
        for role in guild.roles:
            if role.is_default():
                continue
            backup_data["roles"].append({
                "name": role.name,
                "color": role.color.value,
                "hoist": role.hoist,
                "mentionable": role.mentionable,
                "permissions": role.permissions.value,
                "position": role.position
            })

        # Channels and their permission overwrites
        for channel in guild.channels:
            channel_data = {
                "name": channel.name,
                "type": str(channel.type),
                "position": channel.position,
                "category": channel.category.name if channel.category else None,
                "overwrites": {}
            }

            # Text channel extras
            if isinstance(channel, discord.TextChannel):
                channel_data.update({
                    "topic": channel.topic,
                    "nsfw": channel.nsfw,
                    "slowmode_delay": channel.slowmode_delay
                })

            # Voice channel extras
            elif isinstance(channel, discord.VoiceChannel):
                channel_data.update({
                    "bitrate": channel.bitrate,
                    "user_limit": channel.user_limit
                })

            # Permission overwrites for roles
            overwrites = {}
            for target, perms in channel.overwrites.items():
                if isinstance(target, discord.Role):
                    overwrites[target.name] = {
                        "allow": perms.pair()[0].value,
                        "deny": perms.pair()[1].value
                    }
            channel_data["overwrites"] = overwrites

            backup_data["channels"].append(channel_data)

        # Send file
        json_data = json.dumps(backup_data, indent=4)
        file = discord.File(io.BytesIO(json_data.encode()), filename=f"{guild.name}_backup.json")
        await interaction.response.send_message("📁 Backup created!", file=file)
        
    @app_commands.command(name="restore", description="Restore roles and channels from a backup JSON file")
    @app_commands.describe(file="The backup JSON file to restore from")
    @app_commands.checks.has_permissions(administrator=True)
    async def restore(self, interaction: discord.Interaction, file: discord.Attachment):
        if not file.filename.endswith(".json"):
            await interaction.response.send_message("Please upload a valid `.json` file.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        data = await file.read()
        try:
            backup_data = json.loads(data)
        except json.JSONDecodeError:
            await interaction.followup.send("❌ Failed to parse JSON file.", ephemeral=True)
            return

        guild = interaction.guild

        # Restore roles
        role_map = {}
        sorted_roles = sorted(backup_data.get("roles", []), key=lambda r: r["position"])
        for role_data in sorted_roles:
            try:
                new_role = await guild.create_role(
                    name=role_data["name"],
                    color=discord.Color(role_data["color"]),
                    hoist=role_data["hoist"],
                    mentionable=role_data["mentionable"],
                    permissions=discord.Permissions(role_data["permissions"]),
                    reason="Restoring from backup"
                )
                role_map[role_data["name"]] = new_role
            except Exception as e:
                print(f"[!] Error creating role {role_data['name']}: {e}")

        # Create categories first
        categories = {}
        for ch in backup_data.get("channels", []):
            if ch["type"] and "category" in ch["type"].lower():
                try:
                    cat = await guild.create_category(
                        name=ch["name"],
                        position=ch.get("position", 0)
                    )
                    categories[ch["name"]] = cat
                except Exception as e:
                    print(f"[!] Error creating category {ch['name']}: {e}")

        # Create channels
        for ch in backup_data.get("channels", []):
            if ch["type"] and "category" in ch["type"].lower():
                continue

            overwrites = {}
            for role_name, perms in ch.get("overwrites", {}).items():
                role = role_map.get(role_name)
                if role:
                    overwrites[role] = discord.PermissionOverwrite.from_pair(
                        discord.Permissions(perms["allow"]),
                        discord.Permissions(perms["deny"])
                    )

            category = categories.get(ch.get("category")) if ch.get("category") else None

            try:
                if ch["type"] and "text" in ch["type"].lower():
                    await guild.create_text_channel(
                        name=ch["name"],
                        topic=ch.get("topic"),
                        slowmode_delay=ch.get("slowmode_delay", 0),
                        nsfw=ch.get("nsfw", False),
                        position=ch.get("position", 0),
                        overwrites=overwrites,
                        category=category
                    )
                elif ch["type"] and "voice" in ch["type"].lower():
                    await guild.create_voice_channel(
                        name=ch["name"],
                        bitrate=ch.get("bitrate", 64000),
                        user_limit=ch.get("user_limit", 0),
                        position=ch.get("position", 0),
                        overwrites=overwrites,
                        category=category
                    )
            except Exception as e:
                print(f"[!] Error creating channel {ch['name']}: {e}")

        await interaction.followup.send("✅ Restore complete with roles, channels, and overwrites!", ephemeral=True)


async def setup(bot):
    await bot.add_cog(SecurityCog(bot))
