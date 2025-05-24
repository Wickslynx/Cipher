import discord
from discord.ext import commands
from datetime import datetime
import os

LOG_CHANNEL_ID = 123456789012345678  # Replace with your logging channel ID
LOG_DIR = "storage/logs"
os.makedirs(LOG_DIR, exist_ok=True)

class LoggingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def write_log_file(self, guild_id, text):
        filename = os.path.join(LOG_DIR, f"{guild_id}_events.txt")
        with open(filename, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.utcnow().isoformat()} - {text}\n")

    async def log_to_channel(self, guild: discord.Guild, text, color=discord.Color.dark_gray()):
        log_channel = guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(description=text, color=color, timestamp=datetime.utcnow())
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.guild:
            content = f"🗑️ Message deleted in {message.channel.mention} by {message.author}: {message.content}"
            self.write_log_file(message.guild.id, content)
            await self.log_to_channel(message.guild, content, color=discord.Color.red())

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.guild and before.content != after.content:
            content = (f"✏️ Message edited in {before.channel.mention} by {before.author}:\n"
                       f"Before: {before.content}\nAfter: {after.content}")
            self.write_log_file(before.guild.id, content)
            await self.log_to_channel(before.guild, content, color=discord.Color.orange())

    @commands.Cog.listener()
    async def on_member_join(self, member):
        content = f"✅ {member} joined the server."
        self.write_log_file(member.guild.id, content)
        await self.log_to_channel(member.guild, content, color=discord.Color.green())

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        content = f"❌ {member} left or was kicked."
        self.write_log_file(member.guild.id, content)
        await self.log_to_channel(member.guild, content, color=discord.Color.red())

async def setup(bot):
    await bot.add_cog(LoggingCog(bot))
