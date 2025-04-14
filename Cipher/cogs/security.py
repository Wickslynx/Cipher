import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import json
import os

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
        if os.path.exists(SECURITY_CONFIG_FILE):
            with open(SECURITY_CONFIG_FILE, 'r') as f:
                self.config.update(json.load(f))

    def save_config(self):
        with open(SECURITY_CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=4)

    def record_action(self, guild_id, user_id, action):
        now = datetime.utcnow().timestamp()
        self.action_log.setdefault(guild_id, {}).setdefault(user_id, {}).setdefault(action, []).append(now)

    def is_suspicious(self, guild_id, user_id, action):
        timestamps = self.action_log[guild_id][user_id][action]
        window = SUSPICIOUS_ACTIONS[action]['window']
        count = SUSPICIOUS_ACTIONS[action]['count']
        recent = [t for t in timestamps if now - t <= window]
        return len(recent) >= count

    async def alert(self, guild: discord.Guild, message: str):
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
        entry = (await guild.audit_logs(limit=1, action=discord.AuditLogAction.ban).flatten())[0]
        if entry.user.id in self.config['ignored_users']: return
        self.record_action(guild.id, entry.user.id, 'mass_ban')
        if self.is_suspicious(guild.id, entry.user.id, 'mass_ban'):
            await self.alert(guild, f"{entry.user} is mass banning members!")

    @commands.Cog.listener()
    async def on_member_kick(self, member):
        guild = member.guild
        entry = (await guild.audit_logs(limit=1, action=discord.AuditLogAction.kick).flatten())[0]
        if entry.user.id in self.config['ignored_users']: return
        self.record_action(guild.id, entry.user.id, 'mass_kick')
        if self.is_suspicious(guild.id, entry.user.id, 'mass_kick'):
            await self.alert(guild, f"{entry.user} is mass kicking members!")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        guild = channel.guild
        entry = (await guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete).flatten())[0]
        if entry.user.id in self.config['ignored_users']: return
        self.record_action(guild.id, entry.user.id, 'channel_delete')
        if self.is_suspicious(guild.id, entry.user.id, 'channel_delete'):
            await self.alert(guild, f"{entry.user} is deleting multiple channels!")

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        guild = role.guild
        entry = (await guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete).flatten())[0]
        if entry.user.id in self.config['ignored_users']: return
        self.record_action(guild.id, entry.user.id, 'role_delete')
        if self.is_suspicious(guild.id, entry.user.id, 'role_delete'):
            await self.alert(guild, f"{entry.user} is deleting multiple roles!")

    @tasks.loop(minutes=1)
    async def cleanup_actions(self):
        now = datetime.utcnow().timestamp()
        for guild_id in list(self.action_log):
            for user_id in list(self.action_log[guild_id]):
                for action in list(self.action_log[guild_id][user_id]):
                    self.action_log[guild_id][user_id][action] = [
                        t for t in self.action_log[guild_id][user_id][action] if now - t <= 120
                    ]

    @cleanup_actions.before_loop
    async def before_cleanup(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(SecurityCog(bot))

