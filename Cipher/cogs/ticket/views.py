
import discord
import asyncio

OT_ID = 111111111111111111
INTERNAL_AFFAIRS_ID = 222222222222222222
TICKET_CATEGORY_ID = 444444444444444444
TICKET_LOGS_CHANNEL_ID = 333333333333333333

class TicketCreateView(discord.ui.View):
    def __init__(self, ticket_system):
        super().__init__(timeout=None)
        self.ticket_system = ticket_system

    @discord.ui.select(
        placeholder="Select ticket type",
        options=[
            discord.SelectOption(label="Support", value="support"),
            discord.SelectOption(label="Appeal", value="appeal"),
            discord.SelectOption(label="Report", value="report"),
            discord.SelectOption(label="Ad Inquiry", value="paid-ad")
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(f"Creating a {select.values[0]} ticket...", ephemeral=True)

        ticket_id = self.ticket_system.generate_ticket_id()
        name = f"{select.values[0]}-{interaction.user.name[:4]}-{ticket_id}"

        category = interaction.guild.get_channel(TICKET_CATEGORY_ID)
        if not category:
            await interaction.followup.send("Category not found.", ephemeral=True)
            return

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.get_role(OT_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.get_role(INTERNAL_AFFAIRS_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        channel = await interaction.guild.create_text_channel(name, category=category, overwrites=overwrites)
        self.ticket_system.active_tickets.setdefault(interaction.guild.id, {})[ticket_id] = {
            "channel_id": channel.id,
            "creator": interaction.user.id,
            "type": select.values[0]
        }

        embed = discord.Embed(title=f"{select.values[0].capitalize()} Ticket",
                              description="A staff member will be with you shortly.",
                              color=discord.Color.blue())
        await channel.send(content=interaction.user.mention, embed=embed)
        await interaction.followup.send(f"✅ Ticket created: {channel.mention}", ephemeral=True)

class TicketCloseView(discord.ui.View):
    def __init__(self, ticket_system, ticket_id):
        super().__init__(timeout=30)
        self.ticket_system = ticket_system
        self.ticket_id = ticket_id

    @discord.ui.button(label="Solved", style=discord.ButtonStyle.green)
    async def solved(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.close_ticket(interaction, "Solved")

    @discord.ui.button(label="No Response", style=discord.ButtonStyle.gray)
    async def no_response(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.close_ticket(interaction, "User didn't respond")

    @discord.ui.button(label="Other", style=discord.ButtonStyle.red)
    async def other(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.close_ticket(interaction, "Other")

    async def close_ticket(self, interaction: discord.Interaction, reason: str):
        embed = discord.Embed(title="Ticket Closed",
                              description=f"Closed by {interaction.user.mention}\nReason: {reason}",
                              color=discord.Color.red())
        log_channel = interaction.guild.get_channel(TICKET_LOGS_CHANNEL_ID)
        if log_channel:
            await log_channel.send(embed=embed)
        await interaction.channel.send("Closing ticket in 3 seconds...")
        await asyncio.sleep(3)
        await interaction.channel.delete()

class TicketConfigModal(discord.ui.Modal):
    def __init__(self, title: str, default_text: str = ""):
        super().__init__(title=title)
        self.message_input = discord.ui.TextInput(
            label="Enter your message",
            style=discord.TextStyle.paragraph,
            placeholder="Enter your custom message here...",
            default=default_text,
            required=True,
            max_length=1000
        )
        self.add_item(self.message_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        return self.message_input.value

class TicketConfigView(discord.ui.View):
    def __init__(self, ticket_system):
        super().__init__(timeout=300)
        self.ticket_system = ticket_system

    @discord.ui.select(
        custom_id="ticket_config_select", 
        placeholder="Select what to configure", 
        min_values=1, 
        max_values=1,
        options=[
            discord.SelectOption(label="Welcome Message", value="welcome_message"),
            discord.SelectOption(label="Support Ticket Message", value="support_message"),
            discord.SelectOption(label="Report Ticket Message", value="report_message"),
            discord.SelectOption(label="Appeal Ticket Message", value="appeal_message"),
            discord.SelectOption(label="Partnership/Ad Ticket Message", value="paid_ad_message"),
            discord.SelectOption(label="Set Ticket Banner", value="ticket_banner"),
            discord.SelectOption(label="Preview Current Settings", value="preview")
        ]
    )
    async def config_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        guild_id = interaction.guild.id

        if guild_id not in self.ticket_system.ticket_config:
            self.ticket_system.ticket_config[guild_id] = {
                'welcome_message': "Welcome to ticket support!",
                'support_message': "Please describe your issue.",
                'report_message': "Please provide evidence.",
                'appeal_message': "Explain your appeal.",
                'paid_ad_message': "Describe your ad request.",
                'ticket_banner': None
            }

        config = self.ticket_system.ticket_config[guild_id]
        selected_option = select.values[0]

        if selected_option == "preview":
            embed = discord.Embed(title="Current Ticket Configuration", color=discord.Color.blue())
            for key, value in config.items():
                if key != "ticket_banner":
                    embed.add_field(name=key.replace('_', ' ').title(), value=value, inline=False)
            banner_status = "Set" if config.get('ticket_banner') else "Not set"
            embed.add_field(name="Ticket Banner", value=banner_status, inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif selected_option == "ticket_banner":
            await interaction.response.send_message("Upload an image to use as the ticket banner.", ephemeral=True)
            def check(msg): return msg.author.id == interaction.user.id and msg.attachments
            try:
                message = await self.ticket_system.bot.wait_for('message', check=check, timeout=60.0)
                if not message.attachments[0].content_type.startswith('image/'):
                    await interaction.followup.send("Invalid image type.", ephemeral=True)
                    return
                config['ticket_banner'] = message.attachments[0].url
                await interaction.followup.send("Banner set successfully!", ephemeral=True)
                try: await message.delete()
                except: pass
            except asyncio.TimeoutError:
                await interaction.followup.send("Image upload timed out.", ephemeral=True)

        else:
            current_text = config.get(selected_option, "")
            modal = TicketConfigModal(f"Edit {selected_option.replace('_', ' ').title()}", current_text)
            await interaction.response.send_modal(modal)
