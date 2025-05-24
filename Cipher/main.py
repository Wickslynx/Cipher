import discord 
from discord.ext import commands
from discord import app_commands
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
    application_id=
)



# ---------- INLINE COMMANDS -----------------

REQUIRED_ROLE_ID = 0000000000


@bot.tree.command(name="say", description="Send a message as Cipher.")
async def say(interaction: discord.Interaction, message: str):
    role = discord.utils.get(interaction.guild.roles, id=REQUIRED_ROLE_ID)
    if role in interaction.user.roles:
        await interaction.response.send_message("Message sent!", ephemeral=True)
        await interaction.channel.send(message)
    else:
        await interaction.response.send_message(f'Sorry {interaction.user.mention}, you do not have the required role to run this command.', ephemeral=True)

@bot.tree.command(name="dashboard", description="Get the link to this server's dashboard")
async def dashboard(interaction: discord.Interaction):
    await interaction.response.send_message(f"The link to this server's dashboard is https://PLACEHOLDER/{interaction.guild.id}/", ephemeral=True)



# -------------------------------------------


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
    await bot.load_extension("cogs.cog")
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await bot.load_extension(f'cogs.{filename[:-3]}')


async def main():
    async with bot:
        await load_cogs()

        await bot.start('')


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())

