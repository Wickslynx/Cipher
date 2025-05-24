import discord
from discord import app_commands
from discord.ext import commands
import random
import json
import os
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List

class EconomySystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = "economy_data.json"
        self.users = {}
        self.cooldowns = {}
        self.load_data()
    
    def load_data(self):
        """Load economy data from file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    self.users = json.load(f)
        except Exception as e:
            print(f"Error loading economy data: {e}")
            self.users = {}
    
    def save_data(self):
        """Save economy data to file"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.users, f, indent=4)
        except Exception as e:
            print(f"Error saving economy data: {e}")
    
    def get_user_data(self, user_id: str):
        """Get user data, returns None if not found"""
        return self.users.get(str(user_id))
    
    def create_user(self, user_id: str):
        """Create a new user account"""
        if str(user_id) in self.users:
            return False
        
        self.users[str(user_id)] = {
            "wallet": 1000,  # Starting amount
            "bank": 0,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.save_data()
        return True
    
    def check_cooldown(self, user_id: str, action: str, cooldown_seconds: int):
        """Check if user is on cooldown for an action"""
        user_id = str(user_id)
        
        if user_id not in self.cooldowns:
            self.cooldowns[user_id] = {}
        
        current_time = datetime.now()
        
        if action in self.cooldowns[user_id]:
            cooldown_end = self.cooldowns[user_id][action]
            if current_time < cooldown_end:
                time_left = (cooldown_end - current_time).total_seconds()
                return False, round(time_left)
        
        # Set cooldown
        self.cooldowns[user_id][action] = current_time + timedelta(seconds=cooldown_seconds)
        return True, 0
    
    # Command group for economy commands
    economy = app_commands.Group(name="economy", description="Economy related commands")
    
    @economy.command(name="create", description="Create your economy account")
    async def create_account(self, interaction: discord.Interaction):
        """Create a new economy account"""
        user_id = str(interaction.user.id)
        
        if self.get_user_data(user_id):
            await interaction.response.send_message("You already have an economy account!", ephemeral=True)
            return
        
        success = self.create_user(user_id)
        
        if success:
            embed = discord.Embed(
                title="Account Created!",
                description=f"Welcome to the economy system, {interaction.user.mention}!",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Starting Balance", value="1,000 coins", inline=False)
            embed.set_footer(text="Use /economy help for more information")
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("Failed to create your account. Please try again later.", ephemeral=True)
    
    @economy.command(name="balance", description="Check your economy balance")
    async def balance(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """Check your or another user's balance"""
        target = user if user else interaction.user
        user_id = str(target.id)
        user_data = self.get_user_data(user_id)
        
        if not user_data:
            if target == interaction.user:
                await interaction.response.send_message("You don't have an economy account yet. Use `/economy create` to make one!", ephemeral=True)
            else:
                await interaction.response.send_message(f"{target.display_name} doesn't have an economy account yet.", ephemeral=True)
            return
        
        wallet = user_data["wallet"]
        bank = user_data["bank"]
        
        embed = discord.Embed(
            title=f"{target.display_name}'s Balance",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        embed.add_field(name="👛 Wallet", value=f"{wallet:,} coins", inline=True)
        embed.add_field(name="🏦 Bank", value=f"{bank:,} coins", inline=True)
        embed.add_field(name="💰 Total", value=f"{wallet + bank:,} coins", inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @economy.command(name="work", description="Work to earn some coins")
    async def work(self, interaction: discord.Interaction):
        """Work to earn between 300-500 coins (with cooldown)"""
        user_id = str(interaction.user.id)
        user_data = self.get_user_data(user_id)
        
        if not user_data:
            await interaction.response.send_message("You don't have an economy account yet. Use `/economy create` to make one!", ephemeral=True)
            return
        
        # 1 hour cooldown
        can_work, time_left = self.check_cooldown(user_id, "work", 3600)
        
        if not can_work:
            minutes = int(time_left // 60)
            seconds = int(time_left % 60)
            await interaction.response.send_message(f"You're still tired from your last job! You can work again in {minutes} minutes and {seconds} seconds.", ephemeral=True)
            return
        
        # Random earnings between 300-500
        earnings = random.randint(300, 500)
        
        # Random work messages
        work_messages = [
            f"You worked as a programmer and earned {earnings} coins!",
            f"You delivered some packages and received {earnings} coins!",
            f"You helped moderate a Discord server and got {earnings} coins!",
            f"You wrote an article and got paid {earnings} coins!",
            f"You fixed someone's computer and earned {earnings} coins!"
        ]
        
        work_message = random.choice(work_messages)
        
        # Update user data
        user_data["wallet"] += earnings
        self.save_data()
        
        embed = discord.Embed(
            title="Work Completed!",
            description=work_message,
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Current Balance", value=f"{user_data['wallet']:,} coins in wallet", inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @economy.command(name="deposit", description="Deposit money into your bank")
    @app_commands.describe(amount="Amount to deposit (or 'all' for everything)")
    async def deposit(self, interaction: discord.Interaction, amount: str):
        """Deposit money from wallet to bank"""
        user_id = str(interaction.user.id)
        user_data = self.get_user_data(user_id)
        
        if not user_data:
            await interaction.response.send_message("You don't have an economy account yet. Use `/economy create` to make one!", ephemeral=True)
            return
        
        wallet = user_data["wallet"]
        
        # Check if the user has money to deposit
        if wallet <= 0:
            await interaction.response.send_message("You don't have any money in your wallet to deposit!", ephemeral=True)
            return
        
        # Handle 'all' amount
        if amount.lower() == "all":
            deposit_amount = wallet
        else:
            try:
                deposit_amount = int(amount)
                if deposit_amount <= 0:
                    await interaction.response.send_message("Please enter a positive amount to deposit.", ephemeral=True)
                    return
                
                if deposit_amount > wallet:
                    await interaction.response.send_message(f"You only have {wallet:,} coins in your wallet!", ephemeral=True)
                    return
                
            except ValueError:
                await interaction.response.send_message("Please enter a valid number or 'all'.", ephemeral=True)
                return
        
        # Update balances
        user_data["wallet"] -= deposit_amount
        user_data["bank"] += deposit_amount
        self.save_data()
        
        embed = discord.Embed(
            title="Money Deposited",
            description=f"You've safely deposited {deposit_amount:,} coins to your bank account.",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Wallet Balance", value=f"{user_data['wallet']:,} coins", inline=True)
        embed.add_field(name="Bank Balance", value=f"{user_data['bank']:,} coins", inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @economy.command(name="withdraw", description="Withdraw money from your bank")
    @app_commands.describe(amount="Amount to withdraw (or 'all' for everything)")
    async def withdraw(self, interaction: discord.Interaction, amount: str):
        """Withdraw money from bank to wallet"""
        user_id = str(interaction.user.id)
        user_data = self.get_user_data(user_id)
        
        if not user_data:
            await interaction.response.send_message("You don't have an economy account yet. Use `/economy create` to make one!", ephemeral=True)
            return
        
        bank = user_data["bank"]
        
        # Check if the user has money to withdraw
        if bank <= 0:
            await interaction.response.send_message("You don't have any money in your bank to withdraw!", ephemeral=True)
            return
        
        # Handle 'all' amount
        if amount.lower() == "all":
            withdraw_amount = bank
        else:
            try:
                withdraw_amount = int(amount)
                if withdraw_amount <= 0:
                    await interaction.response.send_message("Please enter a positive amount to withdraw.", ephemeral=True)
                    return
                
                if withdraw_amount > bank:
                    await interaction.response.send_message(f"You only have {bank:,} coins in your bank!", ephemeral=True)
                    return
                
            except ValueError:
                await interaction.response.send_message("Please enter a valid number or 'all'.", ephemeral=True)
                return
        
        # Update balances
        user_data["bank"] -= withdraw_amount
        user_data["wallet"] += withdraw_amount
        self.save_data()
        
        embed = discord.Embed(
            title="Money Withdrawn",
            description=f"You've withdrawn {withdraw_amount:,} coins from your bank account.",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Wallet Balance", value=f"{user_data['wallet']:,} coins", inline=True)
        embed.add_field(name="Bank Balance", value=f"{user_data['bank']:,} coins", inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @economy.command(name="rob", description="Attempt to rob another user")
    async def rob(self, interaction: discord.Interaction, target: discord.Member):
        """Try to rob another user's wallet"""
        # Don't allow robbing yourself
        if target.id == interaction.user.id:
            await interaction.response.send_message("You can't rob yourself!", ephemeral=True)
            return
        
        # Don't allow robbing bots
        if target.bot:
            await interaction.response.send_message("You can't rob bots!", ephemeral=True)
            return
        
        robber_id = str(interaction.user.id)
        target_id = str(target.id)
        
        robber_data = self.get_user_data(robber_id)
        target_data = self.get_user_data(target_id)
        
        if not robber_data:
            await interaction.response.send_message("You don't have an economy account yet. Use `/economy create` to make one!", ephemeral=True)
            return
        
        if not target_data:
            await interaction.response.send_message(f"{target.display_name} doesn't have an economy account to rob!", ephemeral=True)
            return
        
        # Check cooldown (1 hour)
        can_rob, time_left = self.check_cooldown(robber_id, "rob", 3600)
        
        if not can_rob:
            minutes = int(time_left // 60)
            seconds = int(time_left % 60)
            await interaction.response.send_message(f"You're still laying low after your last robbery attempt! You can rob again in {minutes} minutes and {seconds} seconds.", ephemeral=True)
            return
        
        # Check if target has money to steal
        if target_data["wallet"] < 100:
            await interaction.response.send_message(f"{target.display_name} doesn't have enough coins in their wallet to be worth robbing!", ephemeral=True)
            return
        
        # Random success chance (40%)
        success = random.random() < 0.4
        
        if success:
            # Steal between 10-30% of their wallet
            steal_percentage = random.uniform(0.1, 0.3)
            amount_stolen = int(target_data["wallet"] * steal_percentage)
            
            if amount_stolen < 1:
                amount_stolen = 1
            
            # Update balances
            target_data["wallet"] -= amount_stolen
            robber_data["wallet"] += amount_stolen
            self.save_data()
            
            embed = discord.Embed(
                title="Robbery Successful!",
                description=f"You successfully robbed {target.display_name} and got away with {amount_stolen:,} coins!",
                color=discord.Color.dark_green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Your Wallet", value=f"{robber_data['wallet']:,} coins", inline=True)
            
            await interaction.response.send_message(embed=embed)
        else:
            # Failed robbery - lose some money
            fine = int(robber_data["wallet"] * 0.05)  # 5% fine
            
            if fine < 10:
                fine = 10
            
            if fine > robber_data["wallet"]:
                fine = robber_data["wallet"]
            
            robber_data["wallet"] -= fine
            self.save_data()
            
            embed = discord.Embed(
                title="Robbery Failed!",
                description=f"You were caught trying to rob {target.display_name}!",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Fine Paid", value=f"{fine:,} coins", inline=True)
            embed.add_field(name="Your Wallet", value=f"{robber_data['wallet']:,} coins", inline=True)
            
            await interaction.response.send_message(embed=embed)
    
    @economy.command(name="pay", description="Pay another user")
    async def pay(self, interaction: discord.Interaction, recipient: discord.Member, amount: int):
        """Pay another user from your wallet"""
        # Don't allow paying yourself
        if recipient.id == interaction.user.id:
            await interaction.response.send_message("You can't pay yourself!", ephemeral=True)
            return
        
        # Don't allow paying bots
        if recipient.bot:
            await interaction.response.send_message("You can't pay bots!", ephemeral=True)
            return
        
        # Validate amount
        if amount <= 0:
            await interaction.response.send_message("Please enter a positive amount to pay.", ephemeral=True)
            return
        
        payer_id = str(interaction.user.id)
        recipient_id = str(recipient.id)
        
        payer_data = self.get_user_data(payer_id)
        recipient_data = self.get_user_data(recipient_id)
        
        if not payer_data:
            await interaction.response.send_message("You don't have an economy account yet. Use `/economy create` to make one!", ephemeral=True)
            return
        
        if not recipient_data:
            await interaction.response.send_message(f"{recipient.display_name} doesn't have an economy account yet!", ephemeral=True)
            return
        
        # Check if payer has enough money
        if payer_data["wallet"] < amount:
            await interaction.response.send_message(f"You don't have enough coins in your wallet! You have {payer_data['wallet']:,} coins.", ephemeral=True)
            return
        
        # Transfer money
        payer_data["wallet"] -= amount
        recipient_data["wallet"] += amount
        self.save_data()
        
        embed = discord.Embed(
            title="Payment Sent",
            description=f"You've sent {amount:,} coins to {recipient.display_name}!",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Your Wallet", value=f"{payer_data['wallet']:,} coins", inline=True)
        
        await interaction.response.send_message(embed=embed)
        
        # Send confirmation to recipient if not ephemeral
        try:
            recipient_embed = discord.Embed(
                title="Payment Received",
                description=f"You've received {amount:,} coins from {interaction.user.display_name}!",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            recipient_embed.add_field(name="Your Wallet", value=f"{recipient_data['wallet']:,} coins", inline=True)
            
            await recipient.send(embed=recipient_embed)
        except:
            # If we can't DM them, just continue
            pass
    
    @economy.command(name="leaderboard", description="Show the economy leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        """Show the server's economy leaderboard"""
        if not self.users:
            await interaction.response.send_message("There are no economy accounts yet!", ephemeral=True)
            return
        
        # Calculate total wealth for each user (wallet + bank)
        user_totals = []
        for user_id, data in self.users.items():
            total = data["wallet"] + data["bank"]
            user_totals.append((user_id, total))
        
        # Sort by total wealth (descending)
        user_totals.sort(key=lambda x: x[1], reverse=True)
        
        # Create leaderboard embed
        embed = discord.Embed(
            title="Economy Leaderboard",
            description="Top 10 richest users:",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        # Add top 10 users to leaderboard
        for index, (user_id, total) in enumerate(user_totals[:10], start=1):
            try:
                user = await self.bot.fetch_user(int(user_id))
                username = user.display_name
            except:
                username = f"User {user_id}"
            
            embed.add_field(
                name=f"{index}. {username}",
                value=f"{total:,} coins",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @economy.command(name="help", description="View information about economy commands")
    async def help(self, interaction: discord.Interaction):
        """Show help for economy commands"""
        embed = discord.Embed(
            title="Economy System Help",
            description="Here are all the economy commands you can use:",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="/economy create",
            value="Create your economy account and get 1,000 starting coins",
            inline=False
        )
        
        embed.add_field(
            name="/economy balance [user]",
            value="Check your balance or another user's balance",
            inline=False
        )
        
        embed.add_field(
            name="/economy work",
            value="Work to earn 300-500 coins (1 hour cooldown)",
            inline=False
        )
        
        embed.add_field(
            name="/economy deposit <amount>",
            value="Deposit money to your bank (safe from robberies)",
            inline=False
        )
        
        embed.add_field(
            name="/economy withdraw <amount>",
            value="Withdraw money from your bank to your wallet",
            inline=False
        )
        
        embed.add_field(
            name="/economy rob <user>",
            value="Try to rob another user's wallet (1 hour cooldown)",
            inline=False
        )
        
        embed.add_field(
            name="/economy pay <user> <amount>",
            value="Pay another user from your wallet",
            inline=False
        )
        
        embed.add_field(
            name="/economy leaderboard",
            value="See the richest users on the server",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(EconomySystem(bot))
