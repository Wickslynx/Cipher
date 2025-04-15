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
        
        # Check if user has the moderator role
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
        
        # Check if user has the lr role
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

    @app_commands.command(name="roleinfo", description="Get info on a role")
    async def roleinfo(self, interaction: discord.Interaction, role: discord.Role):
        embed = discord.Embed(title=role.name, color=role.color)
        embed.add_field(name="ID", value=role.id)
        embed.add_field(name="Members", value=len(role.members))
        embed.add_field(name="Mentionable", value=role.mentionable)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="add_role", description="Add a role to a user")
    async def add_role(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        await self.get_config(interaction.guild.id)
        
        if not any(r.id == self.ia_role for r in interaction.user.roles):
            await interaction.response.send_message("You do not have permission to add roles to members.", ephemeral=True)
            return
            
        await member.add_roles(role)
        await interaction.response.send_message(f"Added {role.name} to {member.mention}.", ephemeral=True)

    @app_commands.command(name="remove_role", description="Remove a role from a user")
    async def remove_role(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        await self.get_config(interaction.guild.id)
        
        if not any(r.id == self.ia_role for r in interaction.user.roles):
            await interaction.response.send_message("You do not have permission to remove roles from members.", ephemeral=True)
            return
            
        await member.remove_roles(role)
        await interaction.response.send_message(f"Removed {role.name} from {member.mention}.", ephemeral=True)
        
    @app_commands.command(name="nick", description="Change a user's nickname")
    @app_commands.describe(member="The user to change the nickname of", nickname="The new nickname")
    async def nick(self, interaction: discord.Interaction, member: discord.Member, nickname: str):
        await self.get_config(interaction.guild.id)
        
        if not any(role.id == self.moderator_role for role in interaction.user.roles):
            await interaction.response.send_message("You do not have permission to change members nicknames.", ephemeral=True)
            return
            
        try:
            await member.edit(nick=nickname)
            await interaction.response.send_message(f"Changed {member.mention}'s nickname to `{nickname}` ✅", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to change that user's nickname.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: `{e}`", ephemeral=True)
            
    @app_commands.command(name="delete", description="Delete messages containing a specific word in this channel")
    async def delete_word(self, interaction: discord.Interaction, word: str):
        await interaction.response.defer(ephemeral=True)
        await self.get_config(interaction.guild.id)
        
        deleted_count = 0
        error_count = 0
        channel = interaction.channel
        
        if not any(role.id == self.ot_role for role in interaction.user.roles) and interaction.user.id != WICKS:
            await interaction.followup.send("You do not have permission to use this command.", ephemeral=True)
            return

        if isinstance(channel, discord.TextChannel) and channel.permissions_for(interaction.guild.me).read_messages and channel.permissions_for(interaction.guild.me).manage_messages:
            try:
                async for message in channel.history(limit=10000):
                    if word.lower() in message.content.lower():
                        try:
                            await message.delete()
                            deleted_count += 1
                            await asyncio.sleep(0.5)
                        except discord.errors.Forbidden:
                            error_count += 1
                        except Exception as e:
                            print(f"Error deleting message: {e}")
                            error_count += 1
            except Exception as e:
                print(f"Error checking channel {channel.name}: {e}")
        else:
            await interaction.followup.send("Oops! I can't read messages or delete them in this channel.", ephemeral=True)
            return

        await interaction.followup.send(f"Finished filtering in this channel! Deleted {deleted_count} messages containing '{word}'. Failed to delete {error_count} messages.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(ModerationCog(bot))
