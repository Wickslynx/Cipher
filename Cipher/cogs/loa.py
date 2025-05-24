import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta
import json
import os

LOA_FILE = 'storage/LOA.json'
LOA_ROLE_ID = 1322405982462017546
GUILD_ID = 1223694900084867247

# Ensure storage directory exists
os.makedirs(os.path.dirname(LOA_FILE), exist_ok=True)

def load_loa_data():
    if os.path.exists(LOA_FILE):
        with open(LOA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_loa_data(data):
    with open(LOA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

class LOARequestModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="LOA Request Form")
        
        self.reason = discord.ui.TextInput(
            label="Reason for LOA",
            placeholder="Enter the reason for your leave of absence...",
            style=discord.TextStyle.paragraph,
            required=True
        )
        
        self.start_date = discord.ui.TextInput(
            label="Start Date (YYYY-MM-DD)",
            placeholder="e.g. 2025-04-20",
            required=True
        )
        
        self.end_date = discord.ui.TextInput(
            label="End Date (YYYY-MM-DD)",
            placeholder="e.g. 2025-05-01",
            required=True
        )
        
        # Add text input fields to modal
        self.add_item(self.reason)
        self.add_item(self.start_date)
        self.add_item(self.end_date)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse dates
            start = datetime.strptime(self.start_date.value, "%Y-%m-%d")
            end = datetime.strptime(self.end_date.value, "%Y-%m-%d")
            
            # Create embed for LOA request
            embed = discord.Embed(
                title="Leave of Absence Request",
                description=f"**Reason:** {self.reason.value}",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            
            embed.add_field(name="Staff Member", value=interaction.user.mention, inline=True)
            embed.add_field(name="Start Date", value=start.strftime("%B %d, %Y"), inline=True)
            embed.add_field(name="End Date", value=end.strftime("%B %d, %Y"), inline=True)
            embed.add_field(name="Duration", value=f"{(end - start).days + 1} days", inline=True)
            embed.set_footer(text=f"Requested by {interaction.user.name}")
            
            # Send the embed with approval buttons
            await interaction.response.send_message("Your LOA request has been submitted!", ephemeral=True)
            channel = interaction.channel
            await channel.send(embed=embed, view=ReactionButtons())
            
        except ValueError as e:
            await interaction.response.send_message(
                "Error: Invalid date format. Please use YYYY-MM-DD format.", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"An error occurred: {str(e)}", 
                ephemeral=True
            )

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
            loa_data[str(user_id)] = {
                'start_date': start, 
                'end_date': end,
                'approved_by': interaction.user.id,
                'approved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            save_loa_data(loa_data)
            
            member = interaction.guild.get_member(user_id)
            if member:
                role = interaction.guild.get_role(LOA_ROLE_ID)
                await member.add_roles(role)
                try:
                    await member.send(f"Your LOA request has been approved from {start_date_field.value} to {end_date_field.value}.")
                except:
                    pass  # User might have DMs closed
        
        for item in self.children:
            item.disabled = True
        
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("LOA approved!", ephemeral=True)
    
    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red, custom_id="deny_loa")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.add_field(name="Status", value=f"Denied by {interaction.user.mention}", inline=False)
        
        user_field = discord.utils.get(embed.fields, name="Staff Member")
        if user_field:
            user_id = int(''.join(filter(str.isdigit, user_field.value)))
            member = interaction.guild.get_member(user_id)
            if member:
                try:
                    await member.send("Your LOA request has been denied.")
                except:
                    pass  # User might have DMs closed
        
        for item in self.children:
            item.disabled = True
        
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("LOA denied.", ephemeral=True)

class LOAManageView(discord.ui.View):
    def __init__(self, user_id, loa_info):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.loa_info = loa_info
    
    @discord.ui.button(label="End LOA Early", style=discord.ButtonStyle.red)
    async def end_loa(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != int(self.user_id) and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You don't have permission to end this LOA.", ephemeral=True)
            return
        
        loa_data = load_loa_data()
        if str(self.user_id) in loa_data:
            del loa_data[str(self.user_id)]
            save_loa_data(loa_data)
            
            # Remove LOA role
            member = interaction.guild.get_member(int(self.user_id))
            if member:
                role = interaction.guild.get_role(LOA_ROLE_ID)
                await member.remove_roles(role)
            
            await interaction.response.send_message("LOA has been ended early.", ephemeral=True)
        else:
            await interaction.response.send_message("No active LOA found.", ephemeral=True)
        
        for item in self.children:
            item.disabled = True
        
        await interaction.message.edit(view=self)

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
                    try:
                        await user.send(f"Your LOA starts today and ends on {info['end_date']}.")
                    except:
                        pass  # User might have DMs closed
                
                if info['end_date'] == today:
                    try:
                        await user.send("Your LOA has ended.")
                    except:
                        pass  # User might have DMs closed
                    
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
    
    # Create the LOA command group
    loa = app_commands.Group(name="loa", description="Leave of Absence management commands")
        
    @loa.command(name="request", description="Request a LOA.")
    async def loa_request(self, interaction: discord.Interaction):
        """Opens a form to request a leave of absence"""
        await interaction.response.send_modal(LOARequestModal())
        
    @loa.command(name="manage", description="Manage a members LOA.")
    async def loa_manage(self, interaction: discord.Interaction, user: discord.Member = None):
        """View and manage LOA for yourself or another user (admin only)"""
        target_user = user or interaction.user
        
        # Check permissions if managing someone else's LOA
        if user and user.id != interaction.user.id and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You don't have permission to manage other users' LOAs.", ephemeral=True)
            return
        
        loa_data = load_loa_data()
        user_id = str(target_user.id)
        
        if user_id in loa_data:
            # User has an active LOA
            start_date = datetime.strptime(loa_data[user_id]['start_date'], '%Y-%m-%d')
            end_date = datetime.strptime(loa_data[user_id]['end_date'], '%Y-%m-%d')
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            if today < start_date:
                status = f"Starting in {(start_date - today).days} days"
            elif today <= end_date:
                status = f"{(end_date - today).days + 1} days remaining"
            else:
                status = "Ended (will be removed soon)"
            
            embed = discord.Embed(
                title="Leave of Absence Status",
                description=f"LOA status for {target_user.mention}",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="Start Date", value=start_date.strftime("%B %d, %Y"), inline=True)
            embed.add_field(name="End Date", value=end_date.strftime("%B %d, %Y"), inline=True)
            embed.add_field(name="Status", value=status, inline=True)
            embed.add_field(name="Total Duration", value=f"{(end_date - start_date).days + 1} days", inline=True)
            
            view = LOAManageView(user_id, loa_data[user_id]) if today <= end_date else None
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            # No active LOA
            embed = discord.Embed(
                title="Leave of Absence Status",
                description=f"{target_user.mention} has no active LOA.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
    @loa.command(name="view", description="Show all current LOA's.")
    async def loa_view(self, interaction: discord.Interaction):
        """View all active LOAs in the server"""
        loa_data = load_loa_data()
        
        if not loa_data:
            embed = discord.Embed(
                title="Active LOAs",
                description="There are no active LOAs at the moment.",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Active LOAs",
            description=f"There are currently {len(loa_data)} active LOAs.",
            color=discord.Color.blue()
        )
        
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for user_id, info in loa_data.items():
            try:
                user = await self.bot.fetch_user(int(user_id))
                start_date = datetime.strptime(info['start_date'], '%Y-%m-%d')
                end_date = datetime.strptime(info['end_date'], '%Y-%m-%d')
                
                if today < start_date:
                    status = f"Starting in {(start_date - today).days} days"
                elif today <= end_date:
                    status = f"{(end_date - today).days + 1} days remaining"
                else:
                    status = "Ended (will be removed soon)"
                
                value = f"**Period:** {start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}\n**Status:** {status}"
                embed.add_field(name=f"{user.name}", value=value, inline=False)
            except Exception as e:
                embed.add_field(name=f"User ID: {user_id}", value="Error loading user data", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(LOACog(bot))
    bot.add_view(ReactionButtons())
