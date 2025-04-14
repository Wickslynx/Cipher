import discord
from discord.ext import commands, tasks
from datetime import datetime
import json
import os

LOA_FILE = 'storage/LOA.json'
LOA_ROLE_ID = 1322405982462017546
GUILD_ID = 1223694900084867247

class ReactionButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green, custom_id="approve_loa")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.add_field(name="Status", value=f"Approved by {interaction.user.mention}", inline=False)

        user_field = discord.utils.get(embed.fields, name="Staff Member")
        start_date_field = discord.utils.get(embed.fields, name="Start Date")
        end_date_field = discord.utils.get(embed.fields, name="End Date")

        if all([user_field, start_date_field, end_date_field]):
            user_id = int(''.join(filter(str.isdigit, user_field.value)))
            start = datetime.strptime(start_date_field.value, "%B %d, %Y").strftime('%Y-%m-%d')
            end = datetime.strptime(end_date_field.value, "%B %d, %Y").strftime('%Y-%m-%d')

            loa_data = load_loa_data()
            loa_data[str(user_id)] = {'start_date': start, 'end_date': end}
            save_loa_data(loa_data)

            member = interaction.guild.get_member(user_id)
            if member:
                role = interaction.guild.get_role(LOA_ROLE_ID)
                await member.add_roles(role)

        for item in self.children:
            item.disabled = True

        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("LOA approved!", ephemeral=True)

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red, custom_id="deny_loa")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.add_field(name="Status", value=f"Denied by {interaction.user.mention}", inline=False)

        for item in self.children:
            item.disabled = True

        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("LOA denied.", ephemeral=True)


def load_loa_data():
    if os.path.exists(LOA_FILE):
        with open(LOA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_loa_data(data):
    with open(LOA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

class LOACog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_check.start()

    @tasks.loop(time=datetime.strptime("00:00", "%H:%M").time())
    async def daily_check(self):
        today = datetime.now().strftime('%Y-%m-%d')
        loa_data = load_loa_data()
        guild = self.bot.get_guild(GUILD_ID)

        for user_id, info in list(loa_data.items()):
            try:
                user = await self.bot.fetch_user(int(user_id))
                if info['start_date'] == today:
                    await user.send(f"Your LOA starts today and ends on {info['end_date']}.")
                if info['end_date'] == today:
                    await user.send("Your LOA has ended.")
                    member = guild.get_member(int(user_id))
                    if member:
                        role = guild.get_role(LOA_ROLE_ID)
                        await member.remove_roles(role)
                    del loa_data[user_id]
            except Exception as e:
                print(f"LOA check error for user {user_id}: {e}")

        save_loa_data(loa_data)

    @daily_check.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(LOACog(bot))
    bot.add_view(ReactionButtons())

