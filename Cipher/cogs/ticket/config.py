
import json, os

TICKET_CONFIG_PATH = "storage/ticket_config.json"

class TicketSystem:
    def __init__(self, bot):
        self.bot = bot
        self.ticket_config = {}
        self.active_tickets = {}
        self.max_tickets_per_user = 4

    def generate_ticket_id(self):
        import random, string
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

    def get_user_ticket_count(self, guild_id, user_id):
        return sum(1 for t in self.active_tickets.get(guild_id, {}).values() if t['creator'] == user_id)

    def save_config(self):
        with open(TICKET_CONFIG_PATH, 'w') as f:
            json.dump(self.ticket_config, f, indent=4)

    def load_config(self):
        if os.path.exists(TICKET_CONFIG_PATH):
            with open(TICKET_CONFIG_PATH, 'r') as f:
                self.ticket_config = json.load(f)
        else:
            self.ticket_config = {}
