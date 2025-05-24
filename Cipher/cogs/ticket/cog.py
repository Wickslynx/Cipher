
from discord.ext import commands
from .config import TicketSystem
from .views import TicketCreateView, TicketCloseView, TicketConfigView
from discord import app_commands
import discord

class Ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.system = TicketSystem(bot)
        self.system.load_config()
        
	
    ticket = app_commands.Group(name="ticket", description="Ticket related commands.")
    
    
    @ticket.command(name="setup", description="Send the ticket creation panel")
    async def ticket_setup(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You need admin permissions.", ephemeral=True)
            return
        embed = discord.Embed(title="🎫 Create a Ticket",
                              description="Use the dropdown below to open a ticket.",
                              color=discord.Color.blue())
        view = TicketCreateView(self.system)
        await interaction.response.send_message("Setup complete.", ephemeral=True)
        await interaction.channel.send(embed=embed, view=view)

    @ticket.command(name="close", description="Close the current ticket")
    async def ticket_close(self, interaction: discord.Interaction):
        view = TicketCloseView(self.system, "AUTO")
        await interaction.response.send_message("Why are you closing the ticket?", view=view, ephemeral=True)

    @ticket.command(name="claim", description="Claim this ticket")
    async def ticket_claim(self, interaction: discord.Interaction):
        await interaction.channel.edit(name=f"{interaction.channel.name}-claimed")
        await interaction.response.send_message("Ticket claimed.", ephemeral=True)

    @ticket.command(name="unclaim", description="Unclaim this ticket")
    async def ticket_unclaim(self, interaction: discord.Interaction):
        if "-claimed" in interaction.channel.name:
            new_name = interaction.channel.name.replace("-claimed", "")
            await interaction.channel.edit(name=new_name)
            await interaction.response.send_message("Ticket unclaimed.", ephemeral=True)
        else:
            await interaction.response.send_message("This ticket is not claimed.", ephemeral=True)

    @ticket.command(name="add", description="Add a member to this ticket")
    async def ticket_add(self, interaction: discord.Interaction, member: discord.Member):
	 if not interaction.channel.name.startswith(("support-", "report-", "appeal-", "paid-ad-")):
	   	await interaction.response.send_message(
			"This command can only be used in a ticket channel.", 
			ephemeral=True
		)
		return
		
        await interaction.channel.set_permissions(member, read_messages=True, send_messages=True)
        await interaction.response.send_message(f"{member.mention} added to the ticket.", ephemeral=True)
        
    @ticket.command(name="remove", description="Remove a user from the current ticket")
    async def ticket_remove(interaction: discord.Interaction, member: discord.Member):
		
	 """Remove a user from the current ticket channel."""
	 # Verify this is a ticket channel
	 if not interaction.channel.name.startswith(("support-", "report-", "appeal-", "paid-ad-")):
	   	await interaction.response.send_message(
		    "This command can only be used in a ticket channel.", 
		    ephemeral=True
		)
		return
        
    	await interaction.channel.set_permissions(member, read_messages=False, send_messages=False)
    	await interaction.response.send_message(f"{member.mention} has been removed from the ticket.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Ticket(bot))
