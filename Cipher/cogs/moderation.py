import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json
from datetime import datetime


WICKS = 1159829981803860009
WARNINGS_FILE = 'storage/warnings.json'


class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_cog = self.bot.get_cog("ConfigCog")

    async def get_config(self, guild_id):
        guild_config = self.config_cog.get_guild_config(guild_id)
        self.MODERATION_LOG_CHANNEL_ID = guild_config.get("MOD_LOGS_CHANNEL_ID")
        self.moderator_role = guild_config.get("ADMIN_ROLE_ID")
        self.lr_role = guild_config.get("MOD_ROLE_ID")
        self.ia_role = guild_config.get("INTERNAL_AFFAIRS_ID")
        self.ot_role = guild_config.get("OT_ID")
        return guild_config

    def load_warnings(self):
        try:
            with open(WARNINGS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}

    def save_warnings(self, data):
        with open(WARNINGS_FILE, 'w') as f:
            json.dump(data, f, indent=4)

    def has_mod_role(self, member):
        return discord.utils.get(member.roles, id=self.moderator_role) is not None

    async def log_action(self, guild, title, description, color):
        channel = guild.get_channel(self.MODERATION_LOG_CHANNEL_ID)
        if channel:
            embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.utcnow())
            await channel.send(embed=embed)

    @app_commands.command(name="warn", description="Warn a member")
    async def warn(self, interaction: discord.Interaction, member: discord.Member, *, reason: str):
        await self.get_config(interaction.guild.id)

        if not any(role.id == self.moderator_role for role in interaction.user.roles):
            await interaction.response.send_message("You do not have permission to warn members.", ephemeral=True)
            return

        warnings = self.load_warnings()
        uid = str(member.id)
        warnings.setdefault(uid, []).append({
            'moderator_id': interaction.user.id,
            'reason': reason,
            'timestamp': datetime.utcnow().isoformat()
        })
        self.save_warnings(warnings)

        await self.log_action(interaction.guild, "Member Warned",
                              f"**User:** {member.mention}\n**Moderator:** {interaction.user.mention}\n**Reason:** {reason}",
                              discord.Color.yellow())
        try:
            await member.send(f"You have been warned in {interaction.guild.name}. Reason: {reason}")
        except:
            pass

        await interaction.response.send_message(f"{member.name} has been warned.", ephemeral=True)

    @app_commands.command(name="warnings", description="View warnings for a member")
    async def warnings(self, interaction: discord.Interaction, member: discord.Member):
        await self.get_config(interaction.guild.id)

        if not any(role.id == self.lr_role for role in interaction.user.roles):
            await interaction.response.send_message("You do not have permission to view warnings.", ephemeral=True)
            return

        warnings = self.load_warnings().get(str(member.id), [])
        if not warnings:
            await interaction.response.send_message(f"{member.display_name} has no warnings.", ephemeral=True)
            return

        embed = discord.Embed(title=f"Warnings for {member.display_name}", color=discord.Color.orange())
        for i, w in enumerate(warnings, 1):
            mod = interaction.guild.get_member(w['moderator_id'])
            embed.add_field(name=f"#{i} - {w['timestamp'][:10]}",
                            value=f"**By:** {mod.mention if mod else 'Unknown'}\n**Reason:** {w['reason']}",
                            inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="ban", description="Ban a member")
    async def ban(self, interaction: discord.Interaction, member: discord.Member, *, reason: str = "No reason provided"):
        await self.get_config(interaction.guild.id)

        if not any(role.id == self.ia_role for role in interaction.user.roles):
            await interaction.response.send_message("You do not have permission to ban members.", ephemeral=True)
            return

        try:
            await member.send(f"You have been banned from {interaction.guild.name}. Reason: {reason}")
        except:
            pass

        await member.ban(reason=reason)
        await self.log_action(interaction.guild, "Member Banned",
                              f"**User:** {member.mention}\n**Moderator:** {interaction.user.mention}\n**Reason:** {reason}",
                              discord.Color.red())
        await interaction.response.send_message(f"{member.name} has been banned.", ephemeral=True)

    @app_commands.command(name="unban", description="Unban a member")
    async def unban(self, interaction: discord.Interaction, user_id: str):
        await self.get_config(interaction.guild.id)

        if not any(role.id == self.ia_role for role in interaction.user.roles):
            await interaction.response.send_message("You do not have permission to unban members.", ephemeral=True)
            return

        try:
            user = await self.bot.fetch_user(int(user_id))
            await interaction.guild.unban(user)
            await self.log_action(interaction.guild, "Member Unbanned",
                                  f"**User:** {user.mention}\n**Moderator:** {interaction.user.mention}",
                                  discord.Color.green())
            await interaction.response.send_message(f"{user.name} has been unbanned.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Invalid user ID.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @app_commands.command(name="kick", description="Kick a member")
    async def kick(self, interaction: discord.Interaction, member: discord.Member, *, reason: str = "No reason provided"):
        await self.get_config(interaction.guild.id)

        if not any(role.id == self.moderator_role for role in interaction.user.roles):
            await interaction.response.send_message("You do not have permission to kick members.", ephemeral=True)
            return

        await member.kick(reason=reason)
        await self.log_action(interaction.guild, "Member Kicked",
                              f"**User:** {member.mention}\n**Moderator:** {interaction.user.mention}\n**Reason:** {reason}",
                              discord.Color.dark_orange())
        await interaction.response.send_message(f"{member.name} has been kicked.", ephemeral=True)

    @app_commands.command(name="lock", description="Lock a channel")
    async def lock(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        await self.get_config(interaction.guild.id)

        if not any(role.id == self.ot_role for role in interaction.user.roles):
            await interaction.response.send_message("You do not have permission to lock channels.", ephemeral=True)
            return

        channel = channel or interaction.channel
        overwrite = channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False
        await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.response.send_message(f"🔒 {channel.mention} is now locked.", ephemeral=True)

    @app_commands.command(name="unlock", description="Unlock a channel")
    async def unlock(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        await self.get_config(interaction.guild.id)

        if not any(role.id == self.ot_role for role in interaction.user.roles):
            await interaction.response.send_message("You do not have permission to unlock channels.", ephemeral=True)
            return

        channel = channel or interaction.channel
        overwrite = channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = True
        await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.response.send_message(f"🔓 {channel.mention} is now unlocked.", ephemeral=True)

    @app_commands.command(name="serverinfo", description="Display server information")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = discord.Embed(title=guild.name, description=f"ID: {guild.id}", color=discord.Color.blurple())
        embed.add_field(name="Members", value=guild.member_count)
        embed.add_field(name="Channels", value=len(guild.channels))
        embed.add_field(name="Roles", value=len(guild.roles))
        embed.set_thumbnail(url=guild.icon.url if guild.icon else discord.Embed.Empty)
        await interaction.response.send_message(embed=embed)

    role_group = app_commands.Group(name="role", description="Role-related commands")

    @role_group.command(name="add", description="Add a role to a user")
    async def add_role(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        await self.get_config(interaction.guild.id)

        if not any(role.id == self.moderator_role for role in interaction.user.roles):
            await interaction.response.send_message("You do not have permission to add roles.", ephemeral=True)
            return

        await member.add_roles(role)
        await interaction.response.send_message(f"✅ {role.name} added to {member.display_name}.", ephemeral=True)

    @role_group.command(name="remove", description="Remove a role from a user")
    async def remove_role(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        await self.get_config(interaction.guild.id)

        if not any(role.id == self.moderator_role for role in interaction.user.roles):
            await interaction.response.send_message("You do not have permission to remove roles.", ephemeral=True)
            return

        await member.remove_roles(role)
        await interaction.response.send_message(f"✅ {role.name} removed from {member.display_name}.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(ModerationCog(bot))

