import discord
from discord.ext import commands
import os

# Intents setup
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.reactions = True

# Create bot instance
bot = commands.Bot(
    command_prefix=';',
    intents=intents,
    application_id=1361017411746136145
)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s).")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


# Load all cogs
async def load_cogs():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await bot.load_extension(f'cogs.{filename[:-3]}')


async def main():
    async with bot:
        await load_cogs()
        await bot.start('BOT_TOKEN')


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())

