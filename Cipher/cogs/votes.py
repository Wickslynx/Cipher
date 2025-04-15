import discord
from discord.ext import commands
import json
import os

VOTE_FILE = 'storage/vote_counts.json'

vote_counts = {}

def load_votes():
    global vote_counts
    if os.path.exists(VOTE_FILE):
        with open(VOTE_FILE, 'r') as f:
            vote_counts = json.load(f)
    else:
        vote_counts = {}

def save_votes():
    with open(VOTE_FILE, 'w') as f:
        json.dump(vote_counts, f, indent=4)

class VoteView(discord.ui.View):
    def __init__(self, message_id: str):
        super().__init__(timeout=None)
        self.message_id = str(message_id)
        if self.message_id not in vote_counts:
            vote_counts[self.message_id] = {'up': 0, 'down': 0}

    @discord.ui.button(label="✔️ 0", style=discord.ButtonStyle.success, custom_id="upvote")
    async def upvote(self, interaction: discord.Interaction, button: discord.ui.Button):
        vote_counts[self.message_id]['up'] += 1
        save_votes()
        button.label = f"✔️ {vote_counts[self.message_id]['up']}"
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="🗙 0", style=discord.ButtonStyle.danger, custom_id="downvote")
    async def downvote(self, interaction: discord.Interaction, button: discord.ui.Button):
        vote_counts[self.message_id]['down'] += 1
        save_votes()
        button.label = f"🗙 {vote_counts[self.message_id]['down']}"
        await interaction.response.edit_message(view=self)

class VoteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        load_votes()

    @commands.command(name="vote_embed")
    async def vote_embed(self, ctx: commands.Context):
        embed = discord.Embed(title="🗳️ Cast Your Vote!", description="React below to vote.", color=discord.Color.blurple())
        message = await ctx.send(embed=embed, view=VoteView(message_id=str(ctx.message.id)))


async def setup(bot):
    await bot.add_cog(VoteCog(bot))

